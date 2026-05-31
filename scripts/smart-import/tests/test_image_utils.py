"""
Tests for ``image_utils`` — standalone region extraction and data URI helpers.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest

from PIL import Image

from image_utils import extract_region, region_to_data_uri


def _make_test_image(path: str, w: int = 100, h: int = 100) -> None:
    """Create a small solid-colour JPEG fixture."""
    img = Image.new("RGB", (w, h), color=(200, 50, 50))
    img.save(path, "JPEG", quality=90)


class TestRegionToDataUri(unittest.TestCase):
    """``region_to_data_uri`` — data URI output."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_returns_data_uri(self):
        path = os.path.join(self.tmp_dir, "test.jpg")
        _make_test_image(path, 200, 150)
        uri = region_to_data_uri(path, {"x": 10, "y": 10, "w": 100, "h": 80})
        self.assertTrue(uri.startswith("data:image/"))
        self.assertIn(";base64,", uri)

    def test_empty_string_on_missing_file(self):
        uri = region_to_data_uri("/nonexistent.jpg", {"x": 0, "y": 0, "w": 10, "h": 10})
        self.assertEqual(uri, "")

    def test_empty_string_on_zero_area(self):
        path = os.path.join(self.tmp_dir, "test.jpg")
        _make_test_image(path, 100, 100)
        uri = region_to_data_uri(path, {"x": 0, "y": 0, "w": 0, "h": 0})
        self.assertEqual(uri, "")

    def test_empty_string_on_negative_area(self):
        path = os.path.join(self.tmp_dir, "test.jpg")
        _make_test_image(path, 100, 100)
        uri = region_to_data_uri(path, {"x": 5, "y": 5, "w": -10, "h": -10})
        self.assertEqual(uri, "")

    def test_clamps_to_image_bounds(self):
        path = os.path.join(self.tmp_dir, "small.jpg")
        _make_test_image(path, 50, 50)
        uri = region_to_data_uri(path, {"x": 0, "y": 0, "w": 500, "h": 500})
        self.assertTrue(uri.startswith("data:image/"))

    def test_negative_bbox(self):
        path = os.path.join(self.tmp_dir, "test.jpg")
        _make_test_image(path, 100, 100)
        uri = region_to_data_uri(path, {"x": -10, "y": -10, "w": 50, "h": 50})
        self.assertTrue(uri.startswith("data:image/"))

    def test_jpeg_format_preserved(self):
        path = os.path.join(self.tmp_dir, "photo.jpg")
        _make_test_image(path, 100, 100)
        uri = region_to_data_uri(path, {"x": 0, "y": 0, "w": 50, "h": 50})
        self.assertTrue(uri.startswith("data:image/jpeg;base64,"))

    def test_data_uri_decodes_to_valid_image(self):
        path = os.path.join(self.tmp_dir, "test.jpg")
        _make_test_image(path, 100, 100)
        uri = region_to_data_uri(path, {"x": 0, "y": 0, "w": 50, "h": 50})
        import base64, io
        header, encoded = uri.split(",", 1)
        img = Image.open(io.BytesIO(base64.b64decode(encoded)))
        self.assertEqual(img.size, (50, 50))


class TestExtractRegion(unittest.TestCase):
    """``extract_region`` — file-based output."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_extract_to_specified_path(self):
        src = os.path.join(self.tmp_dir, "src.jpg")
        _make_test_image(src, 200, 200)
        out = os.path.join(self.tmp_dir, "crop.png")
        result = extract_region(src, {"x": 10, "y": 10, "w": 80, "h": 60}, output_path=out)
        self.assertEqual(result, out)
        self.assertTrue(os.path.isfile(out))
        img = Image.open(out)
        self.assertEqual(img.size, (80, 60))

    def test_extract_to_temp_file(self):
        src = os.path.join(self.tmp_dir, "src.jpg")
        _make_test_image(src, 100, 100)
        result = extract_region(src, {"x": 0, "y": 0, "w": 50, "h": 50})
        self.assertIsNotNone(result)
        self.assertTrue(os.path.isfile(result))
        self.assertIn("smart-import-crop-", os.path.basename(result))

    def test_extract_none_on_missing_file(self):
        result = extract_region("/nonexistent.jpg", {"x": 0, "y": 0, "w": 10, "h": 10})
        self.assertIsNone(result)

    def test_extract_none_on_zero_area(self):
        src = os.path.join(self.tmp_dir, "src.jpg")
        _make_test_image(src, 100, 100)
        result = extract_region(src, {"x": 0, "y": 0, "w": 0, "h": 0})
        self.assertIsNone(result)

    def test_extract_clamps_and_succeeds(self):
        src = os.path.join(self.tmp_dir, "src.jpg")
        _make_test_image(src, 30, 30)
        out = os.path.join(self.tmp_dir, "big-crop.png")
        result = extract_region(src, {"x": 0, "y": 0, "w": 500, "h": 500}, output_path=out)
        self.assertEqual(result, out)
        img = Image.open(out)
        self.assertEqual(img.size, (30, 30))

    def test_extract_negative_bbox(self):
        src = os.path.join(self.tmp_dir, "src.jpg")
        _make_test_image(src, 100, 100)
        out = os.path.join(self.tmp_dir, "neg-crop.png")
        result = extract_region(src, {"x": -10, "y": -10, "w": 60, "h": 60}, output_path=out)
        self.assertEqual(result, out)
        img = Image.open(out)
        self.assertGreater(img.size[0], 0)
        self.assertGreater(img.size[1], 0)


class TestIntegration(unittest.TestCase):
    """Integration: pipeline components using image_utils."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_extract_then_data_uri_same_region(self):
        src = os.path.join(self.tmp_dir, "grid.jpg")
        _make_test_image(src, 100, 100)
        bbox = {"x": 20, "y": 30, "w": 60, "h": 40}

        out = extract_region(src, bbox)
        self.assertIsNotNone(out)

        uri = region_to_data_uri(src, bbox)
        self.assertTrue(uri.startswith("data:image/"))

        import base64, io
        header, encoded = uri.split(",", 1)
        from_uri = Image.open(io.BytesIO(base64.b64decode(encoded)))
        from_file = Image.open(out)
        self.assertEqual(from_uri.size, from_file.size)

    def test_round_trip_file_to_data_uri(self):
        src = os.path.join(self.tmp_dir, "roundtrip.jpg")
        _make_test_image(src, 200, 200)
        out = extract_region(src, {"x": 50, "y": 50, "w": 100, "h": 100})
        self.assertIsNotNone(out)

        uri = region_to_data_uri(src, {"x": 50, "y": 50, "w": 100, "h": 100})
        self.assertTrue(uri.startswith("data:image/"))


if __name__ == "__main__":
    unittest.main()
