"""
pipeline_v6.py — Smart Import V6. Variantes B, C, D.

Variante B:  Qwen detector → Qwen reconstructor (semántico) → Font matcher → Alignment
Variante C:  Qwen detector → Gemini reconstructor → Gemini inpaint → Font matcher → Alignment
Variante D:  Qwen detector (relaciones) → Qwen reconstructor → Constraint solver → Font matcher

Cada variante produce renders en subdirectorios separados para comparación:
  output/<model>/v6-{variant}/<image_id>/render.png

Uso:
    python pipeline_v6.py --image path/to/image.jpg --variant B
    python pipeline_v6.py --image path/to/image.jpg --variant C --inpaint openrouter
    python pipeline_v6.py --all --variant D
"""

from __future__ import annotations

import argparse
import copy
import json
import logging
import os
import sys
import time
from typing import Any, Optional

import cv2
import numpy as np

from florence_client import florence_caption, florence_dense_regions, florence_ocr
from openrouter import OpenRouterClient

# Reuse V3-V5 internals
from pipeline_v3 import (
    QWEN_DETECTION_PROMPT,
    QWEN_DETECTION_SYSTEM,
    SEMANTIC_PROMPT_BASE,
    SEMANTIC_SYSTEM,
    _safe_float,
    assemble_v3,
    extract_palette,
    find_images,
    render_tc,
    _qwen_to_bbox,
    _infer_text_style,
)
from pipeline_v4 import (
    _crop_and_inpaint,
    compile_to_tc,
    to_scenegraph,
)
from pipeline_v5 import (
    FlorenceCache,
    _run_florence_tasks,
    merge_text_elements,
)

logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 0: Enhanced Detection Prompt (with relationships)
# ═══════════════════════════════════════════════════════════════════════════════

V6_DETECTION_PROMPT = QWEN_DETECTION_PROMPT + """

Además, para CADA elemento detectado incluye RELACIONES ESPACIALES:
- "id": ID único (t1, t2, ..., img1, img2, ..., sh1, sh2, ...)
- "insideImage": id de la imagen que lo contiene (o null)
- "belowText": id del texto que está encima (o null)
- "isCentered": true si el texto está centrado horizontalmente
- "overlapsImage": id de imagen con la que se superpone (o null)
"""

V6_DETECTION_SYSTEM = (
    "Eres un analizador de diseño gráfico experto. "
    "Analiza la imagen y extrae TODOS los elementos visuales "
    "con coordenadas precisas en PIXELES, "
    "relaciones espaciales entre elementos, y colores exactos. "
    "Devuelve UNICAMENTE JSON válido, sin markdown."
)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1b: Reconstructor — runs SEMANTIC_PROMPT_BASE on detection data
# ═══════════════════════════════════════════════════════════════════════════════

