# comfyui-videorouter

ComfyUI nodes for [videorouter.sh](https://videorouter.sh) — call our hosted image/video
generation API (100+ models, price/failover routing across providers) from inside a ComfyUI
graph, billed to your existing `llmr_sk_...` credits. See
`docs/DESIGN-comfyui-integration.md` in the main `llmrouter` repo for the full design
rationale and the Phase 2 (video nodes)/Phase 3 (Registry publish) roadmap — this directory
is **Phase 1: image generation + edit only**.

Developed here alongside the server it talks to (same pattern as `cli/` in this repo, which
ships standalone as the `videorouter-cli` npm package) — will move to its own repo before
publishing to the ComfyUI Registry, since Registry conventions expect one repo per pack.

## Partner Node relay (Kling, MiniMax H3, BFL)

Besides its own nodes, installing this pack also redirects ComfyUI's **own official**
Kling, MiniMax H3, and BFL (`flux-pro-1.1-ultra`/`flux-kontext-pro`/`flux-kontext-max`)
Partner Nodes to bill through your videorouter.sh account instead of a comfy.org one — no
comfy.org login needed, no changes to those nodes. Every request is translated and routed
through this platform's own `/v1/videos`/`/v1/images` (never a separate direct-to-provider
path), so pricing/failover/sandbox behavior stay defined in exactly one place. Every other
official Partner Node (Veo, Luma, ElevenLabs, ...) is untouched, transparently relayed to
the real comfy.org. See `docs/DESIGN-comfyui-integration.md` §9 for the full mechanism.

