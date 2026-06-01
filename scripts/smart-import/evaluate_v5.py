"""
evaluate_v5.py — Auto-Evaluator V5 for Smart Import Pipeline.

Compares original design images against rendered output across 7 scoring
dimensions: layout, textAccuracy, colorAccuracy, visualSimilarity,
editability, structureF1, and posterQuality (legibilidad, contraste, CTA).

Usage
-----
    python evaluate_v5.py --all
    python evaluate_v5.py --image poster-simple.jpg
    python evaluate_v5.py --image path/to/original.jpg \\
        --render path/to/render.png \\
        --detection path/to/detection.json \\
        --ground-truth path/to/ground-truth.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import cv2
import imagehash
import numpy as np
from PIL import Image
from rapidfuzz import fuzz
from skimage.metrics import structural_similarity as ssim

from ground_truths import get_ground_truth

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent.resolve()
DATASET_DIR = SCRIPT_DIR / "dataset"
OUTPUT_DIR = SCRIPT_DIR / "output"
EVAL_CACHE_DIR = OUTPUT_DIR / ".eval_cache"
DEFAULT_MODEL = "google/gemini-2.5-flash"
DEFAULT_MODEL_SAFE = "google-gemini-2-5-flash"

# All 14 dataset images (in priority order matching the dataset listing)
DATASET_IMAGES: list[str] = [
    "poster-simple.jpg",
    "poster-gradient.jpg",
    "flyer-text-heavy.jpg",
    "poster-person.jpg",
    "banner-horizontal.jpg",
    "poster-display-font.jpg",
    "poster-low-contrast.jpg",
    "multi-photo-collage.jpg",
    "portrait-overlay.jpg",
    "showcase-two-products.jpg",
    "inpaint-face-text.jpg",
    "inpaint-forest-text.jpg",
    "inpaint-pattern-text.jpg",
    "meditacion_11_julio_vertical_completo.jpg",
]

# ---------------------------------------------------------------------------
# Weights for the 7 evaluation dimensions
# ---------------------------------------------------------------------------

WEIGHTS: dict[str, float] = {
    "layout": 0.20,
    "textAccuracy": 0.20,
    "colorAccuracy": 0.10,
    "visualSimilarity": 0.15,
    "editability": 0.10,
    "structureF1": 0.10,
    "posterQuality": 0.15,
}

# ---------------------------------------------------------------------------
# Enums & Dataclasses
# ---------------------------------------------------------------------------


class ScoreDimension(str, Enum):
    """The 7 evaluation dimensions for V5 auto-evaluator."""

    LAYOUT = "layout"
    TEXT_ACCURACY = "textAccuracy"
    COLOR_ACCURACY = "colorAccuracy"
    VISUAL_SIMILARITY = "visualSimilarity"
    EDITABILITY = "editability"
    STRUCTURE_F1 = "structureF1"
    POSTER_QUALITY = "posterQuality"


@dataclass
class EvaluationResult:
    """Result of evaluating a single image across all 7 dimensions.

    Each dimension score is in [0.0, 1.0] and *overall* is the weighted sum.
    """

    image_id: str
    layout: float = 0.0
    textAccuracy: float = 0.0
    colorAccuracy: float = 0.0
    visualSimilarity: float = 0.0
    editability: float = 0.0
    structureF1: float = 0.0
    posterQuality: float = 0.0
    overall: float = 0.0
    weights: dict[str, float] = field(default_factory=lambda: dict(WEIGHTS))
    details: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSON output."""
        return asdict(self)


# ===================================================================
# LOW-LEVEL SCORING FUNCTIONS (one per dimension)
# ===================================================================


