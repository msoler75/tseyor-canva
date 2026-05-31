import base64
import json
import math
import re
from pathlib import Path


OUT = Path("docs/dev/fixtures/qa-visual-effects-matrix.tc")
W, H = 1080, 1350
CENTER_X, CENTER_Y = W / 2, H / 2


def uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


PHOTO = uri("""<svg width="1200" height="900" viewBox="0 0 1200 900" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="g" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#0ea5e9"/><stop offset=".48" stop-color="#7c3aed"/><stop offset="1" stop-color="#111827"/></linearGradient></defs><rect width="1200" height="900" fill="url(#g)"/><circle cx="970" cy="150" r="96" fill="#fde68a"/><circle cx="230" cy="210" r="140" fill="#fff" fill-opacity=".15"/><path d="M0 720 L210 500 L385 655 L555 360 L760 675 L940 510 L1200 735 L1200 900 L0 900Z" fill="#020617" fill-opacity=".82"/><path d="M0 780 L265 610 L450 740 L620 560 L850 790 L1050 670 L1200 760 L1200 900 L0 900Z" fill="#67e8f9" fill-opacity=".32"/><rect x="86" y="78" width="318" height="176" rx="34" fill="#fff" fill-opacity=".20"/><rect x="128" y="122" width="212" height="26" rx="13" fill="#fff" fill-opacity=".72"/><rect x="128" y="174" width="156" height="20" rx="10" fill="#fff" fill-opacity=".48"/></svg>""")
PORTRAIT = uri("""<svg width="1200" height="900" viewBox="0 0 1200 900" xmlns="http://www.w3.org/2000/svg"><defs><radialGradient id="r" cx="48%" cy="35%" r="70%"><stop stop-color="#fef3c7"/><stop offset=".45" stop-color="#fb7185"/><stop offset="1" stop-color="#581c87"/></radialGradient><pattern id="d" width="50" height="50" patternUnits="userSpaceOnUse"><circle cx="12" cy="12" r="5" fill="#fff" fill-opacity=".28"/></pattern></defs><rect width="1200" height="900" fill="url(#r)"/><rect width="1200" height="900" fill="url(#d)"/><circle cx="450" cy="385" r="190" fill="#020617" fill-opacity=".28"/><circle cx="450" cy="340" r="74" fill="#fff" fill-opacity=".82"/><rect x="315" y="430" width="270" height="245" rx="132" fill="#fff" fill-opacity=".70"/><path d="M760 170 C940 80 1090 180 1065 370 C1035 595 790 555 735 385 C700 280 690 210 760 170Z" fill="#38bdf8" fill-opacity=".45"/><path d="M760 640 C875 545 990 620 1110 552" stroke="#facc15" stroke-width="44" stroke-linecap="round" fill="none" stroke-opacity=".78"/></svg>""")
TEXTURE = uri("""<svg width="1200" height="1200" viewBox="0 0 1200 1200" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="g" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#111827"/><stop offset=".5" stop-color="#0f766e"/><stop offset="1" stop-color="#f97316"/></linearGradient><pattern id="grid" width="80" height="80" patternUnits="userSpaceOnUse"><path d="M80 0H0V80" fill="none" stroke="#fff" stroke-opacity=".22" stroke-width="3"/></pattern></defs><rect width="1200" height="1200" fill="url(#g)"/><rect width="1200" height="1200" fill="url(#grid)"/><circle cx="980" cy="220" r="190" fill="#fff" fill-opacity=".20"/><circle cx="250" cy="900" r="260" fill="#020617" fill-opacity=".28"/><path d="M70 620 C310 350 480 820 710 560 S1050 490 1140 760" fill="none" stroke="#fef3c7" stroke-opacity=".60" stroke-width="42" stroke-linecap="round"/></svg>""")
CHECKER = uri("""<svg width="800" height="800" viewBox="0 0 800 800" xmlns="http://www.w3.org/2000/svg"><rect width="800" height="800" fill="#e2e8f0"/><g fill="#94a3b8" fill-opacity=".65"><rect x="0" y="0" width="100" height="100"/><rect x="200" y="0" width="100" height="100"/><rect x="400" y="0" width="100" height="100"/><rect x="600" y="0" width="100" height="100"/><rect x="100" y="100" width="100" height="100"/><rect x="300" y="100" width="100" height="100"/><rect x="500" y="100" width="100" height="100"/><rect x="700" y="100" width="100" height="100"/></g><path d="M0 200H800M0 400H800M0 600H800M200 0V800M400 0V800M600 0V800" stroke="#fff" stroke-width="8" opacity=".65"/></svg>""")
QR = uri("""<svg width="400" height="400" viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg"><rect width="400" height="400" fill="#fff"/><g fill="#0f172a"><rect x="36" y="36" width="92" height="92"/><rect x="58" y="58" width="48" height="48" fill="#fff"/><rect x="73" y="73" width="18" height="18"/><rect x="272" y="36" width="92" height="92"/><rect x="294" y="58" width="48" height="48" fill="#fff"/><rect x="309" y="73" width="18" height="18"/><rect x="36" y="272" width="92" height="92"/><rect x="58" y="294" width="48" height="48" fill="#fff"/><rect x="73" y="309" width="18" height="18"/><rect x="164" y="44" width="24" height="24"/><rect x="204" y="44" width="24" height="24"/><rect x="164" y="92" width="64" height="24"/><rect x="156" y="156" width="28" height="28"/><rect x="204" y="156" width="76" height="28"/><rect x="316" y="156" width="28" height="28"/><rect x="156" y="204" width="28" height="76"/><rect x="204" y="244" width="28" height="28"/><rect x="252" y="204" width="28" height="76"/><rect x="316" y="220" width="28" height="28"/><rect x="156" y="316" width="28" height="28"/><rect x="204" y="300" width="76" height="28"/><rect x="300" y="284" width="28" height="80"/><rect x="348" y="316" width="20" height="48"/></g></svg>""")


