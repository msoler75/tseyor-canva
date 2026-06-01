"""
OpenRouter client for chat completions, vision analysis, and image evaluation.

Uses the ``requests`` library (not the OpenAI SDK) for full control over
OpenRouter-specific parameters.  Implements retry with exponential backoff
(3 attempts on 429/5xx), usage logging with cost calculation, and automatic
loading of ``.env`` from ``scripts/smart-import/.env``.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from the same directory this file lives in
# ---------------------------------------------------------------------------
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model pricing (USD per 1K tokens)
# Source: OpenRouter pricing page — review/update before production runs.
# ---------------------------------------------------------------------------
MODEL_PRICING: dict[str, dict[str, float]] = {
    "google/gemini-2.5-flash":         {"input": 0.000_075, "output": 0.000_30},
    "google/gemini-2.5-flash-lite":    {"input": 0.000_030, "output": 0.000_15},
    "google/gemini-2.5-pro":           {"input": 0.001_25,  "output": 0.005_00},
    "anthropic/claude-sonnet-4.5":     {"input": 0.003_00,  "output": 0.015_00},
    # Fallback for unknown models
    "default":                         {"input": 0.001_00,  "output": 0.002_00},
}

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class ChatResponse:
    """Structured response from an OpenRouter chat completion call."""
    content: str
    model: str
    usage: dict = field(default_factory=dict)
    latency_ms: int = 0
    status: str = "success"
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class UsageLog:
    """Log entry for a single API call — matches the openrouter.json format."""
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    timestamp: str = ""
    status: str = "success"
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "promptTokens": self.prompt_tokens,
            "completionTokens": self.completion_tokens,
            "totalTokens": self.total_tokens,
            "costUsd": self.cost_usd,
            "latencyMs": self.latency_ms,
            "timestamp": self.timestamp,
            "status": self.status,
            "errorMessage": self.error_message,
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate USD cost from token counts using *MODEL_PRICING*."""
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
    input_cost = (prompt_tokens / 1000.0) * pricing["input"]
    output_cost = (completion_tokens / 1000.0) * pricing["output"]
    return round(input_cost + output_cost, 8)