def _resize_to_match(img: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Resize *img* to the spatial dimensions of *target*."""
    h, w = target.shape[:2]
    return cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)


def score_layout(
    original_path: Path, render_path: Path
) -> tuple[float, Optional[dict]]:
    """Score dimension 1 — **layout** via SSIM on grayscale.

    Uses ``skimage.metrics.structural_similarity`` on grayscale versions
    of both images.  The render is resized to match the original's
    dimensions before comparison.

    Returns
    -------
    ``(score, details_or_None)``
    """
    try:
        orig = cv2.imread(str(original_path), cv2.IMREAD_GRAYSCALE)
        rend = cv2.imread(str(render_path), cv2.IMREAD_GRAYSCALE)
        if orig is None or rend is None:
            logger.warning("  [layout] Could not read one or both images")
            return 0.0, {"error": "image read failure"}

        # Resize render to match original spatial dimensions
        if orig.shape != rend.shape:
            rend = _resize_to_match(rend, orig)

        ssim_score = ssim(orig, rend, data_range=rend.max() - rend.min())
        ssim_score = max(0.0, min(1.0, float(ssim_score)))
        return ssim_score, {"ssim": round(ssim_score, 4)}
    except Exception as exc:
        logger.warning("  [layout] Exception: %s", exc)
        return 0.0, {"error": str(exc)}


def _ocr_text(image_path: Path, reader: Any) -> list[str]:
    """Run easyocr on *image_path* and return a list of recognised text strings."""
    try:
        results = reader.readtext(str(image_path))
        return [item[1] for item in results]
    except Exception as exc:
        logger.warning("  [ocr] Failed on %s: %s", image_path.name, exc)
        return []


def score_text_accuracy(
    render_path: Path,
    detection: dict,
    reader: Optional[Any] = None,
) -> tuple[float, Optional[dict]]:
    """Score dimension 2 — **textAccuracy** via expected-texts OCR.

    Instead of comparing original vs render OCR (which is fragile), uses the
    texts detected by Qwen (``detection``) as the ground-truth expected texts,
    then checks whether each one appears in the render via easyocr.

    Returns
    -------
    ``(score, details_or_None)``
    """
    try:
        # Collect expected texts from detection (Qwen-sourced only, skip Florence)
        expected = _collect_expected_texts(detection)
        if not expected:
            logger.info("  [textAccuracy] No expected texts in detection -> 1.0")
            return 1.0, {"expected": [], "found": [], "matched": 0, "total": 0}

        if reader is None:
            import easyocr

            reader = easyocr.Reader(["en"], gpu=False)

        render_texts = _ocr_text(render_path, reader)
        # Normalise: lowercase, strip, collapse whitespace
        render_norm = [re.sub(r"\s+", " ", t.lower()).strip() for t in render_texts]

        # Build combined token set from ALL render OCR (for subset matching)
        all_render_tokens: set[str] = set()
        for rn in render_norm:
            all_render_tokens.update(rn.split())

        matched = 0
        details_per_text = []
        for exp in expected:
            exp_norm = re.sub(r"\s+", " ", exp.lower()).strip()
            # Phase 1: best fuzzy match against individual OCR results
            best = max(
                (fuzz.ratio(exp_norm, rn) for rn in render_norm),
                default=0,
            )
            # Phase 2: token coverage — all expected words appear across render?
            exp_tokens = set(exp_norm.split())
            if exp_tokens and all_render_tokens:
                covered = len(exp_tokens & all_render_tokens) / len(exp_tokens)
                token_score = covered * 100
            else:
                token_score = 0
            final_best = max(best, token_score)
            found = final_best >= 70  # 70% fuzzy threshold
            if found:
                matched += 1
            details_per_text.append({
                "text": exp,
                "found": found,
                "best_match_pct": round(best, 1),
                "token_coverage_pct": round(token_score, 1),
                "final_score": round(final_best, 1),
            })

        score = matched / len(expected) if expected else 1.0
        score = max(0.0, min(1.0, score))

        return score, {
            "expected_count": len(expected),
            "matched_count": matched,
            "score": round(score, 4),
            "details": details_per_text,
            "render_ocr_raw": render_texts[:20],
        }
    except Exception as exc:
        logger.warning("  [textAccuracy] Exception: %s", exc)
        return 0.0, {"error": str(exc)}


def _iter_detection_elements(detection: dict):
    """Yield all elements from detection regardless of format.

    V4/V5: ``elements`` array with ``type`` field.
    V6:    separate ``text_elements``, ``images``, ``shapes`` arrays.
    """
    if "text_elements" in detection:
        for el in detection.get("text_elements", []):
            yield {"type": "text", **el}
        for el in detection.get("images", []):
            yield {"type": "image", **el}
        for el in detection.get("shapes", []):
            yield {"type": "shape", **el}
    elif "elements" in detection:
        yield from detection["elements"]


def _collect_expected_texts(detection: dict) -> list[str]:
    """Collect unique, non-noise texts from detection results.

    Handles both V4/V5 format (``elements`` array with ``type`` field)
    and V6 format (``text_elements`` array, ``images``, ``shapes``).
    Filters out Florence-2 noise (``</s>`` prefix, exact dupes, etc.).
    """
    seen: set[str] = set()
    texts: list[str] = []

    # V6-style: text_elements, images, shapes
    if "text_elements" in detection:
        for el in detection.get("text_elements", []):
            text = (el.get("text") or el.get("content") or "").strip()
            if not text:
                continue
            # Skip Florence-2 noise
            source = el.get("source", "")
            if source == "florence-2":
                continue
            norm = re.sub(r"\s+", " ", text.lower()).strip()
            if norm in seen:
                continue
            seen.add(norm)
            texts.append(text)

    # V4/V5-style: elements array with type field
    elif "elements" in detection:
        for el in _iter_detection_elements(detection):
            if el.get("type") != "text":
                continue
            text = (el.get("text") or el.get("content") or "").strip()
            if not text:
                continue
            source = el.get("source", "")
            if source == "florence-2":
                continue
            norm = re.sub(r"\s+", " ", text.lower()).strip()
            if norm in seen:
                continue
            seen.add(norm)
            texts.append(text)

    return texts


def score_color_accuracy(
    original_path: Path, render_path: Path
) -> tuple[float, Optional[dict]]:
    """Score dimension 3 — **colorAccuracy** via HSV histogram correlation.

    Converts both images to HSV, computes 2D histograms (H & S channels),
    and compares them with OpenCV's ``cv2.compareHist`` (CORREL method).

    Returns
    -------
    ``(score, details_or_None)``
    """
    try:
        orig = cv2.imread(str(original_path))
        rend = cv2.imread(str(render_path))
        if orig is None or rend is None:
            return 0.0, {"error": "image read failure"}

        # Resize render to match original
        if orig.shape != rend.shape:
            rend = _resize_to_match(rend, orig)

        # HSV histograms
        orig_hsv = cv2.cvtColor(orig, cv2.COLOR_BGR2HSV)
        rend_hsv = cv2.cvtColor(rend, cv2.COLOR_BGR2HSV)

        h_bins, s_bins = 50, 60
        hist_size = [h_bins, s_bins]
        h_ranges = [0, 180]
        s_ranges = [0, 256]
        ranges = h_ranges + s_ranges
        channels = [0, 1]

        orig_hist = cv2.calcHist([orig_hsv], channels, None, hist_size, ranges, accumulate=False)
        rend_hist = cv2.calcHist([rend_hsv], channels, None, hist_size, ranges, accumulate=False)

        cv2.normalize(orig_hist, orig_hist, 0, 1, cv2.NORM_MINMAX)
        cv2.normalize(rend_hist, rend_hist, 0, 1, cv2.NORM_MINMAX)

        correlation = cv2.compareHist(orig_hist, rend_hist, cv2.HISTCMP_CORREL)
        # correlation is in [-1, 1]; shift to [0, 1]
        score = max(0.0, min(1.0, (correlation + 1.0) / 2.0))

        return score, {"correlation": round(correlation, 4), "score": round(score, 4)}
    except Exception as exc:
        logger.warning("  [colorAccuracy] Exception: %s", exc)
        return 0.0, {"error": str(exc)}


def score_visual_similarity(
    original_path: Path, render_path: Path
) -> tuple[float, Optional[dict]]:
    """Score dimension 4 — **visualSimilarity** via perceptual hash + SSIM.

    Uses ``imagehash.average_hash`` (phash) for a quick perceptual distance,
    combined with the SSIM score from *score_layout*.

    The final score is::

        0.6 * (1 - phash_norm_dist) + 0.4 * ssim_score

    Returns
    -------
    ``(score, details_or_None)``
    """
    try:
        # Perceptual hash
        orig_pil = Image.open(str(original_path))
        rend_pil = Image.open(str(render_path))

        orig_hash = imagehash.average_hash(orig_pil)
        rend_hash = imagehash.average_hash(rend_pil)

        hash_dist = orig_hash - rend_hash  # Hamming distance
        max_dist = orig_hash.hash.size  # total bits
        hash_similarity = 1.0 - (hash_dist / max_dist)
        hash_similarity = max(0.0, min(1.0, float(hash_similarity)))

        # SSIM component
        ssim_score, _ = score_layout(original_path, render_path)

        # Weighted blend
        score = 0.6 * hash_similarity + 0.4 * ssim_score
        score = max(0.0, min(1.0, score))

        return score, {
            "hash_distance": int(hash_dist),
            "hash_similarity": round(hash_similarity, 4),
            "ssim": round(ssim_score, 4),
            "blended_score": round(score, 4),
        }
    except Exception as exc:
        logger.warning("  [visualSimilarity] Exception: %s", exc)
        return 0.0, {"error": str(exc)}


def _count_element_types(
    detection: dict,
) -> dict[str, int]:
    """Count element types from a detection or scene dict.

    Handles two formats:
    - Qwen detection: ``text_elements``, ``images``, ``shapes``
    - SceneGraph:     ``layers`` with ``kind`` per entry
    """
    if "layers" in detection:
        return _count_scene_types(detection)
    return {
        "text": len(detection.get("text_elements", [])),
        "image": len(detection.get("images", [])),
        "shape": len(detection.get("shapes", [])),
    }


def _count_scene_types(scene: dict) -> dict[str, int]:
    """Count element kinds from a scene/layers dict."""
    layers = scene.get("layers", [])
    counts: dict[str, int] = {"text": 0, "image": 0, "shape": 0}
    for layer in layers:
        kind = layer.get("kind", "unknown")
        if kind in counts:
            counts[kind] += 1
        else:
            counts[kind] = 1
    return counts


def _type_count_score(extracted: dict[str, int], reference: dict[str, int]) -> float:
    """Score how well extracted type counts match reference (0.0–1.0).

    Uses a simple accuracy: ``1 - (sum(abs diff) / max(total_ref, 1))``.
    """
    all_keys = set(extracted) | set(reference)
    total_diff = sum(abs(extracted.get(k, 0) - reference.get(k, 0)) for k in all_keys)
    total_ref = sum(reference.values())
    if total_ref == 0:
        return 1.0 if total_diff == 0 else 0.0
    return max(0.0, 1.0 - (total_diff / total_ref))


def score_editability(
    detection: dict,
    ground_truth: Optional[dict] = None,
    scene: Optional[dict] = None,
) -> tuple[float, Optional[dict]]:
    """Score dimension 5 — **editability** via element count comparison.

    If a ground-truth SceneGraph is available, compares detection counts
    against it.  Otherwise falls back to comparing detection counts against
    the rendered SceneGraph (``scene``).

    Returns
    -------
    ``(score, details_or_None)``
    """
    try:
        detected_counts = _count_element_types(detection)

        if ground_truth and ground_truth.get("layers"):
            ref_counts = _count_scene_types(ground_truth)
            ref_source = "ground_truth"
        elif scene:
            ref_counts = _count_scene_types(scene)
            ref_source = "scene"
        else:
            return 0.0, {"error": "no reference (gt or scene) available"}

        score = _type_count_score(detected_counts, ref_counts)

        return score, {
            "detected": detected_counts,
            "reference": ref_counts,
            "reference_source": ref_source,
            "score": round(score, 4),
        }
    except Exception as exc:
        logger.warning("  [editability] Exception: %s", exc)
        return 0.0, {"error": str(exc)}


def score_structure_f1(
    detection: dict,
    ground_truth: Optional[dict] = None,
    scene: Optional[dict] = None,
) -> tuple[float, Optional[dict]]:
    """Score dimension 6 — **structureF1** (element type classification).

    Computes precision and recall for detecting each element type
    (text, image, shape) relative to ground truth or scene reference.

    If ground truth is available, it's used as the reference. Otherwise
    the rendered SceneGraph is used.

    Precision per type = min(detected, ref) / max(detected, 1)
    Recall per type = min(detected, ref) / max(ref, 1)
    F1 per type = harmonic mean of precision and recall
    Macro F1 = average F1 across types with non-zero reference count.

    Returns
    -------
    ``(score, details_or_None)``
    """
    try:
        detected_counts = _count_element_types(detection)

        if ground_truth and ground_truth.get("layers"):
            ref_counts = _count_scene_types(ground_truth)
            ref_source = "ground_truth"
        elif scene:
            ref_counts = _count_scene_types(scene)
            ref_source = "scene"
        else:
            return 0.0, {"error": "no reference (gt or scene) available"}

        types = ["text", "image", "shape"]
        f1_scores: dict[str, float] = {}
        weighted_f1_sum = 0.0
        total_weight = 0

        for t in types:
            detected = detected_counts.get(t, 0)
            ref = ref_counts.get(t, 0)

            if ref == 0 and detected == 0:
                # Perfect match on absent type
                f1_scores[t] = 1.0
                continue

            precision = min(detected, ref) / max(detected, 1)
            recall = min(detected, ref) / max(ref, 1)
            f1 = (2 * precision * recall / (precision + recall + 1e-10)
                  if (precision + recall) > 0 else 0.0)
            f1_scores[t] = round(f1, 4)

            if ref > 0:
                weighted_f1_sum += f1 * ref
                total_weight += ref

        macro_f1 = weighted_f1_sum / max(total_weight, 1) if total_weight > 0 else 1.0
        macro_f1 = max(0.0, min(1.0, macro_f1))

        return macro_f1, {
            "detected": detected_counts,
            "reference": ref_counts,
            "reference_source": ref_source,
            "f1_per_type": f1_scores,
            "macro_f1": round(macro_f1, 4),
        }
    except Exception as exc:
        logger.warning("  [structureF1] Exception: %s", exc)
        return 0.0, {"error": str(exc)}


# ===================================================================
# POSTER QUALITY DIMENSION — automated metrics (legibilidad, contraste, CTA)
# ===================================================================


def score_poster_quality(
    original_path: Path,
    render_path: Path,
    detection: dict,
    reader: Optional[Any] = None,
) -> tuple[float, Optional[dict]]:
    """Score dimension 7 — **posterQuality** (preservation of quality).

    Measures whether the render PRESERVES the original's poster quality
    across three dimensions:
      1. Legibilidad (0.40) — text readability similarity
      2. Contraste    (0.35) — text-background contrast similarity
      3. CTA          (0.25) — CTA prominence similarity

    For each sub-dimension we compute the score on BOTH original and
    render, then the final score is **how close they are** (1 − |diff|).
    If original and render have identical quality -> 1.0, even if both
    are "low" quality.

    All fully automated, no API calls.

    Returns
    -------
    ``(score, details_or_None)``
    """
    try:
        orig_img = cv2.imread(str(original_path))
        render_img = cv2.imread(str(render_path))
        if orig_img is None or render_img is None:
            return 0.0, {"error": "cannot read one or both images"}

        if reader is None:
            import easyocr
            reader = easyocr.Reader(["en"], gpu=False)

        WEIGHTS_PQ = {"legibilidad": 0.40, "contraste": 0.35, "cta": 0.25}

        # ── 1. Legibilidad ────────────────────────────────────────
        # Original: OCR its own texts directly
        orig_ocr = _ocr_text(original_path, reader)
        render_ocr = _ocr_text(render_path, reader)
        legibilidad, leg_details = _score_legibilidad(
            orig_ocr, render_ocr, detection
        )

        # ── 2. Contraste ──────────────────────────────────────────
        contraste, con_details = _score_contraste(
            orig_img, render_img, detection
        )

        # ── 3. CTA prominence ─────────────────────────────────────
        cta, cta_details = _score_cta_prominence(
            original_path, render_path, render_img, detection, reader
        )

        # ── Composite ─────────────────────────────────────────────
        composite = (
            WEIGHTS_PQ["legibilidad"] * legibilidad
            + WEIGHTS_PQ["contraste"] * contraste
            + WEIGHTS_PQ["cta"] * cta
        )
        composite = max(0.0, min(1.0, composite))

        return composite, {
            "pq_score": round(composite, 4),
            "weights": WEIGHTS_PQ,
            "legibilidad": {"score": round(legibilidad, 4), **leg_details},
            "contraste": {"score": round(contraste, 4), **con_details},
            "cta": {"score": round(cta, 4), **cta_details},
        }
    except Exception as exc:
        logger.warning("  [posterQuality] Exception: %s", exc)
        return 0.0, {"error": str(exc)}


def _score_legibilidad(
    orig_ocr: list[str],
    render_ocr: list[str],
    detection: dict,
) -> tuple[float, dict]:
    """Legibilidad: compare original OCR vs render OCR readability.

    1. Get expected texts from detection (what *should* be there).
    2. Compute % found in original OCR -> orig_quality.
    3. Compute % found in render OCR -> render_quality.
    4. Score = 1 − |orig_quality − render_quality|.
    """
    expected = _collect_expected_texts(detection)

    if not expected:
        # No expected texts -> compare raw OCR similarity
        orig_set = set(re.sub(r"\s+", " ", t.lower()).strip() for t in orig_ocr)
        render_set = set(re.sub(r"\s+", " ", t.lower()).strip() for t in render_ocr)
        if not orig_set and not render_set:
            return 1.0, {"note": "no texts in either", "orig_quality": 1.0, "render_quality": 1.0}
        intersect = orig_set & render_set
        similarity = len(intersect) / max(len(orig_set | render_set), 1)
        return similarity, {
            "note": "fallback: raw OCR similarity (no detection texts)",
            "orig_quality": 1.0 if not orig_set else 0.0,
            "render_quality": 1.0 if not render_set else 0.0,
            "ocr_similarity": round(similarity, 4),
        }

    def _best_match(exp_norm: str, candidates: list[str], all_tokens: set[str]) -> tuple[float, float]:
        """Best fuzzy match + token coverage for a single expected text."""
        best_fuzzy = max((fuzz.ratio(exp_norm, c) for c in candidates), default=0)
        exp_tokens = set(exp_norm.split())
        if exp_tokens and all_tokens:
            covered = len(exp_tokens & all_tokens) / len(exp_tokens)
            token_score = covered * 100
        else:
            token_score = 0
        return best_fuzzy, token_score

    # Compute quality on original
    orig_norm = [re.sub(r"\s+", " ", t.lower()).strip() for t in orig_ocr]
    orig_all_tokens: set[str] = set()
    for t in orig_norm:
        orig_all_tokens.update(t.split())
    orig_matched = 0
    for exp in expected:
        exp_norm = re.sub(r"\s+", " ", exp.lower()).strip()
        fuzzy, tokens = _best_match(exp_norm, orig_norm, orig_all_tokens)
        found = max(fuzzy, tokens) >= 70
        if found:
            orig_matched += 1
    orig_quality = orig_matched / len(expected) if expected else 1.0

    # Compute quality on render
    render_norm = [re.sub(r"\s+", " ", t.lower()).strip() for t in render_ocr]
    render_all_tokens: set[str] = set()
    for t in render_norm:
        render_all_tokens.update(t.split())
    render_matched = 0
    render_per_text = []
    for exp in expected:
        exp_norm = re.sub(r"\s+", " ", exp.lower()).strip()
        fuzzy, tokens = _best_match(exp_norm, render_norm, render_all_tokens)
        final = max(fuzzy, tokens)
        found = final >= 70
        if found:
            render_matched += 1
        render_per_text.append({
            "text": exp,
            "found": found,
            "best_match_pct": round(fuzzy, 1),
            "token_coverage_pct": round(tokens, 1),
            "final_score": round(final, 1),
        })
    render_quality = render_matched / len(expected) if expected else 1.0

    # Score = how close are they?
    score = 1.0 - abs(orig_quality - render_quality)

    return score, {
        "orig_quality": round(orig_quality, 4),
        "render_quality": round(render_quality, 4),
        "orig_matched": orig_matched,
        "render_matched": render_matched,
        "total_expected": len(expected),
        "render_per_text": render_per_text,
        "orig_ocr_preview": orig_ocr[:10],
        "render_ocr_preview": render_ocr[:10],
    }


def _score_contraste(
    orig_img: np.ndarray,
    render_img: np.ndarray,
    detection: dict,
) -> tuple[float, dict]:
    """Contraste: compare text-background contrast between original and render.

    For each text element in detection:
      1. Compute contrast on original at that position
      2. Compute contrast on render at that position
      3. Score per element = 1 − |orig_contrast − render_contrast|
    Returns average across all elements.
    """
    h, w = render_img.shape[:2]
    per_element: list[dict] = []
    scores: list[float] = []

    for el in _iter_detection_elements(detection):
        if el.get("type") != "text":
            continue
        pos = el.get("position", {})
        if not pos:
            continue
        tx, ty, tw, th = (
            int(pos.get("x", 0)),
            int(pos.get("y", 0)),
            int(pos.get("width", 0)),
            int(pos.get("height", 0)),
        )
        if tw < 5 or th < 5:
            continue

        text_hex = el.get("color") or (el.get("style") or {}).get("colorHex", "#000000")
        try:
            text_hex = text_hex.lstrip("#")
            tr, tg, tb = int(text_hex[:2], 16), int(text_hex[2:4], 16), int(text_hex[4:6], 16)
        except (ValueError, IndexError):
            tr, tg, tb = 0, 0, 0
        text_lum = 0.299 * tr + 0.587 * tg + 0.114 * tb

        def _weber_contrast(img: np.ndarray) -> float:
            x1, y1 = max(0, tx - 5), max(0, ty - 5)
            x2, y2 = min(img.shape[1], tx + tw + 5), min(img.shape[0], ty + th + 5)
            if x2 <= x1 or y2 <= y1:
                return 0.0
            bg = img[y1:y2, x1:x2]
            bg_mean = bg.mean(axis=(0, 1))
            bg_lum = 0.114 * bg_mean[0] + 0.587 * bg_mean[1] + 0.299 * bg_mean[2]
            if bg_lum < 1:
                bg_lum = 1.0
            return abs(text_lum - bg_lum) / bg_lum

        orig_contrast = _weber_contrast(orig_img)
        render_contrast = _weber_contrast(render_img)

        # Normalise both
        orig_norm = min(1.0, orig_contrast * 1.2)
        render_norm = min(1.0, render_contrast * 1.2)

        element_score = 1.0 - abs(orig_norm - render_norm)
        scores.append(element_score)
        per_element.append({
            "id": el.get("id", "?"),
            "orig_contrast": round(orig_contrast, 3),
            "render_contrast": round(render_contrast, 3),
            "orig_score": round(orig_norm, 3),
            "render_score": round(render_norm, 3),
            "similarity": round(element_score, 3),
        })

    if not scores:
        return 0.5, {"note": "no text elements with positions", "per_element": []}

    avg = sum(scores) / len(scores)
    return avg, {
        "average_similarity": round(avg, 4),
        "element_count": len(scores),
        "per_element": per_element,
    }


def _score_cta_prominence(
    original_path: Path,
    render_path: Path,
    render_img: np.ndarray,
    detection: dict,
    reader: Any,
) -> tuple[float, dict]:
    """CTA prominence: compare CTA visibility between original and render.

    Uses easyocr on both images to find CTA-like text, then compares
    their size and position prominence.
    """
    h, w = render_img.shape[:2]
    canvas_area = w * h
    cta_keywords = [
        "buy", "shop", "sale", "register", "sign up", "subscribe",
        "join", "get", "try", "start", "download", "learn more",
        "call", "book", "order", "reserve", "contact", "more info",
    ]

    def _detect_cta_in_ocr(ocr_texts: list[str]) -> float:
        """Return a CTA prominence score from OCR text list."""
        if not ocr_texts:
            return 0.0
        hits = 0
        for t in ocr_texts:
            tl = t.lower().strip()
            if any(kw in tl for kw in cta_keywords):
                hits += 1
        return min(1.0, hits / max(len(ocr_texts), 1) * 3)

    # Also check detection for CTA-tagged elements
    def _cta_from_detection() -> float:
        """Return CTA prominence from detection data (size+position)."""
        scores = []
        for el in _iter_detection_elements(detection):
            text = (el.get("text") or el.get("content") or "").lower().strip()
            role = (el.get("visualRole") or el.get("role") or "").lower().strip()
            is_cta = role in ("cta", "button") or any(kw in text for kw in cta_keywords)
            if not is_cta:
                continue
            pos = el.get("position", {})
            if not pos:
                continue
            cw, ch = pos.get("width", 0), pos.get("height", 0)
            area_ratio = (cw * ch) / max(canvas_area, 1)
            cx = (pos.get("x", 0) + cw / 2) / max(w, 1)
            cy = (pos.get("y", 0) + ch / 2) / max(h, 1)
            pos_score = 1.0 - abs(cx - 0.5) * 0.5 - abs(cy - 0.65) * 0.5
            pos_score = max(0.0, min(1.0, pos_score))
            size_score = min(1.0, area_ratio * 10)
            scores.append(0.5 * size_score + 0.5 * pos_score)
        return max(scores) if scores else 0.0

    orig_ocr_cta = _detect_cta_in_ocr(_ocr_text(original_path, reader))
    render_ocr_cta = _detect_cta_in_ocr(_ocr_text(render_path, reader))
    det_cta = _cta_from_detection()

    orig_score = orig_ocr_cta
    render_score = max(render_ocr_cta, det_cta)

    score = 1.0 - abs(orig_score - render_score)
    return score, {
        "orig_score": round(orig_score, 4),
        "render_score": round(render_score, 4),
        "ocr_orig_cta_hits": orig_ocr_cta,
        "ocr_render_cta_hits": render_ocr_cta,
        "detection_cta_score": round(det_cta, 4),
        "similarity": round(score, 4),
    }


# ===================================================================
# ORCHESTRATOR
# ===================================================================


def evaluate_single(
    original_path: Path,
    render_path: Path,
    detection_path: Path,
    image_id: str,
    ground_truth: Optional[dict] = None,
    ocr_reader: Any = None,
) -> EvaluationResult:
    """Run all 7 evaluation dimensions for a single image.

    Parameters
    ----------
    original_path:
        Path to the original design image.
    render_path:
        Path to the rendered output image.
    detection_path:
        Path to the detection JSON (output of Qwen / Florence).
    image_id:
        Unique identifier for this image (used for caching).
    ground_truth:
        Optional ground-truth SceneGraph dict.
    ocr_reader:
        Optional pre-initialised easyocr Reader instance.

    Returns
    -------
    EvaluationResult with all dimension scores and the weighted overall.
    """
    # Load detection
    try:
        detection = json.loads(detection_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.error("  Cannot read detection: %s", exc)
        detection = {"text_elements": [], "images": [], "shapes": []}

    # Load scene (if available next to render)
    scene_path = render_path.parent / "scene.json"
    scene = None
    if scene_path.is_file():
        try:
            scene = json.loads(scene_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Dimension 1: Layout
    logger.info("  [layout] SSIM...")
    layout_score, layout_details = score_layout(original_path, render_path)

    # Dimension 2: Text Accuracy (uses detection texts as expected)
    logger.info("  [textAccuracy] Expected-texts OCR...")
    text_score, text_details = score_text_accuracy(
        render_path, detection, reader=ocr_reader
    )

    # Dimension 3: Color Accuracy
    logger.info("  [colorAccuracy] HSV histogram...")
    color_score, color_details = score_color_accuracy(original_path, render_path)

    # Dimension 4: Visual Similarity
    logger.info("  [visualSimilarity] Perceptual hash + SSIM...")
    visual_score, visual_details = score_visual_similarity(
        original_path, render_path
    )

    # Dimension 5: Editability
    logger.info("  [editability] Element counts...")
    edit_score, edit_details = score_editability(
        detection, ground_truth=ground_truth, scene=scene
    )

    # Dimension 6: Structure F1
    logger.info("  [structureF1] Type classification...")
    struct_score, struct_details = score_structure_f1(
        detection, ground_truth=ground_truth, scene=scene
    )

    # Dimension 7: Poster Quality (legibilidad, contraste, CTA)
    logger.info("  [posterQuality] Comparing original vs render quality...")
    pq_score, pq_details = score_poster_quality(
        original_path, render_path, detection, reader=ocr_reader
    )

    # Weighted overall
    overall = (
        WEIGHTS["layout"] * layout_score
        + WEIGHTS["textAccuracy"] * text_score
        + WEIGHTS["colorAccuracy"] * color_score
        + WEIGHTS["visualSimilarity"] * visual_score
        + WEIGHTS["editability"] * edit_score
        + WEIGHTS["structureF1"] * struct_score
        + WEIGHTS["posterQuality"] * pq_score
    )

    result = EvaluationResult(
        image_id=image_id,
        layout=round(layout_score, 4),
        textAccuracy=round(text_score, 4),
        colorAccuracy=round(color_score, 4),
        visualSimilarity=round(visual_score, 4),
        editability=round(edit_score, 4),
        structureF1=round(struct_score, 4),
        posterQuality=round(pq_score, 4),
        overall=round(overall, 4),
        details={
            "layout": layout_details,
            "textAccuracy": text_details,
            "colorAccuracy": color_details,
            "visualSimilarity": visual_details,
            "editability": edit_details,
            "structureF1": struct_details,
            "posterQuality": pq_details,
        },
    )

    return result


# ===================================================================
# BATCH EVALUATION
# ===================================================================


def find_output_image(
    image_filename: str,
    output_base: Path,
    model_safe: str = DEFAULT_MODEL_SAFE,
) -> Optional[Path]:
    """Find the render output for *image_filename* under *output_base*.

    Searches::

        {output_base}/{model_safe}/{image_stem}/
        {output_base}/**/{image_stem}/render.png

    Returns the first ``render.png`` found, or ``None``.
    """
    stem = Path(image_filename).stem

    # Primary location: model_safe / image_stem
    primary = output_base / model_safe / stem / "render.png"
    if primary.is_file():
        return primary

    # Search in v4 structure
    v4 = output_base / "qwen-qwen3-vl-32b-instruct" / "v4" / stem / "render.png"
    if v4.is_file():
        return v4

    # Fallback: glob search
    for candidate in sorted(output_base.rglob(f"*/{stem}/render.png")):
        return candidate

    return None


def find_detection_json(
    image_filename: str,
    output_base: Path,
    model_safe: str = DEFAULT_MODEL_SAFE,
) -> Optional[Path]:
    """Find the detection JSON for *image_filename*.

    Prefers the v4 ``detection.json`` (Qwen output format with
    ``text_elements``, ``images``, ``shapes`` keys) over the rendered
    ``scene.json`` (SceneGraph format with ``layers``).
    """
    stem = Path(image_filename).stem

    # v4 detection (preferred — has text_elements/images/shapes structure)
    v4 = output_base / "qwen-qwen3-vl-32b-instruct" / "v4" / stem / "detection.json"
    if v4.is_file():
        return v4

    # Primary model output detection
    primary = output_base / model_safe / stem / "detection.json"
    if primary.is_file():
        return primary

    # Fallback: any detection.json
    for candidate in sorted(output_base.rglob(f"*/{stem}/detection.json")):
        return candidate

    return None


def run_batch(
    output_dir: str | Path = "output",
    model_safe: str = DEFAULT_MODEL_SAFE,
    images: Optional[list[str]] = None,
) -> list[EvaluationResult]:
    """Run evaluation on all (or specified) dataset images.

    Parameters
    ----------
    output_dir:
        Base output directory.
    model_safe:
        Model directory name (safe path version).
    images:
        Subset of image filenames to evaluate.  Defaults to all 14.

    Returns
    -------
    List of ``EvaluationResult`` (one per image processed).
    """
    output_base = Path(output_dir) if Path(output_dir).is_absolute() else SCRIPT_DIR / output_dir

    if images is None:
        images = list(DATASET_IMAGES)

    # Pre-initialise OCR reader once for the batch
    import easyocr

    try:
        ocr_reader = easyocr.Reader(["en"], gpu=False)
    except Exception as exc:
        logger.warning("Failed to initialise easyocr: %s", exc)
        ocr_reader = None

    results: list[EvaluationResult] = []

    for img_name in images:
        original_path = DATASET_DIR / img_name
        if not original_path.is_file():
            logger.warning("  Original not found: %s", original_path)
            results.append(
                EvaluationResult(
                    image_id=Path(img_name).stem,
                    details={"error": f"original not found: {original_path}"},
                )
            )
            continue

        render_path = find_output_image(img_name, output_base, model_safe)
        if render_path is None:
            logger.warning("  Render not found for: %s", img_name)
            results.append(
                EvaluationResult(
                    image_id=Path(img_name).stem,
                    details={"error": "render not found"},
                )
            )
            continue

        detection_path = find_detection_json(img_name, output_base, model_safe)
        if detection_path is None:
            logger.warning("  Detection not found for: %s", img_name)
            results.append(
                EvaluationResult(
                    image_id=Path(img_name).stem,
                    details={"error": "detection not found"},
                )
            )
            continue

        image_id = Path(img_name).stem
        ground_truth = get_ground_truth(image_id)

        logger.info("\n  Evaluating: %s", image_id)
        logger.info("    Original : %s", original_path)
        logger.info("    Render   : %s", render_path)
        logger.info("    Detection: %s", detection_path)
        logger.info("    GT       : %s", "yes" if ground_truth else "no")

        t0 = time.monotonic()
        result = evaluate_single(
            original_path=original_path,
            render_path=render_path,
            detection_path=detection_path,
            image_id=image_id,
            ground_truth=ground_truth,
            ocr_reader=ocr_reader,
        )
        elapsed = time.monotonic() - t0
        logger.info(
            "    Score: %.4f overall  (%.1fs)",
            result.overall, elapsed,
        )

        results.append(result)

    return results


def _generate_summary(results: list[EvaluationResult]) -> dict:
    """Build a summary dict from a list of per-image evaluation results."""
    n = len(results)
    if n == 0:
        return {"images_evaluated": 0, "scores": {}}

    dims = [
        "layout", "textAccuracy", "colorAccuracy",
        "visualSimilarity", "editability", "structureF1", "posterQuality",
    ]

    totals: dict[str, float] = {d: 0.0 for d in dims}
    totals["overall"] = 0.0
    counts = {d: 0 for d in dims}
    counts["overall"] = 0

    per_image: list[dict] = []
    for r in results:
        entry = {"image_id": r.image_id}
        has_error = r.details and "error" in r.details
        for d in dims:
            val = getattr(r, d, 0.0)
            entry[d] = val
            if not has_error:
                totals[d] += val
                counts[d] += 1
        entry["overall"] = r.overall
        if not has_error:
            totals["overall"] += r.overall
            counts["overall"] += 1
        per_image.append(entry)

    averages = {}
    for d in dims:
        averages[d] = round(totals[d] / max(counts[d], 1), 4)
    averages["overall"] = round(totals["overall"] / max(counts["overall"], 1), 4)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "images_evaluated": n,
        "dimensions": dims,
        "weights": dict(WEIGHTS),
        "averages": averages,
        "per_image": per_image,
    }


# ===================================================================
# CLI
# ===================================================================


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    p = argparse.ArgumentParser(
        description="Auto-Evaluator V5 — 7-dimension quality scoring for Smart Import"
    )
    p.add_argument(
        "--all",
        action="store_true",
        help="Run evaluation on all 14 dataset images",
    )
    p.add_argument(
        "--image",
        default=None,
        help="Path to the original design image (or image stem for --all mode)",
    )
    p.add_argument(
        "--render",
        default=None,
        help="Path to the rendered output image (required with --image)",
    )
    p.add_argument(
        "--detection",
        default=None,
        help="Path to the detection JSON (required with --image)",
    )
    p.add_argument(
        "--ground-truth",
        default=None,
        help="Path to ground-truth JSON (optional for single mode)",
    )
    p.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for result JSON files (default: output/)",
    )
    p.add_argument(
        "--model",
        default=DEFAULT_MODEL_SAFE,
        help=f"Model directory name (default: {DEFAULT_MODEL_SAFE})",
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG logging",
    )
    return p


def main() -> None:
    """CLI entry point for the V5 auto-evaluator."""
    parser = build_parser()
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stdout,
    )

    output_base = Path(args.output_dir) if args.output_dir else OUTPUT_DIR

    if args.all:
        logger.info("V5 Auto-Evaluator — Batch mode (%d images)", len(DATASET_IMAGES))
        t_start = time.monotonic()
        results = run_batch(
            output_dir=str(output_base),
            model_safe=args.model,
        )
        elapsed_total = time.monotonic() - t_start

        # Generate summary
        summary = _generate_summary(results)

        # Save per-image results
        EVAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        for r in results:
            out_path = output_base / args.model / r.image_id / "evaluate_v5.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                json.dumps(r.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        # Save summary
        summary_path = output_base / args.model / "evaluate_v5_summary.json"
        summary_path.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Print summary table
        logger.info("\n" + "=" * 70)
        logger.info("V5 EVALUATION SUMMARY")
        logger.info("=" * 70)
        logger.info(
            "  %-30s  %s", "Dimension", "Average"
        )
        logger.info("  " + "-" * 42)
        for dim in summary["dimensions"]:
            logger.info("  %-30s  %.4f", dim, summary["averages"][dim])
        logger.info("  " + "-" * 42)
        logger.info("  %-30s  %.4f", "OVERALL", summary["averages"]["overall"])
        logger.info("")
        logger.info("  Images: %d  |  Time: %.1fs", len(results), elapsed_total)
        logger.info("  Results saved to: %s", summary_path)
        logger.info("")

        # Per-image table
        logger.info("%-30s  %-8s  %-8s  %-8s  %-8s  %-8s  %-8s  %-8s  %-8s",
                     "Image", "Layout", "Text", "Color", "Visual",
                     "Edit", "F1", "Sem", "Overall")
        logger.info("-" * 110)
        for r in results:
            err = r.details and r.details.get("error")
            if err:
                logger.info("%-30s  ERROR: %s", r.image_id, err)
            else:
                logger.info(
                    "%-30s  %-8.4f  %-8.4f  %-8.4f  %-8.4f  %-8.4f  %-8.4f  %-8.4f  %-8.4f",
                    r.image_id,
                    r.layout, r.textAccuracy, r.colorAccuracy,
                    r.visualSimilarity, r.editability, r.structureF1,
                    r.posterQuality, r.overall,
                )

        logger.info("\nDone.")

    elif args.image:
        # Single image mode
        img_path = Path(args.image)
        render_path = Path(args.render) if args.render else None
        detection_path = Path(args.detection) if args.detection else None

        if not img_path.is_file():
            logger.error("Image not found: %s", img_path)
            sys.exit(1)

        # Try to auto-discover render and detection if only --image given
        if render_path is None or detection_path is None:
            image_id = img_path.stem
            found_render = None
            found_detection = None

            if render_path is None:
                found_render = find_output_image(img_path.name, output_base, args.model)
                if found_render is None:
                    logger.error(
                        "Render not found for '%s'. Provide --render explicitly.",
                        image_id,
                    )
                    sys.exit(1)
                render_path = found_render

            if detection_path is None:
                found_detection = find_detection_json(
                    img_path.name, output_base, args.model
                )
                if found_detection is None:
                    logger.error(
                        "Detection not found for '%s'. Provide --detection explicitly.",
                        image_id,
                    )
                    sys.exit(1)
                detection_path = found_detection

        # Load ground truth if provided
        ground_truth = None
        if args.ground_truth:
            gt_path = Path(args.ground_truth)
            if gt_path.is_file():
                ground_truth = json.loads(gt_path.read_text(encoding="utf-8"))
        else:
            ground_truth = get_ground_truth(img_path.stem)

        logger.info(
            "V5 Auto-Evaluator — Single mode\n"
            "  Original : %s\n"
            "  Render   : %s\n"
            "  Detection: %s\n"
            "  GT       : %s",
            img_path, render_path, detection_path,
            "yes" if ground_truth else "no",
        )

        t0 = time.monotonic()
        result = evaluate_single(
            original_path=img_path,
            render_path=render_path,
            detection_path=detection_path,
            image_id=img_path.stem,
            ground_truth=ground_truth,
        )
        elapsed = time.monotonic() - t0

        # Print result
        logger.info("\n" + "=" * 50)
        logger.info("EVALUATION RESULT: %s", img_path.stem)
        logger.info("=" * 50)
        for dim in ["layout", "textAccuracy", "colorAccuracy",
                     "visualSimilarity", "editability", "structureF1", "posterQuality"]:
            logger.info("  %-20s  %.4f", dim, getattr(result, dim))
        logger.info("-" * 50)
        logger.info("  %-20s  %.4f", "OVERALL", result.overall)
        logger.info("  Elapsed: %.1fs", elapsed)

        # Save result
        eval_cache_dir = EVAL_CACHE_DIR
        eval_cache_dir.mkdir(parents=True, exist_ok=True)
        out_path = eval_cache_dir / f"{img_path.stem}_result.json"
        out_path.write_text(
            json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("  Saved to: %s", out_path)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
