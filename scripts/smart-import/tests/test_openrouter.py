"""
Unit tests for the OpenRouter client.

Uses ``unittest.mock`` to simulate HTTP responses so no real API calls
are made.  Covers:
- Successful chat completion
- Vision analysis with image encoding
- Image evaluation (two images)
- Retry on 429 (rate-limit)
- Retry on 5xx (server error)
- Max retries exhausted
- JSON parsing from code-fenced responses
- Missing API key
"""

from __future__ import annotations

import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

# Ensure the parent directory is on sys.path for imports
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openrouter import (
    ChatResponse,
    OpenRouterClient,
    OpenRouterError,
    UsageLog,
    _calculate_cost,
    _encode_image,
)


# A minimal PNG (1×1 pixel) encoded as bytes for testing image encoding
_MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n"  # PNG signature
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
    b"\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
    b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestOpenRouterClientInit(unittest.TestCase):
    """Construction and API key resolution."""

    def test_init_with_explicit_key(self):
        client = OpenRouterClient(api_key="sk-or-v1-test")
        self.assertEqual(client.api_key, "sk-or-v1-test")

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-v1-env"}, clear=True)
    def test_init_from_env_var(self):
        client = OpenRouterClient()
        self.assertEqual(client.api_key, "sk-or-v1-env")

    @patch.dict(os.environ, {}, clear=True)
    def test_init_missing_key_raises(self):
        with self.assertRaises(ValueError) as ctx:
            OpenRouterClient()
        self.assertIn("API key", str(ctx.exception))

    def test_init_default_model(self):
        client = OpenRouterClient(api_key="sk-or-v1-test")
        self.assertEqual(client.default_model, "google/gemini-2.5-flash")

    def test_init_custom_model(self):
        client = OpenRouterClient(api_key="sk-or-v1-test", model="custom/model")
        self.assertEqual(client.default_model, "custom/model")

    @patch.dict(os.environ, {"DEFAULT_VISION_MODEL": "env/model"}, clear=True)
    def test_init_model_from_env(self):
        client = OpenRouterClient(api_key="sk-or-v1-test")
        self.assertEqual(client.default_model, "env/model")


class TestOpenRouterChatCompletion(unittest.TestCase):
    """Core ``chat_completion`` method."""

    def setUp(self):
        self.client = OpenRouterClient(api_key="sk-or-v1-test")
        self.sample_response = {
            "id": "chatcmpl-xxx",
            "model": "google/gemini-2.5-flash",
            "choices": [{"message": {"content": '{"hello": "world"}'}}],
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 10,
                "total_tokens": 60,
            },
        }

    @patch("openrouter.requests.Session.post")
    def test_successful_completion(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self.sample_response
        mock_post.return_value = mock_resp

        response = self.client.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
        )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.content, '{"hello": "world"}')
        self.assertEqual(response.usage["promptTokens"], 50)
        self.assertEqual(response.usage["completionTokens"], 10)
        self.assertEqual(response.usage["totalTokens"], 60)
        self.assertGreater(response.usage["costUsd"], 0)
        self.assertGreaterEqual(response.latency_ms, 0)

    @patch("openrouter.requests.Session.post")
    def test_completion_with_response_format(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self.sample_response
        mock_post.return_value = mock_resp

        self.client.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            response_format={"type": "json_object"},
        )

        # Verify the payload includes response_format
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        self.assertEqual(payload["response_format"], {"type": "json_object"})

    @patch("openrouter.requests.Session.post")
    def test_retry_on_429_then_success(self, mock_post):
        """Should retry on rate-limit (429) and succeed on second attempt."""
        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_429.headers = {"Retry-After": "1"}

        resp_ok = MagicMock()
        resp_ok.status_code = 200
        resp_ok.json.return_value = self.sample_response

        mock_post.side_effect = [resp_429, resp_ok]

        response = self.client.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            max_retries=3,
        )

        self.assertEqual(response.status, "success")
        self.assertEqual(mock_post.call_count, 2)

    @patch("openrouter.requests.Session.post")
    def test_retry_on_500_then_success(self, mock_post):
        """Should retry on server error (500) and succeed on second attempt."""
        resp_500 = MagicMock()
        resp_500.status_code = 500

        resp_ok = MagicMock()
        resp_ok.status_code = 200
        resp_ok.json.return_value = self.sample_response

        mock_post.side_effect = [resp_500, resp_ok]

        response = self.client.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            max_retries=3,
        )

        self.assertEqual(response.status, "success")
        self.assertEqual(mock_post.call_count, 2)

    @patch("openrouter.requests.Session.post")
    def test_max_retries_exhausted(self, mock_post):
        """Should return error after exhausting all retries on 5xx."""
        resp_err = MagicMock()
        resp_err.status_code = 503
        resp_err.raise_for_status.side_effect = (
            __import__("requests").HTTPError("Server error")
        )

        mock_post.return_value = resp_err

        response = self.client.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            max_retries=2,
        )

        self.assertEqual(response.status, "error")
        self.assertIsNotNone(response.error_message)
        # Should have tried exactly 2 times
        self.assertEqual(mock_post.call_count, 2)

    @patch("openrouter.requests.Session.post")
    def test_max_retries_exhausted_on_429(self, mock_post):
        """Should retry 3 times on 429 and eventually return error."""
        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_429.headers = {"Retry-After": "1"}

        mock_post.return_value = resp_429

        response = self.client.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            max_retries=3,
        )

        self.assertEqual(response.status, "error")
        self.assertEqual(mock_post.call_count, 3)

    @patch("openrouter.requests.Session.post")
    def test_request_exception_retry(self, mock_post):
        """Should retry on connection errors."""
        mock_post.side_effect = [
            __import__("requests").ConnectionError("Connection reset"),
            __import__("requests").ConnectionError("Connection reset"),
            MagicMock(status_code=200, json=lambda: self.sample_response),
        ]

        response = self.client.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            max_retries=3,
        )

        self.assertEqual(response.status, "success")
        self.assertEqual(mock_post.call_count, 3)


