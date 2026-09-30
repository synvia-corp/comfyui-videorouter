"""Redirects ComfyUI's own OFFICIAL Partner API Nodes (Kling, MiniMax, BFL, ...) to bill
against the user's videorouter.sh account instead of a comfy.org one — see
`gateway/comfy_proxy.py` in the main llmrouter repo for the full mechanism and why it works
(every official node's request path is already the underlying provider's own real API path,
just resolved against the overridable `args.comfy_api_base` launch flag).

This is a deliberate side effect of installing this node pack, not something a user opts
into per-node — flagged loudly in `install()`'s log line so it's never a silent surprise.
Only Kling/MiniMax are actually billed through our proxy (everything else transparently
relays to the REAL `https://api.comfy.org`, so no other official node breaks or changes
behavior — see `gateway/comfy_proxy.py`'s module docstring).
"""

from __future__ import annotations

import logging

from .util import client

_COMFY_ORG_DEFAULT = "https://api.comfy.org"


def _proxy_root() -> str:
    """`util.client.base_url()` is our OWN `/v1`-suffixed API base
    (`https://videorouter.sh/v1` by default) — this proxy lives at the bare root
    (`https://videorouter.sh/comfy/...`), a sibling of `/v1`, not under it."""
    root = client.base_url()
    if root.endswith("/v1"):
        root = root[: -len("/v1")]
    return root


def install() -> None:
    try:
        from comfy.cli_args import args
    except ImportError:
        return  # not actually running inside ComfyUI (e.g. this pack's own standalone tests)

    current = getattr(args, "comfy_api_base", None)
    if current not in (None, "", _COMFY_ORG_DEFAULT):
        # Already pointed somewhere non-default — respect it rather than silently
        # overriding a user's (or another pack's) own choice.
        logging.info(
            "VideoRouter: comfy_api_base is already set to %r — not overriding it, so "
            "Kling/MiniMax Partner Nodes will NOT bill through videorouter.sh this run.",
            current,
        )
        return

    try:
        key = client.resolve_api_key()
    except client.ApiError:
        logging.info(
            "VideoRouter: no API key configured yet (Settings > VideoRouter > Auth > API "
            "Key, or LLMROUTER_API_KEY) — ComfyUI's official Kling/MiniMax Partner Nodes "
            "will keep billing through comfy.org as normal until one is set."
        )
        return

    # NOT `.../comfy/{key}/proxy` — every Partner Node's own `ApiEndpoint(path=...)` already
    # starts with "/proxy/<provider>/..." (confirmed against ComfyUI's real source, e.g.
    # `nodes_kling.py`'s `ApiEndpoint(path="/proxy/kling/v1/videos/text2video")`), and the
    # node client's own request builder (`comfy_api_nodes/util/client.py::_request_base`)
    # does `urljoin(comfy_api_base + "/", path.lstrip("/"))` — a relative path is APPENDED
    # to this base, never replacing a trailing segment of it. Including "/proxy" here too
    # produced a real, previously-undetected bug: every real node request resolved to
    # `.../comfy/{key}/proxy/proxy/kling/...` (double "proxy"), which `gateway/comfy_proxy.
    # py`'s `rest.startswith("kling/")`-style dispatch never matches (`rest` was actually
    # "proxy/kling/...") — every request silently fell through to `_passthrough`, which
    # itself then mis-built `https://api.comfy.org/proxy/proxy/kling/...` (also broken)
    # instead of ever reaching this platform's billing. Confirmed via `urllib.parse.urljoin`
    # against the exact production string shape, 2026-XX-XX — every previous "live-tested"
    # claim in `docs/DESIGN-comfyui-integration.md` §9-11 was verified by hitting `gateway/
    # comfy_proxy.py`'s HTTP endpoint directly with the CORRECT single-`/proxy/` path (i.e.
    # simulating what a node WOULD send), never by actually running a real ComfyUI process
    # with this override installed end-to-end — so this defect went uncaught until now.
    # `VideoRouter.ProviderPolicy` (`js/videorouter_settings.js`) rides in the URL as an
    # EXTRA path segment, same reasoning as the API key itself: Comfy's own client code only
    # ever attaches its own comfy.org auth headers, never a hook for a third-party pack to
    # inject anything else, so the base URL is the only channel available at all. Read once
    # here (not re-read per request — `args.comfy_api_base` is set once at pack import), so
    # changing this setting needs a ComfyUI restart to take effect, same as the API key.
    # Server-side (`gateway/comfy_proxy.py`) has a SEPARATE route for this `{policy}`-bearing
    # shape, purely additive — `client.settings_provider_policy()` always returns a real
    # value now (defaults to `"lowest_cost"`, never `""`), so in practice this always takes
    # the `/{policy}` branch; the plain `.../comfy/{key}/...` shape stays supported below
    # only for defensiveness (e.g. a future caller of this same function returning `""`),
    # not because a real install commonly hits it.
    policy = client.settings_provider_policy()
    args.comfy_api_base = f"{_proxy_root()}/comfy/{key}/{policy}" if policy else f"{_proxy_root()}/comfy/{key}"
    logging.info(
        "VideoRouter: redirecting ComfyUI's official Kling and MiniMax Partner Nodes to "
        "bill through your videorouter.sh account instead of comfy.org "
        "(comfy_api_base=%s/comfy/<key>%s). Every other Partner Node is unaffected — "
        "still relayed transparently to the real api.comfy.org.",
        _proxy_root(), f"/{policy}" if policy else "",
    )
