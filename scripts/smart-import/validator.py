"""
SceneGraph validator — validates, repairs, and normalizes SceneGraph JSON.

Validates against scene_schema.json (draft-2020-12), clamps bounding boxes
to canvas bounds, filters layers according to the selected Smart Import V1
mode, normalizes hex colors to lowercase 6-digit format, and attempts structural repair for
common issues (missing fields, wrong types).
"""

from __future__ import annotations

import copy
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import jsonschema
from jsonschema import validate, ValidationError

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parent / "scene_schema.json"
SUPPORTED_MODES = {"text_only", "basic_image_layers"}
BASIC_IMAGE_LAYER_CONFIDENCE_THRESHOLD = 0.5


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Result of SceneGraph validation.

    Attributes:
        valid: True if the fixed scene passes schema validation.
        errors: List of error messages (schema violations that could not be repaired).
        warnings: List of non-critical issues (discarded layers, unknown format, etc.).
        original: Deep copy of the input scene (before any fixes).
        fixed: The scene after all normalization, clamping, and repair attempts.
    """
    valid: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    original: Optional[dict] = None
    fixed: Optional[dict] = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_schema() -> dict:
    """Load the JSON Schema file from disk."""
    try:
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot load schema from {SCHEMA_PATH}: {exc}")


def _normalize_hex_color(color: str) -> str:
    """Normalize a hex color to lowercase 6-digit format.

    Handles ``#RGB``, ``#RRGGBB``, ``#RRGGBBAA``, with or without ``#`` prefix.
    Returns the original string unchanged if it cannot be normalized.
    """
    if not color or not isinstance(color, str):
        return color
    c = color.strip().lstrip("#")
    if not c or len(c) not in (3, 6, 8):
        return color  # not a recognizable hex shortcut
    if not re.match(r"^[0-9a-fA-F]+$", c):
        return color  # invalid hex chars
    if len(c) == 3:
        c = "".join(2 * ch for ch in c)
    if len(c) == 8:
        c = c[:6]  # drop alpha channel
    return f"#{c.lower()}"


CSS_DIRECTION_MAP = {
    "to top": 0, "to right": 90, "to bottom": 180, "to left": 270,
    "to top right": 45, "to top left": 315,
    "to bottom right": 135, "to bottom left": 225,
}

def _normalize_gradient_angle(angle: object) -> float:
    """Normalize gradient angle to float degrees.

    Handles CSS direction keywords (``'to left'``), ``'Xdeg'`` strings,
    plain numeric strings, and numbers.
    """
    if angle is None:
        return 180.0
    if isinstance(angle, (int, float)):
        return float(angle)
    s = str(angle).strip().lower()
    if s in CSS_DIRECTION_MAP:
        return float(CSS_DIRECTION_MAP[s])
    if s.endswith("deg"):
        s = s[:-3]
    try:
        return float(s)
    except (ValueError, TypeError):
        return 180.0


_ALLOWED_BACKGROUND_KEYS = {"kind", "color", "gradient", "confidence"}


def _normalize_scene(scene: dict) -> dict:
    """Deep-normalize all colours, gradient angles, and other values in a scene."""
    fixed = copy.deepcopy(scene)

    # Background — strip unknown keys (e.g. AI sometimes adds 'description')
    bg = fixed.get("background")
    if isinstance(bg, dict):
        for key in list(bg):
            if key not in _ALLOWED_BACKGROUND_KEYS:
                del bg[key]
        if "color" in bg:
            bg["color"] = _normalize_hex_color(bg["color"])
        grad = bg.get("gradient")
        if isinstance(grad, dict):
            if "angle" in grad:
                grad["angle"] = _normalize_gradient_angle(grad["angle"])
            for stop in grad.get("stops", []):
                if isinstance(stop, dict) and "color" in stop:
                    stop["color"] = _normalize_hex_color(stop["color"])

    # Layers
    for layer in fixed.get("layers", []):
        if not isinstance(layer, dict):
            continue
        style = layer.get("style")
        if isinstance(style, dict):
            if "fontSize" in style and isinstance(style["fontSize"], str):
                import re as _re
                _m = _re.match(r"(\d+(?:\.\d+)?)", style["fontSize"])
                if _m:
                    style["fontSize"] = float(_m.group(1))
                else:
                    style["fontSize"] = 24
            if "color" in style:
                style["color"] = _normalize_hex_color(style["color"])
            if "fontWeight" in style and isinstance(style["fontWeight"], (int, float)):
                style["fontWeight"] = str(style["fontWeight"])
            if "fontSize" in style:
                val = style["fontSize"]
                if isinstance(val, str):
                    m = re.match(r"(\d+(?:\.\d+)?)", val)
                    style["fontSize"] = float(m.group(1)) if m else 24
            shadow = style.get("shadow")
            if isinstance(shadow, dict) and "color" in shadow:
                shadow["color"] = _normalize_hex_color(shadow["color"])
        shape_style = layer.get("shapeStyle")
        if isinstance(shape_style, dict) and "fill" in shape_style:
            shape_style["fill"] = _normalize_hex_color(shape_style["fill"])

    return fixed


def _clamp_bbox_to_canvas(scene: dict) -> dict:
    """Clamp bounding-box coordinates so they stay inside canvas bounds.

    Non-negative x/y/w/h are enforced **before** canvas clamping so that
    negative positions are pulled up to 0, then w/h are shrunk if the
    bbox would overflow the canvas edge.
    """
    fixed = copy.deepcopy(scene)
    canvas_w = fixed.get("canvas", {}).get("width", 0) or 0
    canvas_h = fixed.get("canvas", {}).get("height", 0) or 0

    for layer in fixed.get("layers", []):
        if not isinstance(layer, dict):
            continue
        bbox = layer.get("bbox")
        if not isinstance(bbox, dict):
            continue

        # Clamp origin to non-negative
        x = max(0, bbox.get("x", 0))
        y = max(0, bbox.get("y", 0))
        # Clamp dimensions to non-negative
        w = max(0, bbox.get("w", 0))
        h = max(0, bbox.get("h", 0))

        # Shrink if box overflows canvas
        if canvas_w > 0:
            w = min(w, canvas_w - x)
        if canvas_h > 0:
            h = min(h, canvas_h - y)

        # Ensure final dimensions are >= 0 (important when x >= canvas_w)
        bbox["x"] = max(x, 0)
        bbox["y"] = max(y, 0)
        bbox["w"] = max(w, 0)
        bbox["h"] = max(h, 0)

    return fixed


def _discard_low_confidence_layers(scene: dict, threshold: float = 0.3) -> tuple[dict, list[str]]:
    """Remove layers whose confidence is below *threshold*.

    Returns ``(fixed_scene, discarded_layer_ids)``.
    """
    fixed = copy.deepcopy(scene)
    discarded: list[str] = []
    kept: list[dict] = []
    for layer in fixed.get("layers", []):
        if not isinstance(layer, dict):
            discarded.append("(non-dict layer)")
            continue
        conf = layer.get("confidence")
        if conf is None or conf < threshold:
            discarded.append(layer.get("id", "(no-id)"))
        else:
            kept.append(layer)
    fixed["layers"] = kept
    return fixed, discarded


def _filter_layers_for_mode(scene: dict, mode: str) -> tuple[dict, list[str], list[str]]:
    """Apply Smart Import V1 mode filtering.

    Returns ``(fixed_scene, discarded_non_text_ids, discarded_low_conf_ids)``.
    ``text_only`` keeps only text layers. ``basic_image_layers`` keeps any
    layer whose confidence is at least 0.5.
    """
    if mode not in SUPPORTED_MODES:
        raise ValueError(
            f"Unsupported Smart Import mode: {mode}. "
            f"Expected one of: {', '.join(sorted(SUPPORTED_MODES))}"
        )

    fixed = copy.deepcopy(scene)
    discarded_non_text: list[str] = []
    discarded_low_confidence: list[str] = []
    kept: list[dict] = []

    for layer in fixed.get("layers", []):
        if not isinstance(layer, dict):
            discarded_low_confidence.append("(non-dict layer)")
            continue

        layer_id = layer.get("id", "(no-id)")
        kind = layer.get("kind")

        if mode == "text_only" and kind != "text":
            discarded_non_text.append(layer_id)
            continue

        if mode == "basic_image_layers":
            confidence = layer.get("confidence")
            if confidence is None or confidence < BASIC_IMAGE_LAYER_CONFIDENCE_THRESHOLD:
                discarded_low_confidence.append(layer_id)
                continue

        kept.append(layer)

    fixed["layers"] = kept
    return fixed, discarded_non_text, discarded_low_confidence


def _attempt_repair(scene: dict) -> tuple[dict, list[str]]:
    """Try to fix common structural issues in a scene.

    Returns ``(fixed_scene, repair_messages)``.  Repair never raises.
    """
    fixed = copy.deepcopy(scene)
    repairs: list[str] = []

    # --- canvas ---
    if "canvas" not in fixed or not isinstance(fixed.get("canvas"), dict):
        fixed["canvas"] = {"width": 1080, "height": 1350, "detectedFormat": "vertical"}
        repairs.append("Added missing canvas with default 1080×1350 vertical")

    canvas = fixed["canvas"]
    for key, default in (("width", 1080), ("height", 1350)):
        val = canvas.get(key)
        if not isinstance(val, (int, float)):
            canvas[key] = default
            repairs.append(f"Fixed canvas.{key} to {default}")
        else:
            canvas[key] = int(val)

    if "detectedFormat" not in canvas or canvas.get("detectedFormat") not in ("vertical", "horizontal", "square"):
        canvas["detectedFormat"] = "vertical"
        repairs.append("Fixed canvas.detectedFormat to 'vertical'")

    # --- layers ---
    if "layers" not in fixed or not isinstance(fixed.get("layers"), list):
        fixed["layers"] = []
        repairs.append("Added empty layers array")

    for i, layer in enumerate(fixed["layers"]):
        if not isinstance(layer, dict):
            fixed["layers"][i] = {
                "id": f"layer-{i}",
                "kind": "shape",
                "confidence": 0.5,
                "bbox": {"x": 0, "y": 0, "w": 100, "h": 100},
            }
            repairs.append(f"Replaced non-dict layer at index {i}")
            continue

        # id
        if "id" not in layer or not isinstance(layer.get("id"), str):
            layer["id"] = f"layer-{i}"
            repairs.append(f"Fixed missing/invalid id at layer {i}")

        # kind
        if "kind" not in layer or layer.get("kind") not in ("text", "image", "shape"):
            layer["kind"] = "shape"
            repairs.append(f"Fixed missing/invalid kind for {layer['id']}")

        # bbox
        if "bbox" not in layer or not isinstance(layer.get("bbox"), dict):
            layer["bbox"] = {"x": 0, "y": 0, "w": 100, "h": 50}
            repairs.append(f"Added default bbox for {layer['id']}")
        else:
            bbox = layer["bbox"]
            for key in ("x", "y", "w", "h"):
                val = bbox.get(key)
                if not isinstance(val, int):
                    try:
                        bbox[key] = int(val)
                    except (ValueError, TypeError):
                        bbox[key] = 0
                    repairs.append(f"Fixed bbox.{key} type for {layer['id']}")

        # kind-specific requirements: add empty string for optional-but-relevant
        if layer["kind"] == "text" and "text" not in layer:
            layer["text"] = ""
            repairs.append(f"Added empty text for {layer['id']}")
        if layer["kind"] == "image" and "description" not in layer:
            layer["description"] = ""
            repairs.append(f"Added empty description for {layer['id']}")

    return fixed, repairs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_scene(scene: dict, mode: str = "basic_image_layers") -> ValidationResult:
    """Validate a SceneGraph and return a fixed, normalized version.

    The pipeline always:
      1. Validates the original scene against the JSON Schema.
      2. Attempts structural repair (missing fields, wrong types).
      3. Normalises hex colours to lowercase 6-digit form.
      4. Applies mode-aware layer filtering:
         - text_only: discard non-text layers
         - basic_image_layers: discard layers with confidence < 0.5
      5. Clamps bbox coordinates to canvas bounds.
      6. Re-validates the fixed scene.

    Returns a ``ValidationResult`` with both the original and fixed scene.
    """
    if mode not in SUPPORTED_MODES:
        raise ValueError(
            f"Unsupported Smart Import mode: {mode}. "
            f"Expected one of: {', '.join(sorted(SUPPORTED_MODES))}"
        )

    result = ValidationResult(original=copy.deepcopy(scene))
    schema = _load_schema()

    # --- 1. Initial validation ---
    try:
        validate(instance=scene, schema=schema)
        initially_valid = True
    except ValidationError as exc:
        initially_valid = False
        path = " -> ".join(str(p) for p in exc.absolute_path) if exc.absolute_path else "root"
        result.errors.append(f"Schema validation error at {path}: {exc.message}")

    # --- 2. Repair ---
    fixed, repairs = _attempt_repair(scene)
    for msg in repairs:
        logger.debug("Repair: %s", msg)

    # --- 3. Normalize colors, gradient angles, etc. ---
    fixed = _normalize_scene(fixed)

    # --- 4. Apply mode-aware filtering ---
    fixed, discarded_non_text, discarded_low_confidence = _filter_layers_for_mode(
        fixed, mode
    )
    if discarded_non_text:
        result.warnings.append(
            f"Discarded {len(discarded_non_text)} non-text layers for text_only mode: "
            f"{', '.join(discarded_non_text)}"
        )
    if discarded_low_confidence:
        result.warnings.append(
            f"Discarded {len(discarded_low_confidence)} layers below confidence threshold "
            f"{BASIC_IMAGE_LAYER_CONFIDENCE_THRESHOLD}: "
            f"{', '.join(discarded_low_confidence)}"
        )

    # --- 5. Clamp bounding boxes ---
    fixed = _clamp_bbox_to_canvas(fixed)

    # --- 6. Re-validate ---
    try:
        validate(instance=fixed, schema=schema)
        result.valid = True
        if repairs:
            result.warnings.append(f"Applied {len(repairs)} repairs to fix schema issues")
    except ValidationError as exc:
        path = " -> ".join(str(p) for p in exc.absolute_path) if exc.absolute_path else "root"
        result.errors.append(f"After repair, still invalid at {path}: {exc.message}")
        result.valid = False
    except Exception as exc:
        result.errors.append(f"Re-validation error: {exc}")
        result.valid = False

    # --- 7. Structural warnings (non-blocking) ---
    if result.valid and not initially_valid:
        result.warnings.insert(0, "Original scene had schema issues — repairs applied")

    fmt = fixed.get("canvas", {}).get("detectedFormat", "")
    if fmt and fmt not in ("vertical", "horizontal", "square"):
        result.warnings.append(f"Unknown canvas.detectedFormat: {fmt}")

    if len(fixed.get("layers", [])) == 0:
        result.warnings.append("No layers remaining after validation")

    result.fixed = fixed
    return result
