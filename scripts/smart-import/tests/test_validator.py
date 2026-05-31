"""
Unit tests for the SceneGraph validator.

Tests schema validation, bbox clamping, low-confidence layer discarding,
hex colour normalisation, structural repair, and edge cases.
"""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure parent directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from validator import (
    ValidationResult,
    validate_scene,
    _normalize_hex_color,
    _clamp_bbox_to_canvas,
    _discard_low_confidence_layers,
    _attempt_repair,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_VALID_SCENE = {
    "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
    "layers": [
        {
            "id": "layer-1",
            "kind": "text",
            "confidence": 0.92,
            "bbox": {"x": 50, "y": 100, "w": 400, "h": 60},
            "text": "Hello World",
        },
        {
            "id": "layer-2",
            "kind": "image",
            "confidence": 0.50,
            "bbox": {"x": 0, "y": 0, "w": 1080, "h": 800},
            "description": "A mountain landscape",
            "cropFromSource": True,
        },
        {
            "id": "layer-3",
            "kind": "shape",
            "confidence": 0.40,
            "bbox": {"x": 100, "y": 200, "w": 300, "h": 150},
            "shape": "rectangle",
            "shapeStyle": {"fill": "#FF0000", "opacity": 0.5, "borderRadius": 8},
        },
    ],
    "warnings": ["Test warning"],
    "usage": {"promptTokens": 100, "completionTokens": 20, "costUsd": 0.001},
}

_SAMPLE_LOW_CONF = {
    "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
    "layers": [
        {
            "id": "layer-1",
            "kind": "text",
            "confidence": 0.95,
            "bbox": {"x": 0, "y": 0, "w": 100, "h": 50},
            "text": "Keep me",
        },
        {
            "id": "layer-2",
            "kind": "text",
            "confidence": 0.15,
            "bbox": {"x": 0, "y": 0, "w": 50, "h": 50},
            "text": "Discard me",
        },
        {
            "id": "layer-3",
            "kind": "text",
            "confidence": 0.3,
            "bbox": {"x": 0, "y": 0, "w": 50, "h": 50},
            "text": "Borderline",
        },
    ],
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestNormalizeHexColor(unittest.TestCase):
    """``_normalize_hex_color`` unit tests."""

    def test_lowercase_already(self):
        self.assertEqual(_normalize_hex_color("#ffffff"), "#ffffff")

    def test_uppercase_to_lowercase(self):
        self.assertEqual(_normalize_hex_color("#FFFFFF"), "#ffffff")

    def test_shorthand_3_digit(self):
        self.assertEqual(_normalize_hex_color("#F00"), "#ff0000")

    def test_shorthand_lowercase(self):
        self.assertEqual(_normalize_hex_color("#abc"), "#aabbcc")

    def test_without_hash_prefix(self):
        self.assertEqual(_normalize_hex_color("FF0000"), "#ff0000")

    def test_empty_string(self):
        self.assertEqual(_normalize_hex_color(""), "")

    def test_none_returns_none(self):
        self.assertIsNone(_normalize_hex_color(None))

    def test_invalid_hex_string(self):
        # Should return as-is if it can't normalize
        self.assertEqual(_normalize_hex_color("#ZZZ"), "#ZZZ")

    def test_invalid_length(self):
        self.assertEqual(_normalize_hex_color("#FFFF"), "#FFFF")


class TestClampBbox(unittest.TestCase):
    """``_clamp_bbox_to_canvas`` unit tests."""

    def test_bbox_within_canvas(self):
        scene = {
            "canvas": {"width": 1080, "height": 1350},
            "layers": [{"bbox": {"x": 100, "y": 100, "w": 500, "h": 300}}],
        }
        fixed = _clamp_bbox_to_canvas(scene)
        bbox = fixed["layers"][0]["bbox"]
        self.assertEqual(bbox, {"x": 100, "y": 100, "w": 500, "h": 300})

    def test_negative_coordinates_clamped(self):
        scene = {
            "canvas": {"width": 1080, "height": 1350},
            "layers": [{"bbox": {"x": -50, "y": -20, "w": 100, "h": 80}}],
        }
        fixed = _clamp_bbox_to_canvas(scene)
        bbox = fixed["layers"][0]["bbox"]
        self.assertEqual(bbox["x"], 0)
        self.assertEqual(bbox["y"], 0)

    def test_bbox_overflowing_canvas_clamped(self):
        scene = {
            "canvas": {"width": 1080, "height": 1350},
            "layers": [{"bbox": {"x": 1000, "y": 1300, "w": 200, "h": 200}}],
        }
        fixed = _clamp_bbox_to_canvas(scene)
        bbox = fixed["layers"][0]["bbox"]
        # w should be clamped to canvas_w - x = 1080 - 1000 = 80
        self.assertEqual(bbox["w"], 80)
        # h should be clamped to canvas_h - y = 1350 - 1300 = 50
        self.assertEqual(bbox["h"], 50)

    def test_zero_dimensions_bbox(self):
        scene = {
            "canvas": {"width": 1080, "height": 1350},
            "layers": [{"bbox": {"x": 0, "y": 0, "w": 0, "h": 0}}],
        }
        fixed = _clamp_bbox_to_canvas(scene)
        bbox = fixed["layers"][0]["bbox"]
        self.assertEqual(bbox, {"x": 0, "y": 0, "w": 0, "h": 0})

    def test_bbox_x_beyond_canvas_gets_zero_w(self):
        scene = {
            "canvas": {"width": 1080, "height": 1350},
            "layers": [{"bbox": {"x": 2000, "y": 100, "w": 100, "h": 100}}],
        }
        fixed = _clamp_bbox_to_canvas(scene)
        bbox = fixed["layers"][0]["bbox"]
        self.assertEqual(bbox["w"], 0)

    def test_missing_bbox_keys_default_to_zero(self):
        scene = {
            "canvas": {"width": 1080, "height": 1350},
            "layers": [{"bbox": {"x": 10, "y": 20}}],
        }
        fixed = _clamp_bbox_to_canvas(scene)
        bbox = fixed["layers"][0]["bbox"]
        self.assertEqual(bbox["x"], 10)
        self.assertEqual(bbox["y"], 20)
        self.assertEqual(bbox["w"], 0)
        self.assertEqual(bbox["h"], 0)


class TestDiscardLowConfidence(unittest.TestCase):
    """``_discard_low_confidence_layers`` unit tests."""

    def test_discards_low_confidence(self):
        fixed, discarded = _discard_low_confidence_layers(copy.deepcopy(_SAMPLE_LOW_CONF))
        layer_ids = [l["id"] for l in fixed["layers"]]
        self.assertIn("layer-1", layer_ids)
        self.assertNotIn("layer-2", layer_ids)
        self.assertIn("layer-3", layer_ids)  # exactly 0.3, should be kept
        self.assertIn("layer-2", discarded)

    def test_threshold_at_exact_boundary(self):
        """Confidence exactly at threshold (0.3) should be kept."""
        fixed, discarded = _discard_low_confidence_layers(
            copy.deepcopy(_SAMPLE_LOW_CONF), threshold=0.3
        )
        layer_ids = [l["id"] for l in fixed["layers"]]
        self.assertIn("layer-3", layer_ids)
        self.assertNotIn("layer-2", layer_ids)

    def test_all_high_confidence_kept(self):
        scene = {
            "canvas": {"width": 100, "height": 100},
            "layers": [
                {"id": "a", "confidence": 0.9, "bbox": {"x": 0, "y": 0, "w": 10, "h": 10}},
                {"id": "b", "confidence": 1.0, "bbox": {"x": 0, "y": 0, "w": 10, "h": 10}},
            ],
        }
        fixed, discarded = _discard_low_confidence_layers(scene)
        self.assertEqual(len(fixed["layers"]), 2)
        self.assertEqual(len(discarded), 0)

    def test_empty_layers(self):
        scene = {"layers": []}
        fixed, discarded = _discard_low_confidence_layers(scene)
        self.assertEqual(len(fixed["layers"]), 0)
        self.assertEqual(len(discarded), 0)

    def test_handles_non_dict_layers(self):
        scene = {"layers": [None, "string", 123]}
        fixed, discarded = _discard_low_confidence_layers(scene)
        self.assertEqual(len(fixed["layers"]), 0)
        self.assertEqual(len(discarded), 3)


class TestAttemptRepair(unittest.TestCase):
    """``_attempt_repair`` unit tests."""

    def test_missing_canvas_added(self):
        fixed, repairs = _attempt_repair({"layers": []})
        self.assertIn("canvas", fixed)
        self.assertEqual(fixed["canvas"]["width"], 1080)
        self.assertEqual(fixed["canvas"]["height"], 1350)
        self.assertTrue(any("canvas" in r.lower() for r in repairs))

    def test_missing_layers_array(self):
        fixed, repairs = _attempt_repair({"canvas": {"width": 100, "height": 100, "detectedFormat": "vertical"}})
        self.assertEqual(fixed["layers"], [])
        self.assertTrue(any("layers" in r.lower() for r in repairs))

    def test_non_dict_layer_replaced(self):
        fixed, repairs = _attempt_repair({
            "canvas": {"width": 100, "height": 100, "detectedFormat": "vertical"},
            "layers": ["bad"],
        })
        self.assertEqual(len(fixed["layers"]), 1)
        self.assertIsInstance(fixed["layers"][0], dict)
        self.assertEqual(fixed["layers"][0]["id"], "layer-0")
        self.assertEqual(fixed["layers"][0]["kind"], "shape")

    def test_missing_layer_id_fixed(self):
        fixed, repairs = _attempt_repair({
            "canvas": {"width": 100, "height": 100, "detectedFormat": "vertical"},
            "layers": [{"kind": "text", "confidence": 0.9, "bbox": {"x": 0, "y": 0, "w": 10, "h": 10}}],
        })
        self.assertEqual(fixed["layers"][0]["id"], "layer-0")

    def test_missing_bbox_added(self):
        fixed, repairs = _attempt_repair({
            "canvas": {"width": 100, "height": 100, "detectedFormat": "vertical"},
            "layers": [{"id": "layer-1", "kind": "text", "confidence": 0.9}],
        })
        self.assertIn("bbox", fixed["layers"][0])
        self.assertEqual(fixed["layers"][0]["bbox"]["x"], 0)

    def test_invalid_bbox_type_fixed(self):
        fixed, repairs = _attempt_repair({
            "canvas": {"width": 100, "height": 100, "detectedFormat": "vertical"},
            "layers": [{"id": "l1", "kind": "text", "confidence": 0.9, "bbox": {"x": "abc", "y": 10, "w": 50, "h": 30}}],
        })
        self.assertEqual(fixed["layers"][0]["bbox"]["x"], 0)

    def test_missing_kind_defaults_to_shape(self):
        fixed, repairs = _attempt_repair({
            "canvas": {"width": 100, "height": 100, "detectedFormat": "vertical"},
            "layers": [{"id": "l1", "confidence": 0.9, "bbox": {"x": 0, "y": 0, "w": 10, "h": 10}}],
        })
        self.assertEqual(fixed["layers"][0]["kind"], "shape")

    def test_canvas_integer_coercion(self):
        fixed, repairs = _attempt_repair({
            "canvas": {"width": 1080.5, "height": "1350", "detectedFormat": "vertical"},
            "layers": [],
        })
        self.assertEqual(fixed["canvas"]["width"], 1080)
        self.assertEqual(fixed["canvas"]["height"], 1350)


class TestValidateSceneIntegration(unittest.TestCase):
    """Integration tests for ``validate_scene``."""

    def test_valid_scene(self):
        result = validate_scene(copy.deepcopy(_VALID_SCENE))
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)
        self.assertIsNotNone(result.fixed)
        self.assertIsNotNone(result.original)

    def test_invalid_scene_rejected(self):
        scene = {"bad": "data"}
        result = validate_scene(scene)
        self.assertFalse(result.valid)
        self.assertGreater(len(result.errors), 0)

    def test_low_confidence_discarded(self):
        scene = copy.deepcopy(_SAMPLE_LOW_CONF)
        result = validate_scene(scene)
        self.assertTrue(result.valid)
        # Default mode is basic_image_layers, which discards confidence < 0.5.
        self.assertEqual(len(result.fixed["layers"]), 1)  # discarded 2 of 3
        self.assertTrue(
            any("confidence" in w.lower() for w in result.warnings),
            f"Expected 'confidence' in warnings, got: {result.warnings}",
        )

    def test_colors_normalized(self):
        scene = {
            "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
            "layers": [
                {
                    "id": "layer-1",
                    "kind": "text",
                    "confidence": 0.9,
                    "bbox": {"x": 0, "y": 0, "w": 100, "h": 50},
                    "text": "Test",
                    "style": {"color": "#FFAABB"},
                },
                {
                    "id": "layer-2",
                    "kind": "shape",
                    "confidence": 0.9,
                    "bbox": {"x": 0, "y": 0, "w": 100, "h": 50},
                    "shape": "rectangle",
                    "shapeStyle": {"fill": "#ABC"},
                },
            ],
        }
        result = validate_scene(scene)
        self.assertTrue(result.valid)
        # Check color normalization
        self.assertEqual(result.fixed["layers"][0]["style"]["color"], "#ffaabb")
        self.assertEqual(result.fixed["layers"][1]["shapeStyle"]["fill"], "#aabbcc")

    def test_background_color_normalized(self):
        scene = {
            "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
            "layers": [],
            "background": {
                "kind": "solid",
                "color": "#FFF000",
                "confidence": 0.9,
            },
        }
        result = validate_scene(scene)
        self.assertTrue(result.valid)
        self.assertEqual(result.fixed["background"]["color"], "#fff000")

    def test_bbox_clamped(self):
        scene = {
            "canvas": {"width": 500, "height": 500, "detectedFormat": "square"},
            "layers": [
                {
                    "id": "layer-1",
                    "kind": "text",
                    "confidence": 0.9,
                    "bbox": {"x": 400, "y": 400, "w": 200, "h": 200},
                    "text": "Overflowing",
                },
            ],
        }
        result = validate_scene(scene)
        self.assertTrue(result.valid)
        bbox = result.fixed["layers"][0]["bbox"]
        self.assertLessEqual(bbox["x"] + bbox["w"], 500)
        self.assertLessEqual(bbox["y"] + bbox["h"], 500)

    def test_empty_scene_repaired(self):
        result = validate_scene({})
        # Should attempt repair and end up with canvas + empty layers
        self.assertIn("canvas", result.fixed)
        self.assertIn("layers", result.fixed)

    def test_original_preserved(self):
        scene = copy.deepcopy(_VALID_SCENE)
        result = validate_scene(scene)
        self.assertEqual(result.original, _VALID_SCENE)
        # Modify result — original should be unchanged
        result.fixed["layers"].append({"extra": True})
        self.assertEqual(len(result.original["layers"]), 3)

    def test_missing_detected_format_gets_repaired(self):
        scene = {
            "canvas": {"width": 1080, "height": 1350, "detectedFormat": "unknown"},
            "layers": [],
        }
        result = validate_scene(scene)
        self.assertTrue(result.valid)
        self.assertEqual(result.fixed["canvas"]["detectedFormat"], "vertical")

    def test_no_layers_remaining_warning(self):
        scene = {
            "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
            "layers": [
                {"id": "l1", "kind": "text", "confidence": 0.1, "bbox": {"x": 0, "y": 0, "w": 10, "h": 10}, "text": "x"},
            ],
        }
        result = validate_scene(scene)
        self.assertTrue(result.valid)  # repaired structure is valid
        # The layer was discarded due to low confidence, so layers is empty
        self.assertEqual(len(result.fixed["layers"]), 0)
        # There should be a warning about no layers remaining
        self.assertTrue(
            any("no layers" in w.lower() for w in result.warnings),
            f"Expected 'no layers remaining' warning, got: {result.warnings}",
        )


class TestValidateSceneModes(unittest.TestCase):
    """Mode-aware filtering required by Smart Import V1."""

    def test_text_only_mode_discards_non_text_layers(self):
        result = validate_scene(copy.deepcopy(_VALID_SCENE), mode="text_only")
        self.assertTrue(result.valid)

        layer_ids = [layer["id"] for layer in result.fixed["layers"]]
        self.assertEqual(layer_ids, ["layer-1"])
        self.assertTrue(
            any("text_only" in warning for warning in result.warnings),
            f"Expected text_only warning, got: {result.warnings}",
        )

    def test_basic_image_layers_discards_layers_below_05_confidence(self):
        result = validate_scene(copy.deepcopy(_VALID_SCENE), mode="basic_image_layers")
        self.assertTrue(result.valid)

        layer_ids = [layer["id"] for layer in result.fixed["layers"]]
        self.assertEqual(layer_ids, ["layer-1", "layer-2"])
        self.assertNotIn("layer-3", layer_ids)

    def test_invalid_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_scene(copy.deepcopy(_VALID_SCENE), mode="advanced_restoration")


if __name__ == "__main__":
    unittest.main()