def content(title="", subtitle="", extra=""):
    return dict(title=title, subtitle=subtitle, date="", time="", location="", platform="", teacher="", price="", contact="", extra=extra)


def bg(color="#0f172a", **kw):
    base = dict(
        backgroundColor=color, fillMode="solid", gradientStart="#0ea5e9", gradientEnd="#8b5cf6", gradientAngle=135,
        backgroundImageSrc=None, backgroundImageAssetId=None, backgroundImagePendingDataUrl=None, backgroundImageStoragePath=None,
        backgroundImageWidth=None, backgroundImageHeight=None, backgroundImageCropScale=1, backgroundImageCropOffsetX=0,
        backgroundImageCropOffsetY=0, backgroundImageFlipX=False, backgroundImageFlipY=False, backgroundImageOpacity=100,
        backgroundImageTransparencyType="flat", backgroundImageTransparencyFadeOpacity=0, backgroundImageTransparencyCenterX=50,
        backgroundImageTransparencyCenterY=50, backgroundImageTransparencyRadius=70, backgroundImageTransparencyRadiusX=70,
        backgroundImageTransparencyRadiusY=45, backgroundImageTransparencyRotation=0, backgroundImageTransparencyStartX=0,
        backgroundImageTransparencyStartY=50, backgroundImageTransparencyEndX=100, backgroundImageTransparencyEndY=50,
        backgroundImageTransparencyEasing="linear",
    )
    base.update(kw)
    return base


def centered_box(cx, cy, w, h, **kw):
    return dict(x=cx - (w / 2), y=cy - (h / 2), w=w, h=h, **kw)


def visual(**kw):
    base = dict(
        rotation=0, opacity=100, border=False, borderStyle="solid", contourWidth=0, contourColor="#ffffff",
        shadow=False, shadowPreset="soft", shadowColor="#0f172a", shadowAngle=135, shadowOffset=20, shadowBlur=25,
        shadowOpacity=65, neonColor="", neonIntensity=55, bubbleColor="", backgroundColor="transparent", borderRadius=12,
        fillMode="solid", gradientStart="#0ea5e9", gradientEnd="#8b5cf6", gradientAngle=135, imageCropScale=1,
        imageCropOffsetX=0, imageCropOffsetY=0, flipX=False, flipY=False, transparencyType="flat",
        transparencyFadeOpacity=0, transparencyCenterX=50, transparencyCenterY=50, transparencyRadius=70,
        transparencyRadiusX=70, transparencyRadiusY=45, transparencyRotation=0, transparencyStartX=0,
        transparencyStartY=50, transparencyEndX=100, transparencyEndY=50, transparencyEasing="linear",
        imageTintColor="#0f172a", imageTintStrength=0, borderRadiusTopLeft=12, borderRadiusTopRight=12,
        borderRadiusBottomRight=12, borderRadiusBottomLeft=12,
    )
    base.update(kw)
    return base


def shape_l(x, y, w, h, z=10, **kw):
    opts = {"backgroundColor": "#ffffff", **kw}
    return dict(x=x, y=y, w=w, h=h, zIndex=z, **visual(**opts))


def img_l(x, y, w, h, z=20, **kw):
    return dict(x=x, y=y, w=w, h=h, zIndex=z, **visual(**kw))


def txt_l(x, y, w, fs, z=80, **kw):
    base = dict(
        x=x, y=y, w=w, zIndex=z, fontSize=fs, color="#0f172a", shadow=False, border=False, borderStyle="solid",
        fontFamily="Manrope, sans-serif", opacity=100, fontWeight="regular", italic=False, uppercase=False,
        textAlign="left", letterSpacing=0, lineHeight=1.25, shadowPreset="soft", shadowColor="#0f172a",
        shadowAngle=135, shadowOffset=18, shadowBlur=22, shadowOpacity=65, contourWidth=0, contourColor="#ffffff",
        neonColor="", neonIntensity=55, misalignedThickness=0, hollowText=False, bubbleColor="",
        backgroundColor="transparent", backgroundRoundness=45, backgroundPadding=0, backgroundOpacity=70,
        textEffectMode="", imageCropScale=1, imageCropOffsetX=0, imageCropOffsetY=0, flipX=False, flipY=False,
        transparencyType="flat", transparencyFadeOpacity=0, transparencyCenterX=50, transparencyCenterY=50,
        transparencyRadius=70, transparencyRadiusX=70, transparencyRadiusY=45, transparencyRotation=0,
        transparencyStartX=0, transparencyStartY=50, transparencyEndX=100, transparencyEndY=50, transparencyEasing="linear",
    )
    base.update(kw)
    base.setdefault("paragraphStyles", [dict(
        fontSize=base["fontSize"], color=base["color"], fontFamily=base["fontFamily"], fontWeight=base["fontWeight"],
        italic=base["italic"], uppercase=base["uppercase"], textAlign=base["textAlign"],
        letterSpacing=base["letterSpacing"], lineHeight=base["lineHeight"],
    )])
    return base


def shape_e(id, label, kind): return dict(id=id, type="shape", label=label, shapeKind=kind)
def img_e(id, label, src, iw=1200, ih=900): return dict(id=id, type="image", label=label, src=src, intrinsicWidth=iw, intrinsicHeight=ih, uploadStatus="done", needsUpload=False)
def txt_e(id, label, text): return dict(id=id, type="text", label=label, text=text, html="")
def linked_e(id, label, html): return dict(id=id, type="linkedText", label=label, text=html, html=html)