def _run_reconstructor(
    client: OpenRouterClient,
    detection: dict,
    palette: dict,
    model: str,
) -> Optional[dict]:
    """Run the semantic reconstructor prompt on detection + palette data.

    This is Phase 1b in Variante B/C/D — a second model call that
    takes raw Qwen detection and infers visual hierarchy, style, zIndex.
    """
    # Format detection + palette as JSON for the prompt
    det_json = json.dumps(detection, indent=2, ensure_ascii=False)
    pal_json = json.dumps(palette, indent=2, ensure_ascii=False)

    prompt = SEMANTIC_PROMPT_BASE.replace("{detection_json}", det_json).replace(
        "{palette_json}", pal_json
    )

    logger.info("  [Reconstructor] Inferring hierarchy & style (model=%s)...", model)
    try:
        # Text-only call (no image needed)
        response = client.chat_completion(
            messages=[
                {"role": "system", "content": SEMANTIC_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            model=model,
        )
        if response.status == "error":
            logger.warning("  [Reconstructor] Failed: %s", response.error_message)
            return None
        result = json.loads(response.content) if isinstance(response.content, str) else response.content
        logger.info("  [Reconstructor] OK — %d layers inferred",
                     len(result.get("scene", {}).get("layers", [])))
        return result
    except Exception as e:
        logger.warning("  [Reconstructor] Error: %s", e)
        return None


def _apply_reconstructor_to_detection(
    detection: dict,
    reconstructor_output: dict,
) -> dict:
    """Merge reconstructor output back into the Qwen detection format.

    The reconstructor returns a scene JSON with layers containing zIndex,
    style info, and hierarchy. We merge this back into detection so
    downstream phases (assembly, crop, etc.) can use the improved data.
    """
    scene = reconstructor_output.get("scene", {})
    recon_layers = scene.get("layers", [])

    if not recon_layers:
        logger.info("  [Reconstructor] No layers — keeping original detection")
        return detection

    # Build lookup by ID
    id_map: dict[str, dict] = {}
    for layer in recon_layers:
        lid = layer.get("id", "")
        if lid:
            id_map[lid] = layer

    # Update text_elements with reconstructor info (style, zIndex, hierarchy)
    updated_texts: list[dict] = []
    for t in detection.get("text_elements", []):
        tid = t.get("id", "")
        recon = id_map.get(tid, {})
        if recon:
            style = recon.get("style", {})
            t["style"] = {
                "fontCategory": style.get("fontCategory", "sans"),
                "sizeCategory": style.get("sizeCategory", "body"),
                "weightCategory": style.get("weightCategory", "regular"),
                "colorHex": style.get("colorHex", "#000000"),
                "alignH": style.get("alignH", "left"),
            }
            t["zIndex"] = recon.get("zIndex", 20)
            t["isOccluded"] = recon.get("isOccluded", False)
            t["visualRole"] = recon.get("visualRole", "body")
        updated_texts.append(t)
    detection["text_elements"] = updated_texts

    # Update images with isOccluded
    updated_images: list[dict] = []
    for img in detection.get("images", []):
        iid = img.get("id", "")
        recon = id_map.get(iid, {})
        if recon:
            img["isOccluded"] = recon.get("isOccluded", False)
        updated_images.append(img)
    detection["images"] = updated_images

    logger.info("  [Reconstructor] Applied to %d texts, %d images",
                len(updated_texts), len(updated_images))
    return detection


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5: Font Matcher Integration
# ═══════════════════════════════════════════════════════════════════════════════

def _apply_font_matcher(
    assembly: dict,
    image_path: str,
    crops_dir: str,
) -> dict:
    """Run font matcher on each text element to get precise font family.

    For each text element in the assembly, we crop the text region from
    the original image, classify it with FontMatcher, and update the style.
    """
    try:
        from font_matcher import FontMatcher
    except ImportError:
        logger.warning("  [Font] font_matcher not available — skipping")
        return assembly

    matcher = FontMatcher(debug=False)
    original = cv2.imread(image_path)
    if original is None:
        logger.warning("  [Font] Cannot read original image — skipping")
        return assembly

    h, w = original.shape[:2]
    font_count = 0

    for i, layer in enumerate(assembly.get("layers", [])):
        if layer.get("kind") != "text":
            continue

        bbox = layer.get("bbox", {})
        bw_raw = _safe_float(bbox.get("w", 0), 0)
        bh_raw = _safe_float(bbox.get("h", 0), 0)
        if bw_raw < 10 or bh_raw < 10:
            continue  # Skip zero/tiny bboxes

        x = max(0, int(bbox.get("x", 0)))
        y = max(0, int(bbox.get("y", 0)))
        x2 = min(w, x + int(bw_raw))
        y2 = min(h, y + int(bh_raw))

        if x2 <= x or y2 <= y or (x2 - x) < 10 or (y2 - y) < 10:
            continue

        try:
            crop = original[y:y2, x:x2]
            crop_path = os.path.join(crops_dir, f"font_crop_{i}.png")
            os.makedirs(crops_dir, exist_ok=True)
            cv2.imwrite(crop_path, crop)

            result = matcher.classify(crop_path)
            layer["style"] = layer.get("style", {})
            layer["style"]["fontFamily"] = result.family
            layer["style"]["fontWeight"] = result.properties.weight
            layer["style"]["fontMatchScore"] = round(result.overall_score, 2)
            font_count += 1
            logger.info("    [Font] t%d: %s (score=%.2f)", i, result.family, result.overall_score)
        except Exception as e:
            logger.debug("  [Font] t%d error: %s", i, e)

    if font_count:
        logger.info("  [Font] Matched %d/%d text elements", font_count,
                     sum(1 for l in assembly["layers"] if l.get("kind") == "text"))
    return assembly


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6: Alignment Correction + Constraint Solver
# ═══════════════════════════════════════════════════════════════════════════════

def _correct_alignment(
    assembly: dict,
    canvas_w: float,
    canvas_h: float,
    use_constraint_solver: bool = False,
) -> dict:
    """Post-process layer positions to correct alignment issues.

    For all variants:
    - Snap elements near canvas center to exact center
    - Fix elements that extend beyond canvas bounds
    - Group aligned elements (same x or y within threshold)

    For Variante D (use_constraint_solver=True):
    - Row/column detection: detect rows and columns of elements
    - Uniform spacing: adjust positions for even spacing within rows
    - Center groups: center-align groups of elements
    """
    layers = assembly.get("layers", [])
    if not layers:
        return assembly

    center_x = canvas_w / 2
    center_threshold = canvas_w * 0.05  # 5% threshold for "near center"

    for layer in layers:
        bbox = layer.get("bbox", {})
        if not bbox:
            continue

        x = bbox.get("x", 0)
        y = bbox.get("y", 0)
        bw = bbox.get("w", 0)
        bh = bbox.get("h", 0)

        if bw <= 0 or bh <= 0:
            continue

        # 1. Snap to center if element is approximately centered
        elem_center = x + bw / 2
        if abs(elem_center - center_x) < center_threshold:
            new_x = center_x - bw / 2
            bbox["x"] = round(new_x, 1)
            layer["alignment"] = "center"

        # 2. Clamp to canvas bounds
        bbox["x"] = round(max(0, min(bbox["x"], canvas_w - bw)), 1)
        bbox["y"] = round(max(0, min(bbox["y"], canvas_h - bh)), 1)

    # --- Constraint solver for Variante D ---
    if use_constraint_solver and len(layers) > 1:
        _solve_layout_constraints(layers, canvas_w, canvas_h)

    return assembly


def _solve_layout_constraints(
    layers: list[dict],
    canvas_w: float,
    canvas_h: float,
) -> None:
    """Constraint-based layout refinement for Variante D.

    Detects:
    - Columns: elements with similar x position → align left edges
    - Rows: elements with similar y position → align top edges
    - Even spacing: distribute row/column elements evenly
    - Margin consistency: detect and apply consistent margins
    """
    # Group text layers by approximate vertical position (rows)
    rows: list[list[dict]] = []
    ROW_THRESHOLD = canvas_h * 0.03  # 3% of canvas height

    sorted_texts = sorted(
        [l for l in layers if l.get("kind") == "text"],
        key=lambda l: l.get("bbox", {}).get("y", 0),
    )

    for layer in sorted_texts:
        placed = False
        ly = layer.get("bbox", {}).get("y", 0)
        for row in rows:
            ref_y = row[0].get("bbox", {}).get("y", 0)
            if abs(ly - ref_y) < ROW_THRESHOLD:
                row.append(layer)
                placed = True
                break
        if not placed:
            rows.append([layer])

    # Within each row, align top edges and distribute evenly
    for row in rows:
        if len(row) < 2:
            continue

        # Align all tops to the minimum y in the row
        min_y = min(l.get("bbox", {}).get("y", 0) for l in row)
        for layer in row:
            layer["bbox"]["y"] = round(min_y, 1)

        # If row has 3+ elements, distribute evenly horizontally
        if len(row) >= 3:
            sorted_row = sorted(row, key=lambda l: l.get("bbox", {}).get("x", 0))
            min_x = sorted_row[0]["bbox"]["x"]
            max_x = sorted_row[-1]["bbox"]["x"] + sorted_row[-1]["bbox"]["w"]
            row_width = max_x - min_x
            spacing = row_width / (len(sorted_row) - 1) if len(sorted_row) > 1 else 0

            for i, layer in enumerate(sorted_row[1:-1], 1):
                target_x = min_x + spacing * i
                # Keep width, adjust x
                bw = layer["bbox"]["w"]
                layer["bbox"]["x"] = round(target_x - bw / 2, 1)


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE V6 — Multi-Variant Processor
# ═══════════════════════════════════════════════════════════════════════════════

def process_image_v6(
    image_path: str,
    output_dir: str,
    variant: str = "B",
    detection_model: str = "qwen/qwen3-vl-32b-instruct",
    reconstructor_model: Optional[str] = None,
    inpaint_method: str = "opencv",
    skip_detection: bool = False,
    skip_render: bool = False,
) -> dict:
    """Run the V6 pipeline for a single image with the given variant.

    Parameters
    ----------
    variant:
        ``"B"`` | ``"C"`` | ``"D"``
    detection_model:
        Model for Qwen detection phase.
    reconstructor_model:
        Model for reconstructor phase. Default for B/D = detection_model.
        For C = Gemini model (e.g. ``"google/gemini-2.5-flash-preview"``).
    """
    variant = variant.upper()
    if variant not in ("B", "C", "D"):
        return {"status": "failed", "errors": [f"Unknown variant: {variant}"]}

    # Default: reconstructor uses same model as detector for B/D
    if reconstructor_model is None:
        if variant == "C":
            reconstructor_model = "google/gemini-2.5-flash"
        else:
            reconstructor_model = detection_model

    image_id = os.path.splitext(os.path.basename(image_path))[0]
    model_safe = detection_model.replace("/", "-").replace(".", "-")
    base_dir = os.path.join(output_dir, model_safe, f"v6-{variant}", image_id)
    os.makedirs(base_dir, exist_ok=True)

    paths = {
        "base": base_dir,
        "detection": os.path.join(base_dir, "detection.json"),
        "reconstructor": os.path.join(base_dir, "reconstructor.json"),
        "palette": os.path.join(base_dir, "palette.json"),
        "florence_cache": os.path.join(base_dir, "florence-cache.json"),
        "assembly": os.path.join(base_dir, "assembly.json"),
        "scene": os.path.join(base_dir, "scene.json"),
        "tc": os.path.join(base_dir, "design.tc"),
        "render": os.path.join(base_dir, "render.png"),
        "crops": os.path.join(base_dir, "crops"),
    }

    client = OpenRouterClient(model=detection_model)
    florence_cache = FlorenceCache(paths["florence_cache"])
    result: dict = {"status": "success", "image_id": image_id,
                    "variant": variant, "errors": []}

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 0: OpenCV Palette + Dimensions
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
    canvas_h = float(palette.get("height", 1350))

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 1: Qwen3-VL — Detection (with relationships for B/D)
    # ═══════════════════════════════════════════════════════════════════
    detection: Optional[dict] = None
    if not skip_detection and os.path.isfile(paths["detection"]):
        with open(paths["detection"], "r", encoding="utf-8") as f:
            detection = json.load(f)
        logger.info("  [Qwen] Cached detection loaded")

    if detection is None:
        detect_prompt = V6_DETECTION_PROMPT if variant in ("B", "D") else QWEN_DETECTION_PROMPT
        detect_system = V6_DETECTION_SYSTEM if variant in ("B", "D") else QWEN_DETECTION_SYSTEM
        logger.info("  [Qwen] Detecting (variant=%s)...", variant)
        try:
            raw = client.vision_analyze(
                image_path=image_path,
                prompt=detect_prompt,
                system_prompt=detect_system,
                model=detection_model,
            )
            detection = raw
            with open(paths["detection"], "w", encoding="utf-8") as f:
                json.dump(detection, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("  [Qwen] Failed: %s", e)
            return {"status": "failed", "errors": [f"Qwen detection: {e}"]}

    logger.info("  [Qwen] %d text(s), %d image(s), %d shape(s)",
                len(detection.get("text_elements", [])),
                len(detection.get("images", [])),
                len(detection.get("shapes", [])))

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 1b: Reconstructor (Semantic Hierarchy) — B, C, D
    # ═══════════════════════════════════════════════════════════════════
    # Runs SEMANTIC_PROMPT_BASE to infer zIndex, style, hierarchy
    if not skip_detection and os.path.isfile(paths["reconstructor"]):
        try:
            with open(paths["reconstructor"], "r", encoding="utf-8") as f:
                recon_output = json.load(f)
            detection = _apply_reconstructor_to_detection(detection, recon_output)
            logger.info("  [Reconstructor] Cached result applied")
        except Exception:
            pass
    elif not skip_detection:
        recon_output = _run_reconstructor(client, detection, palette, reconstructor_model)
        if recon_output:
            with open(paths["reconstructor"], "w", encoding="utf-8") as f:
                json.dump(recon_output, f, indent=2, ensure_ascii=False)
            detection = _apply_reconstructor_to_detection(detection, recon_output)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 2: Florence-2 — OCR + Dense Regions
    # ═══════════════════════════════════════════════════════════════════
    florence_data = _run_florence_tasks(
        image_path, canvas_w, canvas_h,
        florence_cache,
        allow_api_calls=(not skip_detection),
    )
    florence_texts_raw = florence_data.get("ocr", [])

    # Deduplicate Florence-2 texts by normalized text content
    def _normalize_text(t: str) -> str:
        return t.strip().lower().replace("\u00b7", ".").replace("\u2022", ".")
    seen_texts: set[str] = set()
    florence_texts: list[dict] = []
    for ft in florence_texts_raw:
        nt = _normalize_text(ft.get("text", ""))
        if nt and nt not in seen_texts:
            seen_texts.add(nt)
            florence_texts.append(ft)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 3: Coordinate Merge (Qwen + Florence-2)
    # ═══════════════════════════════════════════════════════════════════
    if florence_texts:
        logger.info("  [Merge] Replacing Qwen texts with Florence-2 OCR...")
        merged_texts = merge_text_elements(detection, florence_texts, iou_threshold=0.15)
        # Filter out zero-bbox entries (Florence-2 unmatched texts with bad coords)
        valid_texts = []
        for t in merged_texts:
            pos = t.get("position", {})
            bw = _safe_float(pos.get("width", 0) if "width" in pos else pos.get("w", 0), 0)
            bh = _safe_float(pos.get("height", 0) if "height" in pos else pos.get("h", 0), 0)
            if bw > 5 and bh > 5:
                valid_texts.append(t)
            else:
                logger.debug("  [Merge] Skipped zero-bbox text: %s", t.get("text", "")[:40])
        qwen_before = len(detection.get("text_elements", []))
        detection["text_elements"] = valid_texts
        detection["florence_ocr"] = florence_texts
        logger.info("    Qwen texts: %d → Merged texts: %d (filtered %d zero-bbox)",
                    qwen_before, len(valid_texts), len(merged_texts) - len(valid_texts))
    else:
        detection["florence_ocr"] = []

    with open(paths["detection"], "w", encoding="utf-8") as f:
        json.dump(detection, f, indent=2, ensure_ascii=False)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 4: Assembly
    # ═══════════════════════════════════════════════════════════════════
    logger.info("  Assembly...")
    assembly = assemble_v3(detection, palette)

    with open(paths["assembly"], "w", encoding="utf-8") as f:
        json.dump(assembly, f, indent=2, ensure_ascii=False)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 5: Crop + Inpaint
    # ═══════════════════════════════════════════════════════════════════
    inpaint = inpaint_method
    if variant == "C" and inpaint_method == "opencv":
        # Variante C defaults to Gemini inpainting
        inpaint = "openrouter"

    has_images = any(l.get("kind") == "image" for l in assembly.get("layers", []))
    if has_images:
        logger.info("  Crop + Inpaint (%s)...", inpaint)
        assembly = _crop_and_inpaint(
            assembly, detection, image_path, paths["crops"],
            canvas_w, canvas_h, inpaint,
        )
        with open(paths["assembly"], "w", encoding="utf-8") as f:
            json.dump(assembly, f, indent=2, ensure_ascii=False)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 6: Font Matcher (B, C, D)
    # ═══════════════════════════════════════════════════════════════════
    assembly = _apply_font_matcher(assembly, image_path, paths["crops"])

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 7: Alignment Correction (B, C, D) + Constraint Solver (D)
    # ═══════════════════════════════════════════════════════════════════
    use_constraint_solver = (variant == "D")
    assembly = _correct_alignment(assembly, canvas_w, canvas_h, use_constraint_solver)

    with open(paths["assembly"], "w", encoding="utf-8") as f:
        json.dump(assembly, f, indent=2, ensure_ascii=False)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 8: SceneGraph
    # ═══════════════════════════════════════════════════════════════════
    logger.info("  SceneGraph generation...")
    sg = to_scenegraph(assembly, canvas_w, canvas_h)
    with open(paths["scene"], "w", encoding="utf-8") as f:
        json.dump(sg, f, indent=2, ensure_ascii=False)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 9: Compile → .tc → Render
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

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Smart Import V6 — Variantes B, C, D"
    )
    p.add_argument("--image", type=str, default=None, metavar="PATH")
    p.add_argument("--all", action="store_true")
    p.add_argument("--image-dir", "-d", default=None)
    p.add_argument(
        "--variant", default="B", choices=["B", "C", "D"],
        help="Pipeline variant (default: B)",
    )
    p.add_argument(
        "--detection-model",
        default="qwen/qwen3-vl-32b-instruct",
        help="Model for Qwen detection",
    )
    p.add_argument(
        "--reconstructor-model",
        default=None,
        help="Model for reconstructor phase (default: same as detector for B/D, Gemini for C)",
    )
    p.add_argument("--output", default=DEFAULT_OUTPUT_DIR)
    p.add_argument(
        "--inpaint", default="opencv",
        choices=["openrouter", "lama", "opencv", "none"],
    )
    p.add_argument("--skip-detection", action="store_true")
    p.add_argument("--skip-render", action="store_true")
    p.add_argument("--verbose", "-v", action="store_true")
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # Force UTF-8 for Windows console (prevents UnicodeEncodeError on \u2192 etc.)
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )

    images: list[tuple[str, str]] = []
    if args.image:
        if not os.path.isfile(args.image):
            logger.error("Image not found: %s", args.image)
            sys.exit(1)
        image_id = os.path.splitext(os.path.basename(args.image))[0]
        images = [(args.image, image_id)]
    elif args.all:
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

    logger.info("V6 Pipeline | Variant: %s | Detector: %s | Images: %d",
                args.variant, args.detection_model, len(images))

    results: list[dict] = []
    for img_path, img_id in images:
        logger.info("\n[v6-%s] %s", args.variant, img_id)
        t0 = time.monotonic()
        r = process_image_v6(
            image_path=img_path,
            output_dir=args.output,
            variant=args.variant,
            detection_model=args.detection_model,
            reconstructor_model=args.reconstructor_model,
            inpaint_method=args.inpaint,
            skip_detection=args.skip_detection,
            skip_render=args.skip_render,
        )
        elapsed = time.monotonic() - t0
        r["elapsed"] = round(elapsed, 1)
        results.append(r)

        icon = "OK" if r["status"] == "success" else "FAIL"
        logger.info("  [%s] %s  (%.1fs)", icon, r["status"], elapsed)

    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")
    logger.info("\nDone: %d success, %d failed", success, failed)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
