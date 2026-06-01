"""
TC Fidelity Evaluator — measures how faithfully a compiled .tc file
represents the SceneGraph it was compiled from.

Metrics (Level 2 — compilation fidelity)
-----------------------------------------
- ``elementPreservation``: % of SceneGraph elements that exist in the .tc
- ``typeFidelity``: % of element types preserved correctly
- ``textFidelity``: % of text content passed through correctly
- ``positionFidelity``: avg overlap (IoU) of element positions
- ``propertyFidelity``: avg preservation of style/color/font properties
- ``overallScore``: weighted harmonic mean
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate_tc_fidelity(tc: dict | None, scene: dict | None) -> dict:
    """Compare compiled .tc against the source SceneGraph.

    Parameters
    ----------
    tc:
        The compiled .tc dict.  ``None`` if compilation failed.
    scene:
        The validated SceneGraph dict.  ``None`` if analysis failed.

    Returns
    -------
    dict
        Score dict with keys: ``elementPreservation``, ``typeFidelity``,
        ``textFidelity``, ``positionFidelity``, ``propertyFidelity``,
        ``overallScore``, ``detail``.
    """
    if tc is None or scene is None:
        return _empty_result("no-tc-or-scene")

    scene_layers = scene.get("layers", [])
    if not scene_layers:
        return _empty_result("no-scene-layers")

    pages = tc.get("pages", [])
    if not pages:
        return _empty_result("no-tc-pages")

    page = pages[0]
    element_layout = page.get("elementLayout", {}) or {}
    custom_elements = page.get("customElements", {}) or {}

    # Exclude background from element comparison
    tc_elem_ids = set(custom_elements.keys())
    scene_elem_ids = set()

    # Track matched elements
    matched_ids: set[str] = set()
    type_ok = 0
    text_ok = 0
    text_total = 0
    iou_values: list[float] = []
    property_scores: list[float] = []

    # Map scene layers → their IDs
    for layer in scene_layers:
        lid = layer.get("id", "")
        if lid:
            scene_elem_ids.add(lid)

    # --- Element preservation ---
    for layer in scene_layers:
        lid = layer.get("id", "")
        if lid in tc_elem_ids:
            matched_ids.add(lid)
            scene_kind = layer.get("kind", "")
            tc_type = custom_elements.get(lid, {}).get("type", "")

            # Type mapping: scene kind → tc type
            expected_tc_type = _scene_kind_to_tc_type(scene_kind)
            if tc_type == expected_tc_type:
                type_ok += 1

            # Text fidelity
            if scene_kind == "text":
                text_total += 1
                scene_text = layer.get("text", "")
                tc_text = custom_elements.get(lid, {}).get("text", "")
                if scene_text.strip().lower() == tc_text.strip().lower():
                    text_ok += 1

            # Position fidelity (IoU)
            scene_bbox = layer.get("bbox") or {}
            tc_layout = element_layout.get(lid, {}) or {}
            iou = _bbox_iou(scene_bbox, tc_layout)
            if iou is not None:
                iou_values.append(iou)

            # Property fidelity (color, font size, etc.)
            prop_score = _property_score(layer, custom_elements.get(lid, {}))
            property_scores.append(prop_score)

    # --- Compute scores ---
    elem_preservation = len(matched_ids) / max(len(scene_layers), 1)
    type_fidelity = type_ok / max(len(matched_ids), 1)
    text_fidelity = text_ok / max(text_total, 1)
    position_fidelity = (sum(iou_values) / max(len(iou_values), 1)) if iou_values else 0.0
    property_fidelity = (sum(property_scores) / max(len(property_scores), 1)) if property_scores else 0.0

    overall = (
        0.25 * elem_preservation +
        0.20 * type_fidelity +
        0.20 * text_fidelity +
        0.15 * position_fidelity +
        0.20 * property_fidelity
    )

    return {
        "elementPreservation": round(elem_preservation, 4),
        "typeFidelity": round(type_fidelity, 4),
        "textFidelity": round(text_fidelity, 4),
        "positionFidelity": round(position_fidelity, 4),
        "propertyFidelity": round(property_fidelity, 4),
        "overallScore": round(overall, 4),
        "detail": {
            "sceneLayerCount": len(scene_layers),
            "tcElementCount": len(tc_elem_ids),
            "matchedCount": len(matched_ids),
            "typeMatches": type_ok,
            "textMatches": text_ok,
            "textTotal": text_total,
            "avgIoU": round(sum(iou_values) / max(len(iou_values), 1), 4) if iou_values else 0.0,
            "avgPropertyScore": round(sum(property_scores) / max(len(property_scores), 1), 4) if property_scores else 0.0,
        },
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _scene_kind_to_tc_type(kind: str) -> str:
    mapping = {
        "text": "text",
        "image": "image",
        "shape": "shape",
        "background": "background",
    }
    return mapping.get(kind, "unknown")


def _bbox_iou(
    scene_bbox: dict,
    tc_layout: dict,
) -> float | None:
    """Compute IoU between a SceneGraph bbox and a .tc layout entry."""
    sx = scene_bbox.get("x")
    sy = scene_bbox.get("y")
    sw = scene_bbox.get("w")
    sh = scene_bbox.get("h")

    tx = tc_layout.get("x")
    ty = tc_layout.get("y")
    tw = tc_layout.get("w")
    th = tc_layout.get("h")

    if any(v is None for v in (sx, sy, sw, sh, tx, ty, tw, th)):
        return None

    sx1, sy1, sx2, sy2 = float(sx), float(sy), float(sx + sw), float(sy + sh)
    tx1, ty1, tx2, ty2 = float(tx), float(ty), float(tx + tw), float(ty + th)

    xi1 = max(sx1, tx1)
    yi1 = max(sy1, ty1)
    xi2 = min(sx2, tx2)
    yi2 = min(sy2, ty2)

    inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
    area_s = max(0, sx2 - sx1) * max(0, sy2 - sy1)
    area_t = max(0, tx2 - tx1) * max(0, ty2 - ty1)
    union = area_s + area_t - inter

    return inter / max(union, 1) if union > 0 else 0.0


def _property_score(scene_layer: dict, tc_element: dict) -> float:
    """Score how well the .tc element preserves SceneGraph properties.

    Checks colour, font size, font weight, text alignment.
    Returns a normalised score in [0, 1].
    """
    scene_style = scene_layer.get("style") or {}
    signals = 0
    matches = 0

    # Color
    scene_color = scene_style.get("color") or scene_layer.get("color", "")
    tc_color = tc_element.get("color", "")
    if scene_color and tc_color:
        signals += 1
        if scene_color.strip().lower() == tc_color.strip().lower():
            matches += 1

    # Font size
    scene_fs = scene_style.get("fontSize") or scene_layer.get("fontSize", 0)
    tc_fs = tc_element.get("fontSize", 0) or 0
    if scene_fs and tc_fs:
        signals += 1
        ratio = min(float(scene_fs), float(tc_fs)) / max(float(scene_fs), float(tc_fs), 1)
        matches += ratio

    # Font weight
    scene_fw = scene_style.get("fontWeight", "")
    tc_fw = tc_element.get("fontWeight", "")
    if scene_fw and tc_fw:
        signals += 1
        if _fw_match(scene_fw, tc_fw):
            matches += 1

    # Text alignment
    scene_align = scene_style.get("textAlign", "")
    tc_align = tc_element.get("textAlign", "")
    if scene_align and tc_align:
        signals += 1
        if scene_align == tc_align:
            matches += 1

    if signals == 0:
        return 1.0  # no properties to compare
    return matches / signals


def _fw_match(a: str, b: str) -> bool:
    """Normalise font-weight strings before comparing."""
    mapping = {"bold": "bold", "700": "bold", "normal": "normal", "400": "normal"}
    a_norm = mapping.get(a.strip().lower(), a.strip().lower())
    b_norm = mapping.get(b.strip().lower(), b.strip().lower())
    return a_norm == b_norm


def _empty_result(reason: str) -> dict:
    return {
        "elementPreservation": 0.0,
        "typeFidelity": 0.0,
        "textFidelity": 0.0,
        "positionFidelity": 0.0,
        "propertyFidelity": 0.0,
        "overallScore": 0.0,
        "detail": {"reason": reason},
    }
