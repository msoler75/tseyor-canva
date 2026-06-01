"""
formats.py — Alternative output formats for the Smart Import pipeline.

Each format defines:
- ``SYSTEM_PROMPT`` / ``ANALYSIS_PROMPT`` — how to prompt the LLM
- ``validate(raw: str) -> tuple[bool, list[str]]`` — syntactic validation
- ``render(raw: str, output_png: str)`` — Playwright-based rendering
- ``file_extension`` — output file extension

Supported formats:
- ``scenegraph`` — SceneGraph JSON → .tc v2 → Vue app screenshot (current)
- ``svg`` — AI generates SVG, rendered directly in browser
- ``html`` — AI generates HTML + inline CSS, rendered directly in browser
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# SCENEGRAPH (baseline)
# ═══════════════════════════════════════════════════════════════════════════════

SCENEGRAPH_SYSTEM_PROMPT: str = (
    "Eres un analizador de composición gráfica especializado en extraer "
    "SceneGraphs de imágenes de diseño (carteles, flyers, banners, posts "
    "y cualquier pieza gráfica publicitaria). "
    "Debes analizar la imagen y devolver un JSON que describa su estructura "
    "visual siguiendo el schema SceneGraph v1 exactamente. "
    "No inventes campos fuera del schema; respeta los tipos y nombres "
    "definidos.\n\n"
    "Estructura requerida:\n"
    "- canvas: { width (px), height (px), detectedFormat: 'vertical'|'horizontal'|'square' }\n"
    "- background: { kind: 'solid'|'gradient'|'image', color: hex (6 dígitos), confidence: 0..1 }\n"
    "- layers: array de objetos con:\n"
    "  * id: string único ('layer-1', 'layer-2', ...)\n"
    "  * kind: 'text' | 'image' | 'shape'\n"
    "  * confidence: 0..1\n"
    "  * bbox: { x, y, w, h } en píxeles — MUY IMPORTANTE: las coordenadas deben ser PRECISAS.\n"
    "           Mide desde la esquina superior izquierda del canvas.\n"
    "  * text: (obligatorio si kind=text) el texto exacto\n"
    "  * style: (para text) { fontSize (número, sin unidades), fontWeight (string|número), color (hex 6 dígitos), textAlign, lineHeight, letterSpacing }\n"
    "  * description: (para image) descripción breve\n"
    "  * cropFromSource: bool (para image)\n"
    "  * shape: (para shape) 'rectangle'|'circle'|'ellipse'\n"
    "  * shapeStyle: (para shape) { fill (hex 6 dígitos), opacity, borderRadius }\n"
    "- warnings: string[]\n\n"
    "IMPORTANTE:\n"
    "- Las coordenadas y dimensiones deben ser lo más precisas posible.\n"
    "- Respetar el orden de capas: el array layers debe estar ordenado de atrás a adelante (z-index).\n"
    "- Los colores deben ser exactos (formato #RRGGBB de 6 dígitos).\n"
    "- No uses unidades (px, pt) en fontSize — solo el número.\n"
    "Devuelve SOLO el JSON válido, sin explicaciones ni markdown fences."
)

SCENEGRAPH_ANALYSIS_PROMPT: str = (
    "Analiza esta imagen de diseño y extrae su estructura como SceneGraph JSON. "
    "Identifica el canvas, el fondo, y cada capa visual ordenada por z-index "
    "(de atrás a adelante). Para cada capa proporciona:\n"
    "- bounding box PRECISO en píxeles (x, y desde esquina superior izquierda)\n"
    "- tipo: text, image o shape\n"
    "- contenido textual completo y exacto\n"
    "- color exacto (#RRGGBB), fontSize sin unidades\n"
    "- nivel de confianza\n\n"
    "Devuelve SOLO el JSON."
)


# ═══════════════════════════════════════════════════════════════════════════════
# SVG
# ═══════════════════════════════════════════════════════════════════════════════

SVG_SYSTEM_PROMPT: str = (
    "Eres un diseñador gráfico experto en SVG. "
    "Debes analizar la imagen de diseño (cartel, flyer, banner, post, etc.) "
    "y generar código SVG que la reproduzca lo más fielmente posible.\n\n"
    "REQUISITOS:\n"
    "- Usa un elemento <svg> raíz con viewBox preciso (mismas dimensiones que la imagen original).\n"
    "- Organiza los elementos por z-index: primero el fondo, luego las capas de atrás a adelante.\n"
    "- Para texto: usa <text> con font-size, font-family, font-weight, fill exactos.\n"
    "- Para imágenes: usa <image> con href, x, y, width, height precisos. "
    "NO incluyas imágenes reales — usa placeholders con rectángulos de color similar.\n"
    "- Para fondos degradados: usa <linearGradient> o <radialGradient>.\n"
    "- Para formas: usa <rect>, <circle>, <ellipse> con colores exactos.\n"
    "- Las coordenadas y dimensiones deben ser PRECISAS — mide desde la esquina superior izquierda.\n"
    "- Los colores deben ser exactos (#RRGGBB de 6 dígitos).\n\n"
    "IMPORTANTE: Devuelve SOLO el código SVG válido, sin explicaciones ni markdown fences."
)

SVG_ANALYSIS_PROMPT: str = (
    "Analiza esta imagen de diseño y genera código SVG que la reproduzca "
    "con la máxima fidelidad posible. Incluye: fondo, textos, imágenes "
    "(como placeholders), formas y degradados. Usa coordenadas y colores precisos. "
    "Devuelve SOLO el SVG."
)


def validate_svg(raw: str) -> tuple[bool, list[str]]:
    """Basic SVG validation."""
    errors: list[str] = []
    raw_stripped = raw.strip()

    if not raw_stripped:
        errors.append("Empty SVG")
        return False, errors

    if not raw_stripped.startswith("<svg") and not raw_stripped.startswith("<?xml"):
        errors.append("Does not start with <svg> or <?xml>")
        return False, errors

    if "</svg>" not in raw_stripped:
        errors.append("Missing closing </svg>")
        return False, errors

    # Check for viewBox
    if "viewBox" not in raw_stripped:
        errors.append("Missing viewBox attribute on <svg>")

    return len(errors) == 0, errors


_SVG_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #f0f0f0; }}
  svg {{ max-width: 100vw; max-height: 100vh; }}
</style>
</head>
<body>
{sVG_CONTENT}
</body>
</html>"""


