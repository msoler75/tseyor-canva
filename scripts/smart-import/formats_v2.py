"""
formats_v2.py — V2 Smart Import con 3 prompts secuenciales y coordenadas 0..1.

Cada formato (SceneGraph, SVG, HTML) comparte los mismos 3 prompts de extracción
y luego genera su representación específica desde la estructura unificada.

Flujo:
  1. Prompt 1 — Composición espacial (regiones, canvas, fondo)
  2. Prompt 2 — Extracción de texto (apoyado en regiones del P1)
  3. Prompt 3 — Imágenes, formas y efectos (apoyado en P1 + P2)
  4. Assembly — Fusiona P1 + P2 + P3 en estructura unificada
  5. Generación — Convierte estructura unificada a formato destino
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import subprocess
import tempfile
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES COMPARTIDAS
# ═══════════════════════════════════════════════════════════════════════════════

SIZE_CATEGORY_TO_PX: dict[str, float] = {
    "hero": 72.0,
    "heading": 48.0,
    "subheading": 32.0,
    "body": 20.0,
    "caption": 14.0,
    "label": 11.0,
}

FONT_CATEGORY_TO_FAMILY: dict[str, str] = {
    "display": "Arial Black, Impact, sans-serif",
    "sans": "Arial, Helvetica, sans-serif",
    "serif": "Georgia, 'Times New Roman', serif",
    "handwriting": "'Comic Sans MS', 'Segoe Script', cursive",
    "monospace": "'Courier New', 'Consolas', monospace",
}

WEIGHT_CATEGORY_TO_VALUE: dict[str, str] = {
    "bold": "bold",
    "regular": "normal",
    "light": "300",
}

ALIGN_TO_SVG: dict[str, str] = {
    "left": "start",
    "center": "middle",
    "right": "end",
}

LETTER_SPACING_TO_EM: dict[str, float] = {
    "tight": -0.025,
    "normal": 0.0,
    "wide": 0.05,
}

# ═══════════════════════════════════════════════════════════════════════════════
# SISTEMA DE COORDENADAS (inyectado en todos los prompts)
# ═══════════════════════════════════════════════════════════════════════════════

COORD_SYSTEM_INSTRUCTIONS = (
    "SISTEMA DE COORDENADAS (OBLIGATORIO):\n"
    "- El origen (0,0) está en la esquina superior izquierda del canvas.\n"
    "- x e y son la posición del borde superior izquierdo del elemento.\n"
    "- w y h son el ancho y alto del elemento.\n"
    "- TODOS los valores están NORMALIZADOS entre 0.0 y 1.0 "
    "(donde 1.0 = ancho/alto total del canvas).\n"
    "- NUNCA uses píxeles absolutos.\n"
    "- NUNCA devuelvas valores fuera del rango 0.0–1.0.\n"
    "- bbox.x + bbox.w NUNCA debe superar 1.0.\n"
    "- bbox.y + bbox.h NUNCA debe superar 1.0."
)

# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS DE EJEMPLO (usamos Python dicts para evitar escapes de llaves)
# ═══════════════════════════════════════════════════════════════════════════════

SCHEMA_COMPOSITION_EXAMPLE = {
    "canvas": {
        "orientation": "vertical|horizontal|square",
        "aspectRatio": "estimado, ej: 4:5",
        "dominantPalette": ["#hex1", "#hex2", "#hex3"],
    },
    "background": {
        "kind": "solid|gradient|image|pattern",
        "color": "hex o null si gradiente",
        "gradient": {"from": "#hex", "to": "#hex", "angle": 0},
    },
    "regions": [
        {
            "id": "r1",
            "kind": "text_zone|image_zone|shape_zone|mixed_zone",
            "bbox": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 0.25},
            "visualWeight": "high|medium|low",
            "zIndex": 1,
        }
    ],
}

SCHEMA_TEXT_EXAMPLE = {
    "textLayers": [
        {
            "id": "t1",
            "regionRef": "r1",
            "bbox": {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0},
            "text": "texto exacto",
            "textUncertain": False,
            "style": {
                "fontCategory": "display|sans|serif|handwriting|monospace",
                "sizeCategory": "hero|heading|subheading|body|caption|label",
                "weightCategory": "bold|regular|light",
                "colorHex": "#ffffff",
                "alignH": "left|center|right",
                "isItalic": False,
                "hasStroke": False,
                "hasShadow": False,
                "letterSpacingCategory": "tight|normal|wide",
            },
            "zIndex": 10,
            "confidence": 0.95,
        }
    ],
}

SCHEMA_SHAPES_EXAMPLE = {
    "imageLayers": [
        {
            "id": "img1",
            "regionRef": "r2",
            "bbox": {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0},
            "description": "descripción breve",
            "isOccluded": False,
            "occludedBy": ["t1"],
            "cropFromSource": True,
            "confidence": 0.88,
        },
    ],
    "shapeLayers": [
        {
            "id": "sh1",
            "regionRef": "r1",
            "bbox": {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0},
            "shapeType": "rect|circle|line|pill|triangle",
            "fill": "#hex",
            "opacity": 1.0,
            "borderRadius": 0.0,
            "border": {"color": "#hex", "width": 0.005},
            "zIndex": 5,
            "confidence": 0.82,
        },
    ],
}

# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT 1 — COMPOSICIÓN ESPACIAL
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT_1: str = (
    "Eres un analizador de composición espacial especializado en diseño gráfico. "
    "Tu única tarea es identificar las REGIONES visuales principales de una imagen: "
    "zonas donde hay concentración de elementos, separaciones claras, "
    "bloques de color o foto diferenciados.\n\n"
    "NO extraigas texto ni describas imágenes todavía. Solo estructura espacial.\n\n"
    + COORD_SYSTEM_INSTRUCTIONS + "\n\n"
    "Devuelve ÚNICAMENTE JSON válido, sin explicaciones ni markdown fences."
)

ANALYSIS_PROMPT_1 = (
    "Analiza la composición espacial de esta imagen de diseño gráfico.\n"
    "Identifica el canvas, el fondo, y las REGIONES visuales principales.\n"
    "NO extraigas texto ni describas contenido de imágenes.\n\n"
    "Devuelve EXACTAMENTE este schema JSON:\n\n"
    + json.dumps(SCHEMA_COMPOSITION_EXAMPLE, indent=2)
)

# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT 2 — EXTRACCIÓN DE TEXTO
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT_2: str = (
    "Eres un extractor de texto especializado en diseño gráfico. "
    "Recibes una imagen y el análisis de composición previo (regiones). "
    "Tu única tarea es extraer TODOS los bloques de texto visibles con su "
    "contenido exacto y estilo tipográfico.\n\n"
    + COORD_SYSTEM_INSTRUCTIONS + "\n\n"
    "Usa el análisis de regiones como referencia, pero ajusta el bbox "
    "al área real que ocupa cada texto, no al de la región completa.\n"
    "Si no puedes leer el texto con certeza, marca textUncertain: true.\n\n"
    "Devuelve ÚNICAMENTE JSON válido, sin explicaciones ni markdown fences."
)

_SCHEMA_TEXT_JSON = json.dumps(SCHEMA_TEXT_EXAMPLE, indent=2)


def build_prompt_2(composition_json: str) -> str:
    """Build Phase 2 prompt with composition context injected."""
    return (
        "Extrae todos los bloques de texto de esta imagen de diseño gráfico.\n\n"
        "Análisis de composición previo:\n<composicion>\n"
        f"{composition_json}\n"
        "</composicion>\n\n"
        "Devuelve EXACTAMENTE este schema JSON:\n\n"
        f"{_SCHEMA_TEXT_JSON}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT 3 — IMÁGENES, FORMAS Y EFECTOS
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT_3: str = (
    "Eres un analizador de elementos visuales no textuales en diseño gráfico. "
    "Recibes una imagen, el análisis de composición y los textos extraídos. "
    "Tu tarea es identificar fotografías, ilustraciones, formas geométricas, "
    "overlays, iconos y texturas.\n\n"
    + COORD_SYSTEM_INSTRUCTIONS + "\n\n"
    "NO repitas textos ya detectados en el análisis previo.\n"
    "Para imágenes: describe brevemente el contenido.\n"
    "Para formas: identifica el tipo geométrico y colores.\n"
    "Para overlays/gradientes sobre imagen: descríbelos como shape con opacidad.\n\n"
    "Devuelve ÚNICAMENTE JSON válido, sin explicaciones ni markdown fences."
)

_SCHEMA_SHAPES_JSON = json.dumps(SCHEMA_SHAPES_EXAMPLE, indent=2)


def build_prompt_3(composition_json: str, text_json: str) -> str:
    """Build Phase 3 prompt with composition + text context injected."""
    return (
        "Identifica los elementos NO textuales de esta imagen de diseño gráfico.\n\n"
        "Análisis de composición previo:\n<composicion>\n"
        f"{composition_json}\n"
        "</composicion>\n\n"
        "Textos ya extraídos:\n<textos>\n"
        f"{text_json}\n"
        "</textos>\n\n"
        "Devuelve EXACTAMENTE este schema JSON:\n\n"
        f"{_SCHEMA_SHAPES_JSON}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ASSEMBLY — Fusiona los 3 outputs en estructura unificada
# ═══════════════════════════════════════════════════════════════════════════════

def _safe_float(val: Any, default: float = 0.0) -> float:
    """Convert value to float safely."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_str(val: Any, default: str = "") -> str:
    if val is None:
        return default
    return str(val)


