"""
Ground truth definitions for the 10 synthetic fixture images.

Each function returns a ground-truth SceneGraph dict describing exactly what
the corresponding generator in ``generate_fixtures.py`` draws.  The structure
mirrors the model's SceneGraph output so we can compare them objectively.

Usage::

    from gt_helpers import GROUND_TRUTHS
    gt = GROUND_TRUTHS["poster-simple.jpg"]
"""

from __future__ import annotations


def _rgb_to_hex(c) -> str:
    return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}" if isinstance(c, (tuple, list)) else str(c)


def _build_poster_simple(size=(1080, 1350)):
    w, h = size
    return {
        "canvas": {"width": w, "height": h, "detectedFormat": "vertical"},
        "background": {"kind": "solid", "color": "#1a237e"},
        "layers": [
            {
                "id": "title",
                "kind": "text",
                "text": "SUMMER FEST",
                "position": {"x": round((w - tw) / 2) if (tw := ...) else 0, "y": round(h * 0.08)},
                "font_size": 96,
                "bold": True,
                "color": "#ffffff",
                "alignment": "center",
                "z_index": 0,
            },
        ],
    }
