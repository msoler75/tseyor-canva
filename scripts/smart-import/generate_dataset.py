"""
generate_dataset.py — Synthetic .tc v2 dataset generator.

Generates deterministic, procedurally-constructed .tc v2 JSON files
matching the format from ``docs/dev/fixtures/qa-visual-effects-matrix.tc``.

Usage::

    python generate_dataset.py --count 10 --seed 42 --output generated-dataset/

Dependencies: Python stdlib only (json, random, os, base64, datetime).
"""

from __future__ import annotations

import argparse
import base64
import datetime
import json
import math
import os
import random
import re
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Constants — Content Pools & Configuration
# ---------------------------------------------------------------------------

DESIGN_PALETTE: list[str] = [
    "#020617", "#0f172a", "#1e293b", "#312e81", "#4338ca",
    "#0ea5e9", "#06b6d4", "#14b8a6", "#22c55e", "#65a30d",
    "#f59e0b", "#f97316", "#ef4444", "#e11d48", "#db2777",
    "#f8fafc", "#e2e8f0", "#cbd5e1", "#94a3b8", "#475569",
]

FONT_FAMILIES: dict[str, str] = {
    "title": "Poppins, sans-serif",
    "subtitle": "Manrope, sans-serif",
    "body": "Montserrat, sans-serif",
    "label": "Manrope, sans-serif",
}

FONT_SIZES: dict[str, list[int]] = {
    "title": list(range(32, 65)),
    "subtitle": list(range(18, 37)),
    "body": list(range(10, 25)),
    "label": list(range(8, 17)),
}

FONT_WEIGHTS: dict[str, str] = {
    "title": "bold",
    "subtitle": "regular",
    "body": "medium",
    "label": "regular",
}

# Position bounds on a 1080x1350 canvas
POSITION_RANGES: dict[str, dict[str, int]] = {
    "x": {"min": 20, "max": 900},
    "y": {"min": 20, "max": 1250},
    "w": {"min": 60, "max": 800},
    "h": {"min": 30, "max": 500},
}

SCENARIO_TITLES: list[str] = [
    "Summer Sale Banner",
    "Product Launch Event",
    "Webinar Invitation",
    "New Collection Drop",
    "Flash Deal Alert",
    "Brand Awareness Campaign",
    "Holiday Promotion",
    "Social Media Giveaway",
    "Workshop Registration",
    "Exclusive Preview",
    "Seasonal Special",
    "VIP Access Offer",
    "Behind the Scenes",
    "Limited Edition Release",
    "Community Spotlight",
]

TEXT_PHRASES: list[str] = [
    # Short phrases
    "Limited time offer",
    "Sign up today",
    "Learn more",
    "Shop now",
    "Don't miss out",
    "Exclusive access",
    "Claim your spot",
    "Reserve your seat",
    "Early bird pricing",
    "Free shipping",
    "While supplies last",
    "Members only",
    "New arrivals",
    "Back in stock",
    "Bundle and save",
    "Available now",
    "Pre-order today",
    "Get started free",
    "Upgrade your experience",
    "Join the waitlist",
    # Longer text for body elements
    "Discover our latest collection of handcrafted products designed to elevate your everyday style. Each piece is made with sustainable materials and a commitment to quality that lasts.",
    "Join thousands of satisfied customers who have transformed their workflow with our all-in-one platform. From project management to team collaboration, we've got you covered.",
    "Limited time offer: Get 40% off your first purchase when you subscribe to our newsletter today. Plus, enjoy free shipping on all orders over $50. Terms and conditions apply.",
    "Our mission is to make professional design accessible to everyone. With intuitive tools, thousands of templates, and real-time collaboration, anyone can create stunning visuals.",
    "Transform your space with our curated selection of modern furniture and home decor. From minimalist Scandinavian designs to bold contemporary pieces, find your perfect look.",
    "Join us for an exclusive workshop where industry experts share insider tips on digital marketing, brand strategy, and content creation that actually converts.",

]

PLATFORMS: list[str] = [
    "Instagram", "Facebook", "Twitter", "LinkedIn",
    "YouTube", "TikTok", "Pinterest", "Email",
]

SHAPE_KINDS: list[str] = [
    "diamond", "parallelogram", "trapezoid", "trapezoid-inv",
    "triangle-up", "triangle-right-angle", "triangle-down", "triangle-right", "triangle-left",
    "pentagon", "hexagon", "octagon",
    "star-5", "star-4", "star-6", "star-burst",
    "arrow-right", "arrow-curved", "arrow-left", "arrow-up", "arrow-down",
    "arrow-double-h", "arrow-double-v",
    "chevron-right", "chevron-left",
    "cross", "x-mark",
    "heart",
    "badge", "ribbon",
    "frame", "frame-thick", "frame-thin", "frame-notch",
    "callout", "callout-ellipse", "callout-cloud", "callout-burst",
    "callout-top", "callout-left", "callout-right",
]

EFFECT_PROBABILITIES: dict[str, float] = {
    "shadow": 0.30,
    "border": 0.45,
    "gradient": 0.25,
    "transparency": 0.40,
    "text_effect": 0.12,
}

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1350

# ---------------------------------------------------------------------------
# SVG Pattern Generator (lazy cache)
# ---------------------------------------------------------------------------


class SVGPatternGenerator:
    """Generates small SVG patterns encoded as base64 data URIs.

    Results are cached by ``(pattern_type, color_a, color_b)`` so each
    unique combination is rendered only once per process.
    """

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str, str], str] = {}

    def _data_uri(self, svg: str) -> str:
        return "data:image/svg+xml;base64," + base64.b64encode(
            svg.encode("utf-8")
        ).decode("ascii")

    def checkerboard(self, color_a: str, color_b: str, size: int = 80) -> str:
        """8×8 checkerboard, 80×80 viewBox, two alternating colors."""
        key = ("checker", color_a, color_b)
        if key not in self._cache:
            half = size // 2
            cells = []
            for row in range(2):
                for col in range(2):
                    fill = color_a if (row + col) % 2 == 0 else color_b
                    cells.append(
                        f'<rect x="{col * half}" y="{row * half}" '
                        f'width="{half}" height="{half}" fill="{fill}"/>'
                    )
            svg = (
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{size}" height="{size}" '
                f'viewBox="0 0 {size} {size}">'
                f'{"".join(cells)}'
                f'</svg>'
            )
            self._cache[key] = self._data_uri(svg)
        return self._cache[key]

    def dots(
        self, pattern_color: str, bg_color: str, size: int = 40
    ) -> str:
        """40×40 pattern unit, centered circles."""
        key = ("dots", pattern_color, bg_color)
        if key not in self._cache:
            r = size * 0.2
            svg = (
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{size}" height="{size}" '
                f'viewBox="0 0 {size} {size}">'
                f'<rect width="{size}" height="{size}" fill="{bg_color}"/>'
                f'<circle cx="{size * 0.25}" cy="{size * 0.25}" '
                f'r="{r}" fill="{pattern_color}"/>'
                f'<circle cx="{size * 0.75}" cy="{size * 0.75}" '
                f'r="{r}" fill="{pattern_color}"/>'
                f'</svg>'
            )
            self._cache[key] = self._data_uri(svg)
        return self._cache[key]

    def stripes(
        self, pattern_color: str, bg_color: str, size: int = 40
    ) -> str:
        """Diagonal stripes at 45°, configurable stroke."""
        key = ("stripes", pattern_color, bg_color)
        if key not in self._cache:
            svg = (
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{size}" height="{size}" '
                f'viewBox="0 0 {size} {size}">'
                f'<rect width="{size}" height="{size}" fill="{bg_color}"/>'
                f'<line x1="0" y1="0" x2="{size}" y2="{size}" '
                f'stroke="{pattern_color}" stroke-width="4"/>'
                f'<line x1="0" y1="{size}" x2="{size}" y2="0" '
                f'stroke="{pattern_color}" stroke-width="4"/>'
                f'</svg>'
            )
            self._cache[key] = self._data_uri(svg)
        return self._cache[key]

    def generate(self, pattern_type: str, c1: str, c2: str) -> str:
        """Dispatch to the appropriate pattern method."""
        if pattern_type == "checkerboard":
            return self.checkerboard(c1, c2)
        elif pattern_type == "dots":
            return self.dots(c1, c2)
        else:
            return self.stripes(c1, c2)


