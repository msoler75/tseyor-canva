"""
ImportJudge — judge model evaluator for the smart import calibration pipeline.

Uses the existing ``OpenRouterClient`` to send both the original and the rendered
image to a multimodal judge model.  Parses and validates the structured score
response.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from openrouter import ChatResponse, OpenRouterClient, OpenRouterError, _encode_image

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_JUDGE_SYSTEM_PROMPT = (
    "You are a quality judge for an automated design import pipeline. "
    "Compare the ORIGINAL image with the IMPORTED RENDER (screenshot of what "
    "the editor produced after importing the auto-generated .tc file)."
)

_JUDGE_EVAL_PROMPT = """Evaluate these dimensions on a scale 0.0 to 1.0:
1. visualSimilarity — Global visual resemblance (layout, proportions, colors)
2. textAccuracy — Are all texts present? Are they correct? (OCR accuracy)
3. layoutAccuracy — Positions, sizes, spacing match the original
4. colorAccuracy — Background, text, and shape colors match
5. editability — Are the important elements editable text layers (not flattened)?

Also list:
- criticalIssues: specific problems that reduce fidelity
- recommendations: actionable improvements for the pipeline

Scene summary for context:
{scene_summary}

Return ONLY valid JSON matching this schema:
{{"overallScore": 0.0-1.0, "visualSimilarity": 0.0-1.0, "textAccuracy": 0.0-1.0, "layoutAccuracy": 0.0-1.0, "colorAccuracy": 0.0-1.0, "editability": 0.0-1.0, "criticalIssues": ["..."], "recommendations": ["..."]}}"""

_REQUIRED_SCORE_KEYS = frozenset({
    "overallScore", "visualSimilarity", "textAccuracy",
    "layoutAccuracy", "colorAccuracy", "editability",
    "criticalIssues", "recommendations",
})

_SCORE_KEYS = frozenset({
    "overallScore", "visualSimilarity", "textAccuracy",
    "layoutAccuracy", "colorAccuracy", "editability",
})


# ---------------------------------------------------------------------------
# ImportJudge
# ---------------------------------------------------------------------------


class ImportJudge:
    """Judge model evaluator for the smart import pipeline.

    Uses a multimodal model (via ``OpenRouterClient``) to compare the original
    source image with the rendered screenshot and produce a structured quality
    score.

    Usage::

        judge = ImportJudge(client)
        score = judge.evaluate("original.png", "render.png", scene, tc_summary)
        print(score["overallScore"])
    """

    def __init__(
        self,
        client: OpenRouterClient,
        model: Optional[str] = None,
    ):
        self.client = client
        self.model = model or os.getenv(
            "JUDGE_MODEL", "google/gemini-2.5-pro"
        )

    # ---------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------

    def evaluate(
        self,
        original_path: str,
        render_path: str,
        scene: dict,
        tc_summary: dict,
    ) -> dict:
        """Compare *original_path* against *render_path* via a judge model.

        Parameters
        ----------
        original_path:
            Filesystem path to the original source image.
        render_path:
            Filesystem path to the rendered screenshot.
        scene:
            The validated SceneGraph dict used for the import.
        tc_summary:
            Summary of the compiled .tc structure (from
            :meth:`_build_tc_summary`).

        Returns
        -------
        dict
            Score dict with keys ``overallScore``, ``visualSimilarity``,
            ``textAccuracy``, ``layoutAccuracy``, ``colorAccuracy``,
            ``editability``, ``criticalIssues``, ``recommendations``.

        Raises
        ------
        OpenRouterError
            If the API call fails or the response cannot be parsed.
        ValueError
            If the parsed score fails validation.
        FileNotFoundError
            If either image path does not exist (raised by ``_encode_image``).
        """
        # Encode both images — raises FileNotFoundError if missing
        original_b64 = _encode_image(original_path)
        render_b64 = _encode_image(render_path)

        # Build the evaluation prompt with scene context
        eval_prompt = self._build_prompt(scene, tc_summary)

        # Build messages with system prompt + both images
        messages = [
            {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": eval_prompt},
                    {"type": "image_url", "image_url": {"url": original_b64}},
                    {"type": "image_url", "image_url": {"url": render_b64}},
                ],
            },
        ]

        # Call the judge model
        response = self.client.chat_completion(
            messages=messages,
            response_format={"type": "json_object"},
            model=self.model,
        )

        if response.status == "error":
            raise OpenRouterError(
                f"Judge evaluation failed: {response.error_message}",
                response_body=response.error_message or "",
            )

        # Parse and validate the score
        score = self._parse_score(response)
        return score

    # ---------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------

    def _build_prompt(self, scene: dict, tc_summary: dict) -> str:
        """Build the judge evaluation prompt with scene context."""
        scene_summary = {
            "canvas": scene.get("canvas", {}),
            "layerCount": len(scene.get("layers", [])),
            "layerTypes": {
                "text": sum(
                    1 for lyr in scene.get("layers", []) if lyr.get("kind") == "text"
                ),
                "image": sum(
                    1 for lyr in scene.get("layers", []) if lyr.get("kind") == "image"
                ),
                "shape": sum(
                    1 for lyr in scene.get("layers", []) if lyr.get("kind") == "shape"
                ),
            },
            "tcSummary": tc_summary,
        }

        return _JUDGE_EVAL_PROMPT.format(
            scene_summary=json.dumps(scene_summary, indent=2)
        )

    @staticmethod
    def _parse_score(response: ChatResponse) -> dict:
        """Extract and validate a score dict from a judge model response.

        Uses ``OpenRouterClient._parse_json_response`` under the hood for
        JSON extraction, then validates the structure and ranges.
        """
        content = response.content.strip()
        if not content:
            raise OpenRouterError(
                "Judge response is empty.",
                response_body="",
            )

        # Try direct JSON parse first, else use the client's flexible parser
        try:
            score = json.loads(content)
        except json.JSONDecodeError:
            score = OpenRouterClient._parse_json_response(content, "judge")

        # Validate required keys
        missing = _REQUIRED_SCORE_KEYS - set(score.keys())
        if missing:
            raise ValueError(
                f"Judge score missing required keys: {sorted(missing)}. "
                f"Got keys: {sorted(score.keys())}"
            )

        # Validate score ranges (0.0 to 1.0)
        for key in _SCORE_KEYS:
            val = score.get(key)
            if not isinstance(val, (int, float)):
                raise ValueError(
                    f"Judge score key '{key}' should be numeric, "
                    f"got {type(val).__name__} ({val!r})"
                )
            if val < 0.0 or val > 1.0:
                raise ValueError(
                    f"Judge score key '{key}'={val} is outside [0.0, 1.0]"
                )

        # Validate list fields
        for key in ("criticalIssues", "recommendations"):
            val = score.get(key)
            if not isinstance(val, list):
                raise ValueError(
                    f"Judge score key '{key}' should be a list, "
                    f"got {type(val).__name__}"
                )

        return score

    @staticmethod
    def _build_tc_summary(tc: dict) -> dict:
        """Build a compact summary of a compiled .tc structure.

        Parameters
        ----------
        tc:
            The compiled .tc dict (output of ``SmartImportCompiler.compile``).

        Returns
        -------
        dict
            Summary with keys ``elementCount``, ``elementIds``, ``layerTypes``,
            ``backgroundKind``, ``designSurface``.
        """
        pages = tc.get("pages", [])
        page = pages[0] if pages else {}

        custom_elements = page.get("customElements", {}) or {}
        element_layout = page.get("elementLayout", {}) or {}

        # Count elements by type
        layer_types: dict[str, int] = {}
        for elem_id, elem in custom_elements.items():
            t = elem.get("type", "unknown")
            layer_types[t] = layer_types.get(t, 0) + 1

        # Determine background kind
        bg = element_layout.get("background", {}) or {}
        if bg.get("fillMode") == "gradient":
            bg_kind = "gradient"
        elif bg.get("backgroundColor") or bg.get("fillMode"):
            bg_kind = "solid"
        else:
            bg_kind = "none"

        return {
            "elementCount": len(custom_elements),
            "elementIds": sorted(custom_elements.keys()),
            "layerTypes": layer_types,
            "backgroundKind": bg_kind,
            "designSurface": tc.get("designSurface", {}),
        }
