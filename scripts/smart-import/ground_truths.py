"""
Ground-truth SceneGraphs for the 10 synthetic fixture images.

Each entry describes EXACTLY what the corresponding generator in
``generate_fixtures.py`` draws.  Values are extracted directly from the
generator code (magic numbers, computed positions, colors, text strings).

These serve as the "correct answer" when evaluating model-extracted
SceneGraphs: precision/recall of element detection, text accuracy,
layout similarity, colour fidelity, and classification accuracy.

Usage::

    from ground_truths import GROUND_TRUTHS
    gt = GROUND_TRUTHS["poster-simple.jpg"]
"""

from __future__ import annotations


def _parse_color(c: tuple[int, int, int] | tuple[int, int, int, int]) -> str:
    """RGBA or RGB tuple → hex string (alpha optional)."""
    if len(c) == 4:
        return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}{c[3]:02x}"
    return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"


GROUND_TRUTHS: dict[str, dict] = {}


# -----------------------------------------------------------------------
# 1. poster-simple.jpg   1080×1350
# -----------------------------------------------------------------------

GROUND_TRUTHS["poster-simple.jpg"] = {
    "id": "poster-simple",
    "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
    "background": {"kind": "solid", "color": "#1a237e"},
    "layers": [
        {
            "id": "title",
            "kind": "text",
            "text": "SUMMER FEST",
            "position": {"y_pct": 0.08},
            "font_size": 96,
            "bold": True,
            "color": "#ffffff",
            "alignment": "center",
            "z_index": 0,
        },
        {
            "id": "subtitle",
            "kind": "text",
            "text": "AUGUST 15-17 · CENTRAL PARK",
            "position": {"y_pct": 0.08, "offset_y": "title_h + 30"},
            "font_size": 42,
            "bold": False,
            "color": "#b4c8ff",
            "alignment": "center",
            "z_index": 0,
        },
        {
            "id": "photo",
            "kind": "image",
            "position": {
                "x": 108, "y": 472, "width": 864, "height": 742,
                "x_pct": 0.10, "y_pct": 0.35,
                "w_pct": 0.80, "h_pct": 0.55,
            },
            "opacity": 1.0,
            "z_index": 1,
        },
        {
            "id": "gradient-overlay",
            "kind": "shape",
            "type": "rectangle",
            "position": {
                "x": 108, "y": 843, "width": 864, "height": 371,
            },
            "color": "#000000b4",  # alpha 180 at peak
            "opacity": "gradient (0-180 alpha)",
            "z_index": 2,
        },
        {
            "id": "overlay-label",
            "kind": "text",
            "text": "Main Stage · Live Music",
            "position": {"x": 138, "y": 863},
            "font_size": 36,
            "bold": True,
            "color": "#ffffff",
            "alignment": "left",
            "z_index": 3,
        },
        {
            "id": "badge",
            "kind": "text",
            "text": "NOW ON SALE",
            "position": {"x": 924, "y": 487},
            "font_size": 28,
            "bold": True,
            "color": "#111827",
            "alignment": "left",
            "z_index": 4,
        },
        {
            "id": "badge-bg",
            "kind": "shape",
            "type": "rounded-rect",
            "position": {"x": 908, "y": 483, "width": "auto", "height": "auto"},
            "color": "#eab308dc",
            "z_index": 4,
        },
    ],
    "element_count": 7,
    "text_count": 4,
    "image_count": 1,
    "shape_count": 2,
}


# -----------------------------------------------------------------------
# 2. poster-gradient.jpg   1080×1350
# -----------------------------------------------------------------------