def _encode_image(image_path: str) -> str:
    """Read an image file and return it as a base64 data URI.

    Supported extensions: png, jpg/jpeg, webp, gif.
    Raises ``FileNotFoundError`` if the path does not exist.
    """
    with open(image_path, "rb") as f:
        data = f.read()

    ext = os.path.splitext(image_path)[1].lower().lstrip(".")
    mime_map = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "gif": "image/gif",
    }
    mime = mime_map.get(ext, "image/png")
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{b64}"


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class OpenRouterError(Exception):
    """Raised when the OpenRouter API returns an error or response parsing fails."""

    def __init__(self, message: str, status_code: int = 0, response_body: str = ""):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class OpenRouterClient:
    """Client for the OpenRouter ``/chat/completions`` endpoint.

    Usage::

        client = OpenRouterClient()
        resp = client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            response_format={"type": "json_object"},
        )
        print(resp.content)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = (
            base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        ).rstrip("/")
        self.default_model = model or os.getenv("DEFAULT_VISION_MODEL", "google/gemini-2.5-flash")

        if not self.api_key:
            raise ValueError(
                "OpenRouter API key not provided. "
                "Set OPENROUTER_API_KEY env var or pass it to __init__()."
            )

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://tseyor.com",
        })

        # Accumulated usage logs for this client instance
        self.usage_logs: list[UsageLog] = []
        # Full conversation logs (messages sent + response received)
        self.conversation_logs: list[dict] = []

    # ---------------------------------------------------------------
    # Core method
    # ---------------------------------------------------------------

    def chat_completion(
        self,
        messages: list[dict],
        response_format: Optional[dict] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
    ) -> ChatResponse:
        """Send a chat completion request with retry + usage logging.

        Parameters
        ----------
        messages:
            Standard OpenAI-format message list.
        response_format:
            Optional ``{"type": "json_object"}`` or a JSON Schema.
        model:
            Override the default model for this call.
        max_retries:
            Number of retries on 429 / 5xx errors (default 3).

        Returns
        -------
        ChatResponse with parsed content, usage, latency, and status.
        """
        model_name = model or self.default_model
        payload: dict = {
            "model": model_name,
            "messages": messages,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        url = urljoin(self.base_url + "/", "chat/completions")
        last_error: Optional[str] = None
        response_data: Optional[dict] = None
        latency_ms = 0

        for attempt in range(max_retries):
            start_time = time.monotonic()
            try:
                resp = self.session.post(url, json=payload, timeout=120)
                latency_ms = int((time.monotonic() - start_time) * 1000)

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 2**attempt))
                    logger.warning(
                        "Rate limited (429). Retrying in %ss (attempt %d/%d)",
                        retry_after, attempt + 1, max_retries,
                    )
                    time.sleep(retry_after)
                    continue

                if 500 <= resp.status_code < 600:
                    logger.warning(
                        "Server error %s. Retrying in %ss (attempt %d/%d)",
                        resp.status_code, 2**attempt, attempt + 1, max_retries,
                    )
                    time.sleep(2**attempt)
                    continue

                resp.raise_for_status()
                response_data = resp.json()
                last_error = None
                break  # success

            except requests.RequestException as exc:
                latency_ms = int((time.monotonic() - start_time) * 1000)
                last_error = str(exc)
                if attempt < max_retries - 1:
                    sleep_time = 2**attempt
                    logger.warning(
                        "Request failed: %s. Retrying in %ss (attempt %d/%d)",
                        exc, sleep_time, attempt + 1, max_retries,
                    )
                    time.sleep(sleep_time)
                # else — fall through to error response below

        # --- Build response ---
        if response_data is not None:
            choice = response_data["choices"][0]
            content = choice["message"]["content"].strip()

            usage_data = response_data.get("usage", {})
            pt = usage_data.get("prompt_tokens", 0) or 0
            ct = usage_data.get("completion_tokens", 0) or 0
            tt = usage_data.get("total_tokens", 0) or 0

            cost = _calculate_cost(model_name, pt, ct)

            usage = {
                "promptTokens": pt,
                "completionTokens": ct,
                "totalTokens": tt,
                "costUsd": cost,
            }

            chat_resp = ChatResponse(
                content=content,
                model=response_data.get("model", model_name),
                usage=usage,
                latency_ms=latency_ms,
                status="success",
            )
        else:
            chat_resp = ChatResponse(
                content="",
                model=model_name,
                usage={},
                latency_ms=latency_ms,
                status="error",
                error_message=last_error or "Max retries exceeded",
            )

        # --- Log usage ---
        self._log_usage(chat_resp)
        # --- Log conversation (messages + response) ---
        self._log_conversation(messages, chat_resp)
        return chat_resp

    # ---------------------------------------------------------------
    # High-level methods
    # ---------------------------------------------------------------

    def vision_analyze(
        self,
        image_path: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
    ) -> dict:
        """Analyse an image with a vision model and return the parsed JSON result.

        The image is encoded as a base64 data URI and sent inside the
        message content array alongside the text prompt.

        Parameters
        ----------
        image_path:
            Filesystem path to the image file.
        prompt:
            User message text instructing the model what to extract.
        system_prompt:
            Optional system-level instruction.
        model:
            Override model (defaults to ``DEFAULT_VISION_MODEL``).

        Returns
        -------
        Parsed JSON dictionary from the model response.

        Raises
        ------
        OpenRouterError
            If the API call fails or the response cannot be parsed as JSON.
        """
        image_data_uri = _encode_image(image_path)

        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_data_uri}},
            ],
        })

        response = self.chat_completion(
            messages=messages,
            response_format={"type": "json_object"},
            model=model,
        )

        if response.status == "error":
            raise OpenRouterError(
                f"Vision analysis failed: {response.error_message}",
                response_body=response.error_message or "",
            )

        return self._parse_json_response(response.content, "vision")

    def evaluate_images(
        self,
        original_path: str,
        render_path: str,
        scene: dict,
        tc_summary: Optional[dict] = None,
        model: Optional[str] = None,
    ) -> dict:
        """Send original + rendered images to a judge model for quality evaluation.

        Parameters
        ----------
        original_path:
            Filesystem path to the original source image.
        render_path:
            Filesystem path to the rendered screenshot.
        scene:
            The SceneGraph dict used for the import.
        tc_summary:
            Optional extra summary of the compiled .tc structure.
        model:
            Judge model override (defaults to ``DEFAULT_VISION_MODEL``).

        Returns
        -------
        Parsed JSON score dict with keys like ``overallScore``,
        ``visualSimilarity``, ``textAccuracy``, etc.
        """
        original_b64 = _encode_image(original_path)
        render_b64 = _encode_image(render_path)

        # Build a compact scene summary for the judge
        layers = scene.get("layers", [])
        scene_summary = {
            "canvas": scene.get("canvas", {}),
            "layerCount": len(layers),
            "layerTypes": {
                "text": sum(1 for l in layers if l.get("kind") == "text"),
                "image": sum(1 for l in layers if l.get("kind") == "image"),
                "shape": sum(1 for l in layers if l.get("kind") == "shape"),
            },
        }
        if tc_summary:
            scene_summary["tcSummary"] = tc_summary

        judge_prompt = (
            "Compare the ORIGINAL IMAGE with the IMPORTED RENDER (a screenshot of the editor after "
            "importing the auto-generated .tc file).\n\n"
            "Evaluate:\n"
            "1. Visual similarity overall (colors, layout, proportions)\n"
            "2. Text accuracy (OCR: are all texts present and correct?)\n"
            "3. Layout accuracy (positions, sizes, spacing)\n"
            "4. Color accuracy (background, text, shapes)\n"
            "5. Editability (texts are editable layers, not flat image)\n\n"
            f"Scene summary for context:\n{json.dumps(scene_summary, indent=2)}\n\n"
            "Return ONLY valid JSON with scores 0..1 and lists of critical issues and recommendations "
            "using EXACTLY this schema:\n"
            '{\n'
            '  "overallScore": 0.85,\n'
            '  "visualSimilarity": 0.80,\n'
            '  "textAccuracy": 0.90,\n'
            '  "layoutAccuracy": 0.85,\n'
            '  "colorAccuracy": 0.75,\n'
            '  "editability": 0.95,\n'
            '  "criticalIssues": ["Text layer x missing"],\n'
            '  "recommendations": ["Increase font size for readability"]\n'
            '}'
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": judge_prompt},
                    {"type": "image_url", "image_url": {"url": original_b64}},
                    {"type": "image_url", "image_url": {"url": render_b64}},
                ],
            }
        ]

        response = self.chat_completion(
            messages=messages,
            response_format={"type": "json_object"},
            model=model,
        )

        if response.status == "error":
            raise OpenRouterError(
                f"Image evaluation failed: {response.error_message}",
                response_body=response.error_message or "",
            )

        return self._parse_json_response(response.content, "evaluation")

    # ---------------------------------------------------------------
    # Usage log helpers
    # ---------------------------------------------------------------

    def _log_usage(self, response: ChatResponse) -> None:
        """Record a usage log entry for the given response."""
        usage = response.usage or {}
        log_entry = UsageLog(
            model=response.model,
            prompt_tokens=usage.get("promptTokens", 0),
            completion_tokens=usage.get("completionTokens", 0),
            total_tokens=usage.get("totalTokens", 0),
            cost_usd=usage.get("costUsd", 0.0),
            latency_ms=response.latency_ms,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=response.status,
            error_message=response.error_message,
        )
        self.usage_logs.append(log_entry)

    def get_usage_logs(self) -> list[dict]:
        """Return all accumulated usage logs as plain dicts."""
        return [log.to_dict() for log in self.usage_logs]

    def save_usage_log(self, path: str) -> None:
        """Write all accumulated usage logs to a JSON file (openrouter.json format)."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.get_usage_logs(), f, indent=2, ensure_ascii=False)

    # ---------------------------------------------------------------
    # Conversation log helpers
    # ---------------------------------------------------------------

    def _log_conversation(self, messages: list[dict], response: ChatResponse) -> None:
        """Record the full request messages and response content."""
        conv = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": response.model,
            "status": response.status,
            "latency_ms": response.latency_ms,
            "request": {
                "messages": _truncate_conversation(messages),
            },
            "response": {
                "content": response.content if response.status == "success" else None,
                "error": response.error_message,
            },
        }
        self.conversation_logs.append(conv)

    def get_conversation_logs(self) -> list[dict]:
        return list(self.conversation_logs)

    def save_conversation_log(self, path: str) -> None:
        """Write all accumulated conversation logs to a JSON file."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.get_conversation_logs(), f, indent=2, ensure_ascii=False)

    # ---------------------------------------------------------------
    # Internal JSON extraction
    # ---------------------------------------------------------------

    @staticmethod
    def _parse_json_response(content: str, context: str = "response") -> dict:
        """Extract and parse a JSON object from *content*.

        Tries ``json.loads`` directly first; if that fails, looks for a
        code-fenced or bare JSON block in the text.
        """
        # Direct parse
        content = content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try fenced code block
        match = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL
        )
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try to find a JSON-like object with { ... }
        brace_match = re.search(r"(\{.*\})", content, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(1))
            except json.JSONDecodeError:
                pass

        raise OpenRouterError(
            f"Failed to parse JSON from {context} response. "
            f"Content starts with: {content[:300]}"
        )


def _truncate_conversation(messages: list[dict]) -> list[dict]:
    """Return a copy of messages with image data URIs truncated for readability."""
    truncated = []
    for msg in messages:
        t_msg = {"role": msg.get("role")}
        content = msg.get("content")
        if isinstance(content, str):
            t_msg["content"] = content
        elif isinstance(content, list):
            t_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    url = part.get("image_url", {}).get("url", "")
                    if url.startswith("data:image/"):
                        t_parts.append({"type": "image_url", "image_url": {"url": f"data:image/...;base64,<TRUNCATED ({len(url)} chars)>"}})
                    else:
                        t_parts.append(part)
                else:
                    t_parts.append(part)
            t_msg["content"] = t_parts
        else:
            t_msg["content"] = content
        truncated.append(t_msg)
    return truncated
