"""
Unit tests for the report generator.

Tests report generation with mock results, markdown table formatting, JSON output
structure, averaging calculations, ranking logic, empty results handling, and
results with failures.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

# Ensure the parent directory is on sys.path for imports
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from report import aggregate_results, generate_report


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SAMPLE_RESULTS = [
    {
        "imageId": "img-01",
        "model": "gemini-2.5-flash",
        "scenePath": "output/flash/img-01/scene.json",
        "tcPath": "output/flash/img-01/design.tc",
        "renderPath": "output/flash/img-01/render.png",
        "score": {
            "overallScore": 0.85,
            "visualSimilarity": 0.80,
            "textAccuracy": 0.90,
            "layoutAccuracy": 0.85,
            "colorAccuracy": 0.75,
            "editability": 0.95,
            "criticalIssues": [],
            "recommendations": ["Increase contrast"],
        },
        "costUsd": 0.005,
        "latencyMs": 1200,
        "status": "success",
        "errorMessage": None,
    },
    {
        "imageId": "img-02",
        "model": "gemini-2.5-flash",
        "scenePath": "output/flash/img-02/scene.json",
        "tcPath": "output/flash/img-02/design.tc",
        "renderPath": "output/flash/img-02/render.png",
        "score": {
            "overallScore": 0.72,
            "visualSimilarity": 0.70,
            "textAccuracy": 0.65,
            "layoutAccuracy": 0.75,
            "colorAccuracy": 0.68,
            "editability": 0.80,
            "criticalIssues": ["Text block 40px too high"],
            "recommendations": ["Adjust text positions"],
        },
        "costUsd": 0.004,
        "latencyMs": 1100,
        "status": "success",
        "errorMessage": None,
    },
    {
        "imageId": "img-01",
        "model": "gemini-2.5-pro",
        "scenePath": "output/pro/img-01/scene.json",
        "tcPath": "output/pro/img-01/design.tc",
        "renderPath": "output/pro/img-01/render.png",
        "score": {
            "overallScore": 0.92,
            "visualSimilarity": 0.90,
            "textAccuracy": 0.95,
            "layoutAccuracy": 0.92,
            "colorAccuracy": 0.88,
            "editability": 0.96,
            "criticalIssues": [],
            "recommendations": [],
        },
        "costUsd": 0.015,
        "latencyMs": 3400,
        "status": "success",
        "errorMessage": None,
    },
]

_FAILED_RESULT = {
    "imageId": "img-03",
    "model": "gemini-2.5-flash",
    "scenePath": "output/flash/img-03/scene.json",
    "tcPath": "output/flash/img-03/design.tc",
    "renderPath": "output/flash/img-03/render.png",
    "score": None,
    "costUsd": 0.002,
    "latencyMs": 500,
    "status": "failed",
    "errorMessage": "Render timeout after 30s",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGenerateReport(unittest.TestCase):
    """``generate_report`` — output structure, averaging, ranking."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # ---------------------------------------------------------------
    # File output
    # ---------------------------------------------------------------

    def test_report_creates_json_and_md(self):
        generate_report(_SAMPLE_RESULTS, self.tmp_dir)
        self.assertTrue(
            os.path.exists(os.path.join(self.tmp_dir, "report.json"))
        )
        self.assertTrue(
            os.path.exists(os.path.join(self.tmp_dir, "report.md"))
        )

    def test_report_json_structure(self):
        report = generate_report(_SAMPLE_RESULTS, self.tmp_dir)
        self.assertIn("summary", report)
        self.assertIn("modelStats", report)
        self.assertIn("models", report)
        self.assertIn("ranking", report)
        self.assertIn("criticalIssues", report)
        self.assertIn("generatedAt", report)

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------

    def test_summary_counts(self):
        report = generate_report(_SAMPLE_RESULTS, self.tmp_dir)
        s = report["summary"]
        self.assertEqual(s["totalImages"], 3)
        self.assertEqual(s["totalModels"], 2)
        self.assertGreater(s["totalCost"], 0)
        self.assertGreater(s["avgOverallScore"], 0)

    # ---------------------------------------------------------------
    # Model stats
    # ---------------------------------------------------------------

    def test_model_stats_count(self):
        report = generate_report(_SAMPLE_RESULTS, self.tmp_dir)
        self.assertEqual(len(report["modelStats"]), 2)

    def test_model_stats_keys(self):
        report = generate_report(_SAMPLE_RESULTS, self.tmp_dir)
        for ms in report["modelStats"]:
            self.assertIn("model", ms)
            self.assertIn("count", ms)
            self.assertIn("totalCost", ms)
            self.assertIn("avgScore", ms)
            self.assertIn("avgLatencyMs", ms)

    def test_averaging_correct(self):
        """flash avg = (0.85 + 0.72) / 2 = 0.785"""
        report = generate_report(_SAMPLE_RESULTS, self.tmp_dir)
        flash_stats = [
            m for m in report["modelStats"]
            if m["model"] == "gemini-2.5-flash"
        ][0]
        self.assertAlmostEqual(flash_stats["avgScore"], 0.785, places=4)

    def test_per_dimension_averages(self):
        report = generate_report(_SAMPLE_RESULTS, self.tmp_dir)
        flash = [
            m for m in report["modelStats"]
            if m["model"] == "gemini-2.5-flash"
        ][0]
        # visualSimilarity: (0.80 + 0.70) / 2 = 0.75
        self.assertAlmostEqual(
            flash["avgVisualSimilarity"], 0.75, places=4
        )
        # textAccuracy: (0.90 + 0.65) / 2 = 0.775
        self.assertAlmostEqual(flash["avgTextAccuracy"], 0.775, places=4)

    def test_latency_averaging(self):
        report = generate_report(_SAMPLE_RESULTS, self.tmp_dir)
        flash = [
            m for m in report["modelStats"]
            if m["model"] == "gemini-2.5-flash"
        ][0]
        # (1200 + 1100) / 2 = 1150
        self.assertAlmostEqual(flash["avgLatencyMs"], 1150.0, places=1)

    # ---------------------------------------------------------------
    # Ranking
    # ---------------------------------------------------------------

    def test_ranking_logic(self):
        """Pro should rank above flash."""
        report = generate_report(_SAMPLE_RESULTS, self.tmp_dir)
        self.assertEqual(report["ranking"][0]["model"], "gemini-2.5-pro")
        self.assertEqual(report["ranking"][1]["model"], "gemini-2.5-flash")

    def test_ranking_has_score_per_cost(self):
        report = generate_report(_SAMPLE_RESULTS, self.tmp_dir)
        for entry in report["ranking"]:
            self.assertIn("scorePerCost", entry)
            self.assertGreater(entry["scorePerCost"], 0)

    # ---------------------------------------------------------------
    # Critical issues
    # ---------------------------------------------------------------

    def test_critical_issues_in_report(self):
        report = generate_report(_SAMPLE_RESULTS, self.tmp_dir)
        self.assertGreater(len(report["criticalIssues"]), 0)
        issue_texts = [i["issue"] for i in report["criticalIssues"]]
        self.assertTrue(
            any("40px" in t for t in issue_texts),
            f"Expected '40px' in issues, got {issue_texts}",
        )

    # ---------------------------------------------------------------
    # Markdown output
    # ---------------------------------------------------------------

    def test_markdown_contains_summary_table(self):
        generate_report(_SAMPLE_RESULTS, self.tmp_dir)
        md = self._read_md()
        self.assertIn("Smart Import Calibration Report", md)
        self.assertIn("## Summary", md)
        self.assertIn("Total images", md)
        self.assertIn("Total cost", md)

    def test_markdown_contains_results_by_model(self):
        generate_report(_SAMPLE_RESULTS, self.tmp_dir)
        md = self._read_md()
        self.assertIn("## Results by Model", md)
        self.assertIn("gemini-2.5-flash", md)
        self.assertIn("gemini-2.5-pro", md)

    def test_markdown_contains_model_ranking(self):
        generate_report(_SAMPLE_RESULTS, self.tmp_dir)
        md = self._read_md()
        self.assertIn("## Model Ranking", md)

    def test_markdown_contains_critical_issues(self):
        generate_report(_SAMPLE_RESULTS, self.tmp_dir)
        md = self._read_md()
        self.assertIn("## Critical Issues Log", md)
        self.assertIn("40px", md)

    def test_markdown_table_headers(self):
        generate_report(_SAMPLE_RESULTS, self.tmp_dir)
        md = self._read_md()
        lines = md.split("\n")
        table_lines = [l for l in lines if l.startswith("| Image ")]
        self.assertGreater(len(table_lines), 0)
        header = table_lines[0]
        self.assertIn("Visual", header)
        self.assertIn("Text", header)
        self.assertIn("Layout", header)
        self.assertIn("Color", header)
        self.assertIn("Overall", header)
        self.assertIn("Cost", header)
        self.assertIn("Time", header)

    def test_markdown_has_data_rows(self):
        generate_report(_SAMPLE_RESULTS, self.tmp_dir)
        md = self._read_md()
        self.assertIn("img-01", md)
        self.assertIn("img-02", md)

    # ---------------------------------------------------------------
    # JSON round-trip
    # ---------------------------------------------------------------

    def test_json_output_roundtrip(self):
        report = generate_report(_SAMPLE_RESULTS, self.tmp_dir)
        json_path = os.path.join(self.tmp_dir, "report.json")
        with open(json_path, encoding="utf-8") as f:
            loaded = json.load(f)
        self.assertEqual(
            loaded["summary"]["totalImages"],
            report["summary"]["totalImages"],
        )
        self.assertEqual(len(loaded["models"]), len(report["models"]))

    # ---------------------------------------------------------------
    # Edge cases
    # ---------------------------------------------------------------

    def test_empty_results_list(self):
        report = generate_report([], self.tmp_dir)
        self.assertEqual(report["summary"]["totalImages"], 0)
        self.assertEqual(report["summary"]["totalCost"], 0)
        self.assertEqual(report["summary"]["avgOverallScore"], 0)
        self.assertEqual(len(report["models"]), 0)
        self.assertEqual(len(report["ranking"]), 0)

    def test_results_with_failure(self):
        results = _SAMPLE_RESULTS + [_FAILED_RESULT]
        report = generate_report(results, self.tmp_dir)
        # Summary should include all results
        self.assertEqual(report["summary"]["totalImages"], 4)
        # The failed result should not affect score averages
        flash = [
            m for m in report["modelStats"]
            if m["model"] == "gemini-2.5-flash"
        ][0]
        # flash avg still (0.85 + 0.72) / 2 = 0.785 even with 3rd failed
        self.assertAlmostEqual(flash["avgScore"], 0.785, places=4)
        # Cost should include failed result
        self.assertAlmostEqual(flash["totalCost"], 0.005 + 0.004 + 0.002, places=4)
        # Critical issues should include pipeline error
        self.assertTrue(
            any("Render timeout" in i["issue"] for i in report["criticalIssues"]),
        )

    def test_results_with_none_scores(self):
        """A result with ``score: None`` should not crash the report."""
        no_score = {
            "imageId": "img-null",
            "model": "gemini-2.5-flash",
            "score": None,
            "costUsd": 0.001,
            "latencyMs": 100,
            "status": "success",
            "errorMessage": None,
        }
        results = _SAMPLE_RESULTS + [no_score]
        report = generate_report(results, self.tmp_dir)
        self.assertEqual(report["summary"]["totalImages"], 4)

    def test_single_model_single_image(self):
        single = [_SAMPLE_RESULTS[0]]
        report = generate_report(single, self.tmp_dir)
        self.assertEqual(report["summary"]["totalImages"], 1)
        self.assertEqual(report["summary"]["totalModels"], 1)
        self.assertEqual(len(report["models"]), 1)
        self.assertEqual(len(report["ranking"]), 1)

    def test_results_with_varying_models(self):
        """Multiple models should each get their own section."""
        extra = {
            "imageId": "img-04",
            "model": "claude-sonnet-4.5",
            "score": {
                "overallScore": 0.95,
                "visualSimilarity": 0.93,
                "textAccuracy": 0.97,
                "layoutAccuracy": 0.94,
                "colorAccuracy": 0.91,
                "editability": 0.98,
                "criticalIssues": [],
                "recommendations": [],
            },
            "costUsd": 0.030,
            "latencyMs": 5200,
            "status": "success",
            "errorMessage": None,
        }
        results = _SAMPLE_RESULTS + [extra]
        report = generate_report(results, self.tmp_dir)
        self.assertEqual(report["summary"]["totalModels"], 3)
        self.assertEqual(len(report["modelStats"]), 3)
        # Claude should rank first
        self.assertEqual(report["ranking"][0]["model"], "claude-sonnet-4.5")

    # ---------------------------------------------------------------
    # Helper
    # ---------------------------------------------------------------

    def _read_md(self) -> str:
        md_path = os.path.join(self.tmp_dir, "report.md")
        with open(md_path, encoding="utf-8") as f:
            return f.read()


