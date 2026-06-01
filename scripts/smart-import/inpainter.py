"""
inpainter.py — Text removal & background reconstruction for Smart Import.

Backends (tiered, best first):
  1. LaMa (lama-cleaner Python package) — ML inpainting, high quality, needs PyTorch
  2. lama-cleaner CLI — subprocess fallback
  3. OpenCV TELEA — fast, no deps, basic quality (always available)

Classes
-------
- BackgroundInpainter — class-based API with sequential removal and extraction

Functions (backward-compatible with V4)
----------------------------------------
- inpaint_region(...) — original V4 API with crop + mask from bboxes
- inpaint_text_region(image, mask) — single region, any backend
- inpaint_image(image, mask) — alias for inpaint_text_region

Usage
-----
    from inpainter import BackgroundInpainter, inpaint_region

    # New class-based API
    inpainter = BackgroundInpainter()
    cleaned = inpainter.inpaint(image, mask)
    background = inpainter.extract_background(image, masks, z_order)

    # Legacy function API (V4) — unchanged
    path = inpaint_region(source_path="input.jpg", image_bbox={...}, ...)

CLI
---
    python inpainter.py --image input.jpg --mask mask.png
    python inpainter.py --image input.jpg --masks-dir ./masks/ --z-order 2,1,0
    python inpainter.py --info
"""

from __future__ import annotations

import argparse
import base64
import io
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Optional

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OPENROUTER_API_KEY_VAR = "OPENROUTER_API_KEY"
DEFAULT_GEMINI_MODEL = "google/gemini-3.1-flash-image-preview"
INPAINT_PROMPT = (
    "Remove ALL text from this image. Replace the areas where text was "
    "with the natural background that would be underneath (sky, rocks, sand, "
    "fabric, pattern, etc.). Keep all non-text areas exactly as they are. "
    "Return ONLY the cleaned image, no text description."
)
INPAINT_SYSTEM_PROMPT = (
    "You are an expert image inpainting tool. Remove text overlays "
    "from images and fill with natural background."
)

# When mask active pixel count exceeds this, we downscale before inpainting
_LARGE_MASK_THRESHOLD = 200_000

# ---------------------------------------------------------------------------
# BackgroundInpainter — class-based API
# ---------------------------------------------------------------------------


