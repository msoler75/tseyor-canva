"""
pipeline_v7.py — Smart Import V7 with TextAnalyzer color/effects refinement.

Self-contained pipeline (copies V6-D processing steps) that uses:
  1. Enhanced detection prompt (fontSize, fontWeight, colorHex, textEffects)
  2. OpenCV-based TextAnalyzer for REAL text color + effects extraction
  3. Constraint solver (from V6-D, the best variant)

Usage
-----
    python pipeline_v7.py --image dataset/poster-simple.jpg --variant A
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import time
from typing import Any, Optional

import cv2

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from openrouter import OpenRouterClient
from pipeline_v3 import (
    _safe_float,
    assemble_v3,
    extract_palette,
    _infer_text_style,
)
from pipeline_v4 import (
    _crop_and_inpaint,
    compile_to_tc,
    to_scenegraph,
    render_tc,
)
from pipeline_v5 import (
    FlorenceCache,
    _run_florence_tasks,
    merge_text_elements,
)
from pipeline_v6 import (
    _run_reconstructor,
    _apply_reconstructor_to_detection,
    _correct_alignment,
    _solve_layout_constraints,
    _apply_font_matcher,
)
from text_analyzer import TextAnalyzer

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# V7 PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════

V7_A_PROMPT = """Analiza esta imagen de diseño gráfico y extrae en JSON:

- canvas: dimensiones totales (ANCHO x ALTO en píxeles)
- background: tipo y color de fondo
- text_elements: array con CADA texto visible:
  - id: ID único (t1, t2, t3, ...)
  - text: contenido EXACTO del texto (sin modificar)
  - position: {x, y, width, height} en píxeles ABSOLUTOS
  - colorHex: color HEX exacto del texto (CRÍTICO: el color DEL TEXTO, no del fondo)
  - fontSize: tamaño de fuente estimado en píxeles (entero)
  - fontWeight: peso CSS ("bold", "regular", "light", o número)
  - fontFamily: nombre de la fuente si reconocible
  - font_style: descripción completa (bold, italic, uppercase, etc.)
  - textEffects: array de efectos visuales, ej: ["shadow", "outline", "blur"]
  - insideImage: id de la imagen que lo contiene (o null)
  - belowText: id del texto inmediatamente encima (o null)
  - isCentered: true si centrado horizontalmente
  - overlapsImage: id de imagen con la que se superpone (o null)
- images: array con fotos/ilustraciones (position, description)
- shapes: array con formas/rectángulos (position, color, opacity)
- caption: descripción general

CRÍTICO:
- colorHex debe ser EXACTAMENTE el color del texto (foreground), no el fondo
- Si tiene sombra (drop shadow), incluir "shadow" en textEffects
- Si tiene borde/outline, incluir "outline" en textEffects
- Coordenadas precisas en píxeles absolutos"""

V7_A_SYSTEM = (
    "Eres un analizador de diseño gráfico experto. "
    "Extrae TODOS los elementos visuales con coordenadas precisas en PÍXELES, "
    "colores HEX exactos del texto, y metadatos tipográficos completos. "
    "Devuelve UNICAMENTE JSON válido, sin markdown."
)

V7_B_PROMPT = V7_A_PROMPT + """

