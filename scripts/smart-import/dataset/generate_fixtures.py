"""
Generate 7 synthetic test images for the Smart Import Calibration Pipeline.

Each image covers a distinct visual case as specified in the SDD spec
(smart-import-pipeline/spec.md §1). Uses Pillow drawing primitives only
— no external assets required.

Usage:
    python generate_fixtures.py [--output-dir DIR] [--quality N]

Output: 7 JPEG files in the specified directory (default: dataset/)
"""

import argparse
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

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


def _draw_gradient(draw, x1, y1, x2, y2, color_start, color_end, vertical=True):
    """Draw a linear gradient rectangle from color_start to color_end."""
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
    """Draw a rectangle with rounded corners."""
    x1, y1, x2, y2 = bbox
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline, width=width)


# ── Image builders ──────────────────────────────────────────────────


def build_poster_simple(size=(1080, 1350)):
    """Simple poster: solid background + big title + photo rectangle."""
    w, h = size
    img = Image.new("RGB", size, C_DARK_BLUE)
    draw = ImageDraw.Draw(img)

    # Title text — big white letters
    title = "SUMMER FEST"
    _, _, tw, th = draw.textbbox((0, 0), title, font=None)
    tx = (w - tw) / 2
    ty = h * 0.08
    # Draw multiple times with offset for a bold effect (no system font guaranteed)
    for dx in range(-3, 4, 2):
        for dy in range(-3, 4, 2):
            draw.text((tx + dx, ty + dy), title, fill=C_DARK_BLUE)
    draw.text((tx, ty), title, fill=C_WHITE)

    # Subtitle
    sub = "AUGUST 15-17 · CENTRAL PARK"
    _, _, sw, sh = draw.textbbox((0, 0), sub, font=None)
    draw.text(((w - sw) / 2, ty + th + 30), sub, fill=(180, 200, 255))

    # Photo rectangle (gray placeholder)
    photo_x, photo_y = int(w * 0.1), int(h * 0.35)
    photo_w, photo_h = int(w * 0.8), int(h * 0.55)
    _draw_rounded_rect(
        draw,
        (photo_x, photo_y, photo_x + photo_w, photo_y + photo_h),
        radius=16,
        fill=(60, 70, 120),
        outline=(100, 120, 200),
        width=3,
    )

    # "Photo" inner hint
    hint = "📷"
    _, _, hw, hh = draw.textbbox((0, 0), hint, font=None)
    draw.text(
        (photo_x + (photo_w - hw) / 2, photo_y + (photo_h - hh) / 2 - 10),
        hint,
        fill=(120, 140, 200),
    )
    hint2 = "IMAGE"
    _, _, h2w, h2h = draw.textbbox((0, 0), hint2, font=None)
    draw.text(
        (photo_x + (photo_w - h2w) / 2, photo_y + (photo_h - h2h) / 2 + 15),
        hint2,
        fill=(120, 140, 200),
    )

    return img


