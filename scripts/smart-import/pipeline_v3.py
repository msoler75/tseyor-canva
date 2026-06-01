"""
pipeline_v3.py — Smart Import V3.

V3 usa un modelo de detección (Qwen3-VL) + OpenCV para datos duros,
y un LLM (Gemini Flash) solo para semántica.

Flujo:
  1. Qwen3-VL: detección de texto, regiones, formas (todo con bboxes)
  2. OpenCV: paleta dominante, análisis de color y contraste
  3. LLM semántico (Gemini Flash): jerarquía, estilo, resolución de ambigüedades
  4. Assembly → SceneGraph JSON
  5. Compilar a .tc (compiler existente)
  6. Render (tc_render_standalone.js existente)

Uso:
    python pipeline_v3.py --image-dir datasets --image poster-simple
    python pipeline_v3.py --image-dir datasets --model qwen/qwen3-vl-32b-instruct
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Optional

import numpy as np

from compiler import SmartImportCompiler
from image_utils import extract_region
from openrouter import OpenRouterClient

logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT ÚNICO PARA QWEN3-VL (detección + OCR + regiones)
# ═══════════════════════════════════════════════════════════════════════════════

QWEN_DETECTION_SYSTEM = (
    "Eres un analizador de diseño gráfico. Analiza la imagen y extrae "
    "todos los elementos visuales con sus coordenadas y propiedades. "
    "Devuelve UNICAMENTE JSON válido, sin markdown ni explicaciones."
)

QWEN_DETECTION_PROMPT = """Analiza esta imagen de diseño gráfico y extrae en JSON:
- canvas: dimensiones totales
- background: tipo de fondo y color
- text_elements: array con cada texto → text, position {x,y,width,height}, color, font_style
- images: array con cada foto/ilustración → position {x,y,width,height}, description
- shapes: array con cada forma/rectángulo → position {x,y,width,height}, color, opacity
- caption: descripción general de la imagen

Sé preciso con las coordenadas y los textos."""


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT PARA GEMINI (semántico, recibe datos de Qwen + OpenCV)
# ═══════════════════════════════════════════════════════════════════════════════

SEMANTIC_SYSTEM = (
    "Eres un experto en diseño gráfico. Recibes datos de detección de una imagen "
    "(textos con posiciones, imágenes, formas, paleta de colores).\n"
    "Tu único trabajo es inferir la JERARQUÍA VISUAL y ESTILO del diseño.\n"
    "NO modifiques las posiciones ni los textos.\n"
    "Devuelve UNICAMENTE JSON."
)

SEMANTIC_PROMPT_BASE = """Analiza estos datos extraídos de un diseño gráfico:

=== DETECCIÓN (textos, imágenes, formas) ===
{detection_json}

=== ANÁLISIS DE COLOR (OpenCV) ===
{palette_json}

Con base en esto:
1. Asigna zIndex a cada capa (fondo=0, formas=1-9, imágenes=10-19, textos=20+)
2. Identifica el texto principal (heading) y secundario
3. Detecta si hay texto superpuesto sobre imágenes (isOccluded)
4. Identifica la jerarquía visual general

