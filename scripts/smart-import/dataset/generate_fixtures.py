"""
Generate 7 synthetic test images for the Smart Import Calibration Pipeline.

Each image covers a distinct visual case as specified in the SDD spec
(smart-import-pipeline/spec.md §1). Uses Pillow drawing primitives only
— no external assets required.

Features:
  - Realistic synthetic "photo" content (gradient patterns, shapes)
  - Text overlaid ON images with drop shadows
  - Gradient/transparency overlays over image areas
  - Semi-transparent elements composited over backgrounds

Usage:
    python generate_fixtures.py [--output-dir DIR] [--quality N]

Output: 7 JPEG files in the specified directory (default: dataset/)
"""

import argparse
import hashlib
import math
import os
import platform
import random as _random
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

# ── Colour palette ──────────────────────────────────────────────────

C_DARK_BLUE = (26, 35, 126)
C_WHITE = (255, 255, 255)
C_LIGHT_GRAY = (232, 232, 232)
C_MED_GRAY = (180, 180, 180)
C_DARK_GRAY = (80, 80, 80)
C_NEARLY_WHITE = (248, 249, 250)
C_PURPLE = (124, 58, 237)
C_PINK = (236, 72, 153)
C_TEAL = (13, 148, 136)
C_ORANGE = (234, 88, 12)
C_AMBER = (251, 146, 60)
C_ALMOST_BLACK = (17, 24, 39)
C_WARM_GRAY_BG = (240, 240, 235)
C_LOW_CONTRAST_TEXT = (192, 192, 192)
C_GOLD = (234, 179, 8)
C_SOFT_BLUE = (59, 130, 246)
C_CREAM = (255, 253, 240)

# ── Font lookup ──────────────────────────────────────────────────────

_FONT_CACHE: dict[tuple[int, bool], ImageFont.FreeTypeFont] = {}


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    weight = "Bold" if bold else "Regular"
    weight_abbr = "bd" if bold else "r"

    candidates: list[str] = []
    if platform.system() == "Windows":
        windir = os.environ.get("WINDIR", "C:\\Windows")
        candidates = [
            os.path.join(windir, "Fonts", f"Arial{weight_abbr}.ttf"),
            os.path.join(windir, "Fonts", "Arial.ttf"),
            os.path.join(windir, "Fonts", "SegoeUI.ttf"),
        ]
    elif platform.system() == "Darwin":
        candidates = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
        ]
    else:
        candidates = [
            f"/usr/share/fonts/truetype/dejavu/DejaVuSans-{weight}.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            f"/usr/share/fonts/truetype/liberation/LiberationSans-{weight}.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]

    for path in candidates:
        if os.path.isfile(path):
            try:
                font = ImageFont.truetype(path, size)
                _FONT_CACHE[key] = font
                return font
            except Exception:
                continue

    font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


# ── Drawing helpers ──────────────────────────────────────────────────


def _draw_gradient(draw, x1, y1, x2, y2, color_start, color_end, vertical=True):
    steps = abs(y2 - y1) if vertical else abs(x2 - x1)
    for i in range(steps):
        ratio = i / max(steps - 1, 1)
        r = int(color_start[0] + (color_end[0] - color_start[0]) * ratio)
        g = int(color_start[1] + (color_end[1] - color_start[1]) * ratio)
        b = int(color_start[2] + (color_end[2] - color_start[2]) * ratio)
        color = (r, g, b)
        if vertical:
            draw.line([(x1, y1 + i), (x2, y1 + i)], fill=color, width=1)
        else:
            draw.line([(x1 + i, y1), (x1 + i, y2)], fill=color, width=1)


def _draw_rounded_rect(draw, bbox, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline, width=width)


def _draw_text_with_shadow(draw, pos, text, font, fill, shadow_color=(0, 0, 0), shadow_offset=(3, 3)):
    """Draw text with a drop shadow behind it — works over any background."""
    sx, sy = pos
    ox, oy = shadow_offset
    draw.text((sx + ox, sy + oy), text, fill=shadow_color, font=font)
    draw.text((sx, sy), text, fill=fill, font=font)


# ── Real photo download with cache ─────────────────────────────────


_PHOTO_CACHE_DIR: Path | None = None


def _photo_cache_dir() -> Path:
    global _PHOTO_CACHE_DIR
    if _PHOTO_CACHE_DIR is None:
        _PHOTO_CACHE_DIR = Path(__file__).resolve().parent / ".photo_cache"
        _PHOTO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _PHOTO_CACHE_DIR