def build_poster_gradient(size=(1080, 1350)):
    """Poster with gradient background + 2 texts + shape."""
    w, h = size
    img = Image.new("RGB", size, (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Gradient background: purple → pink
    _draw_gradient(draw, 0, 0, w, h, C_PURPLE, C_PINK)

    # Large title
    title = "NEW COLLECTION"
    _, _, tw, th = draw.textbbox((0, 0), title, font=None)
    draw.text(((w - tw) / 2, h * 0.12), title, fill=C_WHITE)

    # Subtitle
    sub = "Spring 2026 · Limited Edition"
    _, _, sw, sh = draw.textbbox((0, 0), sub, font=None)
    draw.text(((w - sw) / 2, h * 0.12 + th + 25), sub, fill=(220, 200, 255))

    # Decorative circle/ellipse shape
    cx, cy = w // 2, int(h * 0.58)
    rx, ry = int(w * 0.35), int(h * 0.22)
    draw.ellipse(
        [cx - rx, cy - ry, cx + rx, cy + ry],
        outline=(255, 255, 255, 80),
        width=4,
    )

    # Inner circle
    draw.ellipse(
        [cx - rx // 2, cy - ry // 2, cx + rx // 2, cy + ry // 2],
        outline=(255, 255, 255, 60),
        width=2,
    )

    # Bottom CTA text
    cta = "SHOP NOW →"
    _, _, cw, ch = draw.textbbox((0, 0), cta, font=None)
    draw.text(((w - cw) / 2, h * 0.85), cta, fill=(255, 230, 250))

    return img


def build_flyer_text_heavy(size=(1080, 1350)):
    """Flyer with 5-8 text blocks, 2 sizes."""
    w, h = size
    img = Image.new("RGB", size, C_NEARLY_WHITE)
    draw = ImageDraw.Draw(img)

    # Top accent bar
    draw.rectangle([(0, 0), (w, 8)], fill=C_SOFT_BLUE)

    # Header block
    header = "COMMUNITY MEETUP"
    _, _, hw, hh = draw.textbbox((0, 0), header, font=None)
    draw.text(((w - hw) / 2, 40), header, fill=C_ALMOST_BLACK)

    # Sub-header
    sub = "Tech & Innovation Summit 2026"
    _, _, sw, sh = draw.textbbox((0, 0), sub, font=None)
    draw.text(((w - sw) / 2, 40 + hh + 15), sub, fill=C_DARK_GRAY)

    # Divider line
    div_y = 40 + hh + 15 + sh + 20
    draw.line([(int(w * 0.2), div_y), (int(w * 0.8), div_y)], fill=C_SOFT_BLUE, width=2)

    # Text blocks (7 blocks)
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
        _, _, tw, th = draw.textbbox((0, 0), text, font=None)
        draw.text((int(w * 0.15), block_y), text, fill=C_DARK_GRAY)

        # Sub-label in smaller text (simulate 2 sizes)
        _, _, lw, lh = draw.textbbox((0, 0), _label, font=None)
        draw.text(
            (int(w * 0.15) + tw + 15, block_y + 2),
            f"[{_label}]",
            fill=C_MED_GRAY,
        )
        block_y += th + 18

    # Bottom bar
    draw.rectangle([(0, h - 50), (w, h)], fill=C_SOFT_BLUE)
    footer = "Free entry · Register now!"
    _, _, fw, fh = draw.textbbox((0, 0), footer, font=None)
    draw.text(((w - fw) / 2, h - 35), footer, fill=C_WHITE)

    return img


def build_poster_person(size=(1080, 1080)):
    """Square post with person silhouette + title + metadata."""
    w, h = size
    img = Image.new("RGB", size, C_TEAL)
    draw = ImageDraw.Draw(img)

    # Decorative background circles
    draw.ellipse([-100, -100, 300, 300], fill=(11, 118, 108), width=0)
    draw.ellipse([w - 250, h - 250, w + 50, h + 50], fill=(11, 118, 108), width=0)
    draw.ellipse([w // 2 - 200, h // 2 - 200, w // 2 + 200, h // 2 + 200], fill=(10, 128, 118), width=0)

    # Person silhouette
    head_cx, head_cy = w // 2, int(h * 0.30)
    head_r = int(w * 0.10)
    # Head (circle)
    draw.ellipse(
        [head_cx - head_r, head_cy - head_r, head_cx + head_r, head_cy + head_r],
        fill=(200, 220, 210),
    )

    # Body (trapezoid)
    body_top_y = head_cy + head_r - 10
    body_bottom_y = int(h * 0.55)
    shoulder_w = int(w * 0.18)
    base_w = int(w * 0.14)
    draw.polygon(
        [
            (head_cx - shoulder_w, body_top_y),
            (head_cx + shoulder_w, body_top_y),
            (head_cx + base_w, body_bottom_y),
            (head_cx - base_w, body_bottom_y),
        ],
        fill=(200, 220, 210),
    )

    # Title text
    title = "JANE DOE"
    _, _, tw, th = draw.textbbox((0, 0), title, font=None)
    draw.text(((w - tw) / 2, int(h * 0.65)), title, fill=C_WHITE)

    # Metadata
    meta = "@janedoe · 12k followers"
    _, _, mw, mh = draw.textbbox((0, 0), meta, font=None)
    draw.text(((w - mw) / 2, int(h * 0.65) + th + 10), meta, fill=(180, 220, 210))

    # Verified badge
    badge = "✓"
    _, _, bw, bh = draw.textbbox((0, 0), badge, font=None)
    bx = (w + tw) // 2 + 25
    draw.text((bx, int(h * 0.65)), badge, fill=C_GOLD)

    return img


def build_banner_horizontal(size=(1920, 1080)):
    """Horizontal banner with text + photo."""
    w, h = size
    img = Image.new("RGB", size, (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Horizontal gradient: orange → amber
    _draw_gradient(draw, 0, 0, w, h, C_ORANGE, C_AMBER, vertical=False)

    # Big text on left side
    title = "SALE"
    _, _, tw, th = draw.textbbox((0, 0), title, font=None)
    draw.text((int(w * 0.08), int(h * 0.20)), title, fill=C_WHITE)

    sub = "UP TO 50% OFF"
    _, _, sw, sh = draw.textbbox((0, 0), sub, font=None)
    draw.text((int(w * 0.08), int(h * 0.20) + th + 10), sub, fill=C_CREAM)

    # Detail text
    detail = "Limited time · Select items"
    _, _, dw, dh = draw.textbbox((0, 0), detail, font=None)
    draw.text((int(w * 0.08), int(h * 0.20) + th + sh + 25), detail, fill=(255, 220, 180))

    # CTA button
    cta = "SHOP NOW  →"
    _, _, cw, ch = draw.textbbox((0, 0), cta, font=None)
    btn_x, btn_y = int(w * 0.08), int(h * 0.65)
    btn_w, btn_h = cw + 40, ch + 20
    _draw_rounded_rect(
        draw,
        (btn_x, btn_y, btn_x + btn_w, btn_y + btn_h),
        radius=8,
        fill=C_DARK_BLUE,
    )
    draw.text((btn_x + 20, btn_y + 10), cta, fill=C_WHITE)

    # Photo placeholder on right side
    photo_x = int(w * 0.50)
    photo_y = int(h * 0.12)
    photo_w = int(w * 0.42)
    photo_h = int(h * 0.76)
    _draw_rounded_rect(
        draw,
        (photo_x, photo_y, photo_x + photo_w, photo_y + photo_h),
        radius=12,
        fill=(200, 160, 100),
        outline=(255, 220, 150),
        width=3,
    )

    # Photo inner hint
    hint = "PRODUCT"
    _, _, hw, hh = draw.textbbox((0, 0), hint, font=None)
    draw.text(
        (photo_x + (photo_w - hw) / 2, photo_y + (photo_h - hh) / 2),
        hint,
        fill=(160, 120, 70),
    )

    return img


def build_poster_display_font(size=(1080, 1350)):
    """Design with decorative display typography."""
    w, h = size
    img = Image.new("RGB", size, C_ALMOST_BLACK)
    draw = ImageDraw.Draw(img)

    # Subtle radial-like effect with concentric circles
    cx, cy = w // 2, h // 2
    for r in range(0, max(w, h), 30):
        alpha = max(0, 255 - r * 2)
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=(40, 40, 60, alpha),
            width=1,
        )

    # Decorative stars
    stars = [(120, 150), (w - 150, 200), (200, h - 180), (w - 180, h - 250), (w // 2, 80), (w // 2 + 100, h - 150)]
    for sx, sy in stars:
        draw.text((sx, sy), "✦", fill=C_GOLD)

    # Small decorative dots
    dot_positions = [
        (80, 400),
        (w - 100, 500),
        (150, h - 300),
        (w - 120, h - 400),
        (w // 3, 700),
        (2 * w // 3, 800),
    ]
    for dx, dy in dot_positions:
        draw.ellipse([dx - 4, dy - 4, dx + 4, dy + 4], fill=C_GOLD)

    # Decorative lines
    draw.line([(int(w * 0.15), int(h * 0.40)), (int(w * 0.40), int(h * 0.40))], fill=C_GOLD, width=2)
    draw.line([(int(w * 0.60), int(h * 0.40)), (int(w * 0.85), int(h * 0.40))], fill=C_GOLD, width=2)
    draw.line([(int(w * 0.15), int(h * 0.65)), (int(w * 0.40), int(h * 0.65))], fill=C_GOLD, width=2)
    draw.line([(int(w * 0.60), int(h * 0.65)), (int(w * 0.85), int(h * 0.65))], fill=C_GOLD, width=2)

    # Main display text
    display_text = "DREAM"
    _, _, dw, dh = draw.textbbox((0, 0), display_text, font=None)
    draw.text(((w - dw) / 2, int(h * 0.43)), display_text, fill=C_WHITE)

    # Ornamental underline
    underline_y = int(h * 0.43) + dh + 15
    draw.line([(int(w * 0.25), underline_y), (int(w * 0.75), underline_y)], fill=C_GOLD, width=1)

    # Secondary text
    sub = "BIG · BOLD · BEAUTIFUL"
    _, _, sw, sh = draw.textbbox((0, 0), sub, font=None)
    draw.text(((w - sw) / 2, underline_y + 15), sub, fill=C_MED_GRAY)

    return img


def build_poster_low_contrast(size=(1080, 1350)):
    """Design with low contrast text/background — deliberately hard to read."""
    w, h = size

    # Create subtle noise-like background for realistic low-contrast design
    bg = Image.new("RGB", size, C_LIGHT_GRAY)
    # Add slight noise to avoid completely flat background
    import random
    random.seed(42)
    pixels = bg.load()
    for _ in range(5000):
        px = random.randint(0, w - 1)
        py = random.randint(0, h - 1)
        r, g, b = pixels[px, py]
        delta = random.randint(-8, 8)
        pixels[px, py] = (
            max(0, min(255, r + delta)),
            max(0, min(255, g + delta)),
            max(0, min(255, b + delta)),
        )

    draw = ImageDraw.Draw(bg)

    # Very subtle border
    draw.rectangle([(10, 10), (w - 10, h - 10)], outline=(220, 220, 220), width=1)

    # Title — low contrast (light gray on slightly lighter gray)
    title = "Whisper Collection"
    _, _, tw, th = draw.textbbox((0, 0), title, font=None)
    draw.text(((w - tw) / 2, int(h * 0.08)), title, fill=C_LOW_CONTRAST_TEXT)

    # Subtitle even lower contrast
    sub = "barely visible elegance"
    _, _, sw, sh = draw.textbbox((0, 0), sub, font=None)
    draw.text(((w - sw) / 2, int(h * 0.08) + th + 10), sub, fill=(200, 200, 200))

    # Divider — subtle
    div_y = int(h * 0.08) + th + sh + 30
    draw.line([(int(w * 0.15), div_y), (int(w * 0.85), div_y)], fill=(215, 215, 215), width=1)

    # Body text blocks — all low contrast
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
        _, _, lw, lh = draw.textbbox((0, 0), line, font=None)
        draw.text(((w - lw) / 2, by), line, fill=C_LOW_CONTRAST_TEXT)
        by += lh + 5

    # Bottom metadata — even harder to read
    meta = "www.whisper-design.studio · @whisper"
    _, _, mw, mh = draw.textbbox((0, 0), meta, font=None)
    draw.text(((w - mw) / 2, int(h * 0.88)), meta, fill=(195, 195, 195))

    return bg


# ── Registry ─────────────────────────────────────────────────────────

GENERATORS = {
    "poster-simple.jpg": build_poster_simple,
    "poster-gradient.jpg": build_poster_gradient,
    "flyer-text-heavy.jpg": build_flyer_text_heavy,
    "poster-person.jpg": build_poster_person,
    "banner-horizontal.jpg": build_banner_horizontal,
    "poster-display-font.jpg": build_poster_display_font,
    "poster-low-contrast.jpg": build_poster_low_contrast,
}


# ── CLI ──────────────────────────────────────────────────────────────

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate 7 synthetic fixture images for the Smart Import Pipeline."
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: same directory as this script)",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=95,
        help="JPEG quality (default: 95, spec requires 90+)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List the images that would be generated without creating them",
    )
    return parser.parse_args(argv)


def generate_all(output_dir=None, quality=95):
    """Generate all 7 fixture images. Returns list of (filename, filepath)."""
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
            ("poster-simple.jpg", "1080×1350 · Simple poster: solid bg + title + photo"),
            ("poster-gradient.jpg", "1080×1350 · Gradient bg + 2 texts + circle shape"),
            ("flyer-text-heavy.jpg", "1080×1350 · 7 text blocks, 2 font sizes"),
            ("poster-person.jpg", "1080×1080 · Person silhouette + title + metadata"),
            ("banner-horizontal.jpg", "1920×1080 · Banner with text + photo"),
            ("poster-display-font.jpg", "1080×1350 · Decorative display typography"),
            ("poster-low-contrast.jpg", "1080×1350 · Low contrast text/background"),
        ]:
            print(f"  - {name}  --  {desc}")
        return

    print("Generating 7 synthetic fixture images...")
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
