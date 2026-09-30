"""Conversions between ComfyUI's native `IMAGE` type (a `(B, H, W, C)` float32 tensor,
values 0..1) and the raw image bytes videorouter.sh's API sends/receives — PNG for upload,
whatever `media_type` a result comes back as for download. Uses Pillow/numpy/torch only —
all three are core ComfyUI dependencies already, nothing new pulled into a user's install.
"""

from __future__ import annotations

import io as _io

import numpy as np
from PIL import Image


def tensor_to_png_bytes(tensor, index: int = 0) -> bytes:
    """`tensor` is a ComfyUI IMAGE batch; encodes frame `index` as PNG bytes for
    `POST /v1/uploads` or an inline `data:` URI."""
    arr = tensor[index].detach().cpu().numpy()
    arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
    buf = _io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def bytes_to_tensor(content: bytes):
    """Inverse of `tensor_to_png_bytes` — decodes arbitrary image bytes (a hosted result)
    into a single-frame ComfyUI IMAGE batch."""
    import torch  # local import: only the download path needs torch, keeps module load cheap

    img = Image.open(_io.BytesIO(content)).convert("RGB")
    arr = np.array(img).astype(np.float32) / 255.0
    return torch.from_numpy(arr)[None, ...]


def batch_tensors(tensors: list):
    """Concatenates several single-frame IMAGE tensors (e.g. `n>1` results) into one batch,
    same shape a native ComfyUI generate node would return for a multi-image result."""
    import torch

    return torch.cat(tensors, dim=0)
