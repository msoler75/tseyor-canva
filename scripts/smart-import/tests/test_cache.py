"""
Unit and integration tests for SmartImportPipeline cache helpers.

The cache is intentionally owned by the orchestrator: it prevents repeated
OpenRouter calls for identical image bytes and stores deterministic artifacts
under ``output/.cache``.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import SmartImportPipeline


def _write_file(path: str, data: bytes) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return path


class TestCacheKey(unittest.TestCase):
    """Hash-based cache key generation."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.image_path = _write_file(
            os.path.join(self.tmp_dir, "image.jpg"),
            b"same-binary-image-content",
        )
        self.client_patcher = patch("pipeline.OpenRouterClient")
        self.client_patcher.start().return_value.usage_logs = []

    def tearDown(self):
        self.client_patcher.stop()
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_cache_key_uses_sha256_pipeline_version_and_model_id(self):
        pipeline = SmartImportPipeline({
            "dataset_dir": self.tmp_dir,
            "output_dir": os.path.join(self.tmp_dir, "output"),
            "model": "test-model",
            "pipeline_version": "9.9.9",
        })

        digest = hashlib.sha256(b"same-binary-image-content").hexdigest()
        self.assertEqual(
            pipeline._cache_key(self.image_path),
            f"smart-import:{digest}:9.9.9:test-model",
        )

    def test_cache_key_invalidates_when_model_changes(self):
        first = SmartImportPipeline({
            "dataset_dir": self.tmp_dir,
            "output_dir": os.path.join(self.tmp_dir, "out-a"),
            "model": "model-a",
        })
        second = SmartImportPipeline({
            "dataset_dir": self.tmp_dir,
            "output_dir": os.path.join(self.tmp_dir, "out-b"),
            "model": "model-b",
        })

        self.assertNotEqual(first._cache_key(self.image_path), second._cache_key(self.image_path))

    def test_cache_key_invalidates_when_pipeline_version_changes(self):
        first = SmartImportPipeline({
            "dataset_dir": self.tmp_dir,
            "output_dir": os.path.join(self.tmp_dir, "out-a"),
            "model": "test-model",
            "pipeline_version": "1.0.0",
        })
        second = SmartImportPipeline({
            "dataset_dir": self.tmp_dir,
            "output_dir": os.path.join(self.tmp_dir, "out-b"),
            "model": "test-model",
            "pipeline_version": "1.0.1",
        })

        self.assertNotEqual(first._cache_key(self.image_path), second._cache_key(self.image_path))


class TestCacheArtifacts(unittest.TestCase):
    """Flat-file cache persistence."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.client_patcher = patch("pipeline.OpenRouterClient")
        self.client_patcher.start().return_value.usage_logs = []
        self.pipeline = SmartImportPipeline({
            "dataset_dir": self.tmp_dir,
            "output_dir": os.path.join(self.tmp_dir, "output"),
            "model": "test-model",
        })

    def tearDown(self):
        self.client_patcher.stop()
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_save_and_load_scene_artifact(self):
        cache_key = "smart-import:abc:1.0.0:test-model"
        scene = {"canvas": {"width": 100, "height": 100}, "layers": []}

        self.pipeline._save_to_cache(cache_key, "scene", scene)
        loaded = self.pipeline._load_from_cache(cache_key, "scene")

        self.assertEqual(loaded, scene)

    def test_cache_path_is_filesystem_safe_on_windows(self):
        cache_key = "smart-import:abc/def:1.0.0:google/gemini-2.5-flash"
        path = self.pipeline._cache_artifact_path(cache_key, "scene")
        cache_leaf = Path(path).parent.name

        self.assertNotIn(":", cache_leaf)
        self.assertNotIn("/", cache_leaf)
        self.assertTrue(str(path).startswith(os.path.join(self.tmp_dir, "output", ".cache")))


class TestCacheIntegration(unittest.TestCase):
    """Pipeline-level cache reuse across repeated image bytes."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.dataset_dir = os.path.join(self.tmp_dir, "dataset")
        self.output_dir = os.path.join(self.tmp_dir, "output")
        _write_file(os.path.join(self.dataset_dir, "first.jpg"), b"duplicate")
        _write_file(os.path.join(self.dataset_dir, "second.jpg"), b"duplicate")

        self.scene = {
            "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
            "layers": [],
            "background": {"kind": "solid", "color": "#ffffff", "confidence": 1},
        }

        self.validation = MagicMock()
        self.validation.valid = True
        self.validation.errors = []
        self.validation.warnings = []
        self.validation.fixed = self.scene

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    @patch("pipeline.generate_report")
    @patch("pipeline.ImportJudge")
    @patch("pipeline.SmartImportCompiler")
    @patch("pipeline.validate_scene")
    @patch("pipeline.OpenRouterClient")
    def test_repeated_image_bytes_call_openrouter_once(
        self,
        mock_client_cls,
        mock_validate_scene,
        mock_compiler_cls,
        mock_judge_cls,
        mock_generate_report,
    ):
        client = MagicMock()
        client.vision_analyze.return_value = self.scene
        client.usage_logs = []
        mock_client_cls.return_value = client
        mock_validate_scene.return_value = self.validation

        compiler = MagicMock()
        compiler.compile.return_value = {
            "tcVersion": 2,
            "designSurface": {"width": 1080, "height": 1350},
            "pages": [{"id": "smart-page-1", "content": {}, "elementLayout": {}, "customElements": {}}],
        }
        mock_compiler_cls.return_value = compiler

        pipeline = SmartImportPipeline({
            "dataset_dir": self.dataset_dir,
            "output_dir": self.output_dir,
            "model": "test-model",
            "skip_render": True,
            "skip_eval": True,
        })
        results = pipeline.run()

        self.assertEqual(len(results), 2)
        self.assertEqual(client.vision_analyze.call_count, 1)
        self.assertTrue(os.path.isfile(results[0].paths["scene"]))
        self.assertTrue(os.path.isfile(results[1].paths["scene"]))
        self.assertEqual(mock_generate_report.call_count, 1)


if __name__ == "__main__":
    unittest.main()