class TestOpenRouterVisionAnalyze(unittest.TestCase):
    """``vision_analyze`` — image encoding + message construction."""

    def setUp(self):
        self.client = OpenRouterClient(api_key="sk-or-v1-test")
        # Create a temporary PNG file for testing
        self.tmp_dir = tempfile.mkdtemp()
        self.test_image = os.path.join(self.tmp_dir, "test.png")
        with open(self.test_image, "wb") as f:
            f.write(_MINIMAL_PNG)

    def tearDown(self):
        os.remove(self.test_image)
        os.rmdir(self.tmp_dir)

    @patch("openrouter.OpenRouterClient.chat_completion")
    def test_vision_analyze_builds_messages(self, mock_chat):
        mock_chat.return_value = ChatResponse(
            content=json.dumps({"detected": "text"}),
            model="gemini-test",
            usage={"promptTokens": 100, "completionTokens": 20, "totalTokens": 120, "costUsd": 0.001},
            latency_ms=500,
            status="success",
        )

        result = self.client.vision_analyze(
            image_path=self.test_image,
            prompt="What do you see?",
            system_prompt="You are a helpful assistant.",
        )

        self.assertEqual(result, {"detected": "text"})

        # Check the message structure
        call_args = mock_chat.call_args[1]
        messages = call_args["messages"]

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], "You are a helpful assistant.")
        self.assertEqual(messages[1]["role"], "user")
        self.assertIsInstance(messages[1]["content"], list)
        self.assertEqual(messages[1]["content"][0]["type"], "text")
        self.assertEqual(messages[1]["content"][0]["text"], "What do you see?")
        self.assertEqual(messages[1]["content"][1]["type"], "image_url")
        self.assertIn("data:image/png;base64,", messages[1]["content"][1]["image_url"]["url"])

    @patch("openrouter.OpenRouterClient.chat_completion")
    def test_vision_analyze_no_system_prompt(self, mock_chat):
        mock_chat.return_value = ChatResponse(
            content=json.dumps({"result": "ok"}),
            model="gemini-test",
            usage={},
            latency_ms=100,
            status="success",
        )

        self.client.vision_analyze(
            image_path=self.test_image,
            prompt="Describe this image.",
        )

        call_args = mock_chat.call_args[1]
        messages = call_args["messages"]
        self.assertEqual(len(messages), 1)  # no system prompt
        self.assertEqual(messages[0]["role"], "user")

    @patch("openrouter.OpenRouterClient.chat_completion")
    def test_vision_analyze_raises_on_error(self, mock_chat):
        mock_chat.return_value = ChatResponse(
            content="",
            model="gemini-test",
            usage={},
            latency_ms=100,
            status="error",
            error_message="API error",
        )

        with self.assertRaises(OpenRouterError):
            self.client.vision_analyze(
                image_path=self.test_image,
                prompt="Describe this image.",
            )

    @patch("openrouter.OpenRouterClient.chat_completion")
    def test_vision_analyze_parses_json_from_fence(self, mock_chat):
        """Should extract JSON from markdown code fences."""
        mock_chat.return_value = ChatResponse(
            content="```json\n{\"result\": \"ok\"}\n```",
            model="gemini-test",
            usage={},
            latency_ms=100,
            status="success",
        )

        result = self.client.vision_analyze(
            image_path=self.test_image,
            prompt="Describe this image.",
        )

        self.assertEqual(result, {"result": "ok"})


