"""
Unit tests for ImportJudge.

Tests prompt construction, score parsing (valid JSON, code fences, malformed),
tc_summary builder, edge cases, and full evaluate flow with mocked API.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure the parent directory is on sys.path for imports
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluate import ImportJudge
from openrouter import ChatResponse, OpenRouterClient, OpenRouterError


# ---------------------------------------------------------------------------
# Minimal PNG fixture (1×1 pixel)
# ---------------------------------------------------------------------------

_MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
    b"\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
    b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _make_test_image(path: str) -> None:
    """Write a minimal PNG to *path*."""
    with open(path, "wb") as f:
        f.write(_MINIMAL_PNG)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_VALID_SCORE = {
    "overallScore": 0.82,
    "visualSimilarity": 0.78,
    "textAccuracy": 0.94,
    "layoutAccuracy": 0.81,
    "colorAccuracy": 0.74,
    "editability": 0.86,
    "criticalIssues": ["Text too small"],
    "recommendations": ["Increase font size"],
}

_SAMPLE_SCENE = {
    "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
    "layers": [
        {
            "kind": "text", "id": "layer-1", "confidence": 0.9,
            "bbox": {"x": 0, "y": 0, "w": 100, "h": 50},
            "text": "Hello", "style": {"fontSize": 24},
        },
    ],
}

_SAMPLE_TC_SUMMARY = {"elementCount": 1, "layerTypes": {"text": 1}}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(content: str, status: str = "success") -> ChatResponse:
    """Build a ``ChatResponse`` with given *content*."""
    return ChatResponse(
        content=content,
        model="judge-model",
        usage={"promptTokens": 100, "completionTokens": 20, "totalTokens": 120, "costUsd": 0.001},
        latency_ms=500,
        status=status,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestImportJudgeInit(unittest.TestCase):
    """Construction and model resolution."""

    def test_init_with_client_and_default_model(self):
        client = OpenRouterClient(api_key="sk-or-v1-test")
        judge = ImportJudge(client)
        self.assertIs(judge.client, client)
        self.assertEqual(judge.model, "google/gemini-2.5-pro")

    def test_init_with_custom_model(self):
        client = OpenRouterClient(api_key="sk-or-v1-test")
        judge = ImportJudge(client, model="custom/judge")
        self.assertEqual(judge.model, "custom/judge")

    @patch.dict(os.environ, {"JUDGE_MODEL": "env/judge"}, clear=True)
    def test_init_model_from_env(self):
        client = OpenRouterClient(api_key="sk-or-v1-test")
        judge = ImportJudge(client)
        self.assertEqual(judge.model, "env/judge")


class TestImportJudgeBuildTcSummary(unittest.TestCase):
    """``_build_tc_summary`` helper."""

    def test_empty_tc(self):
        tc = {
            "tcVersion": 2,
            "pages": [{"content": {}, "elementLayout": {}, "customElements": {}}],
        }
        summary = ImportJudge._build_tc_summary(tc)
        self.assertEqual(summary["elementCount"], 0)
        self.assertEqual(summary["elementIds"], [])
        self.assertEqual(summary["layerTypes"], {})
        self.assertEqual(summary["backgroundKind"], "none")

    def test_tc_with_elements(self):
        tc = {
            "tcVersion": 2,
            "designSurface": {"width": 1080, "height": 1350},
            "pages": [
                {
                    "content": {"title": "Hello"},
                    "elementLayout": {
                        "background": {"backgroundColor": "#ffffff", "zIndex": 0},
                        "layer-1": {"x": 0, "y": 0, "w": 100, "h": 50, "zIndex": 1},
                    },
                    "customElements": {
                        "layer-1": {"type": "text", "text": "Hello"},
                        "layer-2": {"type": "image", "src": "data:..."},
                    },
                }
            ],
        }
        summary = ImportJudge._build_tc_summary(tc)
        self.assertEqual(summary["elementCount"], 2)
        self.assertEqual(summary["elementIds"], ["layer-1", "layer-2"])
        self.assertEqual(summary["layerTypes"], {"text": 1, "image": 1})
        self.assertEqual(summary["backgroundKind"], "solid")
        self.assertEqual(summary["designSurface"]["width"], 1080)

    def test_tc_gradient_background(self):
        tc = {
            "tcVersion": 2,
            "pages": [
                {
                    "elementLayout": {
                        "background": {
                            "fillMode": "gradient",
                            "gradientStart": "#000000",
                            "gradientEnd": "#ffffff",
                            "zIndex": 0,
                        }
                    },
                    "customElements": {},
                }
            ],
        }
        summary = ImportJudge._build_tc_summary(tc)
        self.assertEqual(summary["backgroundKind"], "gradient")

    def test_tc_no_background(self):
        tc = {
            "tcVersion": 2,
            "pages": [{"elementLayout": {}, "customElements": {}}],
        }
        summary = ImportJudge._build_tc_summary(tc)
        self.assertEqual(summary["backgroundKind"], "none")


class TestImportJudgeScoreParsing(unittest.TestCase):
    """``_parse_score`` — JSON extraction and validation."""

    def test_parse_valid_json_direct(self):
        response = _make_response(json.dumps(_VALID_SCORE))
        parsed = ImportJudge._parse_score(response)
        self.assertEqual(parsed["overallScore"], 0.82)
        self.assertEqual(parsed["textAccuracy"], 0.94)
        self.assertEqual(parsed["criticalIssues"], ["Text too small"])

    def test_parse_json_from_code_fence(self):
        response = _make_response(
            f"```json\n{json.dumps(_VALID_SCORE)}\n```"
        )
        parsed = ImportJudge._parse_score(response)
        self.assertEqual(parsed["overallScore"], 0.82)

    def test_parse_json_with_extra_text(self):
        response = _make_response(
            f"Here is the evaluation:\n{json.dumps(_VALID_SCORE)}\nEnd."
        )
        parsed = ImportJudge._parse_score(response)
        self.assertEqual(parsed["overallScore"], 0.82)

    def test_missing_required_keys_raises(self):
        incomplete = {"overallScore": 0.5}
        response = _make_response(json.dumps(incomplete))
        with self.assertRaises(ValueError) as ctx:
            ImportJudge._parse_score(response)
        self.assertIn("missing required keys", str(ctx.exception))

    def test_score_out_of_range_raises(self):
        bad = dict(_VALID_SCORE)
        bad["overallScore"] = 1.5
        response = _make_response(json.dumps(bad))
        with self.assertRaises(ValueError) as ctx:
            ImportJudge._parse_score(response)
        self.assertIn("outside [0.0, 1.0]", str(ctx.exception))

    def test_negative_score_raises(self):
        bad = dict(_VALID_SCORE)
        bad["visualSimilarity"] = -0.1
        response = _make_response(json.dumps(bad))
        with self.assertRaises(ValueError) as ctx:
            ImportJudge._parse_score(response)
        self.assertIn("outside [0.0, 1.0]", str(ctx.exception))

    def test_non_numeric_score_raises(self):
        bad = dict(_VALID_SCORE)
        bad["overallScore"] = "high"
        response = _make_response(json.dumps(bad))
        with self.assertRaises(ValueError) as ctx:
            ImportJudge._parse_score(response)
        self.assertIn("should be numeric", str(ctx.exception))

    def test_non_list_issues_raises(self):
        bad = dict(_VALID_SCORE)
        bad["criticalIssues"] = "not a list"
        response = _make_response(json.dumps(bad))
        with self.assertRaises(ValueError) as ctx:
            ImportJudge._parse_score(response)
        self.assertIn("should be a list", str(ctx.exception))

    def test_empty_response_raises(self):
        response = _make_response("")
        with self.assertRaises(OpenRouterError):
            ImportJudge._parse_score(response)

    def test_malformed_json_raises(self):
        response = _make_response("This is not JSON at all")
        with self.assertRaises(OpenRouterError):
            ImportJudge._parse_score(response)

    def test_score_at_boundaries(self):
        """Values exactly at 0.0 and 1.0 must be accepted."""
        boundary = dict(_VALID_SCORE)
        boundary["overallScore"] = 0.0
        boundary["visualSimilarity"] = 1.0
        response = _make_response(json.dumps(boundary))
        parsed = ImportJudge._parse_score(response)
        self.assertEqual(parsed["overallScore"], 0.0)
        self.assertEqual(parsed["visualSimilarity"], 1.0)


class TestImportJudgeEvaluate(unittest.TestCase):
    """Full ``evaluate`` flow with mocked API calls."""

    def setUp(self):
        self.client = OpenRouterClient(api_key="sk-or-v1-test")
        self.judge = ImportJudge(self.client)
        self.tmp_dir = tempfile.mkdtemp()
        self.original_path = os.path.join(self.tmp_dir, "original.png")
        self.render_path = os.path.join(self.tmp_dir, "render.png")
        _make_test_image(self.original_path)
        _make_test_image(self.render_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    @patch("openrouter.OpenRouterClient.chat_completion")
    def test_evaluate_success(self, mock_chat):
        mock_chat.return_value = _make_response(
            json.dumps(_VALID_SCORE)
        )

        result = self.judge.evaluate(
            original_path=self.original_path,
            render_path=self.render_path,
            scene=_SAMPLE_SCENE,
            tc_summary=_SAMPLE_TC_SUMMARY,
        )

        self.assertEqual(result["overallScore"], 0.82)
        self.assertEqual(result["textAccuracy"], 0.94)

        # Verify call structure
        call_args = mock_chat.call_args[1]
        messages = call_args["messages"]
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("quality judge", messages[0]["content"].lower())
        self.assertEqual(messages[1]["role"], "user")

        # Verify images are in the request
        content_blocks = messages[1]["content"]
        self.assertEqual(content_blocks[0]["type"], "text")
        self.assertIn("visualSimilarity", content_blocks[0]["text"])
        self.assertIn("textAccuracy", content_blocks[0]["text"])

        image_blocks = [b for b in content_blocks if b["type"] == "image_url"]
        self.assertEqual(len(image_blocks), 2)
        self.assertIn("base64,", image_blocks[0]["image_url"]["url"])
        self.assertIn("base64,", image_blocks[1]["image_url"]["url"])

        # Verify response_format was passed
        self.assertEqual(
            call_args.get("response_format"), {"type": "json_object"}
        )

        # Verify model override
        self.assertEqual(call_args.get("model"), self.judge.model)

    @patch("openrouter.OpenRouterClient.chat_completion")
    def test_evaluate_api_error_raises(self, mock_chat):
        mock_chat.return_value = _make_response("", status="error")
        mock_chat.return_value.error_message = "API failure"

        with self.assertRaises(OpenRouterError):
            self.judge.evaluate(
                original_path=self.original_path,
                render_path=self.render_path,
                scene=_SAMPLE_SCENE,
                tc_summary=_SAMPLE_TC_SUMMARY,
            )

    def test_evaluate_missing_original_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.judge.evaluate(
                original_path="/nonexistent/original.png",
                render_path=self.render_path,
                scene=_SAMPLE_SCENE,
                tc_summary=_SAMPLE_TC_SUMMARY,
            )

    def test_evaluate_missing_render_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.judge.evaluate(
                original_path=self.original_path,
                render_path="/nonexistent/render.png",
                scene=_SAMPLE_SCENE,
                tc_summary=_SAMPLE_TC_SUMMARY,
            )

    @patch("openrouter.OpenRouterClient.chat_completion")
    def test_evaluate_with_invalid_score_from_api(self, mock_chat):
        """If the API returns an invalid score, validation should catch it."""
        bad_score = dict(_VALID_SCORE)
        bad_score["overallScore"] = 99.9
        mock_chat.return_value = _make_response(json.dumps(bad_score))

        with self.assertRaises(ValueError):
            self.judge.evaluate(
                original_path=self.original_path,
                render_path=self.render_path,
                scene=_SAMPLE_SCENE,
                tc_summary=_SAMPLE_TC_SUMMARY,
            )


class TestImportJudgeBuildPrompt(unittest.TestCase):
    """``_build_prompt`` — prompt construction."""

    def setUp(self):
        self.client = OpenRouterClient(api_key="sk-or-v1-test")
        self.judge = ImportJudge(self.client)

    def test_prompt_contains_all_dimensions(self):
        prompt = self.judge._build_prompt(
            {"canvas": {"width": 1080, "height": 1350}, "layers": []},
            {"elementCount": 0},
        )
        self.assertIn("visualSimilarity", prompt)
        self.assertIn("textAccuracy", prompt)
        self.assertIn("layoutAccuracy", prompt)
        self.assertIn("colorAccuracy", prompt)
        self.assertIn("editability", prompt)
        self.assertIn("criticalIssues", prompt)
        self.assertIn("recommendations", prompt)

    def test_prompt_contains_scene_summary(self):
        prompt = self.judge._build_prompt(
            {
                "canvas": {"width": 1080, "height": 1350},
                "layers": [
                    {"kind": "text", "id": "t1"},
                    {"kind": "image", "id": "i1"},
                ],
            },
            {"elementCount": 2, "layerTypes": {"text": 1}},
        )
        self.assertIn("1080", prompt)
        self.assertIn("layerCount", prompt)
        self.assertIn("layerTypes", prompt)
        self.assertIn("tcSummary", prompt)

    def test_prompt_json_schema_embedded(self):
        """The prompt must contain the expected JSON schema."""
        prompt = self.judge._build_prompt(
            {"canvas": {}, "layers": []}, {}
        )
        # The schema keys should be present
        self.assertIn("overallScore", prompt)
        self.assertIn("criticalIssues", prompt)
        self.assertIn("recommendations", prompt)

    def test_prompt_empty_scene_does_not_crash(self):
        prompt = self.judge._build_prompt({}, {})
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 50)


if __name__ == "__main__":
    unittest.main()