# ---------------------------------------------------------------------------
# Effect Coverage Tracker
# ---------------------------------------------------------------------------


class EffectCoverageTracker:
    """Tracks effect coverage per page to enforce minimum percentages."""

    def __init__(self) -> None:
        self._total_elements = 0
        self._total_shapes = 0
        self._total_text = 0
        self._shadow_count = 0
        self._border_count = 0
        self._gradient_count = 0
        self._transparency_count = 0
        self._text_effect_count = 0

    def count_element(self, el_type: str) -> None:
        self._total_elements += 1
        if el_type == "shape":
            self._total_shapes += 1
        elif el_type == "text":
            self._total_text += 1

    def count_shadow(self) -> None:
        self._shadow_count += 1

    def count_border(self) -> None:
        self._border_count += 1

    def count_gradient(self) -> None:
        self._gradient_count += 1

    def count_transparency(self) -> None:
        self._transparency_count += 1

    def count_text_effect(self) -> None:
        self._text_effect_count += 1

    def shadow_ok(self) -> bool:
        if self._total_elements == 0:
            return True
        return (self._shadow_count / self._total_elements) >= 0.30

    def border_ok(self) -> bool:
        if self._total_elements == 0:
            return True
        return (self._border_count / self._total_elements) >= 0.30

    def gradient_ok(self) -> bool:
        if self._total_shapes == 0:
            return True
        return (self._gradient_count / self._total_shapes) >= 0.20

    def transparency_ok(self) -> bool:
        if self._total_elements == 0:
            return True
        return (self._transparency_count / self._total_elements) >= 0.40

    def text_effect_ok(self) -> bool:
        if self._total_text == 0:
            return True
        return (self._text_effect_count / self._total_text) >= 0.10

    def all_ok(self) -> bool:
        return (
            self.shadow_ok()
            and self.border_ok()
            and self.gradient_ok()
            and self.transparency_ok()
            and self.text_effect_ok()
        )

    def summary(self) -> dict:
        return {
            "total": self._total_elements,
            "shapes": self._total_shapes,
            "texts": self._total_text,
            "shadow%": round(self._shadow_count / max(self._total_elements, 1) * 100),
            "border%": round(self._border_count / max(self._total_elements, 1) * 100),
            "gradient%": round(self._gradient_count / max(self._total_shapes, 1) * 100),
            "transparency%": round(self._transparency_count / max(self._total_elements, 1) * 100),
            "text_effect%": round(self._text_effect_count / max(self._total_text, 1) * 100),
        }


# ---------------------------------------------------------------------------
# Layout Composer (AABB collision avoidance)
# ---------------------------------------------------------------------------


class LayoutComposer:
    """Assigns positions for elements with AABB collision avoidance.

    Set ``self.allow_overlap`` to ``True`` to allow elements to overlap
    (for layered/complex designs).
    """

    def __init__(self) -> None:
        self._max_retries = 5
        self.allow_overlap = False

    @staticmethod
    def _aabb_overlap_area(a: tuple, b: tuple) -> float:
        """Return the overlap area between two bounding boxes.

        Each box is ``(x, y, w, h)``.
        """
        a_x, a_y, a_w, a_h = a
        b_x, b_y, b_w, b_h = b

        x_overlap = max(0, min(a_x + a_w, b_x + b_w) - max(a_x, b_x))
        y_overlap = max(0, min(a_y + a_h, b_y + b_h) - max(a_y, b_y))
        return float(x_overlap * y_overlap)

    def assign_position(
        self, existing: list[tuple], el_type: str,
        allow_overlap: bool = False,
    ) -> tuple:
        """Return ``(x, y, w, h)`` with collision avoidance.

        When ``allow_overlap=True``, the position may intentionally
        overlap existing elements (for layered/complex designs).

        For text elements (title/subtitle), ``h`` is returned as 0 and
        the caller should omit it from the output.
        """
        is_text = el_type in ("text_title", "text_subtitle", "text_body", "text_label")

        for attempt in range(self._max_retries + 1):
            if is_text:
                w = random.randint(200, 800)
                h = 0  # text height is computed by the renderer
            elif el_type == "qr":
                w = random.randint(80, 160)
                h = w  # QR codes are square
            else:
                w = random.randint(
                    POSITION_RANGES["w"]["min"], POSITION_RANGES["w"]["max"]
                )
                h = random.randint(
                    POSITION_RANGES["h"]["min"], POSITION_RANGES["h"]["max"]
                )

            x = random.randint(
                POSITION_RANGES["x"]["min"],
                min(POSITION_RANGES["x"]["max"], CANVAS_WIDTH - w - 10),
            )
            y = random.randint(
                POSITION_RANGES["y"]["min"],
                min(POSITION_RANGES["y"]["max"], CANVAS_HEIGHT - h - 10),
            )

            # Clamp within canvas
            x = max(0, min(x, CANVAS_WIDTH - w))
            y = max(0, min(y, CANVAS_HEIGHT - h))

            candidate = (x, y, w, h)
            if allow_overlap or self.allow_overlap:
                return candidate
            if self._is_valid_position(candidate, existing):
                return candidate

        # Fallback: place at a deterministic position
        idx = len(existing)
        x = 20 + (idx * 30) % 800
        y = 100 + (idx * 50) % 1000
        return (x, y, max(w, 100), max(h, 50))

    def _is_valid_position(
        self, candidate: tuple, existing: list[tuple]
    ) -> bool:
        """Return True if ``candidate`` does not significantly overlap."""
        cx, cy, cw, ch = candidate
        if ch == 0:
            ch = 50  # assume default text height for overlap calc
        candidate_area = cw * ch
        if candidate_area <= 0:
            return True

        for rect in existing:
            rx, ry, rw, rh = rect
            if rh == 0:
                rh = 50
            overlap = self._aabb_overlap_area(
                (cx, cy, cw, ch), (rx, ry, rw, rh)
            )
            if overlap / candidate_area > 0.5:
                return False
        return True


