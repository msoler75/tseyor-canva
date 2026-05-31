"""
Report generator for the smart import calibration pipeline.

Aggregates individual evaluation results into structured JSON and
human-readable Markdown reports.
"""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SCORE_DIMENSIONS = [
    "visualSimilarity",
    "textAccuracy",
    "layoutAccuracy",
    "colorAccuracy",
    "editability",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _safe_avg(values: list[Optional[float]]) -> float:
    """Compute average, ignoring *None* / missing values."""
    filtered = [v for v in values if v is not None]
    if not filtered:
        return 0.0
    return sum(filtered) / len(filtered)


def _safe_score(result: dict, key: str) -> Optional[float]:
    """Extract a single score dimension from a result dict, or return *None*."""
    score = result.get("score") or {}
    return score.get(key)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(results: list[dict], output_dir: str) -> dict:
    """Generate a full calibration report from a list of result dicts.

    Writes two files to *output_dir*:

    * ``report.json`` — full structured data (machine-readable)
    * ``report.md`` — human-readable Markdown summary

    Parameters
    ----------
    results:
        List of result dicts.  Each result must have at minimum:
        ``imageId``, ``model``, ``score`` (dict), ``costUsd``,
        ``latencyMs``, ``status``.
    output_dir:
        Directory to write the report files into (created if absent).

    Returns
    -------
    dict
        The report data structure (same dict written to ``report.json``).
    """
    os.makedirs(output_dir, exist_ok=True)

    # --- Aggregate top-level summary ---
    total_images = len(results)
    total_cost = sum(r.get("costUsd", 0) or 0 for r in results)
    all_overall = [
        _safe_score(r, "overallScore") for r in results if r.get("score")
    ]
    avg_overall = _safe_avg(all_overall)

    # Group by model
    by_model: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_model[r.get("model", "unknown")].append(r)

    # --- Per-model statistics ---
    model_stats_list: list[dict] = []
    model_sections: list[dict] = []

    for model_name in sorted(by_model):
        model_results = by_model[model_name]
        # Only count successful results for score averages
        scored_results = [
            r for r in model_results
            if r.get("score") and r.get("status") == "success"
        ]
        model_cost = sum(r.get("costUsd", 0) or 0 for r in model_results)
        model_count_total = len(model_results)

        model_avg_overall = _safe_avg(
            [_safe_score(r, "overallScore") for r in scored_results]
        )

        dim_avgs: dict[str, float] = {}
        for dim in _SCORE_DIMENSIONS:
            dim_avgs[dim] = _safe_avg(
                [_safe_score(r, dim) for r in scored_results]
            )

        avg_latency = _safe_avg([
            r.get("latencyMs") for r in model_results
            if r.get("latencyMs") is not None
        ])

        model_stats_list.append({
            "model": model_name,
            "count": model_count_total,
            "totalCost": round(model_cost, 6),
            "avgScore": round(model_avg_overall, 4),
            "avgVisualSimilarity": round(dim_avgs["visualSimilarity"], 4),
            "avgTextAccuracy": round(dim_avgs["textAccuracy"], 4),
            "avgLayoutAccuracy": round(dim_avgs["layoutAccuracy"], 4),
            "avgColorAccuracy": round(dim_avgs["colorAccuracy"], 4),
            "avgEditability": round(dim_avgs["editability"], 4),
            "avgLatencyMs": round(avg_latency, 1),
        })

        # Per-image rows
        image_rows: list[dict] = []
        for r in sorted(model_results, key=lambda x: x.get("imageId", "")):
            score = r.get("score") or {}
            image_rows.append({
                "imageId": r.get("imageId", "?"),
                "visualSimilarity": score.get("visualSimilarity"),
                "textAccuracy": score.get("textAccuracy"),
                "layoutAccuracy": score.get("layoutAccuracy"),
                "colorAccuracy": score.get("colorAccuracy"),
                "editability": score.get("editability"),
                "overallScore": score.get("overallScore"),
                "costUsd": r.get("costUsd"),
                "latencyMs": r.get("latencyMs"),
                "status": r.get("status", "?"),
                "errorMessage": r.get("errorMessage"),
            })

        model_sections.append({
            "model": model_name,
            "imageCount": model_count_total,
            "totalCost": round(model_cost, 6),
            "avgOverallScore": round(model_avg_overall, 4),
            "avgLatencyMs": round(avg_latency, 1),
            "images": image_rows,
        })

    # --- Model ranking (by avgScore descending) ---
    sorted_models = sorted(
        model_stats_list,
        key=lambda m: m["avgScore"],
        reverse=True,
    )
    ranking: list[dict] = []
    for rank, m in enumerate(sorted_models, start=1):
        score_cost = round(m["avgScore"] / m["totalCost"], 1) if m["totalCost"] > 0 else 0
        ranking.append({
            "rank": rank,
            "model": m["model"],
            "avgScore": m["avgScore"],
            "totalCost": m["totalCost"],
            "scorePerCost": score_cost,
            "avgLatencyMs": m["avgLatencyMs"],
        })

    # --- Critical issues log ---
    critical_issues: list[dict] = []
    for r in results:
        score = r.get("score") or {}
        issues = score.get("criticalIssues") or []
        for issue in issues:
            critical_issues.append({
                "imageId": r.get("imageId", "?"),
                "model": r.get("model", "?"),
                "issue": issue,
            })
        # Also surface pipeline errors as issues
        if r.get("status") == "failed" and r.get("errorMessage"):
            critical_issues.append({
                "imageId": r.get("imageId", "?"),
                "model": r.get("model", "?"),
                "issue": f"Pipeline error: {r['errorMessage']}",
            })

    # --- Assemble report dict ---
    report: dict = {
        "summary": {
            "totalImages": total_images,
            "totalCost": round(total_cost, 6),
            "avgOverallScore": round(avg_overall, 4),
            "totalModels": len(by_model),
        },
        "modelStats": model_stats_list,
        "models": model_sections,
        "ranking": ranking,
        "criticalIssues": critical_issues,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }

    # --- Write report.json ---
    json_path = os.path.join(output_dir, "report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # --- Write report.md ---
    md_path = os.path.join(output_dir, "report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(_format_markdown(report, results))

    logger.info("Report written to %s and %s", json_path, md_path)
    return report


# ---------------------------------------------------------------------------
# Markdown formatting
# ---------------------------------------------------------------------------


def _format_markdown(report: dict, raw_results: list[dict]) -> str:
    """Format the report dict as a human-readable Markdown string."""
    lines: list[str] = []
    s = report["summary"]

    lines.append("# Smart Import Calibration Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total images | {s['totalImages']} |")
    lines.append(f"| Total cost | ${s['totalCost']:.6f} |")
    lines.append(f"| Avg score | {s['avgOverallScore']:.4f} |")
    if report["ranking"]:
        best = report["ranking"][0]
        lines.append(
            f"| Best model | {best['model']} ({best['avgScore']:.4f}) |"
        )
    lines.append("")

    # --- Results by model ---
    lines.append("## Results by Model")
    lines.append("")

    for ms in report["models"]:
        lines.append(f"### {ms['model']}")
        lines.append("")
        lines.append(
            f"Average: {ms['avgOverallScore']:.4f} | "
            f"Total cost: ${ms['totalCost']:.6f} | "
            f"Avg latency: {ms['avgLatencyMs']:.1f}ms"
        )
        lines.append("")

        # Table header
        lines.append(
            "| Image | Visual | Text | Layout | Color | Editability | "
            "Overall | Cost | Time |"
        )
        lines.append(
            "|-------|--------|------|--------|-------|-------------|"
            "---------|------|------|"
        )

        for img in ms["images"]:
            cost_str = (
                f"${img['costUsd']:.4f}"
                if img["costUsd"] is not None
                else "N/A"
            )
            lat_str = (
                f"{img['latencyMs'] / 1000:.1f}s"
                if img["latencyMs"] is not None
                else "N/A"
            )

            def _fmt(v):
                if v is None:
                    return "N/A"
                return f"{v:.2f}"

            row = (
                f"| {img['imageId']} "
                f"| {_fmt(img['visualSimilarity'])} "
                f"| {_fmt(img['textAccuracy'])} "
                f"| {_fmt(img['layoutAccuracy'])} "
                f"| {_fmt(img['colorAccuracy'])} "
                f"| {_fmt(img['editability'])} "
                f"| {_fmt(img['overallScore'])} "
                f"| {cost_str} "
                f"| {lat_str} |"
            )
            lines.append(row)

            # Show error annotation if the result failed
            if img["status"] == "failed" and img["errorMessage"]:
                lines.append(
                    f"  _(Error: {img['errorMessage']})_"
                )

        lines.append("")

    # --- Model Ranking ---
    lines.append("## Model Ranking")
    lines.append("")
    lines.append(
        "| Rank | Model | Avg Score | Total Cost | Score/Cost | Avg Latency |"
    )
    lines.append(
        "|------|-------|-----------|------------|------------|-------------|"
    )
    for m in report["ranking"]:
        lines.append(
            f"| {m['rank']} "
            f"| {m['model']} "
            f"| {m['avgScore']:.4f} "
            f"| ${m['totalCost']:.6f} "
            f"| {m['scorePerCost']:.1f} "
            f"| {m['avgLatencyMs']:.1f}ms |"
        )
    lines.append("")

    # --- Critical Issues Log ---
    if report["criticalIssues"]:
        lines.append("## Critical Issues Log")
        lines.append("")
        for issue in report["criticalIssues"]:
            lines.append(
                f"- {issue['imageId']} ({issue['model']}): {issue['issue']}"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Aggregation helper
# ---------------------------------------------------------------------------


def aggregate_results(results_dir: str) -> list[dict]:
    """Read individual result files from a structured output directory.

    Expected directory structure::

        {results_dir}/
        ├── {model-name}/
        │   ├── {image-id}/
        │   │   ├── score.json
        │   │   ├── scene.json
        │   │   ├── design.tc
        │   │   ├── render.png
        │   │   └── openrouter.json
        │   └── ...

    Returns a list of result dicts ready for ``generate_report``.
    """
    results: list[dict] = []

    if not os.path.isdir(results_dir):
        logger.warning("Results directory does not exist: %s", results_dir)
        return results

    for model_dir_name in sorted(os.listdir(results_dir)):
        model_dir = os.path.join(results_dir, model_dir_name)
        if not os.path.isdir(model_dir):
            continue

        for image_dir_name in sorted(os.listdir(model_dir)):
            image_dir = os.path.join(model_dir, image_dir_name)
            if not os.path.isdir(image_dir):
                continue

            result = _read_result(image_dir, model_dir_name, image_dir_name)
            results.append(result)

    return results


def _read_result(image_dir: str, model_name: str, image_id: str) -> dict:
    """Read a single result from an image-level directory."""
    score = _safe_read_json(os.path.join(image_dir, "score.json"))
    openrouter_log = _safe_read_json(os.path.join(image_dir, "openrouter.json"))

    cost_usd = 0.0
    latency_ms = 0
    status = "success"
    error_message: Optional[str] = None

    if isinstance(openrouter_log, list):
        cost_usd = sum(
            log.get("costUsd", 0) or 0 for log in openrouter_log
        )
        latency_ms = sum(
            log.get("latencyMs", 0) or 0 for log in openrouter_log
        )
        # If any log entry has status=error, mark overall as failed
        if any(log.get("status") == "error" for log in openrouter_log):
            status = "failed"
            error_entries = [
                log.get("errorMessage", "Unknown error")
                for log in openrouter_log
                if log.get("errorMessage")
            ]
            error_message = (
                "; ".join(error_entries) if error_entries else "API error"
            )

    return {
        "imageId": image_id,
        "model": model_name,
        "scenePath": os.path.join(image_dir, "scene.json"),
        "tcPath": os.path.join(image_dir, "design.tc"),
        "renderPath": os.path.join(image_dir, "render.png"),
        "score": score,
        "costUsd": cost_usd,
        "latencyMs": latency_ms,
        "status": status,
        "errorMessage": error_message,
    }


def _safe_read_json(path: str) -> Any:
    """Read a JSON file, or return *None* if it doesn't exist or is invalid."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read %s: %s", path, exc)
        return None
