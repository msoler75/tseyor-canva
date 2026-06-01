"""
SmartImportPipeline -- main orchestrator for the smart import calibration pipeline.

Iterates images from a dataset, runs OpenRouter analysis, validates SceneGraphs,
compiles them to .tc v2, optionally renders via Playwright (``tc_render.js``),
optionally evaluates quality via a judge model, and generates a report.

Usage::

    python scripts/smart-import/pipeline.py \\
        --dataset scripts/smart-import/dataset/ \\
        --model google/gemini-2.5-flash \\
        --output scripts/smart-import/output/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

from compiler import SmartImportCompiler
from evaluate import ImportJudge
from openrouter import OpenRouterClient, OpenRouterError
from report import generate_report
from scene_evaluator import evaluate_scene_graph
from tc_evaluator import evaluate_tc_fidelity
from validator import validate_scene

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
SUPPORTED_MODES = {"text_only", "basic_image_layers"}
PIPELINE_VERSION = "1.0.0"
CACHE_PHASE_FILES = {
    "scene": "scene.json",
    "scene_fixed": "scene-fixed.json",
    "tc": "design.tc",
    "score": "score.json",
}

SYSTEM_PROMPT_A: str = (
    "Eres un analizador de composición gráfica especializado en extraer "
    "SceneGraphs de imágenes de diseño (carteles, flyers, banners, posts "
    "y cualquier pieza gráfica publicitaria). "
    "Debes analizar la imagen y devolver un JSON que describa su estructura "
    "visual siguiendo el schema SceneGraph v1 exactamente. "
    "No inventes campos fuera del schema; respeta los tipos y nombres "
    "definidos.\n\n"
    "Estructura requerida:\n"
    "- canvas: { width (px), height (px), detectedFormat: 'vertical'|'horizontal'|'square' }\n"
    "- background: { kind: 'solid'|'gradient'|'image', color: hex, confidence: 0..1, "
    "gradient?: { type, angle, stops: [{ color, position }] } }\n"
    "- layers: array de objetos con:\n"
    "  * id: string único ('layer-1', 'layer-2', ...)\n"
    "  * kind: 'text' | 'image' | 'shape'\n"
    "  * confidence: 0..1\n"
    "  * bbox: { x, y, w, h } en píxeles\n"
    "  * text: (obligatorio si kind=text) el texto exacto\n"
    "  * style: (para text) { fontSize, fontWeight, color, textAlign }\n"
    "  * description: (para image) descripción breve\n"
    "  * cropFromSource: bool (para image)\n"
    "  * shape: (para shape) 'rectangle'|'circle'|'ellipse'\n"
    "  * shapeStyle: (para shape) { fill, opacity, borderRadius }\n"
    "- warnings: string[]\n\n"
    "IMPORTANTE: Devuelve SOLO el JSON válido, sin explicaciones ni "
    "markdown fences."
)

ANALYSIS_PROMPT: str = (
    "Analiza esta imagen de diseño y extrae su estructura como SceneGraph JSON. "
    "Identifica el canvas, el fondo, y cada capa visual (texto, imagen, forma). "
    "Para cada capa proporciona bounding box preciso, tipo, contenido textual "
    "completo, estilos y nivel de confianza. "
    "Devuelve SOLO el JSON."
)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class Result:
    """Result of processing a single image through the full pipeline."""

    image_id: str = ""
    model: str = ""
    paths: dict = field(default_factory=dict)
    score: Optional[dict] = None
    scene_score: Optional[dict] = None
    tc_score: Optional[dict] = None
    cost_usd: float = 0.0
    latency_ms: int = 0
    status: str = "success"
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict = {
            "imageId": self.image_id,
            "model": self.model,
            "paths": self.paths,
            "score": self.score,
            "sceneScore": self.scene_score,
            "tcScore": self.tc_score,
            "costUsd": self.cost_usd,
            "latencyMs": self.latency_ms,
            "status": self.status,
            "errorMessage": self.error_message,
        }
        return d


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _write_json(path: str, data: dict) -> None:
    """Write a dict to a JSON file, creating parent directories."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _read_json(path: str) -> Optional[dict]:
    """Read a JSON file, returning *None* if missing or invalid."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class SmartImportPipeline:
    """Main pipeline orchestrator.

    Usage::

        pipeline = SmartImportPipeline({
            "dataset_dir": "scripts/smart-import/dataset/",
            "model": "google/gemini-2.5-flash",
            "output_dir": "scripts/smart-import/output/",
        })
        results = pipeline.run()
    """

    def __init__(self, config: dict):
        self.dataset_dir: str = config["dataset_dir"]
        self.model: str = config.get(
            "model",
            os.getenv("DEFAULT_VISION_MODEL", "google/gemini-2.5-flash"),
        )
        self.compiler_model: str = config.get(
            "compiler_model",
            os.getenv("DEFAULT_COMPILER_MODEL", "google/gemini-2.5-flash-lite"),
        )
        self.judge_model: str = config.get(
            "judge_model",
            os.getenv("JUDGE_MODEL", "google/gemini-2.5-pro"),
        )
        self.output_dir: str = config.get(
            "output_dir", "scripts/smart-import/output"
        )
        self.mode: str = config.get("mode", "basic_image_layers")
        if self.mode not in SUPPORTED_MODES:
            raise ValueError(
                f"Unsupported Smart Import mode: {self.mode}. "
                f"Expected one of: {', '.join(sorted(SUPPORTED_MODES))}"
            )
        self.pipeline_version: str = config.get(
            "pipeline_version", PIPELINE_VERSION
        )
        self.skip_analysis: bool = config.get("skip_analysis", False)
        self.skip_render: bool = config.get("skip_render", False)
        self.skip_eval: bool = config.get("skip_eval", False)

        # Derive a safe directory name from the model string
        self.model_name: str = self.model.replace("/", "-").replace(".", "-")
        self.model_output_dir: str = os.path.join(
            self.output_dir, self.model_name
        )
        self.cache_dir: str = config.get(
            "cache_dir", os.path.join(self.output_dir, ".cache")
        )

        # Instantiate components
        self.client = OpenRouterClient(model=self.model)
        self.compiler = SmartImportCompiler(mode=self.mode)
        self.judge = ImportJudge(client=self.client, model=self.judge_model)

        # Path of *this* script, used to locate sibling modules (tc_render.js)
        self._script_dir: str = os.path.dirname(os.path.abspath(__file__))

    # ---------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------

    def run(
        self, filter_image: Optional[str] = None
    ) -> list[Result]:
        """Run the full pipeline over images in the dataset.

        Parameters
        ----------
        filter_image:
            Optional image ID (filename stem) to process a single image.
            When *None* every supported image in the dataset is processed.

        Returns
        -------
        list[Result]
            One result per image.
        """
        image_paths = self._find_images(filter_image)

        if not image_paths:
            logger.warning(
                "No images found in %s (filter=%s)",
                self.dataset_dir, filter_image,
            )
            return []

        logger.info(
            "Pipeline started — %d images, model=%s, mode=%s, output=%s",
            len(image_paths), self.model_name, self.mode, self.model_output_dir,
        )
        os.makedirs(self.model_output_dir, exist_ok=True)

        results: list[Result] = []
        total = len(image_paths)

        for idx, (image_id, image_path) in enumerate(image_paths, start=1):
            logger.info(
                "Processing %s/%d (%s)...",
                image_id, total, os.path.basename(image_path),
            )

            result = self._process_single(image_id, image_path)
            results.append(result)

            if result.status == "success":
                score_str = (
                    f"{result.score.get('overallScore', 'N/A'):.4f}"
                    if result.score and result.score.get("overallScore") is not None
                    else "N/A"
                )
                logger.info(
                    "  [OK] Done — score=%s, cost=$%.6f, latency=%dms",
                    score_str, result.cost_usd, result.latency_ms,
                )
            else:
                logger.warning(
                    "  [FAIL] %s", result.error_message,
                )

        # --- Generate report ---
        logger.info("Generating report...")
        report_dicts = [r.to_dict() for r in results]
        try:
            generate_report(report_dicts, self.output_dir)
        except Exception as exc:
            logger.error("Report generation failed: %s", exc)

        self._print_summary(results)
        return results

    # ---------------------------------------------------------------
    # Image discovery
    # ---------------------------------------------------------------

    def _find_images(
        self, filter_image: Optional[str] = None
    ) -> list[tuple[str, str]]:
        """Scan *dataset_dir* for supported image files.

        Returns ``[(stem, full_path), ...]`` sorted alphabetically.
        When *filter_image* is provided only entries whose stem matches
        exactly are returned.
        """
        if not os.path.isdir(self.dataset_dir):
            logger.warning("Dataset directory not found: %s", self.dataset_dir)
            return []

        images: list[tuple[str, str]] = []
        for fname in sorted(os.listdir(self.dataset_dir)):
            ext = os.path.splitext(fname)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                stem = os.path.splitext(fname)[0]
                if filter_image is not None and stem != filter_image:
                    continue
                images.append((stem, os.path.join(self.dataset_dir, fname)))

        return images

    # ---------------------------------------------------------------
    # Single-image processing
    # ---------------------------------------------------------------

    def _process_single(self, image_id: str, image_path: str) -> Result:
        """Run the four pipeline phases for one image.

        Each phase is independent -- a failure in one does not prevent
        later phases from executing (but may influence their input).
        All exceptions are caught so the caller's iteration continues.
        """
        image_dir = os.path.join(self.model_output_dir, image_id)
        os.makedirs(image_dir, exist_ok=True)

        paths: dict = {
            "image": image_path,
            "scene": os.path.join(image_dir, "scene.json"),
            "scene_fixed": os.path.join(image_dir, "scene-fixed.json"),
            "tc": os.path.join(image_dir, "design.tc"),
            "render": os.path.join(image_dir, "render.png"),
            "score": os.path.join(image_dir, "score.json"),
            "scene_score": os.path.join(image_dir, "scene-score.json"),
            "tc_score": os.path.join(image_dir, "tc-score.json"),
            "openrouter": os.path.join(image_dir, "openrouter.json"),
        }

        result = Result(
            image_id=image_id,
            model=self.model_name,
            paths=paths,
        )

        start_time = time.monotonic()
        usage_count_before = len(self.client.usage_logs)
        analysis_cache_key = self._cache_key(
            image_path, model_id=f"{self.model}:{self.mode}"
        )
        score_cache_key = self._cache_key(
            image_path,
            model_id=f"{self.model}:{self.mode}:{self.judge_model}",
        )

        # ---- Phase 1: Analyse (vision model → SceneGraph) ----
        raw_scene: Optional[dict] = None
        fixed_scene: Optional[dict] = None

        try:
            cached_raw_scene = self._load_from_cache(analysis_cache_key, "scene")
            cached_fixed_scene = self._load_from_cache(
                analysis_cache_key, "scene_fixed"
            )

            if cached_raw_scene is not None:
                raw_scene = cached_raw_scene
                fixed_scene = cached_fixed_scene
                logger.info("  Analyze... (hash cache)")
            elif self.skip_analysis:
                cached = self._load_cached_scene(image_dir)
                if cached is not None:
                    raw_scene, fixed_scene = cached
                    logger.info("  Analyze... (local cache)")
                else:
                    logger.warning(
                        "  Analyze... (no cache found, using empty scene)"
                    )
            else:
                logger.info("  Analyze...")
                raw_scene = self.client.vision_analyze(
                    image_path=image_path,
                    prompt=ANALYSIS_PROMPT,
                    system_prompt=SYSTEM_PROMPT_A,
                    model=self.model,
                )
                _write_json(paths["scene"], raw_scene)
                self._save_to_cache(analysis_cache_key, "scene", raw_scene)

            # Validate & fix the scene
            if fixed_scene is not None:
                if raw_scene is not None and not os.path.isfile(paths["scene"]):
                    _write_json(paths["scene"], raw_scene)
                _write_json(paths["scene_fixed"], fixed_scene)
            elif raw_scene is not None:
                validation = validate_scene(raw_scene, mode=self.mode)
                fixed_scene = validation.fixed
                _write_json(paths["scene_fixed"], fixed_scene)
                self._save_to_cache(analysis_cache_key, "scene_fixed", fixed_scene)

                if not validation.valid:
                    logger.warning(
                        "  Scene validation errors: %s", validation.errors,
                    )
                if validation.warnings:
                    for w in validation.warnings:
                        logger.info("  Scene warning: %s", w)

            # Persist usage logs + conversation logs for this image
            self._save_image_usage_log(paths["openrouter"], usage_count_before)
            self._save_image_conversation_log(
                os.path.join(image_dir, "conversation.json"),
                usage_count_before,
            )

        except OpenRouterError as exc:
            logger.error("  Analyze failed: %s", exc)
            raw_scene = None
            fixed_scene = None
        except Exception as exc:
            logger.error("  Analyze unexpected error: %s", exc)
            raw_scene = None
            fixed_scene = None

        # ---- SceneGraph Evaluation (Level 1) ----
        scene_score: Optional[dict] = None
        try:
            logger.info("  SceneGraph eval...")
            scene_score = evaluate_scene_graph(fixed_scene, image_id)
        except Exception as exc:
            logger.warning("  SceneGraph eval failed: %s", exc)
            scene_score = {"overallScore": 0.0, "detail": {"reason": str(exc)}}
        if scene_score is not None:
            _write_json(paths.get("scene_score", os.path.join(image_dir, "scene-score.json")), scene_score)

        # ---- Phase 2: Compile (SceneGraph → .tc) ----
        tc: Optional[dict] = None
        try:
            logger.info("  Compile...")
            if fixed_scene is None:
                # Build a minimal empty scene so the pipeline can continue
                fixed_scene = {
                    "canvas": {
                        "width": 1080,
                        "height": 1350,
                        "detectedFormat": "vertical",
                    },
                    "layers": [],
                }

            cached_tc = self._load_from_cache(analysis_cache_key, "tc")
            if cached_tc is not None:
                tc = cached_tc
                logger.info("  Compile... (hash cache)")
            else:
                tc = self.compiler.compile(fixed_scene, image_path)
                self._save_to_cache(analysis_cache_key, "tc", tc)
            self.compiler.export(tc, paths["tc"])
        except Exception as exc:
            logger.error("  Compile failed: %s", exc)
            # Attempt a minimal .tc so downstream phases can still run
            if tc is None:
                tc = {
                    "tcVersion": 2,
                    "designSurface": {"width": 1080, "height": 1350},
                    "format": "vertical",
                    "size": "1080 × 1350 px",
                    "pages": [
                        {
                            "id": "smart-page-1",
                            "content": {},
                            "elementLayout": {},
                            "customElements": {},
                        }
                    ],
                }
                try:
                    self.compiler.export(tc, paths["tc"])
                    self._save_to_cache(analysis_cache_key, "tc", tc)
                except Exception:
                    pass

        # ---- TC Fidelity Evaluation (Level 2) ----
        tc_score: Optional[dict] = None
        try:
            tc_score = evaluate_tc_fidelity(tc, fixed_scene)
            logger.info("  TC eval... %s", tc_score.get("overallScore", "N/A"))
        except Exception as exc:
            logger.warning("  TC eval failed: %s", exc)
            tc_score = {"overallScore": 0.0, "detail": {"reason": str(exc)}}
        if tc_score is not None:
            _write_json(paths.get("tc_score", os.path.join(image_dir, "tc-score.json")), tc_score)

        # ---- Phase 3: Render (.tc → PNG) ----
        render_success = False
        if not self.skip_render:
            logger.info("  Render...")
            try:
                self._render_tc(paths["tc"], paths["render"])
                if (
                    os.path.isfile(paths["render"])
                    and os.path.getsize(paths["render"]) > 0
                ):
                    render_success = True
                else:
                    logger.warning("  Render produced empty file")
            except Exception as exc:
                logger.error("  Render failed: %s", exc)

        # ---- Phase 4: Evaluate (judge model) ----
        score: Optional[dict] = None
        cached_score = self._load_from_cache(score_cache_key, "score")
        if self.skip_eval:
            if cached_score is not None:
                logger.info("  Evaluate... (hash cache, skip-eval)")
                score = cached_score
                _write_json(paths["score"], score)
        else:
            logger.info("  Evaluate...")
            try:
                if cached_score is not None:
                    score = cached_score
                    logger.info("  Evaluate... (hash cache)")
                elif not render_success:
                    logger.warning("  Render failed — assigning score 0")
                    score = {
                        "overallScore": 0.0,
                        "visualSimilarity": 0.0,
                        "textAccuracy": 0.0,
                        "layoutAccuracy": 0.0,
                        "colorAccuracy": 0.0,
                        "editability": 0.0,
                        "criticalIssues": [
                            "Render failed — no screenshot available"
                        ],
                        "recommendations": [
                            "Fix render pipeline",
                            "Check .tc validity",
                        ],
                    }
                else:
                    tc_summary = ImportJudge._build_tc_summary(tc)
                    score = self.judge.evaluate(
                        original_path=image_path,
                        render_path=paths["render"],
                        scene=fixed_scene or {},
                        tc_summary=tc_summary,
                    )

                if score is not None:
                    _write_json(paths["score"], score)
                    self._save_to_cache(score_cache_key, "score", score)

            except Exception as exc:
                logger.error("  Evaluate error: %s", exc)
                score = {
                    "overallScore": 0.5,
                    "visualSimilarity": 0.0,
                    "textAccuracy": 0.0,
                    "layoutAccuracy": 0.0,
                    "colorAccuracy": 0.0,
                    "editability": 0.0,
                    "criticalIssues": [f"Evaluation failed: {exc}"],
                    "recommendations": [
                        "Check judge model availability",
                        "Review API key and quotas",
                    ],
                }
                _write_json(paths["score"], score)
                self._save_to_cache(score_cache_key, "score", score)

        # ---- Collect result ----
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        result.score = score
        result.scene_score = scene_score
        result.tc_score = tc_score
        result.cost_usd = self._calculate_image_cost(usage_count_before)
        result.latency_ms = elapsed_ms
        result.status = "success" if not result.error_message else "failed"

        return result

    # ---------------------------------------------------------------
    # Render via tc_render.js
    # ---------------------------------------------------------------

    def _render_tc(self, tc_path: str, output_path: str) -> None:
        """Call ``tc_render.js`` as a subprocess to produce a PNG screenshot.

        Raises ``FileNotFoundError`` if the render script is missing, or
        ``RuntimeError`` if the script exits with a non-zero code.
        """
        render_script = os.path.join(self._script_dir, "tc_render_standalone.js")
        if not os.path.isfile(render_script):
            raise FileNotFoundError(
                f"Render script not found: {render_script}"
            )

        # Ensure output parent directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        logger.info("    node %s --tc %s --output %s",
                     os.path.basename(render_script),
                     os.path.basename(tc_path),
                     os.path.basename(output_path))

        proc = subprocess.run(
            ["node", render_script, "--tc", tc_path, "--output", output_path],
            capture_output=True,
            text=True,
            errors="backslashreplace",
            timeout=120,
        )

        if proc.returncode != 0:
            stderr = proc.stderr.strip() if proc.stderr else ""
            stdout = proc.stdout.strip() if proc.stdout else ""
            error_msg = stderr or stdout or f"Exit code {proc.returncode}"
            raise RuntimeError(f"Render failed: {error_msg}")

    # ---------------------------------------------------------------
    # Cached-scene helpers
    # ---------------------------------------------------------------

    def _load_cached_scene(
        self, image_dir: str
    ) -> Optional[tuple[Optional[dict], Optional[dict]]]:
        """Load previously-saved scene.json and scene-fixed.json.

        Returns ``(raw_scene, fixed_scene)`` if ``scene.json`` exists,
        else ``None``.
        """
        scene_path = os.path.join(image_dir, "scene.json")
        scene_fixed_path = os.path.join(image_dir, "scene-fixed.json")

        raw = _read_json(scene_path)
        fixed = _read_json(scene_fixed_path)

        if raw is not None:
            return (raw, fixed)
        return None

    # ---------------------------------------------------------------
    # Hash cache helpers
    # ---------------------------------------------------------------

    def _cache_key(self, image_path: str, model_id: Optional[str] = None) -> str:
        """Return the logical cache key for an image/model combination.

        The key follows the OpenSpec contract:
        ``smart-import:{sha256}:{pipelineVersion}:{modelId}``.
        """
        with open(image_path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        return (
            f"smart-import:{digest}:{self.pipeline_version}:"
            f"{model_id or self.model}"
        )

    @staticmethod
    def _safe_cache_key(cache_key: str) -> str:
        """Map a logical key to a filesystem-safe directory name.

        The logical key uses ``:`` and OpenRouter model IDs use ``/``.  Both
        are problematic on Windows paths, so the cache stores artifacts under
        a sanitized directory and keeps the logical key in ``cache-key.json``.
        """
        return re.sub(r"[^A-Za-z0-9._-]+", "_", cache_key).strip("_")

    def _cache_artifact_path(self, cache_key: str, phase: str) -> str:
        """Return the cache path for a known phase artifact."""
        filename = CACHE_PHASE_FILES.get(phase)
        if filename is None:
            raise ValueError(f"Unknown cache phase: {phase}")
        return os.path.join(
            self.cache_dir,
            self._safe_cache_key(cache_key),
            filename,
        )

    def _load_from_cache(self, cache_key: str, phase: str) -> Optional[dict]:
        """Load a JSON artifact from ``output/.cache`` if present."""
        return _read_json(self._cache_artifact_path(cache_key, phase))

    def _save_to_cache(self, cache_key: str, phase: str, data: dict) -> None:
        """Persist a JSON artifact under ``output/.cache``."""
        artifact_path = self._cache_artifact_path(cache_key, phase)
        cache_dir = os.path.dirname(os.path.abspath(artifact_path))
        os.makedirs(cache_dir, exist_ok=True)
        _write_json(os.path.join(cache_dir, "cache-key.json"), {"key": cache_key})
        _write_json(artifact_path, data)

    # ---------------------------------------------------------------
    # Usage-log / cost helpers
    # ---------------------------------------------------------------

    def _save_image_usage_log(
        self, path: str, usage_count_before: int
    ) -> None:
        """Persist only the usage log entries added since *usage_count_before*."""
        new_logs = self.client.usage_logs[usage_count_before:]
        if new_logs:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    [log.to_dict() for log in new_logs],
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

    def _save_image_conversation_log(
        self, path: str, conv_count_before: int
    ) -> None:
        """Persist conversation logs added since *conv_count_before*."""
        new_logs = self.client.conversation_logs[conv_count_before:]
        if new_logs:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(new_logs, f, indent=2, ensure_ascii=False)

    def _calculate_image_cost(self, usage_count_before: int) -> float:
        """Sum the cost of API calls made since *usage_count_before*."""
        new_logs = self.client.usage_logs[usage_count_before:]
        return round(sum(log.cost_usd for log in new_logs), 8)

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------

    @staticmethod
    def _print_summary(results: list[Result]) -> None:
        """Print a short summary table to stdout."""
        success_count = sum(1 for r in results if r.status == "success")
        failed_count = sum(1 for r in results if r.status == "failed")
        total_cost = sum(r.cost_usd for r in results)

        print()
        print("=" * 60)
        print("  PIPELINE SUMMARY")
        print("=" * 60)
        print(f"  Total images:  {len(results)}")
        print(f"  Successful:    {success_count}")
        print(f"  Failed:        {failed_count}")
        print(f"  Total cost:    ${total_cost:.6f}")

        if results:
            avg_score = (
                sum(
                    r.score.get("overallScore", 0) or 0
                    for r in results
                    if r.score
                )
                / len(results)
            )
            print(f"  Avg score:     {avg_score:.4f}")

        print("=" * 60)

    # ---------------------------------------------------------------
    # Default error score
    # ---------------------------------------------------------------

    @staticmethod
    def _default_error_score(error_message: str) -> dict:
        return {
            "overallScore": 0.5,
            "visualSimilarity": 0.0,
            "textAccuracy": 0.0,
            "layoutAccuracy": 0.0,
            "colorAccuracy": 0.0,
            "editability": 0.0,
            "criticalIssues": [f"Evaluation error: {error_message}"],
            "recommendations": ["Check judge model availability"],
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser (separated for testability)."""
    parser = argparse.ArgumentParser(
        description="Smart Import Calibration Pipeline — "
        "orchestrate image → .tc → render → evaluate",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  Full pipeline:\n"
            "    python scripts/smart-import/pipeline.py\n"
            "  Skip analysis (reuse cached scenes) and re-render:\n"
            "    python scripts/smart-import/pipeline.py --skip-analysis\n"
            "  Process a single image:\n"
            "    python scripts/smart-import/pipeline.py --image poster-simple\n"
        ),
    )
    parser.add_argument(
        "--dataset",
        default="scripts/smart-import/dataset/",
        help="Dataset directory (default: %(default)s)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Vision model for analysis (default: from env or "
        "google/gemini-2.5-flash)",
    )
    parser.add_argument(
        "--compiler-model",
        default=None,
        help="Compiler model for .tc generation "
        "(default: from env or google/gemini-2.5-flash-lite)",
    )
    parser.add_argument(
        "--judge-model",
        default=None,
        help="Judge model for evaluation "
        "(default: from env or google/gemini-2.5-pro)",
    )
    parser.add_argument(
        "--output",
        default="scripts/smart-import/output/",
        help="Output directory (default: %(default)s)",
    )
    parser.add_argument(
        "--mode",
        choices=sorted(SUPPORTED_MODES),
        default="basic_image_layers",
        help="V1 compilation mode: text_only or basic_image_layers "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--skip-analysis",
        action="store_true",
        help="Skip analysis phase, reuse cached scenes",
    )
    parser.add_argument(
        "--skip-render",
        action="store_true",
        help="Skip rendering phase",
    )
    parser.add_argument(
        "--skip-eval",
        action="store_true",
        help="Skip evaluation phase",
    )
    parser.add_argument(
        "--image",
        default=None,
        metavar="ID",
        help="Specific image ID (filename stem) to process (default: all)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable DEBUG-level logging",
    )
    return parser


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )

    config: dict = {
        "dataset_dir": args.dataset,
        "model": args.model
        or os.getenv("DEFAULT_VISION_MODEL", "google/gemini-2.5-flash"),
        "compiler_model": args.compiler_model
        or os.getenv(
            "DEFAULT_COMPILER_MODEL", "google/gemini-2.5-flash-lite"
        ),
        "judge_model": args.judge_model
        or os.getenv("JUDGE_MODEL", "google/gemini-2.5-pro"),
        "output_dir": args.output,
        "mode": args.mode,
        "skip_analysis": args.skip_analysis,
        "skip_render": args.skip_render,
        "skip_eval": args.skip_eval,
    }

    pipeline = SmartImportPipeline(config)
    results = pipeline.run(filter_image=args.image)

    # Exit 0 if all succeeded, 1 if any failed
    failed = any(r.status == "failed" for r in results)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
