"""
Unit tests for the pipeline orchestrator (pipeline.py).

Tests argument parsing, image iteration, full pipeline flow with mocked
modules, error isolation, skip flags, and report generation integration.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, call, patch

# Ensure the parent directory is on sys.path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import (
    SmartImportPipeline,
    Result,
    build_parser,
    SUPPORTED_EXTENSIONS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_test_image(
    directory: str, name: str, content: str = "fake-image-data"
) -> str:
    """Create a minimal image file (just enough to exist with a valid extension)."""
    path = os.path.join(directory, name)
    with open(path, "w") as f:
        f.write(content)
    return path


# ---------------------------------------------------------------------------
# Test: Argument Parsing
# ---------------------------------------------------------------------------


class TestArgumentParsing(unittest.TestCase):
    """``build_parser`` and CLI defaults."""

    def test_default_values(self):
        """All flags should have sensible defaults."""
        parser = build_parser()
        args = parser.parse_args([])

        self.assertEqual(args.dataset, "scripts/smart-import/dataset/")
        self.assertIsNone(args.model)
        self.assertIsNone(args.compiler_model)
        self.assertIsNone(args.judge_model)
        self.assertEqual(args.output, "scripts/smart-import/output/")
        self.assertEqual(args.mode, "basic_image_layers")
        self.assertFalse(args.skip_analysis)
        self.assertFalse(args.skip_render)
        self.assertFalse(args.skip_eval)
        self.assertIsNone(args.image)
        self.assertFalse(args.verbose)

    def test_custom_values(self):
        """Custom flag values should be reflected."""
        argv = [
            "--dataset", "/custom/dataset/",
            "--model", "custom-model",
            "--compiler-model", "custom-compiler",
            "--judge-model", "custom-judge",
            "--output", "/custom/output/",
            "--mode", "text_only",
            "--skip-analysis",
            "--skip-render",
            "--skip-eval",
            "--image", "poster-simple",
            "--verbose",
        ]
        args = build_parser().parse_args(argv)

        self.assertEqual(args.dataset, "/custom/dataset/")
        self.assertEqual(args.model, "custom-model")
        self.assertEqual(args.compiler_model, "custom-compiler")
        self.assertEqual(args.judge_model, "custom-judge")
        self.assertEqual(args.output, "/custom/output/")
        self.assertEqual(args.mode, "text_only")
        self.assertTrue(args.skip_analysis)
        self.assertTrue(args.skip_render)
        self.assertTrue(args.skip_eval)
        self.assertEqual(args.image, "poster-simple")
        self.assertTrue(args.verbose)

    def test_skip_flags_independent(self):
        """Each skip flag can be set independently."""
        args = build_parser().parse_args(["--skip-analysis"])
        self.assertTrue(args.skip_analysis)
        self.assertFalse(args.skip_render)
        self.assertFalse(args.skip_eval)

        args = build_parser().parse_args(["--skip-render"])
        self.assertFalse(args.skip_analysis)
        self.assertTrue(args.skip_render)
        self.assertFalse(args.skip_eval)

        args = build_parser().parse_args(["--skip-eval"])
        self.assertFalse(args.skip_analysis)
        self.assertFalse(args.skip_render)
        self.assertTrue(args.skip_eval)

    def test_help_flag(self):
        """--help should not raise (SystemExit is expected from argparse)."""
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["--help"])

    def test_unknown_flag(self):
        """Unknown flags should cause exit."""
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["--nonexistent"])

    def test_invalid_mode_rejected(self):
        """``--mode`` should accept only the two V1 compilation modes."""
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["--mode", "advanced_restoration"])


# ---------------------------------------------------------------------------
# Test: Image Iteration
# ---------------------------------------------------------------------------


class TestImageIteration(unittest.TestCase):
    """``_find_images`` discovering and filtering dataset files."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        # We patch OpenRouterClient so pipeline construction doesn't fail
        self.patcher = patch("pipeline.OpenRouterClient")
        self.mock_client_cls = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_client.usage_logs = []
        self.mock_client_cls.return_value = self.mock_client

    def tearDown(self):
        self.patcher.stop()
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _make_pipeline(self, dataset_dir: str | None = None) -> SmartImportPipeline:
        return SmartImportPipeline({
            "dataset_dir": dataset_dir or self.tmp_dir,
            "output_dir": os.path.join(self.tmp_dir, "output"),
        })

    def test_finds_supported_images(self):
        """All supported extensions should be discovered."""
        # Use unique filenames so stems don't collide (e.g. test.jpg vs test.jpeg)
        names = {
            ".jpg": "alpha.jpg",
            ".jpeg": "beta.jpeg",
            ".png": "gamma.png",
            ".webp": "delta.webp",
            ".gif": "epsilon.gif",
        }
        for ext, fname in names.items():
            _create_test_image(self.tmp_dir, fname)

        pipeline = self._make_pipeline()
        images = pipeline._find_images()
        self.assertEqual(len(images), 5)

        stems = {stem for stem, _ in images}
        self.assertEqual(stems, {"alpha", "beta", "gamma", "delta", "epsilon"})

    def test_ignores_unsupported_extensions(self):
        """Non-image files and unsupported extensions should be skipped."""
        _create_test_image(self.tmp_dir, "data.txt")
        _create_test_image(self.tmp_dir, "script.py")
        _create_test_image(self.tmp_dir, "photo.svg")
        _create_test_image(self.tmp_dir, "image.jpg")

        pipeline = self._make_pipeline()
        images = pipeline._find_images()
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0][0], "image")

    def test_ignores_directories(self):
        """Subdirectories should not be treated as images."""
        subdir = os.path.join(self.tmp_dir, "subdir")
        os.makedirs(subdir)
        _create_test_image(self.tmp_dir, "photo.jpg")

        pipeline = self._make_pipeline()
        images = pipeline._find_images()
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0][0], "photo")

    def test_sorts_alphabetically(self):
        """Images should be returned in alphabetical order."""
        _create_test_image(self.tmp_dir, "zebra.jpg")
        _create_test_image(self.tmp_dir, "alpha.png")
        _create_test_image(self.tmp_dir, "beta.webp")

        pipeline = self._make_pipeline()
        images = pipeline._find_images()
        stems = [stem for stem, _ in images]
        self.assertEqual(stems, ["alpha", "beta", "zebra"])

    def test_empty_directory(self):
        """An empty or image-less directory should return an empty list."""
        pipeline = self._make_pipeline()
        images = pipeline._find_images()
        self.assertEqual(images, [])

    def test_nonexistent_directory(self):
        """A path that does not exist should return an empty list."""
        pipeline = self._make_pipeline(dataset_dir="/nonexistent/path")
        images = pipeline._find_images()
        self.assertEqual(images, [])

    def test_filter_by_image_id(self):
        """``filter_image`` should return only the matching stem."""
        _create_test_image(self.tmp_dir, "poster-simple.jpg")
        _create_test_image(self.tmp_dir, "poster-gradient.jpg")
        _create_test_image(self.tmp_dir, "flyer-text.jpg")

        pipeline = self._make_pipeline()
        images = pipeline._find_images(filter_image="poster-simple")
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0][0], "poster-simple")

    def test_filter_no_match_returns_empty(self):
        """A filter that matches nothing should yield an empty list."""
        _create_test_image(self.tmp_dir, "photo.jpg")

        pipeline = self._make_pipeline()
        images = pipeline._find_images(filter_image="nonexistent")
        self.assertEqual(images, [])

    def test_filter_with_dash_stem(self):
        """Filename stems with dashes should work correctly as image IDs."""
        _create_test_image(self.tmp_dir, "poster-display-font.jpg")

        pipeline = self._make_pipeline()
        images = pipeline._find_images(filter_image="poster-display-font")
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0][0], "poster-display-font")

    def test_returns_full_paths(self):
        """The second element should be a full absolute path."""
        _create_test_image(self.tmp_dir, "photo.jpg")

        pipeline = self._make_pipeline()
        images = pipeline._find_images()
        self.assertEqual(len(images), 1)
        _, path = images[0]
        self.assertTrue(os.path.isabs(path) or os.path.exists(path))
        self.assertTrue(path.endswith("photo.jpg"))