def _get_photo(w: int, h: int, seed: str = "1") -> Image.Image:
    """Download a real photo from picsum.photos, cached locally.

    Falls back to a synthetic abstract pattern on any network error.
    """
    cache_dir = _photo_cache_dir()
    cache_key = f"picsum_{seed}_{w}x{h}.jpg"
    cache_path = cache_dir / cache_key

    if cache_path.exists():
        try:
            return Image.open(cache_path).copy()
        except Exception:
            pass

    url = f"https://picsum.photos/seed/{seed}/{w}/{h}"
    try:
        print(f"    Downloading {url} ...", end=" ")
        req = urllib.request.Request(url, headers={"User-Agent": "TseyorCanva/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        with open(cache_path, "wb") as f:
            f.write(data)
        img = Image.open(cache_path).copy()
        # Resize to exact requested size (picsum sometimes returns slightly different)
        if img.size != (w, h):
            img = img.resize((w, h), Image.LANCZOS)
            img.save(cache_path, "JPEG", quality=90)
        print("done")
        return img
    except Exception as exc:
        print(f"failed ({exc}) — using fallback")
        return _get_photo_fallback(w, h, int(hashlib.md5(seed.encode()).hexdigest()[:8], 16))


def _get_photo_fallback(w: int, h: int, seed_int: int = 0) -> Image.Image:
    """Synthetic pattern fallback when download fails."""
    rng = _random.Random(seed_int)
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    colors = [
        (rng.randint(40, 220), rng.randint(40, 220), rng.randint(40, 220)),
        (rng.randint(40, 220), rng.randint(40, 220), rng.randint(40, 220)),
        (rng.randint(40, 220), rng.randint(40, 220), rng.randint(40, 220)),
    ]
    band_h = h // 5
    for i in range(5):
        c = colors[i % len(colors)]
        y0 = i * band_h
        y1 = (i + 1) * band_h
        for y in range(y0, min(y1, h)):
            t = (y - y0) / max(band_h, 1)
            r = int(c[0] + (colors[(i + 1) % len(colors)][0] - c[0]) * t)
            g = int(c[1] + (colors[(i + 1) % len(colors)][1] - c[1]) * t)
            b = int(c[2] + (colors[(i + 1) % len(colors)][2] - c[2]) * t)
            draw.line([(0, y), (w, y)], fill=(r, g, b), width=1)
    for _ in range(rng.randint(3, 6)):
        cx = rng.randint(0, w)
        cy = rng.randint(0, h)
        rx = rng.randint(w // 8, w // 3)
        ry = rng.randint(h // 8, h // 3)
        alpha = rng.randint(30, 80)
        blob = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        bdraw = ImageDraw.Draw(blob)
        bdraw.ellipse(
            [cx - rx, cy - ry, cx + rx, cy + ry],
            fill=(rng.randint(100, 255), rng.randint(100, 255), rng.randint(100, 255), alpha),
        )
        img = Image.alpha_composite(img.convert("RGBA"), blob).convert("RGB")
    return img


# ── Image builders ──────────────────────────────────────────────────


def build_poster_simple(size=(1080, 1350)):
    """Poster with synthetic photo, gradient overlay over image, text on top."""
    w, h = size
    img = Image.new("RGB", size, C_DARK_BLUE)
    draw = ImageDraw.Draw(img)

    F_TITLE = _get_font(96, bold=True)
    F_SUB = _get_font(42)
    F_OVERLAY_TEXT = _get_font(36, bold=True)
    F_LABEL = _get_font(28)

    title = "SUMMER FEST"
    _, _, tw, th = draw.textbbox((0, 0), title, font=F_TITLE)
    tx = (w - tw) / 2
    ty = h * 0.08
    _draw_text_with_shadow(draw, (tx, ty), title, F_TITLE, fill=C_WHITE, shadow_color=(0, 0, 30))

    sub = "AUGUST 15-17 · CENTRAL PARK"
    _, _, sw, sh = draw.textbbox((0, 0), sub, font=F_SUB)
    draw.text(((w - sw) / 2, ty + th + 30), sub, fill=(180, 200, 255), font=F_SUB)

    # Photo area with synthetic content
    photo_x, photo_y = int(w * 0.1), int(h * 0.35)
    photo_w, photo_h = int(w * 0.8), int(h * 0.55)
    photo = _get_photo(photo_w, photo_h, seed="poster-simple")
    img.paste(photo, (photo_x, photo_y))

    # Semi-transparent dark gradient overlay at bottom of photo
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    grad_height = photo_h // 2
    for i in range(grad_height):
        alpha = int(180 * (1 - i / grad_height))
        odraw.line(
            [(photo_x, photo_y + photo_h - grad_height + i), (photo_x + photo_w, photo_y + photo_h - grad_height + i)],
            fill=(0, 0, 0, alpha), width=1,
        )
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Text on top of the photo (bottom-left area)
    overlay_label = "Main Stage · Live Music"
    _, _, ltw, lth = draw.textbbox((0, 0), overlay_label, font=F_OVERLAY_TEXT)
    lx = photo_x + 30
    ly = photo_y + photo_h - grad_height + 20
    _draw_text_with_shadow(
        draw, (lx, ly), overlay_label, F_OVERLAY_TEXT,
        fill=C_WHITE, shadow_color=(0, 0, 0),
    )

    # Small badge on top-right of photo
    badge = "NOW ON SALE"
    _, _, bw, bh = draw.textbbox((0, 0), badge, font=F_LABEL)
    bx = photo_x + photo_w - bw - 20
    by = photo_y + 15
    _draw_rounded_rect(draw, (bx - 8, by - 4, bx + bw + 8, by + bh + 4), radius=6, fill=(234, 179, 8, 220))
    draw.text((bx, by), badge, fill=C_ALMOST_BLACK, font=F_LABEL)

    return img


def build_poster_gradient(size=(1080, 1350)):
    """Gradient bg + circular product photo with overlay + text over photo."""
    w, h = size
    img = Image.new("RGB", size, (0, 0, 0))
    draw = ImageDraw.Draw(img)

    F_TITLE = _get_font(96, bold=True)
    F_SUB = _get_font(42)
    F_OVERLAY = _get_font(38, bold=True)
    F_CTA = _get_font(40, bold=True)

    _draw_gradient(draw, 0, 0, w, h, C_PURPLE, C_PINK)

    title = "NEW COLLECTION"
    _, _, tw, th = draw.textbbox((0, 0), title, font=F_TITLE)
    draw.text(((w - tw) / 2, h * 0.06), title, fill=C_WHITE, font=F_TITLE)

    sub = "Spring 2026 · Limited Edition"
    _, _, sw, sh = draw.textbbox((0, 0), sub, font=F_SUB)
    draw.text(((w - sw) / 2, h * 0.06 + th + 20), sub, fill=(220, 200, 255), font=F_SUB)

    # Circular synthetic product photo
    cx, cy = w // 2, int(h * 0.54)
    radius = int(min(w, h) * 0.22)
    photo_size = radius * 2
    photo = _get_photo(photo_size, photo_size, seed="poster-gradient")
    # Mask to circle
    mask = Image.new("L", (photo_size, photo_size), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.ellipse([0, 0, photo_size, photo_size], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(2))
    # Paste with mask
    img.paste(photo, (cx - radius, cy - radius), mask)

    # Semi-transparent ring/overlay on the circle
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    # Gradient overlay from bottom of the circle region
    cy_top = cy - radius + photo_size - photo_size // 3
    for i in range(photo_size // 3):
        alpha = int(140 * (1 - i / (photo_size // 3)))
        odraw.line(
            [(cx - radius, cy_top + i), (cx + radius, cy_top + i)],
            fill=(80, 0, 120, alpha), width=1,
        )
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Text INSIDE the circle — over the photo
    inside_text = "EXCLUSIVE"
    _, _, itw, ith = draw.textbbox((0, 0), inside_text, font=F_OVERLAY)
    _draw_text_with_shadow(
        draw,
        (cx - itw // 2, cy - ith // 2),
        inside_text, F_OVERLAY,
        fill=C_WHITE, shadow_color=(60, 0, 90),
    )

    # Ring border
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        outline=(255, 255, 255, 60), width=3,
    )

    cta = "SHOP NOW →"
    _, _, cw, ch = draw.textbbox((0, 0), cta, font=F_CTA)
    draw.text(((w - cw) / 2, int(h * 0.88)), cta, fill=(255, 230, 250), font=F_CTA)

    return img


def build_flyer_text_heavy(size=(1080, 1350)):
    """Text-heavy flyer with background image + semi-transparent overlay for readability."""
    w, h = size

    # Background: synthetic abstract pattern
    bg_img = _get_photo(w, h, seed="flyer-bg")
    # Dark overlay so text is readable
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 160))
    bg_img = Image.alpha_composite(bg_img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(bg_img)

    F_HEADER = _get_font(72, bold=True)
    F_SUB = _get_font(40)
    F_BODY = _get_font(34)
    F_LABEL = _get_font(22)
    F_FOOTER = _get_font(32, bold=True)

    # Top accent bar (semi-transparent)
    bar = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(bar)
    bdraw.rectangle([(0, 0), (w, 8)], fill=(59, 130, 246, 200))
    bg_img = Image.alpha_composite(bg_img.convert("RGBA"), bar).convert("RGB")
    draw = ImageDraw.Draw(bg_img)

    header = "COMMUNITY MEETUP"
    _, _, hw, hh = draw.textbbox((0, 0), header, font=F_HEADER)
    draw.text(((w - hw) / 2, 40), header, fill=C_WHITE, font=F_HEADER)

    sub = "Tech & Innovation Summit 2026"
    _, _, sw, sh = draw.textbbox((0, 0), sub, font=F_SUB)
    draw.text(((w - sw) / 2, 40 + hh + 15), sub, fill=(200, 210, 255), font=F_SUB)

    div_y = 40 + hh + 15 + sh + 20
    draw.line([(int(w * 0.2), div_y), (int(w * 0.8), div_y)], fill=(59, 130, 246, 200), width=2)

    blocks = [
        ("📅 Date: June 15, 2026", "When"),
        ("📍 Venue: Grand Hall, Downtown", "Where"),
        ("⏰ Time: 9:00 AM - 6:00 PM", "Time"),
        ("🎤 Keynote: Future of AI", "Talk 1"),
        ("🛠 Workshops: Hands-on sessions", "Talk 2"),
        ("🤝 Networking: Meet the speakers", "Talk 3"),
        ("🎟 Register: community-meetup.io", "CTA"),
    ]

    block_y = div_y + 35
    for text, _label in blocks:
        _, _, tw, th = draw.textbbox((0, 0), text, font=F_BODY)
        draw.text((int(w * 0.15), block_y), text, fill=C_WHITE, font=F_BODY)

        _, _, lw, lh = draw.textbbox((0, 0), _label, font=F_LABEL)
        draw.text(
            (int(w * 0.15) + tw + 15, block_y + 6),
            f"[{_label}]",
            fill=(180, 190, 220),
            font=F_LABEL,
        )
        block_y += th + 18

    # Bottom bar (semi-transparent)
    bottom_bar = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bbdraw = ImageDraw.Draw(bottom_bar)
    bbdraw.rectangle([(0, h - 60), (w, h)], fill=(59, 130, 246, 200))
    bg_img = Image.alpha_composite(bg_img.convert("RGBA"), bottom_bar).convert("RGB")
    draw = ImageDraw.Draw(bg_img)

    footer = "Free entry · Register now!"
    _, _, fw, fh = draw.textbbox((0, 0), footer, font=F_FOOTER)
    draw.text(((w - fw) / 2, h - 42), footer, fill=C_WHITE, font=F_FOOTER)

    return bg_img


def build_poster_person(size=(1080, 1080)):
    """Square post: real person photo + gradient overlay + title ON image."""
    w, h = size

    F_TITLE = _get_font(72, bold=True)
    F_META = _get_font(36)
    F_BADGE = _get_font(48)
    F_TAG = _get_font(28, bold=True)

    img = Image.new("RGB", size, C_TEAL)
    draw = ImageDraw.Draw(img)

    # Decorative background circles
    draw.ellipse([-100, -100, 300, 300], fill=(11, 118, 108), width=0)
    draw.ellipse([w - 250, h - 250, w + 50, h + 50], fill=(11, 118, 108), width=0)
    draw.ellipse([w // 2 - 200, h // 2 - 200, w // 2 + 200, h // 2 + 200], fill=(10, 128, 118), width=0)

    # Real person photo (centred, circular mask)
    photo_size = int(min(w, h) * 0.45)
    person_photo = _get_photo(photo_size, photo_size, seed="person-profile-photo")
    mask = Image.new("L", (photo_size, photo_size), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.ellipse([0, 0, photo_size, photo_size], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(2))
    img.paste(person_photo, ((w - photo_size) // 2, int(h * 0.08)), mask)

    # Semi-transparent gradient overlay from bottom half
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    grad_start = int(h * 0.50)
    for i in range(h - grad_start):
        alpha = int(160 * (i / (h - grad_start)))
        odraw.line([(0, grad_start + i), (w, grad_start + i)], fill=(0, 0, 0, alpha), width=1)
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Title — over the gradient overlay (bottom area)
    title = "JANE DOE"
    _, _, tw, th = draw.textbbox((0, 0), title, font=F_TITLE)
    _draw_text_with_shadow(
        draw, ((w - tw) / 2, int(h * 0.68)),
        title, F_TITLE, fill=C_WHITE,
    )

    meta = "@janedoe · 12k followers"
    _, _, mw, mh = draw.textbbox((0, 0), meta, font=F_META)
    _draw_text_with_shadow(
        draw, ((w - mw) / 2, int(h * 0.68) + th + 15),
        meta, F_META, fill=(200, 240, 230),
    )

    badge = "✓"
    _, _, bw, bh = draw.textbbox((0, 0), badge, font=F_BADGE)
    bx = (w + tw) // 2 + 30
    _draw_text_with_shadow(draw, (bx, int(h * 0.68)), badge, F_BADGE, fill=C_GOLD)

    # Badge tag top-left (semi-transparent)
    tag = "FEATURED"
    _, _, tagw, tagh = draw.textbbox((0, 0), tag, font=F_TAG)
    tag_badge = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(tag_badge)
    tdraw.rounded_rectangle([20, 20, 20 + tagw + 24, 20 + tagh + 12], radius=6, fill=(234, 179, 8, 200))
    tdraw.text((32, 26), tag, fill=C_ALMOST_BLACK, font=F_TAG)
    img = Image.alpha_composite(img.convert("RGBA"), tag_badge).convert("RGB")

    return img


def build_banner_horizontal(size=(1920, 1080)):
    """Horizontal banner: product photo + gradient overlay + text ON image."""
    w, h = size

    F_TITLE = _get_font(120, bold=True)
    F_SUB = _get_font(56)
    F_DETAIL = _get_font(34)
    F_CTA = _get_font(40, bold=True)
    F_BADGE = _get_font(32, bold=True)

    img = Image.new("RGB", size, (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Left half: gradient
    _draw_gradient(draw, 0, 0, w // 2, h, C_ORANGE, C_AMBER, vertical=False)

    # Right half: synthetic product photo
    photo_x = w // 2
    photo_w = w // 2
    photo = _get_photo(photo_w, h, seed="banner-product")
    img.paste(photo, (photo_x, 0))

    # Dark gradient overlay on the photo side (from left edge of photo)
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    grad_w = photo_w // 3
    for i in range(grad_w):
        alpha = int(200 * (1 - i / grad_w))
        odraw.line([(photo_x + i, 0), (photo_x + i, h)], fill=(0, 0, 0, alpha), width=1)
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Text on the left (gradient side)
    title = "SALE"
    _, _, tw, th = draw.textbbox((0, 0), title, font=F_TITLE)
    _draw_text_with_shadow(draw, (int(w * 0.06), int(h * 0.18)), title, F_TITLE, fill=C_WHITE)

    sub = "UP TO 50% OFF"
    _, _, sw, sh = draw.textbbox((0, 0), sub, font=F_SUB)
    _draw_text_with_shadow(draw, (int(w * 0.06), int(h * 0.18) + th + 15), sub, F_SUB, fill=C_CREAM)

    detail = "Limited time · Select items"
    _, _, dw, dh = draw.textbbox((0, 0), detail, font=F_DETAIL)
    draw.text((int(w * 0.06), int(h * 0.18) + th + sh + 25), detail, fill=(255, 220, 180), font=F_DETAIL)

    # CTA button
    cta = "SHOP NOW  →"
    _, _, cw, ch = draw.textbbox((0, 0), cta, font=F_CTA)
    btn_x, btn_y = int(w * 0.06), int(h * 0.65)
    btn_w, btn_h = cw + 40, ch + 20
    _draw_rounded_rect(draw, (btn_x, btn_y, btn_x + btn_w, btn_y + btn_h), radius=8, fill=C_DARK_BLUE)
    draw.text((btn_x + 20, btn_y + 10), cta, fill=C_WHITE, font=F_CTA)

    # Badge over the photo area (top-right)
    badge_txt = "NEW ARRIVAL"
    _, _, badw, badh = draw.textbbox((0, 0), badge_txt, font=F_BADGE)
    bx = photo_x + 20
    by = 25
    _draw_rounded_rect(draw, (bx, by, bx + badw + 20, by + badh + 12), radius=6, fill=(234, 179, 8, 220))
    draw.text((bx + 10, by + 6), badge_txt, fill=C_ALMOST_BLACK, font=F_BADGE)

    # Text overlay on the photo side
    photo_label = "Premium Collection"
    pl_font = _get_font(42, bold=True)
    _, _, plw, plh = draw.textbbox((0, 0), photo_label, font=pl_font)
    _draw_text_with_shadow(
        draw,
        (photo_x + (photo_w - plw) // 2, h - 80),
        photo_label, pl_font,
        fill=C_WHITE,
    )

    return img


def build_poster_display_font(size=(1080, 1350)):
    """Display typography over abstract artistic image with dark overlay."""
    w, h = size

    # Background: synthetic abstract pattern
    bg = _get_photo(w, h, seed="display-bg")
    # Dark overlay
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 160))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(bg)

    F_STAR = _get_font(28)
    F_MAIN = _get_font(120, bold=True)
    F_SUB = _get_font(44)

    # Subtle radial-like effect
    cx, cy = w // 2, h // 2
    for r in range(0, max(w, h), 30):
        alpha = max(0, 120 - r)
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=(255, 255, 200, alpha),
            width=1,
        )

    # Decorative stars
    stars = [(120, 150), (w - 150, 200), (200, h - 180), (w - 180, h - 250), (w // 2, 80), (w // 2 + 100, h - 150)]
    for sx, sy in stars:
        draw.text((sx, sy), "✦", fill=C_GOLD, font=F_STAR)

    for dx, dy in [(80, 400), (w - 100, 500), (150, h - 300), (w - 120, h - 400), (w // 3, 700), (2 * w // 3, 800)]:
        draw.ellipse([dx - 4, dy - 4, dx + 4, dy + 4], fill=C_GOLD)

    draw.line([(int(w * 0.15), int(h * 0.40)), (int(w * 0.40), int(h * 0.40))], fill=C_GOLD, width=2)
    draw.line([(int(w * 0.60), int(h * 0.40)), (int(w * 0.85), int(h * 0.40))], fill=C_GOLD, width=2)
    draw.line([(int(w * 0.15), int(h * 0.65)), (int(w * 0.40), int(h * 0.65))], fill=C_GOLD, width=2)
    draw.line([(int(w * 0.60), int(h * 0.65)), (int(w * 0.85), int(h * 0.65))], fill=C_GOLD, width=2)

    display_text = "DREAM"
    _, _, dw, dh = draw.textbbox((0, 0), display_text, font=F_MAIN)
    _draw_text_with_shadow(
        draw, ((w - dw) / 2, int(h * 0.42)),
        display_text, F_MAIN, fill=C_WHITE,
        shadow_color=(60, 40, 20),
    )

    underline_y = int(h * 0.42) + dh + 20
    draw.line([(int(w * 0.25), underline_y), (int(w * 0.75), underline_y)], fill=C_GOLD, width=2)

    sub = "BIG · BOLD · BEAUTIFUL"
    _, _, sw, sh = draw.textbbox((0, 0), sub, font=F_SUB)
    _draw_text_with_shadow(
        draw, ((w - sw) / 2, underline_y + 20),
        sub, F_SUB, fill=C_MED_GRAY,
        shadow_color=(10, 10, 10),
    )

    return bg


def build_poster_low_contrast(size=(1080, 1350)):
    """Low contrast design — kept as-is, adding an image would defeat the purpose."""
    w, h = size

    F_TITLE = _get_font(72, bold=True)
    F_SUB = _get_font(38)
    F_BODY = _get_font(30)
    F_META = _get_font(26)

    bg = Image.new("RGB", size, C_LIGHT_GRAY)
    _random.seed(42)
    pixels = bg.load()
    for _ in range(5000):
        px = _random.randint(0, w - 1)
        py = _random.randint(0, h - 1)
        r, g, b = pixels[px, py]
        delta = _random.randint(-8, 8)
        pixels[px, py] = (
            max(0, min(255, r + delta)),
            max(0, min(255, g + delta)),
            max(0, min(255, b + delta)),
        )

    draw = ImageDraw.Draw(bg)
    draw.rectangle([(10, 10), (w - 10, h - 10)], outline=(220, 220, 220), width=1)

    title = "Whisper Collection"
    _, _, tw, th = draw.textbbox((0, 0), title, font=F_TITLE)
    draw.text(((w - tw) / 2, int(h * 0.08)), title, fill=C_LOW_CONTRAST_TEXT, font=F_TITLE)

    sub = "barely visible elegance"
    _, _, sw, sh = draw.textbbox((0, 0), sub, font=F_SUB)
    draw.text(((w - sw) / 2, int(h * 0.08) + th + 15), sub, fill=(200, 200, 200), font=F_SUB)

    div_y = int(h * 0.08) + th + sh + 30
    draw.line([(int(w * 0.15), div_y), (int(w * 0.85), div_y)], fill=(215, 215, 215), width=1)

    body_texts = [
        "This design explores the boundaries",
        "of visual perception through minimal",
        "contrast ratios. Every element sits",
        "close to the background value,",
        "creating a subtle, almost ethereal",
        "aesthetic that rewards close looking.",
        "",
        "— Design Philosophy, 2026",
    ]

    by = div_y + 30
    for line in body_texts:
        _, _, lw, lh = draw.textbbox((0, 0), line, font=F_BODY)
        draw.text(((w - lw) / 2, by), line, fill=C_LOW_CONTRAST_TEXT, font=F_BODY)
        by += lh + 6

    meta = "www.whisper-design.studio · @whisper"
    _, _, mw, mh = draw.textbbox((0, 0), meta, font=F_META)
    draw.text(((w - mw) / 2, int(h * 0.88)), meta, fill=(195, 195, 195), font=F_META)

    return bg


# ── New: multi-photo recognition images ──────────────────────────────


def _draw_face(draw, cx, cy, scale=1.0, skin_color=(220, 190, 170), hair_color=(50, 30, 20)):
    """Draw a stylised front-facing face centered at (cx, cy) with *scale*."""
    s = scale
    # Head oval
    head_w, head_h = int(160 * s), int(200 * s)
    draw.ellipse([cx - head_w // 2, cy - head_h // 2, cx + head_w // 2, cy + head_h // 2], fill=skin_color)

    # Hair (simple cap on top)
    draw.ellipse([cx - int(165 * s), cy - int(130 * s), cx + int(165 * s), cy + int(10 * s)], fill=hair_color)
    # Side hair
    draw.rectangle([cx - int(165 * s), cy - int(80 * s), cx - int(150 * s), cy + int(50 * s)], fill=hair_color)
    draw.rectangle([cx + int(150 * s), cy - int(80 * s), cx + int(165 * s), cy + int(50 * s)], fill=hair_color)

    # Eyes
    eye_y = cy - int(20 * s)
    eye_spacing = int(50 * s)
    eye_w, eye_h = int(28 * s), int(18 * s)
    for ex in [cx - eye_spacing, cx + eye_spacing]:
        draw.ellipse([ex - eye_w // 2, eye_y - eye_h // 2, ex + eye_w // 2, eye_y + eye_h // 2], fill=(255, 255, 255))
        # Iris
        iris_r = int(8 * s)
        draw.ellipse([ex - iris_r, eye_y - iris_r, ex + iris_r, eye_y + iris_r], fill=(80, 120, 180))
        # Pupil
        pupil_r = int(4 * s)
        draw.ellipse([ex - pupil_r, eye_y - pupil_r, ex + pupil_r, eye_y + pupil_r], fill=(20, 20, 40))
        # Eye shine
        draw.ellipse([ex + int(3 * s), eye_y - int(5 * s), ex + int(6 * s), eye_y - int(2 * s)], fill=(255, 255, 255))

    # Eyebrows
    brow_y = eye_y - int(20 * s)
    for bx in [cx - eye_spacing, cx + eye_spacing]:
        draw.arc([bx - int(30 * s), brow_y - int(8 * s), bx + int(30 * s), brow_y + int(8 * s)],
                 180, 360, fill=hair_color, width=int(4 * s))

    # Nose
    nose_top = cy - int(5 * s)
    nose_bottom = cy + int(30 * s)
    draw.line([(cx, nose_top), (cx, nose_bottom)], fill=(190, 160, 140), width=int(3 * s))
    # Nostrils
    for nx in [cx - int(10 * s), cx + int(10 * s)]:
        draw.ellipse([nx - int(4 * s), nose_bottom - int(2 * s), nx + int(4 * s), nose_bottom + int(4 * s)], fill=(170, 140, 120))

    # Mouth
    mouth_y = cy + int(50 * s)
    draw.arc([cx - int(35 * s), mouth_y - int(10 * s), cx + int(35 * s), mouth_y + int(15 * s)],
             0, 180, fill=(180, 100, 100), width=int(4 * s))
    # Lower lip line
    draw.arc([cx - int(30 * s), mouth_y + int(5 * s), cx + int(30 * s), mouth_y + int(20 * s)],
             0, 180, fill=(160, 90, 90), width=int(2 * s))

    # Ears
    ear_w, ear_h = int(18 * s), int(40 * s)
    draw.ellipse([cx - head_w // 2 - ear_w, cy - ear_h // 2, cx - head_w // 2, cy + ear_h // 2], fill=skin_color)
    draw.ellipse([cx + head_w // 2, cy - ear_h // 2, cx + head_w // 2 + ear_w, cy + ear_h // 2], fill=skin_color)


def build_multi_photo_collage(size=(1080, 1350)):
    """Collage with 3 photos, overlapping, different transparencies — test multi-image detection."""
    w, h = size
    img = Image.new("RGB", size, C_NEARLY_WHITE)
    draw = ImageDraw.Draw(img)

    F_TITLE = _get_font(72, bold=True)
    F_SUB = _get_font(36)

    # Title area
    title = "PHOTO COLLAGE"
    _, _, tw, th = draw.textbbox((0, 0), title, font=F_TITLE)
    draw.text(((w - tw) / 2, 25), title, fill=C_ALMOST_BLACK, font=F_TITLE)
    sub = "Multi-image recognition test"
    _, _, sw, sh = draw.textbbox((0, 0), sub, font=F_SUB)
    draw.text(((w - sw) / 2, 25 + th + 8), sub, fill=C_DARK_GRAY, font=F_SUB)

    # --- Photo 1: main large, bottom-left, rotated ---
    pw1, ph1 = int(w * 0.55), int(h * 0.40)
    photo1 = _get_photo(pw1, ph1, seed="collage-a")
    p1_x, p1_y = int(w * 0.05), int(h * 0.30)
    img.paste(photo1, (p1_x, p1_y))

    # --- Photo 2: medium, top-right, overlapping photo 1 ---
    pw2, ph2 = int(w * 0.45), int(h * 0.32)
    photo2 = _get_photo(pw2, ph2, seed="collage-b")
    # Semi-transparent paste: composite with alpha
    p2_x, p2_y = int(w * 0.40), int(h * 0.25)
    overlay2 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    overlay2.paste(photo2, (p2_x, p2_y))
    # Fade the entire photo to 75% opacity
    alpha2 = Image.new("L", (w, h), 0)
    adraw2 = ImageDraw.Draw(alpha2)
    adraw2.rectangle([p2_x, p2_y, p2_x + pw2, p2_y + ph2], fill=191)  # 75%
    img = Image.composite(overlay2, img.convert("RGBA"), alpha2).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Border on photo 2
    draw.rectangle([p2_x, p2_y, p2_x + pw2, p2_y + ph2], outline=C_WHITE, width=4)

    # --- Photo 3: small, bottom-right, overlapping photo 1, highly transparent ---
    pw3, ph3 = int(w * 0.35), int(h * 0.28)
    photo3 = _get_photo(pw3, ph3, seed="collage-c")
    p3_x, p3_y = int(w * 0.55), int(h * 0.55)
    overlay3 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    overlay3.paste(photo3, (p3_x, p3_y))
    alpha3 = Image.new("L", (w, h), 0)
    adraw3 = ImageDraw.Draw(alpha3)
    adraw3.rectangle([p3_x, p3_y, p3_x + pw3, p3_y + ph3], fill=128)  # 50%
    img = Image.composite(overlay3, img.convert("RGBA"), alpha3).convert("RGB")
    draw = ImageDraw.Draw(img)

    draw.rectangle([p3_x, p3_y, p3_x + pw3, p3_y + ph3], outline=C_WHITE, width=3)

    # Subtle labels over each photo
    F_LABEL = _get_font(26, bold=True)
    draw.text((p1_x + 10, p1_y + 10), "PHOTO A", fill=C_WHITE, font=F_LABEL)
    _draw_text_with_shadow(draw, (p2_x + 10, p2_y + 10), "PHOTO B", F_LABEL, fill=C_WHITE)
    _draw_text_with_shadow(draw, (p3_x + 10, p3_y + 10), "PHOTO C", F_LABEL, fill=C_WHITE)

    return img


def build_portrait_overlay(size=(1080, 1350)):
    """Real person photo with gradient overlays, semi-transparent shapes — test transparency + face detection."""
    w, h = size

    # Background: colourful abstract gradient
    img = Image.new("RGB", size, (0, 0, 0))
    draw = ImageDraw.Draw(img)
    _draw_gradient(draw, 0, 0, w, h, (60, 30, 100), (200, 80, 120))

    # Real person photo in centre — try multiple portrait seeds
    person_w = int(w * 0.75)
    person_h = int(h * 0.60)
    px = (w - person_w) // 2
    py = int(h * 0.15)

    person_photo = _get_photo(person_w, person_h, seed="real-portrait-person")
    img.paste(person_photo, (px, py))

    F_TITLE = _get_font(52, bold=True)
    F_SUB = _get_font(30)

    # --- Semi-transparent diagonal overlay bar across the face ---
    bar = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(bar)
    for offset in range(0, 70):
        alpha = int(160 * (1 - offset / 70))
        bdraw.line([(int(w * 0.35) + offset, 0), (int(w * 0.35) + offset + h * 0.4, h)], fill=(255, 255, 255, alpha), width=1)
    img = Image.alpha_composite(img.convert("RGBA"), bar).convert("RGB")
    draw = ImageDraw.Draw(img)

    # --- Second semi-transparent circle overlay (right side of photo) ---
    overlay2 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    odraw2 = ImageDraw.Draw(overlay2)
    cx2, cy2 = px + int(person_w * 0.7), py + int(person_h * 0.4)
    r2 = int(person_h * 0.35)
    for r in range(r2, 0, -2):
        t = r / r2
        alpha = int(120 * (1 - t))
        odraw2.ellipse([cx2 - r, cy2 - r, cx2 + r, cy2 + r], fill=(234, 179, 8, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay2).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Title at top
    title = "PORTRAIT STUDY"
    _, _, tw, th = draw.textbbox((0, 0), title, font=F_TITLE)
    _draw_text_with_shadow(draw, ((w - tw) / 2, 30), title, F_TITLE, fill=C_WHITE)

    # Bottom text
    sub = "Transparency · Overlay · Face detection"
    _, _, sw, sh = draw.textbbox((0, 0), sub, font=F_SUB)
    _draw_text_with_shadow(draw, ((w - sw) / 2, h - 50), sub, F_SUB, fill=C_CREAM)

    return img


def build_showcase_two_products(size=(1080, 1350)):
    """2 product photos side-by-side with reflections, shadows, semi-transparent overlays — test multi-image."""
    w, h = size
    img = Image.new("RGB", size, C_WHITE)
    draw = ImageDraw.Draw(img)

    F_TITLE = _get_font(64, bold=True)
    F_SUB = _get_font(32)
    F_PRICE = _get_font(36, bold=True)
    F_LABEL = _get_font(24)

    # Header
    title = "DUO COLLECTION"
    _, _, tw, th = draw.textbbox((0, 0), title, font=F_TITLE)
    draw.text(((w - tw) / 2, 30), title, fill=C_ALMOST_BLACK, font=F_TITLE)
    draw.line([(int(w * 0.1), 30 + th + 12), (int(w * 0.9), 30 + th + 12)], fill=C_DARK_GRAY, width=1)

    # --- Left product ---
    left_cx = int(w * 0.28)
    prod_y = int(h * 0.25)
    prod_size = int(w * 0.30)

    # Shadow
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.ellipse([left_cx - prod_size // 2 - 10, prod_y + prod_size - 5, left_cx + prod_size // 2 + 10, prod_y + prod_size + 15],
                  fill=(0, 0, 0, 60))
    img = Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Product photo (circular)
    photo1 = _get_photo(prod_size, prod_size, seed="showcase-a")
    mask1 = Image.new("L", (prod_size, prod_size), 0)
    mdraw1 = ImageDraw.Draw(mask1)
    mdraw1.ellipse([0, 0, prod_size, prod_size], fill=255)
    mask1 = mask1.filter(ImageFilter.GaussianBlur(3))
    img.paste(photo1, (left_cx - prod_size // 2, prod_y), mask1)

    # Ring overlay on product
    ring = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    rdraw = ImageDraw.Draw(ring)
    rdraw.ellipse([left_cx - prod_size // 2, prod_y, left_cx + prod_size // 2, prod_y + prod_size],
                  outline=(234, 179, 8, 200), width=4)
    img = Image.alpha_composite(img.convert("RGBA"), ring).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Reflection (flipped bottom half with gradient fade)
    ref_raw = photo1.crop((0, prod_size // 2, prod_size, prod_size))
    ref_raw = ref_raw.transpose(Image.FLIP_TOP_BOTTOM)
    reflect = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ref_draw = ImageDraw.Draw(reflect)
    for y in range(prod_size // 2):
        alpha = int(100 * (1 - y / (prod_size // 2)))
        for x in range(prod_size):
            rp, gp, bp = ref_raw.getpixel((x, y))
            reflect.putpixel((left_cx - prod_size // 2 + x, prod_y + prod_size + y), (rp, gp, bp, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), reflect).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Product labels
    draw.text((left_cx - 30, prod_y + prod_size + 60), "CLASSIC", fill=C_DARK_GRAY, font=F_LABEL)
    _draw_text_with_shadow(draw, (left_cx - 40, prod_y + prod_size + 90), "$49.99", F_PRICE, fill=C_ALMOST_BLACK)

    # --- Right product ---
    right_cx = int(w * 0.72)
    # (slightly offset Y for visual variety)
    prod_y2 = int(h * 0.30)
    prod_size2 = int(w * 0.26)

    shadow2 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sdraw2 = ImageDraw.Draw(shadow2)
    sdraw2.ellipse([right_cx - prod_size2 // 2 - 10, prod_y2 + prod_size2 - 5, right_cx + prod_size2 // 2 + 10, prod_y2 + prod_size2 + 15],
                   fill=(0, 0, 0, 60))
    img = Image.alpha_composite(img.convert("RGBA"), shadow2).convert("RGB")
    draw = ImageDraw.Draw(img)

    photo2 = _get_photo(prod_size2, prod_size2, seed="showcase-b")
    # Rounded rect mask
    mask2 = Image.new("L", (prod_size2, prod_size2), 0)
    mdraw2 = ImageDraw.Draw(mask2)
    mdraw2.rounded_rectangle([0, 0, prod_size2, prod_size2], radius=20, fill=255)
    mask2 = mask2.filter(ImageFilter.GaussianBlur(2))
    img.paste(photo2, (right_cx - prod_size2 // 2, prod_y2), mask2)

    # Semi-transparent gradient overlay on right product
    grad_overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(grad_overlay)
    for i in range(prod_size2 // 2):
        alpha = int(80 * (1 - i / (prod_size2 // 2)))
        gdraw.line(
            [(right_cx - prod_size2 // 2, prod_y2 + prod_size2 // 2 + i),
             (right_cx + prod_size2 // 2, prod_y2 + prod_size2 // 2 + i)],
            fill=(255, 255, 200, alpha), width=1,
        )
    img = Image.alpha_composite(img.convert("RGBA"), grad_overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # "SALE" badge on right product
    sale = "-30%"
    _, _, salew, saleh = draw.textbbox((0, 0), sale, font=_get_font(28, bold=True))
    sale_badge = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sdraw3 = ImageDraw.Draw(sale_badge)
    sdraw3.rounded_rectangle(
        [right_cx - salew - 16, prod_y2 + 10, right_cx + 10, prod_y2 + saleh + 26],
        radius=8, fill=(234, 179, 8, 220),
    )
    sdraw3.text((right_cx - salew - 6, prod_y2 + 15), sale, fill=C_ALMOST_BLACK, font=_get_font(28, bold=True))
    img = Image.alpha_composite(img.convert("RGBA"), sale_badge).convert("RGB")
    draw = ImageDraw.Draw(img)

    draw.text((right_cx - 35, prod_y2 + prod_size2 + 40), "MODERN", fill=C_DARK_GRAY, font=F_LABEL)
    _draw_text_with_shadow(draw, (right_cx - 45, prod_y2 + prod_size2 + 70), "$79.99", F_PRICE, fill=C_ALMOST_BLACK)

    # Bottom CTA bar
    bar = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bdraw4 = ImageDraw.Draw(bar)
    bdraw4.rectangle([(0, h - 60), (w, h)], fill=(26, 35, 126, 220))
    img = Image.alpha_composite(img.convert("RGBA"), bar).convert("RGB")
    draw = ImageDraw.Draw(img)

    cta = "SHOP THE DUO · FREE SHIPPING"
    F_CTA = _get_font(32, bold=True)
    _, _, cw, ch = draw.textbbox((0, 0), cta, font=F_CTA)
    draw.text(((w - cw) / 2, h - 42), cta, fill=C_WHITE, font=F_CTA)

    return img


# ── V4 Inpainting-specific test images ───────────────────────────────


def build_inpaint_forest_text(size=(1080, 1350)):
    """Large text over dense forest photo — test OpenCV texture reconstruction."""
    w, h = size
    F_TITLE = _get_font(100, bold=True)
    F_SUB = _get_font(42)
    F_TAG = _get_font(28)

    photo = _get_photo(w, h, seed="inpaint-forest")
    draw = ImageDraw.Draw(photo)

    # Semi-transparent dark bar at top for contrast
    bar = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(bar)
    bdraw.rectangle([(0, 0), (w, 120)], fill=(0, 0, 0, 100))
    photo = Image.alpha_composite(photo.convert("RGBA"), bar).convert("RGB")
    draw = ImageDraw.Draw(photo)

    tag = "EXPLORE · TREK · DISCOVER"
    _, _, tagw, tagh = draw.textbbox((0, 0), tag, font=F_TAG)
    draw.text(((w - tagw) // 2, 30), tag, fill=(255, 255, 255, 200), font=F_TAG)

    # BIG text over the forest — covers large area
    title = "DISCOVER NATURE"
    _, _, tw, th = draw.textbbox((0, 0), title, font=F_TITLE)
    _draw_text_with_shadow(
        draw,
        ((w - tw) // 2, int(h * 0.28)),
        title, F_TITLE, fill=C_WHITE,
        shadow_color=(20, 40, 10),
    )

    # Subtitle over different forest area
    sub = "Explore the wilderness within"
    _, _, sw, sh = draw.textbbox((0, 0), sub, font=F_SUB)
    _draw_text_with_shadow(
        draw,
        ((w - sw) // 2, int(h * 0.28) + th + 30),
        sub, F_SUB, fill=(220, 240, 200),
    )

    # Small text badge bottom-left on photo
    badge = "NATIONAL PARK SERIES"
    _, _, bw, bh = draw.textbbox((0, 0), badge, font=F_TAG)
    _draw_rounded_rect(draw, (30, h - 80, 30 + bw + 20, h - 80 + bh + 12), radius=6, fill=(0, 0, 0, 160))
    draw.text((40, h - 74), badge, fill=C_WHITE, font=F_TAG)

    return photo


def build_inpaint_face_text(size=(1080, 1350)):
    """Text over a person's face — test facial feature reconstruction."""
    w, h = size
    F_TITLE = _get_font(80, bold=True)
    F_SUB = _get_font(36)

    photo = _get_photo(w, h, seed="inpaint-face")
    draw = ImageDraw.Draw(photo)

    # Semi-transparent dark overlay bottom
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for i in range(int(h * 0.4)):
        alpha = int(120 * (1 - i / (h * 0.4)))
        odraw.line([(0, h - int(h * 0.4) + i), (w, h - int(h * 0.4) + i)], fill=(0, 0, 0, alpha), width=1)
    photo = Image.alpha_composite(photo.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(photo)

    # Text directly over the face area
    title = "YOU ARE"
    _, _, tw, th = draw.textbbox((0, 0), title, font=F_TITLE)
    _draw_text_with_shadow(
        draw,
        ((w - tw) // 2, int(h * 0.30)),
        title, F_TITLE, fill=C_WHITE,
    )

    sub = "BEAUTIFUL"
    _, _, sw, sh = draw.textbbox((0, 0), sub, font=F_TITLE)
    _draw_text_with_shadow(
        draw,
        ((w - sw) // 2, int(h * 0.30) + th + 10),
        sub, F_TITLE, fill=C_GOLD,
    )

    # Small text bottom-right
    tag = "#youareenough"
    _, _, tagw, tagh = draw.textbbox((0, 0), tag, font=F_SUB)
    draw.text((w - tagw - 30, h - 60), tag, fill=(255, 220, 220, 200), font=F_SUB)

    return photo


def build_inpaint_pattern_text(size=(1080, 1350)):
    """Text over geometric pattern — tests patterned background reconstruction."""
    w, h = size
    F_TITLE = _get_font(72, bold=True)
    F_SUB = _get_font(32, bold=True)
    F_LABEL = _get_font(24)

    # Create a geometric pattern background
    img = Image.new("RGB", size, C_DARK_GRAY)
    draw = ImageDraw.Draw(img)

    # Grid of lines (architectural pattern)
    for x in range(0, w, 40):
        alpha = 40
        draw.line([(x, 0), (x, h)], fill=(200, 200, 200, alpha), width=1)
    for y in range(0, h, 40):
        alpha = 40
        draw.line([(0, y), (w, y)], fill=(200, 200, 200, alpha), width=1)

    # Diagonal crossing lines
    draw.line([(0, 0), (w, h)], fill=(180, 180, 180, 60), width=2)
    draw.line([(w, 0), (0, h)], fill=(180, 180, 180, 60), width=2)

    # Pattern circles
    for cx, cy in [(w // 4, h // 3), (3 * w // 4, h // 2), (w // 3, 3 * h // 4), (2 * w // 3, h // 3)]:
        for r in range(30, 120, 30):
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(150, 150, 150, 30), width=1)

    # Now overlay text over this pattern
    title = "GEOMETRY"
    _, _, tw, th = draw.textbbox((0, 0), title, font=F_TITLE)
    _draw_text_with_shadow(
        draw,
        ((w - tw) // 2, int(h * 0.30)),
        title, F_TITLE, fill=C_WHITE,
    )

    sub_lines = ["IN · DESIGN · PATTERNS", "LINES · CIRCLES · GRIDS"]
    for i, line in enumerate(sub_lines):
        _, _, sw, sh = draw.textbbox((0, 0), line, font=F_SUB)
        _draw_text_with_shadow(
            draw,
            ((w - sw) // 2, int(h * 0.30) + th + 20 + i * (sh + 10)),
            line, F_SUB, fill=C_GOLD,
        )

    # Small text labels over pattern intersections
    labels = ["A1", "B2", "C3", "D4"]
    positions = [(60, 60), (w - 80, 80), (60, h - 100), (w - 80, h - 100)]
    for label, (lx, ly) in zip(labels, positions):
        _draw_text_with_shadow(draw, (lx, ly), label, F_LABEL, fill=(200, 200, 255))

    return img


# ── Registry ─────────────────────────────────────────────────────────

GENERATORS = {
    "poster-simple.jpg": build_poster_simple,
    "poster-gradient.jpg": build_poster_gradient,
    "flyer-text-heavy.jpg": build_flyer_text_heavy,
    "poster-person.jpg": build_poster_person,
    "banner-horizontal.jpg": build_banner_horizontal,
    "poster-display-font.jpg": build_poster_display_font,
    "poster-low-contrast.jpg": build_poster_low_contrast,
    "multi-photo-collage.jpg": build_multi_photo_collage,
    "portrait-overlay.jpg": build_portrait_overlay,
    "showcase-two-products.jpg": build_showcase_two_products,
    # V4 inpainting-specific — text over challenging backgrounds
    "inpaint-forest-text.jpg": build_inpaint_forest_text,
    "inpaint-face-text.jpg": build_inpaint_face_text,
    "inpaint-pattern-text.jpg": build_inpaint_pattern_text,
}


# ── CLI ──────────────────────────────────────────────────────────────


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate 7 synthetic fixture images for the Smart Import Pipeline."
    )
    parser.add_argument("--output-dir", default=None, help="Output directory (default: same directory as this script)")
    parser.add_argument("--quality", type=int, default=95, help="JPEG quality (default: 95, spec requires 90+)")
    parser.add_argument("--list", action="store_true", help="List the images that would be generated without creating them")
    return parser.parse_args(argv)


def generate_all(output_dir=None, quality=95):
    if output_dir is None:
        output_dir = Path(__file__).resolve().parent
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    created = []
    for filename, builder_fn in GENERATORS.items():
        print(f"  Generating {filename} ...", end=" ")
        img = builder_fn()
        filepath = output_dir / filename
        img.save(str(filepath), "JPEG", quality=quality)
        size_kb = filepath.stat().st_size / 1024
        print(f"[OK] {img.size[0]}x{img.size[1]}  ({size_kb:.1f} KB)")
        created.append((filename, str(filepath)))

    return created


def main(argv=None):
    args = parse_args(argv)

    if args.list:
        print("Images that will be generated:")
        for name, desc in [
            ("poster-simple.jpg", "1080×1350 · Synthetic photo + gradient overlay + text on image + badge"),
            ("poster-gradient.jpg", "1080×1350 · Gradient bg + circular product photo + text INSIDE circle"),
            ("flyer-text-heavy.jpg", "1080×1350 · Abstract bg with dark overlay + 7 text blocks with icons"),
            ("poster-person.jpg", "1080×1080 · Person silhouette + gradient overlay + title ON image + featured tag"),
            ("banner-horizontal.jpg", "1920×1080 · Product photo + gradient overlay + text on both sides + badge"),
            ("poster-display-font.jpg", "1080×1350 · Display typography over abstract image + dark overlay"),
            ("poster-low-contrast.jpg", "1080×1350 · Low contrast text/background (no image — deliberate)"),
            ("multi-photo-collage.jpg", "1080×1350 · 3 photos overlapping + different opacities + labels"),
            ("portrait-overlay.jpg", "1080×1350 · Face drawing + diagonal transparency + radial overlay"),
            ("showcase-two-products.jpg", "1080×1350 · 2 products + reflections + shadows + badges + overlay"),
            ("inpaint-forest-text.jpg", "1080×1350 · [V4] Large text over dense forest — test texture inpainting"),
            ("inpaint-face-text.jpg", "1080×1350 · [V4] Text over face photo — test facial reconstruction"),
            ("inpaint-pattern-text.jpg", "1080×1350 · [V4] Text over geometric pattern — test pattern continuity"),
        ]:
            print(f"  - {name}  --  {desc}")
        return

    print("Generating 13 synthetic fixture images...")
    print(f"  Output dir: {args.output_dir or 'dataset/'}")
    print(f"  JPEG quality: {args.quality}")
    print()

    created = generate_all(output_dir=args.output_dir, quality=args.quality)

    print()
    print(f"[OK] Done — {len(created)} images generated:")
    for name, path in created:
        print(f"     {path}")


if __name__ == "__main__":
    main()
