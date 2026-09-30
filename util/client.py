"""Thin async HTTP client over videorouter.sh's public API — `GET /v1/images/models`,
`POST /v1/images`, `POST /v1/uploads` (Phase 1, image-only; `POST /v1/videos` + poll lands
in Phase 2). Mirrors `cli/src/client.js`/`cli/src/config.js` in the main llmrouter repo: same
base URL + env var precedence, same Bearer auth, same `{"error": {"message", "type", "code"}}`
error shape — so error messages surfaced in a ComfyUI node match what a user would see from
the CLI or curl, not a third dialect invented for this pack.

Depends only on `aiohttp` beyond the stdlib — already a core ComfyUI server dependency, so
this doesn't pull anything new into a user's environment.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import aiohttp

DEFAULT_BASE_URL = "https://api.videorouter.sh/v1"


class ApiError(Exception):
    """Raised for any non-2xx response. `status`/`type`/`code` mirror the CLI's `ApiError`
    (`cli/src/client.js`) so a caller can special-case e.g. 402 (insufficient credits) the
    same way the CLI's own exit-code-2 handling does."""

    def __init__(self, status: int, body: dict):
        error = (body or {}).get("error") or {}
        message = error.get("message") or f"HTTP {status}"
        super().__init__(message)
        self.status = status
        self.type = error.get("type")
        self.code = error.get("code")
        self.body = body


def base_url() -> str:
    return os.environ.get("VIDEOROUTER_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _settings_file_path() -> Optional[str]:
    """Path to ComfyUI's own per-user settings file (`Settings > VideoRouter > Auth > API
    Key`'s storage, `js/videorouter_settings.js`, normally written through ComfyUI's
    generic `POST /settings/{id}` route, `app/app_settings.py`). Resolved straight off disk
    rather than over HTTP: a node's `execute()` runs outside a request context with no
    per-user path to resolve the "proper" way — but without `--multi-user` (the normal single-machine
    desktop/manual-install case) ComfyUI always uses the same fixed `"default"` user, so
    `<user_dir>/default/comfy.settings.json` is a stable, direct path
    (`app/user_manager.py`'s own `default_user = "default"` / `get_request_user_id`).
    Live-confirmed against a real ComfyUI install, 2026-09-14 (see README).

    `folder_paths` only exists inside a running ComfyUI process — imported lazily so this
    module still loads standalone (this pack's own non-ComfyUI unit tests). Returns `None`
    outside ComfyUI."""
    try:
        import folder_paths
    except ImportError:
        return None
    return os.path.join(folder_paths.get_user_directory(), "default", "comfy.settings.json")


def _settings_api_key() -> str:
    path = _settings_file_path()
    if path is None:
        return ""
    import json as _json

    try:
        with open(path) as f:
            data = _json.load(f)
    except (OSError, ValueError):
        return ""
    return str(data.get("VideoRouter.ApiKey") or "").strip()


def resolve_api_key(widget_value: Optional[str]) -> str:
    """Precedence: a node's own `api_key` widget (explicit per-node override) > the
    VideoRouter Settings-panel entry (set once, applies to every node — the recommended
    path). No environment-variable fallback (removed 2026-09-14, per product decision) —
    one clear source of truth, not several silently-stacked ones; a missing key is a clean
    error, not a guess about which of multiple places it might be set."""
    key = (widget_value or "").strip() or _settings_api_key()
    if not key:
        raise ApiError(401, {"error": {
            "message": "No VideoRouter API key configured. Set one in ComfyUI's Settings "
                       "> VideoRouter > Auth > API Key (recommended) or fill in this "
                       "node's api_key widget. Get a key at https://videorouter.sh/keys.",
            "type": "authentication_error",
        }})
    return key


async def request(method: str, path: str, api_key: str, *, json_body: Optional[dict] = None,
                   form: Optional[aiohttp.FormData] = None, timeout: float = 120.0) -> dict:
    url = base_url() + path
    headers = {"Authorization": f"Bearer {api_key}"}
    async with aiohttp.ClientSession() as session:
        async with session.request(
            method, url, json=json_body, data=form, headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            try:
                body = await resp.json(content_type=None)
            except Exception:
                text = await resp.text()
                body = {"error": {"message": text or f"HTTP {resp.status}",
                                   "type": "invalid_response"}}
            if resp.status >= 400:
                raise ApiError(resp.status, body if isinstance(body, dict) else {})
            return body


async def fetch_bytes(url: str, timeout: float = 120.0) -> bytes:
    """Downloads a generated-image URL from a `/v1/images` response — no auth header (R2
    presigned URLs and provider-hosted result URLs are both public-by-URL, same as every
    other client of this API's outputs)."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            resp.raise_for_status()
            return await resp.read()


async def upload_bytes(api_key: str, content: bytes, filename: str, content_type: str) -> str:
    """`POST /v1/uploads` (`gateway/uploads.py`) — stages local bytes in R2 and returns a
    presigned URL good for ~30 minutes, the bridge this pack uses for local-tensor -> hosted
    reference-image input (design doc §4.4). Not used by Phase 1's generate-only nodes yet;
    Image Edit and the Phase 2 video node call this for their `image`/`start_image_url`
    inputs."""
    form = aiohttp.FormData()
    form.add_field("file", content, filename=filename, content_type=content_type)
    body = await request("POST", "/uploads", api_key, form=form)
    return body["url"]


async def list_image_models(api_key: str) -> list[str]:
    body = await request("GET", "/images/models", api_key)
    return [row["id"] for row in body.get("data", [])]


async def generate_image(api_key: str, payload: dict) -> dict:
    return await request("POST", "/images", api_key, json_body=payload)


def extract_image_entries(body: dict) -> list[dict[str, Any]]:
    """`/v1/images`'s response shape (`gateway/server/images.py`, confirmed against the
    handler's own `data = {"created": ..., "data": [...]}` construction): each row in
    `data["data"]` has EITHER a `url` OR a `b64_json` field, never both."""
    return body.get("data") or []