def html_to_text(value):
    value = str(value or "")
    value = re.sub(r"</p\s*>", "\n", value, flags=re.I)
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", value).strip()


def text_for_element(page_data, element_id):
    if element_id == "title":
        return page_data["content"].get("title", "")
    if element_id == "subtitle":
        return page_data["content"].get("subtitle", "")
    if element_id == "meta":
        return " ".join(filter(None, [page_data["content"].get("date"), page_data["content"].get("time")]))
    if element_id == "contact":
        return " ".join(filter(None, [
            page_data["content"].get("location"),
            page_data["content"].get("platform"),
            page_data["content"].get("contact"),
        ]))
    if element_id == "extra":
        return page_data["content"].get("extra", "")
    element = page_data.get("customElements", {}).get(element_id, {})
    return html_to_text(element.get("html") or element.get("text") or "")


def estimate_text_height(layout, text):
    font_size = float(layout.get("fontSize", 18) or 18)
    line_height = float(layout.get("lineHeight", 1.25) or 1.25)
    width = max(1.0, float(layout.get("w", 160) or 160))
    letter_spacing = float(layout.get("letterSpacing", 0) or 0)
    padding = float(layout.get("backgroundPadding", 0) or 0)
    chars_per_line = max(6, int(width / max(6.0, (font_size * 0.54) + letter_spacing)))
    source_lines = str(text or "").splitlines() or [""]
    line_count = 0
    for line in source_lines:
        line_count += max(1, math.ceil(max(1, len(line)) / chars_per_line))
    return (line_count * font_size * line_height) + (padding * 2)


def raw_box(page_data, element_id, layout):
    x = float(layout.get("x", 0) or 0)
    y = float(layout.get("y", 0) or 0)
    w = float(layout.get("w", 0) or 0)
    if "h" in layout and layout.get("h") is not None:
        h = float(layout.get("h", 0) or 0)
    elif "fontSize" in layout:
        h = estimate_text_height(layout, text_for_element(page_data, element_id))
    else:
        h = 0.0
    return x, y, w, h


def visual_bleed(layout):
    bleed = 0.0
    if layout.get("transparencyType", "flat") != "flat":
        # buildElementContentStyle() uses effectBleed=56 for advanced masks.
        bleed += 56
    if layout.get("border"):
        bleed += float(layout.get("contourWidth", 1) or 1)
    if layout.get("shadow"):
        bleed += (float(layout.get("shadowBlur", 0) or 0) * 0.9) + (float(layout.get("shadowOffset", 0) or 0) * 0.65)
    if layout.get("textEffectMode") in {"neon", "hollow", "misaligned"}:
        bleed += float(layout.get("contourWidth", 0) or 0) + (float(layout.get("neonIntensity", 0) or 0) * 0.22)
    bleed += float(layout.get("backgroundPadding", 0) or 0)
    return bleed


def visual_bounds_for(page_data, element_id, layout):
    x, y, w, h = raw_box(page_data, element_id, layout)
    bleed = visual_bleed(layout)
    angle = abs(float(layout.get("rotation", 0) or 0)) % 180
    if angle:
        radians = math.radians(angle)
        rotated_w = abs(w * math.cos(radians)) + abs(h * math.sin(radians))
        rotated_h = abs(w * math.sin(radians)) + abs(h * math.cos(radians))
        cx, cy = x + w / 2, y + h / 2
        x, y = cx - rotated_w / 2, cy - rotated_h / 2
        w, h = rotated_w, rotated_h
    return x - bleed, y - bleed, x + w + bleed, y + h + bleed


def page_visual_bounds(page_data):
    bounds = []
    for element_id, layout in page_data.get("elementLayout", {}).items():
        if element_id == "background" or not isinstance(layout, dict):
            continue
        bounds.append(visual_bounds_for(page_data, element_id, layout))
    if not bounds:
        return 0, 0, W, H
    return min(b[0] for b in bounds), min(b[1] for b in bounds), max(b[2] for b in bounds), max(b[3] for b in bounds)


SCALAR_KEYS = {
    "fontSize", "letterSpacing", "contourWidth", "shadowOffset", "shadowBlur",
    "backgroundPadding", "borderRadius", "borderRadiusTopLeft", "borderRadiusTopRight",
    "borderRadiusBottomRight", "borderRadiusBottomLeft", "misalignedThickness",
}


def scale_value(value, scale):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    return round(value * scale, 2)


def transform_page(page_data, min_x, min_y, scale, offset_x, offset_y):
    for element_id, layout in page_data.get("elementLayout", {}).items():
        if element_id == "background" or not isinstance(layout, dict):
            continue
        if "x" in layout:
            layout["x"] = round((float(layout["x"]) - min_x) * scale + offset_x, 2)
        if "y" in layout:
            layout["y"] = round((float(layout["y"]) - min_y) * scale + offset_y, 2)
        if "w" in layout and isinstance(layout.get("w"), (int, float)):
            layout["w"] = round(float(layout["w"]) * scale, 2)
        if "h" in layout and isinstance(layout.get("h"), (int, float)):
            layout["h"] = round(float(layout["h"]) * scale, 2)
        for key in list(layout.keys()):
            if key in SCALAR_KEYS:
                layout[key] = scale_value(layout[key], scale)
        for paragraph in layout.get("paragraphStyles") or []:
            if not isinstance(paragraph, dict):
                continue
            for key in ("fontSize", "letterSpacing"):
                if key in paragraph:
                    paragraph[key] = scale_value(paragraph[key], scale)