def assemble(p1: dict, p2: dict, p3: dict) -> dict:
    """Merge the 3 prompt outputs into a unified scene structure.

    Args:
        p1: Composition analysis (canvas, background, regions)
        p2: Text extraction (textLayers)
        p3: Images and shapes (imageLayers, shapeLayers)

    Returns:
        Unified scene dict with: canvas, background, layers[]
    """
    canvas = p1.get("canvas", {})
    background = p1.get("background", {})

    layers: list[dict] = []

    # Option B: Deterministic zIndex reconstruction
    # Order: background -> shapes -> images -> text

    # Shapes: zIndex 1-9
    for i, sh in enumerate(p3.get("shapeLayers", [])):
        layers.append({
            "id": sh.get("id", f"sh{i+1}"),
            "kind": "shape",
            "bbox": clamp_bbox(sh.get("bbox", {"x": 0, "y": 0, "w": 1, "h": 1})),
            "shapeType": sh.get("shapeType", "rect"),
            "fill": sh.get("fill", "#cccccc"),
            "opacity": _safe_float(sh.get("opacity"), 1.0),
            "borderRadius": _safe_float(sh.get("borderRadius"), 0.0),
            "border": sh.get("border"),
            "zIndex": i + 1,
            "confidence": _safe_float(sh.get("confidence"), 0.5),
            "regionRef": sh.get("regionRef"),
        })

    # Images: zIndex 10-19
    for i, img in enumerate(p3.get("imageLayers", [])):
        layers.append({
            "id": img.get("id", f"img{i+1}"),
            "kind": "image",
            "bbox": clamp_bbox(img.get("bbox", {"x": 0, "y": 0, "w": 1, "h": 1})),
            "description": img.get("description", ""),
            "isOccluded": img.get("isOccluded", False),
            "occludedBy": img.get("occludedBy", []),
            "cropFromSource": img.get("cropFromSource", True),
            "zIndex": i + 10,
            "confidence": _safe_float(img.get("confidence"), 0.5),
            "regionRef": img.get("regionRef"),
        })

    # Text: zIndex 20+
    for i, t in enumerate(p2.get("textLayers", [])):
        style = t.get("style", {})
        layers.append({
            "id": t.get("id", f"t{i+1}"),
            "kind": "text",
            "bbox": clamp_bbox(t.get("bbox", {"x": 0, "y": 0, "w": 1, "h": 1})),
            "text": t.get("text", ""),
            "textUncertain": t.get("textUncertain", False),
            "style": {
                "fontCategory": style.get("fontCategory", "sans"),
                "sizeCategory": style.get("sizeCategory", "body"),
                "weightCategory": style.get("weightCategory", "regular"),
                "colorHex": style.get("colorHex", "#000000"),
                "alignH": style.get("alignH", "left"),
                "isItalic": style.get("isItalic", False),
                "hasStroke": style.get("hasStroke", False),
                "hasShadow": style.get("hasShadow", False),
                "letterSpacingCategory": style.get("letterSpacingCategory", "normal"),
            },
            "zIndex": i + 20,
            "confidence": _safe_float(t.get("confidence"), 0.5),
            "regionRef": t.get("regionRef"),
        })

    # Sort by zIndex
    layers.sort(key=lambda l: l["zIndex"])

    return {
        "canvas": canvas,
        "background": background,
        "layers": layers,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# GENERADORES — Convierten estructura unificada a formato destino
# ═══════════════════════════════════════════════════════════════════════════════


def _bbox_to_px(
    bbox: dict,
    canvas_w: float,
    canvas_h: float,
    padding: float = 0.01,
) -> dict:
    """Convert normalized bbox to pixels with safety padding."""
    return {
        "x": max(0, (bbox.get("x", 0) - padding) * canvas_w),
        "y": max(0, (bbox.get("y", 0) - padding) * canvas_h),
        "w": min(canvas_w, (bbox.get("w", 0) + padding * 2) * canvas_w),
        "h": min(canvas_h, (bbox.get("h", 0) + padding * 2) * canvas_h),
    }


def _size_to_px(size_category: str) -> float:
    """Convert sizeCategory to approximate px value."""
    return SIZE_CATEGORY_TO_PX.get(size_category, 20.0)


def _bg_to_css(background: dict) -> str:
    """Convert background dict to CSS background property."""
    kind = background.get("kind", "solid")
    if kind == "gradient":
        grad = background.get("gradient") or {}
        angle = _safe_float(grad.get("angle", 0), 0)
        frm = grad.get("from", "#000000")
        to = grad.get("to", "#ffffff")
        return f"linear-gradient({angle}deg, {frm}, {to})"
    elif kind == "image":
        return "#e0e0e0"  # placeholder
    else:
        return background.get("color", "#ffffff")


# ── SceneGraph generator ──────────────────────────────────────────────────────

def generate_scenegraph(assembly: dict) -> dict:
    """Convert assembled structure to SceneGraph JSON with per-pixel coordinates.

    The .tc compiler expects pixel values, so we convert normalized coords
    to pixels here based on canvas dimensions.
    """
    canvas = assembly.get("canvas", {})
    canvas_w = _safe_float(canvas.get("width", 1080))
    canvas_h = _safe_float(canvas.get("height", 1920))

    # If canvas has aspectRatio but not width/height, estimate from orientation
    if not canvas.get("width") or not canvas.get("height"):
        orientation = canvas.get("orientation", "vertical")
        if orientation == "horizontal":
            canvas_w, canvas_h = 1920, 1080
        elif orientation == "square":
            canvas_w, canvas_h = 1080, 1080
        else:
            canvas_w, canvas_h = 1080, 1920

    bg = assembly.get("background", {})
    bg_color = bg.get("color", "#ffffff")

    sg_layers: list[dict] = []
    for layer in assembly.get("layers", []):
        bbox_px = _bbox_to_px(layer.get("bbox", {}), canvas_w, canvas_h, padding=0.0)
        kind = layer.get("kind", "shape")

        entry: dict = {
            "id": layer.get("id", f"l{len(sg_layers)+1}"),
            "kind": kind,
            "bbox": {
                "x": round(bbox_px["x"], 1),
                "y": round(bbox_px["y"], 1),
                "w": round(bbox_px["w"], 1),
                "h": round(bbox_px["h"], 1),
            },
            "zIndex": layer.get("zIndex", 1),
            "confidence": layer.get("confidence", 0.5),
        }

        if kind == "text":
            style = layer.get("style", {})
            entry["text"] = layer.get("text", "")
            entry["textUncertain"] = layer.get("textUncertain", False)
            entry["style"] = {
                "fontSize": _size_to_px(style.get("sizeCategory", "body")),
                "fontWeight": WEIGHT_CATEGORY_TO_VALUE.get(
                    style.get("weightCategory", "regular"), "normal"
                ),
                "color": style.get("colorHex", "#000000"),
                "textAlign": style.get("alignH", "left"),
                "fontFamily": FONT_CATEGORY_TO_FAMILY.get(
                    style.get("fontCategory", "sans"), "Arial"
                ),
                "isItalic": style.get("isItalic", False),
                "letterSpacing": LETTER_SPACING_TO_EM.get(
                    style.get("letterSpacingCategory", "normal"), 0.0
                ),
            }

        elif kind == "image":
            entry["description"] = layer.get("description", "")
            entry["cropFromSource"] = layer.get("cropFromSource", True)

        elif kind == "shape":
            entry["shapeType"] = layer.get("shapeType", "rect")
            entry["fill"] = layer.get("fill", "#cccccc")
            entry["opacity"] = layer.get("opacity", 1.0)
            br = _safe_float(layer.get("borderRadius", 0), 0)
            entry["borderRadius"] = round(br * canvas_w, 1)

        sg_layers.append(entry)

    return {
        "canvas": {
            "width": round(canvas_w),
            "height": round(canvas_h),
            "detectedFormat": canvas.get("orientation", "vertical"),
        },
        "background": {
            "kind": bg.get("kind", "solid"),
            "color": bg_color,
            "confidence": 1.0,
        },
        "layers": sg_layers,
    }


# ── SVG generator ─────────────────────────────────────────────────────────────

def generate_svg(assembly: dict, canvas_w: float, canvas_h: float) -> str:
    """Convert assembled structure to SVG code.

    Args:
        assembly: Unified scene structure from assemble()
        canvas_w: Canvas width in pixels
        canvas_h: Canvas height in pixels

    Returns:
        Complete SVG string
    """
    bg = assembly.get("background", {})
    bg_kind = bg.get("kind", "solid")

    lines: list[str] = [
        f'<svg width="{int(canvas_w)}" height="{int(canvas_h)}" '
        f'viewBox="0 0 {int(canvas_w)} {int(canvas_h)}" '
        'xmlns="http://www.w3.org/2000/svg">',
        "  <defs>",
    ]

    # Background gradient defs
    grad_id = None
    if bg_kind == "gradient":
        grad = bg.get("gradient") or {}
        grad_id = "bg-grad"
        angle = _safe_float(grad.get("angle", 0), 0)
        frm = grad.get("from", "#000000")
        to = grad.get("to", "#ffffff")
        # SVG gradient angle is measured differently: SVG uses objectBoundingBox
        # where 0 = top-to-bottom, 90 = left-to-right
        svg_angle = angle - 90  # convert CSS angle to SVG
        rad = math.radians(svg_angle)
        x1 = 0.5 - 0.5 * math.cos(rad)
        y1 = 0.5 - 0.5 * math.sin(rad)
        x2 = 0.5 + 0.5 * math.cos(rad)
        y2 = 0.5 + 0.5 * math.sin(rad)
        lines.append(
            f'    <linearGradient id="{grad_id}" '
            f'x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}">'
        )
        lines.append(f'      <stop offset="0%" stop-color="{frm}"/>')
        lines.append(f'      <stop offset="100%" stop-color="{to}"/>')
        lines.append("    </linearGradient>")

    lines.append("  </defs>")

    # Background
    if grad_id:
        lines.append(f'  <rect x="0" y="0" width="{int(canvas_w)}" height="{int(canvas_h)}" fill="url(#{grad_id})"/>')
    else:
        bg_color = bg.get("color", "#ffffff")
        lines.append(f'  <rect x="0" y="0" width="{int(canvas_w)}" height="{int(canvas_h)}" fill="{bg_color}"/>')

    # Layers
    for layer in assembly.get("layers", []):
        bbox_px = _bbox_to_px(layer.get("bbox", {}), canvas_w, canvas_h)
        kind = layer.get("kind", "shape")
        x = round(bbox_px["x"], 1)
        y = round(bbox_px["y"], 1)
        w = round(bbox_px["w"], 1)
        h = round(bbox_px["h"], 1)

        if kind == "text":
            style = layer.get("style", {})
            font_size = _size_to_px(style.get("sizeCategory", "body"))
            font_family = FONT_CATEGORY_TO_FAMILY.get(
                style.get("fontCategory", "sans"), "Arial"
            )
            fill = style.get("colorHex", "#000000")
            align = ALIGN_TO_SVG.get(style.get("alignH", "left"), "start")
            weight = WEIGHT_CATEGORY_TO_VALUE.get(
                style.get("weightCategory", "regular"), "normal"
            )
            font_style = "italic" if style.get("isItalic") else "normal"
            letter_spacing = LETTER_SPACING_TO_EM.get(
                style.get("letterSpacingCategory", "normal"), 0.0
            )

            text = layer.get("text", "")
            # Escape XML entities
            text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            # SVG <text> uses y for baseline, we use top of bbox
            text_y = y + font_size * 0.85  # approximate baseline offset

            # Calculate text x position based on alignment
            text_x = x
            if align == "middle":
                text_x = x + w / 2
            elif align == "end":
                text_x = x + w

            lines.append(f'  <text x="{text_x}" y="{round(text_y, 1)}" '
                         f'font-family="{font_family}" '
                         f'font-size="{font_size}" '
                         f'font-weight="{weight}" '
                         f'font-style="{font_style}" '
                         f'fill="{fill}" '
                         f'text-anchor="{align}" '
                         f'letter-spacing="{letter_spacing}em">'
                         f'{text}</text>')

        elif kind == "image":
            fill = "#e0e0e0"  # placeholder
            lines.append(f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" '
                         f'fill="{fill}" rx="4"/>')
            # Description as subtle label
            desc = layer.get("description", "")
            if desc:
                lines.append(f'  <text x="{x + 8}" y="{y + h / 2}" '
                             f'font-size="14" fill="#666" '
                             f'font-family="Arial, sans-serif">'
                             f'{desc[:50]}</text>')

        elif kind == "shape":
            shape_type = layer.get("shapeType", "rect")
            fill = layer.get("fill", "#cccccc")
            opacity = _safe_float(layer.get("opacity"), 1.0)
            br = _safe_float(layer.get("borderRadius"), 0) * canvas_w
            border = layer.get("border")

            if shape_type == "circle":
                cx = x + w / 2
                cy = y + h / 2
                r = min(w, h) / 2
                lines.append(f'  <circle cx="{cx}" cy="{cy}" r="{r}" '
                             f'fill="{fill}" opacity="{opacity}"/>')
            elif shape_type == "ellipse":
                cx = x + w / 2
                cy = y + h / 2
                rx = w / 2
                ry = h / 2
                lines.append(f'  <ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" '
                             f'fill="{fill}" opacity="{opacity}"/>')
            elif shape_type == "pill":
                lines.append(f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" '
                             f'rx="{h/2}" ry="{h/2}" fill="{fill}" opacity="{opacity}"/>')
            elif shape_type == "triangle":
                points = f"{x+w/2},{y} {x+w},{y+h} {x},{y+h}"
                lines.append(f'  <polygon points="{points}" fill="{fill}" opacity="{opacity}"/>')
            else:
                # Default to rect
                border_attr = ""
                if border:
                    border_attr = (f' stroke="{border.get("color", "#000")}" '
                                   f'stroke-width="{_safe_float(border.get("width"), 0) * canvas_w}"')
                lines.append(f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" '
                             f'rx="{round(br, 1)}" fill="{fill}" opacity="{opacity}"{border_attr}/>')

    lines.append("</svg>")
    return "\n".join(lines)


# ── HTML + CSS generator ──────────────────────────────────────────────────────

def generate_html(assembly: dict, canvas_w: float, canvas_h: float) -> str:
    """Convert assembled structure to HTML + CSS code.

    Args:
        assembly: Unified scene structure from assemble()
        canvas_w: Canvas width in pixels
        canvas_h: Canvas height in pixels

    Returns:
        Complete HTML document string
    """
    bg = assembly.get("background", {})
    bg_css = _bg_to_css(bg)

    lines: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="es">',
        "<head>",
        '<meta charset="utf-8">',
        "<style>",
        "  * { margin: 0; padding: 0; box-sizing: border-box; }",
        f"  .canvas {{ position: relative; width: {int(canvas_w)}px; height: {int(canvas_h)}px; overflow: hidden; background: {bg_css}; }}",
        "</style>",
        "</head>",
        "<body>",
        f'<div class="canvas">',
    ]

    for layer in assembly.get("layers", []):
        bbox_px = _bbox_to_px(layer.get("bbox", {}), canvas_w, canvas_h)
        kind = layer.get("kind", "shape")
        x = round(bbox_px["x"], 1)
        y = round(bbox_px["y"], 1)
        w = round(bbox_px["w"], 1)
        h = round(bbox_px["h"], 1)
        z = layer.get("zIndex", 1)

        css = f"position: absolute; left: {x}px; top: {y}px; width: {w}px; height: {h}px; z-index: {z};"

        if kind == "text":
            style = layer.get("style", {})
            font_size = _size_to_px(style.get("sizeCategory", "body"))
            font_family = FONT_CATEGORY_TO_FAMILY.get(
                style.get("fontCategory", "sans"), "Arial"
            )
            color = style.get("colorHex", "#000000")
            align = style.get("alignH", "left")
            weight = WEIGHT_CATEGORY_TO_VALUE.get(
                style.get("weightCategory", "regular"), "normal"
            )
            fstyle = "italic" if style.get("isItalic") else "normal"
            letter_space = LETTER_SPACING_TO_EM.get(
                style.get("letterSpacingCategory", "normal"), 0.0
            )
            text = layer.get("text", "")

            css += (
                f" font-size: {font_size}px; font-family: {font_family}; "
                f"color: {color}; text-align: {align}; font-weight: {weight}; "
                f"font-style: {fstyle}; letter-spacing: {letter_space}em; "
                f"display: flex; align-items: center; overflow: hidden;"
            )
            lines.append(f'  <div style="{css}">{text}</div>')

        elif kind == "image":
            desc = layer.get("description", "")
            lines.append(f'  <div style="{css} background: #e0e0e0; border-radius: 4px;" '
                         f'title="{desc}"></div>')

        elif kind == "shape":
            fill = layer.get("fill", "#cccccc")
            opacity = _safe_float(layer.get("opacity"), 1.0)
            br = _safe_float(layer.get("borderRadius"), 0) * canvas_w
            shape_type = layer.get("shapeType", "rect")
            border = layer.get("border")
            border_css = ""
            if border:
                border_css = (f" border: {_safe_float(border.get('width', 0), 0) * canvas_w}px "
                              f"solid {border.get('color', '#000')};")

            if shape_type == "circle":
                radius = min(w, h) / 2
                css += f" border-radius: {radius}px; background: {fill}; opacity: {opacity};"
                lines.append(f'  <div style="{css}{border_css}"></div>')
            elif shape_type == "pill":
                css += f" border-radius: {h/2}px; background: {fill}; opacity: {opacity};"
                lines.append(f'  <div style="{css}{border_css}"></div>')
            else:
                css += f" border-radius: {round(br, 1)}px; background: {fill}; opacity: {opacity};"
                lines.append(f'  <div style="{css}{border_css}"></div>')

    lines.append("</div>")
    lines.append("</body>")
    lines.append("</html>")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def validate_assembly(assembly: dict, tolerance: float = 0.02) -> tuple[bool, list[str]]:
    """Validate the assembled structure with tolerance.

    Instead of rejecting slightly-out-of-range values, we clamp them.
    This function reports warnings but does NOT reject — use
    the return value to decide whether to continue.

    Args:
        assembly: The assembled scene dict.
        tolerance: Allowed deviation beyond [0,1] range (default 0.02).

    Returns:
        (is_valid, warnings_list)
    """
    warnings: list[str] = []

    if "canvas" not in assembly:
        warnings.append("Missing 'canvas'")
    if "background" not in assembly:
        warnings.append("Missing 'background'")
    if "layers" not in assembly:
        warnings.append("Missing 'layers'")

    for i, layer in enumerate(assembly.get("layers", [])):
        bbox = layer.get("bbox", {})
        x = _safe_float(bbox.get("x"), 0)
        y = _safe_float(bbox.get("y"), 0)
        w = _safe_float(bbox.get("w"), 0)
        h = _safe_float(bbox.get("h"), 0)

        # Clamp values with tolerance
        clamped = False
        if x < -tolerance or x > 1 + tolerance:
            warnings.append(f"Layer {i}: x={x:.3f} clamped to [0,1]")
            clamped = True
        if y < -tolerance or y > 1 + tolerance:
            warnings.append(f"Layer {i}: y={y:.3f} clamped to [0,1]")
            clamped = True
        if w < -tolerance or w > 1 + tolerance:
            warnings.append(f"Layer {i}: w={w:.3f} clamped to [0,1]")
            clamped = True
        if h < -tolerance or h > 1 + tolerance:
            warnings.append(f"Layer {i}: h={h:.3f} clamped to [0,1]")
            clamped = True
        if x + w > 1 + tolerance:
            warnings.append(f"Layer {i}: x+w={x+w:.3f} > 1.0 (clamped)")
        if y + h > 1 + tolerance:
            warnings.append(f"Layer {i}: y+h={y+h:.3f} > 1.0 (clamped)")

        kind = layer.get("kind")
        if kind not in ("text", "image", "shape"):
            warnings.append(f"Layer {i}: invalid kind '{kind}'")

    return len(warnings) == 0, warnings


