"""
evaluate_v5.py — Auto-Evaluator V5 for Smart Import Pipeline.

Compares original design images against rendered output across 7 scoring
dimensions: layout, textAccuracy, colorAccuracy, visualSimilarity,
editability, structureF1, and semantic (Gemini judge).

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
    "semantic": 0.15,
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
    SEMANTIC = "semantic"


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
    semantic: float = 0.0
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
    original_path: Path,
    render_path: Path,
    reader: Optional[Any] = None,
) -> tuple[float, Optional[dict]]:
    """Score dimension 2 — **textAccuracy** via easyocr + rapidfuzz.

    Extracts text from both images with easyocr, then computes
    ``fuzz.token_sort_ratio`` on the concatenated text strings.

    Returns
    -------
    ``(score, details_or_None)``
    """
    try:
        if reader is None:
            import easyocr

            reader = easyocr.Reader(["en"], gpu=False)

        orig_texts = _ocr_text(original_path, reader)
        render_texts = _ocr_text(render_path, reader)

        orig_concat = " ".join(orig_texts)
        render_concat = " ".join(render_texts)

        if not orig_concat and not render_concat:
            # Both empty → no text to compare → perfect score
            return 1.0, {"orig_texts": [], "render_texts": [], "similarity": 1.0}

        if not orig_concat or not render_concat:
            # One has text, the other doesn't
            return 0.0, {
                "orig_texts": orig_texts,
                "render_texts": render_texts,
                "similarity": 0.0,
            }

        similarity = fuzz.token_sort_ratio(orig_concat, render_concat) / 100.0
        similarity = max(0.0, min(1.0, similarity))

        return similarity, {
            "orig_texts": orig_texts,
            "render_texts": render_texts,
            "similarity": round(similarity, 4),
        }
    except Exception as exc:
        logger.warning("  [textAccuracy] Exception: %s", exc)
        return 0.0, {"error": str(exc)}


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
# SEMANTIC DIMENSION — Gemini via OpenRouter (cached)
# ===================================================================


def _gemini_eval_prompt() -> str:
    """Return the system prompt for the semantic judge evaluation."""
    return (
        "You are a design quality judge. Compare the ORIGINAL design image "
        "with the IMPORTED RENDER (a screenshot of what the editor produced). "
        "Evaluate whether the render preserves the original design intent — "
        "layout, color scheme, text content, visual hierarchy, and overall "
        "aesthetic. Return ONLY valid JSON matching this schema:\n"
        '{"semanticScore": 0.0-1.0, "reasoning": "brief explanation", '
        '"criticalIssues": ["..."], "strengths": ["..."]}'
    )


def call_gemini(
    original_path: Path,
    render_path: Path,
    model: str = DEFAULT_MODEL,
) -> dict:
    """Call Gemini (via OpenRouter) to evaluate semantic similarity.

    Parameters
    ----------
    original_path:
        Path to the original design image.
    render_path:
        Path to the rendered output image.
    model:
        OpenRouter model identifier (default: ``google/gemini-2.5-flash``).

    Returns
    -------
    dict
        Parsed JSON response with keys ``semanticScore``, ``reasoning``,
        ``criticalIssues``, ``strengths``.

    Raises
    ------
    OpenRouterError
        If the API call fails or response cannot be parsed.
    """
    # Lazy import to avoid circular dependency at module level
    from openrouter import OpenRouterClient, _encode_image, OpenRouterError

    original_b64 = _encode_image(str(original_path))
    render_b64 = _encode_image(str(render_path))

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": _gemini_eval_prompt()},
                {"type": "image_url", "image_url": {"url": original_b64}},
                {"type": "image_url", "image_url": {"url": render_b64}},
            ],
        }
    ]

    client = OpenRouterClient(model=model)
    response = client.chat_completion(
        messages=messages,
        response_format={"type": "json_object"},
        model=model,
    )

    if response.status == "error":
        raise OpenRouterError(
            f"Gemini semantic evaluation failed: {response.error_message}",
            response_body=response.error_message or "",
        )

    # Parse JSON from response
    content = response.content.strip()
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        result = OpenRouterClient._parse_json_response(content, "semantic")

    return {
        "semanticScore": result.get("semanticScore", 0.0),
        "reasoning": result.get("reasoning", ""),
        "criticalIssues": result.get("criticalIssues", []),
        "strengths": result.get("strengths", []),
    }


def _cached_gemini_eval(
    original_path: Path,
    render_path: Path,
    image_id: str,
) -> dict:
    """Call semantic Gemini judge with caching.

    Caches results in ``output/.eval_cache/{image_id}.json`` to avoid
    re-calling the API for the same image.

    Returns
    -------
    dict with keys ``semanticScore``, ``reasoning``, ``criticalIssues``,
    ``strengths``.
    """
    EVAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = EVAL_CACHE_DIR / f"{image_id}.json"

    # Check cache first
    if cache_path.is_file():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            # Validate cache has the expected key
            if "semanticScore" in cached:
                logger.info("  [semantic] Using cached result")
                return cached
        except (json.JSONDecodeError, OSError):
            logger.warning("  [semantic] Cache corrupt, re-evaluating")

    # Call API
    logger.info("  [semantic] Calling Gemini via OpenRouter...")
    try:
        result = call_gemini(original_path, render_path)

        # Normalise score
        raw = result.get("semanticScore", 0.0)
        if isinstance(raw, str):
            raw = float(raw)
        result["semanticScore"] = max(0.0, min(1.0, float(raw)))

        # Cache result
        cache_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return result
    except Exception as exc:
        logger.warning("  [semantic] API call failed: %s", exc)
        return {
            "semanticScore": 0.0,
            "reasoning": f"API error: {exc}",
            "criticalIssues": [],
            "strengths": [],
        }


def score_semantic(
    original_path: Path,
    render_path: Path,
    image_id: str,
) -> tuple[float, Optional[dict]]:
    """Score dimension 7 — **semantic** via Gemini judge.

    Uses ``call_gemini`` (with caching) to evaluate whether the render
    preserves the original design intent.

    Returns
    -------
    ``(score, details_or_None)``
    """
    result = _cached_gemini_eval(original_path, render_path, image_id)
    score = result.get("semanticScore", 0.0)
    return score, {
        "semanticScore": round(score, 4),
        "reasoning": result.get("reasoning", ""),
        "criticalIssues": result.get("criticalIssues", []),
        "strengths": result.get("strengths", []),
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

    # Dimension 2: Text Accuracy
    logger.info("  [textAccuracy] OCR + rapidfuzz...")
    text_score, text_details = score_text_accuracy(
        original_path, render_path, reader=ocr_reader
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

    # Dimension 7: Semantic (Gemini)
    logger.info("  [semantic] Gemini judge...")
    semantic_score, semantic_details = score_semantic(
        original_path, render_path, image_id
    )

    # Weighted overall
    overall = (
        WEIGHTS["layout"] * layout_score
        + WEIGHTS["textAccuracy"] * text_score
        + WEIGHTS["colorAccuracy"] * color_score
        + WEIGHTS["visualSimilarity"] * visual_score
        + WEIGHTS["editability"] * edit_score
        + WEIGHTS["structureF1"] * struct_score
        + WEIGHTS["semantic"] * semantic_score
    )

    result = EvaluationResult(
        image_id=image_id,
        layout=round(layout_score, 4),
        textAccuracy=round(text_score, 4),
        colorAccuracy=round(color_score, 4),
        visualSimilarity=round(visual_score, 4),
        editability=round(edit_score, 4),
        structureF1=round(struct_score, 4),
        semantic=round(semantic_score, 4),
        overall=round(overall, 4),
        details={
            "layout": layout_details,
            "textAccuracy": text_details,
            "colorAccuracy": color_details,
            "visualSimilarity": visual_details,
            "editability": edit_details,
            "structureF1": struct_details,
            "semantic": semantic_details,
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
        "visualSimilarity", "editability", "structureF1", "semantic",
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
                    r.semantic, r.overall,
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
                     "visualSimilarity", "editability", "structureF1", "semantic"]:
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