def normalize_pages_to_safe_area(all_pages, safe=190, initial_scale=0.70):
    report = []
    for page_data in all_pages:
        for iteration in range(5):
            min_x, min_y, max_x, max_y = page_visual_bounds(page_data)
            bw, bh = max_x - min_x, max_y - min_y
            available_w, available_h = W - (safe * 2), H - (safe * 2)
            needs = min_x < safe or min_y < safe or max_x > W - safe or max_y > H - safe
            fit_scale = min(1.0, available_w / bw, available_h / bh) if bw > 0 and bh > 0 else 1.0
            # This fixture is for QA stability, not final artwork aesthetics:
            # force a first-pass reduction so editor padding, CSS masks, auto-height text,
            # and import-time rendering differences cannot push effects outside the page.
            scale = min(initial_scale if iteration == 0 else 1.0, fit_scale)
            if iteration > 0 and not needs and fit_scale >= 1:
                break
            offset_x = (W - (bw * scale)) / 2
            offset_y = (H - (bh * scale)) / 2
            transform_page(page_data, min_x, min_y, scale, offset_x, offset_y)
        report.append((page_data["id"], page_visual_bounds(page_data)))
    return report


def page(pid, title, subtitle, background, dark=False):
    p = dict(id=pid, content=content(title, subtitle), elementLayout=dict(background=background), customElements={})
    title_box = centered_box(CENTER_X, 80, 920, 44)
    subtitle_box = centered_box(CENTER_X, 131, 840, 21)
    p["elementLayout"]["title"] = txt_l(title_box["x"], title_box["y"], title_box["w"], 44, color="#ffffff" if dark else "#0f172a", fontWeight="bold", fontFamily="Poppins, sans-serif", textAlign="center", lineHeight=1.05)
    p["elementLayout"]["subtitle"] = txt_l(subtitle_box["x"], subtitle_box["y"], subtitle_box["w"], 21, color="#bae6fd" if dark else "#475569", textAlign="center", lineHeight=1.25)
    return p


pages = []

# 1. Índice
p = page("effects-page-01-index", "QA EFFECTS MATRIX", "10 páginas de pruebas visuales: transparencias, imágenes, texto, formas y combinaciones.", bg("#020617", fillMode="gradient", gradientStart="#020617", gradientEnd="#312e81", gradientAngle=145, backgroundImageSrc=TEXTURE, backgroundImageWidth=1200, backgroundImageHeight=1200, backgroundImageOpacity=22, backgroundImageTransparencyType="linear", backgroundImageTransparencyFadeOpacity=0), True)
for i, item in enumerate([
    "02 Transparencias base: flat, circle, ellipse, linear",
    "03 Transparencias lineales: dirección + easing",
    "04 Imágenes sobre fondos: máscaras y tintes",
    "05 Imagen de fondo: transparencia del background",
    "06 Formas: gradiente + borde + sombra + máscara",
    "07 Texto: contorno, hueco, neón, fondos y máscaras",
    "08 Capas: solapes, z-index y opacidades acumuladas",
    "09 Imagen: crop, flip, tinte y transparencia combinados",
    "10 Stress final: todo combinado con linkedText y QR",
]):
    y = 245 + i * 82
    sid, tid = f"p1-chip-{i}", f"p1-text-{i}"
    p["elementLayout"][sid] = shape_l(120, y, 840, 58, 20, backgroundColor="#ffffff", opacity=12, border=True, contourWidth=1.5, contourColor="#67e8f9", borderRadius=18)
    p["customElements"][sid] = shape_e(sid, item, "rectangle")
    p["elementLayout"][tid] = txt_l(150, y + 15, 780, 21, 40, color="#f8fafc", fontWeight="bold")
    p["customElements"][tid] = txt_e(tid, item, item)
pages.append(p)

# 2. Transparencias base
p = page("effects-page-02-transparency-primitives", "Transparencias base", "Misma forma sobre checker: cambia tipo, radio, centro, opacidad final y easing.", bg("#f8fafc", fillMode="gradient", gradientStart="#f8fafc", gradientEnd="#dbeafe", gradientAngle=180))
cols = [(95, "flat", {}), (330, "circle", dict(transparencyCenterX=35, transparencyCenterY=38, transparencyRadius=58)), (565, "ellipse", dict(transparencyCenterX=60, transparencyCenterY=44, transparencyRadiusX=84, transparencyRadiusY=38)), (800, "linear", dict(transparencyStartX=0, transparencyStartY=0, transparencyEndX=100, transparencyEndY=100))]
rows = [(255, 0, "fade→0"), (530, 30, "fade→30"), (805, 65, "fade→65")]
for ci, (x, t, extra) in enumerate(cols):
    lab = f"p2-label-{ci}"
    p["elementLayout"][lab] = txt_l(x, 205, 185, 18, color="#0f172a", fontWeight="bold", textAlign="center")
    p["customElements"][lab] = txt_e(lab, t, t)
    for ri, (y, fade, label) in enumerate(rows):
        bid, sid, tid = f"p2-bg-{ci}-{ri}", f"p2-shape-{ci}-{ri}", f"p2-note-{ci}-{ri}"
        p["elementLayout"][bid] = img_l(x, y, 185, 190, 5, src=CHECKER, borderRadius=18)
        p["customElements"][bid] = img_e(bid, "Fondo checker", CHECKER, 800, 800)
        p["elementLayout"][sid] = shape_l(x + 18, y + 22, 150, 145, 30, fillMode="gradient", gradientStart="#06b6d4", gradientEnd="#a855f7", gradientAngle=35, opacity=92, border=True, contourWidth=3, contourColor="#0f172a", shadow=True, shadowPreset="lifted", shadowColor="#334155", shadowOpacity=60, shadowBlur=35, transparencyType=t, transparencyFadeOpacity=fade, transparencyEasing="smoothstep", **extra)
        p["customElements"][sid] = shape_e(sid, f"{t} {label}", "circle" if ri == 0 else ("hexagon" if ri == 1 else "star-6"))
        p["elementLayout"][tid] = txt_l(x + 8, y + 218, 170, 15, color="#334155", textAlign="center")
        p["customElements"][tid] = txt_e(tid, label, label)
