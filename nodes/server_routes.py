"""Registers this pack's HTTP route(s) on ComfyUI's own server (`PromptServer.instance.routes`
— confirmed pattern, matches ComfyUI's own `custom_nodes/example_node.py.example`), so the
`VideoRouter Model Picker` node's live combo (`nodes/models.py`) has something to poll.

Runs server-side, in the same process every node's `execute` already runs in — so it
resolves the key the same way every node does (`util.client.resolve_api_key`: Settings
panel, then `LLMROUTER_API_KEY`; no widget value to check here since this route takes no
per-node input). There's no per-request auth to forward from the frontend's plain
`axios.get(route)` call (`RemoteOptions` has no header/auth hook), which is fine here since
the key is a server-side setting, not a per-user browser credential.

Imported once at package load (`__init__.py`) purely for its route-registration side effect
— nothing in this module is meant to be imported for its return value.
"""

from __future__ import annotations

import logging

from aiohttp import web
from server import PromptServer

from ..util import client

IMAGE_MODELS_ROUTE = "/videorouter/image_models"


@PromptServer.instance.routes.get(IMAGE_MODELS_ROUTE)
async def _get_image_models(request: web.Request) -> web.Response:
    try:
        key = client.resolve_api_key(None)
        models = await client.list_image_models(key)
    except Exception as exc:
        # Deliberately broad: a network failure (DNS, timeout, connection refused — none of
        # which are `client.ApiError`, confirmed live 2026-09-14 when this route 500'd on a
        # `ClientConnectorDNSError` that only the narrower except left uncaught) must degrade
        # to the static fallback, not crash the combo widget's refresh request.
        logging.warning("VideoRouter: /v1/images/models fetch failed: %s", exc)
        return web.json_response(["auto"])
    return web.json_response(["auto"] + models)