GROUND_TRUTHS["poster-gradient.jpg"] = {
    "id": "poster-gradient",
    "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
    "background": {"kind": "gradient", "color_start": "#7c3aed", "color_end": "#ec4899"},
    "layers": [
        {
            "id": "title",
            "kind": "text",
            "text": "NEW COLLECTION",
            "position": {"y_pct": 0.06},
            "font_size": 96,
            "bold": True,
            "color": "#ffffff",
            "alignment": "center",
            "z_index": 0,
        },
        {
            "id": "subtitle",
            "kind": "text",
            "text": "Spring 2026 · Limited Edition",
            "position": {"y_pct": 0.06, "offset_y": "title_h + 20"},
            "font_size": 42,
            "bold": False,
            "color": "#dcc8ff",
            "alignment": "center",
            "z_index": 0,
        },
        {
            "id": "circle-photo",
            "kind": "image",
            "position": {
                "cx": 540, "cy": 729, "radius": 237,
                "cx_pct": 0.50, "cy_pct": 0.54, "r_pct": 0.22,
            },
            "opacity": 1.0,
            "mask": "circle",
            "z_index": 1,
        },
        {
            "id": "circle-gradient-overlay",
            "kind": "shape",
            "type": "gradient-overlay",
            "position": {"cx": 540, "cy_pct": 0.54, "width": 474, "height": 158},
            "color": "#500078",
            "opacity": "gradient (0-140 alpha)",
            "z_index": 2,
        },
        {
            "id": "inside-text",
            "kind": "text",
            "text": "EXCLUSIVE",
            "position": {"cx": 540, "cy": 729},
            "font_size": 38,
            "bold": True,
            "color": "#ffffff",
            "alignment": "center",
            "z_index": 3,
        },
        {
            "id": "ring-border",
            "kind": "shape",
            "type": "ellipse",
            "position": {"cx": 540, "cy": 729, "radius": 237},
            "color": "#ffffff3c",
            "z_index": 3,
        },
        {
            "id": "cta",
            "kind": "text",
            "text": "SHOP NOW →",
            "position": {"y_pct": 0.88},
            "font_size": 40,
            "bold": True,
            "color": "#ffe6fa",
            "alignment": "center",
            "z_index": 4,
        },
    ],
    "element_count": 7,
    "text_count": 4,
    "image_count": 1,
    "shape_count": 2,
}


# -----------------------------------------------------------------------
# 3. flyer-text-heavy.jpg   1080×1350
# -----------------------------------------------------------------------

FLYER_BLOCKS = [
    "📅 Date: June 15, 2026",
    "📍 Venue: Grand Hall, Downtown",
    "⏰ Time: 9:00 AM - 6:00 PM",
    "🎤 Keynote: Future of AI",
    "🛠 Workshops: Hands-on sessions",
    "🤝 Networking: Meet the speakers",
    "🎟 Register: community-meetup.io",
]