p["content"]["extra"] = "Objetivo: comprobar mask-image, bleed y persistencia visual en canvas/export."
p["elementLayout"]["extra"] = txt_l(90, 1130, 900, 22, color="#0f172a", fontWeight="bold", textAlign="center", backgroundColor="#ffffff", backgroundOpacity=84, backgroundPadding=14, backgroundRoundness=30)
pages.append(p)

# 3. Lineal + easing
p = page("effects-page-03-linear-easing", "Lineal + easing", "Misma máscara lineal: direcciones y curvas linear, ease-in, ease-out, smoothstep.", bg("#111827", fillMode="gradient", gradientStart="#111827", gradientEnd="#0f766e", gradientAngle=30), True)
directions = [("izq→der", 0, 50, 100, 50), ("arriba→abajo", 50, 0, 50, 100), ("diag ↘", 0, 0, 100, 100), ("diag ↗", 0, 100, 100, 0)]
easings = ["linear", "ease-in", "ease-out", "smoothstep"]
for r, (d, sx, sy, ex, ey) in enumerate(directions):
    y = 245 + r * 220
    tid = f"p3-dir-{r}"
    p["elementLayout"][tid] = txt_l(75, y + 74, 120, 18, color="#e0f2fe", fontWeight="bold", textAlign="right")
    p["customElements"][tid] = txt_e(tid, d, d)
    for c, ease in enumerate(easings):
        x = 220 + c * 200
        sid, lid = f"p3-lin-{r}-{c}", f"p3-lab-{r}-{c}"
        p["elementLayout"][sid] = shape_l(x, y, 150, 150, 30, fillMode="gradient", gradientStart="#facc15", gradientEnd="#fb7185", gradientAngle=45, opacity=100, border=True, contourWidth=2, contourColor="#ffffff", borderRadius=28, shadow=True, shadowPreset="soft", shadowColor="#000000", shadowOpacity=60, shadowBlur=26, transparencyType="linear", transparencyFadeOpacity=0, transparencyStartX=sx, transparencyStartY=sy, transparencyEndX=ex, transparencyEndY=ey, transparencyEasing=ease)
        p["customElements"][sid] = shape_e(sid, f"{d} {ease}", "rectangle")
        p["elementLayout"][lid] = txt_l(x - 12, y + 165, 174, 15, color="#cbd5e1", textAlign="center")
        p["customElements"][lid] = txt_e(lid, ease, ease)
pages.append(p)

