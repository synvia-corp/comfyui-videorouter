"""Monkey-patches the `price_badge` shown on a handful of OFFICIAL Partner Node schemas
(Kling/MiniMax/Veo) this pack relays, replacing comfy.org's own hardcoded credit-cost
estimate with a real videorouter.sh price — WITHOUT forking the ComfyUI frontend.

Why this works at all: `INPUT_TYPES()`/`GET_NODE_INFO_V1()` (what `/object_info` actually
serves to the frontend) call `cls.define_schema()` fresh on every request rather than caching
a schema built once at import time (`comfy_api/latest/_io.py::FINALIZE_SCHEMA`) — so replacing
a node class's `define_schema` classmethod is, in principle, enough; no need to touch anything
the frontend renders directly.

**The one real gotcha, found live (2026-XX-XX)**: `import comfy_api_nodes.nodes_kling` from
THIS pack resolves to a DIFFERENT class object than the one actually serving `/object_info` —
confirmed via `id()` comparison. ComfyUI loads `comfy_api_nodes` (a built-in "extra node
directory", not a normal importable package from this pack's own perspective) through its own
dynamic per-file loader (`nodes.py::load_custom_node`, `importlib.util.spec_from_file_location`
under a synthetic module name), a SEPARATE execution of the same source from what a plain
`from comfy_api_nodes.nodes_kling import ...` package-style import gives — two independent
class objects with identical code, different identity, patching one never touches the other.
Fixed by looking the class up from `nodes.NODE_CLASS_MAPPINGS[node_id]` instead — the exact
registry `server.py`'s `/object_info` handler reads from — never importing the node module
directly at all. `comfy_api_nodes`' own built-in nodes are registered before this pack's own
`__init__.py` runs (`init_builtin_extra_nodes()` precedes `init_external_custom_nodes()`), so
the lookup is populated by the time `install()` below runs.

`Schema` is a plain (non-frozen) dataclass, so the wrapped function just calls the ORIGINAL
`define_schema()` (keeping every real input/output/tooltip untouched) and mutates only the
returned object's `.price_badge` field before handing it back.

**What this does NOT do** (see comfyui/README.md's own "Known limitation" note, still true
for everything not covered here): it can't add a genuinely new input widget whose VALUE needs
to reach this platform's server, since the official node's own `execute()` only ever sends the
specific fields it already knows to send — a host-picker widget would need the node's real
request-sending logic rewritten, not just its displayed schema. Price-badge-only patches like
this are display-layer only; billing already reflects the real price/host before or after this
file ever runs, this only fixes what the UI *shows in advance*.

Scoped to the 3 nodes this pack has actually live-verified end-to-end this pass
(`docs/DESIGN-comfyui-integration.md`) — not all 26 relayed providers. Each node's real price
is read from an inline constant matching the exact row this session's live tests billed
against (`router/price_overrides_video.json`), not re-derived at runtime — if the underlying
price ever changes, this file needs a manual update, same "hand-verified, not auto-synced"
discipline every price row in this codebase already follows for its own listing.
"""

from __future__ import annotations

import logging


def _wrap_define_schema(node_cls, mutate) -> None:
    original = node_cls.define_schema.__func__

    @classmethod
    def patched(cls):
        schema = original(cls)
        mutate(schema)
        return schema

    node_cls.define_schema = patched


def _patch_by_node_id(node_id: str, mutate) -> bool:
    """Looks the class up from `nodes.NODE_CLASS_MAPPINGS` — the actual registry
    `/object_info` reads from — rather than importing the node module directly (see this
    file's own docstring for why a direct import resolves to the wrong class object).
    `mutate(schema)` is called on every fresh `define_schema()` result and is expected to
    mutate it in place (no return value used) — usually just setting `.price_badge`, but
    also rewriting a combo's own option text where the node's real dropdown names a
    checkpoint this platform doesn't actually use (see `_patch_kling_text_to_video`)."""
    import nodes as comfy_nodes  # local import — only exists inside a running ComfyUI process

    node_cls = comfy_nodes.NODE_CLASS_MAPPINGS.get(node_id)
    if node_cls is None:
        return False
    _wrap_define_schema(node_cls, mutate)
    return True


def _rename_combo_option(schema, widget_id: str, old: str, new: str) -> None:
    """Rewrites `old` -> `new` in a combo widget's own option strings and default value —
    for a node whose real dropdown names a checkpoint this platform's relay doesn't actually
    use (see each patch's own comment for why), so the dropdown doesn't visually contradict
    the price badge sitting right above it."""
    for inp in schema.inputs:
        if getattr(inp, "id", None) == widget_id and isinstance(getattr(inp, "options", None), list):
            inp.options = [o.replace(old, new) if isinstance(o, str) else o for o in inp.options]
            if isinstance(inp.default, str):
                inp.default = inp.default.replace(old, new)