GROUND_TRUTHS["flyer-text-heavy.jpg"] = {
    "id": "flyer-text-heavy",
    "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
    "background": {"kind": "photo-with-overlay", "color": "#000000a0"},
    "layers": [
        {
            "id": "bg-photo",
            "kind": "image",
            "position": {"x": 0, "y": 0, "width": 1080, "height": 1350},
            "opacity": 1.0,
            "z_index": 0,
        },
        {
            "id": "dark-overlay",
            "kind": "shape",
            "type": "rectangle",
            "position": {"x": 0, "y": 0, "width": 1080, "height": 1350},
            "color": "#000000a0",
            "opacity": 1.0,
            "z_index": 1,
        },
        {
            "id": "accent-bar",
            "kind": "shape",
            "type": "rectangle",
            "position": {"x": 0, "y": 0, "width": 1080, "height": 8},
            "color": "#3b82f6c8",
            "opacity": 1.0,
            "z_index": 2,
        },
        {
            "id": "header",
            "kind": "text",
            "text": "COMMUNITY MEETUP",
            "position": {"y": 40},
            "font_size": 72,
            "bold": True,
            "color": "#ffffff",
            "alignment": "center",
            "z_index": 3,
        },
        {
            "id": "subheader",
            "kind": "text",
            "text": "Tech & Innovation Summit 2026",
            "position": {"y": "header_y + header_h + 15"},
            "font_size": 40,
            "bold": False,
            "color": "#c8d2ff",
            "alignment": "center",
            "z_index": 3,
        },
        {
            "id": "divider",
            "kind": "shape",
            "type": "line",
            "position": {"x1_pct": 0.20, "x2_pct": 0.80, "y": "divider_y"},
            "color": "#3b82f6c8",
            "z_index": 3,
        },
    ] + [
        {
            "id": f"block-{i}",
            "kind": "text",
            "text": text,
            "position": {"x_pct": 0.15, "y": f"block_y_{i}"},
            "font_size": 34,
            "bold": False,
            "color": "#ffffff",
            "alignment": "left",
            "z_index": 4,
        }
        for i, text in enumerate(FLYER_BLOCKS)
    ] + [
        {
            "id": "bottom-bar",
            "kind": "shape",
            "type": "rectangle",
            "position": {"x": 0, "y": 1290, "width": 1080, "height": 60},
            "color": "#3b82f6c8",
            "z_index": 5,
        },
        {
            "id": "footer",
            "kind": "text",
            "text": "Free entry · Register now!",
            "position": {"y": 1308},
            "font_size": 32,
            "bold": True,
            "color": "#ffffff",
            "alignment": "center",
            "z_index": 6,
        },
    ],
    "element_count": 12,
    "text_count": 9,
    "image_count": 1,
    "shape_count": 4,
}


# -----------------------------------------------------------------------
# 4. poster-person.jpg   1080×1080
# -----------------------------------------------------------------------

GROUND_TRUTHS["poster-person.jpg"] = {
    "id": "poster-person",
    "canvas": {"width": 1080, "height": 1080, "detectedFormat": "square"},
    "background": {"kind": "solid", "color": "#0d9488"},
    "layers": [
        # Decorative circles (background)
        {"id": "deco-circle-1", "kind": "shape", "type": "ellipse",
         "position": {"cx": 50, "cy": 50, "rx": 200, "ry": 200},
         "color": "#0b766c", "z_index": 0},
        {"id": "deco-circle-2", "kind": "shape", "type": "ellipse",
         "position": {"cx": 930, "cy": 930, "rx": 150, "ry": 150},
         "color": "#0b766c", "z_index": 0},
        {"id": "deco-circle-3", "kind": "shape", "type": "ellipse",
         "position": {"cx": 540, "cy": 540, "rx": 200, "ry": 200},
         "color": "#0a8076", "z_index": 0},
        # Real person photo (circular mask)
        {"id": "person-photo", "kind": "image",
         "position": {"cx_pct": 0.50, "cy_pct": 0.28, "size_pct": 0.45},
         "mask": "circle", "opacity": 1.0, "z_index": 1},
        {"id": "gradient-overlay", "kind": "shape", "type": "gradient-overlay",
         "position": {"y_pct": 0.50, "h_pct": 0.50},
         "color": "#000000", "opacity": "gradient (0-160 alpha)", "z_index": 2},
        {"id": "title", "kind": "text", "text": "JANE DOE",
         "font_size": 72, "bold": True, "color": "#ffffff",
         "alignment": "center", "position": {"y_pct": 0.68}, "z_index": 3},
        {"id": "meta", "kind": "text", "text": "@janedoe · 12k followers",
         "font_size": 36, "bold": False, "color": "#c8f0e6",
         "alignment": "center", "position": {"y_pct": 0.68, "offset_y": "title_h + 15"}, "z_index": 3},
        {"id": "verified-badge", "kind": "text", "text": "✓",
         "font_size": 48, "bold": False, "color": "#eab308",
         "alignment": "left", "position": {"x": "title_right + 30", "y_pct": 0.68}, "z_index": 3},
        {"id": "featured-tag", "kind": "text", "text": "FEATURED",
         "font_size": 28, "bold": True, "color": "#111827",
         "alignment": "left", "position": {"x": 32, "y": 26}, "z_index": 4},
        {"id": "featured-tag-bg", "kind": "shape", "type": "rounded-rect",
         "position": {"x": 20, "y": 20},
         "color": "#eab308c8", "z_index": 4},
    ],
    "element_count": 10,
    "text_count": 4,
    "image_count": 1,
    "shape_count": 5,
}