def clamp_bbox(bbox: dict) -> dict:
    """Clamp bbox values to [0,1] range."""
    return {
        "x": max(0.0, min(1.0, _safe_float(bbox.get("x"), 0))),
        "y": max(0.0, min(1.0, _safe_float(bbox.get("y"), 0))),
        "w": max(0.0, min(1.0, _safe_float(bbox.get("w"), 0))),
        "h": max(0.0, min(1.0, _safe_float(bbox.get("h"), 0))),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# RENDER (reutiliza render_page.mjs para SVG y HTML)
# ═══════════════════════════════════════════════════════════════════════════════

def _strip_fences(raw: str) -> str:
    result = raw.strip()
    if result.startswith("```"):
        result = re.sub(r"^```\w*\s*\n?", "", result)
        result = re.sub(r"\s*```$", "", result)
    return result.strip()


def render_html_v2(html_content: str, output_png: str, playwright_script: str) -> None:
    """Render HTML string to PNG via Playwright."""
    tmp_dir = tempfile.mkdtemp(prefix="html_render_v2_")
    html_path = os.path.join(tmp_dir, "render.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    result = subprocess.run(
        ["node", playwright_script, "--input", html_path, "--output", output_png],
        capture_output=True, text=True, errors="backslashreplace", timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"HTML render failed: {result.stderr or result.stdout}")

    try:
        os.remove(html_path)
        os.rmdir(tmp_dir)
    except OSError:
        pass


def render_svg_v2(svg_content: str, output_png: str, playwright_script: str) -> None:
    """Render SVG to PNG via Playwright (wraps in HTML)."""
    # Ensure no markdown fences
    svg_clean = _strip_fences(svg_content)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #f0f0f0; }}
</style>
</head>
<body>
{svg_clean}
</body>
</html>"""

    tmp_dir = tempfile.mkdtemp(prefix="svg_render_v2_")
    html_path = os.path.join(tmp_dir, "render.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    result = subprocess.run(
        ["node", playwright_script, "--input", html_path, "--output", output_png],
        capture_output=True, text=True, errors="backslashreplace", timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"SVG render failed: {result.stderr or result.stdout}")

    try:
        os.remove(html_path)
        os.rmdir(tmp_dir)
    except OSError:
        pass
