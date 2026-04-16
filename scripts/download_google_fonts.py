import os
import re
import requests
from pathlib import Path

# Lista de familias de fuentes extraídas de app.blade.php
FAMILIES = [
    "Anton",
    "Bebas Neue",
    "Caveat",
    "Inter",
    "Libre Baskerville",
    "Lobster",
    "Manrope",
    "Merriweather",
    "Montserrat",
    "Nunito",
    "Oswald",
    "Pacifico",
    "Playfair Display",
    "Poppins",
    "Quicksand",
    "Raleway",
    "Roboto Slab",
    "Rubik",
    "Source Sans 3",
    "Ubuntu",
    "Work Sans",
]

# Variantes a descargar para cada fuente
VARIANTS = ["400", "400italic", "700", "700italic"]

# Genera la lista de fuentes para el script
FONTS = [
    {"family": fam, "variants": VARIANTS} for fam in FAMILIES
]

GOOGLE_FONTS_CSS = "https://fonts.googleapis.com/css2?family={family}:{axes}"
FONTS_DIR = Path("public/fontsx")
CSS_OUTPUT = Path("public/fontsx/fonts.css")

# Utilidades

def variant_to_axis(variant):
    # Convierte '400italic' -> (400, italic)
    match = re.match(r"(\d+)(italic)?", variant)
    if not match:
        return ("400", "normal")
    weight = match.group(1)
    style = "italic" if match.group(2) else "normal"
    return (weight, style)

def get_css_url(family, variants):
    # Construye la URL de Google Fonts para la familia y variantes (API v2)
    # Ejemplo: family=Roboto:ital,wght@0,400;1,400;0,700;1,700
    axis_set = set()
    for v in variants:
        w, s = variant_to_axis(v)
        ital = "1" if s == "italic" else "0"
        axis_set.add(f"{ital},{w}")
    axis_list = sorted(axis_set)
    axes_str = ",".join(["ital","wght"]) + "@" + ";".join(axis_list)
    return f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}:{axes_str}&display=swap"

def download_and_parse_css(family, variants):
    # Descarga el CSS de Google Fonts y extrae los @font-face
    url = get_css_url(family, variants)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
    }
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    css = r.text
    # Extrae los bloques @font-face
    font_faces = re.findall(r"(@font-face\s*\{[^}]+\})", css)
    return font_faces, css

def download_woff2_from_css(font_faces, family):
    local_font_faces = []
    for block in font_faces:
        # Busca la URL del woff2
        m = re.search(r"src: [^;]*url\(([^)]+\.woff2)\)", block)
        if not m:
            continue
        url = m.group(1)
        # Extrae peso y estilo
        weight = re.search(r"font-weight: (\d+);", block).group(1)
        style = re.search(r"font-style: (\w+);", block).group(1)
        # Nombre de archivo local
        fname = f"{family.replace(' ', '_')}-{weight}-{style}.woff2"
        fpath = FONTS_DIR / fname
        # Descarga si no existe
        if not fpath.exists():
            print(f"Descargando {fname}...")
            resp = requests.get(url)
            resp.raise_for_status()
            with open(fpath, "wb") as f:
                f.write(resp.content)
        # Reemplaza la URL en el bloque CSS
        local_block = re.sub(r"url\([^)]+\)", f"url('/fonts/{fname}')", block)
        local_font_faces.append(local_block)
    return local_font_faces

def main():
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    all_font_faces = []
    for font in FONTS:
        family = font["family"]
        variants = font["variants"]
        font_faces, _ = download_and_parse_css(family, variants)
        local_faces = download_woff2_from_css(font_faces, family)
        all_font_faces.extend(local_faces)
    # Escribe el CSS
    CSS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(CSS_OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(all_font_faces))
    print(f"Fuentes y CSS generados correctamente en {FONTS_DIR} y {CSS_OUTPUT}")

if __name__ == "__main__":
    main()