# -----------------------------------------------------------------------
# 5. banner-horizontal.jpg   1920×1080
# -----------------------------------------------------------------------

GROUND_TRUTHS["banner-horizontal.jpg"] = {
    "id": "banner-horizontal",
    "canvas": {"width": 1920, "height": 1080, "detectedFormat": "horizontal"},
    "background": {"kind": "split", "left": "gradient(orange→amber)", "right": "photo"},
    "layers": [
        {"id": "left-gradient", "kind": "shape", "type": "gradient",
         "position": {"x": 0, "y": 0, "width": 960, "height": 1080},
         "color_start": "#ea580c", "color_end": "#fb923c", "z_index": 0},
        {"id": "right-photo", "kind": "image",
         "position": {"x": 960, "y": 0, "width": 960, "height": 1080},
         "opacity": 1.0, "z_index": 1},
        {"id": "transition-overlay", "kind": "shape", "type": "gradient-overlay",
         "position": {"x": 960, "y": 0, "width": 320, "height": 1080},
         "color": "#000000", "opacity": "gradient (0-200 alpha)", "z_index": 2},
        {"id": "title", "kind": "text", "text": "SALE",
         "font_size": 120, "bold": True, "color": "#ffffff",
         "alignment": "left", "position": {"x_pct": 0.06, "y_pct": 0.18}, "z_index": 3},
        {"id": "subtitle", "kind": "text", "text": "UP TO 50% OFF",
         "font_size": 56, "bold": False, "color": "#fffdf0",
         "alignment": "left", "position": {"x_pct": 0.06, "y_pct": 0.18, "offset_y": "title_h + 15"}, "z_index": 3},
        {"id": "detail", "kind": "text", "text": "Limited time · Select items",
         "font_size": 34, "bold": False, "color": "#ffdcb4",
         "alignment": "left", "position": {"x_pct": 0.06, "y_pct": 0.18, "offset_y": "title_h + sub_h + 25"}, "z_index": 3},
        {"id": "cta-btn", "kind": "shape", "type": "rounded-rect",
         "position": {"x_pct": 0.06, "y_pct": 0.65},
         "color": "#1a237e", "z_index": 3},
        {"id": "cta-text", "kind": "text", "text": "SHOP NOW  →",
         "font_size": 40, "bold": True, "color": "#ffffff",
         "alignment": "left", "position": {"x_pct": 0.06, "y_pct": 0.65, "offset_x": 20, "offset_y": 10}, "z_index": 4},
        {"id": "badge", "kind": "text", "text": "NEW ARRIVAL",
         "font_size": 32, "bold": True, "color": "#111827",
         "alignment": "left", "position": {"x": 990, "y": 31}, "z_index": 4},
        {"id": "badge-bg", "kind": "shape", "type": "rounded-rect",
         "position": {"x": 980, "y": 25},
         "color": "#eab308dc", "z_index": 4},
        {"id": "photo-label", "kind": "text", "text": "Premium Collection",
         "font_size": 42, "bold": True, "color": "#ffffff",
         "alignment": "center", "position": {"x": 1440, "y": 1000}, "z_index": 4},
    ],
    "element_count": 11,
    "text_count": 6,
    "image_count": 1,
    "shape_count": 4,
}


# -----------------------------------------------------------------------
# 6. poster-display-font.jpg   1080×1350
# -----------------------------------------------------------------------

