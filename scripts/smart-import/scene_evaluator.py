"""
SceneGraph Evaluator — compares a model-extracted SceneGraph against a
ground-truth reference and produces objective metrics.

Metrics (Level 1 — SceneGraph quality)
---------------------------------------
- ``elementPrecision``: % of detected elements that match a ground-truth element
- ``elementRecall``: % of ground-truth elements that were detected
- ``textAccuracy``: % of text elements whose content matches exactly
- ``typeAccuracy``: % of elements classified with the correct kind (text/image/shape)
- ``layoutScore``: overlap / proximity similarity between matched elements
- ``overallScore``: weighted harmonic mean of the above
"""

from __future__ import annotations

import logging

from ground_truths import get_ground_truth

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate_scene_graph(
    extracted: dict | None,
    image_id: str,
) -> dict:
    """Compare extracted SceneGraph against ground truth for *image_id*.

    Parameters
    ----------
    extracted:
        The model-extracted SceneGraph dict (or ``None`` if analysis failed).
    image_id:
        Image stem or filename used to look up the ground truth.

    Returns
    -------
    dict
        Score dict with keys: ``elementPrecision``, ``elementRecall``,
        ``f1Score``, ``textAccuracy``, ``typeAccuracy``,
        ``layoutScore``, ``overallScore``, ``detail``.
    """
    gt = get_ground_truth(image_id)
    if gt is None:
        logger.warning("No ground truth found for '%s' — skipping evaluation", image_id)
        return _empty_result("no-ground-truth")

    if extracted is None or not extracted.get("layers"):
        return _empty_result("no-extracted-layers")

    extracted_layers = _normalize_layers(extracted.get("layers", []))
    gt_layers = gt.get("layers", [])

    # --- Element detection (precision / recall / F1) ---
    matched_gt: set[int] = set()
    matched_extracted: set[int] = set()
    text_matches = 0
    text_total = 0
    type_matches = 0
    layout_distances: list[float] = []

    for ei, el in enumerate(extracted_layers):
        best_gi, best_dist = _find_best_match(el, gt_layers, matched_gt)

        if best_gi is not None:
            matched_gt.add(best_gi)
            matched_extracted.add(ei)

            # Text accuracy
            if el.get("kind") == "text" and gt_layers[best_gi].get("kind") == "text":
                text_total += 1
                if _texts_match(el.get("text", ""), gt_layers[best_gi].get("text", "")):
                    text_matches += 1

            # Type accuracy
            if el.get("kind") == gt_layers[best_gi].get("kind"):
                type_matches += 1

            # Layout proximity
            dist = _position_distance(el.get("position", {}), gt_layers[best_gi].get("position", {})) or 0.0
            layout_distances.append(dist)

    precision = len(matched_extracted) / max(len(extracted_layers), 1)
    recall = len(matched_gt) / max(len(gt_layers), 1)
    f1 = (2 * precision * recall / (precision + recall + 1e-10)
          if (precision + recall) > 0 else 0.0)
    text_acc = text_matches / max(text_total, 1)
    type_acc = type_matches / max(len(matched_extracted), 1)
    layout_score = 1.0 - (sum(layout_distances) / max(len(layout_distances), 1)) if layout_distances else 0.0

    # Overall: weighted harmonic-ish mean
    overall = (
        0.25 * f1 +
        0.20 * text_acc +
        0.15 * type_acc +
        0.15 * layout_score +
        0.25 * _count_accuracy(extracted_layers, gt_layers)
    )

    return {
        "elementPrecision": round(precision, 4),
        "elementRecall": round(recall, 4),
        "f1Score": round(f1, 4),
        "textAccuracy": round(text_acc, 4),
        "typeAccuracy": round(type_acc, 4),
        "layoutScore": round(layout_score, 4),
        "overallScore": round(overall, 4),
        "detail": {
            "extractedCount": len(extracted_layers),
            "groundTruthCount": len(gt_layers),
            "matchedCount": len(matched_gt),
            "textMatches": text_matches,
            "textTotal": text_total,
            "typeMatches": type_matches,
            "layoutDistances": [round(d, 4) for d in layout_distances],
        },
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_layers(layers: list[dict]) -> list[dict]:
    """Ensure all layers have the fields we need."""
    out = []
    for lyr in layers:
        out.append({
            "id": lyr.get("id", ""),
            "kind": lyr.get("kind", "unknown"),
            "type": lyr.get("type", ""),
            "text": lyr.get("text", ""),
            "position": lyr.get("position", {}),
            "color": lyr.get("color", "#000000"),
            "font_size": lyr.get("font_size"),
            "opacity": lyr.get("opacity", 1.0),
            "z_index": lyr.get("z_index", 0),
            "bold": lyr.get("bold", False),
            "alignment": lyr.get("alignment", "left"),
        })
    return out


def _find_best_match(
    extracted: dict,
    gt_layers: list[dict],
    already_matched: set[int],
) -> tuple[int | None, float]:
    """Find the best ground-truth match for an extracted element.

    Scoring considers: kind match, text match, position proximity.
    Returns ``(gt_index, distance)`` or ``(None, inf)``.
    """
    best_idx: int | None = None
    best_dist = float("inf")

    for gi, gt in enumerate(gt_layers):
        if gi in already_matched:
            continue
        dist = _element_distance(extracted, gt)
        if dist < best_dist:
            best_dist = dist
            best_idx = gi

    # Threshold: if distance > 0.6, consider it unmatched
    if best_dist > 0.6:
        return None, best_dist
    return best_idx, best_dist


def _element_distance(a: dict, b: dict) -> float:
    """Compute a normalised distance (0 = perfect, 1 = unrelated) between two
    element descriptions.  Uses type, text, position, and colour signals."""
    dist = 0.0
    signals = 0

    # Kind mismatch → heavy penalty
    if a.get("kind") != b.get("kind"):
        if a.get("kind") == "unknown" or b.get("kind") == "unknown":
            dist += 0.3
        else:
            dist += 0.6
    else:
        dist += 0.0
    signals += 1

    # Text match
    a_text = a.get("text", "").strip()
    b_text = b.get("text", "").strip()
    if a_text and b_text:
        if a_text == b_text:
            dist += 0.0
        elif a_text.lower() == b_text.lower():
            dist += 0.2
        elif len(set(a_text.split()) & set(b_text.split())) > 0:
            dist += 0.4
        else:
            dist += 0.7
        signals += 1

    # Position proximity (using bounding box overlap if available)
    pos_dist = _position_distance(a.get("position", {}), b.get("position", {}))
    if pos_dist is not None:
        dist += pos_dist
        signals += 1

    # Colour similarity
    col_dist = _color_distance(a.get("color", "#000000"), b.get("color", "#000000"))
    if col_dist is not None:
        dist += col_dist
        signals += 1

    return dist / max(signals, 1)


def _position_distance(a_pos: dict, b_pos: dict) -> float | None:
    """Normalised position distance using available position info."""
    # Try bbox intersection over union
    a_bbox = _resolve_bbox(a_pos)
    b_bbox = _resolve_bbox(b_pos)
    if a_bbox and b_bbox:
        return 1.0 - _iou(a_bbox, b_bbox)
    # Fallback: compare centre-point percentages
    def _to_float(v, default=0.0):
        if v is None:
            return default
        try:
            return float(v)
        except (ValueError, TypeError):
            return default
    a_cx = _to_float(a_pos.get("cx")) or _to_float(a_pos.get("x")) + (_to_float(a_pos.get("width")) / 2)
    a_cy = _to_float(a_pos.get("cy")) or _to_float(a_pos.get("y")) + (_to_float(a_pos.get("height")) / 2)
    b_cx = _to_float(b_pos.get("cx")) or _to_float(b_pos.get("x")) + (_to_float(b_pos.get("width")) / 2)
    b_cy = _to_float(b_pos.get("cy")) or _to_float(b_pos.get("y")) + (_to_float(b_pos.get("height")) / 2)
    if a_cx and a_cy and b_cx and b_cy:
        dx = abs(float(a_cx) - float(b_cx)) / 2000.0  # rough normalisation
        dy = abs(float(a_cy) - float(b_cy)) / 2000.0
        return min(1.0, dx + dy)
    if a_pos.get("y_pct") and b_pos.get("y_pct"):
        return min(1.0, abs(float(a_pos["y_pct"]) - float(b_pos["y_pct"])) * 2)
    return None


def _resolve_bbox(pos: dict) -> tuple[float, float, float, float] | None:
    """Try to extract (x1, y1, x2, y2) from a position dict."""
    x, y, w, h = pos.get("x"), pos.get("y"), pos.get("width"), pos.get("height")
    if all(v is not None for v in (x, y, w, h)):
        try:
            return (float(x), float(y), float(x) + float(w), float(y) + float(h))
        except (ValueError, TypeError):
            pass
    cx, cy, radius = pos.get("cx"), pos.get("cy"), pos.get("radius")
    if all(v is not None for v in (cx, cy, radius)):
        r = float(radius)
        return (float(cx) - r, float(cy) - r, float(cx) + r, float(cy) + r)
    return None


def _iou(a, b):
    """Intersection over union of two bounding boxes (x1,y1,x2,y2)."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    xi1 = max(ax1, bx1)
    yi1 = max(ay1, by1)
    xi2 = min(ax2, bx2)
    yi2 = min(ay2, by2)
    inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    union = area_a + area_b - inter
    return inter / max(union, 1)


def _color_distance(a: str, b: str) -> float | None:
    """Normalised RGB distance between two hex colours."""
    try:
        a = a.lstrip("#")
        b = b.lstrip("#")
        if len(a) >= 6 and len(b) >= 6:
            ar, ag, ab = int(a[:2], 16), int(a[2:4], 16), int(a[4:6], 16)
            br, bg, bb = int(b[:2], 16), int(b[2:4], 16), int(b[4:6], 16)
            dr, dg, db = ar - br, ag - bg, ab - bb
            dist = (dr ** 2 + dg ** 2 + db ** 2) ** 0.5
            return min(1.0, dist / 441.67)  # 441.67 = sqrt(255^2*3)
    except (ValueError, IndexError):
        pass
    return None


def _texts_match(a: str, b: str) -> bool:
    return a.strip().lower() == b.strip().lower()


def _count_accuracy(extracted: list[dict], gt: list[dict]) -> float:
    """Score based on how well element type counts match."""
    def _counts(layers):
        counts = {"text": 0, "image": 0, "shape": 0}
        for lyr in layers:
            k = lyr.get("kind", "unknown")
            if k in counts:
                counts[k] += 1
            else:
                counts[k] = 1
        return counts

    ec = _counts(extracted)
    gc = _counts(gt)
    all_keys = set(ec) | set(gc)
    diffs = sum(abs(ec.get(k, 0) - gc.get(k, 0)) for k in all_keys)
    total = sum(gc.values())
    return 1.0 - (diffs / max(total * 2, 1))


def _empty_result(reason: str) -> dict:
    return {
        "elementPrecision": 0.0,
        "elementRecall": 0.0,
        "f1Score": 0.0,
        "textAccuracy": 0.0,
        "typeAccuracy": 0.0,
        "layoutScore": 0.0,
        "overallScore": 0.0,
        "detail": {"reason": reason},
    }
