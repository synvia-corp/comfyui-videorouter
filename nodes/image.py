"""VideoRouter Image Generate / VideoRouter Image Edit — `POST /v1/images`
(`gateway/server/images.py`). Both are synchronous: `execute` makes one HTTP call and
returns immediately with the result — no polling, unlike the Phase 2 video node.

NOTE on the V3 `io.*` schema types used below (`io.ComfyNode`, `io.Schema`, `io.String`,
`io.Combo`, `io.Int`, `io.Image`, `io.NodeOutput`): these match the pattern documented at
docs.comfy.org/custom-nodes/v3_migration and used by ComfyUI's own built-in
`comfy_api_nodes/` as of 2026-09, researched against source/docs rather than a live install
(no ComfyUI environment was available to run this in). Exact keyword arguments (e.g.
whether `io.String.Input` takes a `multiline` kwarg in your installed version) should be
verified against `comfy_api.latest.io` in the ComfyUI version this pack is installed into
before first real use — see the pack README's "Testing" section.
"""

from __future__ import annotations

from comfy_api.latest import io

from ..util import client, media_bridge
from .server_routes import IMAGE_MODELS_ROUTE

# Same live-refreshing combo mechanism the (now-removed) standalone VideoRouterModelPicker
# used — `Combo.Input(remote=io.RemoteOptions(...))` polls `IMAGE_MODELS_ROUTE`
# (`GET /v1/images/models`, proxied server-side by `server_routes.py`) and repopulates the
# dropdown in place, so there's no separate node just to browse the catalog.
_MODEL_COMBO_KWARGS = dict(
    options=["auto"], default="auto",
    remote=io.RemoteOptions(route=IMAGE_MODELS_ROUTE, refresh_button=True),
)


class VideoRouterImageGenerate(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="VideoRouterImageGenerate",
            display_name="VideoRouter Image Generate",
            category="VideoRouter/Image",
            description="Generate an image via videorouter.sh (100+ hosted models, billed "
                        "to your LLMROUTER_API_KEY credits).",
            inputs=[
                io.String.Input("prompt", multiline=True),
                io.Combo.Input("model", **_MODEL_COMBO_KWARGS),
                io.Int.Input("n", default=1, min=1, max=4),
                io.String.Input("aspect_ratio", optional=True, default=""),
                io.String.Input("resolution", optional=True, default=""),
            ],
            outputs=[
                io.Image.Output(),
            ],
            is_api_node=True,
        )

    @classmethod
    async def execute(cls, prompt: str, model: str, n: int, aspect_ratio: str,
                       resolution: str) -> io.NodeOutput:
        key = client.resolve_api_key()
        payload: dict = {"model": model, "prompt": prompt, "n": n}
        if aspect_ratio:
            payload["aspect_ratio"] = aspect_ratio
        if resolution:
            payload["resolution"] = resolution
        body = await client.generate_image(key, payload)
        tensor = await _entries_to_image_batch(body)
        return io.NodeOutput(tensor)


class VideoRouterImageEdit(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="VideoRouterImageEdit",
            display_name="VideoRouter Image Edit",
            category="VideoRouter/Image",
            description="Image-to-image edit via videorouter.sh — requires an "
                        "edit-capable model.",
            inputs=[
                io.Image.Input("image"),
                io.String.Input("prompt", multiline=True),
                io.Combo.Input("model", **_MODEL_COMBO_KWARGS),
                io.Int.Input("n", default=1, min=1, max=4),
                io.String.Input("aspect_ratio", optional=True, default=""),
                io.String.Input("resolution", optional=True, default=""),
            ],
            outputs=[
                io.Image.Output(),
            ],
            is_api_node=True,
        )

    @classmethod
    async def execute(cls, image, prompt: str, model: str, n: int, aspect_ratio: str,
                       resolution: str) -> io.NodeOutput:
        key = client.resolve_api_key()
        png_bytes = media_bridge.tensor_to_png_bytes(image)
        ref_url = await client.upload_bytes(key, png_bytes, "input.png", "image/png")
        # `input_references` (gateway/server/images.py) — array of `{"image_url": {"url": ...}}`,
        # the same reference shape `/v1/videos` uses for its own reference fields.
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "n": n,
            "input_references": [{"image_url": {"url": ref_url}}],
        }
        if aspect_ratio:
            payload["aspect_ratio"] = aspect_ratio
        if resolution:
            payload["resolution"] = resolution
        body = await client.generate_image(key, payload)
        tensor = await _entries_to_image_batch(body)
        return io.NodeOutput(tensor)


async def _entries_to_image_batch(body: dict):
    entries = client.extract_image_entries(body)
    if not entries:
        raise RuntimeError(f"VideoRouter returned no images: {body}")
    tensors = []
    for entry in entries:
        if entry.get("url"):
            content = await client.fetch_bytes(entry["url"])
        elif entry.get("b64_json"):
            import base64
            content = base64.b64decode(entry["b64_json"])
        else:
            raise RuntimeError(f"unrecognized /v1/images result entry: {entry}")
        tensors.append(media_bridge.bytes_to_tensor(content))
    return media_bridge.batch_tensors(tensors)
