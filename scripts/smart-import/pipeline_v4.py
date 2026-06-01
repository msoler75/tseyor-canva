"""
pipeline_v4.py — Smart Import V4.

V4 añade **inpainting de texto** sobre imágenes al pipeline V3.
Cuando un texto detectado por Qwen se superpone a una imagen,
se crea una máscara y se rellena la zona con fondo natural.

3 métodos de inpainting (por orden de calidad):
  1. OpenRouter (Gemini 3.1 Flash Image) — mejor calidad, ~$0.01/imagen
  2. LaMa (lama-cleaner) — buena calidad local, CPU/GPU
  3. OpenCV TELEA — rápido, sin dependencias, calidad básica (fallback)

Flujo V4:
  1. Qwen3-VL: detección unificada (textos, imágenes, formas)
  2. OpenCV: paleta dominante + dimensiones reales
  3. Assembly: fusiona detección + paleta
  4. Crop + Inpaint: recorta regiones de imagen, remueve texto superpuesto
  5. SceneGraph: coordenadas escaladas a canvas real
  6. Compile: .tc con imágenes limpias embebidas
  7. Render: headless PNG

Uso:
    python pipeline_v4.py --image-dir datasets --image poster-simple
    python pipeline_v4.py --image-dir datasets --inpaint opencv  (sin API)
    python pipeline_v4.py --image-dir datasets --inpaint openrouter --inpaint-all
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from typing import Any, Optional

from compiler import SmartImportCompiler
from image_utils import extract_region, region_to_data_uri
from inpainter import inpaint_region
from openrouter import OpenRouterClient

# Reuse V3 functions
from pipeline_v3 import (
    QWEN_DETECTION_PROMPT,
    QWEN_DETECTION_SYSTEM,
    _infer_text_style,
    _is_pixel_coord,
    _qwen_to_bbox,
    _safe_float,
    assemble_v3,
    extract_palette,
    find_images,
    render_tc,
    SIZE_TO_PX,
    FONT_FAMILY,
    WEIGHT_MAP,
)

logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")


# ═══════════════════════════════════════════════════════════════════════════════
# OVERLAP DETECTION
# ═══════════════════════════════════════════════════════════════════════════════


def _find_text_overlaps(
    detection: dict, qwen_canvas: dict, real_w: float, real_h: float
) -> dict[str, list[dict]]:
    """Find which text elements overlap with which image regions.

    Returns mapping: image_layer_id -> [list of overlapping text bboxes in Qwen coords]
    """
    sx = real_w / qwen_canvas.get("width", real_w)
    sy = real_h / qwen_canvas.get("height", real_h)
    overlaps: dict[str, list[dict]] = {}

    images = detection.get("images", [])
    texts = detection.get("text_elements", [])

    for img_idx, img in enumerate(images):
        img_id = img.get("id", f"img{img_idx + 1}")
        ip = img.get("position", {})
        ix = ip.get("x", 0)
        iy = ip.get("y", 0)
        iw = ip.get("width", 0)
        ih = ip.get("height", 0)

        overlapping_texts = []
        for t in texts:
            tp = t.get("position", {})
            tx = tp.get("x", 0)
            ty = tp.get("y", 0)
            tw = tp.get("width", 0)
            th = tp.get("height", 0)

            # AABB overlap test in Qwen's coordinate space
            if not (tx + tw < ix or tx > ix + iw or ty + th < iy or ty > iy + ih):
                overlapping_texts.append({
                    "x": tx,
                    "y": ty,
                    "w": tw,
                    "h": th,
                    "text": t.get("text", ""),
                })

        if overlapping_texts:
            overlaps[img_id] = overlapping_texts
            texts_on = ", ".join(t["text"] for t in overlapping_texts)
            logger.info("    [Overlap] %s <- %s", img_id, texts_on)

    return overlaps


# ═══════════════════════════════════════════════════════════════════════════════
# CROP + INPAINT
# ═══════════════════════════════════════════════════════════════════════════════


def _crop_and_inpaint(
    assembly: dict,
    detection: dict,
    source_path: str,
    crops_dir: str,
    real_w: float,
    real_h: float,
    inpaint_method: str = "openrouter",
) -> dict:
    """Crop image regions, inpaint overlapping text, save results.

    Updates each image layer with:
      - cropPath: path to cropped (and optionally inpainted) PNG
      - cropDataUri: base64 data URI for .tc embedding
      - inpainted: bool (True if inpainting was applied)
      - inpaintMethod: method used

    Returns updated assembly.
    """
    qwen_c = assembly.get("qwen_canvas", {})
    qw = qwen_c.get("width", real_w)
    qh = qwen_c.get("height", real_h)
    sx = real_w / qw
    sy = real_h / qh

    # Find overlaps
    overlaps = _find_text_overlaps(detection, qwen_c, real_w, real_h)

    os.makedirs(crops_dir, exist_ok=True)
    updated_layers: list[dict] = []

    for layer in assembly.get("layers", []):
        if layer.get("kind") != "image":
            updated_layers.append(layer)
            continue

        bbox = layer.get("bbox", {})
        layer_id = layer.get("id", "img")
        crop_path = os.path.join(crops_dir, f"{layer_id}.png")

        # First, crop from source
        out = extract_region(source_path, bbox, output_path=crop_path)
        if not out:
            logger.warning("    Crop failed for %s", layer_id)
            updated_layers.append(layer)
            continue

        layer["cropPath"] = os.path.abspath(out)
        layer["inpainted"] = False

        # Check if this image has overlapping text
        text_bboxes = overlaps.get(layer_id, [])
        if text_bboxes and inpaint_method != "none":
            logger.info("    Inpainting %s (%d texts)...", layer_id, len(text_bboxes))
            clean_path = os.path.join(crops_dir, f"{layer_id}_clean.png")

            # Find matching detection image by index (avoids coordinate-space mismatch)
            detection_images = detection.get("images", [])
            all_img_layers = [l for l in assembly.get("layers", []) if l.get("kind") == "image"]
            img_idx = -1
            for idx, lyr in enumerate(all_img_layers):
                if lyr.get("id") == layer_id:
                    img_idx = idx
                    break
            if 0 <= img_idx < len(detection_images):
                img_pos = detection_images[img_idx].get("position", {})
            else:
                img_pos = {"x": bbox.get("x", 0), "y": bbox.get("y", 0),
                           "width": bbox.get("w", 0), "height": bbox.get("h", 0)}

            offset_x = int(img_pos.get("x", 0) * sx)
            offset_y = int(img_pos.get("y", 0) * sy)

            result_path = inpaint_region(
                source_path=source_path,
                image_bbox=bbox,  # already in real pixels
                text_bboxes=text_bboxes,  # Qwen coords (will be scaled inside)
                method=inpaint_method,
                canvas_scale=(sx, sy),
                canvas_offset=(offset_x, offset_y),
                output_path=clean_path,
            )

            if result_path:
                layer["cropPath"] = os.path.abspath(result_path)
                layer["inpainted"] = True
                layer["inpaintMethod"] = inpaint_method
                # Compute data URI from inpainted image
                uri = region_to_data_uri(result_path, {
                    "x": 0, "y": 0, "w": 99999, "h": 99999
                })
                if uri:
                    layer["cropDataUri"] = uri

        # If not inpainted, compute data URI from original crop
        if not layer.get("cropDataUri"):
            uri = region_to_data_uri(source_path, bbox)
            if uri:
                layer["cropDataUri"] = uri

        updated_layers.append(layer)

    assembly["layers"] = updated_layers
    return assembly


# ═══════════════════════════════════════════════════════════════════════════════
# SCENEGRAPH (same as V3)
# ═══════════════════════════════════════════════════════════════════════════════


def to_scenegraph(assembly: dict, canvas_w: float, canvas_h: float) -> dict:
    """Convert assembly to SceneGraph JSON with pixel coords."""
    bg = assembly.get("background", {})
    qwen_c = assembly.get("qwen_canvas", {})
    qw = _safe_float(qwen_c.get("width", 0), 0)
    qh = _safe_float(qwen_c.get("height", 0), 0)

    orientation = "square"
    if canvas_w > canvas_h * 1.1:
        orientation = "horizontal"
    elif canvas_h > canvas_w * 1.1:
        orientation = "vertical"

    sg = {
        "canvas": {
            "width": round(canvas_w),
            "height": round(canvas_h),
            "detectedFormat": orientation,
        },
        "background": {
            "kind": bg.get("kind", "solid"),
            "color": bg.get("color", "#ffffff"),
            "confidence": 1.0,
        },
        "layers": [],
    }

    for layer in assembly.get("layers", []):
        bbox = layer.get("bbox", {})
        kind = layer.get("kind", "shape")

        is_pixel = _is_pixel_coord(bbox)
        bx = _safe_float(bbox.get("x", 0), 0)
        by = _safe_float(bbox.get("y", 0), 0)
        bw = _safe_float(bbox.get("w", 0), 0)
        bh = _safe_float(bbox.get("h", 0), 0)

        if is_pixel:
            if qw > 0 and qh > 0:
                scale_x = canvas_w / qw
                scale_y = canvas_h / qh
                bx *= scale_x
                by *= scale_y
                bw *= scale_x
                bh *= scale_y
        else:
            bx = bx * canvas_w
            by = by * canvas_h
            bw = bw * canvas_w
            bh = bh * canvas_h

        entry: dict[str, Any] = {
            "id": layer.get("id", f"l{len(sg['layers'])+1}"),
            "kind": kind,
            "bbox": {
                "x": round(max(0, bx), 1),
                "y": round(max(0, by), 1),
                "w": round(min(canvas_w, max(0, bw)), 1),
                "h": round(min(canvas_h, max(0, bh)), 1),
            },
            "zIndex": layer.get("zIndex", 1),
            "confidence": layer.get("confidence", 0.5),
        }

        if kind == "text":
            style = layer.get("style", {})
            sc = style.get("sizeCategory", "body")
            entry["text"] = layer.get("text", "")
            entry["style"] = {
                "fontSize": SIZE_TO_PX.get(sc, 20),
                "fontWeight": WEIGHT_MAP.get(style.get("weightCategory", "regular"), "normal"),
                "color": style.get("colorHex", "#000000"),
                "textAlign": style.get("alignH", "left"),
                "fontFamily": FONT_FAMILY.get(style.get("fontCategory", "sans"), "Arial"),
            }
        elif kind == "image":
            entry["description"] = layer.get("description", "")
            entry["cropFromSource"] = True
            entry["inpainted"] = layer.get("inpainted", False)
        elif kind == "shape":
            entry["shapeType"] = layer.get("shapeType", "rect")
            entry["fill"] = layer.get("fill", "#cccccc")
            entry["opacity"] = layer.get("opacity", 1.0)
            entry["borderRadius"] = round(
                _safe_float(layer.get("borderRadius", 0), 0) * canvas_w, 1
            )

        sg["layers"].append(entry)

    return sg


# ═══════════════════════════════════════════════════════════════════════════════
# COMPILE → .tc → RENDER
# ═══════════════════════════════════════════════════════════════════════════════


def compile_to_tc(scene_json: dict, source_image: str, output_tc: str) -> bool:
    """Compile SceneGraph to .tc using SmartImportCompiler."""
    try:
        compiler = SmartImportCompiler(mode="basic_image_layers")
        tc = compiler.compile(scene_json, source_image)
        compiler.export(tc, output_tc)
        return os.path.isfile(output_tc)
    except Exception as e:
        logger.warning("Compile failed: %s", e)
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════


def run_v4(
    image_path: str,
    image_id: str,
    model: str,
    model_safe: str,
    output_dir: str,
    inpaint_method: str = "openrouter",
    skip_detection: bool = False,
    skip_render: bool = False,
) -> dict:
    """Run V4 pipeline for a single image."""
    base_dir = os.path.join(output_dir, model_safe, "v4", image_id)
    os.makedirs(base_dir, exist_ok=True)

    paths = {
        "base": base_dir,
        "detection": os.path.join(base_dir, "detection.json"),
        "palette": os.path.join(base_dir, "palette.json"),
        "assembly": os.path.join(base_dir, "assembly.json"),
        "scene": os.path.join(base_dir, "scene.json"),
        "tc": os.path.join(base_dir, "design.tc"),
        "render": os.path.join(base_dir, "render.png"),
    }

    client = OpenRouterClient(model=model)
    result = {"status": "success", "image_id": image_id, "errors": []}

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 1: Qwen3-VL Detection
    # ═══════════════════════════════════════════════════════════════════
    detection: Optional[dict] = None
    if not skip_detection and os.path.isfile(paths["detection"]):
        with open(paths["detection"], "r", encoding="utf-8") as f:
            detection = json.load(f)
        logger.info("  [Detect] Cached")

    if detection is None:
        logger.info("  [Detect] Qwen3-VL analysing...")
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
            logger.error("  [Detect] Failed: %s", e)
            return {"status": "failed", "errors": [f"Detection: {e}"]}

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 2: OpenCV Analysis
    # ═══════════════════════════════════════════════════════════════════
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
    canvas_h = float(palette.get("height", 1920))

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 3: Assembly
    # ═══════════════════════════════════════════════════════════════════
    logger.info("  Assembly...")
    assembly = assemble_v3(detection, palette)

    with open(paths["assembly"], "w", encoding="utf-8") as f:
        json.dump(assembly, f, indent=2, ensure_ascii=False)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 4: Crop + Inpaint (V4 new)
    # ═══════════════════════════════════════════════════════════════════
    crops_dir = os.path.join(base_dir, "crops")
    has_images = any(l.get("kind") == "image" for l in assembly.get("layers", []))
    if has_images:
        logger.info("  Crop + Inpaint (%s)...", inpaint_method)
        assembly = _crop_and_inpaint(
            assembly, detection, image_path, crops_dir,
            canvas_w, canvas_h, inpaint_method,
        )

        # Report inpainting stats
        inpainted = sum(1 for l in assembly["layers"] if l.get("inpainted"))
        if inpainted:
            logger.info("    Inpainted %d image(s)", inpainted)

        # Re-save assembly with inpainting metadata
        with open(paths["assembly"], "w", encoding="utf-8") as f:
            json.dump(assembly, f, indent=2, ensure_ascii=False)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 5: SceneGraph
    # ═══════════════════════════════════════════════════════════════════
    logger.info("  SceneGraph generation...")
    sg = to_scenegraph(assembly, canvas_w, canvas_h)
    with open(paths["scene"], "w", encoding="utf-8") as f:
        json.dump(sg, f, indent=2, ensure_ascii=False)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 6: Compile → .tc → Render
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
    p = argparse.ArgumentParser(
        description="Smart Import V4 — Qwen3-VL detection + Inpainting"
    )
    p.add_argument("--image-dir", "-d", required=True)
    p.add_argument(
        "--model",
        default="qwen/qwen3-vl-32b-instruct",
        help="Detection model (default: qwen/qwen3-vl-32b-instruct)",
    )
    p.add_argument("--output", default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--image", default=None, metavar="ID", help="Specific image")
    p.add_argument(
        "--inpaint",
        default="openrouter",
        choices=["openrouter", "lama", "opencv", "none"],
        help="Inpainting method (default: openrouter)",
    )
    p.add_argument("--skip-detection", action="store_true")
    p.add_argument("--skip-render", action="store_true")
    p.add_argument("--verbose", "-v", action="store_true")
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )

    model = args.model
    model_safe = model.replace("/", "-").replace(".", "-")

    images = find_images(args.image_dir, args.image)
    if not images:
        logger.error("No images found in %s", args.image_dir)
        sys.exit(1)

    logger.info(
        "V4 Pipeline | Model: %s | Inpaint: %s | Images: %d",
        model, args.inpaint, len(images),
    )

    results: list[dict] = []
    for img_path, img_id in images:
        logger.info("\n[v4] %s", img_id)
        t0 = time.monotonic()
        result = run_v4(
            image_path=img_path,
            image_id=img_id,
            model=model,
            model_safe=model_safe,
            output_dir=args.output,
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
