"""comfyui-videorouter — its own image-generation nodes, plus a Partner Node relay that
redirects 20+ of ComfyUI's OFFICIAL nodes (Kling/MiniMax/Veo/Meshy/...) to bill through
videorouter.sh instead of comfy.org (see `comfy_relay.py`, `README.md`).

Registers via ComfyUI's V3 extension entrypoint (`comfy_entrypoint()` returning a
`ComfyExtension`) rather than the legacy `NODE_CLASS_MAPPINGS` dict, matching how ComfyUI's
own built-in API Nodes (`comfy_api_nodes/`) register as of 2026.
"""

from __future__ import annotations

from comfy_api.latest import ComfyExtension

from . import comfy_relay, price_patch
from .nodes import server_routes  # noqa: F401 - side effect: registers this pack's HTTP route
from .nodes.image import VideoRouterImageEdit, VideoRouterImageGenerate
from .nodes.models import VideoRouterModelPicker

_NODES = [
    VideoRouterImageGenerate,
    VideoRouterImageEdit,
    VideoRouterModelPicker,
]

# Loaded independently of the V3 node-registration path above — ComfyUI's frontend scans
# every custom node pack for this exact module-level name and auto-serves/loads any `.js`
# file under it (docs.comfy.org/custom-nodes/js/javascript_overview). Live-confirmed
# 2026-09-14 to work unchanged for a V3/`comfy_entrypoint()` pack like this one, not just
# the legacy `NODE_CLASS_MAPPINGS` style the docs page itself is written against.
# `js/videorouter_settings.js` adds the "VideoRouter > Auth > API Key" entry to ComfyUI's
# own Settings dialog.
WEB_DIRECTORY = "./js"

# Side effect, not a node registration: redirects ComfyUI's own official Kling/MiniMax
# Partner Nodes to bill through videorouter.sh instead of comfy.org — see
# `comfy_relay.py`'s docstring and `gateway/comfy_proxy.py` (main repo) for the mechanism.
# Every other Partner Node is unaffected (transparently relayed to the real comfy.org).
comfy_relay.install()

# Also a side effect, not a node registration: monkey-patches the price_badge shown on a
# few of the official nodes above (Kling/MiniMax/Veo) so the UI shows this platform's real
# price instead of comfy.org's own hardcoded credit estimate — see `price_patch.py`'s own
# docstring for why this works without forking the frontend, and its documented limits.
price_patch.install()


class VideoRouterExtension(ComfyExtension):
    async def get_node_list(self):
        return _NODES


async def comfy_entrypoint() -> ComfyExtension:
    return VideoRouterExtension()


__all__ = ["WEB_DIRECTORY"]