Devuelve EXACTAMENTE este JSON:
{
  "scene": {
    "canvas": { "orientation", "aspectRatio" },
    "background": { "kind", "color", "gradient" },
    "layers": [
      {
        "id": "t1",
        "kind": "text|image|shape",
        "text": "solo para text",
        "bbox": {"x", "y", "w", "h"},
        "zIndex": 20,
        "style": {
          "fontCategory", "sizeCategory", "weightCategory",
          "colorHex", "alignH"
        },
        "description": "solo para image",
        "shapeType": "solo para shape",
        "fill": "solo para shape",
        "opacity": 1.0,
        "isOccluded": false,
        "confidence": 0.95
      }
    ]
  }
}
"""


# ═══════════════════════════════════════════════════════════════════════════════
# OPENCV ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def extract_palette(image_path: str, num_colors: int = 5) -> dict:
    """Extract dominant color palette from image using OpenCV k-means."""
    try:
        import cv2
        img = cv2.imread(image_path)
        if img is None:
            return {"palette": [], "dominant": "#cccccc", "avg_brightness": 0.5}

        h, w = img.shape[:2]
        pixels = img.reshape(-1, 3).astype(np.float32)

        # K-means clustering for dominant colors
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, centers = cv2.kmeans(
            pixels, num_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
        )

        # Count pixels per cluster
        counts = np.bincount(labels.flatten())
        total = counts.sum()

        palette = []
        for i in range(num_colors):
            bgr = centers[i].astype(int)
            rgb = (int(bgr[2]), int(bgr[1]), int(bgr[0]))
            hex_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            palette.append({
                "color": hex_color,
                "percentage": round(float(counts[i]) / total * 100, 1),
                "rgb": rgb,
            })

        # Sort by percentage descending
        palette.sort(key=lambda x: x["percentage"], reverse=True)
        dominant = palette[0]["color"] if palette else "#cccccc"

        # Average brightness (0-1)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        avg_brightness = float(gray.mean()) / 255.0

        return {
            "palette": palette,
            "dominant": dominant,
            "avg_brightness": round(avg_brightness, 3),
            "width": w,
            "height": h,
        }
    except Exception as e:
        logger.warning("OpenCV palette extraction failed: %s", e)
        return {"palette": [], "dominant": "#cccccc", "avg_brightness": 0.5, "width": 1080, "height": 1920}


def detect_shapes_opencv(image_path: str) -> list[dict]:
    """Detect basic geometric shapes using OpenCV contour detection."""
    shapes: list[dict] = []
    try:
        import cv2
        img = cv2.imread(image_path)
        if img is None:
            return shapes

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        # Dilate edges
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        h, w = img.shape[:2]

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 500:  # Skip tiny contours
                continue

            # Approximate polygon
            epsilon = 0.02 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            x, y, cw, ch = cv2.boundingRect(cnt)

            # Normalize
            shapes.append({
                "bbox": {
                    "x": round(x / w, 4),
                    "y": round(y / h, 4),
                    "w": round(cw / w, 4),
                    "h": round(ch / h, 4),
                },
                "num_vertices": len(approx),
                "area_pct": round(area / (w * h) * 100, 2),
            })
    except Exception as e:
        logger.warning("OpenCV shape detection failed: %s", e)

    return shapes


# ═══════════════════════════════════════════════════════════════════════════════
# ASSEMBLY
# ═══════════════════════════════════════════════════════════════════════════════

def _clamp_bbox(bbox: dict) -> dict:
    """Clamp negative values to 0."""
    return {
        "x": max(0, _safe_float(bbox.get("x", 0), 0)),
        "y": max(0, _safe_float(bbox.get("y", 0), 0)),
        "w": max(0, _safe_float(bbox.get("w", 0), 0)),
        "h": max(0, _safe_float(bbox.get("h", 0), 0)),
    }


def _is_pixel_coord(bbox: dict) -> bool:
    """Detect if bbox values are in pixels (>1.5) or normalized (0-1)."""
    vals = [_safe_float(bbox.get(k, 0), 0) for k in ("x", "y", "w", "h")]
    return any(v > 1.5 for v in vals)


def _qwen_to_bbox(item: dict) -> dict:
    """Convert Qwen's {position: {x, y, width, height}} to {bbox: {x, y, w, h}}."""
    pos = item.get("position", {})
    if not isinstance(pos, dict):
        return {"x": 0, "y": 0, "w": 0, "h": 0}
    return {
        "x": max(0, _safe_float(pos.get("x", 0), 0)),
        "y": max(0, _safe_float(pos.get("y", 0), 0)),
        "w": max(0, _safe_float(pos.get("width", 0), 0)),
        "h": max(0, _safe_float(pos.get("height", 0), 0)),
    }


def _infer_text_style(t: dict) -> dict:
    """Infer structured styles from Qwen's font_style string."""
    fs = t.get("font_style", "").lower()
    color = t.get("color", "#000000")

    # fontCategory — check sans-serif BEFORE serif
    if "sans" in fs or "sans-serif" in fs or "arial" in fs or "helvetica" in fs:
        font_cat = "sans"
    elif "serif" in fs or "georgia" in fs or "times" in fs:
        font_cat = "serif"
    elif "mono" in fs:
        font_cat = "monospace"
    elif any(k in fs for k in ("handwriting", "script", "cursive")):
        font_cat = "handwriting"
    elif any(k in fs for k in ("display", "impact", "uppercase")):
        font_cat = "display"
    else:
        font_cat = "sans"

    # weightCategory
    weight_cat = "bold" if "bold" in fs else ("light" if "light" in fs else "regular")

    # sizeCategory — infer from position/context
    size_cat = "body"

    # alignH — default left
    align_h = "center" if "center" in fs else ("right" if "right" in fs else "left")

    return {
        "fontCategory": font_cat,
        "sizeCategory": size_cat,
        "weightCategory": weight_cat,
        "colorHex": color,
        "alignH": align_h,
    }