# ---------------------------------------------------------------------------
# Effects Composer
# ---------------------------------------------------------------------------

# Singleton pattern generator
_SVG_GEN: SVGPatternGenerator | None = None


def _svg() -> SVGPatternGenerator:
    global _SVG_GEN
    if _SVG_GEN is None:
        _SVG_GEN = SVGPatternGenerator()
    return _SVG_GEN


class EffectsComposer:
    """Applies effects (shadow, border, gradient, transparency, text fx)
    to element layout entries."""

    @staticmethod
    def maybe_apply_shadow(
        tracker: EffectCoverageTracker, force: bool = False
    ) -> dict:
        """Return shadow-effect fields."""
        apply = force or random.random() < EFFECT_PROBABILITIES["shadow"]
        if not apply:
            return {
                "shadow": False,
                "shadowPreset": "soft",
                "shadowColor": "#0f172a",
                "shadowAngle": 135,
                "shadowOffset": round(random.uniform(2, 8), 2),
                "shadowBlur": round(random.uniform(4, 12), 2),
                "shadowOpacity": 30,
            }
        tracker.count_shadow()
        return {
            "shadow": True,
            "shadowPreset": random.choice(["soft", "lifted"]),
            "shadowColor": random.choice(
                ["#0f172a", "#1e293b", "#020617", "#475569"]
            ),
            "shadowAngle": random.randint(0, 360),
            "shadowOffset": round(random.uniform(2, 20), 2),
            "shadowBlur": round(random.uniform(4, 30), 2),
            "shadowOpacity": random.randint(20, 80),
        }

    @staticmethod
    def maybe_apply_border(
        tracker: EffectCoverageTracker, force: bool = False
    ) -> dict:
        """Return border/stroke-effect fields."""
        apply = force or random.random() < EFFECT_PROBABILITIES["border"]
        if not apply:
            return {
                "border": False,
                "borderStyle": "solid",
                "contourWidth": 0.0,
                "contourColor": "#ffffff",
            }
        tracker.count_border()
        return {
            "border": True,
            "borderStyle": random.choice(["solid", "dashed", "dotted"]),
            "contourWidth": round(random.uniform(1, 40), 2),
            "contourColor": random.choice(DESIGN_PALETTE),
        }

    @staticmethod
    def maybe_apply_gradient(
        tracker: EffectCoverageTracker, is_shape: bool = False,
        force: bool = False,
    ) -> dict:
        """Return gradient fill fields (shape elements only)."""
        if not is_shape:
            return {"fillMode": "solid"}
        apply = force or random.random() < EFFECT_PROBABILITIES["gradient"]
        if not apply:
            return {"fillMode": "solid"}
        tracker.count_gradient()
        c1, c2 = random.sample(DESIGN_PALETTE, 2)
        return {
            "fillMode": "gradient",
            "gradientStart": c1,
            "gradientEnd": c2,
            "gradientAngle": random.randint(0, 360),
        }

    @staticmethod
    def maybe_apply_transparency(
        tracker: EffectCoverageTracker, force: bool = False
    ) -> dict:
        """Return transparency-effect fields."""
        apply = force or random.random() < EFFECT_PROBABILITIES["transparency"]
        if not apply:
            return {
                "transparencyType": "flat",
                "transparencyFadeOpacity": 0,
                "transparencyCenterX": 50,
                "transparencyCenterY": 50,
                "transparencyRadius": 70,
                "transparencyRadiusX": 70,
                "transparencyRadiusY": 45,
                "transparencyRotation": 0,
                "transparencyStartX": 0,
                "transparencyStartY": 50,
                "transparencyEndX": 100,
                "transparencyEndY": 50,
                "transparencyEasing": "linear",
            }
        tracker.count_transparency()
        ttype = random.choice(["circle", "ellipse", "linear"])
        base = {
            "transparencyType": ttype,
            "transparencyFadeOpacity": random.randint(0, 100),
            "transparencyCenterX": random.randint(20, 80),
            "transparencyCenterY": random.randint(20, 80),
            "transparencyRadius": random.randint(30, 90),
            "transparencyRadiusX": random.randint(30, 90),
            "transparencyRadiusY": random.randint(20, 80),
            "transparencyRotation": random.randint(0, 360),
            "transparencyStartX": random.randint(0, 30),
            "transparencyStartY": random.randint(20, 80),
            "transparencyEndX": random.randint(70, 100),
            "transparencyEndY": random.randint(20, 80),
            "transparencyEasing": random.choice(["linear", "smoothstep"]),
        }
        return base

    @staticmethod
    def maybe_apply_text_effects(
        tracker: EffectCoverageTracker, force: bool = False
    ) -> dict:
        """Return text-effect fields (text elements only)."""
        apply = force or random.random() < EFFECT_PROBABILITIES["text_effect"]
        if not apply:
            return {
                "neonColor": "",
                "neonIntensity": 55,
                "misalignedThickness": 0.0,
                "hollowText": False,
                "bubbleColor": "",
                "contourWidth": 0.0,
                "contourColor": "#ffffff",
            }
        tracker.count_text_effect()
        effect_type = random.choice(["neon", "contour", "hollow"])
        result: dict[str, Any] = {
            "misalignedThickness": 0.0,
            "bubbleColor": "",
        }
        if effect_type == "neon":
            result["neonColor"] = random.choice(
                ["#f59e0b", "#0ea5e9", "#ef4444", "#22c55e"]
            )
            result["neonIntensity"] = random.randint(30, 100)
            result["hollowText"] = False
            result["contourWidth"] = 0.0
            result["contourColor"] = "#ffffff"
        elif effect_type == "contour":
            result["neonColor"] = ""
            result["neonIntensity"] = 55
            result["hollowText"] = False
            result["contourWidth"] = round(random.uniform(0.5, 4.0), 2)
            result["contourColor"] = random.choice(DESIGN_PALETTE)
        else:  # hollow
            result["neonColor"] = ""
            result["neonIntensity"] = 55
            result["hollowText"] = True
            result["contourWidth"] = round(random.uniform(0.5, 3.0), 2)
            result["contourColor"] = random.choice(DESIGN_PALETTE)
        return result

    @staticmethod
    def base_text_layout_fields() -> dict:
        """Return the common set of layout fields present on all text
        elements (title, subtitle, body text, labels, notes)."""
        return {
            "borderStyle": "solid",
            "italic": random.choice([True, False]) if random.random() < 0.15 else False,
            "uppercase": random.choice([True, False]) if random.random() < 0.1 else False,
            "letterSpacing": round(random.uniform(-1, 5), 1),
            "lineHeight": round(random.uniform(0.8, 2.0), 2),
            "textEffectMode": "",
            "imageCropScale": 1,
            "imageCropOffsetX": 0,
            "imageCropOffsetY": 0,
            "flipX": False,
            "flipY": False,
            "backgroundColor": "transparent",
            "backgroundRoundness": 45,
            "backgroundPadding": 0.0,
            "backgroundOpacity": 70,
        }

    @staticmethod
    def base_shape_layout_fields() -> dict:
        """Return the common set of layout fields present on all shape
        elements (chips, shapes, image backgrounds, QR)."""
        return {
            "borderStyle": "solid",
            "neonColor": "",
            "neonIntensity": 55,
            "bubbleColor": "",
            "imageCropScale": 1,
            "imageCropOffsetX": 0,
            "imageCropOffsetY": 0,
            "flipX": False,
            "flipY": False,
            "imageTintColor": "#0f172a",
            "imageTintStrength": 0,
        }