EJEMPLOS de colores correctos:
  - Texto BLANCO sobre fondo oscuro -> colorHex: "#FFFFFF"
  - Texto NEGRO sobre fondo claro -> colorHex: "#000000"
  - Texto azul marino sobre blanco -> colorHex: "#1A237E"
  - Texto con sombra -> colorHex es el color del texto, NO de la sombra"""

PROMPT_VARIANTS: dict[str, tuple[str, str]] = {
    "A": (V7_A_PROMPT, V7_A_SYSTEM),
    "B": (V7_B_PROMPT, V7_A_SYSTEM),
}


# ═══════════════════════════════════════════════════════════════════════════════
# CORE PIPELINE (self-contained, based on V6-D)
# ═══════════════════════════════════════════════════════════════════════════════

def process_image_v7(
    image_path: str,
    output_dir: str,
    prompt_variant: str = "A",
    detection_model: str = "qwen/qwen3-vl-32b-instruct",
    reconstructor_model: Optional[str] = None,
    inpaint_method: str = "opencv",
    skip_detection: bool = False,
    skip_render: bool = False,
    skip_text_analyzer: bool = False,
) -> dict:
    """Run V7 pipeline for a single image."""
    prompt_variant = prompt_variant.upper()
    if prompt_variant not in PROMPT_VARIANTS:
        return {"status": "failed", "errors": [f"Unknown prompt: {prompt_variant}"]}
    if reconstructor_model is None:
        reconstructor_model = detection_model

    image_id = os.path.splitext(os.path.basename(image_path))[0]
    model_safe = detection_model.replace("/", "-").replace(".", "-")
    base_dir = os.path.join(output_dir, model_safe, f"v7-{prompt_variant}", image_id)
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
        "text_analysis": os.path.join(base_dir, "text_analysis.json"),
    }

    client = OpenRouterClient(model=detection_model)
    florence_cache = FlorenceCache(paths["florence_cache"])
    result: dict = {"status": "success", "image_id": image_id,
                    "variant": f"V7-{prompt_variant}", "errors": []}

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 0: OpenCV Palette
    # ═══════════════════════════════════════════════════════════════════
    palette: Optional[dict] = None
    if os.path.isfile(paths["palette"]):
        with open(paths["palette"], encoding="utf-8") as f:
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
    # PHASE 1: V7 Detection + TextAnalyzer
    # ═══════════════════════════════════════════════════════════════════
    detection: Optional[dict] = None

    # If skip_detection is True AND no V7 cache exists, fall back to V6-D source
    v6_source_dir = os.path.join(output_dir, model_safe, "v6-D", image_id)
    v6_source_path = os.path.join(v6_source_dir, "detection.json")

    if skip_detection:
        if os.path.isfile(paths["detection"]):
            with open(paths["detection"], encoding="utf-8") as f:
                detection = json.load(f)
            logger.info("  [Qwen] V7 cached detection loaded (skip_detection)")
        elif os.path.isfile(v6_source_path):
            shutil.copy2(v6_source_path, paths["detection"])
            with open(paths["detection"], encoding="utf-8") as f:
                detection = json.load(f)
            logger.info("  [Qwen] V6-D detection loaded as fallback (skip_detection)")
        else:
            logger.error("  [Qwen] No detection source found (skip_detection)")
            return {"status": "failed", "errors": ["No detection source available"]}
    elif os.path.isfile(paths["detection"]):
        with open(paths["detection"], encoding="utf-8") as f:
            detection = json.load(f)
        logger.info("  [Qwen] Cached detection loaded")

        # Also load cached TextAnalyzer results
        if os.path.isfile(paths["text_analysis"]):
            with open(paths["text_analysis"], encoding="utf-8") as f:
                ta_cache = json.load(f)
            for el in detection.get("text_elements", []):
                cached = ta_cache.get(el.get("id", ""), {})
                if cached.get("colorHex"):
                    el["color"] = cached["colorHex"]
                    el["colorHex"] = cached["colorHex"]
                for k in ("cvColorHex", "cvFontWeight", "cvFontSizePx",
                          "cvIsItalic", "cvIsUnderlined", "textEffects"):
                    if k in cached:
                        el[k] = cached[k]
            logger.info("  [TextAnalyzer] Cached results applied")

    if detection is None:
        detect_prompt, detect_system = PROMPT_VARIANTS[prompt_variant]
        logger.info("  [Qwen] V7 detection (variant=%s)...", prompt_variant)
        try:
            detection = client.vision_analyze(
                image_path=image_path,
                prompt=detect_prompt,
                system_prompt=detect_system,
                model=detection_model,
            )
            with open(paths["detection"], "w", encoding="utf-8") as f:
                json.dump(detection, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("  [Qwen] Failed: %s", e)
            return {"status": "failed", "errors": [f"Qwen: {e}"]}

    logger.info("  [Qwen] %d text(s), %d image(s), %d shape(s)",
                len(detection.get("text_elements", [])),
                len(detection.get("images", [])),
                len(detection.get("shapes", [])))

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 2: Florence-2 OCR + merge (from V6-D)
    # ═══════════════════════════════════════════════════════════════════
    florence_data = _run_florence_tasks(
        image_path, canvas_w, canvas_h,
        florence_cache,
        allow_api_calls=True,
    )
    florence_texts_raw = florence_data.get("ocr", [])

    # Dedup Florence-2 texts
    def _norm_text(t: str) -> str:
        return t.strip().lower().replace("\u00b7", ".").replace("\u2022", ".")
    seen: set[str] = set()
    florence_texts: list[dict] = []
    for ft in florence_texts_raw:
        nt = _norm_text(ft.get("text", ""))
        if nt and nt not in seen:
            seen.add(nt)
            florence_texts.append(ft)

    if florence_texts:
        logger.info("  [Merge] Florence-2 -> Qwen (iou=0.15)...")
        merged = merge_text_elements(detection, florence_texts, iou_threshold=0.15)
        valid = []
        for t in merged:
            pos = t.get("position", {})
            bw = _safe_float(pos.get("width", 0), 0) if "width" in pos else _safe_float(pos.get("w", 0), 0)
            bh = _safe_float(pos.get("height", 0), 0) if "height" in pos else _safe_float(pos.get("h", 0), 0)
            if bw > 5 and bh > 5:
                valid.append(t)
        detection["text_elements"] = valid
        detection["florence_ocr"] = florence_texts
    else:
        detection["florence_ocr"] = []

    with open(paths["detection"], "w", encoding="utf-8") as f:
        json.dump(detection, f, indent=2, ensure_ascii=False)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 3: Reconstructor
    # ═══════════════════════════════════════════════════════════════════
    recon_path = paths["reconstructor"]
    if os.path.isfile(recon_path):
        try:
            with open(recon_path, encoding="utf-8") as f:
                detection = _apply_reconstructor_to_detection(detection, json.load(f))
            logger.info("  [Reconstructor] Cached")
        except Exception:
            pass
    elif skip_detection:
        # Fall back to V6-D's cached reconstructor
        v6_recon_path = os.path.join(v6_source_dir, "reconstructor.json")
        if os.path.isfile(v6_recon_path):
            shutil.copy2(v6_recon_path, recon_path)
            with open(recon_path, encoding="utf-8") as f:
                detection = _apply_reconstructor_to_detection(detection, json.load(f))
            logger.info("  [Reconstructor] V6-D fallback")
    else:
        recon = _run_reconstructor(client, detection, palette, reconstructor_model)
        if recon:
            with open(recon_path, "w", encoding="utf-8") as f:
                json.dump(recon, f, indent=2, ensure_ascii=False)
            detection = _apply_reconstructor_to_detection(detection, recon)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 4: TextAnalyzer (after reconstructor — uses corrected bboxes)
    # ═══════════════════════════════════════════════════════════════════
    if not skip_text_analyzer and not os.path.isfile(paths["text_analysis"]):
        te_list = detection.get("text_elements", [])
        logger.info("  [TextAnalyzer] Analyzing %d text elements (post-reconstructor)...", len(te_list))
        image = cv2.imread(image_path)
        if image is not None:
            analyzer = TextAnalyzer()
            ta_cache = {}
            refined_color = 0
            for el in te_list:
                bbox = el.get("position", {})
                if not bbox:
                    continue
                ta = analyzer.analyze_text_region(image, bbox)
                if not ta or "error" in ta:
                    continue
                el_id = el.get("id", "")
                cv_color = ta.get("colorHex")
                ta_cache[el_id] = {
                    "colorHex": cv_color,
                    "cvColorHex": cv_color,
                    "cvFontWeight": ta.get("fontWeight", "regular"),
                    "cvFontSizePx": ta.get("fontSizePx", 12),
                    "cvIsItalic": ta.get("isItalic", False),
                    "cvIsUnderlined": ta.get("isUnderlined", False),
                    "cvConfidence": round(ta.get("confidence", 0.0), 3),
                    "textEffects": [e["type"] for e in ta.get("effects", [])],
                }
                if cv_color:
                    el["color"] = cv_color
                    el["colorHex"] = cv_color
                    refined_color += 1
                el["cvColorHex"] = cv_color
                el["cvFontWeight"] = ta.get("fontWeight", "regular")
                el["cvFontSizePx"] = ta.get("fontSizePx", 12)
                el["cvIsItalic"] = ta.get("isItalic", False)
                el["cvIsUnderlined"] = ta.get("isUnderlined", False)
                el["cvTextEffects"] = ta.get("effects", [])
                el["textEffects"] = [e["type"] for e in ta.get("effects", [])]

            with open(paths["text_analysis"], "w", encoding="utf-8") as f:
                json.dump(ta_cache, f, indent=2, ensure_ascii=False)
            logger.info("  [TextAnalyzer] Refined %d/%d text colors",
                        refined_color, len(te_list))

            # Re-save detection with refined properties
            with open(paths["detection"], "w", encoding="utf-8") as f:
                json.dump(detection, f, indent=2, ensure_ascii=False)
    elif os.path.isfile(paths["text_analysis"]):
        logger.info("  [TextAnalyzer] Cached results loaded")

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 5: Assembly (assemble_v3)
    # ═══════════════════════════════════════════════════════════════════
    logger.info("  Assembly...")
    assembly = assemble_v3(detection, palette)
    with open(paths["assembly"], "w", encoding="utf-8") as f:
        json.dump(assembly, f, indent=2, ensure_ascii=False)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 5: Crop + Inpaint
    # ═══════════════════════════════════════════════════════════════════
    has_images = any(l.get("kind") == "image" for l in assembly.get("layers", []))
    if has_images:
        logger.info("  Crop + Inpaint (%s)...", inpaint_method)
        assembly = _crop_and_inpaint(
            assembly, detection, image_path, paths["crops"],
            canvas_w, canvas_h, inpaint_method,
        )
        with open(paths["assembly"], "w", encoding="utf-8") as f:
            json.dump(assembly, f, indent=2, ensure_ascii=False)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 6: Font Matcher + Constraint Solver
    # ═══════════════════════════════════════════════════════════════════
    assembly = _apply_font_matcher(assembly, image_path, paths["crops"])
    assembly = _correct_alignment(assembly, canvas_w, canvas_h, use_constraint_solver=True)

    with open(paths["assembly"], "w", encoding="utf-8") as f:
        json.dump(assembly, f, indent=2, ensure_ascii=False)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 7: SceneGraph + Render
    # ═══════════════════════════════════════════════════════════════════
    logger.info("  SceneGraph generation...")
    sg = to_scenegraph(assembly, canvas_w=canvas_w, canvas_h=canvas_h)
    with open(paths["scene"], "w", encoding="utf-8") as f:
        json.dump(sg, f, indent=2, ensure_ascii=False)

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
                logger.warning("  Render failed (Node/Playwright?)")
        else:
            logger.warning("  Compile skipped or tc_render not found")

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)

    p = argparse.ArgumentParser(description="Smart Import V7 Pipeline")
    p.add_argument("--image", required=True)
    p.add_argument("--output", default=os.path.join(SCRIPT_DIR, "output"))
    p.add_argument("--variant", default="A", choices=["A", "B"])
    p.add_argument("--model", default="qwen/qwen3-vl-32b-instruct")
    p.add_argument("--reconstructor-model", default=None)
    p.add_argument("--inpaint", default="opencv", choices=["openrouter", "lama", "opencv", "none"])
    p.add_argument("--skip-detection", action="store_true")
    p.add_argument("--skip-render", action="store_true")
    p.add_argument("--skip-text-analyzer", action="store_true")
    args = p.parse_args()

    t0 = time.monotonic()
    r = process_image_v7(
        image_path=args.image, output_dir=args.output,
        prompt_variant=args.variant, detection_model=args.model,
        reconstructor_model=args.reconstructor_model,
        inpaint_method=args.inpaint,
        skip_detection=args.skip_detection, skip_render=args.skip_render,
        skip_text_analyzer=args.skip_text_analyzer,
    )
    elapsed = time.monotonic() - t0
    if r.get("status") == "success":
        logger.info("[v7-%s] %s  [OK] success  (%.1fs)", args.variant, r.get("image_id","?"), elapsed)
    else:
        logger.error("[v7-%s] %s  [FAIL] %s", args.variant, r.get("image_id","?"), r.get("errors",[]))
