import json
from pathlib import Path


OUT = Path("docs/dev/fixtures/qa-coordinate-calibration.tc")
W, H = 1080, 1350
CENTER_X, CENTER_Y = W / 2, H / 2


def bg(color="#f8fafc"):
    return {
        "backgroundColor": color,
        "fillMode": "solid",
        "gradientStart": "#f8fafc",
        "gradientEnd": "#e2e8f0",
        "gradientAngle": 135,
        "backgroundImageSrc": None,
        "backgroundImageOpacity": 100,
        "backgroundImageTransparencyType": "flat",
        "backgroundImageTransparencyFadeOpacity": 0,
    }


def visual(**kw):
    base = {
        "rotation": 0,
        "opacity": 100,
        "border": False,
        "borderStyle": "solid",
        "contourWidth": 0,
        "contourColor": "#0f172a",
        "shadow": False,
        "backgroundColor": "#ffffff",
        "borderRadius": 0,
        "fillMode": "solid",
        "gradientStart": "#ffffff",
        "gradientEnd": "#ffffff",
        "gradientAngle": 135,
        "transparencyType": "flat",
        "transparencyFadeOpacity": 0,
    }
    base.update(kw)
    return base


def shape_layout(x, y, w, h, color, z=10, border=True, radius=0):
    return {
        "x": round(x, 2),
        "y": round(y, 2),
        "w": round(w, 2),
        "h": round(h, 2),
        "zIndex": z,
        **visual(
            backgroundColor=color,
            border=border,
            contourWidth=3 if border else 0,
            contourColor="#0f172a",
            borderRadius=radius,
        ),
    }


def centered_layout(cx, cy, w, h, color, z=10, border=True, radius=0):
    return shape_layout(cx - (w / 2), cy - (h / 2), w, h, color, z=z, border=border, radius=radius)


def text_layout(x, y, w, font_size=24, color="#0f172a", z=80, align="left"):
    return {
        "x": round(x, 2),
        "y": round(y, 2),
        "w": round(w, 2),
        "zIndex": z,
        "fontSize": font_size,
        "color": color,
        "fontFamily": "Manrope, sans-serif",
        "fontWeight": "bold",
        "italic": False,
        "uppercase": False,
        "textAlign": align,
        "letterSpacing": 0,
        "lineHeight": 1.15,
        "opacity": 100,
        "border": False,
        "shadow": False,
        "backgroundColor": "transparent",
        "backgroundPadding": 0,
        "backgroundOpacity": 0,
        "textEffectMode": "",
        "transparencyType": "flat",
        "transparencyFadeOpacity": 0,
        "paragraphStyles": [
            {
                "fontSize": font_size,
                "color": color,
                "fontFamily": "Manrope, sans-serif",
                "fontWeight": "bold",
                "italic": False,
                "uppercase": False,
                "textAlign": align,
                "letterSpacing": 0,
                "lineHeight": 1.15,
            }
        ],
    }


def shape_element(eid, label, kind="rectangle"):
    return {"id": eid, "type": "shape", "label": label, "shapeKind": kind}


def text_element(eid, text):
    return {"id": eid, "type": "text", "label": text, "text": text, "html": ""}


def content(title, subtitle):
    return {
        "title": title,
        "subtitle": subtitle,
        "date": "",
        "time": "",
        "location": "",
        "platform": "",
        "teacher": "",
        "price": "",
        "contact": "",
        "extra": "",
    }


CANONICAL_BOXES = [
    # id, x, y, w, h, color, label
    ("outer", 40, 40, 1000, 1270, "#ffffff", "margen 40"),
    ("inner", 140, 140, 800, 1070, "#e0f2fe", "margen 140"),
    ("center-v", CENTER_X - 2, 40, 4, 1270, "#f97316", "x centro exacto"),
    ("center-h", 40, CENTER_Y - 2, 1000, 4, "#f97316", "y centro exacto"),
    ("tl", 60, 60, 120, 120, "#22c55e", "TL 60,60"),
    ("tr", 900, 60, 120, 120, "#3b82f6", "TR 900,60"),
    ("bl", 60, 1170, 120, 120, "#eab308", "BL 60,1170"),
    ("br", 900, 1170, 120, 120, "#ef4444", "BR 900,1170"),
    ("center", CENTER_X - 75, CENTER_Y - 75, 150, 150, "#a855f7", "CENTER exacto"),
    ("center-dot", CENTER_X - 6, CENTER_Y - 6, 12, 12, "#111827", "CENTRO"),
]


def identity(x, y, w, h):
    return x, y, w, h


def scale_half_from_origin(x, y, w, h):
    return x * 0.5, y * 0.5, w * 0.5, h * 0.5


def compensate_half_page_offset(x, y, w, h):
    return x - (W * 0.5), y - (H * 0.5), w, h


def compensate_half_page_offset_and_scale(x, y, w, h):
    return (x * 0.5) - (W * 0.25), (y * 0.5) - (H * 0.25), w * 0.5, h * 0.5


def safe_half_canvas(x, y, w, h):
    # Keeps all reference boxes inside the top-left 540x675 quadrant.
    return x * 0.42 + 40, y * 0.42 + 40, w * 0.42, h * 0.42