# ---------------------------------------------------------------------------
# Element Generators
# ---------------------------------------------------------------------------


def generate_background() -> dict:
    """Generate the background elementLayout entry."""
    is_gradient = random.random() < 0.5
    bg: dict = {}
    if is_gradient:
        c1, c2 = random.sample(DESIGN_PALETTE, 2)
        bg["backgroundColor"] = c1
        bg["fillMode"] = "gradient"
        bg["gradientStart"] = c1
        bg["gradientEnd"] = c2
        bg["gradientAngle"] = random.randint(0, 360)
    else:
        bg["backgroundColor"] = random.choice(DESIGN_PALETTE)
        bg["fillMode"] = "solid"

    bg.update({
        "backgroundImageSrc": None,
        "backgroundImageAssetId": None,
        "backgroundImagePendingDataUrl": None,
        "backgroundImageStoragePath": None,
        "backgroundImageWidth": 1200,
        "backgroundImageHeight": 1200,
        "backgroundImageCropScale": 1,
        "backgroundImageCropOffsetX": 0,
        "backgroundImageCropOffsetY": 0,
        "backgroundImageFlipX": False,
        "backgroundImageFlipY": False,
        "backgroundImageOpacity": random.randint(10, 40),
        "backgroundImageTransparencyType": "linear",
        "backgroundImageTransparencyFadeOpacity": 0,
        "backgroundImageTransparencyCenterX": 50,
        "backgroundImageTransparencyCenterY": 50,
        "backgroundImageTransparencyRadius": 70,
        "backgroundImageTransparencyRadiusX": 70,
        "backgroundImageTransparencyRadiusY": 45,
        "backgroundImageTransparencyRotation": 0,
        "backgroundImageTransparencyStartX": 0,
        "backgroundImageTransparencyStartY": 50,
        "backgroundImageTransparencyEndX": 100,
        "backgroundImageTransparencyEndY": 50,
        "backgroundImageTransparencyEasing": "linear",
    })
    return bg


def generate_title_subtitle(
    role: str, text: str, page_prefix: str,
    tracker: EffectCoverageTracker,
    composer: LayoutComposer, existing: list[tuple],
    force: bool = False,
) -> tuple[dict, dict]:
    """Generate elementLayout and customElements for a title or subtitle."""
    is_title = role == "title"
    family = FONT_FAMILIES["title"] if is_title else FONT_FAMILIES["subtitle"]
    size = random.choice(FONT_SIZES["title"] if is_title else FONT_SIZES["subtitle"])
    weight = FONT_WEIGHTS["title"] if is_title else FONT_WEIGHTS["subtitle"]
    key = role
    color = random.choice(
        ["#ffffff", "#f8fafc", "#bae6fd", "#fef3c7", "#f1f5f9"]
    )

    pos = composer.assign_position(existing, f"text_{role}")
    x, y, w, _ = pos
    z_index = random.randint(60, 100)

    effects = EffectsComposer()
    layout: dict = {
        "x": float(x),
        "y": float(y),
        "w": float(w),
        "zIndex": z_index,
        "fontSize": float(size),
        "color": color,
        "fontFamily": family,
        "fontWeight": weight,
        "textAlign": "center" if is_title else random.choice(["left", "center", "right", "justify"]),
        "opacity": random.randint(85, 100),
    }
    layout.update(effects.base_text_layout_fields())

    # Effects
    shadow = effects.maybe_apply_shadow(tracker, force=force)
    border = effects.maybe_apply_border(tracker, force=force)
    tex_eff = effects.maybe_apply_text_effects(tracker, force=force)
    transp = effects.maybe_apply_transparency(tracker, force=force)
    layout.update(shadow)
    layout.update(border)
    layout.update(tex_eff)
    layout.update(transp)

    # paragraphStyles
    layout["paragraphStyles"] = [
        {
            "fontSize": float(size),
            "color": color,
            "fontFamily": family,
            "fontWeight": weight,
            "italic": False,
            "uppercase": False,
            "textAlign": layout["textAlign"],
            "letterSpacing": layout["letterSpacing"],
            "lineHeight": layout["lineHeight"],
        }
    ]

    tracker.count_element("text")
    custom: dict = {
        "id": key,
        "type": "text",
        "text": text,
        "html": text,
    }

    existing.append(pos)
    return layout, custom


def generate_body_text(
    key: str, page_prefix: str,
    tracker: EffectCoverageTracker,
    composer: LayoutComposer, existing: list[tuple],
    force: bool = False,
) -> tuple[dict, dict]:
    """Generate a body text element (pN-text-N, pN-label-N, pN-note-N)."""
    text = random.choice(TEXT_PHRASES)
    is_label = "label" in key
    role = "label" if is_label else "body"
    family = FONT_FAMILIES.get(role, FONT_FAMILIES["body"])
    size = random.choice(FONT_SIZES.get(role, FONT_SIZES["body"]))
    weight = FONT_WEIGHTS.get(role, FONT_WEIGHTS["body"])

    pos = composer.assign_position(existing, f"text_{role}")
    x, y, w, _ = pos
    z_index = max(10, random.randint(10, 70))

    effects = EffectsComposer()
    layout: dict = {
        "x": float(x),
        "y": float(y),
        "w": float(w),
        "zIndex": z_index,
        "fontSize": float(size),
        "color": random.choice(DESIGN_PALETTE),
        "fontFamily": family,
        "fontWeight": weight,
        "textAlign": random.choice(["left", "center", "right"]),
        "opacity": random.randint(70, 100),
    }
    layout.update(effects.base_text_layout_fields())

    shadow = effects.maybe_apply_shadow(tracker, force=force)
    border = effects.maybe_apply_border(tracker, force=force)
    tex_eff = effects.maybe_apply_text_effects(tracker, force=force)
    transp = effects.maybe_apply_transparency(tracker, force=force)
    layout.update(shadow)
    layout.update(border)
    layout.update(tex_eff)
    layout.update(transp)

    layout["paragraphStyles"] = [
        {
            "fontSize": float(size),
            "color": layout["color"],
            "fontFamily": family,
            "fontWeight": weight,
            "italic": False,
            "uppercase": False,
            "textAlign": layout["textAlign"],
            "letterSpacing": layout["letterSpacing"],
            "lineHeight": layout["lineHeight"],
        }
    ]

    tracker.count_element("text")
    custom: dict = {
        "id": key,
        "type": "text",
        "label": text[:30],
        "text": text,
        "html": text,
    }

    existing.append(pos)
    return layout, custom