GROUND_TRUTHS["poster-display-font.jpg"] = {
    "id": "poster-display-font",
    "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
    "background": {"kind": "photo-with-overlay", "color": "#000000a0"},
    "layers": [
        {"id": "bg-photo", "kind": "image",
         "position": {"x": 0, "y": 0, "width": 1080, "height": 1350},
         "opacity": 1.0, "z_index": 0},
        {"id": "dark-overlay", "kind": "shape", "type": "rectangle",
         "position": {"x": 0, "y": 0, "width": 1080, "height": 1350},
         "color": "#000000a0", "z_index": 1},
        {"id": "concentric-rings", "kind": "shape", "type": "ellipse",
         "position": {"cx": 540, "cy": 675},
         "color": "#ffffc8", "opacity": "radial (0-120 alpha)", "z_index": 1},
        {"id": "star-1", "kind": "text", "text": "✦",
         "font_size": 28, "bold": False, "color": "#eab308",
         "position": {"x": 120, "y": 150}, "z_index": 2},
        {"id": "star-2", "kind": "text", "text": "✦",
         "font_size": 28, "bold": False, "color": "#eab308",
         "position": {"x": 930, "y": 200}, "z_index": 2},
        {"id": "star-3", "kind": "text", "text": "✦",
         "font_size": 28, "bold": False, "color": "#eab308",
         "position": {"x": 200, "y": 1170}, "z_index": 2},
        {"id": "star-4", "kind": "text", "text": "✦",
         "font_size": 28, "bold": False, "color": "#eab308",
         "position": {"x": 900, "y": 1100}, "z_index": 2},
        {"id": "star-5", "kind": "text", "text": "✦",
         "font_size": 28, "bold": False, "color": "#eab308",
         "position": {"x": 540, "y": 80}, "z_index": 2},
        {"id": "star-6", "kind": "text", "text": "✦",
         "font_size": 28, "bold": False, "color": "#eab308",
         "position": {"x": 640, "y": 1200}, "z_index": 2},
        {"id": "display-text", "kind": "text", "text": "DREAM",
         "font_size": 120, "bold": True, "color": "#ffffff",
         "alignment": "center", "position": {"y_pct": 0.42}, "z_index": 3},
        {"id": "underline-top", "kind": "shape", "type": "line",
         "position": {"x1_pct": 0.15, "x2_pct": 0.85, "y_pct": 0.40},
         "color": "#eab308", "z_index": 3},
        {"id": "underline-bottom", "kind": "shape", "type": "line",
         "position": {"x1_pct": 0.15, "x2_pct": 0.85, "y_pct": 0.65},
         "color": "#eab308", "z_index": 3},
        {"id": "display-underline", "kind": "shape", "type": "line",
         "position": {"x_pct": 0.25, "x2_pct": 0.75, "y": "underline_y"},
         "color": "#eab308", "z_index": 3},
        {"id": "subtitle", "kind": "text", "text": "BIG · BOLD · BEAUTIFUL",
         "font_size": 44, "bold": False, "color": "#b4b4b4",
         "alignment": "center", "position": {"y": "underline_y + 20"}, "z_index": 3},
        {"id": "gold-dots", "kind": "shape", "type": "ellipse",
         "position": {}, "color": "#eab308", "z_index": 2},
    ],
    "element_count": 16,
    "text_count": 8,
    "image_count": 1,
    "shape_count": 7,
}


# -----------------------------------------------------------------------
# 7. poster-low-contrast.jpg   1080×1350
# -----------------------------------------------------------------------