def centered_in_half_canvas(x, y, w, h):
    # Same reduced scale, but centered around the expected 1080x1350 canvas.
    return x * 0.42 + 294, y * 0.42 + 358.5, w * 0.42, h * 0.42


TESTS = [
    (
        "coord-page-01-control",
        "01 CONTROL página 1",
        "Sistema normal: si esta página está bien, el documento base 1080x1350 se interpreta correctamente.",
        identity,
        "#f8fafc",
    ),
    (
        "coord-page-02-same-as-page-1",
        "02 MISMAS coordenadas que página 1",
        "Debe verse idéntica a página 1. Si falla, el problema aparece al cambiar a páginas 2+.",
        identity,
        "#fff7ed",
    ),
    (
        "coord-page-03-half-scale-origin",
        "03 Coordenadas al 50% desde origen",
        "Diagnóstico: si esta cabe pero queda en una esquina, hay una escala real distinta en páginas 2+.",
        scale_half_from_origin,
        "#f0fdf4",
    ),
    (
        "coord-page-04-negative-half-offset",
        "04 Compensación -50% ancho/alto",
        "Diagnóstico: si esta se centra bien, el render de páginas 2+ está sumando medio lienzo al origen.",
        compensate_half_page_offset,
        "#fef2f2",
    ),
    (
        "coord-page-05-negative-half-offset-scaled",
        "05 Compensación -25% + escala 50%",
        "Diagnóstico mixto: prueba si hay desplazamiento y sobredimensionado simultáneo.",
        compensate_half_page_offset_and_scale,
        "#eef2ff",
    ),
    (
        "coord-page-06-safe-half-canvas",
        "06 Todo dentro del cuadrante 540x675",
        "Si esta es la primera que cabe completa, páginas 2+ se están tratando como medio lienzo.",
        safe_half_canvas,
        "#ecfeff",
    ),
    (
        "coord-page-07-half-scale-centered",
        "07 Escala 42% centrada",
        "Debe caber incluso con errores moderados de escala; sirve como control visual reducido.",
        centered_in_half_canvas,
        "#faf5ff",
    ),
]


def add_reference_grid(page, transform):
    layout = page["elementLayout"]
    elements = page["customElements"]

    for key, x, y, w, h, color, label in CANONICAL_BOXES:
        tx, ty, tw, th = transform(x, y, w, h)
        eid = f"{page['id']}-{key}"
        layout[eid] = shape_layout(
            tx,
            ty,
            tw,
            th,
            color,
            z=10,
            radius=8 if key in {"tl", "tr", "bl", "br", "center", "center-dot"} else 0,
            border=key != "center-dot",
        )
        elements[eid] = shape_element(eid, label)

    # Coordinate labels use the same transform as the boxes, so they reveal text coordinate drift too.
    labels = [
        ("label-tl", 65, 190, 260, "TL x=60 y=60"),
        ("label-tr", 760, 190, 260, "TR x=900 y=60"),
        ("label-bl", 65, 1125, 300, "BL x=60 y=1170"),
        ("label-br", 720, 1125, 320, "BR x=900 y=1170"),
        ("label-center", 360, 770, 360, "CENTER exacto"),
    ]
    for key, x, y, w, text in labels:
        tx, ty, tw, _ = transform(x, y, w, 40)
        eid = f"{page['id']}-{key}"
        layout[eid] = text_layout(tx, ty, tw, 20, "#0f172a", z=90, align="center")
        elements[eid] = text_element(eid, text)


def build_page(pid, title, subtitle, transform, bg_color):
    page = {
        "id": pid,
        "content": content(title, subtitle),
        "elementLayout": {"background": bg(bg_color)},
        "customElements": {},
    }
    title_x, title_y, title_w, _ = transform(60, 22, 960, 40)
    subtitle_x, subtitle_y, subtitle_w, _ = transform(90, 82, 900, 30)
    page["elementLayout"]["title"] = text_layout(title_x, title_y, title_w, 32, "#0f172a", z=100, align="center")
    page["elementLayout"]["subtitle"] = text_layout(subtitle_x, subtitle_y, subtitle_w, 18, "#475569", z=100, align="center")
    add_reference_grid(page, transform)
    return page


pages = [build_page(*test) for test in TESTS]
first = pages[0]

snapshot = {
    "tcVersion": 2,
    "format": "vertical",
    "size": "1080 × 1350 px",
    "designSurface": {"width": W, "height": H},
    "designTitle": "QA coordenadas · calibración multipágina",
    "designTitleManual": True,
    "objective": "generic",
    "outputType": "digital",
    "pages": pages,
    "content": first["content"],
    "elementLayout": first["elementLayout"],
    "customElements": first["customElements"],
    "userUploadedImages": [],
    "workingDocumentPageId": first["id"],
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{OUT.as_posix()} | {OUT.stat().st_size} bytes | {len(pages)} pages")
for page in pages:
    xs = []
    ys = []
    for eid, layout in page["elementLayout"].items():
        if eid == "background":
            continue
        xs.extend([layout.get("x", 0), layout.get("x", 0) + layout.get("w", 0)])
        ys.extend([layout.get("y", 0), layout.get("y", 0) + layout.get("h", layout.get("fontSize", 0) * 1.15)])
    print(f"{page['id']}: source_bounds=({min(xs):.1f}, {min(ys):.1f}, {max(xs):.1f}, {max(ys):.1f})")