def generate_shape_element(
    key: str, page_prefix: str,
    tracker: EffectCoverageTracker,
    composer: LayoutComposer, existing: list[tuple],
    force: bool = False,
) -> tuple[dict, dict]:
    """Generate a shape (rectangle) element."""
    pos = composer.assign_position(existing, "shape")
    x, y, w, h = pos
    z_index = max(10, random.randint(10, 60))

    effects = EffectsComposer()
    layout: dict = {
        "x": float(x),
        "y": float(y),
        "w": float(w),
        "h": float(h),
        "zIndex": z_index,
        "rotation": round(random.uniform(-15, 15), 2),
        "opacity": random.randint(20, 100),
    }
    layout.update(effects.base_shape_layout_fields())

    # Border radius
    br = round(random.uniform(0, 20), 2)
    layout["borderRadius"] = br
    layout["borderRadiusTopLeft"] = br
    layout["borderRadiusTopRight"] = br
    layout["borderRadiusBottomRight"] = br
    layout["borderRadiusBottomLeft"] = br

    # Background
    bg_color = random.choice(DESIGN_PALETTE)
    layout["backgroundColor"] = bg_color

    # Effects
    shadow = effects.maybe_apply_shadow(tracker, force=force)
    border = effects.maybe_apply_border(tracker, force=force)
    grad = effects.maybe_apply_gradient(tracker, is_shape=True, force=force)
    transp = effects.maybe_apply_transparency(tracker, force=force)
    layout.update(shadow)
    layout.update(border)
    layout.update(grad)
    layout.update(transp)

    tracker.count_element("shape")
    custom: dict = {
        "id": key,
        "type": "shape",
        "shapeKind": random.choice(SHAPE_KINDS),
        "label": f"Shape {key}",
    }

    existing.append(pos)
    return layout, custom


# Path to local placeholder images (downloaded by sub-agent)
PLACEHOLDER_IMAGE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "public", "uploads",
)
# URL path prefix for serving via the app server
PLACEHOLDER_URL_PREFIX = "/uploads"


def _local_images() -> list[str]:
    """Return paths to locally downloaded placeholder images.

    Only returns files matching ``placeholder-*`` to ensure consistent
    high-quality stock photos (downloaded from picsum.photos).
    """
    if not os.path.isdir(PLACEHOLDER_IMAGE_DIR):
        return []
    files = sorted(
        f for f in os.listdir(PLACEHOLDER_IMAGE_DIR)
        if f.lower().startswith("placeholder-")
        and f.lower().endswith((".jpg", ".jpeg", ".png"))
    )
    return files


def generate_image_placeholder(
    key: str, page_prefix: str,
    tracker: EffectCoverageTracker,
    composer: LayoutComposer, existing: list[tuple],
    force: bool = False,
) -> tuple[dict, dict]:
    """Generate an image placeholder element.

    Uses real images from ``public/uploads/`` when available, falls back
    to base64 SVG patterns.
    """
    pos = composer.assign_position(existing, "shape")
    x, y, w, h = pos
    z_index = max(5, random.randint(5, 30))

    local_files = _local_images()
    if local_files:
        # Use a real downloaded image
        chosen = random.choice(local_files)
        src = f"{PLACEHOLDER_URL_PREFIX}/{chosen}"
        # Real images do NOT need upload — the server already hosts them.
        # (The editor import logic overrides needsUpload to True, but the
        #  upload is skipped for non-data: src values. The image renders
        #  directly from src.)
        upload_status = "ready"
        needs_upload = False
    else:
        # Fallback: base64 SVG pattern
        c1 = random.choice(DESIGN_PALETTE)
        c2 = random.choice(DESIGN_PALETTE)
        pat_type = random.choice(["checkerboard", "dots", "stripes"])
        src = _svg().generate(pat_type, c1, c2)
        upload_status = "pending"
        needs_upload = True

    effects = EffectsComposer()
    layout: dict = {
        "x": float(x),
        "y": float(y),
        "w": float(w),
        "h": float(h),
        "zIndex": z_index,
        "rotation": round(random.uniform(-10, 10), 2),
        "opacity": random.randint(50, 100),
    }
    layout.update(effects.base_shape_layout_fields())

    br = round(random.uniform(0, 16), 2)
    layout["borderRadius"] = br
    layout["borderRadiusTopLeft"] = br
    layout["borderRadiusTopRight"] = br
    layout["borderRadiusBottomRight"] = br
    layout["borderRadiusBottomLeft"] = br
    layout["backgroundColor"] = "transparent"

    shadow = effects.maybe_apply_shadow(tracker, force=force)
    border = effects.maybe_apply_border(tracker, force=force)
    transp = effects.maybe_apply_transparency(tracker, force=force)
    layout.update(shadow)
    layout.update(border)
    layout.update({"fillMode": "solid"})
    layout.update(transp)

    tracker.count_element("image")
    custom: dict = {
        "id": key,
        "type": "image",
        "label": f"Image {key}",
        "src": src,
        "intrinsicWidth": w,
        "intrinsicHeight": h,
        "uploadStatus": upload_status,
        "needsUpload": needs_upload,
    }

    existing.append(pos)
    return layout, custom


def generate_qr_placeholder(
    key: str, page_prefix: str,
    tracker: EffectCoverageTracker,
    composer: LayoutComposer, existing: list[tuple],
    force: bool = False,
) -> tuple[dict, dict]:
    """Generate a QR code placeholder element."""
    pos = composer.assign_position(existing, "qr")
    x, y, w, h = pos
    z_index = max(10, random.randint(10, 50))

    effects = EffectsComposer()
    layout: dict = {
        "x": float(x),
        "y": float(y),
        "w": float(w),
        "h": float(h),
        "zIndex": z_index,
        "rotation": round(random.uniform(-5, 5), 2),
        "opacity": random.randint(70, 100),
    }
    layout.update(effects.base_shape_layout_fields())

    br = round(random.uniform(0, 12), 2)
    layout["borderRadius"] = br
    layout["borderRadiusTopLeft"] = br
    layout["borderRadiusTopRight"] = br
    layout["borderRadiusBottomRight"] = br
    layout["borderRadiusBottomLeft"] = br
    layout["backgroundColor"] = "#ffffff"

    shadow = effects.maybe_apply_shadow(tracker, force=force)
    border = effects.maybe_apply_border(tracker, force=force)
    transp = effects.maybe_apply_transparency(tracker, force=force)
    layout.update(shadow)
    layout.update(border)
    layout.update({"fillMode": "solid"})
    layout.update(transp)

    tracker.count_element("qr")
    fake_url = f"https://tseyor.test/qr/{page_prefix}-{key}"
    custom: dict = {
        "id": key,
        "type": "qr",
        "label": f"QR {key}",
        "url": fake_url,
        "uploadStatus": "generated",
    }

    existing.append(pos)
    return layout, custom