class TestOpenRouterEvaluateImages(unittest.TestCase):
    """``evaluate_images`` — two-image judge evaluation."""

    def setUp(self):
        self.client = OpenRouterClient(api_key="sk-or-v1-test")
        self.tmp_dir = tempfile.mkdtemp()
        self.img1 = os.path.join(self.tmp_dir, "original.png")
        self.img2 = os.path.join(self.tmp_dir, "render.png")
        for p in (self.img1, self.img2):
            with open(p, "wb") as f:
                f.write(_MINIMAL_PNG)

    def tearDown(self):
        for p in (self.img1, self.img2):
            if os.path.exists(p):
                os.remove(p)
        os.rmdir(self.tmp_dir)

    @patch("openrouter.OpenRouterClient.chat_completion")
    def test_evaluate_images_builds_correct_messages(self, mock_chat):
        mock_chat.return_value = ChatResponse(
            content=json.dumps({
                "overallScore": 0.85,
                "visualSimilarity": 0.80,
                "textAccuracy": 0.90,
                "layoutAccuracy": 0.85,
                "colorAccuracy": 0.75,
                "editability": 0.95,
                "criticalIssues": [],
                "recommendations": [],
            }),
            model="gemini-test",
            usage={"promptTokens": 200, "completionTokens": 50, "totalTokens": 250, "costUsd": 0.002},
            latency_ms=800,
            status="success",
        )

        scene = {
            "canvas": {"width": 1080, "height": 1350, "detectedFormat": "vertical"},
            "layers": [
                {"kind": "text", "id": "layer-1", "confidence": 0.9, "bbox": {"x": 0, "y": 0, "w": 100, "h": 50}},
            ],
        }

        result = self.client.evaluate_images(
            original_path=self.img1,
            render_path=self.img2,
            scene=scene,
            tc_summary={"elementCount": 3},
        )

        self.assertEqual(result["overallScore"], 0.85)
        self.assertEqual(result["textAccuracy"], 0.90)

        # Verify both images are in the message
        call_args = mock_chat.call_args[1]
        messages = call_args["messages"]
        self.assertEqual(len(messages), 1)
        content_blocks = messages[0]["content"]
        image_urls = [
            b["image_url"]["url"]
            for b in content_blocks
            if b["type"] == "image_url"
        ]
        self.assertEqual(len(image_urls), 2)
        self.assertIn("image/png;base64,", image_urls[0])
        self.assertIn("image/png;base64,", image_urls[1])

    @patch("openrouter.OpenRouterClient.chat_completion")
    def test_evaluate_images_raises_on_error(self, mock_chat):
        mock_chat.return_value = ChatResponse(
            content="",
            model="gemini-test",
            usage={},
            latency_ms=100,
            status="error",
            error_message="API error",
        )

        with self.assertRaises(OpenRouterError):
            self.client.evaluate_images(
                original_path=self.img1,
                render_path=self.img2,
                scene={},
            )


class TestOpenRouterUsageLogging(unittest.TestCase):
    """Usage log accumulation and formatting."""

    def setUp(self):
        self.client = OpenRouterClient(api_key="sk-or-v1-test")

    @patch("openrouter.requests.Session.post")
    def test_usage_log_accumulates(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "x",
            "model": "google/gemini-2.5-flash",
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60},
        }
        mock_post.return_value = mock_resp

        self.client.chat_completion(messages=[{"role": "user", "content": "Hi"}])
        self.client.chat_completion(messages=[{"role": "user", "content": "Hi again"}])

        logs = self.client.get_usage_logs()
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0]["model"], "google/gemini-2.5-flash")
        self.assertEqual(logs[0]["promptTokens"], 50)
        self.assertEqual(logs[0]["completionTokens"], 10)
        self.assertEqual(logs[0]["totalTokens"], 60)
        self.assertGreater(logs[0]["costUsd"], 0)
        self.assertGreaterEqual(logs[0]["latencyMs"], 0)
        self.assertIn("timestamp", logs[0])
        self.assertEqual(logs[0]["status"], "success")

    @patch("openrouter.requests.Session.post")
    def test_usage_log_records_errors(self, mock_post):
        resp_err = MagicMock()
        resp_err.status_code = 503
        resp_err.raise_for_status.side_effect = (
            __import__("requests").HTTPError("Server error")
        )
        mock_post.return_value = resp_err

        self.client.chat_completion(messages=[{"role": "user", "content": "Hi"}], max_retries=1)

        logs = self.client.get_usage_logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["status"], "error")
        self.assertIsNotNone(logs[0]["errorMessage"])

    @patch("openrouter.requests.Session.post")
    def test_save_usage_log(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "x",
            "model": "test-model",
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        mock_post.return_value = mock_resp

        self.client.chat_completion(messages=[{"role": "user", "content": "Hi"}])

        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "openrouter.json")
            self.client.save_usage_log(log_path)

            with open(log_path) as f:
                data = json.load(f)

            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["status"], "success")


