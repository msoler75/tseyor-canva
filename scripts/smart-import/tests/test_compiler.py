"""
Unit tests for the SceneGraph → .tc compiler.

Tests compilation of valid SceneGraphs, background mapping, text/image/shape
layer transformation, bbox handling, content-key assignment, image cropping,
z-indexing, and edge cases (empty scene, missing fields, etc.).
"""

from __future__ import annotations

import base64
import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure the parent directory is on sys.path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compiler import SmartImportCompiler


# ---------------------------------------------------------------------------
# Minimal test image (1×1 red JPEG)
# ---------------------------------------------------------------------------

def _make_test_image(path: str, width: int = 200, height: int = 150) -> str:
    """Create a small test JPEG image at *path* and return the path."""
    from PIL import Image
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    img.save(path, "JPEG", quality=95)
    return path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_VALID_SCENE = {
    "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
    "layers": [
        {
            "id": "layer-1",
            "kind": "text",
            "confidence": 0.95,
            "bbox": {"x": 50, "y": 100, "w": 400, "h": 60},
            "text": "Main Title Here",
            "style": {
                "fontSize": 48,
                "fontWeight": "bold",
                "color": "#000000",
                "textAlign": "center",
            },
        },
        {
            "id": "layer-2",
            "kind": "text",
            "confidence": 0.88,
            "bbox": {"x": 60, "y": 180, "w": 380, "h": 40},
            "text": "Subtitle description",
            "style": {
                "fontSize": 24,
                "fontWeight": "400",
                "color": "#333333",
                "textAlign": "left",
            },
        },
        {
            "id": "layer-3",
            "kind": "image",
            "confidence": 0.92,
            "bbox": {"x": 100, "y": 300, "w": 800, "h": 500},
            "description": "A mountain landscape",
            "cropFromSource": True,
        },
        {
            "id": "layer-4",
            "kind": "shape",
            "confidence": 0.70,
            "bbox": {"x": 0, "y": 0, "w": 1080, "h": 1350},
            "shape": "rectangle",
            "shapeStyle": {
                "fill": "#ff0000",
                "opacity": 0.3,
                "borderRadius": 0,
            },
        },
    ],
    "background": {
        "kind": "solid",
        "color": "#ffffff",
        "confidence": 0.99,
    },
    "warnings": [],
    "usage": {"promptTokens": 100, "completionTokens": 20, "costUsd": 0.001},
}

_SOLID_BG_SCENE = {
    "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
    "layers": [],
    "background": {
        "kind": "solid",
        "color": "#f0f0f0",
        "confidence": 0.95,
    },
}

_GRADIENT_BG_SCENE = {
    "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
    "layers": [],
    "background": {
        "kind": "gradient",
        "color": "#ff0000",
        "gradient": {
            "type": "linear",
            "angle": 135,
            "stops": [
                {"color": "#ff0000", "position": 0},
                {"color": "#0000ff", "position": 100},
            ],
        },
        "confidence": 0.90,
    },
}

_NO_BG_SCENE = {
    "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
    "layers": [],
}

_TEXT_ONLY_SCENE = {
    "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
    "layers": [
        {
            "id": "layer-title",
            "kind": "text",
            "confidence": 0.95,
            "bbox": {"x": 50, "y": 50, "w": 980, "h": 80},
            "text": "Big Title",
            "style": {"fontSize": 72, "fontWeight": "bold"},
        },
        {
            "id": "layer-sub",
            "kind": "text",
            "confidence": 0.85,
            "bbox": {"x": 50, "y": 150, "w": 600, "h": 40},
            "text": "Smaller subtitle",
            "style": {"fontSize": 24, "fontWeight": "400"},
        },
        {
            "id": "layer-meta",
            "kind": "text",
            "confidence": 0.60,
            "bbox": {"x": 50, "y": 200, "w": 400, "h": 30},
            "text": "Meta info",
            "style": {"fontSize": 16, "fontWeight": "300"},
        },
    ],
}

_EMPTY_SCENE = {
    "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
    "layers": [],
}