# ---------------------------------------------------------------------------
# Page Generator
# ---------------------------------------------------------------------------


class PageGenerator:
    """Generates a single page dict with content, elementLayout, and
    customElements."""

    def __init__(self) -> None:
        self.composer = LayoutComposer()

    @staticmethod
    def _boost_coverage(
        tracker: EffectCoverageTracker,
        element_layout: dict,
        custom_elements: dict,
    ) -> None:
        """Retroactively apply effects to meet coverage thresholds.

        For any effect below its minimum threshold, randomly applies the
        effect to eligible layout elements until the threshold is met.
        This keeps variety (random which elements get the effect) while
        guaranteeing the spec thresholds.

        Note: ``maybe_apply_*(force=True)`` calls already increment the
        tracker counters — do NOT call ``tracker.count_*()`` again here.
        """
        effect = EffectsComposer()
        eligible_keys = [k for k in element_layout if k != "background"]
        random.shuffle(eligible_keys)

        # Shadow boost
        if not tracker.shadow_ok():
            for k in eligible_keys:
                props = element_layout[k]
                if not props.get("shadow"):
                    props.update(effect.maybe_apply_shadow(tracker, force=True))
                    if tracker.shadow_ok():
                        break

        # Border boost
        if not tracker.border_ok():
            for k in eligible_keys:
                props = element_layout[k]
                if not props.get("border"):
                    props.update(effect.maybe_apply_border(tracker, force=True))
                    if tracker.border_ok():
                        break

        # Transparency boost
        if not tracker.transparency_ok():
            for k in eligible_keys:
                props = element_layout[k]
                if props.get("transparencyType", "flat") == "flat":
                    props.update(effect.maybe_apply_transparency(
                        tracker, force=True,
                    ))
                    if tracker.transparency_ok():
                        break

        # Gradient boost (shapes only)
        if not tracker.gradient_ok():
            shape_keys = [
                k for k in eligible_keys
                if custom_elements.get(k, {}).get("type") == "shape"
            ]
            for k in shape_keys:
                props = element_layout[k]
                if props.get("fillMode") != "gradient":
                    props.update(effect.maybe_apply_gradient(
                        tracker, is_shape=True, force=True,
                    ))
                    if tracker.gradient_ok():
                        break

        # Text effects boost
        if not tracker.text_effect_ok():
            text_keys = [
                k for k in eligible_keys
                if custom_elements.get(k, {}).get("type") == "text"
            ]
            for k in text_keys:
                props = element_layout[k]
                has_effect = bool(
                    props.get("neonColor")
                    or props.get("hollowText")
                    or props.get("contourWidth", 0) > 0
                )
                if not has_effect:
                    props.update(effect.maybe_apply_text_effects(
                        tracker, force=True,
                    ))
                    if tracker.text_effect_ok():
                        break

    def generate(
        self, page_index: int, scenario_title: str, page_count: int
    ) -> dict:
        """Generate one page, then boost coverage to meet thresholds."""
        page_id = f"page-{page_index:03d}-{self._slugify(scenario_title)}"
        tracker = EffectCoverageTracker()
        element_layout: dict[str, Any] = {}
        custom_elements: dict[str, Any] = {}
        existing_rects: list[tuple] = []

        # --- Background ---
        element_layout["background"] = generate_background()

        # --- Content ---
        title_text = scenario_title.upper()
        subtitle_candidates = [
            "Discover the latest collection",
            "Limited time offer — Act now",
            "Your exclusive invitation awaits",
            "New experiences are here",
            "Be the first to know",
        ]
        subtitle_text = random.choice(subtitle_candidates)

        content = {
            "title": title_text,
            "subtitle": subtitle_text,
            "date": self._maybe_date(),
            "time": self._maybe_field(""),
            "location": self._maybe_field(""),
            "platform": random.choice(PLATFORMS),
            "teacher": self._maybe_field(""),
            "price": self._maybe_price(),
            "contact": self._maybe_field(""),
            "extra": self._maybe_extra(),
        }

        # --- Title ---
        title_layout, title_custom = generate_title_subtitle(
            "title", title_text, f"page-{page_index:03d}",
            tracker, self.composer, existing_rects,
            force=False,
        )
        element_layout["title"] = title_layout
        # title is a BASE FIELD — do NOT add to customElements

        # --- Subtitle ---
        sub_layout, sub_custom = generate_title_subtitle(
            "subtitle", subtitle_text, f"page-{page_index:03d}",
            tracker, self.composer, existing_rects,
            force=False,
        )
        element_layout["subtitle"] = sub_layout
        # subtitle is a BASE FIELD — do NOT add to customElements

        # --- Mix additional elements ---
        element_mix = self._mix_elements()
        for idx, (el_type, sub_type) in enumerate(element_mix):
            # Toggle overlap mode: ~40% of elements overlap for layered designs
            self.composer.allow_overlap = (
                idx > 0 and random.random() < 0.4
            )
            key = self._element_key(el_type, sub_type, page_index, idx)
            gen_result = self._dispatch_element(
                el_type, key, f"page-{page_index:03d}",
                tracker, existing_rects,
                force=False,
            )
            if gen_result is None:
                continue
            el_layout, el_custom = gen_result
            element_layout[key] = el_layout
            custom_elements[key] = el_custom

        # --- Boost coverage to meet spec thresholds ---
        self._boost_coverage(tracker, element_layout, custom_elements)

        return {
            "id": page_id,
            "content": content,
            "elementLayout": element_layout,
            "customElements": custom_elements,
        }

        # --- Title ---
        title_layout, title_custom = generate_title_subtitle(
            "title", title_text, f"page-{page_index:03d}",
            tracker, self.composer, existing_rects,
            force=force_effects,
        )
        element_layout["title"] = title_layout
        custom_elements["title"] = title_custom

        # --- Subtitle ---
        sub_layout, sub_custom = generate_title_subtitle(
            "subtitle", subtitle_text, f"page-{page_index:03d}",
            tracker, self.composer, existing_rects,
            force=force_effects,
        )
        element_layout["subtitle"] = sub_layout
        custom_elements["subtitle"] = sub_custom

        # --- Mix additional elements ---
        element_mix = self._mix_elements()
        for idx, (el_type, sub_type) in enumerate(element_mix):
            key = self._element_key(el_type, sub_type, page_index, idx)
            gen_result = self._dispatch_element(
                el_type, key, f"page-{page_index:03d}",
                tracker, existing_rects,
                force=force_effects,
            )
            if gen_result is None:
                continue
            el_layout, el_custom = gen_result
            element_layout[key] = el_layout
            custom_elements[key] = el_custom

        if force_effects or tracker.all_ok():
            return {
                "id": page_id,
                "content": content,
                "elementLayout": element_layout,
                "customElements": custom_elements,
            }
        return None

    def _build_minimal_page(
        self, page_id: str, scenario_title: str,
    ) -> dict:
        """Build a page that always passes coverage by forcing effects."""
        tracker = EffectCoverageTracker()
        element_layout: dict[str, Any] = {
            "background": generate_background()
        }
        custom_elements: dict[str, Any] = {}
        existing_rects: list[tuple] = []

        title_text = scenario_title.upper()
        subtitle_text = "Your exclusive invitation awaits"

        content = {
            "title": title_text,
            "subtitle": subtitle_text,
            "date": "", "time": "", "location": "",
            "platform": random.choice(PLATFORMS),
            "teacher": "", "price": "", "contact": "",
            "extra": "",
        }

        # Title with forced effects
        eff = EffectsComposer()
        pos = self.composer.assign_position(existing_rects, "text_title")
        x, y, w, _ = pos
        title_layout: dict = {
            "x": float(x), "y": float(y), "w": float(w),
            "zIndex": 80,
            "fontSize": 42.0, "color": "#ffffff",
            "fontFamily": "Poppins, sans-serif",
            "fontWeight": "bold", "textAlign": "center",
            "opacity": 100, "letterSpacing": 1.0, "lineHeight": 1.1,
            "italic": False, "uppercase": False, "borderStyle": "solid",
            "textEffectMode": "",
            "imageCropScale": 1, "imageCropOffsetX": 0,
            "imageCropOffsetY": 0, "flipX": False, "flipY": False,
            "backgroundColor": "transparent", "backgroundRoundness": 45,
            "backgroundPadding": 0.0, "backgroundOpacity": 70,
        }
        title_layout.update(eff.maybe_apply_shadow(tracker, force=True))
        title_layout.update(eff.maybe_apply_border(tracker, force=True))
        title_layout.update(eff.maybe_apply_transparency(tracker, force=True))
        title_layout.update(eff.maybe_apply_text_effects(tracker, force=True))
        title_layout["paragraphStyles"] = [
            {
                "fontSize": 42.0, "color": "#ffffff",
                "fontFamily": "Poppins, sans-serif",
                "fontWeight": "bold", "italic": False,
                "uppercase": False, "textAlign": "center",
                "letterSpacing": 1.0, "lineHeight": 1.1,
            }
        ]
        element_layout["title"] = title_layout
        # NOTE: title is a BASE FIELD — do NOT add to customElements.
        #       The editor reads it from state.content.title + state.elementLayout.title.
        tracker.count_element("text")
        existing_rects.append(pos)

        # Subtitle
        pos2 = self.composer.assign_position(existing_rects, "text_subtitle")
        x2, y2, w2, _ = pos2
        sub_layout: dict = {
            "x": float(x2), "y": float(y2), "w": float(w2),
            "zIndex": 80,
            "fontSize": 18.0, "color": "#bae6fd",
            "fontFamily": "Manrope, sans-serif",
            "fontWeight": "regular", "textAlign": "center",
            "opacity": 100, "letterSpacing": 0.5, "lineHeight": 1.25,
            "italic": False, "uppercase": False, "borderStyle": "solid",
            "textEffectMode": "",
            "imageCropScale": 1, "imageCropOffsetX": 0,
            "imageCropOffsetY": 0, "flipX": False, "flipY": False,
            "backgroundColor": "transparent", "backgroundRoundness": 45,
            "backgroundPadding": 0.0, "backgroundOpacity": 70,
        }
        sub_layout.update(eff.maybe_apply_shadow(tracker, force=True))
        sub_layout.update(eff.maybe_apply_border(tracker, force=True))
        sub_layout.update(eff.maybe_apply_transparency(tracker, force=True))
        sub_layout["paragraphStyles"] = [
            {
                "fontSize": 18.0, "color": "#bae6fd",
                "fontFamily": "Manrope, sans-serif",
                "fontWeight": "regular", "italic": False,
                "uppercase": False, "textAlign": "center",
                "letterSpacing": 0.5, "lineHeight": 1.25,
            }
        ]
        element_layout["subtitle"] = sub_layout
        # NOTE: subtitle is a BASE FIELD — do NOT add to customElements.
        tracker.count_element("text")
        existing_rects.append(pos2)

        # Force a shape with gradient
        pos3 = self.composer.assign_position(existing_rects, "shape")
        x3, y3, w3, h3 = pos3
        shape_layout: dict = {
            "x": float(x3), "y": float(y3), "w": float(w3),
            "h": float(h3), "zIndex": 20, "rotation": 0.0,
            "opacity": 80,
        }
        shape_layout.update(eff.base_shape_layout_fields())
        shape_layout["backgroundColor"] = "#312e81"
        shape_layout["borderRadius"] = 12.0
        shape_layout["borderRadiusTopLeft"] = 12.0
        shape_layout["borderRadiusTopRight"] = 12.0
        shape_layout["borderRadiusBottomRight"] = 12.0
        shape_layout["borderRadiusBottomLeft"] = 12.0
        shape_layout.update(eff.maybe_apply_shadow(tracker, force=True))
        shape_layout.update(eff.maybe_apply_border(tracker, force=True))
        shape_layout.update(eff.maybe_apply_gradient(tracker, is_shape=True, force=True))
        shape_layout.update(eff.maybe_apply_transparency(tracker, force=True))
        shape_key = f"p{page_index}-shape-0"
        element_layout[shape_key] = shape_layout
        custom_elements[shape_key] = {
            "id": shape_key, "type": "shape",
            "shapeKind": random.choice(SHAPE_KINDS), "label": f"Shape {shape_key}",
        }
        tracker.count_element("shape")
        existing_rects.append(pos3)

        return {
            "id": page_id,
            "content": content,
            "elementLayout": element_layout,
            "customElements": custom_elements,
        }

    def _mix_elements(self) -> list[tuple[str, str]]:
        """Decide which extra elements to generate for this page.

        Returns ``[(type, subtype), ...]`` where type is one of
        ``text``, ``shape``, ``image``, ``qr``.
        """
        count = random.randint(3, 12)
        types: list[str] = []
        # Always include at least one shape and one text
        types.append("shape")
        types.append("text")
        for _ in range(count - 2):
            choice = random.choices(
                ["text", "shape", "image", "qr"],
                weights=[3, 3, 2, 1],
                k=1,
            )[0]
            types.append(choice)
        random.shuffle(types)
        return [(t, self._subtype(t)) for t in types]

    @staticmethod
    def _subtype(el_type: str) -> str:
        mapping = {
            "text": "text",
            "shape": "chip",
            "image": "bg",
            "qr": "qr",
        }
        return mapping.get(el_type, el_type)

    @staticmethod
    def _element_key(
        el_type: str, sub_type: str, page_index: int, idx: int,
    ) -> str:
        if sub_type == "chip":
            return f"p{page_index}-chip-{idx}"
        elif sub_type == "text":
            return f"p{page_index}-text-{idx}"
        elif sub_type == "bg":
            return f"p{page_index}-bg-{idx}"
        elif sub_type == "qr":
            return f"p{page_index}-qr-{idx}"
        return f"p{page_index}-{sub_type}-{idx}"

    @staticmethod
    def _dispatch_element(
        el_type: str, key: str, page_prefix: str,
        tracker: EffectCoverageTracker,
        existing: list[tuple],
        force: bool = False,
    ) -> tuple[dict, dict] | None:
        if el_type == "text":
            return generate_body_text(
                key, page_prefix, tracker, LayoutComposer(), existing,
                force=force,
            )
        elif el_type == "shape":
            return generate_shape_element(
                key, page_prefix, tracker, LayoutComposer(), existing,
                force=force,
            )
        elif el_type == "image":
            return generate_image_placeholder(
                key, page_prefix, tracker, LayoutComposer(), existing,
                force=force,
            )
        elif el_type == "qr":
            return generate_qr_placeholder(
                key, page_prefix, tracker, LayoutComposer(), existing,
                force=force,
            )
        return None

    @staticmethod
    def _slugify(text: str) -> str:
        s = text.lower().strip()
        s = re.sub(r"[^a-z0-9\s-]", "", s)
        s = re.sub(r"[\s-]+", "-", s)
        return s[:30]

    @staticmethod
    def _maybe_date() -> str:
        if random.random() < 0.4:
            return ""
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        return f"2026-{month:02d}-{day:02d}"

    @staticmethod
    def _maybe_field(default: str = "") -> str:
        return default if random.random() < 0.6 else random.choice(TEXT_PHRASES)

    @staticmethod
    def _maybe_price() -> str:
        if random.random() < 0.5:
            return ""
        return f"${random.randint(5, 999)}.{random.randint(0, 99):02d}"

    @staticmethod
    def _maybe_extra() -> str:
        if random.random() < 0.5:
            return ""
        return random.choice(TEXT_PHRASES)