class TestUtilityFunctions(unittest.TestCase):
    """Standalone utility functions."""

    def test_calculate_cost_default(self):
        cost = _calculate_cost("unknown-model", 1000, 500)
        # 1000/1000 * 0.001 + 500/1000 * 0.002 = 0.001 + 0.001 = 0.002
        self.assertAlmostEqual(cost, 0.002)

    def test_calculate_cost_gemini_flash(self):
        cost = _calculate_cost("google/gemini-2.5-flash", 1000, 500)
        # 1000/1000 * 0.000075 + 500/1000 * 0.0003 = 0.000075 + 0.00015 = 0.000225
        self.assertAlmostEqual(cost, 0.000225)

    def test_calculate_cost_zero_tokens(self):
        cost = _calculate_cost("google/gemini-2.5-flash", 0, 0)
        self.assertEqual(cost, 0.0)

    def test_encode_image(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(_MINIMAL_PNG)
            tmp_path = f.name

        try:
            data_uri = _encode_image(tmp_path)
            self.assertTrue(data_uri.startswith("data:image/png;base64,"))
            # Should be valid base64 after the comma
            b64_part = data_uri.split(",", 1)[1]
            decoded = base64.b64decode(b64_part)
            self.assertEqual(decoded, _MINIMAL_PNG)
        finally:
            os.unlink(tmp_path)

    def test_encode_image_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            _encode_image("/nonexistent/image.png")


class TestUsageLogDataclass(unittest.TestCase):
    """UsageLog serialization matches the openrouter.json format."""

    def test_to_dict_keys(self):
        log = UsageLog(
            model="test-model",
            prompt_tokens=100,
            completion_tokens=20,
            total_tokens=120,
            cost_usd=0.001,
            latency_ms=500,
            timestamp="2025-01-01T00:00:00",
            status="success",
            error_message=None,
        )
        d = log.to_dict()
        self.assertEqual(d["model"], "test-model")
        self.assertEqual(d["promptTokens"], 100)
        self.assertEqual(d["completionTokens"], 20)
        self.assertEqual(d["totalTokens"], 120)
        self.assertEqual(d["costUsd"], 0.001)
        self.assertEqual(d["latencyMs"], 500)
        self.assertEqual(d["timestamp"], "2025-01-01T00:00:00")
        self.assertEqual(d["status"], "success")
        self.assertIsNone(d["errorMessage"])
        # Verify camelCase keys
        self.assertIn("promptTokens", d)
        self.assertIn("completionTokens", d)
        self.assertNotIn("prompt_tokens", d)


class TestJSONParsing(unittest.TestCase):
    """``_parse_json_response`` edge cases."""

    def setUp(self):
        self.client = OpenRouterClient(api_key="sk-or-v1-test")

    def test_direct_json(self):
        result = self.client._parse_json_response('{"key": "value"}')
        self.assertEqual(result, {"key": "value"})

    def test_code_fenced_json(self):
        result = self.client._parse_json_response(
            'Here is your JSON:\n```json\n{"key": "value"}\n```'
        )
        self.assertEqual(result, {"key": "value"})

    def test_code_fenced_without_lang(self):
        result = self.client._parse_json_response(
            '```\n{"key": "value"}\n```'
        )
        self.assertEqual(result, {"key": "value"})

    def test_braces_in_text(self):
        result = self.client._parse_json_response(
            'The result is {"score": 0.95, "valid": true}.'
        )
        self.assertEqual(result, {"score": 0.95, "valid": True})

    def test_raises_on_invalid(self):
        with self.assertRaises(OpenRouterError):
            self.client._parse_json_response("This is not JSON at all")

    def test_raises_on_empty(self):
        with self.assertRaises(OpenRouterError):
            self.client._parse_json_response("")


if __name__ == "__main__":
    unittest.main()
