"""
font_matcher.py — Visual font property classifier for the Smart Import V5 pipeline.

Analyses text crop images to classify visual font properties (weight,
serif group, width, posture) and maps them to the closest available
CSS font family.

CLI usage::

    python font_matcher.py --image path/to/text-crop.jpg
    python font_matcher.py --list-fonts
    python font_matcher.py --image crop.png --debug --verbose
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEBUG_DIR = Path("output") / "font-debug"

_SERIF_GROUPS = ("serif", "sans-serif", "monospace", "script")
_WEIGHTS = ("light", "regular", "bold")
_WIDTHS = ("condensed", "normal", "expanded")
_POSTURES = ("upright", "italic")

_FONT_DATABASE: list[dict[str, str]] = [
    {"family": "Arial", "serif_group": "sans-serif", "weight": "regular", "width": "normal", "posture": "upright"},
    {"family": "Helvetica", "serif_group": "sans-serif", "weight": "regular", "width": "normal", "posture": "upright"},
    {"family": "Times New Roman", "serif_group": "serif", "weight": "regular", "width": "normal", "posture": "upright"},
    {"family": "Georgia", "serif_group": "serif", "weight": "regular", "width": "normal", "posture": "upright"},
    {"family": "Courier New", "serif_group": "monospace", "weight": "regular", "width": "normal", "posture": "upright"},
    {"family": "Verdana", "serif_group": "sans-serif", "weight": "regular", "width": "normal", "posture": "upright"},
    {"family": "Trebuchet MS", "serif_group": "sans-serif", "weight": "regular", "width": "normal", "posture": "upright"},
    {"family": "Impact", "serif_group": "sans-serif", "weight": "bold", "width": "condensed", "posture": "upright"},
    {"family": "Comic Sans MS", "serif_group": "script", "weight": "regular", "width": "normal", "posture": "upright"},
    {"family": "Montserrat", "serif_group": "sans-serif", "weight": "regular", "width": "normal", "posture": "upright"},
    {"family": "Open Sans", "serif_group": "sans-serif", "weight": "regular", "width": "normal", "posture": "upright"},
    {"family": "Roboto", "serif_group": "sans-serif", "weight": "regular", "width": "normal", "posture": "upright"},
    {"family": "Lato", "serif_group": "sans-serif", "weight": "regular", "width": "normal", "posture": "upright"},
    {"family": "Playfair Display", "serif_group": "serif", "weight": "regular", "width": "normal", "posture": "upright"},
    {"family": "Merriweather", "serif_group": "serif", "weight": "regular", "width": "normal", "posture": "upright"},
    {"family": "Source Code Pro", "serif_group": "monospace", "weight": "regular", "width": "normal", "posture": "upright"},
    {"family": "Pacifico", "serif_group": "script", "weight": "regular", "width": "normal", "posture": "upright"},
    {"family": "Oswald", "serif_group": "sans-serif", "weight": "regular", "width": "condensed", "posture": "upright"},
    {"family": "Raleway", "serif_group": "sans-serif", "weight": "regular", "width": "normal", "posture": "upright"},
    {"family": "PT Sans", "serif_group": "sans-serif", "weight": "regular", "width": "normal", "posture": "upright"},
]

# Font property score weights for matching (must sum = 1.0)
_FONT_WT_SERIF = 0.40
_FONT_WT_WEIGHT = 0.25
_FONT_WT_WIDTH = 0.20
_FONT_WT_POSTURE = 0.15

# Minimum image dimension threshold (pixels)
_MIN_SIZE = 10

# ---- Weight thresholds (stroke width normalised by image height) ----------
_WEIGHT_THIN_MAX = 0.12
_WEIGHT_THICK_MIN = 0.25

# ---- Width thresholds (average aspect ratio width/height) -----------------
_WIDTH_CONDENSED_MAX = 0.45
_WIDTH_EXPANDED_MIN = 0.75

# ---- Posture thresholds ---------------------------------------------------
_POSTURE_ANGLE_THRESHOLD = 5.0   # degrees from 90° for italic
_POSTURE_HOUGH_THRESHOLD_FACTOR = 0.15  # adaptive Hough threshold factor

# ---- Serif group thresholds -----------------------------------------------
_SERIF_EXTREME_RATIO_MIN = 1.5   # (top+bot)/mid horizontal edge ratio
_MONOSPACE_GAP_CV_MAX = 0.30     # coefficient of variation for monospace
_SCRIPT_MERGE_MIN = 0.25         # minimum merge ratio for script


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class FontProperties:
    """Classified visual font properties.

    Attributes
    ----------
    weight:
        Stroke weight category — ``'light'`` | ``'regular'`` | ``'bold'``.
    serif_group:
        Serif category — ``'serif'`` | ``'sans-serif'`` | ``'monospace'`` |
        ``'script'``.
    width:
        Width category — ``'condensed'`` | ``'normal'`` | ``'expanded'``.
    posture:
        Posture category — ``'upright'`` | ``'italic'``.
    """

    weight: str
    serif_group: str
    width: str
    posture: str


@dataclass
class ClassificationResult:
    """Result of a single property classification.

    Attributes
    ----------
    value:
        The classified value (e.g. ``'bold'`` or ``'serif'``).
    confidence:
        Confidence score in ``[0.0, 1.0]``.
    """

    value: str
    confidence: float


@dataclass
class FontMatch:
    """Result of the full font matching process.

    Attributes
    ----------
    family:
        Matched font family name.
    properties:
        Classified visual font properties.
    confidences:
        Per-property confidence scores keyed by property name.
    overall_score:
        Average of all four property confidence scores.
    """

    family: str
    properties: FontProperties
    confidences: dict[str, float]
    overall_score: float


# ═══════════════════════════════════════════════════════════════════════════
# FontMatcher
# ═══════════════════════════════════════════════════════════════════════════


class FontMatcher:
    """Visual font property classifier for text crop images.

    Analyses an image of text using OpenCV and NumPy to classify its visual
    font properties (weight, serif group, width, posture), then maps those
    properties to the closest available font from a predefined database.

    Parameters
    ----------
    debug:
        If ``True``, save intermediate visualisation images to
        ``output/font-debug/``.
    """

    def __init__(self, debug: bool = False) -> None:
        self.debug = debug

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, image_path: str) -> FontMatch:
        """Analyse a text crop image and return the best font match.

        Parameters
        ----------
        image_path:
            Path to a text crop image file (JPEG, PNG, etc.).

        Returns
        -------
        FontMatch
            The matched font family, classified properties, and confidence
            scores.

        Raises
        ------
        FileNotFoundError
            If the image file does not exist.
        ValueError
            If the image cannot be decoded or is below minimum size.
        """
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        img = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Could not decode image: {image_path}")

        h, w = img.shape[:2]
        if h < _MIN_SIZE or w < _MIN_SIZE:
            raise ValueError(
                f"Image too small ({w}x{h}); minimum {_MIN_SIZE} px per side"
            )

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        binary = self._binarize(gray)

        if self.debug:
            self._save_debug("01_gray", gray)
            self._save_debug("02_binary", binary)

        weight_res = self._classify_weight(gray, binary, h)
        serif_res = self._classify_serif_group(gray, binary, h)
        width_res = self._classify_width(binary, h)
        posture_res = self._classify_posture(gray)

        props = FontProperties(
            weight=weight_res.value,
            serif_group=serif_res.value,
            width=width_res.value,
            posture=posture_res.value,
        )

        confidences: dict[str, float] = {
            "weight": weight_res.confidence,
            "serif_group": serif_res.confidence,
            "width": width_res.confidence,
            "posture": posture_res.confidence,
        }

        overall = sum(confidences.values()) / max(len(confidences), 1)
        family = self._match_font(props)

        return FontMatch(
            family=family,
            properties=props,
            confidences=confidences,
            overall_score=overall,
        )

    # ------------------------------------------------------------------
    # Weight classifier
    # ------------------------------------------------------------------

    def _classify_weight(
        self,
        gray: np.ndarray,   # noqa: ARG002
        binary: np.ndarray,
        height: int,
    ) -> ClassificationResult:
        """Classify stroke weight via distance transform.

        Computes the distance transform on the binary image to measure
        average stroke width, normalised by the image height.

        Parameters
        ----------
        gray:
            Grayscale image (kept for uniform signature with other classifiers).
        binary:
            Binary image (text=white, background=black).
        height:
            Image height in pixels used for normalisation.

        Returns
        -------
        ClassificationResult
            ``value`` is ``'light'``, ``'regular'``, or ``'bold'``.
        """
        # Distance transform: distance from each foreground (text) pixel
        # to the nearest background pixel
        dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)

        fg_mask = binary > 0
        fg_count = np.count_nonzero(fg_mask)
        if fg_count == 0:
            return ClassificationResult("regular", 0.0)

        fg_distances = dist[fg_mask]
        stroke_radius = float(np.mean(fg_distances))
        # Approximate full stroke width = 2 * mean radius
        # Normalise by font height (≈ image height for text crops)
        norm_sw = (stroke_radius * 2.0) / max(height, 1)

        logger.debug(
            "Weight: mean_stroke_radius=%.2f, normalised_stroke_width=%.3f",
            stroke_radius,
            norm_sw,
        )

        if self.debug:
            debug_dist = cv2.normalize(dist, None, 0, 255, cv2.NORM_MINMAX)
            self._save_debug("03_distance_transform", debug_dist.astype(np.uint8))

        if norm_sw <= _WEIGHT_THIN_MAX:
            conf = self._confidence_linear(
                norm_sw, 0.0, _WEIGHT_THIN_MAX, high_is_confident=False,
            )
            return ClassificationResult("light", conf)

        if norm_sw >= _WEIGHT_THICK_MIN:
            conf = self._confidence_linear(
                norm_sw, _WEIGHT_THICK_MIN, _WEIGHT_THICK_MIN + 0.20,
                high_is_confident=True,
            )
            return ClassificationResult("bold", conf)

        # Middle range → regular, triangular confidence peaking at midpoint
        conf = self._confidence_triangular(
            norm_sw, _WEIGHT_THIN_MAX, _WEIGHT_THICK_MIN,
        )
        return ClassificationResult("regular", conf)

    # ------------------------------------------------------------------
    # Serif group classifier
    # ------------------------------------------------------------------

    def _classify_serif_group(
        self,
        gray: np.ndarray,
        binary: np.ndarray,
        height: int,
    ) -> ClassificationResult:
        """Classify serif group via edge projection and contour analysis.

        Detects serifs (horizontal protrusions at character extremes),
        monospace (uniform character spacing) and script (connected cursive
        via contour analysis).  Defaults to sans-serif when none is convincing.

        Parameters
        ----------
        gray:
            Grayscale image for edge detection.
        binary:
            Binary image (text=white, background=black).
        height:
            Image height in pixels.

        Returns
        -------
        ClassificationResult
            ``value`` is ``'serif'``, ``'sans-serif'``, ``'monospace'``,
            or ``'script'``.
        """
        edges = cv2.Canny(gray, 50, 150)

        if self.debug:
            self._save_debug("04_canny_edges", edges)

        # --- Serif detection: horizontal edge projection ---
        serif_score = self._detect_serif(edges, height)

        # --- Monospace detection: character gap uniformity ---
        contours = self._find_text_contours(binary)
        mono_score = self._detect_monospace(contours)

        # --- Script detection: connected-cursive via dilation ---
        script_score = self._detect_script(binary)

        scores: dict[str, float] = {
            "serif": serif_score,
            "monospace": mono_score,
            "script": script_score,
        }

        best = max(scores, key=lambda k: scores[k])  # type: ignore[arg-type]
        best_score = scores[best]

        logger.debug(
            "Serif group scores — serif=%.3f monospace=%.3f script=%.3f  → %s",
            serif_score, mono_score, script_score, best,
        )

        # When nothing stands out, default to sans-serif
        if best_score < 0.20:
            return ClassificationResult("sans-serif", max(best_score, 0.1))

        # Confidence: boost based on margin over the runner-up
        sorted_scores = sorted(scores.values(), reverse=True)
        margin = sorted_scores[0] - (sorted_scores[1] if len(sorted_scores) > 1 else 0.0)
        confidence = min(best_score + margin * 0.5, 0.95)

        return ClassificationResult(best, max(confidence, 0.1))

    def _detect_serif(self, edges: np.ndarray, height: int) -> float:
        """Return a serif score in ``[0.0, 1.0]``.

        Computes horizontal edge density at the top and bottom thirds of
        the image versus the middle third.  Serifs produce extra horizontal
        edges at character extremes, raising the extreme-to-middle ratio.
        """
        h = edges.shape[0]
        if h < _MIN_SIZE:
            return 0.0

        # Sobel y-gradient highlights horizontal edges
        sobel_y = cv2.Sobel(edges, cv2.CV_64F, 0, 1, ksize=3)
        horiz_strength = np.abs(sobel_y)
        _thresh = 50
        horiz_mask = horiz_strength > _thresh

        band_top = horiz_mask[: max(1, h // 3), :]
        band_mid = horiz_mask[h // 3 : 2 * h // 3, :]
        band_bot = horiz_mask[2 * h // 3 :, :]

        def _density(region: np.ndarray) -> float:
            return float(np.mean(region)) if region.size > 0 else 0.0

        d_top = _density(band_top)
        d_mid = _density(band_mid)
        d_bot = _density(band_bot)

        extreme_density = (d_top + d_bot) * 0.5
        if d_mid < 1e-8:
            return 0.0

        ratio = extreme_density / d_mid

        # Map ratio to 0..1 with the threshold at _SERIF_EXTREME_RATIO_MIN
        if ratio <= 1.0:
            return 0.0
        return float(np.clip((ratio - 1.0) / (_SERIF_EXTREME_RATIO_MIN * 2.0), 0.0, 1.0))

    def _detect_monospace(self, contours: list) -> float:
        """Return a monospace score in ``[0.0, 1.0]``.

        Analyses the uniformity of gaps between consecutive character
        bounding boxes.  A low coefficient of variation indicates
        fixed-width (monospace) spacing.
        """
        if len(contours) < 3:
            return 0.0

        boxes = [cv2.boundingRect(c) for c in contours]
        # Sort left-to-right by x coordinate
        boxes.sort(key=lambda b: b[0])

        gaps: list[int] = []
        for i in range(1, len(boxes)):
            prev_right = boxes[i - 1][0] + boxes[i - 1][2]
            curr_left = boxes[i][0]
            gap = max(0, curr_left - prev_right)
            gaps.append(gap)

        if len(gaps) < 2:
            return 0.0

        mean_gap = float(np.mean(gaps))
        if mean_gap < 1.0:
            return 0.0

        std_gap = float(np.std(gaps))
        cv_gap = std_gap / mean_gap

        if cv_gap <= _MONOSPACE_GAP_CV_MAX:
            # Strong monospace signal
            return float(np.clip(1.0 - (cv_gap / _MONOSPACE_GAP_CV_MAX) * 0.3, 0.5, 1.0))
        elif cv_gap <= _MONOSPACE_GAP_CV_MAX * 2:
            # Weak signal — partial confidence
            t = (cv_gap - _MONOSPACE_GAP_CV_MAX) / _MONOSPACE_GAP_CV_MAX
            return float(np.clip(0.5 - t * 1.5, 0.0, 0.5))

        return 0.0

    def _detect_script(self, binary: np.ndarray) -> float:
        """Return a script score in ``[0.0, 1.0]``.

        Dilates the binary image to merge nearby strokes, then compares
        the contour count before and after.  Cursive/script text connects
        characters after dilation, so the contour ratio drops significantly.
        """
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        dilated = cv2.dilate(binary, kernel, iterations=2)

        contours_orig, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE,
        )
        contours_dilated, _ = cv2.findContours(
            dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE,
        )

        n_orig = max(len(contours_orig), 1)
        n_dilated = max(len(contours_dilated), 1)

        # Merge ratio: close to 1.0 = no merging (not script),
        # close to 0.0 = lots of merging (likely script)
        merge_ratio = n_dilated / n_orig
        script_score = float(np.clip((1.0 - merge_ratio) * 1.5, 0.0, 1.0))

        if self.debug:
            self._save_debug("05_dilated_script", dilated)

        return script_score

    # ------------------------------------------------------------------
    # Width classifier
    # ------------------------------------------------------------------

    def _classify_width(
        self,
        binary: np.ndarray,
        height: int,
    ) -> ClassificationResult:
        """Classify character width via average bounding-box aspect ratio.

        Parameters
        ----------
        binary:
            Binary image (text=white, background=black).
        height:
            Image height in pixels.

        Returns
        -------
        ClassificationResult
            ``value`` is ``'condensed'``, ``'normal'``, or ``'expanded'``.
        """
        contours = self._find_text_contours(binary)
        if not contours:
            return ClassificationResult("normal", 0.0)

        aspect_ratios: list[float] = []
        for c in contours:
            _x, _y, cw, ch = cv2.boundingRect(c)
            if ch > 3:  # ignore vertical noise
                aspect_ratios.append(cw / ch)

        if not aspect_ratios:
            return ClassificationResult("normal", 0.0)

        avg_ar = float(np.mean(aspect_ratios))

        logger.debug("Width: average aspect_ratio=%.3f (n=%d)", avg_ar, len(aspect_ratios))

        if avg_ar <= _WIDTH_CONDENSED_MAX:
            conf = self._confidence_linear(
                avg_ar, 0.0, _WIDTH_CONDENSED_MAX, high_is_confident=False,
            )
            return ClassificationResult("condensed", conf)

        if avg_ar >= _WIDTH_EXPANDED_MIN:
            conf = self._confidence_linear(
                avg_ar, _WIDTH_EXPANDED_MIN, _WIDTH_EXPANDED_MIN + 0.40,
                high_is_confident=True,
            )
            return ClassificationResult("expanded", conf)

        conf = self._confidence_triangular(
            avg_ar, _WIDTH_CONDENSED_MAX, _WIDTH_EXPANDED_MIN,
        )
        return ClassificationResult("normal", conf)

    # ------------------------------------------------------------------
    # Posture classifier
    # ------------------------------------------------------------------

    def _classify_posture(self, gray: np.ndarray) -> ClassificationResult:
        """Classify posture (upright vs italic) via Hough line analysis.

        Finds near-vertical lines in the image using the probabilistic
        Hough transform and computes their mean angle.  A systematic
        deviation from 90° indicates italic slant.

        Falls back to Sobel gradient histogram analysis when Hough
        produces too few lines.

        Parameters
        ----------
        gray:
            Grayscale image.

        Returns
        -------
        ClassificationResult
            ``value`` is ``'upright'`` or ``'italic'``.
        """
        edges = cv2.Canny(gray, 50, 150)
        h_img, w_img = gray.shape
        adaptive_threshold = max(
            20, int(min(h_img, w_img) * _POSTURE_HOUGH_THRESHOLD_FACTOR),
        )

        lines = cv2.HoughLines(
            edges, 1, np.pi / 180, threshold=adaptive_threshold,
        )

        if lines is not None and len(lines) >= 5:
            return self._posture_via_hough(lines)

        return self._posture_via_sobel(gray)

    def _posture_via_hough(self, lines: np.ndarray) -> ClassificationResult:
        """Classify posture using Hough line angles."""
        vertical_angles: list[float] = []
        for line in lines:
            _rho, theta = line[0]
            deg = float(np.degrees(theta))
            # Hough theta: 0° = horizontal, 90° = vertical
            if 70.0 <= deg <= 110.0:
                vertical_angles.append(deg)

        if len(vertical_angles) < 3:
            return ClassificationResult("upright", 0.3)

        mean_angle = float(np.mean(vertical_angles))
        deviation = abs(mean_angle - 90.0)

        logger.debug(
            "Posture (Hough): mean_angle=%.2f°, deviation=%.2f° (n=%d)",
            mean_angle, deviation, len(vertical_angles),
        )

        if deviation > _POSTURE_ANGLE_THRESHOLD:
            conf = self._confidence_linear(
                deviation, _POSTURE_ANGLE_THRESHOLD, _POSTURE_ANGLE_THRESHOLD + 12.0,
                high_is_confident=True,
            )
            return ClassificationResult("italic", min(conf, 0.9))

        conf = self._confidence_linear(
            deviation, 0.0, _POSTURE_ANGLE_THRESHOLD, high_is_confident=False,
        )
        return ClassificationResult("upright", max(conf, 0.1))

    def _posture_via_sobel(self, gray: np.ndarray) -> ClassificationResult:
        """Fallback: classify posture via Sobel gradient circular mean."""
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

        magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
        angle = np.degrees(np.arctan2(sobel_y, sobel_x))  # -180 .. 180

        # Focus on strong edges (top 20 % magnitude)
        threshold = float(np.percentile(magnitude, 80))
        strong_mask = magnitude > threshold
        strong_angles = angle[strong_mask]

        if len(strong_angles) < 10:
            return ClassificationResult("upright", 0.2)

        # Normalise to [0, 180) because gradient at 0° and 180° both
        # represent near-vertical edges (intensity changes horizontally)
        norm = np.where(strong_angles < 0, strong_angles + 180, strong_angles)

        # Circular mean of the distribution
        angles_rad = np.radians(norm)
        sin_sum = float(np.sum(np.sin(angles_rad)))
        cos_sum = float(np.sum(np.cos(angles_rad)))

        if abs(sin_sum) < 1e-6 and abs(cos_sum) < 1e-6:
            return ClassificationResult("upright", 0.2)

        mean_rad = np.arctan2(sin_sum, cos_sum)
        mean_deg = float(np.degrees(mean_rad))
        if mean_deg < 0:
            mean_deg += 180

        # For near-vertical edges, gradient direction is near 0° or 180°.
        # Distance from this symmetry axis tells us about italic slant.
        deviation = min(abs(mean_deg), abs(mean_deg - 180))

        logger.debug(
            "Posture (Sobel): circular_mean=%.2f°, deviation=%.2f°",
            mean_deg, deviation,
        )

        if deviation > _POSTURE_ANGLE_THRESHOLD:
            conf = self._confidence_linear(
                deviation, _POSTURE_ANGLE_THRESHOLD, _POSTURE_ANGLE_THRESHOLD + 15.0,
                high_is_confident=True,
            )
            return ClassificationResult("italic", min(conf, 0.7))

        return ClassificationResult("upright", 0.4)

    # ------------------------------------------------------------------
    # Font matching
    # ------------------------------------------------------------------

    def _match_font(self, props: FontProperties) -> str:
        """Map classified properties to the closest font from the database.

        Scoring assigns weights per matching property.  When no good match
        exists (score < 0.6), the fallback chain is:

        1. Same ``serif_group`` → first font with that serif group
        2. Same ``weight`` → first font with that weight
        3. Generic ``'sans-serif'``

        Parameters
        ----------
        props:
            Classified font properties.

        Returns
        -------
        str
            The matched font family name.
        """
        scored: list[tuple[float, str]] = []
        for font in _FONT_DATABASE:
            score = 0.0
            if font["serif_group"] == props.serif_group:
                score += _FONT_WT_SERIF
            if font["weight"] == props.weight:
                score += _FONT_WT_WEIGHT
            if font["width"] == props.width:
                score += _FONT_WT_WIDTH
            if font["posture"] == props.posture:
                score += _FONT_WT_POSTURE
            scored.append((score, font["family"]))

        if not scored:
            return "sans-serif"

        scored.sort(key=lambda x: (-x[0], x[1]))
        best_score, best_family = scored[0]

        logger.debug("Font match: best=%s score=%.2f", best_family, best_score)

        if best_score >= 0.6:
            return best_family

        # --- Fallback chain ---
        # 1. Same serif group
        for score, family in scored:
            if score >= _FONT_WT_SERIF - 0.001:
                logger.debug("Font fallback (serif_group): %s", family)
                return family

        # 2. Same weight
        for font in _FONT_DATABASE:
            if font["weight"] == props.weight:
                logger.debug("Font fallback (weight): %s", font["family"])
                return font["family"]

        # 3. Generic fallback
        logger.debug("Font fallback (generic): sans-serif")
        return "sans-serif"

    # ------------------------------------------------------------------
    # Helpers (static)
    # ------------------------------------------------------------------

    @staticmethod
    def _binarize(gray: np.ndarray) -> np.ndarray:
        """Convert grayscale to binary via Otsu thresholding.

        Returns a binary image where text pixels are white (255) and
        background pixels are black (0), which is the convention expected
        by ``cv2.distanceTransform``.
        """
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        return binary

    @staticmethod
    def _find_text_contours(binary: np.ndarray) -> list:
        """Find external contours of text regions in a binary image.

        Small contours (area < 0.1 % of total image) are discarded as
        noise.
        """
        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE,
        )
        h, w = binary.shape
        min_area = max(4, int(h * w * 0.001))
        return [c for c in contours if cv2.contourArea(c) >= min_area]

    @staticmethod
    def _confidence_linear(
        value: float,
        low: float,
        high: float,
        high_is_confident: bool,
    ) -> float:
        """Compute a linear confidence score in ``[0.0, 1.0]``.

        Parameters
        ----------
        value:
            The measured value.
        low:
            Lower bound of the transition band.
        high:
            Upper bound of the transition band.
        high_is_confident:
            If ``True``, values ≥ ``high`` get confidence 1.0.
            If ``False``, values ≤ ``low`` get confidence 1.0.

        Returns
        -------
        float
            Confidence in ``[0.0, 1.0]``.
        """
        if high <= low:
            return 1.0
        if high_is_confident:
            if value >= high:
                return 1.0
            if value <= low:
                return 0.0
            return (value - low) / (high - low)

        # low_is_confident
        if value <= low:
            return 1.0
        if value >= high:
            return 0.0
        return 1.0 - (value - low) / (high - low)

    @staticmethod
    def _confidence_triangular(value: float, low: float, high: float) -> float:
        """Triangular confidence peaking at the midpoint of ``[low, high]``."""
        if high <= low:
            return 1.0
        mid = (low + high) * 0.5
        if value <= low or value >= high:
            return 0.0
        if value <= mid:
            return (value - low) / (mid - low)
        return (high - value) / (high - mid)

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def _save_debug(self, name: str, img: np.ndarray) -> None:
        """Save an intermediate visualisation image for debugging."""
        if not self.debug:
            return
        debug_path = _DEBUG_DIR
        debug_path.mkdir(parents=True, exist_ok=True)
        out = str(debug_path / f"{name}.png")
        cv2.imwrite(out, img)
        logger.debug("Debug image saved: %s", out)


# ═══════════════════════════════════════════════════════════════════════════
# CLI helpers
# ═══════════════════════════════════════════════════════════════════════════


def list_fonts() -> None:
    """Print the font database as a formatted table to stdout."""
    header = (
        f"{'Font Family':<25} {'Serif Group':<15} {'Weight':<10} "
        f"{'Width':<12} {'Posture':<10}"
    )
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)
    for font in _FONT_DATABASE:
        print(
            f"{font['family']:<25} {font['serif_group']:<15} "
            f"{font['weight']:<10} {font['width']:<12} {font['posture']:<10}",
        )
    print(sep)
    print(f"Total: {len(_FONT_DATABASE)} fonts in database.")


def setup_logging(verbose: bool = False) -> None:
    """Configure the root logger with a standard format."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Parameters
    ----------
    argv:
        Argument list.  Defaults to ``sys.argv[1:]``.

    Returns
    -------
    argparse.Namespace
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Visual font property classifier for the Smart Import V5 pipeline.\n"
            "Analyses a text crop image with OpenCV to classify weight, serif "
            "group, width, and posture, then maps to the closest CSS font."
        ),
    )
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="Path to a text crop image to analyse.",
    )
    parser.add_argument(
        "--list-fonts",
        action="store_true",
        help="Print the available font database and exit.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Save intermediate visualisation images to output/font-debug/.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug-level logging.",
    )
    return parser.parse_args(argv)


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════