def assemble_v3(qwen_output: dict, palette: dict) -> dict:
    """Assemble Qwen detection + OpenCV into SceneGraph assembly.

    Qwen naturally outputs:
      - canvas: {width, height}
      - text_elements: [{text, position: {x,y,width,height}, color, font_style, ...}]
      - images: [{position: {x,y,width,height}, description, ...}]
      - shapes: [{position: {x,y,width,height}, color, opacity, ...}]
    """
    layers: list[dict] = []
    z = 0

    # Background (z=0)
    bg = qwen_output.get("background", {})
    bg_kind = bg.get("kind", "solid")
    bg_color = bg.get("color") or palette.get("dominant", "#ffffff")

    # Caption for semantic context
    caption = qwen_output.get("caption", "")

    # Qwen's canvas estimate (used later for pixel scaling)
    qwen_canvas = qwen_output.get("canvas", {})

    # Shapes from Qwen's `shapes` array (z=1-9)
    for i, sh in enumerate(qwen_output.get("shapes", [])):
        z += 1
        layers.append({
            "id": sh.get("id", f"sh{i+1}"),
            "kind": "shape",
            "bbox": _qwen_to_bbox(sh),
            "shapeType": "rect",
            "fill": sh.get("color", "#cccccc"),
            "opacity": sh.get("opacity", 1.0),
            "borderRadius": 0.0,
            "zIndex": z,
            "confidence": sh.get("confidence", 0.5),
        })

    # Images from Qwen's `images` array (z=10-19)
    for i, img in enumerate(qwen_output.get("images", [])):
        z += 1
        layers.append({
            "id": img.get("id", f"img{i+1}"),
            "kind": "image",
            "bbox": _qwen_to_bbox(img),
            "description": img.get("description", ""),
            "cropFromSource": True,
            "zIndex": z + 10,
            "confidence": img.get("confidence", 0.5),
        })

    # Texts from Qwen's `text_elements` array (z=20+)
    for i, t in enumerate(qwen_output.get("text_elements", [])):
        z += 1
        layers.append({
            "id": t.get("id", f"t{i+1}"),
            "kind": "text",
            "bbox": _qwen_to_bbox(t),
            "text": t.get("text", ""),
            "style": _infer_text_style(t),
            "zIndex": z + 20,
            "confidence": t.get("confidence", 0.5),
        })

    layers.sort(key=lambda l: l["zIndex"])

    # Scale bboxes from Qwen canvas space to real pixel space
    # so downstream code (V4 crop/inpaint, compiling) uses consistent coordinates
    real_w = float(palette.get("width", 0))
    real_h = float(palette.get("height", 0))
    qw = float(qwen_canvas.get("width", real_w))
    qh = float(qwen_canvas.get("height", real_h))
    if real_w > 0 and real_h > 0 and qw > 0 and qh > 0 and (qw != real_w or qh != real_h):
        sx = real_w / qw
        sy = real_h / qh
        for layer in layers:
            bbox = layer.get("bbox", {})
            if bbox:
                bbox["x"] = round(bbox.get("x", 0) * sx, 1)
                bbox["y"] = round(bbox.get("y", 0) * sy, 1)
                bbox["w"] = round(bbox.get("w", 0) * sx, 1)
                bbox["h"] = round(bbox.get("h", 0) * sy, 1)

    return {
        "qwen_canvas": qwen_canvas,
        "coordsScaled": True,  # bboxes are now in real pixel space
        "caption": caption,
        "background": {
            "kind": bg_kind,
            "color": bg_color,
            "confidence": 1.0,
        },
        "layers": layers,
        "palette": palette.get("palette", []),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CONVERT TO SCENEGRAPH (with pixel coords for .tc)
# ═══════════════════════════════════════════════════════════════════════════════

def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


SIZE_TO_PX = {
    "hero": 72, "heading": 48, "subheading": 32,
    "body": 20, "caption": 14, "label": 11,
}
FONT_FAMILY = {
    "display": "Arial Black, Impact, sans-serif",
    "sans": "Arial, Helvetica, sans-serif",
    "serif": "Georgia, 'Times New Roman', serif",
    "handwriting": "'Comic Sans MS', 'Segoe Script', cursive",
    "monospace": "'Courier New', 'Consolas', monospace",
}
WEIGHT_MAP = {"bold": "bold", "regular": "normal", "light": "300"}


def to_scenegraph(assembly: dict, canvas_w: float, canvas_h: float) -> dict:
    """Convert assembly to SceneGraph JSON with pixel coords.

    Detects whether bbox values are pixels (from Qwen) or normalized 0..1,
    and converts everything to real pixel values for .tc compilation.
    """
    bg = assembly.get("background", {})

    # Get Qwen's canvas estimate for scaling pixels → real canvas
    qwen_c = assembly.get("qwen_canvas", {})
    qw = _safe_float(qwen_c.get("width", 0), 0)
    qh = _safe_float(qwen_c.get("height", 0), 0)

    # Determine orientation from aspect ratio
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

        # Detect coordinate system and convert to real pixels
        is_pixel = _is_pixel_coord(bbox)
        already_scaled = assembly.get("coordsScaled", False)
        bx = _safe_float(bbox.get("x", 0), 0)
        by = _safe_float(bbox.get("y", 0), 0)
        bw = _safe_float(bbox.get("w", 0), 0)
        bh = _safe_float(bbox.get("h", 0), 0)

        if is_pixel and not already_scaled:
            # Qwen outputs pixels — scale to real canvas if Qwen estimated different dimensions
            if qw > 0 and qh > 0:
                scale_x = canvas_w / qw
                scale_y = canvas_h / qh
                bx *= scale_x
                by *= scale_y
                bw *= scale_x
                bh *= scale_y
            # else: treat as already in real pixels (1:1)
        else:
            # Normalized 0..1 — convert to pixels using real canvas
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
            entry["cropFromSource"] = layer.get("cropFromSource", True)
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
# CROP IMAGES FROM SOURCE
# ═══════════════════════════════════════════════════════════════════════════════

def _crop_image_regions(assembly: dict, source_path: str, crops_dir: str) -> dict:
    """Crop each detected image region from the source and save to disk.

    Updates each image layer with:
      - cropPath: absolute path to the cropped PNG file
      - cropDataUri: base64 data URI for embedding

    Returns the updated assembly.
    """
    os.makedirs(crops_dir, exist_ok=True)
    updated_layers: list[dict] = []

    for layer in assembly.get("layers", []):
        if layer.get("kind") != "image":
            updated_layers.append(layer)
            continue

        bbox = layer.get("bbox", {})
        crop_path = os.path.join(crops_dir, f"{layer.get('id', 'img')}.png")

        out = extract_region(source_path, bbox, output_path=crop_path)
        if out:
            layer["cropPath"] = os.path.abspath(out)
            # Also compute data URI for embedding (needed by compiler)
            from image_utils import region_to_data_uri
            uri = region_to_data_uri(source_path, bbox)
            if uri:
                layer["cropDataUri"] = uri
            logger.info("    Cropped %s -> %s", layer["id"], os.path.basename(out))
        else:
            logger.warning("    Crop failed for %s (bbox: %s)", layer.get("id", "?"), bbox)

        updated_layers.append(layer)

    assembly["layers"] = updated_layers
    return assembly


# ═══════════════════════════════════════════════════════════════════════════════
# COMPILE → .tc → RENDER
# ═══════════════════════════════════════════════════════════════════════════════

def compile_to_tc(scene_json: dict, source_image: str, output_tc: str) -> bool:
    """Compile SceneGraph JSON to .tc using SmartImportCompiler directly."""
    try:
        compiler = SmartImportCompiler(mode="basic_image_layers")
        tc = compiler.compile(scene_json, source_image)
        compiler.export(tc, output_tc)
        return os.path.isfile(output_tc)
    except Exception as e:
        logger.warning("Compile failed: %s", e)
        return False


def render_tc(tc_path: str, output_png: str, render_script: str) -> bool:
    """Render .tc file to PNG using tc_render_standalone."""
    try:
        result = subprocess.run(
            ["node", render_script, "--tc", tc_path, "--output", output_png],
            capture_output=True, text=True, errors="backslashreplace", timeout=120,
        )
        if result.returncode != 0:
            logger.warning("Render stderr: %s", result.stderr[:300])
            return False
        return os.path.isfile(output_png)
    except Exception as e:
        logger.warning("Render failed: %s", e)
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def find_images(dataset_dir: str, filter_image: str | None = None) -> list[tuple[str, str]]:
    supported_exts = (".png", ".jpg", ".jpeg", ".webp")
    results: list[tuple[str, str]] = []

    for fname in sorted(os.listdir(dataset_dir)):
        fpath = os.path.join(dataset_dir, fname)
        if not os.path.isfile(fpath):
            continue
        stem, ext = os.path.splitext(fname)
        if ext.lower() in supported_exts and (filter_image is None or stem == filter_image):
            results.append((fpath, stem))

    if not results:
        for entry in sorted(os.listdir(dataset_dir)):
            entry_path = os.path.join(dataset_dir, entry)
            if not os.path.isdir(entry_path):
                continue
            for ext in supported_exts:
                img_path = os.path.join(entry_path, f"{entry}{ext}")
                if os.path.isfile(img_path) and (filter_image is None or entry == filter_image):
                    results.append((img_path, entry))
                    break

    return results


def run_v3(
    image_path: str,
    image_id: str,
    model: str,
    model_safe: str,
    output_dir: str,
    skip_detection: bool = False,
    skip_semantic: bool = False,
    skip_render: bool = False,
) -> dict:
    """Run V3 pipeline for a single image."""
    base_dir = os.path.join(output_dir, model_safe, "v3", image_id)
    os.makedirs(base_dir, exist_ok=True)

    paths = {
        "base": base_dir,
        "detection": os.path.join(base_dir, "detection.json"),
        "palette": os.path.join(base_dir, "palette.json"),
        "semantic": os.path.join(base_dir, "semantic.json"),
        "assembly": os.path.join(base_dir, "assembly.json"),
        "scene": os.path.join(base_dir, "scene.json"),
        "tc": os.path.join(base_dir, "design.tc"),
        "render": os.path.join(base_dir, "render.png"),
    }

    client = OpenRouterClient(model=model)
    result = {"status": "success", "image_id": image_id, "errors": []}

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 1: Qwen3-VL Detection (single comprehensive prompt)
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
    # PHASE 2: OpenCV Analysis (color palette + shapes)
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
    # PHASE 3.5: Crop image regions from source
    # ═══════════════════════════════════════════════════════════════════
    crops_dir = os.path.join(base_dir, "crops")
    has_images = any(l.get("kind") == "image" for l in assembly.get("layers", []))
    if has_images:
        logger.info("  Cropping image regions...")
        assembly = _crop_image_regions(assembly, image_path, crops_dir)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 4: Convert to SceneGraph
    # ═══════════════════════════════════════════════════════════════════
    logger.info("  SceneGraph generation...")
    sg = to_scenegraph(assembly, canvas_w, canvas_h)
    with open(paths["scene"], "w", encoding="utf-8") as f:
        json.dump(sg, f, indent=2, ensure_ascii=False)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 5: Compile → .tc → Render
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
    p = argparse.ArgumentParser(description="Smart Import V3 — Qwen3-VL detection + OpenCV")
    p.add_argument("--image-dir", "-d", required=True)
    p.add_argument("--model", default="qwen/qwen3-vl-32b-instruct",
                   help="Detection model (default: qwen/qwen3-vl-32b-instruct)")
    p.add_argument("--output", default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--image", default=None, metavar="ID", help="Specific image")
    p.add_argument("--skip-detection", action="store_true")
    p.add_argument("--skip-render", action="store_true")
    p.add_argument("--verbose", "-v", action="store_true")
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s", stream=sys.stdout,
    )

    model = args.model
    model_safe = model.replace("/", "-").replace(".", "-")

    images = find_images(args.image_dir, args.image)
    if not images:
        logger.error("No images found in %s", args.image_dir)
        sys.exit(1)

    logger.info("V3 Pipeline | Model: %s | Images: %d", model, len(images))

    results: list[dict] = []
    for img_path, img_id in images:
        logger.info("\n[v3] %s", img_id)
        t0 = time.monotonic()
        result = run_v3(
            image_path=img_path, image_id=img_id,
            model=model, model_safe=model_safe,
            output_dir=args.output,
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
    logger.info("\nDone: %d success, %d failed, %d skipped", success, failed, len(results) - success - failed)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
