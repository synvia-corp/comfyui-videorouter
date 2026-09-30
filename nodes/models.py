"""VideoRouter Model Picker — a combo widget over `GET /v1/images/models`, live-refreshed via
ComfyUI's `Combo.Input(remote=io.RemoteOptions(...))` mechanism (confirmed against real
ComfyUI source, 2026-09: `comfy_api/latest/_io.py`'s `RemoteOptions` class + the frontend's
`useRemoteWidget.ts`, which does a plain `axios.get(route)` expecting a bare JSON array back
— no `{value,label}` wrapping). `route` below is registered on ComfyUI's own server in
`server_routes.py`, the same `@PromptServer.instance.routes.get(...)` pattern ComfyUI's own
`custom_nodes/example_node.py.example` documents.

Outputs a plain model-id string that wires into VideoRouterImageGenerate/-Edit's `model`
input, so the two Generate nodes don't each need their own live-fetch logic.
"""

from __future__ import annotations

from comfy_api.latest import io

from .server_routes import IMAGE_MODELS_ROUTE


class VideoRouterModelPicker(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="VideoRouterModelPicker",
            display_name="VideoRouter Model Picker",
            category="VideoRouter",
            description="Live image-model catalog from videorouter.sh "
                        "(GET /v1/images/models, via LLMROUTER_API_KEY in this ComfyUI "
                        "process's own environment).",
            inputs=[
                io.Combo.Input(
                    "model", options=["auto"], default="auto",
                    remote=io.RemoteOptions(route=IMAGE_MODELS_ROUTE, refresh_button=True),
                ),
            ],
            outputs=[
                io.String.Output(display_name="model"),
            ],
        )

    @classmethod
    def execute(cls, model: str) -> io.NodeOutput:
        return io.NodeOutput(model)