GROUND_TRUTHS["poster-low-contrast.jpg"] = {
    "id": "poster-low-contrast",
    "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
    "background": {"kind": "solid", "color": "#e8e8e8"},
    "layers": [
        {"id": "noise-texture", "kind": "shape", "type": "texture",
         "position": {"x": 0, "y": 0, "width": 1080, "height": 1350},
         "color": "noise (5000 pixels, ±8 delta)", "z_index": 0},
        {"id": "border", "kind": "shape", "type": "rectangle",
         "position": {"x": 10, "y": 10, "width": 1060, "height": 1330},
         "color": "#dcdcdc", "z_index": 0},
        {"id": "title", "kind": "text", "text": "Whisper Collection",
         "font_size": 72, "bold": True, "color": "#c0c0c0",
         "alignment": "center", "position": {"y_pct": 0.08}, "z_index": 1},
        {"id": "subtitle", "kind": "text", "text": "barely visible elegance",
         "font_size": 38, "bold": False, "color": "#c8c8c8",
         "alignment": "center", "position": {"y_pct": 0.08, "offset_y": "title_h + 15"}, "z_index": 1},
        {"id": "divider", "kind": "shape", "type": "line",
         "position": {"x1_pct": 0.15, "x2_pct": 0.85, "y": "divider_y"},
         "color": "#d7d7d7", "z_index": 1},
        {"id": "body-0", "kind": "text", "text": "This design explores the boundaries",
         "font_size": 30, "bold": False, "color": "#c0c0c0",
         "alignment": "center", "position": {"y": "divider_y + 30"}, "z_index": 1},
        {"id": "body-1", "kind": "text", "text": "of visual perception through minimal",
         "font_size": 30, "bold": False, "color": "#c0c0c0",
         "alignment": "center", "position": {"y": "body_y + lh + 6"}, "z_index": 1},
        {"id": "body-2", "kind": "text", "text": "contrast ratios. Every element sits",
         "font_size": 30, "bold": False, "color": "#c0c0c0",
         "alignment": "center", "position": {"y": "body_y + lh + 6"}, "z_index": 1},
        {"id": "body-3", "kind": "text", "text": "close to the background value,",
         "font_size": 30, "bold": False, "color": "#c0c0c0",
         "alignment": "center", "position": {"y": "body_y + lh + 6"}, "z_index": 1},
        {"id": "body-4", "kind": "text", "text": "creating a subtle, almost ethereal",
         "font_size": 30, "bold": False, "color": "#c0c0c0",
         "alignment": "center", "position": {"y": "body_y + lh + 6"}, "z_index": 1},
        {"id": "body-5", "kind": "text", "text": "aesthetic that rewards close looking.",
         "font_size": 30, "bold": False, "color": "#c0c0c0",
         "alignment": "center", "position": {"y": "body_y + lh + 6"}, "z_index": 1},
        {"id": "body-6", "kind": "text", "text": "",
         "font_size": 30, "bold": False, "color": "#c0c0c0",
         "alignment": "center", "position": {}, "z_index": 1},
        {"id": "body-7", "kind": "text", "text": "— Design Philosophy, 2026",
         "font_size": 30, "bold": False, "color": "#c0c0c0",
         "alignment": "center", "position": {}, "z_index": 1},
        {"id": "meta", "kind": "text", "text": "www.whisper-design.studio · @whisper",
         "font_size": 26, "bold": False, "color": "#c3c3c3",
         "alignment": "center", "position": {"y_pct": 0.88}, "z_index": 1},
    ],
    "element_count": 14,
    "text_count": 11,
    "image_count": 0,
    "shape_count": 3,
}


# -----------------------------------------------------------------------
# 8. multi-photo-collage.jpg   1080×1350
# -----------------------------------------------------------------------