# 4. Imágenes sobre fondos
p = page("effects-page-04-images-on-backgrounds", "Imágenes + transparencia", "Imagen encima de checker: flat, circle, ellipse y linear con tinte.", bg("#fefce8", fillMode="gradient", gradientStart="#fefce8", gradientEnd="#cffafe", gradientAngle=160))
cases = [("flat 80%", "flat", 0, 80, 0, {}), ("circle fade 0", "circle", 0, 100, 20, dict(transparencyRadius=62, transparencyCenterX=42, transparencyCenterY=42)), ("ellipse fade 20", "ellipse", 20, 100, 35, dict(transparencyRadiusX=92, transparencyRadiusY=42)), ("linear fade 0", "linear", 0, 100, 45, dict(transparencyStartX=0, transparencyStartY=0, transparencyEndX=100, transparencyEndY=100, transparencyEasing="smoothstep"))]
for i, (name, t, fade, op, tint, extra) in enumerate(cases):
    x, y = 105 + (i % 2) * 485, 260 + (i // 2) * 420
    bid, iid, tid = f"p4-check-{i}", f"p4-img-{i}", f"p4-label-{i}"
    p["elementLayout"][bid] = img_l(x, y, 380, 300, 5, src=CHECKER, borderRadius=28)
    p["customElements"][bid] = img_e(bid, "Checker inferior", CHECKER, 800, 800)
    p["elementLayout"][iid] = img_l(x + 38, y + 35, 304, 228, 30, src=PHOTO, imageCropScale=1.35, imageCropOffsetX=-0.25 if i % 2 else 0.15, imageCropOffsetY=0.05, imageTintColor="#581c87", imageTintStrength=tint, opacity=op, border=True, contourWidth=4, contourColor="#ffffff", borderRadiusTopLeft=42, borderRadiusTopRight=92, borderRadiusBottomRight=42, borderRadiusBottomLeft=92, shadow=True, shadowPreset="lifted", shadowColor="#0f172a", shadowOpacity=70, shadowBlur=42, transparencyType=t, transparencyFadeOpacity=fade, **extra)
    p["customElements"][iid] = img_e(iid, name, PHOTO)
    p["elementLayout"][tid] = txt_l(x, y + 322, 380, 20, color="#0f172a", fontWeight="bold", textAlign="center")
    p["customElements"][tid] = txt_e(tid, name, name)
pages.append(p)

# 5. Background image
p = page("effects-page-05-background-image", "Background image transparency", "Fondo real con imagen y máscara lineal + paneles que simulan variantes.", bg("#020617", fillMode="gradient", gradientStart="#020617", gradientEnd="#0c4a6e", gradientAngle=20, backgroundImageSrc=TEXTURE, backgroundImageWidth=1200, backgroundImageHeight=1200, backgroundImageCropScale=1.1, backgroundImageOpacity=62, backgroundImageTransparencyType="linear", backgroundImageTransparencyFadeOpacity=6, backgroundImageTransparencyStartX=0, backgroundImageTransparencyStartY=0, backgroundImageTransparencyEndX=100, backgroundImageTransparencyEndY=100, backgroundImageTransparencyEasing="smoothstep"), True)
variants = [("bg circle", "circle", dict(transparencyRadius=60, transparencyCenterX=52, transparencyCenterY=44)), ("bg ellipse", "ellipse", dict(transparencyRadiusX=92, transparencyRadiusY=40)), ("bg linear", "linear", dict(transparencyStartX=100, transparencyStartY=0, transparencyEndX=0, transparencyEndY=100)), ("bg flat 45%", "flat", {})]
for i, (name, t, extra) in enumerate(variants):
    x, y = 110 + (i % 2) * 460, 310 + (i // 2) * 350
    pid, iid, tid = f"p5-panel-{i}", f"p5-bgvariant-{i}", f"p5-label-{i}"
    p["elementLayout"][pid] = shape_l(x - 18, y - 18, 376, 276, 12, backgroundColor="#ffffff", opacity=18, borderRadius=32, border=True, contourWidth=2, contourColor="#bae6fd")
    p["customElements"][pid] = shape_e(pid, "Panel glass", "rectangle")
    p["elementLayout"][iid] = img_l(x, y, 340, 240, 25, src=TEXTURE, imageCropScale=1.2, opacity=45 if t == "flat" else 100, borderRadius=26, border=True, contourWidth=3, contourColor="#ffffff", transparencyType=t, transparencyFadeOpacity=0, transparencyEasing="smoothstep", **extra)
    p["customElements"][iid] = img_e(iid, name, TEXTURE, 1200, 1200)
    p["elementLayout"][tid] = txt_l(x, y + 260, 340, 19, color="#f8fafc", fontWeight="bold", textAlign="center")
    p["customElements"][tid] = txt_e(tid, name, name)
pages.append(p)

# 6. Formas
p = page("effects-page-06-shapes-combinations", "Formas combinadas", "Gradiente + transparencia + borde + sombra en clip-paths distintos.", bg("#f8fafc", fillMode="gradient", gradientStart="#ffffff", gradientEnd="#e0e7ff", gradientAngle=180))
shape_defs = [("diamond", "circle"), ("hexagon", "ellipse"), ("star-burst", "linear"), ("ribbon", "circle"), ("callout-cloud", "ellipse"), ("frame-thick", "linear"), ("arrow-double-h", "circle"), ("badge", "linear")]
for i, (kind, t) in enumerate(shape_defs):
    x, y = 105 + (i % 4) * 235, 285 + (i // 4) * 355
    sid, tid = f"p6-{kind}", f"p6-label-{i}"
    p["elementLayout"][sid] = shape_l(x, y, 170, 170, 30, fillMode="gradient", gradientStart=["#22c55e", "#06b6d4", "#f97316", "#ec4899"][i % 4], gradientEnd=["#14b8a6", "#a855f7", "#facc15", "#6366f1"][i % 4], gradientAngle=35 + i * 22, opacity=88, rotation=-10 + i * 5, border=True, borderStyle=["solid", "dashed", "dotted", "solid"][i % 4], contourWidth=5, contourColor="#0f172a", shadow=True, shadowPreset=["lifted", "soft", "echo", "hard"][i % 4], shadowColor="#334155", shadowOpacity=60, shadowBlur=34, transparencyType=t, transparencyFadeOpacity=25, transparencyRadius=72, transparencyRadiusX=84, transparencyRadiusY=45, transparencyStartX=0, transparencyStartY=0, transparencyEndX=100, transparencyEndY=100, transparencyEasing="smoothstep")
    p["customElements"][sid] = shape_e(sid, kind, kind)
    p["elementLayout"][tid] = txt_l(x - 10, y + 205, 190, 17, color="#0f172a", fontWeight="bold", textAlign="center")
    p["customElements"][tid] = txt_e(tid, f"{kind} / {t}", f"{kind} / {t}")
p["content"]["extra"] = "Borde + clip-path + gradiente + sombra + máscara en la misma forma."
p["elementLayout"]["extra"] = txt_l(120, 1080, 840, 24, color="#1e293b", fontWeight="bold", textAlign="center", backgroundColor="#ffffff", backgroundOpacity=86, backgroundPadding=18, backgroundRoundness=40)
pages.append(p)

# 7. Texto
p = page("effects-page-07-text-effects", "Texto + efectos", "Contorno, hueco, neón, sombra, fondo translúcido y máscaras aplicadas a texto.", bg("#111827", fillMode="gradient", gradientStart="#111827", gradientEnd="#581c87", gradientAngle=145), True)
text_cases = [
    ("OUTLINE + SHADOW", 46, dict(color="#ffffff", border=True, contourWidth=10, contourColor="#0f172a", shadow=True, shadowPreset="hard", shadowColor="#facc15", shadowOpacity=35)),
    ("HOLLOW TEXT", 58, dict(color="#67e8f9", hollowText=True, textEffectMode="hollow", border=True, contourWidth=18, contourColor="#67e8f9", shadow=True, shadowPreset="echo", shadowColor="#0891b2")),
    ("NEÓN + BACKGROUND", 44, dict(color="#ffffff", textEffectMode="neon", neonColor="#f0abfc", neonIntensity=95, backgroundColor="#701a75", backgroundOpacity=58, backgroundPadding=20, backgroundRoundness=80)),
    ("MASKED LINEAR TEXT", 42, dict(color="#fde68a", transparencyType="linear", transparencyFadeOpacity=5, transparencyStartX=0, transparencyStartY=50, transparencyEndX=100, transparencyEndY=50, transparencyEasing="smoothstep", shadow=True, shadowColor="#000", shadowBlur=28)),
    ("CIRCLE FADE TEXT", 42, dict(color="#f8fafc", transparencyType="circle", transparencyFadeOpacity=10, transparencyRadius=58, backgroundColor="#0e7490", backgroundOpacity=38, backgroundPadding=16, backgroundRoundness=50)),
]
for i, (txt, fs, opts) in enumerate(text_cases):
    tid = f"p7-text-{i}"
    p["elementLayout"][tid] = txt_l(110, 255 + i * 170, 860, fs, color=opts.pop("color"), fontWeight="bold", fontFamily="Poppins, sans-serif", textAlign="center", lineHeight=1.05, **opts)
    p["customElements"][tid] = txt_e(tid, txt, txt)
pages.append(p)

# 8. Capas
p = page("effects-page-08-layering", "Capas y solapes", "Opacidades acumuladas, z-index, sombras y máscaras en objetos superpuestos.", bg("#f1f5f9", fillMode="gradient", gradientStart="#f8fafc", gradientEnd="#bae6fd", gradientAngle=160))
p["elementLayout"]["p8-grid"] = img_l(120, 245, 840, 730, 5, src=CHECKER, borderRadius=34, opacity=70)
p["customElements"]["p8-grid"] = img_e("p8-grid", "Grid de referencia", CHECKER, 800, 800)
for i in range(9):
    sid = f"p8-layer-{i}"
    p["elementLayout"][sid] = shape_l(190 + (i % 3) * 205, 320 + (i // 3) * 175, 230, 150, 20 + i, fillMode="gradient", gradientStart=["#ef4444", "#22c55e", "#3b82f6"][i % 3], gradientEnd=["#f97316", "#14b8a6", "#a855f7"][i % 3], gradientAngle=45 + i * 15, opacity=58 + i * 4, rotation=-12 + i * 3, border=True, contourWidth=3, contourColor="#ffffff", borderRadius=26, shadow=True, shadowPreset="soft", shadowColor="#0f172a", shadowOpacity=55, shadowBlur=28, transparencyType=["flat", "circle", "linear"][i % 3], transparencyFadeOpacity=25, transparencyRadius=70, transparencyStartX=0, transparencyStartY=0, transparencyEndX=100, transparencyEndY=100)
    p["customElements"][sid] = shape_e(sid, f"z {20+i}", ["rectangle", "circle", "hexagon"][i % 3])
p["elementLayout"]["p8-front-label"] = txt_l(225, 1020, 630, 28, color="#0f172a", fontWeight="bold", textAlign="center", backgroundColor="#ffffff", backgroundOpacity=88, backgroundPadding=18, backgroundRoundness=48)
p["customElements"]["p8-front-label"] = txt_e("p8-front-label", "Etiqueta frontal", "Etiqueta frontal: debe quedar por encima")
pages.append(p)

# 9. Crop/flip/tint
p = page("effects-page-09-image-crop-flip", "Imagen: crop, flip, tinte", "Recorte, desplazamiento, flip X/Y, tinte y transparencia combinados.", bg("#020617", fillMode="gradient", gradientStart="#020617", gradientEnd="#164e63", gradientAngle=30), True)
img_cases = [("normal + tint", False, False, 1.15, 0, 0, "flat"), ("crop left", False, False, 1.9, -.55, .05, "circle"), ("crop right", False, False, 1.9, .55, -.05, "ellipse"), ("flip X + linear", True, False, 1.35, .1, .1, "linear"), ("flip Y + circle", False, True, 1.35, -.1, -.15, "circle"), ("flip XY + ellipse", True, True, 1.6, .35, .22, "ellipse")]
for i, (name, fx, fy, scale, ox, oy, t) in enumerate(img_cases):
    x, y = 105 + (i % 3) * 310, 270 + (i // 3) * 400
    iid, tid = f"p9-img-{i}", f"p9-label-{i}"
    src = PHOTO if i % 2 == 0 else PORTRAIT
    p["elementLayout"][iid] = img_l(x, y, 245, 255, 30, src=src, imageCropScale=scale, imageCropOffsetX=ox, imageCropOffsetY=oy, flipX=fx, flipY=fy, imageTintColor=["#0f172a", "#581c87", "#064e3b"][i % 3], imageTintStrength=25 + i * 8, opacity=96, border=True, contourWidth=4, contourColor="#e0f2fe", borderRadiusTopLeft=28, borderRadiusTopRight=84, borderRadiusBottomRight=28, borderRadiusBottomLeft=84, shadow=True, shadowPreset="lifted", shadowColor="#000000", shadowOpacity=70, shadowBlur=44, transparencyType=t, transparencyFadeOpacity=18, transparencyRadius=72, transparencyRadiusX=86, transparencyRadiusY=48, transparencyStartX=0, transparencyStartY=0, transparencyEndX=100, transparencyEndY=100, transparencyEasing="smoothstep")
    p["customElements"][iid] = img_e(iid, name, src)
    p["elementLayout"][tid] = txt_l(x - 15, y + 285, 275, 18, color="#f8fafc", fontWeight="bold", textAlign="center")
    p["customElements"][tid] = txt_e(tid, name, name)
pages.append(p)

# 10. Stress final
p = page("effects-page-10-stress-final", "Stress final", "Combinación máxima: fondo, imagen, QR, formas, texto y linkedText.", bg("#111827", fillMode="gradient", gradientStart="#111827", gradientEnd="#7c2d12", gradientAngle=140, backgroundImageSrc=TEXTURE, backgroundImageWidth=1200, backgroundImageHeight=1200, backgroundImageCropScale=1.25, backgroundImageOpacity=36, backgroundImageTransparencyType="ellipse", backgroundImageTransparencyFadeOpacity=5, backgroundImageTransparencyCenterX=62, backgroundImageTransparencyCenterY=38, backgroundImageTransparencyRadiusX=95, backgroundImageTransparencyRadiusY=52), True)
p["elementLayout"]["p10-glass"] = shape_l(100, 210, 880, 930, 8, backgroundColor="#ffffff", opacity=13, borderRadius=46, border=True, contourWidth=3, contourColor="#fed7aa", shadow=True, shadowPreset="lifted", shadowColor="#000", shadowOpacity=70, shadowBlur=60)
p["customElements"]["p10-glass"] = shape_e("p10-glass", "Glass panel", "rectangle")
p["elementLayout"]["p10-photo"] = img_l(575, 330, 325, 390, 25, src=PORTRAIT, imageCropScale=1.3, imageCropOffsetX=.15, imageCropOffsetY=-.08, imageTintColor="#7c2d12", imageTintStrength=28, opacity=94, rotation=-3, border=True, contourWidth=4, contourColor="#fff7ed", borderRadiusTopLeft=44, borderRadiusTopRight=120, borderRadiusBottomRight=44, borderRadiusBottomLeft=120, shadow=True, shadowPreset="lifted", shadowColor="#000", shadowOpacity=72, shadowBlur=48, transparencyType="ellipse", transparencyFadeOpacity=16, transparencyRadiusX=88, transparencyRadiusY=55)
p["customElements"]["p10-photo"] = img_e("p10-photo", "Foto stress", PORTRAIT)
p["elementLayout"]["p10-star"] = shape_l(705, 760, 210, 210, 35, fillMode="gradient", gradientStart="#facc15", gradientEnd="#f97316", gradientAngle=30, opacity=76, rotation=13, border=True, borderStyle="dashed", contourWidth=4, contourColor="#fff", shadow=True, shadowPreset="echo", shadowColor="#7c2d12", transparencyType="circle", transparencyFadeOpacity=25)
p["customElements"]["p10-star"] = shape_e("p10-star", "Star stress", "star-6")
p["elementLayout"]["p10-qr"] = img_l(780, 965, 132, 132, 50, backgroundColor="#ffffff", borderRadius=18, border=True, contourWidth=3, contourColor="#0f172a", rotation=2)
p["customElements"]["p10-qr"] = dict(id="p10-qr", type="qr", label="QR stress", url="https://example.test/tseyor-canva/qa-effects", qrDataUrl=QR)
p["elementLayout"]["p10-headline"] = txt_l(145, 305, 410, 56, color="#ffffff", fontWeight="bold", fontFamily="Poppins, sans-serif", uppercase=True, lineHeight=.95, textEffectMode="neon", neonColor="#facc15", neonIntensity=85, border=True, contourWidth=10, contourColor="#111827", shadow=True, shadowPreset="hard", shadowColor="#7c2d12", shadowOpacity=35)
p["customElements"]["p10-headline"] = txt_e("p10-headline", "Headline stress", "TODO JUNTO")
html = '<p><strong>LinkedText stress:</strong> gradientes, imágenes, máscaras, QR, formas y texto deben convivir sin perder estilos. <span style="color:#facc15">Amarillo</span>, <span style="color:#38bdf8">azul</span>, <em>cursiva</em> y negrita.</p><p style="text-align:justify">Este párrafo justificado comprueba distribución, espacios y recortes dentro de cajas enlazadas.</p>'
for i, (eid, x, y, nxt, prv) in enumerate([("p10-link-a", 145, 520, "p10-link-b", None), ("p10-link-b", 145, 700, "p10-link-c", "p10-link-a"), ("p10-link-c", 145, 880, None, "p10-link-b")]):
    p["elementLayout"][eid] = txt_l(x, y, 360, 21, h=125, color="#ffffff", lineHeight=1.24, backgroundColor="#020617", backgroundOpacity=42, backgroundPadding=13, backgroundRoundness=28, border=True, borderStyle="dotted", contourWidth=2, contourColor="#facc15", linkedTextGroupId="effects-stress-linked", linkedTextPrev=prv, linkedTextNext=nxt, linkedTextChainIndex=i)
    p["customElements"][eid] = linked_e(eid, f"Linked stress {i+1}", html if i == 0 else "")
pages.append(p)


normalization_report = normalize_pages_to_safe_area(pages)
first = pages[0]
snapshot = dict(
    tcVersion=2,
    format="vertical",
    size="1080 × 1350 px",
    designSurface=dict(width=W, height=H),
    designTitle="QA visual · matriz rigurosa de efectos",
    designTitleManual=True,
    objective="generic",
    outputType="digital",
    pages=pages,
    content=first["content"],
    elementLayout=first["elementLayout"],
    customElements=first["customElements"],
    userUploadedImages=[],
    workingDocumentPageId=first["id"],
)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{OUT.as_posix()} | {OUT.stat().st_size} bytes | {len(pages)} pages")
for page_id, bounds in normalization_report:
    print(f"{page_id}: visual_bounds={tuple(round(v, 1) for v in bounds)}")