# ---------------------------------------------------------------------------
# Test: Pipeline Flow (mocked)
# ---------------------------------------------------------------------------


class TestPipelineFlow(unittest.TestCase):
    """Full pipeline execution with all components mocked."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.dataset_dir = os.path.join(self.tmp_dir, "dataset")
        self.output_dir = os.path.join(self.tmp_dir, "output")
        os.makedirs(self.dataset_dir)

        # Create one test image
        _create_test_image(self.dataset_dir, "test-photo.jpg")

        # Common mock returns
        self.mock_scene = {
            "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
            "layers": [
                {
                    "id": "layer-1",
                    "kind": "text",
                    "confidence": 0.95,
                    "bbox": {"x": 50, "y": 100, "w": 400, "h": 60},
                    "text": "Hello",
                    "style": {"fontSize": 48, "fontWeight": "bold", "color": "#000000"},
                }
            ],
            "background": {"kind": "solid", "color": "#ffffff", "confidence": 0.99},
        }

        self.mock_fixed_scene = dict(self.mock_scene)  # pretend it passes validation

        self.mock_tc = {
            "tcVersion": 2,
            "designSurface": {"width": 1080, "height": 1350},
            "pages": [{
                "id": "smart-page-1",
                "content": {},
                "elementLayout": {},
                "customElements": {},
            }],
        }

        self.mock_score = {
            "overallScore": 0.85,
            "visualSimilarity": 0.8,
            "textAccuracy": 0.9,
            "layoutAccuracy": 0.85,
            "colorAccuracy": 0.75,
            "editability": 0.95,
            "criticalIssues": [],
            "recommendations": ["Increase contrast"],
        }

        self.mock_validation = MagicMock()
        self.mock_validation.valid = True
        self.mock_validation.errors = []
        self.mock_validation.warnings = []
        self.mock_validation.fixed = self.mock_fixed_scene
        self.mock_validation.original = self.mock_scene

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _make_pipeline(self, **overrides) -> SmartImportPipeline:
        config = {
            "dataset_dir": self.dataset_dir,
            "output_dir": self.output_dir,
            "model": "test-model",
            "skip_analysis": False,
            "skip_render": False,  # will be mocked at instance level
            "skip_eval": False,
        }
        config.update(overrides)
        return SmartImportPipeline(config)

    # ---------------------------------------------------------------
    # Full pipeline with all mocked
    # ---------------------------------------------------------------

    @patch("pipeline.OpenRouterClient")
    @patch("pipeline.validate_scene")
    @patch("pipeline.SmartImportCompiler")
    @patch("pipeline.ImportJudge")
    @patch("pipeline.generate_report")
    def test_full_pipeline_success(
        self,
        mock_generate_report,
        mock_judge_cls,
        mock_compiler_cls,
        mock_validate_scene,
        mock_client_cls,
    ):
        """A single image should pass through all phases successfully."""
        # Mock client
        mock_client = MagicMock()
        mock_client.vision_analyze.return_value = self.mock_scene
        mock_client.usage_logs = []
        mock_client_cls.return_value = mock_client

        # Mock validator
        mock_validate_scene.return_value = self.mock_validation

        # Mock compiler
        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = self.mock_tc
        mock_compiler_cls.return_value = mock_compiler

        # Mock judge
        mock_judge = MagicMock()
        mock_judge.evaluate.return_value = self.mock_score
        mock_judge_cls.return_value = mock_judge

        pipeline = self._make_pipeline(skip_render=True)  # skip actual render
        results = pipeline.run()

        # Assertions
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result.status, "success")
        self.assertEqual(result.image_id, "test-photo")
        self.assertEqual(result.model, "test-model")

        # Verify each phase was called
        mock_client.vision_analyze.assert_called_once()
        mock_validate_scene.assert_called_once_with(
            self.mock_scene, mode="basic_image_layers"
        )
        mock_compiler.compile.assert_called_once()

        # Verify report was generated
        mock_generate_report.assert_called_once()

    @patch("pipeline.OpenRouterClient")
    @patch("pipeline.validate_scene")
    @patch("pipeline.SmartImportCompiler")
    @patch("pipeline.ImportJudge")
    @patch("pipeline.generate_report")
    def test_pipeline_with_render_calls_judge(
        self,
        mock_generate_report,
        mock_judge_cls,
        mock_compiler_cls,
        mock_validate_scene,
        mock_client_cls,
    ):
        """When render succeeds, the judge should be called."""
        mock_client = MagicMock()
        mock_client.vision_analyze.return_value = self.mock_scene
        mock_client.usage_logs = []
        mock_client_cls.return_value = mock_client

        mock_validate_scene.return_value = self.mock_validation

        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = self.mock_tc
        mock_compiler_cls.return_value = mock_compiler

        mock_judge = MagicMock()
        mock_judge.evaluate.return_value = self.mock_score
        mock_judge_cls.return_value = mock_judge

        pipeline = self._make_pipeline(skip_render=False)
        # Mock _render_tc to succeed — create the output file
        def _fake_render(tc_path, output_path):
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(b"fake render png")
        pipeline._render_tc = _fake_render

        results = pipeline.run()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "success")

        # Judge should have been called since render succeeded
        mock_judge.evaluate.assert_called_once()

    @patch("pipeline.OpenRouterClient")
    @patch("pipeline.validate_scene")
    @patch("pipeline.SmartImportCompiler")
    @patch("pipeline.ImportJudge")
    @patch("pipeline.generate_report")
    def test_pipeline_calls_vision_with_correct_prompt(
        self,
        mock_generate_report,
        mock_judge_cls,
        mock_compiler_cls,
        mock_validate_scene,
        mock_client_cls,
    ):
        """Vision analyze should receive the analysis prompt and system prompt."""
        mock_client = MagicMock()
        mock_client.vision_analyze.return_value = self.mock_scene
        mock_client.usage_logs = []
        mock_client_cls.return_value = mock_client

        mock_validate_scene.return_value = self.mock_validation
        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = self.mock_tc
        mock_compiler_cls.return_value = mock_compiler
        mock_judge = MagicMock()
        mock_judge.evaluate.return_value = self.mock_score
        mock_judge_cls.return_value = mock_judge

        pipeline = self._make_pipeline(skip_render=True)
        pipeline.run()

        # Check that vision_analyze was called with the right args
        call_kwargs = mock_client.vision_analyze.call_args[1]
        self.assertIn("prompt", call_kwargs)
        self.assertIn("system_prompt", call_kwargs)
        self.assertIn("Analiza esta imagen", call_kwargs["prompt"])
        self.assertIn("Eres un analizador", call_kwargs["system_prompt"])

    @patch("pipeline.OpenRouterClient")
    @patch("pipeline.validate_scene")
    @patch("pipeline.SmartImportCompiler")
    @patch("pipeline.ImportJudge")
    @patch("pipeline.generate_report")
    def test_output_structure(
        self,
        mock_generate_report,
        mock_judge_cls,
        mock_compiler_cls,
        mock_validate_scene,
        mock_client_cls,
    ):
        """Each image result should have the expected directory structure."""
        mock_client = MagicMock()
        mock_client.vision_analyze.return_value = self.mock_scene
        mock_client.usage_logs = []
        mock_client_cls.return_value = mock_client

        mock_validate_scene.return_value = self.mock_validation
        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = self.mock_tc
        mock_compiler_cls.return_value = mock_compiler
        mock_judge = MagicMock()
        mock_judge.evaluate.return_value = self.mock_score
        mock_judge_cls.return_value = mock_judge

        pipeline = self._make_pipeline(skip_render=True)
        results = pipeline.run()

        result = results[0]
        paths = result.paths

        # All expected path keys should exist
        expected_keys = {
            "image", "scene", "scene_fixed", "tc",
            "render", "score", "openrouter",
        }
        self.assertEqual(set(paths.keys()), expected_keys)

        # All paths should be under the model output dir
        model_dir = os.path.join(self.output_dir, "test-model")
        self.assertTrue(paths["tc"].startswith(model_dir))
        self.assertTrue(paths["scene"].startswith(model_dir))
        self.assertTrue(paths["scene_fixed"].startswith(model_dir))

    @patch("pipeline.OpenRouterClient")
    @patch("pipeline.validate_scene")
    @patch("pipeline.SmartImportCompiler")
    @patch("pipeline.ImportJudge")
    @patch("pipeline.generate_report")
    def test_result_dict_format(
        self,
        mock_generate_report,
        mock_judge_cls,
        mock_compiler_cls,
        mock_validate_scene,
        mock_client_cls,
    ):
        """Result.to_dict() should produce the expected keys for the report."""
        mock_client = MagicMock()
        mock_client.vision_analyze.return_value = self.mock_scene
        mock_client.usage_logs = []
        mock_client_cls.return_value = mock_client

        mock_validate_scene.return_value = self.mock_validation
        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = self.mock_tc
        mock_compiler_cls.return_value = mock_compiler
        mock_judge = MagicMock()
        mock_judge.evaluate.return_value = self.mock_score
        mock_judge_cls.return_value = mock_judge

        pipeline = self._make_pipeline(skip_render=True)
        results = pipeline.run()

        d = results[0].to_dict()

        # Keys required by generate_report
        self.assertIn("imageId", d)
        self.assertIn("model", d)
        self.assertIn("score", d)
        self.assertIn("costUsd", d)
        self.assertIn("latencyMs", d)
        self.assertIn("status", d)
        self.assertIn("errorMessage", d)
        self.assertIn("paths", d)


# ---------------------------------------------------------------------------
# Test: Error Handling (single image failure)
# ---------------------------------------------------------------------------


class TestErrorHandling(unittest.TestCase):
    """Errors in one image should not stop processing of others."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.dataset_dir = os.path.join(self.tmp_dir, "dataset")
        self.output_dir = os.path.join(self.tmp_dir, "output")
        os.makedirs(self.dataset_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    @patch("pipeline.OpenRouterClient")
    @patch("pipeline.validate_scene")
    @patch("pipeline.SmartImportCompiler")
    @patch("pipeline.ImportJudge")
    @patch("pipeline.generate_report")
    def test_one_failure_does_not_stop_all(
        self,
        mock_generate_report,
        mock_judge_cls,
        mock_compiler_cls,
        mock_validate_scene,
        mock_client_cls,
    ):
        """When one image fails, the other should still process."""
        # Create images in alphabetical order so "alpha" < "beta"
        _create_test_image(self.dataset_dir, "alpha-ok.jpg")
        _create_test_image(self.dataset_dir, "beta-fail.jpg")

        mock_client = MagicMock()

        # Make the second call to vision_analyze fail
        mock_client.vision_analyze.side_effect = [
            {"canvas": {}, "layers": []},  # first image succeeds
            Exception("API failure"),      # second image fails
        ]
        mock_client.usage_logs = []
        mock_client_cls.return_value = mock_client

        mock_validation = MagicMock()
        mock_validation.valid = True
        mock_validation.errors = []
        mock_validation.warnings = []
        mock_validation.fixed = {
            "canvas": {"width": 1080, "height": 1350}, "layers": [],
        }
        mock_validation.original = {}
        mock_validate_scene.return_value = mock_validation

        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = {
            "tcVersion": 2,
            "designSurface": {},
            "pages": [{
                "id": "smart-page-1", "content": {},
                "elementLayout": {}, "customElements": {},
            }],
        }
        mock_compiler_cls.return_value = mock_compiler

        mock_judge = MagicMock()
        mock_judge.evaluate.return_value = {"overallScore": 0.5}
        mock_judge_cls.return_value = mock_judge

        pipeline = SmartImportPipeline({
            "dataset_dir": self.dataset_dir,
            "output_dir": self.output_dir,
            "model": "test-model",
            "skip_render": True,
            "skip_eval": True,
        })
        results = pipeline.run()

        # Both images should have results
        self.assertEqual(len(results), 2)

        # Both should have completed (failure is caught gracefully)
        self.assertEqual(results[0].image_id, "alpha-ok")
        self.assertEqual(results[1].image_id, "beta-fail")

        # Second image completed despite the error (empty scene fallback)
        # Both have status "success" because pipeline continued with empty scene
        self.assertEqual(results[0].status, "success")

    @patch("pipeline.OpenRouterClient")
    @patch("pipeline.validate_scene")
    @patch("pipeline.SmartImportCompiler")
    @patch("pipeline.ImportJudge")
    @patch("pipeline.generate_report")
    def test_vision_analyze_error_gives_empty_scene(
        self,
        mock_generate_report,
        mock_judge_cls,
        mock_compiler_cls,
        mock_validate_scene,
        mock_client_cls,
    ):
        """If vision_analyze raises, the pipeline should continue with empty scene."""
        _create_test_image(self.dataset_dir, "photo.jpg")

        mock_client = MagicMock()
        mock_client.vision_analyze.side_effect = Exception("API error")
        mock_client.usage_logs = []
        mock_client_cls.return_value = mock_client

        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = {
            "tcVersion": 2,
            "designSurface": {},
            "pages": [{
                "id": "smart-page-1", "content": {},
                "elementLayout": {}, "customElements": {},
            }],
        }
        mock_compiler_cls.return_value = mock_compiler

        pipeline = SmartImportPipeline({
            "dataset_dir": self.dataset_dir,
            "output_dir": self.output_dir,
            "model": "test-model",
            "skip_render": True,
            "skip_eval": True,
        })
        results = pipeline.run()

        # Should have completed with empty scene (compiled with defaults)
        self.assertEqual(len(results), 1)
        # The pipeline completed — compiler was called
        mock_compiler.compile.assert_called_once()

    @patch("pipeline.OpenRouterClient")
    @patch("pipeline.validate_scene")
    @patch("pipeline.SmartImportCompiler")
    @patch("pipeline.ImportJudge")
    @patch("pipeline.generate_report")
    def test_report_generated_even_with_failures(
        self,
        mock_generate_report,
        mock_judge_cls,
        mock_compiler_cls,
        mock_validate_scene,
        mock_client_cls,
    ):
        """Report generation should be called regardless of individual failures."""
        _create_test_image(self.dataset_dir, "photo.jpg")

        mock_client = MagicMock()
        mock_client.vision_analyze.side_effect = Exception("API error")
        mock_client.usage_logs = []
        mock_client_cls.return_value = mock_client

        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = {
            "tcVersion": 2,
            "designSurface": {},
            "pages": [{
                "id": "smart-page-1", "content": {},
                "elementLayout": {}, "customElements": {},
            }],
        }
        mock_compiler_cls.return_value = mock_compiler

        pipeline = SmartImportPipeline({
            "dataset_dir": self.dataset_dir,
            "output_dir": self.output_dir,
            "model": "test-model",
            "skip_render": True,
            "skip_eval": True,
        })
        pipeline.run()

        # generate_report should still be called
        mock_generate_report.assert_called_once()


# ---------------------------------------------------------------------------
# Test: Skip Flags
# ---------------------------------------------------------------------------


class TestSkipFlags(unittest.TestCase):
    """Each ``--skip-*`` flag should bypass the corresponding phase."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.dataset_dir = os.path.join(self.tmp_dir, "dataset")
        self.output_dir = os.path.join(self.tmp_dir, "output")
        os.makedirs(self.dataset_dir)
        _create_test_image(self.dataset_dir, "photo.jpg")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    @patch("pipeline.OpenRouterClient")
    @patch("pipeline.validate_scene")
    @patch("pipeline.SmartImportCompiler")
    @patch("pipeline.ImportJudge")
    @patch("pipeline.generate_report")
    def test_skip_analysis(
        self,
        mock_generate_report,
        mock_judge_cls,
        mock_compiler_cls,
        mock_validate_scene,
        mock_client_cls,
    ):
        """With skip_analysis, vision_analyze should NOT be called."""
        mock_client = MagicMock()
        mock_client.vision_analyze.return_value = {"canvas": {}, "layers": []}
        mock_client.usage_logs = []
        mock_client_cls.return_value = mock_client

        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = {
            "tcVersion": 2,
            "designSurface": {},
            "pages": [{
                "id": "smart-page-1", "content": {},
                "elementLayout": {}, "customElements": {},
            }],
        }
        mock_compiler_cls.return_value = mock_compiler

        mock_judge = MagicMock()
        mock_judge.evaluate.return_value = {"overallScore": 0.8}
        mock_judge_cls.return_value = mock_judge

        pipeline = SmartImportPipeline({
            "dataset_dir": self.dataset_dir,
            "output_dir": self.output_dir,
            "model": "test-model",
            "skip_analysis": True,
            "skip_render": True,
            "skip_eval": False,
        })
        pipeline.run()

        # vision_analyze should NOT have been called (no cached scene to load)
        mock_client.vision_analyze.assert_not_called()

        # But compiler should still have been called (with empty scene)
        mock_compiler.compile.assert_called_once()

    @patch("pipeline.OpenRouterClient")
    @patch("pipeline.validate_scene")
    @patch("pipeline.SmartImportCompiler")
    @patch("pipeline.ImportJudge")
    @patch("pipeline.generate_report")
    def test_skip_render(
        self,
        mock_generate_report,
        mock_judge_cls,
        mock_compiler_cls,
        mock_validate_scene,
        mock_client_cls,
    ):
        """With skip_render, _render_tc should NOT be called."""
        mock_client = MagicMock()
        mock_client.vision_analyze.return_value = {"canvas": {}, "layers": []}
        mock_client.usage_logs = []
        mock_client_cls.return_value = mock_client

        mock_validation = MagicMock()
        mock_validation.valid = True
        mock_validation.errors = []
        mock_validation.warnings = []
        mock_validation.fixed = {
            "canvas": {"width": 1080, "height": 1350}, "layers": [],
        }
        mock_validation.original = {}
        mock_validate_scene.return_value = mock_validation

        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = {
            "tcVersion": 2,
            "designSurface": {},
            "pages": [{
                "id": "smart-page-1", "content": {},
                "elementLayout": {}, "customElements": {},
            }],
        }
        mock_compiler_cls.return_value = mock_compiler

        pipeline = SmartImportPipeline({
            "dataset_dir": self.dataset_dir,
            "output_dir": self.output_dir,
            "model": "test-model",
            "skip_analysis": False,
            "skip_render": True,
            "skip_eval": False,
        })

        # Spy on _render_tc
        pipeline._render_tc = MagicMock()

        mock_judge = MagicMock()
        mock_judge.evaluate.return_value = {"overallScore": 0.8}
        mock_judge_cls.return_value = mock_judge

        pipeline.run()

        # _render_tc should NOT have been called
        pipeline._render_tc.assert_not_called()

    @patch("pipeline.OpenRouterClient")
    @patch("pipeline.validate_scene")
    @patch("pipeline.SmartImportCompiler")
    @patch("pipeline.ImportJudge")
    @patch("pipeline.generate_report")
    def test_skip_eval(
        self,
        mock_generate_report,
        mock_judge_cls,
        mock_compiler_cls,
        mock_validate_scene,
        mock_client_cls,
    ):
        """With skip_eval, judge.evaluate should NOT be called."""
        mock_client = MagicMock()
        mock_client.vision_analyze.return_value = {"canvas": {}, "layers": []}
        mock_client.usage_logs = []
        mock_client_cls.return_value = mock_client

        mock_validation = MagicMock()
        mock_validation.valid = True
        mock_validation.errors = []
        mock_validation.warnings = []
        mock_validation.fixed = {
            "canvas": {"width": 1080, "height": 1350}, "layers": [],
        }
        mock_validation.original = {}
        mock_validate_scene.return_value = mock_validation

        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = {
            "tcVersion": 2,
            "designSurface": {},
            "pages": [{
                "id": "smart-page-1", "content": {},
                "elementLayout": {}, "customElements": {},
            }],
        }
        mock_compiler_cls.return_value = mock_compiler

        mock_judge = MagicMock()
        mock_judge.evaluate.return_value = {"overallScore": 0.8}
        mock_judge_cls.return_value = mock_judge

        pipeline = SmartImportPipeline({
            "dataset_dir": self.dataset_dir,
            "output_dir": self.output_dir,
            "model": "test-model",
            "skip_analysis": False,
            "skip_render": True,
            "skip_eval": True,
        })
        pipeline.run()

        # judge.evaluate should NOT have been called
        mock_judge.evaluate.assert_not_called()

    @patch("pipeline.OpenRouterClient")
    @patch("pipeline.validate_scene")
    @patch("pipeline.SmartImportCompiler")
    @patch("pipeline.ImportJudge")
    @patch("pipeline.generate_report")
    def test_skip_all_phases(
        self,
        mock_generate_report,
        mock_judge_cls,
        mock_compiler_cls,
        mock_validate_scene,
        mock_client_cls,
    ):
        """With all skip flags, only compiler and report should run."""
        mock_client = MagicMock()
        mock_client.vision_analyze.return_value = {}
        mock_client.usage_logs = []
        mock_client_cls.return_value = mock_client

        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = {
            "tcVersion": 2,
            "designSurface": {},
            "pages": [{
                "id": "smart-page-1", "content": {},
                "elementLayout": {}, "customElements": {},
            }],
        }
        mock_compiler_cls.return_value = mock_compiler

        pipeline = SmartImportPipeline({
            "dataset_dir": self.dataset_dir,
            "output_dir": self.output_dir,
            "model": "test-model",
            "skip_analysis": True,
            "skip_render": True,
            "skip_eval": True,
        })
        pipeline.run()

        # Compiler should still have been called
        mock_compiler.compile.assert_called_once()

        # Vision should NOT have been called
        mock_client.vision_analyze.assert_not_called()


# ---------------------------------------------------------------------------
# Test: Report Generation
# ---------------------------------------------------------------------------


class TestReportGeneration(unittest.TestCase):
    """Report generation integration with the pipeline."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.dataset_dir = os.path.join(self.tmp_dir, "dataset")
        self.output_dir = os.path.join(self.tmp_dir, "output")
        os.makedirs(self.dataset_dir)
        _create_test_image(self.dataset_dir, "photo.jpg")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    @patch("pipeline.OpenRouterClient")
    @patch("pipeline.validate_scene")
    @patch("pipeline.SmartImportCompiler")
    @patch("pipeline.ImportJudge")
    @patch("pipeline.generate_report")
    def test_report_called_with_correct_args(
        self,
        mock_generate_report,
        mock_judge_cls,
        mock_compiler_cls,
        mock_validate_scene,
        mock_client_cls,
    ):
        """generate_report should receive results list and output_dir."""
        mock_client = MagicMock()
        mock_client.vision_analyze.return_value = {"canvas": {}, "layers": []}
        mock_client.usage_logs = []
        mock_client_cls.return_value = mock_client

        mock_validation = MagicMock()
        mock_validation.valid = True
        mock_validation.fixed = {
            "canvas": {"width": 1080, "height": 1350}, "layers": [],
        }
        mock_validate_scene.return_value = mock_validation

        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = {
            "tcVersion": 2,
            "designSurface": {},
            "pages": [{
                "id": "smart-page-1", "content": {},
                "elementLayout": {}, "customElements": {},
            }],
        }
        mock_compiler_cls.return_value = mock_compiler

        mock_judge = MagicMock()
        mock_judge.evaluate.return_value = {"overallScore": 0.8}
        mock_judge_cls.return_value = mock_judge

        pipeline = SmartImportPipeline({
            "dataset_dir": self.dataset_dir,
            "output_dir": self.output_dir,
            "model": "test-model",
            "skip_render": True,
            "skip_eval": True,
        })
        results = pipeline.run()

        # generate_report should have been called
        mock_generate_report.assert_called_once()

        # First argument should be a list of dicts with the right structure
        call_args, call_kwargs = mock_generate_report.call_args
        reported_results, reported_output = call_args

        self.assertIsInstance(reported_results, list)
        self.assertEqual(len(reported_results), 1)
        self.assertIn("imageId", reported_results[0])
        self.assertIn("model", reported_results[0])

        # Second argument should be the output dir
        self.assertEqual(reported_output, self.output_dir)

    @patch("pipeline.OpenRouterClient")
    @patch("pipeline.validate_scene")
    @patch("pipeline.SmartImportCompiler")
    @patch("pipeline.ImportJudge")
    def test_report_not_called_when_no_images(
        self,
        mock_judge_cls,
        mock_compiler_cls,
        mock_validate_scene,
        mock_client_cls,
    ):
        """With no images, generate_report should not be called."""
        # Use empty dataset dir
        empty_dir = os.path.join(self.tmp_dir, "empty")
        os.makedirs(empty_dir)

        pipeline = SmartImportPipeline({
            "dataset_dir": empty_dir,
            "output_dir": self.output_dir,
            "model": "test-model",
            "skip_render": True,
            "skip_eval": True,
        })
        results = pipeline.run()

        self.assertEqual(results, [])

    @patch("pipeline.OpenRouterClient")
    @patch("pipeline.validate_scene")
    @patch("pipeline.SmartImportCompiler")
    @patch("pipeline.ImportJudge")
    @patch("pipeline.generate_report")
    def test_model_name_in_report(
        self,
        mock_generate_report,
        mock_judge_cls,
        mock_compiler_cls,
        mock_validate_scene,
        mock_client_cls,
    ):
        """Model name should be propagated to results for the report."""
        mock_client = MagicMock()
        mock_client.vision_analyze.return_value = {"canvas": {}, "layers": []}
        mock_client.usage_logs = []
        mock_client_cls.return_value = mock_client

        mock_validation = MagicMock()
        mock_validation.valid = True
        mock_validation.fixed = {
            "canvas": {"width": 1080, "height": 1350}, "layers": [],
        }
        mock_validate_scene.return_value = mock_validation

        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = {
            "tcVersion": 2,
            "designSurface": {},
            "pages": [{
                "id": "smart-page-1", "content": {},
                "elementLayout": {}, "customElements": {},
            }],
        }
        mock_compiler_cls.return_value = mock_compiler

        mock_judge = MagicMock()
        mock_judge.evaluate.return_value = {"overallScore": 0.8}
        mock_judge_cls.return_value = mock_judge

        pipeline = SmartImportPipeline({
            "dataset_dir": self.dataset_dir,
            "output_dir": self.output_dir,
            "model": "google/gemini-2.5-flash",
            "skip_render": True,
            "skip_eval": True,
        })
        results = pipeline.run()

        # Model name should be sanitized: slashes → dashes, dots → dashes
        self.assertEqual(results[0].model, "google-gemini-2-5-flash")


# ---------------------------------------------------------------------------
# Test: Result Data Class
# ---------------------------------------------------------------------------


class TestResultDataclass(unittest.TestCase):
    """``Result`` dataclass construction and serialisation."""

    def test_default_values(self):
        r = Result()
        self.assertEqual(r.image_id, "")
        self.assertEqual(r.model, "")
        self.assertEqual(r.paths, {})
        self.assertIsNone(r.score)
        self.assertEqual(r.cost_usd, 0.0)
        self.assertEqual(r.latency_ms, 0)
        self.assertEqual(r.status, "success")
        self.assertIsNone(r.error_message)

    def test_to_dict_keys(self):
        r = Result(
            image_id="img-01",
            model="test-model",
            paths={"tc": "/tmp/design.tc"},
            score={"overallScore": 0.85},
            cost_usd=0.005,
            latency_ms=1200,
            status="success",
            error_message=None,
        )
        d = r.to_dict()

        self.assertEqual(d["imageId"], "img-01")
        self.assertEqual(d["model"], "test-model")
        self.assertEqual(d["paths"]["tc"], "/tmp/design.tc")
        self.assertEqual(d["score"]["overallScore"], 0.85)
        self.assertEqual(d["costUsd"], 0.005)
        self.assertEqual(d["latencyMs"], 1200)
        self.assertEqual(d["status"], "success")
        self.assertIsNone(d["errorMessage"])

    def test_to_dict_with_error(self):
        r = Result(
            image_id="img-02",
            model="test-model",
            status="failed",
            error_message="Something went wrong",
        )
        d = r.to_dict()
        self.assertEqual(d["status"], "failed")
        self.assertEqual(d["errorMessage"], "Something went wrong")


# ---------------------------------------------------------------------------
# Test: Pipeline Configuration
# ---------------------------------------------------------------------------


class TestPipelineConfig(unittest.TestCase):
    """SmartImportPipeline initialisation with different configs."""

    def setUp(self):
        # We need a valid API key in env or patched OpenRouterClient
        self.patcher = patch("pipeline.OpenRouterClient")
        self.mock_client_cls = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_client.usage_logs = []
        self.mock_client_cls.return_value = self.mock_client

    def tearDown(self):
        self.patcher.stop()

    def test_requires_dataset_dir(self):
        """dataset_dir is required in config."""
        with self.assertRaises(KeyError):
            SmartImportPipeline({"model": "test"})

    def test_model_name_sanitized(self):
        """Model slashes/dots should be replaced for directory names."""
        pipeline = SmartImportPipeline({
            "dataset_dir": "/tmp",
            "model": "google/gemini-2.5-flash",
        })
        self.assertEqual(pipeline.model_name, "google-gemini-2-5-flash")

    def test_model_output_dir_under_output(self):
        """Output should be ``{output_dir}/{model_name}``."""
        pipeline = SmartImportPipeline({
            "dataset_dir": "/tmp",
            "output_dir": "/tmp/output",
            "model": "anthropic/claude-sonnet-4.5",
        })
        expected = os.path.join("/tmp/output", "anthropic-claude-sonnet-4-5")
        self.assertEqual(pipeline.model_output_dir, expected)

    def test_default_model_from_env(self):
        """If no model provided, should use env var default."""
        with patch.dict(os.environ, {"DEFAULT_VISION_MODEL": "env-model"}):
            pipeline = SmartImportPipeline({
                "dataset_dir": "/tmp",
            })
            self.assertEqual(pipeline.model, "env-model")

    @patch.dict(os.environ, {}, clear=True)
    def test_fallback_model_when_no_env(self):
        """Without env, should fall back to hardcoded default."""
        pipeline = SmartImportPipeline({
            "dataset_dir": "/tmp",
        })
        self.assertEqual(pipeline.model, "google/gemini-2.5-flash")
        self.assertEqual(pipeline.compiler_model, "google/gemini-2.5-flash-lite")
        self.assertEqual(pipeline.judge_model, "google/gemini-2.5-pro")

    @patch("pipeline.SmartImportCompiler")
    def test_mode_configures_compiler(self, mock_compiler_cls):
        """The pipeline should instantiate the compiler with the selected mode."""
        SmartImportPipeline({
            "dataset_dir": "/tmp",
            "mode": "text_only",
        })
        mock_compiler_cls.assert_called_once_with(mode="text_only")

    def test_default_mode_is_basic_image_layers(self):
        """The default V1 mode should include high-confidence image layers."""
        pipeline = SmartImportPipeline({
            "dataset_dir": "/tmp",
        })
        self.assertEqual(pipeline.mode, "basic_image_layers")


# ---------------------------------------------------------------------------
# Test: _write_json / _read_json helpers
# ---------------------------------------------------------------------------


class TestJsonHelpers(unittest.TestCase):
    """Internal ``_write_json`` and ``_read_json`` helpers."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_write_and_read_json(self):
        from pipeline import _write_json, _read_json

        data = {"key": "value", "nested": {"a": 1}}
        path = os.path.join(self.tmp_dir, "test.json")

        _write_json(path, data)
        self.assertTrue(os.path.isfile(path))

        loaded = _read_json(path)
        self.assertEqual(loaded, data)

    def test_read_json_missing_file(self):
        from pipeline import _read_json
        result = _read_json("/nonexistent/file.json")
        self.assertIsNone(result)

    def test_read_json_invalid_content(self):
        from pipeline import _read_json
        path = os.path.join(self.tmp_dir, "invalid.json")
        with open(path, "w") as f:
            f.write("not json")
        result = _read_json(path)
        self.assertIsNone(result)

    def test_write_json_creates_parent_dirs(self):
        from pipeline import _write_json
        nested = os.path.join(self.tmp_dir, "a", "b", "c", "test.json")
        _write_json(nested, {"ok": True})
        self.assertTrue(os.path.isfile(nested))

    def test_write_json_roundtrip(self):
        from pipeline import _write_json, _read_json
        data = {"scores": [1, 2, 3], "name": "test"}
        path = os.path.join(self.tmp_dir, "roundtrip.json")
        _write_json(path, data)
        loaded = _read_json(path)
        self.assertEqual(loaded, data)


# ---------------------------------------------------------------------------
# Test: SUPPORTED_EXTENSIONS
# ---------------------------------------------------------------------------


class TestSupportedExtensions(unittest.TestCase):
    """The ``SUPPORTED_EXTENSIONS`` set should cover the required formats."""

    def test_contains_jpg_and_jpeg(self):
        self.assertIn(".jpg", SUPPORTED_EXTENSIONS)
        self.assertIn(".jpeg", SUPPORTED_EXTENSIONS)

    def test_contains_png(self):
        self.assertIn(".png", SUPPORTED_EXTENSIONS)

    def test_contains_webp(self):
        self.assertIn(".webp", SUPPORTED_EXTENSIONS)

    def test_contains_gif(self):
        self.assertIn(".gif", SUPPORTED_EXTENSIONS)

    def test_does_not_contain_svg(self):
        self.assertNotIn(".svg", SUPPORTED_EXTENSIONS)

    def test_does_not_contain_txt(self):
        self.assertNotIn(".txt", SUPPORTED_EXTENSIONS)


# ---------------------------------------------------------------------------
# Test: SDK Constants
# ---------------------------------------------------------------------------


class TestSdkConstants(unittest.TestCase):
    """Verify that key constants referenced in the pipeline exist."""

    def test_system_prompt_exists(self):
        from pipeline import SYSTEM_PROMPT_A
        self.assertTrue(len(SYSTEM_PROMPT_A) > 100)
        self.assertIn("Eres un analizador", SYSTEM_PROMPT_A)

    def test_analysis_prompt_exists(self):
        from pipeline import ANALYSIS_PROMPT
        self.assertTrue(len(ANALYSIS_PROMPT) > 50)
        self.assertIn("Analiza esta imagen", ANALYSIS_PROMPT)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