def main() -> None:
    """CLI entry point for font_matcher.py.

    Analyse a text crop image and print the matched font family plus
    per-property classifications with confidence scores.
    """
    args = parse_args()
    setup_logging(args.verbose)

    if args.list_fonts:
        list_fonts()
        return

    if not args.image:
        logger.error("No image provided. Use --image <path> or --list-fonts.")
        sys.exit(1)

    if not os.path.isfile(args.image):
        logger.error("File not found: %s", args.image)
        sys.exit(1)

    matcher = FontMatcher(debug=args.debug)

    try:
        result = matcher.classify(args.image)
    except (FileNotFoundError, ValueError) as exc:
        logger.error(str(exc))
        sys.exit(1)

    print()
    print(f"  Image:         {args.image}")
    print(f"  Matched font:  {result.family}")
    print(f"  Overall score: {result.overall_score:.2f}")
    print(f"  Properties:")
    print(f"    Weight:       {result.properties.weight:<10} "
          f"(conf: {result.confidences['weight']:.2f})")
    print(f"    Serif group:  {result.properties.serif_group:<10} "
          f"(conf: {result.confidences['serif_group']:.2f})")
    print(f"    Width:        {result.properties.width:<10} "
          f"(conf: {result.confidences['width']:.2f})")
    print(f"    Posture:      {result.properties.posture:<10} "
          f"(conf: {result.confidences['posture']:.2f})")
    print()


if __name__ == "__main__":
    main()
