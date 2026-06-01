"""
pipeline_v5.py — Smart Import V5. Dual-Model Pipeline (Variante B).

V5 combina Qwen3-VL-32B (estructura de layout) con Florence-2 (OCR preciso)
para detección superior de diseño.

Flujo:
  1. Qwen3-VL: detección unificada (textos, imágenes, formas, fondo, z-order)
  2. Florence-2: OCR preciso con bboxes + region descriptions
  3. Coordinate Merge: reemplaza textos de Qwen con OCR de Florence-2
  4. OpenCV: paleta dominante + dimensiones reales
  5. Assembly: fusión detección + paleta (reusa assemble_v3)
  6. Crop + Inpaint: recorta regiones de imagen, remueve texto superpuesto
  7. SceneGraph: coordenadas escaladas a canvas real
  8. Compile: .tc con imágenes limpias embebidas
  9. Render: headless PNG

Uso:
    python pipeline_v5.py --image path/to/image.jpg
    python pipeline_v5.py --image path/to/image.jpg --inpaint opencv
    python pipeline_v5.py --all
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from typing import Any, Optional

from florence_client import florence_caption, florence_dense_regions, florence_ocr
from openrouter import OpenRouterClient

# Reuse V3 and V4 internals
from pipeline_v3 import (
    QWEN_DETECTION_PROMPT,
    QWEN_DETECTION_SYSTEM,
    _safe_float,
    assemble_v3,
    extract_palette,
    find_images,
    render_tc,
)
from pipeline_v4 import (
    _crop_and_inpaint,
    compile_to_tc,
    to_scenegraph,
)

logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

# Replicate rate limit: burst=1, 6 requests/minute → 10s minimum spacing
FLORENCE_MIN_INTERVAL: float = 12.0


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: Florence-2 Cache + Rate Limiting
# ═══════════════════════════════════════════════════════════════════════════════


class FlorenceCache:
    """Cache manager for Florence-2 API results.

    Saves Florence-2 output to a JSON file so re-runs skip API calls entirely.
    Enforces rate limiting with a minimum interval between calls.

    Usage::

        cache = FlorenceCache("output/florence-cache.json")
        data = cache.load()
        if data is None:
            cache.wait_for_rate_limit()
            data = florence_ocr(...)
            cache.save(data)

    Attributes
    ----------
    cache_path : str
        Path to the cache JSON file.
    """

    def __init__(self, cache_path: str) -> None:
        """Initialize the cache manager.

        Parameters
        ----------
        cache_path:
            Path to the cache JSON file.
        """
        self.cache_path = cache_path
        self._data: Optional[dict] = None
        self._last_call: float = 0.0

    def load(self) -> Optional[dict]:
        """Load cached Florence-2 results from disk.

        Returns
        -------
        dict or None
            The cached data, or None if no cache exists or reading fails.
        """
        if os.path.isfile(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                logger.info("  [Florence] Cache loaded (%s)", self.cache_path)
                return self._data
            except Exception as e:
                logger.warning("  [Florence] Cache read failed: %s", e)
        return None

    def save(self, data: dict) -> None:
        """Save Florence-2 results to cache on disk.

        Parameters
        ----------
        data:
            Dictionary with OCR, dense_regions, and caption results.
        """
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self._data = data
        logger.info("  [Florence] Cache saved (%s)", self.cache_path)

    def wait_for_rate_limit(self) -> None:
        """Block until the minimum interval since the last call has elapsed.

        Replicate rate limit is 6 requests/minute (burst=1), so this ensures
        at least ``FLORENCE_MIN_INTERVAL`` seconds between calls.
        """
        elapsed = time.monotonic() - self._last_call
        if elapsed < FLORENCE_MIN_INTERVAL:
            wait = FLORENCE_MIN_INTERVAL - elapsed
            logger.info("  [Florence] Rate limit: waiting %.1fs...", wait)
            time.sleep(wait)
        self._last_call = time.monotonic()


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2b: Run Florence-2 tasks (single entry point)
# ═══════════════════════════════════════════════════════════════════════════════


def _run_florence_tasks(
    image_path: str,
    canvas_w: float,
    canvas_h: float,
    cache: FlorenceCache,
    allow_api_calls: bool = True,
) -> dict:
    """Execute all Florence-2 tasks with caching and rate limiting.

    Checks cache first. If cache miss and ``allow_api_calls`` is ``True``,
    calls Florence-2 OCR, dense regions, and caption sequentially, respecting
    rate limits. If ``allow_api_calls`` is ``False`` and no cache exists,
    returns empty data with a warning.

    Parameters
    ----------
    image_path:
        Path to the source image.
    canvas_w:
        Real canvas width in pixels.
    canvas_h:
        Real canvas height in pixels.
    cache:
        :class:`FlorenceCache` instance for caching results.
    allow_api_calls:
        If ``True`` (default), call Florence-2 API on cache miss.
        If ``False``, only use cached data.

    Returns
    -------
    dict
        Dictionary with keys ``ocr``, ``dense_regions``, ``caption``.
    """
    # Check cache first
    cached = cache.load()
    if cached is not None:
        return cached

    if not allow_api_calls:
        logger.info("  [Florence-2] No cache and API calls disabled — using empty data")
        return {"ocr": [], "dense_regions": [], "caption": ""}

    logger.info("  [Florence-2] Running OCR and dense region caption...")
    data: dict[str, Any] = {
        "ocr": [],
        "dense_regions": [],
        "caption": "",
    }

    # --- OCR ---
    cache.wait_for_rate_limit()
    try:
        data["ocr"] = florence_ocr(image_path, canvas_w, canvas_h)
        logger.info("    OCR: %d text(s) detected", len(data["ocr"]))
    except Exception as e:
        logger.warning("    Florence-2 OCR failed: %s", e)

    # --- Dense regions ---
    cache.wait_for_rate_limit()
    try:
        data["dense_regions"] = florence_dense_regions(image_path, canvas_w, canvas_h)
        logger.info("    Dense regions: %d region(s)", len(data["dense_regions"]))
    except Exception as e:
        logger.warning("    Florence-2 dense regions failed: %s", e)

    # --- Caption (no extra rate-limit wait needed) ---
    try:
        data["caption"] = florence_caption(image_path)
        logger.info("    Caption: %s", data["caption"][:80])
    except Exception as e:
        logger.warning("    Florence-2 caption failed: %s", e)

    # Save cache
    cache.save(data)
    return data


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: Coordinate Merge (Qwen + Florence-2)
# ═══════════════════════════════════════════════════════════════════════════════


def _bbox_iou(a: dict, b: dict) -> float:
    """Compute Intersection-over-Union between two normalized bounding boxes.

    Both bboxes use the format ``{x, y, w, h}`` with values in ``[0, 1]``.

    Parameters
    ----------
    a:
        First bbox.
    b:
        Second bbox.

    Returns
    -------
    float
        IoU value in ``[0, 1]``. Returns ``0.0`` if there is no overlap.
    """
    ax1 = a["x"]
    ay1 = a["y"]
    ax2 = a["x"] + a["w"]
    ay2 = a["y"] + a["h"]

    bx1 = b["x"]
    by1 = b["y"]
    bx2 = b["x"] + b["w"]
    by2 = b["y"] + b["h"]

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih

    area_a = a["w"] * a["h"]
    area_b = b["w"] * b["h"]
    union = area_a + area_b - inter

    return inter / union if union > 0 else 0.0


def _normalize_qwen_position(pos: dict, qw: float, qh: float) -> dict:
    """Convert a Qwen canvas-space position to normalized ``[0, 1]``.

    Parameters
    ----------
    pos:
        Position dict with keys ``x``, ``y``, ``width``, ``height``.
    qw:
        Qwen's canvas width estimate.
    qh:
        Qwen's canvas height estimate.

    Returns
    -------
    dict
        Normalized bbox ``{x, y, w, h}`` in ``[0, 1]``.
    """
    x = _safe_float(pos.get("x", 0), 0)
    y = _safe_float(pos.get("y", 0), 0)
    w = _safe_float(pos.get("width", 0), 0)
    h = _safe_float(pos.get("height", 0), 0)
    if qw <= 0 or qh <= 0:
        return {"x": x, "y": y, "w": w, "h": h}
    return {
        "x": x / qw if qw else 0.0,
        "y": y / qh if qh else 0.0,
        "w": w / qw if qw else 0.0,
        "h": h / qh if qh else 0.0,
    }


def _denormalize_to_qwen_space(bbox: dict, qw: float, qh: float) -> dict:
    """Convert a normalized ``[0, 1]`` bbox back to Qwen's canvas space.

    Parameters
    ----------
    bbox:
        Normalized bbox ``{x, y, w, h}`` in ``[0, 1]``.
    qw:
        Qwen's canvas width estimate.
    qh:
        Qwen's canvas height estimate.

    Returns
    -------
    dict
        Position dict ``{x, y, width, height}`` in Qwen canvas space.
    """
    return {
        "x": round(bbox["x"] * qw, 1),
        "y": round(bbox["y"] * qh, 1),
        "width": round(bbox["w"] * qw, 1),
        "height": round(bbox["h"] * qh, 1),
    }


def merge_text_elements(
    qwen_detection: dict,
    florence_texts: list[dict],
    iou_threshold: float = 0.1,
) -> list[dict]:
    """Replace Qwen text elements with Florence-2 OCR results where they overlap.

    Both coordinate systems are converted to ``[0, 1]`` normalised space for
    IoU comparison. Each Qwen text element is matched to the nearest Florence-2
    element by IoU. If a match is found, the Qwen entry is replaced with
    Florence-2's text and bbox. Qwen texts with no Florence-2 match are kept
    as-is. Unmatched Florence-2 texts with high confidence are appended.

    Parameters
    ----------
    qwen_detection:
        Raw Qwen detection output (contains ``text_elements``, ``canvas``).
    florence_texts:
        List from :func:`florence_ocr` — each entry has
        ``{text, bbox: {x, y, w, h}, confidence}``.
        Bboxes are already normalised to ``[0, 1]``.
    iou_threshold:
        Minimum IoU to consider a match. Default ``0.1``.

    Returns
    -------
    list[dict]
        Merged text elements in Qwen's canvas coordinate space, ready for
        :func:`assemble_v3`.
    """
    canvas = qwen_detection.get("canvas", {})
    qw = _safe_float(canvas.get("width", 1), 1)
    qh = _safe_float(canvas.get("height", 1), 1)

    qwen_texts = qwen_detection.get("text_elements", [])

    # Normalise all Qwen positions to 0..1
    normalized_qwen: list[dict] = []
    for t in qwen_texts:
        pos = t.get("position", {})
        npos = _normalize_qwen_position(pos, qw, qh)
        normalized_qwen.append({
            "index": len(normalized_qwen),
            "original": t,
            "norm_bbox": npos,
        })

    # Florence-2 bboxes are already 0..1
    florence_entries: list[dict] = []
    for ft in florence_texts:
        fb = ft.get("bbox", {})
        florence_entries.append({
            "text": ft.get("text", ""),
            "bbox": fb,
            "confidence": ft.get("confidence", 1.0),
        })

    # Greedy IoU matching (each Florence-2 entry matches at most one Qwen text)
    matched_florence: set[int] = set()
    merged_texts: list[dict] = []

    for qt in normalized_qwen:
        best_iou = 0.0
        best_fi = -1

        for fi, ft in enumerate(florence_entries):
            if fi in matched_florence:
                continue
            iou = _bbox_iou(qt["norm_bbox"], ft["bbox"])
            if iou > best_iou:
                best_iou = iou
                best_fi = fi

        if best_iou >= iou_threshold and best_fi >= 0:
            # Replace with Florence-2 data
            ft = florence_entries[best_fi]
            matched_florence.add(best_fi)

            new_pos = _denormalize_to_qwen_space(ft["bbox"], qw, qh)
            qt["original"]["position"] = new_pos
            qt["original"]["text"] = ft["text"]
            qt["original"]["confidence"] = ft["confidence"]
            qt["original"]["source"] = "florence-2"
            merged_texts.append(qt["original"])
        else:
            # Keep Qwen text as-is
            qt["original"]["source"] = "qwen"
            merged_texts.append(qt["original"])

    # Append unmatched Florence-2 texts (confidence >= 0.5)
    for fi, ft in enumerate(florence_entries):
        if fi not in matched_florence and ft["confidence"] >= 0.5:
            new_pos = _denormalize_to_qwen_space(ft["bbox"], qw, qh)
            merged_texts.append({
                "text": ft["text"],
                "position": new_pos,
                "source": "florence-2",
                "confidence": ft["confidence"],
                "color": "#000000",
            })

    # Sort by approximate vertical position (top→bottom, then left→right)
    merged_texts.sort(key=lambda t: (
        t.get("position", {}).get("y", 0),
        t.get("position", {}).get("x", 0),
    ))

    return merged_texts


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE V5
# ═══════════════════════════════════════════════════════════════════════════════


def process_image_v5(
    image_path: str,
    output_dir: str,
    model: str = "qwen/qwen3-vl-32b-instruct",
    inpaint_method: str = "openrouter",
    skip_detection: bool = False,
    skip_render: bool = False,
) -> dict:
    """Run the V5 dual-model pipeline for a single image.

    Parameters
    ----------
    image_path:
        Filesystem path to the source image.
    output_dir:
        Root output directory. A subdirectory ``{model_safe}/v5/{image_id}``
        will be created inside it.
    model:
        OpenRouter model identifier for Qwen detection.
    inpaint_method:
        Inpainting method: ``"openrouter"``, ``"lama"``, ``"opencv"``, or
        ``"none"``.
    skip_detection:
        If ``True``, reuse cached ``detection.json`` instead of calling Qwen
        or Florence-2 APIs.
    skip_render:
        If ``True``, skip ``.tc`` compilation and headless rendering.

    Returns
    -------
    dict
        Result dictionary with keys ``status``, ``image_id``, and optionally
        ``errors``.
    """
    image_id = os.path.splitext(os.path.basename(image_path))[0]
    model_safe = model.replace("/", "-").replace(".", "-")
    base_dir = os.path.join(output_dir, model_safe, "v5", image_id)
    os.makedirs(base_dir, exist_ok=True)

    paths = {
        "base": base_dir,
        "detection": os.path.join(base_dir, "detection.json"),
        "palette": os.path.join(base_dir, "palette.json"),
        "florence_cache": os.path.join(base_dir, "florence-cache.json"),
        "assembly": os.path.join(base_dir, "assembly.json"),
        "scene": os.path.join(base_dir, "scene.json"),
        "tc": os.path.join(base_dir, "design.tc"),
        "render": os.path.join(base_dir, "render.png"),
    }

    client = OpenRouterClient(model=model)
    florence_cache = FlorenceCache(paths["florence_cache"])
    result: dict = {"status": "success", "image_id": image_id, "errors": []}

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 1: Qwen3-VL — Structure Detection
    # ═══════════════════════════════════════════════════════════════════
    detection: Optional[dict] = None
    if not skip_detection and os.path.isfile(paths["detection"]):
        with open(paths["detection"], "r", encoding="utf-8") as f:
            detection = json.load(f)
        logger.info("  [Qwen] Cached detection loaded")

    if detection is None:
        logger.info("  [Qwen] Detecting layout structure...")
        try:
            raw = client.vision_analyze(
                image_path=image_path,
                prompt=QWEN_DETECTION_PROMPT,
                system_prompt=QWEN_DETECTION_SYSTEM,
                model=model,
            )
            detection = raw
            with open(paths["detection"], "w", encoding="utf-8") as f:
                json.dump(detection, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("  [Qwen] Failed: %s", e)
            return {"status": "failed", "errors": [f"Qwen detection: {e}"]}

    qwen_text_count = len(detection.get("text_elements", []))
    logger.info("  [Qwen] %d text(s), %d image(s), %d shape(s), canvas: %s",
                qwen_text_count,
                len(detection.get("images", [])),
                len(detection.get("shapes", [])),
                detection.get("canvas", {}))

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 2: Florence-2 — OCR + Dense Regions
    # ═══════════════════════════════════════════════════════════════════
    # Need real canvas dimensions from OpenCV for Florence-2 normalization.
    # We run OpenCV early so we can pass canvas_w/canvas_h to Florence-2.
    palette: Optional[dict] = None
    if os.path.isfile(paths["palette"]):
        with open(paths["palette"], "r", encoding="utf-8") as f:
            palette = json.load(f)
        logger.info("  [OpenCV] Cached palette")
    else:
        logger.info("  [OpenCV] Extracting palette...")
        palette = extract_palette(image_path)
        with open(paths["palette"], "w", encoding="utf-8") as f:
            json.dump(palette, f, indent=2, ensure_ascii=False)

    canvas_w = float(palette.get("width", 1080))
    canvas_h = float(palette.get("height", 1350))

    florence_data = _run_florence_tasks(
        image_path, canvas_w, canvas_h,
        florence_cache,
        allow_api_calls=(not skip_detection),
    )

    florence_texts = florence_data.get("ocr", [])
    florence_regions = florence_data.get("dense_regions", [])

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 3: Coordinate Merge
    # ═══════════════════════════════════════════════════════════════════
    if florence_texts:
        logger.info("  [Merge] Replacing Qwen texts with Florence-2 OCR...")
        merged_texts = merge_text_elements(detection, florence_texts)
        qwen_before = len(detection.get("text_elements", []))
        detection["text_elements"] = merged_texts
        detection["florence_ocr"] = florence_texts
        detection["florence_regions"] = florence_regions
        logger.info("    Qwen texts: %d → Merged texts: %d",
                    qwen_before, len(merged_texts))
    else:
        logger.info("  [Merge] No Florence-2 OCR data — keeping Qwen texts as-is")
        detection["florence_ocr"] = []
        detection["florence_regions"] = florence_regions

    # Re-save detection with merged text data
    with open(paths["detection"], "w", encoding="utf-8") as f:
        json.dump(detection, f, indent=2, ensure_ascii=False)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 4: Assembly (reuses assemble_v3 from pipeline_v3)
    # ═══════════════════════════════════════════════════════════════════
    logger.info("  Assembly...")
    assembly = assemble_v3(detection, palette)

    with open(paths["assembly"], "w", encoding="utf-8") as f:
        json.dump(assembly, f, indent=2, ensure_ascii=False)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 5: Crop + Inpaint (reuses pipeline_v4 logic)
    # ═══════════════════════════════════════════════════════════════════
    crops_dir = os.path.join(base_dir, "crops")
    has_images = any(l.get("kind") == "image" for l in assembly.get("layers", []))
    if has_images:
        logger.info("  Crop + Inpaint (%s)...", inpaint_method)
        assembly = _crop_and_inpaint(
            assembly, detection, image_path, crops_dir,
            canvas_w, canvas_h, inpaint_method,
        )

        inpainted = sum(1 for l in assembly["layers"] if l.get("inpainted"))
        if inpainted:
            logger.info("    Inpainted %d image(s)", inpainted)

        with open(paths["assembly"], "w", encoding="utf-8") as f:
            json.dump(assembly, f, indent=2, ensure_ascii=False)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 6: SceneGraph (reuses pipeline_v4's to_scenegraph)
    # ═══════════════════════════════════════════════════════════════════
    logger.info("  SceneGraph generation...")
    sg = to_scenegraph(assembly, canvas_w, canvas_h)
    with open(paths["scene"], "w", encoding="utf-8") as f:
        json.dump(sg, f, indent=2, ensure_ascii=False)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 7: Compile → .tc → Render (reuses pipeline_v4)
    # ═══════════════════════════════════════════════════════════════════
    if not skip_render:
        render_script = os.path.join(SCRIPT_DIR, "tc_render_standalone.js")
        logger.info("  Compiling to .tc...")
        tc_ok = compile_to_tc(sg, image_path, paths["tc"])
        if tc_ok and os.path.isfile(render_script):
            logger.info("  Rendering...")
            render_ok = render_tc(paths["tc"], paths["render"], render_script)
            if render_ok:
                logger.info("  Render: %s", paths["render"])
            else:
                logger.warning("  Render failed (may need Node/Playwright)")
        else:
            logger.warning("  Compile skipped or tc_render not found")

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    p = argparse.ArgumentParser(
        description="Smart Import V5 — Dual-Model Pipeline (Qwen3-VL + Florence-2)"
    )
    p.add_argument(
        "--image",
        type=str,
        default=None,
        metavar="PATH",
        help="Path to a single image to process",
    )
    p.add_argument(
        "--all",
        action="store_true",
        help="Process all images in a dataset directory",
    )
    p.add_argument(
        "--image-dir",
        "-d",
        default=None,
        help="Dataset directory (default: datasets/ in script dir)",
    )
    p.add_argument(
        "--model",
        default="qwen/qwen3-vl-32b-instruct",
        help="Qwen detection model (default: qwen/qwen3-vl-32b-instruct)",
    )
    p.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory (default: scripts/smart-import/output)",
    )
    p.add_argument(
        "--inpaint",
        default="openrouter",
        choices=["openrouter", "lama", "opencv", "none"],
        help="Inpainting method (default: openrouter)",
    )
    p.add_argument(
        "--skip-detection",
        action="store_true",
        help="Skip Qwen and Florence-2 API calls, use cached data",
    )
    p.add_argument(
        "--skip-render",
        action="store_true",
        help="Skip .tc compilation and rendering",
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return p


def main() -> None:
    """CLI entry point for pipeline_v5."""
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )

    # Resolve image list
    images: list[tuple[str, str]] = []

    if args.image:
        # Single image via --image
        if not os.path.isfile(args.image):
            logger.error("Image not found: %s", args.image)
            sys.exit(1)
        image_id = os.path.splitext(os.path.basename(args.image))[0]
        images = [(args.image, image_id)]
    elif args.all:
        # Full dataset
        dataset_dir = args.image_dir or os.path.join(SCRIPT_DIR, "datasets")
        if not os.path.isdir(dataset_dir):
            logger.error("Dataset directory not found: %s", dataset_dir)
            sys.exit(1)
        images = find_images(dataset_dir)
        if not images:
            logger.error("No images found in %s", dataset_dir)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    model = args.model
    logger.info(
        "V5 Pipeline | Model: %s | Inpaint: %s | Images: %d",
        model, args.inpaint, len(images),
    )

    results: list[dict] = []
    for img_path, img_id in images:
        logger.info("\n[v5] %s", img_id)
        t0 = time.monotonic()
        result = process_image_v5(
            image_path=img_path,
            output_dir=args.output,
            model=model,
            inpaint_method=args.inpaint,
            skip_detection=args.skip_detection,
            skip_render=args.skip_render,
        )
        elapsed = time.monotonic() - t0
        result["elapsed"] = round(elapsed, 1)
        results.append(result)

        icon = "OK" if result["status"] == "success" else "FAIL"
        logger.info("  [%s] %s  (%.1fs)", icon, result["status"], elapsed)

    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")
    logger.info(
        "\nDone: %d success, %d failed, %d skipped",
        success, failed, len(results) - success - failed,
    )
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
