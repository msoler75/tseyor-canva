"""
Standalone image utility functions for the Smart Import pipeline.

Provides:
- ``extract_region`` — crop a region and save to a file (temp by default).
- ``region_to_data_uri`` — crop a region and return a base64 data URI.

Both functions clamp coordinates to image bounds, handle negative/zero-area
bboxes gracefully, and preserve the source image format.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import tempfile
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)


def _crop(source_path: str, bbox: dict) -> tuple[Image.Image, str]:
    """Internal: open an image, clamp the bbox, crop, return (Image, format).

    ``format`` is the source image format string (e.g. ``"JPEG"``, ``"PNG"``,
    ``"WEBP"``), or ``"PNG"`` as a safe default.

    Parameters
    ----------
    source_path:
        Filesystem path to the source image.
    bbox:
        Bounding box dict with ``x``, ``y``, ``w``, ``h``.

    Returns
    -------
    tuple[PIL.Image, str]
        Cropped image and its format.

    Raises
    ------
    FileNotFoundError
        If the source image does not exist.
    ValueError
        If the resulting crop area is zero after clamping.
    """
    if not os.path.isfile(source_path):
        raise FileNotFoundError(f"Source image not found: {source_path}")

    x = int(bbox.get("x", 0))
    y = int(bbox.get("y", 0))
    w = int(bbox.get("w", 0))
    h = int(bbox.get("h", 0))

    if w <= 0 or h <= 0:
        raise ValueError(f"Zero-area bbox: {bbox}")

    img = Image.open(source_path)
    src_format = (img.format or "PNG").upper()
    img_w, img_h = img.size

    x = max(0, min(x, img_w - 1))
    y = max(0, min(y, img_h - 1))
    w = min(w, img_w - x)
    h = min(h, img_h - y)

    if w <= 0 or h <= 0:
        raise ValueError(f"Bbox outside image bounds: {bbox} vs ({img_w}x{img_h})")

    return img.crop((x, y, x + w, y + h)), src_format


def region_to_data_uri(source_path: str, bbox: dict) -> str:
    """Crop an image region and return it as a base64 data URI.

    Parameters
    ----------
    source_path:
        Filesystem path to the source image.
    bbox:
        Bounding box dict with ``x``, ``y``, ``w``, ``h``.

    Returns
    -------
    str
        Data URI string (e.g. ``data:image/png;base64,...``) or an empty
        string if cropping fails for any reason (missing file, zero-area,
        bounds error, IO error, etc.).
    """
    try:
        crop, src_format = _crop(source_path, bbox)

        fmt = src_format.lower()
        if fmt in ("jpg", "jpeg"):
            fmt = "JPEG"
            mime = "image/jpeg"
        elif fmt == "webp":
            mime = "image/webp"
        else:
            fmt = "PNG"
            mime = "image/png"

        buf = io.BytesIO()
        crop.save(buf, format=fmt)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:{mime};base64,{b64}"

    except Exception as exc:
        logger.error("Failed to crop from %s: %s", source_path, exc)
        return ""


def extract_region(
    source_path: str,
    bbox: dict,
    output_path: Optional[str] = None,
) -> Optional[str]:
    """Crop an image region and save it to a file.

    If ``output_path`` is ``None`` a temporary file is created (cleaned up
    by the caller or on interpreter exit).

    Parameters
    ----------
    source_path:
        Filesystem path to the source image.
    bbox:
        Bounding box dict with ``x``, ``y``, ``w``, ``h``.
    output_path:
        Where to write the cropped image.  ``None`` → a temp file is created.

    Returns
    -------
    str or None
        Absolute path to the written image file, or ``None`` on failure.
    """
    try:
        crop, src_format = _crop(source_path, bbox)

        if output_path is None:
            fd, output_path = tempfile.mkstemp(
                suffix=_format_ext(src_format),
                prefix="smart-import-crop-",
            )
            os.close(fd)

        crop.save(output_path)
        logger.debug("Extracted region to %s", output_path)
        return output_path

    except Exception as exc:
        logger.error("Failed to extract region from %s: %s", source_path, exc)
        return None


def _format_ext(img_format: Optional[str]) -> str:
    """Return a file extension for a PIL image format."""
    fmt = (img_format or "PNG").lower()
    return {".jpeg": ".jpg", "jpeg": ".jpg", "jpg": ".jpg", "png": ".png", "webp": ".webp"}.get(fmt, ".png")
