"""
text_analyzer.py — OpenCV-based text property analysis for Smart Import V7.

Extracts REAL text properties from image regions instead of relying
solely on LLM detection:
  - Color (hex)
  - Font weight (bold vs regular vs light)
  - Italic detection (cursiva)
  - Underline detection
  - Font size (px estimation)
  - Shadow detection
  - Border/outline detection
  - Blur detection

Usage
-----
    from text_analyzer import TextAnalyzer

    analyzer = TextAnalyzer()
    color = analyzer.extract_text_color(image, bbox)
    effects = analyzer.detect_effects(image, bbox)
    props = analyzer.analyze_text_region(image, bbox)
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class TextAnalyzer:
    """Analyze text regions in an image using OpenCV to extract properties."""

    def analyze_text_region(
        self, image: np.ndarray, bbox: dict | tuple
    ) -> dict[str, Any]:
        """Run ALL analyses on a single text region.

        Parameters
        ----------
        image:
            Full source image (BGR numpy array).
        bbox:
            Dict with keys ``x``, ``y``, ``width``, ``height``
            OR tuple ``(x, y, w, h)``.

        Returns
        -------
        dict with keys: colorHex, fontWeight, isItalic, isUnderlined,
        fontSizePx, effects, confidence.
        """
        x, y, w, h = self._parse_bbox(bbox)
        if w < 3 or h < 3:
            return {"error": "bbox too small", "colorHex": None}

        crop = self._safe_crop(image, x, y, w, h)
        if crop is None or crop.size == 0:
            return {"error": "empty crop", "colorHex": None}

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

        # Threshold to separate text from background
        _, binary = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        # Find actual text sub-region (trim empty space from bbox)
        text_sub = self._locate_text_in_bbox(gray, binary)
        if text_sub is not None:
            sx, sy, sw, sh = text_sub
            if sw > 5 and sh > 5:
                # Re-crop to text region for more accurate color
                text_crop = crop[sy:sy+sh, sx:sx+sw].copy()
                text_gray = gray[sy:sy+sh, sx:sx+sw].copy()
                text_binary = binary[sy:sy+sh, sx:sx+sw].copy()
            else:
                text_crop, text_gray, text_binary = crop, gray, binary
        else:
            text_crop, text_gray, text_binary = crop, gray, binary

        color_hex = self._extract_color_from_crop(text_crop, text_binary)
        font_weight = self._detect_font_weight(text_binary)
        is_italic = self._detect_italic(text_binary)
        is_underlined = self._detect_underline(text_binary)
        font_size = self._estimate_font_size(sh if text_sub else h, text_binary)
        effects = self._detect_effects_from_crop(crop, gray, binary, x, y, w, h)

        return {
            "colorHex": color_hex,
            "fontWeight": font_weight,
            "isItalic": is_italic,
            "isUnderlined": is_underlined,
            "fontSizePx": font_size,
            "effects": effects,
            "confidence": self._compute_confidence(text_binary),
        }

    # ── Color extraction ──────────────────────────────────────────

    def extract_text_color(
        self, image: np.ndarray, bbox: dict | tuple
    ) -> Optional[str]:
        """Extract the dominant text color as a hex string.

        Uses Otsu threshold to isolate text pixels, then takes the
        median color of those pixels in the original BGR image.
        """
        x, y, w, h = self._parse_bbox(bbox)
        crop = self._safe_crop(image, x, y, w, h)
        if crop is None:
            return None
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return self._extract_color_from_crop(crop, binary)

    def _extract_color_from_crop(
        self, crop: np.ndarray, binary: np.ndarray
    ) -> Optional[str]:
        """Extract text color from a cropped region with binary mask.

        Improved: uses edge-guided sampling + connected components
        to avoid background bleed.
        """
        h, w = crop.shape[:2]
        if h < 5 or w < 5:
            return None

        # Which side is foreground (text)?
        fg = np.sum(binary == 255)
        bg = np.sum(binary == 0)
        text_mask = binary == 255 if fg <= bg else binary == 0

        # Approach 1: median of text pixels
        text_pixels = crop[text_mask]
        if len(text_pixels) >= 10:
            median_bgr = np.median(text_pixels, axis=0).astype(int)
        else:
            median_bgr = None

        # Approach 2: edge-guided sampling along Canny edges
        edges = cv2.Canny(crop, 50, 150)
        # Dilate edges slightly to capture stroke width
        kernel = np.ones((2, 2), np.uint8)
        edge_strokes = cv2.dilate(edges, kernel, iterations=1)
        edge_pixels = crop[edge_strokes > 0]
        if len(edge_pixels) >= 10:
            edge_median = np.median(edge_pixels, axis=0).astype(int)
        else:
            edge_median = None

        # Approach 3: connected components on text mask (largest CC = text body)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            text_mask.astype(np.uint8), connectivity=8
        )
        # Skip background (label 0), find largest component
        cc_sizes = [(i, stats[i, cv2.CC_STAT_AREA]) for i in range(1, num_labels)]
        if cc_sizes:
            largest_label = max(cc_sizes, key=lambda x: x[1])[0]
            cc_pixels = crop[labels == largest_label]
            cc_median = np.median(cc_pixels, axis=0).astype(int) if len(cc_pixels) >= 10 else None
        else:
            cc_median = None

        # Vote: pick the most common median across approaches
        candidates = [m for m in [median_bgr, edge_median, cc_median] if m is not None]
        if not candidates:
            return None

        # Cluster by rounding to nearest 16, pick most common
        rounded = [tuple((c // 16) * 16) for c in candidates]
        winner = Counter(rounded).most_common(1)[0][0]
        # Return the original (unrounded) winner
        for c in candidates:
            if tuple((c // 16) * 16) == winner:
                return f"#{c[2]:02X}{c[1]:02X}{c[0]:02X}"

        # Fallback: first candidate
        c = candidates[0]
        return f"#{c[2]:02X}{c[1]:02X}{c[0]:02X}"

    # ── Font weight detection ─────────────────────────────────────

    def _detect_font_weight(self, binary: np.ndarray) -> str:
        """Detect font weight from binary text image.

        Uses stroke width ratio: bold text has thicker strokes.
        Returns ``"bold"``, ``"regular"``, or ``"light"``.
        """
        h, w = binary.shape
        if h < 5 or w < 5:
            return "regular"

        # Distance transform gives stroke width
        dist = cv2.distanceTransform(
            255 - binary, cv2.DIST_L2, 3
        )
        nonzero = dist[dist > 0]
        if len(nonzero) < 5:
            return "regular"

        mean_stroke = float(np.mean(nonzero))
        # Normalize by character height
        ratio = mean_stroke / max(h, 1)

        if ratio > 0.18:
            return "bold"
        elif ratio < 0.08:
            return "light"
        return "regular"

    # ── Italic detection ──────────────────────────────────────────

    def _detect_italic(self, binary: np.ndarray) -> bool:
        """Detect if text is italic by analyzing dominant edge angles."""
        h, w = binary.shape
        if h < 10 or w < 10:
            return False

        # Detect edges
        edges = cv2.Canny(binary, 50, 150)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=20,
            minLineLength=max(5, w // 4),
            maxLineGap=4
        )
        if lines is None:
            return False

        # Count angles: italic text has dominant ~10-20° angles
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 - x1 == 0:
                continue
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
            angles.append(angle)

        if not angles:
            return False

        # For italic: many edges between 5-25 degrees
        italic_edges = sum(1 for a in angles if 5 < a < 25)
        return italic_edges / max(len(angles), 1) > 0.3

    # ── Underline detection ───────────────────────────────────────

    def _detect_underline(self, binary: np.ndarray) -> bool:
        """Detect if text has underline via horizontal line at bottom."""
        h, w = binary.shape
        if h < 10 or w < 10:
            return False

        # Check bottom 20% of region for a strong horizontal line
        bottom = binary[int(h * 0.8):, :]
        if bottom.size == 0:
            return False

        # Horizontal projection — look for a row with mostly white
        row_sums = np.sum(bottom == 255, axis=1) / max(w, 1)
        return bool(np.any(row_sums > 0.6))

    # ── Font size estimation ──────────────────────────────────────

    def _estimate_font_size(self, bbox_h: int, binary: np.ndarray) -> int:
        """Estimate font size in pixels from bbox height and content."""
        if bbox_h < 5:
            return 12

        # Find the actual text extent within the bbox
        rows = np.any(binary == 255, axis=1)
        if not np.any(rows):
            return bbox_h

        text_rows = np.where(rows)[0]
        text_height = text_rows[-1] - text_rows[0]
        # Font size is roughly 70-80% of the text extent
        return max(8, int(text_height * 0.75))

    # ── Effects detection ─────────────────────────────────────────

    def detect_effects(
        self, image: np.ndarray, bbox: dict | tuple
    ) -> list[dict]:
        """Detect text effects (shadow, border, outline, blur).

        Returns a list of dicts::
            [{"type": "shadow", "offset_x": 2, "offset_y": 2, "confidence": 0.8}, ...]
        """
        x, y, w, h = self._parse_bbox(bbox)
        crop = self._safe_crop(image, x, y, w, h)
        if crop is None:
            return []
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return self._detect_effects_from_crop(crop, gray, binary, x, y, w, h)

    def _detect_effects_from_crop(
        self, crop: np.ndarray, gray: np.ndarray,
        binary: np.ndarray, x: int, y: int, w: int, h: int,
    ) -> list[dict]:
        """Detect text effects from a cropped and thresholded region."""
        effects = []

        # ── Shadow detection ──────────────────────────────────────
        shadow = self._detect_shadow(gray, binary)
        if shadow:
            effects.append(shadow)

        # ── Border / outline detection ────────────────────────────
        border = self._detect_border(gray, binary)
        if border:
            effects.append(border)

        # ── Blur detection ────────────────────────────────────────
        blur = self._detect_blur(gray)
        if blur:
            effects.append(blur)

        return effects

    def _detect_shadow(
        self, gray: np.ndarray, binary: np.ndarray
    ) -> Optional[dict]:
        """Detect drop shadow: darker pixels offset from text edges."""
        h, w = gray.shape
        if h < 10 or w < 10:
            return None

        # Dilate the text to get a "shadow region" around it
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(binary, kernel, iterations=2)

        # Shadow = dilated but NOT binary (the region around text)
        shadow_region = dilated & ~binary

        if np.sum(shadow_region) < 10:
            return None

        # Check if the shadow region has darker pixels
        shadow_pixels = gray[shadow_region > 0]
        text_pixels = gray[binary > 0]

        if len(shadow_pixels) < 5 or len(text_pixels) < 5:
            return None

        shadow_mean = float(np.mean(shadow_pixels))
        text_mean = float(np.mean(text_pixels))

        # Shadow should be darker than text area
        if shadow_mean < text_mean * 0.85:
            # Estimate offset
            return {
                "type": "shadow",
                "offset_x": 2,
                "offset_y": 2,
                "confidence": round(min(1.0, (text_mean - shadow_mean) / 128), 2),
            }

        return None

    def _detect_border(
        self, gray: np.ndarray, binary: np.ndarray
    ) -> Optional[dict]:
        """Detect outline/border: contrasting pixels at text edges."""
        h, w = gray.shape
        if h < 10 or w < 10:
            return None

        # Erode text — difference between original and eroded = border
        kernel = np.ones((2, 2), np.uint8)
        eroded = cv2.erode(binary, kernel, iterations=1)
        border_region = binary & ~eroded

        if np.sum(border_region) < 5:
            return None

        # Check contrast at border
        border_pixels = gray[border_region > 0]
        if len(border_pixels) < 5:
            return None

        # If border has high contrast vs text, it's an outline
        text_pixels = gray[binary > 0]
        if len(text_pixels) < 5:
            return None

        border_mean = float(np.mean(border_pixels))
        text_mean = float(np.mean(text_pixels))

        contrast = abs(text_mean - border_mean) / max(text_mean, 1)
        if contrast > 0.3:
            return {
                "type": "outline",
                "color": "#FFFFFF" if border_mean > text_mean else "#000000",
                "width_px": 1,
                "confidence": round(min(1.0, contrast), 2),
            }

        return None

    def _detect_blur(self, gray: np.ndarray) -> Optional[dict]:
        """Detect blur via Laplacian variance (focus measure)."""
        h, w = gray.shape
        if h < 10 or w < 10:
            return None

        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Low variance = blurry
        if laplacian_var < 50:
            return {
                "type": "blur",
                "severity": "high" if laplacian_var < 20 else "medium",
                "confidence": round(max(0, 1.0 - laplacian_var / 100), 2),
            }

        return None

    # ── Text sub-region localization ──────────────────────────────

    def _locate_text_in_bbox(
        self, gray: np.ndarray, binary: np.ndarray
    ) -> Optional[tuple[int, int, int, int]]:
        """Find the actual text sub-region within a bbox.

        Uses horizontal + vertical projection to trim empty space
        around the text.
        """
        h, w = binary.shape
        text_mask = binary == 255

        # Horizontal projection (sum per row)
        row_sums = np.sum(text_mask, axis=1)
        rows_above_zero = np.where(row_sums > max(w * 0.02, 2))[0]
        if len(rows_above_zero) == 0:
            return None
        y1, y2 = int(rows_above_zero[0]), int(rows_above_zero[-1]) + 1

        # Vertical projection (sum per column)
        col_sums = np.sum(text_mask, axis=0)
        cols_above_zero = np.where(col_sums > max(h * 0.02, 2))[0]
        if len(cols_above_zero) == 0:
            return None
        x1, x2 = int(cols_above_zero[0]), int(cols_above_zero[-1]) + 1

        # Pad slightly (10%) for safety
        pad_x = int((x2 - x1) * 0.1)
        pad_y = int((y2 - y1) * 0.1)
        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(w, x2 + pad_x)
        y2 = min(h, y2 + pad_y)

        if x2 <= x1 or y2 <= y1:
            return None
        return (x1, y1, x2 - x1, y2 - y1)

    # ── Helpers ───────────────────────────────────────────────────

    def _compute_confidence(self, binary: np.ndarray) -> float:
        """Confidence based on how clean the text segmentation is."""
        h, w = binary.shape
        if h < 5 or w < 5:
            return 0.0
        fg = np.sum(binary == 255)
        bg = np.sum(binary == 0)
        total = fg + bg
        if total == 0:
            return 0.0
        # Higher confidence when text pixels are a smaller fraction (clean text)
        ratio = min(fg, bg) / max(max(fg, bg), 1)
        return max(0.0, 1.0 - ratio * 2)

    def _safe_crop(
        self, image: np.ndarray, x: int, y: int, w: int, h: int
    ) -> Optional[np.ndarray]:
        """Crop with bounds checking."""
        img_h, img_w = image.shape[:2]
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(img_w, x + w)
        y2 = min(img_h, y + h)
        if x2 <= x1 or y2 <= y1:
            return None
        return image[y1:y2, x1:x2].copy()

    @staticmethod
    def _parse_bbox(bbox: dict | tuple) -> tuple[int, int, int, int]:
        """Normalize bbox to ``(x, y, w, h)``."""
        if isinstance(bbox, dict):
            return (
                int(bbox.get("x", 0)),
                int(bbox.get("y", 0)),
                int(max(bbox.get("width", 0), bbox.get("w", 0))),
                int(max(bbox.get("height", 0), bbox.get("h", 0))),
            )
        return tuple(int(v) for v in bbox[:4])