# ---------------------------------------------------------------------------
# Scene Generator
# ---------------------------------------------------------------------------


class SceneGenerator:
    """Orchestrates the full generation of synthetic .tc v2 files."""

    def __init__(
        self,
        seed: int | None = None,
        count: int = 10,
        output_dir: str = "generated-dataset",
        pages_range: tuple[int, int] = (2, 5),
    ) -> None:
        self.seed = seed
        if seed is not None:
            random.seed(seed % (2**32))
        self.count = count
        self.output_dir = output_dir
        self.pages_range = pages_range
        self.page_gen = PageGenerator()

    def generate(self) -> list[dict]:
        """Generate all samples and return their metadata for the index."""
        samples_meta: list[dict] = []
        for i in range(1, self.count + 1):
            sample_id = f"{i:03d}"
            meta = self._generate_sample(sample_id, i)
            samples_meta.append(meta)
        return samples_meta

    def _generate_sample(self, sample_id: str, index: int) -> dict:
        """Generate one .tc file and return its metadata."""
        scenario = random.choice(SCENARIO_TITLES)
        title = f"{scenario} - Scenario {index}"
        num_pages = random.randint(
            self.pages_range[0], self.pages_range[1]
        )

        pages: list[dict] = []
        element_types: set[str] = set()

        for p_idx in range(1, num_pages + 1):
            page = self.page_gen.generate(p_idx, scenario, num_pages)
            pages.append(page)
            # Collect element types from customElements
            for el in page.get("customElements", {}).values():
                el_type = el.get("type", "unknown")
                if el_type in ("shape", "text", "image", "qr"):
                    element_types.add(el_type)

        # Mirror first-page fields at root level for editor compatibility
        first_page = pages[0] if pages else {}
        tc: dict = {
            "tcVersion": 2,
            "format": "vertical",
            "size": "1080 \u00d7 1350 px",
            "designSurface": {"width": 1080, "height": 1350},
            "designTitle": title,
            "designTitleManual": True,
            "objective": "generic",
            "outputType": "digital",
            "content": first_page.get("content", {}),
            "elementLayout": first_page.get("elementLayout", {}),
            "customElements": first_page.get("customElements", {}),
            "userUploadedImages": [],
            "workingDocumentPageId": first_page.get("id", ""),
            "pages": pages,
        }

        output_path = os.path.join(self.output_dir, sample_id, "design.tc")
        FileWriter.write_sample(tc, output_path)

        return {
            "id": sample_id,
            "path": f"{sample_id}/design.tc",
            "title": title,
            "pages": num_pages,
            "elements": sorted(element_types),
        }