class BackgroundInpainter:
    """High-quality background reconstruction using LaMa with OpenCV fallback.

    Automatically selects the best available backend:
    LaMa package -> lama-cleaner CLI -> OpenCV TELEA.

    Parameters
    ----------
    lama_device:
        Device for LaMa: ``'cuda'`` or ``'cpu'``. Auto-detected if ``None``.
    lama_model:
        LaMa model variant: ``'lama'`` (default) or ``'ldm'``.
    opencv_radius:
        Inpainting radius for OpenCV fallback (default 3).
    cache_dir:
        Directory for caching inpainted backgrounds
        (default ``'output/inpaint-cache/'``).

    Usage
    -----
    >>> inpainter = BackgroundInpainter()
    >>> result = inpainter.inpaint(image, mask)
    >>> background = inpainter.extract_background(image, masks, z_order)
    """

    def __init__(
        self,
        lama_device: Optional[str] = None,
        lama_model: str = "lama",
        opencv_radius: int = 3,
        cache_dir: str = "output/inpaint-cache/",
    ):
        self.lama_device = lama_device or self._detect_device()
        self.lama_model = lama_model
        self.opencv_radius = opencv_radius
        self.cache_dir = cache_dir

        # LaMa model instance (lazy, set by _try_init_lama)
        self._lama_model = None
        self._lama_config = None

        # Resolve backend
        self._backend = self._init_backend()

        logger.info(
            "BackgroundInpainter: backend=%s device=%s opencv_radius=%d",
            self._backend,
            self.lama_device,
            self.opencv_radius,
        )

    # ------------------------------------------------------------------
    # Backend initialization
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_device() -> str:
        """Detect CUDA availability; fall back to ``'cpu'``."""
        try:
            import torch  # noqa: F401

            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "cpu"

    def _init_backend(self) -> str:
        """Initialise the best available inpainting backend.

        Returns
        -------
        str
            One of ``'lama'``, ``'lama-cli'``, ``'opencv'``.
        """
        if self._try_init_lama():
            return "lama"
        if self._try_init_lama_cli():
            return "lama-cli"
        logger.warning("lama-cleaner not available - falling back to OpenCV")
        return "opencv"

    def _try_init_lama(self) -> bool:
        """Try to import and instantiate LaMa from the ``lama_cleaner`` package."""
        try:
            from lama_cleaner.model import LaMa
            from lama_cleaner.schema import Config

            self._lama_model = LaMa(device=self.lama_device)
            self._lama_config = Config(
                ldm_steps=20,
                ldm_sampler="plms",
            )
            logger.info("LaMa backend ready (device=%s)", self.lama_device)
            return True
        except ImportError:
            logger.debug("lama_cleaner package not installed")
            return False
        except Exception as exc:
            logger.warning("LaMa initialisation failed: %s", exc)
            return False

    @staticmethod
    def _try_init_lama_cli() -> bool:
        """Check whether the ``lama-cleaner`` CLI is on ``PATH``."""
        cli = shutil.which("lama-cleaner")
        if cli:
            logger.info("lama-cleaner CLI found at %s", cli)
            return True
        return False

    # ------------------------------------------------------------------
    # Image pre-processing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_bgr(image: np.ndarray) -> np.ndarray:
        """Normalise an image to BGR 3-channel uint8 format.

        Handles RGBA (composites onto white), grayscale, and RGB inputs.
        """
        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        if image.shape[2] == 4:
            # Composite RGBA onto white
            alpha = image[:, :, 3].astype(np.float32) / 255.0
            rgb = image[:, :, :3].astype(np.float32)
            white = np.full_like(rgb, 255.0, dtype=np.float32)
            composite = rgb * alpha[:, :, None] + white * (1.0 - alpha[:, :, None])
            return composite.astype(np.uint8)

        # Already 3-channel -- assume BGR (OpenCV convention)
        return image.copy()

    @staticmethod
    def _check_large_mask(mask: np.ndarray) -> bool:
        """Return ``True`` if the mask exceeds the large-mask threshold."""
        return bool(np.count_nonzero(mask) > _LARGE_MASK_THRESHOLD)

    @staticmethod
    def _downscale(image: np.ndarray, mask: np.ndarray, scale: float = 0.5):
        """Resize image and mask by *scale* for cheaper inpainting."""
        h, w = image.shape[:2]
        nh, nw = int(h * scale), int(w * scale)
        mask_small = cv2.resize(mask, (nw, nh), interpolation=cv2.INTER_NEAREST)
        img_small = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)
        return img_small, mask_small

    # ------------------------------------------------------------------
    # Backend implementations
    # ------------------------------------------------------------------

    def _inpaint_lama_pkg(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Inpaint using LaMa via the ``lama_cleaner`` Python package.

        Parameters
        ----------
        image:
            BGR image (H, W, 3), uint8.
        mask:
            Binary mask (H, W), uint8 -- non-zero pixels are inpainted.

        Returns
        -------
        np.ndarray
            Inpainted BGR image.
        """
        # LaMa expects RGB input
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        result_rgb = self._lama_model(image_rgb, mask, config=self._lama_config)

        # LaMa can return a PIL Image or ndarray
        if isinstance(result_rgb, Image.Image):
            result_rgb = np.array(result_rgb)

        return cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)

    def _inpaint_lama_cli(
        self, image: np.ndarray, mask: np.ndarray
    ) -> Optional[np.ndarray]:
        """Inpaint via ``lama-cleaner`` CLI subprocess."""
        img_path = None
        msk_path = None
        out_path = None

        try:
            # Write inputs to temp files
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                img_path = f.name
            cv2.imwrite(img_path, image)

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                msk_path = f.name
            cv2.imwrite(msk_path, mask)

            fd, out_path = tempfile.mkstemp(suffix=".png")
            os.close(fd)

            cmd = [
                "lama-cleaner",
                "--model=lama",
                f"--device={self.lama_device}",
                f"--image={img_path}",
                f"--mask={msk_path}",
                f"--output={out_path}",
            ]
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120
            )

            if proc.returncode != 0:
                logger.warning(
                    "lama-cleaner CLI failed (rc=%d): %s",
                    proc.returncode,
                    proc.stderr[:500],
                )
                return None

            out_img = cv2.imread(out_path)
            if out_img is None:
                logger.warning("lama-cleaner CLI produced no output image")
                return None

            return out_img

        except FileNotFoundError:
            logger.warning("lama-cleaner CLI not found on PATH")
            return None
        except subprocess.TimeoutExpired:
            logger.warning("lama-cleaner CLI timed out (120s)")
            return None
        except Exception as exc:
            logger.warning("lama-cleaner CLI error: %s", exc)
            return None
        finally:
            for p in (img_path, msk_path, out_path):
                if p is not None:
                    try:
                        os.unlink(p)
                    except OSError:
                        pass

    @staticmethod
    def _inpaint_opencv(image: np.ndarray, mask: np.ndarray, radius: int = 3) -> np.ndarray:
        """Inpaint using OpenCV TELEA (fast, no-dependency fallback)."""
        return cv2.inpaint(
            image, mask,
            inpaintRadius=radius,
            flags=cv2.INPAINT_TELEA,
        )

    # ------------------------------------------------------------------
    # Dispatcher
    # ------------------------------------------------------------------

    def _dispatch(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Run inpainting on the active backend with graceful fallback chain."""
        # -- LaMa package
        if self._backend == "lama":
            try:
                return self._inpaint_lama_pkg(image, mask)
            except Exception as exc:
                logger.warning("LaMa package failed: %s - trying CLI", exc)

        # -- LaMa CLI
        cli_result = self._inpaint_lama_cli(image, mask)
        if cli_result is not None:
            return cli_result

        logger.warning("All LaMa backends failed - falling back to OpenCV")
        return self._inpaint_opencv(image, mask, self.opencv_radius)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def inpaint(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Inpaint a single masked region using the best available backend.

        Parameters
        ----------
        image:
            Input image (H, W, 3 or 4) uint8. Alpha channel is composited
            onto white automatically.
        mask:
            Binary mask (H, W) uint8 -- non-zero pixels are inpainted.

        Returns
        -------
        np.ndarray
            Inpainted image in BGR format.
        """
        # Normalise inputs
        image = self._ensure_bgr(image)
        mask = np.ascontiguousarray(mask, dtype=np.uint8)

        # Large mask optimisation: downscale -> inpaint -> upscale
        if self._check_large_mask(mask):
            px = np.count_nonzero(mask)
            logger.warning(
                "Large mask (%d px) - downscaling to 50%% for performance",
                px,
            )
            img_small, mask_small = self._downscale(image, mask, 0.5)
            h, w = image.shape[:2]

            try:
                result_small = self._dispatch(img_small, mask_small)
                return cv2.resize(
                    result_small, (w, h), interpolation=cv2.INTER_LINEAR
                )
            except Exception as exc:
                logger.warning(
                    "Inpainting on downscaled mask failed: %s - retrying full-size",
                    exc,
                )

        return self._dispatch(image, mask)

    def inpaint_sequential(
        self,
        image: np.ndarray,
        masks: list[np.ndarray],
        z_order: list[int],
    ) -> np.ndarray:
        """Remove elements sequentially from highest z-index to lowest.

        Each mask is inpainted in descending z-order, progressively revealing
        the layers underneath. When all elements are removed the result
        approximates the original background.

        Parameters
        ----------
        image:
            Composite image with all elements present (BGR uint8).
        masks:
            One binary mask per element, same length as *z_order*.
        z_order:
            Z-index values, one per element (higher = on top).

        Returns
        -------
        np.ndarray
            Image with all masked elements removed.
        """
        # Sort mask/z-order pairs descending by z_order
        pairs = sorted(
            zip(masks, z_order), key=lambda x: x[1], reverse=True
        )
        sorted_masks = [p[0] for p in pairs]

        current = image.copy()
        for idx, mask in enumerate(sorted_masks):
            px = np.count_nonzero(mask)
            logger.debug(
                "Sequential inpaint [%d/%d] z=%d mask=%d px",
                idx + 1,
                len(sorted_masks),
                z_order[idx],
                px,
            )
            current = self.inpaint(current, mask)

        return current

    def extract_background(
        self,
        image: np.ndarray,
        masks: list[np.ndarray],
        z_order: list[int],
    ) -> np.ndarray:
        """Extract the clean background after removing all foreground elements.

        This is a semantic alias for :meth:`inpaint_sequential`. The result
        represents the original background as it existed before any elements
        were placed on the canvas.

        Parameters
        ----------
        image:
            Composite image (BGR uint8).
        masks:
            One binary mask per foreground element.
        z_order:
            Z-index values, one per element.

        Returns
        -------
        np.ndarray
            Clean background image.
        """
        return self.inpaint_sequential(image, masks, z_order)

    def info(self) -> dict:
        """Return a report on available backends and current configuration.

        Returns
        -------
        dict
            Keys: ``active_backend``, ``available_backends``, ``device``,
            ``lama_model``, ``opencv_radius``, ``cv2_version``.
        """
        backends: dict[str, bool] = {
            "lama": False,
            "lama-cli": False,
            "opencv": True,  # always available
        }

        try:
            from lama_cleaner.model import LaMa  # noqa: F401

            backends["lama"] = True
        except ImportError:
            pass

        backends["lama-cli"] = shutil.which("lama-cleaner") is not None

        return {
            "active_backend": self._backend,
            "available_backends": backends,
            "device": self.lama_device,
            "lama_model": self.lama_model,
            "opencv_radius": self.opencv_radius,
            "cv2_version": cv2.__version__,
        }


# ===================================================================
# Backward-compatible function API
# ===================================================================

_shared_inpainter: Optional[BackgroundInpainter] = None


def _get_inpainter() -> BackgroundInpainter:
    """Return the module-level shared BackgroundInpainter (lazy-init)."""
    global _shared_inpainter
    if _shared_inpainter is None:
        _shared_inpainter = BackgroundInpainter()
    return _shared_inpainter


def inpaint_text_region(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Remove text from a single image region using any available backend.

    Parameters
    ----------
    image:
        Input image (BGR uint8).
    mask:
        Binary mask of the text region (uint8).

    Returns
    -------
    np.ndarray
        Inpainted image.
    """
    return _get_inpainter().inpaint(image, mask)


def inpaint_image(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Inpaint a masked image region (alias for ``inpaint_text_region``).

    Parameters
    ----------
    image:
        Input image (BGR uint8).
    mask:
        Binary mask of the region to inpaint (uint8).

    Returns
    -------
    np.ndarray
        Inpainted image.
    """
    return _get_inpainter().inpaint(image, mask)


# ===================================================================
# Existing V4 public API -- preserved unchanged
# ===================================================================


def inpaint_region(
    source_path: str,
    image_bbox: dict,
    text_bboxes: list[dict],
    method: str = "openrouter",
    canvas_scale: tuple[float, float] = (1.0, 1.0),
    canvas_offset: tuple[int, int] = (0, 0),
    output_path: Optional[str] = None,
) -> Optional[str]:
    """Remove text from a cropped image region using the specified method.

    .. note::
        This is the original V4 API kept for backward compatibility.

    Parameters
    ----------
    source_path:
        Path to the original source image.
    image_bbox:
        Bounding box ``{"x", "y", "w", "h"}`` in real pixels.
    text_bboxes:
        List of text bounding boxes overlapping the image region.
    method:
        ``"openrouter"`` | ``"lama"`` | ``"opencv"``.
    canvas_scale:
        (scale_x, scale_y) to convert Qwen coords to real pixels.
    canvas_offset:
        (offset_x, offset_y) of the crop within the full canvas.
    output_path:
        Where to save the cleaned image. Auto-generated if ``None``.

    Returns
    -------
    str or None
        Path to the saved cleaned image, or ``None`` on failure.
    """
    if not text_bboxes:
        logger.info("  [Inpaint] No overlapping text -- skipping")
        return None

    crop = _crop_from_source(source_path, image_bbox)
    if crop is None:
        return None

    mask = _create_mask(crop, text_bboxes, canvas_scale, canvas_offset)
    if mask is None or np.count_nonzero(mask) == 0:
        logger.info("  [Inpaint] Mask is empty -- skipping")
        return None

    logger.info(
        "  [Inpaint] Method=%s mask=%dpx text_count=%d",
        method,
        np.count_nonzero(mask),
        len(text_bboxes),
    )

    if method == "openrouter":
        result = _inpaint_openrouter(crop, mask)
    elif method == "lama":
        result = _inpaint_lama(crop, mask)
    elif method == "opencv":
        result = _inpaint_opencv_func(crop, mask, "telea")
    else:
        logger.error("  [Inpaint] Unknown method: %s", method)
        return None

    if result is None:
        logger.warning("  [Inpaint] Primary method failed -- trying OpenCV fallback")
        result = _inpaint_opencv_func(crop, mask, "telea")

    if result is None:
        logger.error("  [Inpaint] All methods failed")
        return None

    if output_path is None:
        output_path = _default_output_path(source_path, method)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, result)
    logger.info("  [Inpaint] Saved -> %s", os.path.basename(output_path))
    return output_path


# ===================================================================
# Internal helpers -- preserved from V4
# ===================================================================


def _crop_from_source(source_path: str, bbox: dict) -> Optional[np.ndarray]:
    """Crop a region from the source image; return BGR ndarray."""
    try:
        img = cv2.imread(source_path)
        if img is None:
            raise FileNotFoundError(f"Source not found: {source_path}")
        h, w = img.shape[:2]
        x = max(0, int(bbox.get("x", 0)))
        y = max(0, int(bbox.get("y", 0)))
        bw = max(1, min(int(bbox.get("w", 0)), w - x))
        bh = max(1, min(int(bbox.get("h", 0)), h - y))
        return img[y : y + bh, x : x + bw]
    except Exception as e:
        logger.error("  [Inpaint] Crop failed: %s", e)
        return None


def _create_mask(
    crop: np.ndarray,
    text_bboxes: list[dict],
    scale: tuple[float, float],
    offset: tuple[int, int],
) -> Optional[np.ndarray]:
    """Create a binary mask from text bounding boxes projected into crop space."""
    try:
        ch, cw = crop.shape[:2]
        mask = np.zeros((ch, cw), dtype=np.uint8)
        sx, sy = scale
        ox, oy = offset

        for tb in text_bboxes:
            tx = int(tb.get("x", 0) * sx) - ox
            ty = int(tb.get("y", 0) * sy) - oy
            tw = int(tb.get("w", 0) * sx)
            th = int(tb.get("h", 0) * sy)

            if tx + tw < 0 or tx > cw or ty + th < 0 or ty > ch:
                continue

            pad = 4
            x1 = max(0, tx - pad)
            y1 = max(0, ty - pad)
            x2 = min(cw, tx + tw + pad)
            y2 = min(ch, ty + th + pad)
            mask[y1:y2, x1:x2] = 255

        return mask
    except Exception as e:
        logger.error("  [Inpaint] Mask creation failed: %s", e)
        return None


# ===================================================================
# V4 inpainting backends -- updated LaMa import, preserved signatures
# ===================================================================


def _inpaint_openrouter(crop: np.ndarray, mask: np.ndarray) -> Optional[np.ndarray]:
    """Inpaint via OpenRouter / Gemini 3.1 Flash Image.

    .. note:: Requires ``OPENROUTER_API_KEY`` env var.
    """
    try:
        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(crop_rgb)
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        data_uri = f"data:image/png;base64,{b64}"

        overlay = crop.copy()
        overlay[mask > 0] = (0, 0, 255)
        overlay_rgb = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)
        overlay_pil = Image.fromarray(overlay_rgb)
        overlay_buf = io.BytesIO()
        overlay_pil.save(overlay_buf, format="PNG")
        overlay_b64 = base64.b64encode(overlay_buf.getvalue()).decode("utf-8")
        overlay_uri = f"data:image/png;base64,{overlay_b64}"

        import requests

        api_key = os.environ.get(OPENROUTER_API_KEY_VAR)
        if not api_key:
            raise ValueError(f"{OPENROUTER_API_KEY_VAR} not set")

        payload = {
            "model": DEFAULT_GEMINI_MODEL,
            "messages": [
                {"role": "system", "content": INPAINT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": INPAINT_PROMPT},
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ],
                },
            ],
        }

        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        choice = data["choices"][0]
        images = choice["message"].get("images", [])

        if not images:
            content = choice["message"].get("content")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "image_url":
                        img_part = part["image_url"]
                        url = img_part.get("url", "") if isinstance(img_part, dict) else str(img_part)
                        images = [{"image_url": {"url": url}}]
                        break

        if not images:
            logger.warning("  [Inpaint] No image in Gemini response")
            logger.debug("  [Inpaint] Response: %s", str(data)[:500])
            return None

        img_entry = images[0]
        img_url_container = img_entry.get("image_url", "")
        img_url = (
            img_url_container.get("url", "")
            if isinstance(img_url_container, dict)
            else str(img_url_container)
        )

        if not img_url or not img_url.startswith("data:image"):
            logger.warning("  [Inpaint] No data URI in response")
            return None

        _, encoded = img_url.split(",", 1)
        img_bytes = base64.b64decode(encoded)

        nparr = np.frombuffer(img_bytes, np.uint8)
        result = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if result is None:
            raise ValueError("Failed to decode inpainted image")

        crop_h, crop_w = crop.shape[:2]
        if result.shape[:2] != (crop_h, crop_w):
            result = cv2.resize(result, (crop_w, crop_h))

        return result

    except Exception as e:
        logger.warning("  [Inpaint] OpenRouter error: %s", e)
        return None


def _inpaint_lama(crop: np.ndarray, mask: np.ndarray) -> Optional[np.ndarray]:
    """Inpaint via LaMa (lama-cleaner) -- updated with correct import path."""
    try:
        from lama_cleaner.model import LaMa
        from lama_cleaner.schema import Config

        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        model = LaMa(device="cpu")
        config = Config(ldm_steps=20, ldm_sampler="plms")
        result_rgb = model(crop_rgb, mask, config=config)

        if isinstance(result_rgb, Image.Image):
            result_rgb = np.array(result_rgb)

        result = cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)
        return result
    except ImportError:
        logger.warning("  [Inpaint] lama_cleaner not installed (pip install lama-cleaner)")
        return None
    except Exception as e:
        logger.warning("  [Inpaint] LaMa error: %s", e)
        return None


def _inpaint_opencv_func(
    crop: np.ndarray, mask: np.ndarray, method: str = "telea"
) -> Optional[np.ndarray]:
    """Inpaint via OpenCV (TELEA or NS)."""
    try:
        radius = 5
        if method == "ns":
            result = cv2.inpaint(crop, mask, inpaintRadius=radius, flags=cv2.INPAINT_NS)
        else:
            result = cv2.inpaint(crop, mask, inpaintRadius=radius, flags=cv2.INPAINT_TELEA)
        return result
    except Exception as e:
        logger.warning("  [Inpaint] OpenCV error: %s", e)
        return None


def _default_output_path(source_path: str, method: str) -> str:
    """Generate a default output path for the inpainted crop."""
    base = os.path.splitext(os.path.basename(source_path))[0]
    return os.path.join(
        os.path.dirname(source_path),
        f"{base}_inpainted_{method}.png",
    )


# ===================================================================
# CLI entry point
# ===================================================================


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Smart Import Inpainter -- LaMa with OpenCV fallback",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python inpainter.py --image input.jpg --mask mask.png\n"
            "  python inpainter.py --image input.jpg"
            " --masks-dir ./masks/ --z-order 2,1,0\n"
            "  python inpainter.py --info\n"
        ),
    )
    parser.add_argument("--image", type=str, help="Path to input image")
    parser.add_argument("--mask", type=str, help="Path to single mask image")
    parser.add_argument(
        "--masks-dir",
        type=str,
        help="Directory containing mask files (one per element)",
    )
    parser.add_argument(
        "--z-order",
        type=str,
        help="Comma-separated z-order list, e.g. '2,1,0'",
    )
    parser.add_argument("--output", type=str, help="Output image path")
    parser.add_argument(
        "--info",
        action="store_true",
        help="Print available backends and exit",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="LaMa device: 'cuda' or 'cpu' (default: auto-detect)",
    )
    parser.add_argument(
        "--opencv-radius",
        type=int,
        default=3,
        help="OpenCV inpainting radius (default: 3)",
    )
    return parser


def _main() -> None:
    """CLI entry point for standalone inpainting."""
    parser = _build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(message)s",
    )

    # -- Backend info -------------------------------------------------
    if args.info:
        inpainter = BackgroundInpainter()
        info = inpainter.info()
        print("=== Inpainter Backend Info ===")
        print(f"  Active backend:    {info['active_backend']}")
        print(f"  Device:            {info['device']}")
        print(f"  OpenCV version:    {info['cv2_version']}")
        print()
        print("Available backends:")
        for name, avail in info["available_backends"].items():
            mark = "[OK]" if avail else "[--]"
            print(f"  {mark} {name}")
        return

    if not args.image:
        parser.print_help()
        sys.exit(1)

    inpainter = BackgroundInpainter(
        lama_device=args.device,
        opencv_radius=args.opencv_radius,
    )

    image = cv2.imread(args.image)
    if image is None:
        print(f"ERROR: Cannot read image: {args.image}", file=sys.stderr)
        sys.exit(1)

    # -- Single-mask mode --------------------------------------------
    if args.mask:
        mask = cv2.imread(args.mask, cv2.IMREAD_GRAYSCALE)
        if mask is None:
            print(f"ERROR: Cannot read mask: {args.mask}", file=sys.stderr)
            sys.exit(1)

        px = np.count_nonzero(mask)
        logger.info("Single inpainting: mask=%d px", px)
        result = inpainter.inpaint(image, mask)

        out_path = args.output or "output_inpainted.png"
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        cv2.imwrite(out_path, result)
        logger.info("Saved -> %s", out_path)
        return

    # -- Sequential masks mode ---------------------------------------
    if args.masks_dir and args.z_order:
        z_values = [int(z.strip()) for z in args.z_order.split(",")]

        masks: list[np.ndarray] = []
        for fname in sorted(os.listdir(args.masks_dir)):
            fpath = os.path.join(args.masks_dir, fname)
            m = cv2.imread(fpath, cv2.IMREAD_GRAYSCALE)
            if m is not None:
                masks.append(m)

        if len(masks) != len(z_values):
            logger.warning(
                "Mask count (%d) != z-order count (%d)",
                len(masks),
                len(z_values),
            )

        logger.info(
            "Sequential inpainting: %d masks, z_order=%s",
            len(masks),
            z_values,
        )
        result = inpainter.inpaint_sequential(image, masks, z_values)

        out_path = args.output or "output_background.png"
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        cv2.imwrite(out_path, result)
        logger.info("Saved background -> %s", out_path)
        return

    # -- No valid mode -----------------------------------------------
    print(
        "ERROR: Provide --mask (single) or --masks-dir + --z-order (sequential).",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    _main()