def render_svg(raw: str, output_png: str, playwright_script: str) -> None:
    """Render SVG to PNG via Playwright."""
    svg_content = raw.strip()
    if svg_content.startswith("```"):
        svg_content = re.sub(r"^```(?:svg)?\s*", "", svg_content)
        svg_content = re.sub(r"\s*```$", "", svg_content)

    html = _SVG_HTML_TEMPLATE.format(sVG_CONTENT=svg_content)

    tmp_dir = tempfile.mkdtemp(prefix="svg_render_")
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


# ═══════════════════════════════════════════════════════════════════════════════
# HTML + CSS
# ═══════════════════════════════════════════════════════════════════════════════

HTML_SYSTEM_PROMPT: str = (
    "Eres un diseñador web experto en HTML y CSS. "
    "Debes analizar la imagen de diseño (cartel, flyer, banner, post, etc.) "
    "y generar código HTML + CSS que la reproduzca lo más fielmente posible.\n\n"
    "REQUISITOS:\n"
    "- Usa HTML5 con CSS inline en <style> dentro del <head>.\n"
    "- El diseño debe estar contenido en un div contenedor con las dimensiones exactas.\n"
    "- Organiza los elementos por z-index usando position: absolute y z-index.\n"
    "- Para texto: usa <div> o <p> con font-size (sin unidades, solo número que se usará como px), "
    "font-weight, color exacto, text-align.\n"
    "- Para imágenes: usa <div> con background-color como placeholder. "
    "Dimensiones precisas con width y height. NO incluyas imágenes reales.\n"
    "- Para fondos degradados: usa background: linear-gradient(...).\n"
    "- Para fondos sólidos: usa background-color en el contenedor.\n"
    "- Las coordenadas (left, top) y dimensiones (width, height) deben ser PRECISAS.\n"
    "- Los colores deben ser exactos (#RRGGBB de 6 dígitos).\n"
    "- El contenedor principal debe tener position: relative.\n"
    "- Cada elemento debe tener position: absolute con left, top, width, height.\n\n"
    "IMPORTANTE: Devuelve SOLO el HTML + CSS válido, completo (doctype a </html>), "
    "sin explicaciones ni markdown fences."
)

HTML_ANALYSIS_PROMPT: str = (
    "Analiza esta imagen de diseño y genera código HTML + CSS que la reproduzca "
    "con la máxima fidelidad posible. Usa position: absolute para cada elemento, "
    "colores exactos (#RRGGBB), tamaños de fuente precisos, y el z-index correcto. "
    "Devuelve SOLO el HTML completo."
)


def validate_html(raw: str) -> tuple[bool, list[str]]:
    """Basic HTML validation."""
    errors: list[str] = []
    raw_stripped = raw.strip()

    if not raw_stripped:
        errors.append("Empty HTML")
        return False, errors

    if "<!DOCTYPE html" not in raw_stripped.upper() and "<html" not in raw_stripped.lower():
        errors.append("Missing <!DOCTYPE html> or <html>")
        return False, errors

    if "</html>" not in raw_stripped.lower():
        errors.append("Missing closing </html>")
        return False, errors

    # Check for inline styles
    if "<style>" not in raw_stripped:
        errors.append("Missing <style> block — inline CSS recommended")

    return len(errors) == 0, errors


def render_html(raw: str, output_png: str, playwright_script: str) -> None:
    """Render HTML to PNG via Playwright."""
    html_content = raw.strip()
    if html_content.startswith("```"):
        html_content = re.sub(r"^```(?:html)?\s*", "", html_content)
        html_content = re.sub(r"\s*```$", "", html_content)

    tmp_dir = tempfile.mkdtemp(prefix="html_render_")
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


# ═══════════════════════════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════════════════════════

FORMATS = {
    "scenegraph": {
        "system_prompt": SCENEGRAPH_SYSTEM_PROMPT,
        "analysis_prompt": SCENEGRAPH_ANALYSIS_PROMPT,
        "file_extension": ".json",
        "validate": None,  # Uses existing validator.py
        "render": None,    # Uses existing tc_render_standalone.js
    },
    "svg": {
        "system_prompt": SVG_SYSTEM_PROMPT,
        "analysis_prompt": SVG_ANALYSIS_PROMPT,
        "file_extension": ".svg",
        "validate": validate_svg,
        "render": render_svg,
    },
    "html": {
        "system_prompt": HTML_SYSTEM_PROMPT,
        "analysis_prompt": HTML_ANALYSIS_PROMPT,
        "file_extension": ".html",
        "validate": validate_html,
        "render": render_html,
    },
}


def get_format(name: str) -> dict:
    """Get format config by name."""
    if name not in FORMATS:
        raise ValueError(
            f"Unsupported format: {name}. "
            f"Supported: {', '.join(sorted(FORMATS))}"
        )
    return FORMATS[name]