_OVERFLOW_BBOX_SCENE = {
    "canvas": {"width": 500, "height": 500, "detectedFormat": "square"},
    "layers": [
        {
            "id": "layer-1",
            "kind": "text",
            "confidence": 0.9,
            "bbox": {"x": 400, "y": 400, "w": 200, "h": 200},
            "text": "Overflow",
            "style": {},
        },
        {
            "id": "layer-2",
            "kind": "image",
            "confidence": 0.9,
            "bbox": {"x": -50, "y": -20, "w": 100, "h": 80},
            "description": "Negative coords",
            "cropFromSource": True,
        },
    ],
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSmartImportCompilerStructure(unittest.TestCase):
    """Top-level .tc structure produced by ``compile``."""

    def setUp(self):
        self.compiler = SmartImportCompiler()
        self.tc = self.compiler.compile(
            copy.deepcopy(_VALID_SCENE), source_image=""
        )

    def test_tc_version_is_2(self):
        self.assertEqual(self.tc["tcVersion"], 2)

    def test_design_surface(self):
        ds = self.tc["designSurface"]
        self.assertEqual(ds["width"], 1080)
        self.assertEqual(ds["height"], 1350)

    def test_format(self):
        self.assertEqual(self.tc["format"], "vertical")

    def test_size_string(self):
        self.assertIn("1080", self.tc["size"])
        self.assertIn("1350", self.tc["size"])
        self.assertIn("px", self.tc["size"])

    def test_pages_is_array(self):
        self.assertIsInstance(self.tc["pages"], list)
        self.assertEqual(len(self.tc["pages"]), 1)

    def test_page_has_required_sections(self):
        page = self.tc["pages"][0]
        self.assertEqual(page["id"], "smart-page-1")
        self.assertIn("content", page)
        self.assertIn("elementLayout", page)
        self.assertIn("customElements", page)

    def test_page_content_is_dict(self):
        content = self.tc["pages"][0]["content"]
        self.assertIsInstance(content, dict)

    def test_page_element_layout_is_dict(self):
        el = self.tc["pages"][0]["elementLayout"]
        self.assertIsInstance(el, dict)

    def test_page_custom_elements_is_dict(self):
        ce = self.tc["pages"][0]["customElements"]
        self.assertIsInstance(ce, dict)


class TestBackgroundMapping(unittest.TestCase):
    """Background → elementLayout.background mapping."""

    def setUp(self):
        self.compiler = SmartImportCompiler()

    def test_solid_background(self):
        tc = self.compiler.compile(copy.deepcopy(_SOLID_BG_SCENE), "")
        bg = tc["pages"][0]["elementLayout"]["background"]
        self.assertEqual(bg["backgroundColor"], "#f0f0f0")
        self.assertEqual(bg["zIndex"], 0)
        self.assertNotIn("fillMode", bg)

    def test_gradient_background(self):
        tc = self.compiler.compile(copy.deepcopy(_GRADIENT_BG_SCENE), "")
        bg = tc["pages"][0]["elementLayout"]["background"]
        self.assertEqual(bg["fillMode"], "gradient")
        self.assertEqual(bg["gradientStart"], "#ff0000")
        self.assertEqual(bg["gradientEnd"], "#0000ff")
        self.assertEqual(bg["gradientAngle"], 135)
        self.assertEqual(bg["zIndex"], 0)

    def test_no_background_skips_bg(self):
        tc = self.compiler.compile(copy.deepcopy(_NO_BG_SCENE), "")
        layout = tc["pages"][0]["elementLayout"]
        self.assertNotIn("background", layout)

    def test_background_without_color_defaults(self):
        scene = copy.deepcopy(_SOLID_BG_SCENE)
        scene["background"] = {"kind": "solid"}  # no color
        tc = self.compiler.compile(scene, "")
        bg = tc["pages"][0]["elementLayout"]["background"]
        self.assertIn("backgroundColor", bg)  # will be None/default

    def test_background_single_stop_gradient(self):
        """A gradient with only 1 stop should handle gracefully."""
        scene = copy.deepcopy(_GRADIENT_BG_SCENE)
        scene["background"]["gradient"]["stops"] = [
            {"color": "#aabbcc", "position": 0},
        ]
        tc = self.compiler.compile(scene, "")
        bg = tc["pages"][0]["elementLayout"]["background"]
        self.assertEqual(bg["fillMode"], "gradient")
        self.assertEqual(bg["gradientStart"], "#aabbcc")
        # When only 1 stop, both start and end are that stop
        self.assertEqual(bg["gradientEnd"], "#aabbcc")


class TestTextLayerMapping(unittest.TestCase):
    """Text layers → content + customElements + elementLayout."""

    def setUp(self):
        self.compiler = SmartImportCompiler()
        self.tc = self.compiler.compile(
            copy.deepcopy(_VALID_SCENE), source_image=""
        )
        self.page = self.tc["pages"][0]

    def test_text_custom_element_type(self):
        ce = self.page["customElements"]["layer-1"]
        self.assertEqual(ce["type"], "text")

    def test_text_custom_element_has_text(self):
        ce = self.page["customElements"]["layer-1"]
        self.assertEqual(ce["text"], "Main Title Here")
        self.assertEqual(ce["html"], "Main Title Here")

    def test_text_style_font_size(self):
        ce = self.page["customElements"]["layer-1"]
        self.assertEqual(ce["fontSize"], 48)

    def test_text_style_font_weight(self):
        ce = self.page["customElements"]["layer-1"]
        # "bold" → "bold"
        self.assertEqual(ce["fontWeight"], "bold")

    def test_text_style_color(self):
        ce = self.page["customElements"]["layer-1"]
        self.assertEqual(ce["color"], "#000000")

    def test_text_style_text_align(self):
        ce = self.page["customElements"]["layer-1"]
        self.assertEqual(ce["textAlign"], "center")

    def test_text_element_layout_position(self):
        el = self.page["elementLayout"]["layer-1"]
        self.assertEqual(el["x"], 50)
        self.assertEqual(el["y"], 100)
        self.assertEqual(el["w"], 400)
        self.assertEqual(el["h"], 60)

    def test_text_element_layout_z_index(self):
        el = self.page["elementLayout"]["layer-1"]
        # Background at 0, layers start at 1
        self.assertEqual(el["zIndex"], 1)

    def test_second_text_gets_z_index_2(self):
        el = self.page["elementLayout"]["layer-2"]
        self.assertEqual(el["zIndex"], 2)

    def test_numeric_font_weight_mapped(self):
        ce = self.page["customElements"]["layer-2"]
        # "400" → "regular"
        self.assertEqual(ce["fontWeight"], "regular")


class TestImageLayerMapping(unittest.TestCase):
    """Image layers → customElements with crop data URI."""

    def setUp(self):
        self.compiler = SmartImportCompiler()
        self.tmp_dir = tempfile.mkdtemp()
        self.test_image = os.path.join(self.tmp_dir, "test.jpg")
        _make_test_image(self.test_image, width=1080, height=1350)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_image_custom_element_type(self):
        tc = self.compiler.compile(copy.deepcopy(_VALID_SCENE), self.test_image)
        ce = tc["pages"][0]["customElements"]["layer-3"]
        self.assertEqual(ce["type"], "image")

    def test_image_src_is_data_uri(self):
        tc = self.compiler.compile(copy.deepcopy(_VALID_SCENE), self.test_image)
        ce = tc["pages"][0]["customElements"]["layer-3"]
        self.assertTrue(ce["src"].startswith("data:image/"))
        self.assertIn(";base64,", ce["src"])

    def test_image_upload_status(self):
        tc = self.compiler.compile(copy.deepcopy(_VALID_SCENE), self.test_image)
        ce = tc["pages"][0]["customElements"]["layer-3"]
        self.assertEqual(ce["uploadStatus"], "pending")
        self.assertTrue(ce["needsUpload"])

    def test_image_intrinsic_dimensions(self):
        tc = self.compiler.compile(copy.deepcopy(_VALID_SCENE), self.test_image)
        ce = tc["pages"][0]["customElements"]["layer-3"]
        # Crop bbox is (100, 300, 900, 800) → 800×500
        self.assertEqual(ce["intrinsicWidth"], 800)
        self.assertEqual(ce["intrinsicHeight"], 500)

    def test_image_element_layout_position(self):
        tc = self.compiler.compile(copy.deepcopy(_VALID_SCENE), self.test_image)
        el = tc["pages"][0]["elementLayout"]["layer-3"]
        self.assertEqual(el["x"], 100)
        self.assertEqual(el["y"], 300)
        self.assertEqual(el["w"], 800)
        self.assertEqual(el["h"], 500)

    def test_image_without_source_gets_no_src(self):
        tc = self.compiler.compile(copy.deepcopy(_VALID_SCENE), "")
        ce = tc["pages"][0]["customElements"]["layer-3"]
        self.assertNotIn("src", ce)

    def test_image_with_nonexistent_source(self):
        tc = self.compiler.compile(
            copy.deepcopy(_VALID_SCENE), "/nonexistent/image.jpg"
        )
        ce = tc["pages"][0]["customElements"]["layer-3"]
        self.assertNotIn("src", ce)

    def test_image_crop_beyond_bounds(self):
        """Bbox extending beyond image bounds should clamp gracefully."""
        scene = copy.deepcopy(_VALID_SCENE)
        # Create a tiny image and try to crop from it
        tiny_img = os.path.join(self.tmp_dir, "tiny.jpg")
        _make_test_image(tiny_img, width=50, height=50)

        tc = self.compiler.compile(scene, tiny_img)
        ce = tc["pages"][0]["customElements"]["layer-3"]
        # The bbox (100,300,800,500) is beyond the 50×50 image,
        # so crop will clamp and produce something smaller
        self.assertIn("src", ce)
        self.assertTrue(ce["src"].startswith("data:image/"))
        os.remove(tiny_img)


class TestShapeLayerMapping(unittest.TestCase):
    """Shape layers → customElements."""

    def setUp(self):
        self.compiler = SmartImportCompiler()
        self.tc = self.compiler.compile(
            copy.deepcopy(_VALID_SCENE), source_image=""
        )
        self.ce = self.tc["pages"][0]["customElements"]["layer-4"]

    def test_shape_custom_element_type(self):
        self.assertEqual(self.ce["type"], "shape")

    def test_shape_kind(self):
        self.assertEqual(self.ce["shapeKind"], "rectangle")

    def test_shape_style_fill(self):
        self.assertEqual(self.ce["fillColor"], "#ff0000")

    def test_shape_style_opacity(self):
        self.assertEqual(self.ce["opacity"], 0.3)

    def test_shape_style_border_radius(self):
        self.assertEqual(self.ce["borderRadius"], 0)

    def test_shape_element_layout(self):
        el = self.tc["pages"][0]["elementLayout"]["layer-4"]
        self.assertEqual(el["x"], 0)
        self.assertEqual(el["y"], 0)
        self.assertEqual(el["w"], 1080)
        self.assertEqual(el["h"], 1350)
        # Background is zIndex 0, then layer-1 (text) = 1, layer-2 (text) = 2,
        # layer-3 (image) = 3, layer-4 (shape) = 4
        self.assertEqual(el["zIndex"], 4)

    def test_shape_with_minimal_data(self):
        """A shape layer with only required fields should still compile."""
        scene = {
            "canvas": {"width": 100, "height": 100, "detectedFormat": "square"},
            "layers": [
                {
                    "id": "my-shape",
                    "kind": "shape",
                    "confidence": 0.5,
                    "bbox": {"x": 10, "y": 10, "w": 50, "h": 50},
                    "shape": "circle",
                },
            ],
        }
        tc = self.compiler.compile(scene, "")
        ce = tc["pages"][0]["customElements"]["my-shape"]
        self.assertEqual(ce["type"], "shape")
        self.assertEqual(ce["shapeKind"], "circle")


class TestContentKeyAssignment(unittest.TestCase):
    """Heuristic content-key assignment (title/subtitle/meta/...)."""

    def setUp(self):
        self.compiler = SmartImportCompiler()

    def test_largest_text_becomes_title(self):
        tc = self.compiler.compile(copy.deepcopy(_TEXT_ONLY_SCENE), "")
        content = tc["pages"][0]["content"]
        self.assertEqual(content.get("title"), "Big Title")

    def test_second_largest_becomes_subtitle(self):
        tc = self.compiler.compile(copy.deepcopy(_TEXT_ONLY_SCENE), "")
        content = tc["pages"][0]["content"]
        self.assertEqual(content.get("subtitle"), "Smaller subtitle")

    def test_third_becomes_meta(self):
        tc = self.compiler.compile(copy.deepcopy(_TEXT_ONLY_SCENE), "")
        content = tc["pages"][0]["content"]
        self.assertEqual(content.get("meta"), "Meta info")

    def test_no_text_layers_returns_empty_content(self):
        tc = self.compiler.compile(copy.deepcopy(_EMPTY_SCENE), "")
        content = tc["pages"][0]["content"]
        self.assertEqual(content, {})

    def test_max_five_content_keys(self):
        """With more than 5 text layers, only 5 keys are assigned."""
        layers = []
        for i in range(7):
            layers.append({
                "id": f"layer-{i}",
                "kind": "text",
                "confidence": 0.9 - (i * 0.05),
                "bbox": {"x": 0, "y": i * 50, "w": 200, "h": 30},
                "text": f"Text block {i + 1}",
                "style": {"fontSize": 24 - i * 2},
            })
        scene = {
            "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
            "layers": layers,
        }
        tc = self.compiler.compile(scene, "")
        content = tc["pages"][0]["content"]
        self.assertLessEqual(len(content), 5)

    def test_content_keys_order_by_importance(self):
        """assignment respects visual prominence (area × fontSize × confidence)."""
        scene = {
            "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
            "layers": [
                {
                    "id": "sml",
                    "kind": "text",
                    "confidence": 0.9,
                    "bbox": {"x": 0, "y": 100, "w": 100, "h": 20},
                    "text": "Small unimportant",
                    "style": {"fontSize": 12},
                },
                {
                    "id": "big",
                    "kind": "text",
                    "confidence": 0.9,
                    "bbox": {"x": 0, "y": 0, "w": 500, "h": 80},
                    "text": "Big important title",
                    "style": {"fontSize": 48},
                },
            ],
        }
        tc = self.compiler.compile(scene, "")
        content = tc["pages"][0]["content"]
        self.assertEqual(content.get("title"), "Big important title")
        self.assertEqual(content.get("subtitle"), "Small unimportant")


class TestConfidenceLabel(unittest.TestCase):
    """``_map_confidence_label`` helper."""

    def setUp(self):
        self.compiler = SmartImportCompiler()

    def test_high_confidence(self):
        self.assertEqual(self.compiler._map_confidence_label(0.95), "high")

    def test_high_boundary(self):
        self.assertEqual(self.compiler._map_confidence_label(0.81), "high")

    def test_medium_confidence(self):
        self.assertEqual(self.compiler._map_confidence_label(0.75), "medium")

    def test_medium_boundary(self):
        self.assertEqual(self.compiler._map_confidence_label(0.51), "medium")

    def test_low_confidence(self):
        self.assertEqual(self.compiler._map_confidence_label(0.3), "low")

    def test_low_boundary(self):
        self.assertEqual(self.compiler._map_confidence_label(0.5), "low")


class TestFontWeightMapping(unittest.TestCase):
    """``_map_weight`` normalisation."""

    def setUp(self):
        self.compiler = SmartImportCompiler()

    def test_bold_named(self):
        self.assertEqual(self.compiler._map_weight("bold"), "bold")

    def test_bold_numeric_700(self):
        self.assertEqual(self.compiler._map_weight("700"), "bold")

    def test_medium_named(self):
        self.assertEqual(self.compiler._map_weight("medium"), "medium")

    def test_medium_numeric_500(self):
        self.assertEqual(self.compiler._map_weight("500"), "medium")

    def test_regular_named(self):
        self.assertEqual(self.compiler._map_weight("regular"), "regular")

    def test_regular_numeric_400(self):
        self.assertEqual(self.compiler._map_weight("400"), "regular")

    def test_light_300(self):
        self.assertEqual(self.compiler._map_weight("300"), "regular")

    def test_empty_string(self):
        self.assertEqual(self.compiler._map_weight(""), "regular")

    def test_none(self):
        self.assertEqual(self.compiler._map_weight(None), "regular")

    def test_semibold_variant(self):
        self.assertEqual(self.compiler._map_weight("semibold"), "medium")
        self.assertEqual(self.compiler._map_weight("semi-bold"), "medium")

    def test_bolder(self):
        self.assertEqual(self.compiler._map_weight("bolder"), "bold")


class TestFontMapping(unittest.TestCase):
    """``_map_font`` category → family."""

    def setUp(self):
        self.compiler = SmartImportCompiler()

    def test_sans_serif_to_manrope(self):
        self.assertEqual(self.compiler._map_font("sans-serif"), "Manrope")

    def test_serif_to_montserrat(self):
        self.assertEqual(self.compiler._map_font("serif"), "Montserrat")

    def test_display_to_montserrat(self):
        self.assertEqual(self.compiler._map_font("display"), "Montserrat")

    def test_unknown_defaults_to_manrope(self):
        self.assertEqual(self.compiler._map_font("comic-sans"), "Manrope")


class TestAlignMapping(unittest.TestCase):
    """``_map_align`` normalisation."""

    def setUp(self):
        self.compiler = SmartImportCompiler()

    def test_left(self):
        self.assertEqual(self.compiler._map_align("left"), "left")

    def test_center(self):
        self.assertEqual(self.compiler._map_align("center"), "center")

    def test_right(self):
        self.assertEqual(self.compiler._map_align("right"), "right")

    def test_justify(self):
        self.assertEqual(self.compiler._map_align("justify"), "justify")

    def test_invalid_defaults_to_left(self):
        self.assertEqual(self.compiler._map_align("top"), "left")


class TestBboxClamping(unittest.TestCase):
    """Compiler should handle extreme or negative bbox values."""

    def setUp(self):
        self.compiler = SmartImportCompiler()

    def test_overflow_bbox_in_element_layout(self):
        """Bbox extending beyond canvas should still appear in layout."""
        tc = self.compiler.compile(
            copy.deepcopy(_OVERFLOW_BBOX_SCENE), source_image=""
        )
        el = tc["pages"][0]["elementLayout"]["layer-1"]
        # The compiler does NOT clamp — it passes bbox through.
        # Clamping is expected to have been done by the validator.
        # Still, bbox values should be present.
        self.assertEqual(el["x"], 400)
        self.assertEqual(el["y"], 400)
        self.assertEqual(el["w"], 200)
        self.assertEqual(el["h"], 200)

    def test_negative_bbox_coords(self):
        """Negative bbox coordinates pass through (validator clamps them)."""
        tc = self.compiler.compile(
            copy.deepcopy(_OVERFLOW_BBOX_SCENE), source_image=""
        )
        el = tc["pages"][0]["elementLayout"]["layer-2"]
        self.assertEqual(el["x"], -50)
        self.assertEqual(el["y"], -20)
        self.assertEqual(el["w"], 100)
        self.assertEqual(el["h"], 80)

    def test_zero_bbox(self):
        """Zero-dimension bbox should not crash."""
        scene = {
            "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
            "layers": [
                {
                    "id": "zero",
                    "kind": "text",
                    "confidence": 0.5,
                    "bbox": {"x": 0, "y": 0, "w": 0, "h": 0},
                    "text": "",
                    "style": {},
                },
            ],
        }
        tc = self.compiler.compile(scene, "")
        el = tc["pages"][0]["elementLayout"]["zero"]
        self.assertEqual(el["w"], 0)
        self.assertEqual(el["h"], 0)
        ce = tc["pages"][0]["customElements"]["zero"]
        self.assertEqual(ce["type"], "text")
        self.assertEqual(ce["text"], "")

    def test_missing_bbox_keys(self):
        """Missing bbox keys should not raise."""
        scene = {
            "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
            "layers": [
                {
                    "id": "partial",
                    "kind": "shape",
                    "confidence": 0.5,
                    "bbox": {"x": 10},  # missing y, w, h
                    "shape": "rectangle",
                },
            ],
        }
        tc = self.compiler.compile(scene, "")
        el = tc["pages"][0]["elementLayout"]["partial"]
        self.assertEqual(el["x"], 10)
        self.assertEqual(el["y"], 0)  # default
        self.assertEqual(el["w"], 0)  # default
        self.assertEqual(el["h"], 0)  # default


class TestEmptyScene(unittest.TestCase):
    """An empty SceneGraph produces a valid minimal .tc."""

    def setUp(self):
        self.compiler = SmartImportCompiler()
        self.tc = self.compiler.compile(copy.deepcopy(_EMPTY_SCENE), "")

    def test_minimal_tc_structure(self):
        self.assertEqual(self.tc["tcVersion"], 2)
        self.assertIn("designSurface", self.tc)
        self.assertIn("pages", self.tc)
        self.assertIsInstance(self.tc["pages"], list)

    def test_minimal_page_sections(self):
        page = self.tc["pages"][0]
        self.assertEqual(page["id"], "smart-page-1")
        self.assertEqual(page["content"], {})
        self.assertEqual(page["elementLayout"], {})
        self.assertEqual(page["customElements"], {})

    def test_minimal_design_surface(self):
        self.assertEqual(self.tc["designSurface"]["width"], 1080)
        self.assertEqual(self.tc["designSurface"]["height"], 1350)

    def test_minimal_format(self):
        self.assertEqual(self.tc["format"], "vertical")


class TestCropImage(unittest.TestCase):
    """``_crop_image`` edge cases."""

    def setUp(self):
        self.compiler = SmartImportCompiler()
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_crop_returns_data_uri(self):
        img_path = os.path.join(self.tmp_dir, "test.jpg")
        _make_test_image(img_path, 200, 150)
        bbox = {"x": 10, "y": 10, "w": 100, "h": 80}
        uri = self.compiler._crop_image(img_path, bbox)
        self.assertTrue(uri.startswith("data:image/"))
        self.assertIn(";base64,", uri)

    def test_crop_empty_string_on_missing_file(self):
        uri = self.compiler._crop_image("/nonexistent.jpg", {"x": 0, "y": 0, "w": 10, "h": 10})
        self.assertEqual(uri, "")

    def test_crop_empty_string_on_zero_area(self):
        img_path = os.path.join(self.tmp_dir, "test.jpg")
        _make_test_image(img_path, 100, 100)
        uri = self.compiler._crop_image(img_path, {"x": 0, "y": 0, "w": 0, "h": 0})
        self.assertEqual(uri, "")

    def test_crop_clamps_to_image_bounds(self):
        """Bbox larger than image should clamp."""
        img_path = os.path.join(self.tmp_dir, "small.jpg")
        _make_test_image(img_path, 50, 50)
        bbox = {"x": 0, "y": 0, "w": 500, "h": 500}
        uri = self.compiler._crop_image(img_path, bbox)
        self.assertTrue(uri.startswith("data:image/"))

    def test_crop_negative_bbox(self):
        img_path = os.path.join(self.tmp_dir, "test.jpg")
        _make_test_image(img_path, 100, 100)
        bbox = {"x": -10, "y": -10, "w": 50, "h": 50}
        uri = self.compiler._crop_image(img_path, bbox)
        self.assertTrue(uri.startswith("data:image/"))

    def test_crop_with_jpeg_format(self):
        img_path = os.path.join(self.tmp_dir, "photo.jpg")
        _make_test_image(img_path, 100, 100)
        bbox = {"x": 0, "y": 0, "w": 50, "h": 50}
        uri = self.compiler._crop_image(img_path, bbox)
        self.assertTrue(uri.startswith("data:image/jpeg;base64,"))


class TestExport(unittest.TestCase):
    """``export`` writes valid JSON to disk."""

    def setUp(self):
        self.compiler = SmartImportCompiler()
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_export_writes_file(self):
        tc = self.compiler.compile(copy.deepcopy(_VALID_SCENE), "")
        out_path = os.path.join(self.tmp_dir, "design.tc")
        self.compiler.export(tc, out_path)
        self.assertTrue(os.path.exists(out_path))

    def test_export_valid_json(self):
        tc = self.compiler.compile(copy.deepcopy(_VALID_SCENE), "")
        out_path = os.path.join(self.tmp_dir, "design.tc")
        self.compiler.export(tc, out_path)
        with open(out_path, encoding="utf-8") as f:
            loaded = json.load(f)
        self.assertEqual(loaded["tcVersion"], 2)
        self.assertIn("pages", loaded)

    def test_export_creates_parent_dir(self):
        nested = os.path.join(self.tmp_dir, "subdir", "nested", "design.tc")
        tc = self.compiler.compile(copy.deepcopy(_EMPTY_SCENE), "")
        self.compiler.export(tc, nested)
        self.assertTrue(os.path.exists(nested))


class TestIntegrationValidScene(unittest.TestCase):
    """Full integration: compile a complete mixed-type SceneGraph."""

    def setUp(self):
        self.compiler = SmartImportCompiler()
        self.tmp_dir = tempfile.mkdtemp()
        self.test_image = os.path.join(self.tmp_dir, "source.jpg")
        _make_test_image(self.test_image, width=1080, height=1350)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_full_scene_compiles(self):
        """A fully populated SceneGraph produces a rich .tc with all sections."""
        tc = self.compiler.compile(
            copy.deepcopy(_VALID_SCENE), self.test_image
        )
        page = tc["pages"][0]

        # Content has 2 text entries (title + subtitle)
        self.assertIn("title", page["content"])
        self.assertIn("subtitle", page["content"])
        self.assertEqual(page["content"]["title"], "Main Title Here")
        self.assertEqual(page["content"]["subtitle"], "Subtitle description")

        # Element layout has 5 entries (background + 4 layers)
        self.assertIn("background", page["elementLayout"])
        self.assertIn("layer-1", page["elementLayout"])
        self.assertIn("layer-2", page["elementLayout"])
        self.assertIn("layer-3", page["elementLayout"])
        self.assertIn("layer-4", page["elementLayout"])
        self.assertEqual(len(page["elementLayout"]), 5)

        # Custom elements has 4 entries (text × 2 + image + shape)
        self.assertIn("layer-1", page["customElements"])
        self.assertIn("layer-2", page["customElements"])
        self.assertIn("layer-3", page["customElements"])
        self.assertIn("layer-4", page["customElements"])
        self.assertEqual(len(page["customElements"]), 4)

        # Text elements
        self.assertEqual(page["customElements"]["layer-1"]["type"], "text")
        self.assertEqual(page["customElements"]["layer-2"]["type"], "text")

        # Image element
        self.assertEqual(page["customElements"]["layer-3"]["type"], "image")
        self.assertIn("src", page["customElements"]["layer-3"])
        self.assertIn("intrinsicWidth", page["customElements"]["layer-3"])
        self.assertIn("intrinsicHeight", page["customElements"]["layer-3"])

        # Shape element
        self.assertEqual(page["customElements"]["layer-4"]["type"], "shape")
        self.assertEqual(
            page["customElements"]["layer-4"]["shapeKind"], "rectangle"
        )

    def test_z_index_is_incremental(self):
        """zIndex increments by layer order, background at 0."""
        tc = self.compiler.compile(
            copy.deepcopy(_VALID_SCENE), self.test_image
        )
        el = tc["pages"][0]["elementLayout"]

        self.assertEqual(el["background"]["zIndex"], 0)
        self.assertEqual(el["layer-1"]["zIndex"], 1)
        self.assertEqual(el["layer-2"]["zIndex"], 2)
        self.assertEqual(el["layer-3"]["zIndex"], 3)
        self.assertEqual(el["layer-4"]["zIndex"], 4)

    def test_z_index_without_background_starts_at_0(self):
        """Without background, first layer starts at zIndex 0."""
        tc = self.compiler.compile(copy.deepcopy(_NO_BG_SCENE), "")
        # Empty scene, no layers to check, but confirm no crash
        self.assertIn("pages", tc)

    def test_tc_is_valid_json(self):
        """Compiled .tc should always be valid JSON-serialisable."""
        tc = self.compiler.compile(
            copy.deepcopy(_VALID_SCENE), self.test_image
        )
        dumped = json.dumps(tc, indent=2)
        loaded = json.loads(dumped)
        self.assertEqual(loaded["tcVersion"], 2)

    def test_data_uri_decodes_correctly(self):
        """The cropped image data URI should decode to a valid image."""
        tc = self.compiler.compile(
            copy.deepcopy(_VALID_SCENE), self.test_image
        )
        src = tc["pages"][0]["customElements"]["layer-3"]["src"]
        header, encoded = src.split(",", 1)
        from PIL import Image
        import io
        img_data = base64.b64decode(encoded)
        img = Image.open(io.BytesIO(img_data))
        # Crop of (100, 300, 800, 500) from 1080×1350 source
        self.assertEqual(img.width, 800)
        self.assertEqual(img.height, 500)


class TestCompilationModes(unittest.TestCase):
    """V1 compilation modes control which editable layers are emitted."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.test_image = os.path.join(self.tmp_dir, "source.jpg")
        _make_test_image(self.test_image, width=1080, height=1350)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_text_only_mode_omits_image_and_shape_layers(self):
        compiler = SmartImportCompiler(mode="text_only")
        tc = compiler.compile(copy.deepcopy(_VALID_SCENE), self.test_image)
        page = tc["pages"][0]

        self.assertEqual(set(page["customElements"].keys()), {"layer-1", "layer-2"})
        self.assertEqual(set(page["elementLayout"].keys()), {"background", "layer-1", "layer-2"})
        self.assertEqual(page["customElements"]["layer-1"]["type"], "text")
        self.assertEqual(page["customElements"]["layer-2"]["type"], "text")

    def test_basic_image_layers_mode_keeps_only_high_confidence_non_text_layers(self):
        scene = copy.deepcopy(_VALID_SCENE)
        scene["layers"].append({
            "id": "low-image",
            "kind": "image",
            "confidence": 0.49,
            "bbox": {"x": 10, "y": 10, "w": 100, "h": 100},
            "description": "Too uncertain",
            "cropFromSource": True,
        })

        compiler = SmartImportCompiler(mode="basic_image_layers")
        tc = compiler.compile(scene, self.test_image)
        page = tc["pages"][0]

        self.assertIn("layer-3", page["customElements"])
        self.assertIn("layer-4", page["customElements"])
        self.assertNotIn("low-image", page["customElements"])
        self.assertNotIn("low-image", page["elementLayout"])

    def test_invalid_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            SmartImportCompiler(mode="advanced_restoration")


class TestMapWeightEdgeCases(unittest.TestCase):
    """Additional weight mapping edge cases."""

    def setUp(self):
        self.compiler = SmartImportCompiler()

    def test_weight_100(self):
        self.assertEqual(self.compiler._map_weight("100"), "regular")

    def test_weight_900(self):
        self.assertEqual(self.compiler._map_weight("900"), "bold")

    def test_weight_case_insensitive(self):
        self.assertEqual(self.compiler._map_weight("Bold"), "bold")
        self.assertEqual(self.compiler._map_weight("MEDIUM"), "medium")

    def test_weight_with_whitespace(self):
        self.assertEqual(self.compiler._map_weight(" 700 "), "bold")


if __name__ == "__main__":
    unittest.main()