GROUND_TRUTHS["multi-photo-collage.jpg"] = {
    "id": "multi-photo-collage",
    "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
    "background": {"kind": "solid", "color": "#f8f9fa"},
    "layers": [
        {"id": "title", "kind": "text", "text": "PHOTO COLLAGE",
         "font_size": 72, "bold": True, "color": "#111827",
         "alignment": "center", "z_index": 0, "position": {"y": 25}},
        {"id": "subtitle", "kind": "text", "text": "Multi-image recognition test",
         "font_size": 36, "bold": False, "color": "#505050",
         "alignment": "center", "z_index": 0, "position": {"y": "title_y + title_h + 8"}},
        {"id": "photo-a", "kind": "image",
         "position": {"x": 54, "y": 405, "width": 594, "height": 540},
         "opacity": 1.0, "z_index": 1},
        {"id": "photo-a-label", "kind": "text", "text": "PHOTO A",
         "font_size": 26, "bold": True, "color": "#ffffff",
         "alignment": "left", "z_index": 2, "position": {"x": 64, "y": 415}},
        {"id": "photo-b", "kind": "image",
         "position": {"x": 432, "y": 338, "width": 486, "height": 432},
         "opacity": 0.75, "z_index": 2},
        {"id": "photo-b-border", "kind": "shape", "type": "rectangle",
         "position": {"x": 432, "y": 338, "width": 486, "height": 432},
         "color": "#ffffff", "z_index": 2},
        {"id": "photo-b-label", "kind": "text", "text": "PHOTO B",
         "font_size": 26, "bold": True, "color": "#ffffff",
         "alignment": "left", "z_index": 3, "position": {"x": 442, "y": 348}},
        {"id": "photo-c", "kind": "image",
         "position": {"x": 594, "y": 743, "width": 378, "height": 378},
         "opacity": 0.50, "z_index": 3},
        {"id": "photo-c-border", "kind": "shape", "type": "rectangle",
         "position": {"x": 594, "y": 743, "width": 378, "height": 378},
         "color": "#ffffff", "z_index": 3},
        {"id": "photo-c-label", "kind": "text", "text": "PHOTO C",
         "font_size": 26, "bold": True, "color": "#ffffff",
         "alignment": "left", "z_index": 4, "position": {"x": 604, "y": 753}},
    ],
    "element_count": 10,
    "text_count": 4,
    "image_count": 3,
    "shape_count": 3,
}


# -----------------------------------------------------------------------
# 9. portrait-overlay.jpg   1080×1350
# -----------------------------------------------------------------------

GROUND_TRUTHS["portrait-overlay.jpg"] = {
    "id": "portrait-overlay",
    "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
    "background": {"kind": "gradient", "color_start": "#3c1e64", "color_end": "#c85078"},
    "layers": [
        {"id": "person-photo", "kind": "image",
         "position": {"x_pct": 0.125, "y_pct": 0.15, "w_pct": 0.75, "h_pct": 0.60},
         "opacity": 1.0, "z_index": 0},
        {"id": "diagonal-bar", "kind": "shape", "type": "diagonal-band",
         "position": {"x": 378, "width": 70, "height": 1350},
         "color": "#ffffff", "opacity": "gradient (0-160 alpha)", "z_index": 1},
        {"id": "radial-overlay", "kind": "shape", "type": "circle",
         "position": {"cx_pct": 0.61, "cy_pct": 0.36, "r_pct": 0.21},
         "color": "#eab308", "opacity": "radial gradient (0-120 alpha)", "z_index": 1},
        {"id": "title", "kind": "text", "text": "PORTRAIT STUDY",
         "font_size": 52, "bold": True, "color": "#ffffff",
         "alignment": "center", "z_index": 2, "position": {"y": 30}},
        {"id": "subtitle", "kind": "text", "text": "Transparency · Overlay · Face detection",
         "font_size": 30, "bold": False, "color": "#fffdf0",
         "alignment": "center", "z_index": 2, "position": {"y": 1300}},
    ],
    "element_count": 5,
    "text_count": 2,
    "image_count": 1,
    "shape_count": 2,
}


# -----------------------------------------------------------------------
# 10. showcase-two-products.jpg   1080×1350
# -----------------------------------------------------------------------