# ---------------------------------------------------------------------------
# File Writer
# ---------------------------------------------------------------------------


class FileWriter:
    """Writes .tc JSON files to disk."""

    @staticmethod
    def ensure_directory(path: str) -> None:
        os.makedirs(path, exist_ok=True)

    @staticmethod
    def write_sample(tc: dict, path: str) -> None:
        parent = os.path.dirname(os.path.abspath(path))
        FileWriter.ensure_directory(parent)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(tc, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Dataset Index Builder
# ---------------------------------------------------------------------------


class DatasetIndexBuilder:
    """Builds and writes ``index.json`` at the dataset root."""

    @staticmethod
    def write(
        index_path: str,
        samples_meta: list[dict],
        seed: int | None,
        count: int,
    ) -> None:
        index: dict = {
            "dataset": "synthetic-tc-v2",
            "generated": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
            "seed": seed % (2**32) if seed is not None else None,
            "count": count,
            "samples": samples_meta,
        }
        parent = os.path.dirname(os.path.abspath(index_path))
        FileWriter.ensure_directory(parent)
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate synthetic .tc v2 dataset for testing.",
    )
    parser.add_argument(
        "--count", "-n",
        type=int,
        default=10,
        help="Number of .tc files to generate (default: 10).",
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        default=None,
        help="PRNG seed for deterministic output.",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="generated-dataset",
        help="Output directory (default: generated-dataset/).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    gen = SceneGenerator(
        seed=args.seed,
        count=args.count,
        output_dir=args.output,
    )
    samples_meta = gen.generate()

    index_path = os.path.join(args.output, "index.json")
    DatasetIndexBuilder.write(index_path, samples_meta, args.seed, args.count)

    print(
        f"Generated {args.count} sample(s) in '{args.output}/' "
        f"({'with' if args.seed is not None else 'without'} seed "
        f"{args.seed})."
    )
    if samples_meta:
        pages_total = sum(s["pages"] for s in samples_meta)
        types_found = set()
        for s in samples_meta:
            types_found.update(s["elements"])
        print(f"  Total pages: {pages_total}")
        print(f"  Element types: {', '.join(sorted(types_found))}")


if __name__ == "__main__":
    main()