**Live-tested with real, successfully-completed paid generations** (small amounts, user
OK'd): MiniMax H3, BFL `flux-kontext-pro`, and both official Kling nodes all confirmed
working end-to-end with real generated media, including one real bug caught and fixed
mid-session (a failover-routing case where polling initially hit the wrong upstream
provider).

Two different official Kling nodes, two different outcomes:
- **`KlingTextToVideoNode`** ("v2.5-turbo pro") — this platform has no confirmed
  direct-Kling price for that exact checkpoint/tier, so (per explicit product decision)
  the relay **substitutes** its own confirmed `kling-v2-6` (Standard) row instead of
  rejecting the request. Real generation, just not the exact tier picked in the dropdown.
- **"Kling 3.0 Turbo"** (a separate official node/endpoint) — needed no substitution at
  all; this platform already has a confirmed, live price for exactly this checkpoint
  (`pika/kling-3.0-turbo`, Pika's resale). Confirmed with a real generation.

## Nodes (Phase 1)

- **VideoRouter Image Generate** — text-to-image via `POST /v1/images`.
- **VideoRouter Image Edit** — image-to-image via `POST /v1/images` (uploads the input
  frame through `POST /v1/uploads` first to get a URL, same bridge Phase 2's video node will
  reuse for start-frame/reference inputs).
- **VideoRouter Model Picker** — live combo widget over `GET /v1/images/models`.

## Auth

Two ways to set the key, checked in this order:

1. **ComfyUI Settings → VideoRouter → Auth → API Key** (recommended) — set once, every
   node picks it up automatically. Saved server-side by ComfyUI itself
   (`user/default/comfy.settings.json`), never into a shared `workflow.json`. Requires
   this pack's bundled frontend fork (see "Frontend fork" below) for the masked,
   edit-gated field — plain ComfyUI renders it as an ordinary always-editable text box.
2. A node's own `api_key` widget — a per-node override. **Avoid for anything you'll share**:
   ComfyUI has no masked/password input type, and a widget value gets saved into
   `workflow.json` — a live key in a workflow file pasted into a forum/Discord is a real
   credential leak.

No environment-variable fallback (removed 2026-09-14) — one clear source of truth, not
several silently-stacked ones; a missing key is a clean error, not a guess about where it
might be set.

Get a key at https://videorouter.sh/keys.

Optional: `VIDEOROUTER_BASE_URL` to point at a non-default gateway (defaults to
`https://api.videorouter.sh/v1`).

## Install (once published)

Via ComfyUI Manager: search "VideoRouter". Manually: clone into your ComfyUI install's
`custom_nodes/` directory and `pip install -r requirements.txt` (or let Manager resolve
`pyproject.toml`'s dependencies).

## Status / testing

**Live-tested 2026-09-14** against a real `Comfy-Org/ComfyUI` checkout (CPU mode, a fresh
venv, `pip install -r requirements.txt`, this pack dropped into `custom_nodes/`) — not just
read against docs. Confirmed via the running server:

- The pack imports cleanly at startup with no error (`Import times for custom nodes` lists
  it at `0.0 seconds`, no `(IMPORT FAILED)` marker).
- `GET /object_info/VideoRouterImageGenerate` / `.../VideoRouterImageEdit` /
  `.../VideoRouterModelPicker` all return the exact schema the node code declares —
  `io.String.Input(multiline=True)`, `io.Combo.Input(options=..., remote=io.RemoteOptions(...))`,
  `io.Int.Input(min=, max=)`, `io.Image.Input`/`.Output()` all serialize as expected.
- A real queued prompt (`POST /prompt` with a `VideoRouterImageGenerate` → `SaveImage`
  graph) ran through ComfyUI's actual async execution engine
  (`EXECUTE_NORMALIZED_ASYNC` → `cls.execute(...)` → `util/client.py` → a real outbound
  `aiohttp` request to `https://api.videorouter.sh/v1/images`) with no signature/type
  errors — it only failed because `api.videorouter.sh` doesn't resolve from this sandbox
  (DNS, not a code bug); the whole call chain up to the actual network hop is verified.
  `SaveImage` accepted `VideoRouterImageGenerate`'s `IMAGE` output with no type mismatch.
- `VideoRouterModelPicker`'s live combo (`Combo.Input(remote=io.RemoteOptions(route=
  "/videorouter/image_models", ...))`) round-tripped for real: the route registered on
  ComfyUI's own server (`nodes/server_routes.py`, the same `PromptServer.instance.routes`
  pattern ComfyUI's own `custom_nodes/example_node.py.example` documents) actually
  responded. **This caught one real bug**, since fixed: the route's `except client.ApiError`
  didn't catch the DNS failure (`aiohttp.ClientConnectorDNSError`), so it 500'd instead of
  degrading to `["auto"]` — now catches broadly and always returns a usable fallback.
- `util/media_bridge.py`'s tensor↔PNG round trip and multi-image batching
  (`torch.cat`) were re-verified with real `torch` (not available in the main dev sandbox,
  available in the ComfyUI venv) — correct shapes and pixel values.

**Full real round trip, since verified**: pointed `VIDEOROUTER_BASE_URL` at this repo's own
local dev gateway (`python app.py`, `http://127.0.0.1:8000/v1` — no public DNS needed) with
a real `env=test` sandbox API key (zero cost, hits no real provider). With **no env var and
a blank node widget**, queuing `VideoRouterImageGenerate → SaveImage` completed
(`status_str: "success"`) and wrote a real PNG to ComfyUI's `output/` folder — proving the
full chain end to end: node → `util/client.py` → real running gateway code → auth → sandbox
response → PNG decode → `IMAGE` tensor → `SaveImage`.

**The Settings-panel auth path (`js/videorouter_settings.js`) is also live-confirmed**,
including one thing the docs didn't state outright: `WEB_DIRECTORY = "./js"` (declared in
`__init__.py`) is honored for a V3-schema (`comfy_entrypoint()`) node pack, not just the
legacy `NODE_CLASS_MAPPINGS` style — confirmed by fetching the served JS file
(`/extensions/comfyui-videorouter/videorouter_settings.js`, HTTP 200) and by running a
prompt with the key set *only* via a simulated Settings-panel write (no env var, no widget
value) — it resolved and completed successfully.

`VideoRouterModelPicker`'s live route was re-tested against the real gateway too (once its
`/v1/images/models` endpoint was live) and correctly returned the full model catalog
(128 entries) instead of the DNS-failure fallback.

**Still not verified:** `VideoRouterImageEdit`'s upload-then-edit path against a real
(non-sandbox) provider, and a real paid model rather than the sandbox echo — both need an
explicit decision to spend real money before testing, not something to do unprompted.