class TestAggregateResults(unittest.TestCase):
    """``aggregate_results`` — reading from a directory structure."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # ---------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------

    def _create_result(
        self,
        model: str,
        image: str,
        score: dict | None = None,
        log: dict | None = None,
    ) -> None:
        """Create a minimal result directory with files."""
        image_dir = os.path.join(self.tmp_dir, model, image)
        os.makedirs(image_dir, exist_ok=True)

        if score is not None:
            with open(os.path.join(image_dir, "score.json"), "w") as f:
                json.dump(score, f)

        if log is not None:
            with open(os.path.join(image_dir, "openrouter.json"), "w") as f:
                json.dump([log], f) if isinstance(log, dict) else json.dump(log, f)

        # Empty stubs for other artifacts
        for name in ("scene.json", "design.tc"):
            with open(os.path.join(image_dir, name), "w") as f:
                json.dump({}, f)

    # ---------------------------------------------------------------
    # Tests
    # ---------------------------------------------------------------

    def test_aggregate_empty_directory(self):
        results = aggregate_results(self.tmp_dir)
        self.assertEqual(results, [])

    def test_aggregate_nonexistent_directory(self):
        results = aggregate_results("/nonexistent/path")
        self.assertEqual(results, [])

    def test_aggregate_single_result(self):
        self._create_result(
            "gemini-flash",
            "img-01",
            {"overallScore": 0.85},
            {"costUsd": 0.005, "latencyMs": 1200, "status": "success"},
        )
        results = aggregate_results(self.tmp_dir)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["imageId"], "img-01")
        self.assertEqual(results[0]["model"], "gemini-flash")
        self.assertEqual(results[0]["score"]["overallScore"], 0.85)
        self.assertAlmostEqual(results[0]["costUsd"], 0.005)
        self.assertEqual(results[0]["latencyMs"], 1200)
        self.assertEqual(results[0]["status"], "success")

    def test_aggregate_multiple_results(self):
        self._create_result(
            "gemini-flash", "img-01",
            {"overallScore": 0.85},
            {"costUsd": 0.005, "latencyMs": 1200, "status": "success"},
        )
        self._create_result(
            "gemini-pro", "img-01",
            {"overallScore": 0.92},
            {"costUsd": 0.015, "latencyMs": 3400, "status": "success"},
        )
        results = aggregate_results(self.tmp_dir)
        self.assertEqual(len(results), 2)

    def test_aggregate_no_score_file(self):
        """Missing score.json should result in ``score: None``."""
        self._create_result("gemini-flash", "img-01", score=None)
        results = aggregate_results(self.tmp_dir)
        self.assertEqual(len(results), 1)
        self.assertIsNone(results[0]["score"])

    def test_aggregate_with_failure(self):
        self._create_result(
            "gemini-flash",
            "img-01",
            score=None,
            log={
                "costUsd": 0.002, "latencyMs": 500,
                "status": "error", "errorMessage": "API failed",
            },
        )
        results = aggregate_results(self.tmp_dir)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "failed")
        self.assertEqual(results[0]["errorMessage"], "API failed")

    def test_aggregate_paths_are_correct(self):
        self._create_result(
            "flash", "img-01",
            {"overallScore": 0.8},
            {"costUsd": 0.001, "latencyMs": 100, "status": "success"},
        )
        results = aggregate_results(self.tmp_dir)
        r = results[0]
        self.assertTrue(r["scenePath"].endswith("scene.json"))
        self.assertTrue(r["tcPath"].endswith("design.tc"))
        self.assertTrue(r["renderPath"].endswith("render.png"))

    def test_aggregate_cost_and_latency_summed(self):
        """Multiple log entries should sum cost and latency."""
        image_dir = os.path.join(self.tmp_dir, "flash", "img-01")
        os.makedirs(image_dir, exist_ok=True)
        with open(os.path.join(image_dir, "score.json"), "w") as f:
            json.dump({"overallScore": 0.85}, f)
        with open(os.path.join(image_dir, "openrouter.json"), "w") as f:
            json.dump([
                {"costUsd": 0.002, "latencyMs": 500, "status": "success"},
                {"costUsd": 0.003, "latencyMs": 700, "status": "success"},
            ], f)

        results = aggregate_results(self.tmp_dir)
        self.assertEqual(len(results), 1)
        self.assertAlmostEqual(results[0]["costUsd"], 0.005)
        self.assertEqual(results[0]["latencyMs"], 1200)


if __name__ == "__main__":
    unittest.main()