def _patch_kling_text_to_video() -> bool:
    from comfy_api.latest import IO

    # Real price: this platform substitutes EVERY request here onto its own confirmed
    # `kling-v2-6` (Standard) row — $0.042/s, 1.02x platform markup — regardless of which
    # exact mode/checkpoint the node's own dropdown says (see `gateway/comfy_proxy.py`'s
    # `_KLING_PRICE_MODEL` comment for why). Live-verified this session: 10s billed exactly
    # $0.4284 (10 * 0.042 * 1.02).
    badge = IO.PriceBadge(
        depends_on=IO.PriceBadgeDepends(widgets=["mode"]),
        expr="""
        (
          $m := widgets.mode;
          $seconds := $contains($m, "10") ? 10 : 5;
          {
            "type": "usd",
            "usd": $seconds * 0.042 * 1.02,
            "format": {"suffix": " (videorouter.sh — kling-v2-6)", "approximate": true}
          }
        )
        """,
    )

    def mutate(schema):
        schema.price_badge = badge
        # The node's own `mode` combo still names "kling-v2-5-turbo" (the checkpoint
        # comfy.org's node actually targets) even though every request is substituted onto
        # `kling-v2-6` above — rewrite the option text itself so the dropdown doesn't
        # visually contradict the price badge sitting right above it.
        _rename_combo_option(schema, "mode", "kling-v2-5-turbo", "kling-v2-6")

    return _patch_by_node_id("KlingTextToVideoNode", mutate)


def _patch_minimax_h3() -> bool:
    from comfy_api.latest import IO

    # Real price: `minimax-h3` — $0.08/s at 768P, $0.13/s at 2K, 1.02x platform markup. Only
    # the node's "MiniMax H3" combo option is relayed (H3 Max/Max Turbo aren't) — this badge
    # assumes that option since it's the only one this pack's relay actually serves.
    badge = IO.PriceBadge(
        depends_on=IO.PriceBadgeDepends(widgets=["model", "model.resolution", "model.duration"]),
        expr="""
        (
          $r := $lookup(widgets, "model.resolution");
          $seconds := $lookup(widgets, "model.duration");
          $pps := $r = "2K" ? 0.13 : 0.08;
          {
            "type": "usd",
            "usd": $pps * $seconds * 1.02,
            "format": {"suffix": " (videorouter.sh — 'MiniMax H3' option only)", "approximate": true}
          }
        )
        """,
    )
    return _patch_by_node_id("MinimaxHailuo03TextToVideoNode", lambda schema: setattr(schema, "price_badge", badge))


def _patch_veo() -> bool:
    from comfy_api.latest import IO

    # Real price: this relay substitutes onto this platform's own multi-host Veo 3.1 rows and
    # always forces audio off (a request with `generate_audio=true` is rejected outright, see
    # `gateway/comfy_proxy.py`'s `_veo_create`) — cheapest-first failover means the ACTUAL host
    # is usually the Pika resale (confirmed live this session: $0.08/s at 720p for
    # veo-3.1-fast-generate, exactly `pika/veo-3.1-fast`'s real rate), so that's what's shown
    # here rather than the pricier direct-Google rate a caller would rarely actually pay.
    # `4k` has no confirmed Pika rate for the fast/lite tiers — shown using the 720p rate as a
    # labeled floor rather than a fabricated number, since JSONata has no clean "unknown" cell.
    badge = IO.PriceBadge(
        depends_on=IO.PriceBadgeDepends(widgets=["model", "resolution", "duration_seconds"]),
        expr="""
        (
          $m := widgets.model;
          $r := widgets.resolution;
          $seconds := widgets.duration_seconds;
          $pps :=
            $contains($m, "lite") ? ($r = "1080p" ? 0.05 : 0.03)
            : $contains($m, "fast") ? ($r = "1080p" ? 0.10 : 0.08)
            : 0.20;
          {
            "type": "usd",
            "usd": $pps * $seconds * 1.02,
            "format": {"suffix": " (videorouter.sh, no-audio; 4k uses the 720p floor rate)", "approximate": true}
          }
        )
        """,
    )
    return _patch_by_node_id("Veo3VideoGenerationNode", lambda schema: setattr(schema, "price_badge", badge))


def install() -> None:
    for patch in (_patch_kling_text_to_video, _patch_minimax_h3, _patch_veo):
        try:
            applied = patch()
            if applied:
                logging.info("VideoRouter: price-badge patch %s applied", patch.__name__)
            else:
                logging.info("VideoRouter: price-badge patch %s skipped (node not found — "
                            "harmless if this ComfyUI build renamed/removed it)", patch.__name__)
        except Exception as exc:  # noqa: BLE001 — a price-badge cosmetic patch must never
            # break node loading; comfy.org's own default badge is a safe fallback if any
            # single patch fails (e.g. an upstream ComfyUI update renames a class/field).
            logging.warning("VideoRouter: price-badge patch %s failed (cosmetic only, node "
                            "still works with the default comfy.org estimate): %r",
                            patch.__name__, exc)