GROUND_TRUTHS["showcase-two-products.jpg"] = {
    "id": "showcase-two-products",
    "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
    "background": {"kind": "solid", "color": "#ffffff"},
    "layers": [
        {"id": "title", "kind": "text", "text": "DUO COLLECTION",
         "font_size": 64, "bold": True, "color": "#111827",
         "alignment": "center", "z_index": 0, "position": {"y": 30}},
        {"id": "header-divider", "kind": "shape", "type": "line",
         "position": {"x1_pct": 0.10, "x2_pct": 0.90, "y": "title_y + title_h + 12"},
         "color": "#505050", "z_index": 0},
        {"id": "shadow-left", "kind": "shape", "type": "ellipse",
         "position": {"cx": 302, "y": "photo_y + photo_h", "rx": 162, "ry": 10},
         "color": "#0000003c", "z_index": 1},
        {"id": "product-left", "kind": "image",
         "position": {"cx": 302, "y": 338, "size": 324},
         "opacity": 1.0, "mask": "circle", "z_index": 2},
        {"id": "ring-left", "kind": "shape", "type": "ellipse",
         "position": {"cx": 302, "y": 338, "rx": 162, "ry": 162},
         "color": "#eab308c8", "z_index": 3},
        {"id": "reflection-left", "kind": "shape", "type": "reflection",
         "position": {"cx": 302, "y": "photo_y + photo_h", "width": 324, "height": 162},
         "opacity": "gradient (0-100 alpha)", "z_index": 2},
        {"id": "label-left", "kind": "text", "text": "CLASSIC",
         "font_size": 24, "bold": False, "color": "#505050",
         "alignment": "left", "z_index": 4, "position": {"x": 272, "y": "label_y"}},
        {"id": "price-left", "kind": "text", "text": "$49.99",
         "font_size": 36, "bold": True, "color": "#111827",
         "alignment": "left", "z_index": 4, "position": {"x": 262, "y": "price_y"}},
        {"id": "shadow-right", "kind": "shape", "type": "ellipse",
         "position": {"cx": 778, "y": "photo_y2 + photo_size2", "rx": 150, "ry": 10},
         "color": "#0000003c", "z_index": 1},
        {"id": "product-right", "kind": "image",
         "position": {"cx": 778, "y": 405, "size": 281},
         "opacity": 1.0, "mask": "rounded-rect", "z_index": 2},
        {"id": "gradient-overlay-right", "kind": "shape", "type": "gradient-overlay",
         "position": {"cx": 778, "y": "photo_y2 + photo_size2/2", "width": 281, "height": 140},
         "color": "#ffffc8", "opacity": "gradient (0-80 alpha)", "z_index": 3},
        {"id": "sale-badge", "kind": "text", "text": "-30%",
         "font_size": 28, "bold": True, "color": "#111827",
         "alignment": "left", "z_index": 4, "position": {"x": "badge_x", "y": "prod_y2 + 10"}},
        {"id": "label-right", "kind": "text", "text": "MODERN",
         "font_size": 24, "bold": False, "color": "#505050",
         "alignment": "left", "z_index": 4, "position": {"x": "right_cx - 35", "y": "label_y2"}},
        {"id": "price-right", "kind": "text", "text": "$79.99",
         "font_size": 36, "bold": True, "color": "#111827",
         "alignment": "left", "z_index": 4, "position": {"x": "right_cx - 45", "y": "price_y2"}},
        {"id": "cta-bar", "kind": "shape", "type": "rectangle",
         "position": {"x": 0, "y": 1290, "width": 1080, "height": 60},
         "color": "#1a237edc", "z_index": 5},
        {"id": "cta-text", "kind": "text", "text": "SHOP THE DUO · FREE SHIPPING",
         "font_size": 32, "bold": True, "color": "#ffffff",
         "alignment": "center", "z_index": 6, "position": {"y": 1308}},
    ],
    "element_count": 16,
    "text_count": 8,
    "image_count": 2,
    "shape_count": 6,
}


def get_ground_truth(image_id: str) -> dict | None:
    """Return the ground-truth SceneGraph for a given image stem or filename."""
    for key in (f"{image_id}.jpg", image_id, f"{image_id}.png"):
        if key in GROUND_TRUTHS:
            return GROUND_TRUTHS[key]
    return None
