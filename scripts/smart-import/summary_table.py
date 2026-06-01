"""
Generate a markdown summary table of the dataset evaluation results.

Usage:
    python summary_table.py [output_dir]

Reads scene-score.json and tc-score.json from each image directory
and prints a clean markdown table to stdout.
"""

from __future__ import annotations

import json
import os
import sys


def load_scores(base_dir: str) -> list[dict]:
    results = []
    for img_dir in sorted(os.listdir(base_dir)):
        d = os.path.join(base_dir, img_dir)
        if not os.path.isdir(d):
            continue

        ss = _read_json(os.path.join(d, "scene-score.json")) or {}
        ts = _read_json(os.path.join(d, "tc-score.json")) or {}
        sc = _read_json(os.path.join(d, "score.json")) or {}

        gt = ss.get("detail", {})
        td = ts.get("detail", {})

        results.append({
            "image": img_dir,
            # Level 1 — SceneGraph
            "s_f1": ss.get("f1Score"),
            "s_text_acc": ss.get("textAccuracy"),
            "s_type_acc": ss.get("typeAccuracy"),
            "s_overall": ss.get("overallScore"),
            "s_detected": gt.get("extractedCount"),
            "s_expected": gt.get("groundTruthCount"),
            "s_matched": gt.get("matchedCount"),
            # Level 2 — TC Fidelity
            "t_overall": ts.get("overallScore"),
            "t_preserv": ts.get("elementPreservation"),
            "t_text_fid": ts.get("textFidelity"),
            "t_pos_fid": ts.get("positionFidelity"),
            "t_prop_fid": ts.get("propertyFidelity"),
            # Level 3 — Visual Judge
            "v_overall": sc.get("overallScore") if sc.get("overallScore") != 0 or any(
                sc.get(k) for k in ("visualSimilarity", "textAccuracy", "layoutAccuracy")
            ) else None,
            "v_visual": sc.get("visualSimilarity"),
            "v_text": sc.get("textAccuracy"),
            "v_layout": sc.get("layoutAccuracy"),
            "v_color": sc.get("colorAccuracy"),
            "v_edit": sc.get("editability"),
            # Metadata
            "has_gt": ss.get("overallScore", 0) > 0 or gt.get("groundTruthCount", 0) > 0,
        })
    return results


def _read_json(path: str) -> dict | None:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _fmt(v, decimals=4) -> str:
    if v is None:
        return "—"
    return f"{v:.{decimals}f}"


def generate_markdown(results: list[dict]) -> str:
    lines: list[str] = []

    lines.append("# Smart Import — Dataset Evaluation Summary")
    lines.append("")

    # --- Overview ---
    total = len(results)
    with_gt = sum(1 for r in results if r["has_gt"])
    avg_s = sum(r["s_overall"] or 0 for r in results if r["has_gt"]) / max(with_gt, 1)
    avg_t = sum(r["t_overall"] or 0 for r in results) / max(total, 1)
    avg_v = sum(r["v_overall"] or 0 for r in results if r["v_overall"] is not None) / max(
        sum(1 for r in results if r["v_overall"] is not None), 1
    )

    lines.append("## Global Averages")
    lines.append("")
    lines.append(f"| Level | Metric | Average |")
    lines.append(f"|-------|--------|---------|")
    lines.append(f"| L1 — SceneGraph | Overall (images with GT: {with_gt}/{total}) | {_fmt(avg_s)} |")
    lines.append(f"| L2 — TC Fidelity | Overall (all {total} images) | {_fmt(avg_t)} |")
    lines.append(f"| L3 — Visual Judge | Overall | {_fmt(avg_v)} |")
    lines.append("")

    # --- Per-image table: Level 1 & 2 ---
    lines.append("## Per-Image Results")
    lines.append("")
    lines.append("| Image | L1 F1 | L1 Text | L1 Type | L1 Overall | Det/Exp/Match | "
                 "L2 Preserv | L2 Text | L2 Pos | L2 Overall |")
    lines.append("|-------|-------|---------|---------|------------|----------------|"
                 "-----------|---------|--------|------------|")
    for r in results:
        det_str = (
            f"{r['s_detected']}/{r['s_expected']}/{r['s_matched']}"
            if r["s_detected"] is not None
            else "—"
        )
        lines.append(
            f"| {r['image']} "
            f"| {_fmt(r['s_f1'])} "
            f"| {_fmt(r['s_text_acc'])} "
            f"| {_fmt(r['s_type_acc'])} "
            f"| {_fmt(r['s_overall'])} "
            f"| {det_str} "
            f"| {_fmt(r['t_preserv'])} "
            f"| {_fmt(r['t_text_fid'])} "
            f"| {_fmt(r['t_pos_fid'])} "
            f"| {_fmt(r['t_overall'])} |"
        )
    lines.append("")

    # --- Visual Judge table ---
    if any(r["v_overall"] is not None for r in results):
        lines.append("## Visual Judge (Level 3)")
        lines.append("")
        lines.append("| Image | Visual | Text | Layout | Color | Editability | Overall |")
        lines.append("|-------|--------|------|--------|-------|-------------|---------|")
        for r in results:
            lines.append(
                f"| {r['image']} "
                f"| {_fmt(r['v_visual'])} "
                f"| {_fmt(r['v_text'])} "
                f"| {_fmt(r['v_layout'])} "
                f"| {_fmt(r['v_color'])} "
                f"| {_fmt(r['v_edit'])} "
                f"| {_fmt(r['v_overall'])} |"
            )
        lines.append("")

    # --- Per-image text (top issues) ---
    worst_text = sorted(
        [r for r in results if r["s_text_acc"] is not None and r["has_gt"]],
        key=lambda r: r["s_text_acc"],
    )[:3]
    if worst_text:
        lines.append("## Lowest Text Accuracy (L1)")
        lines.append("")
        for r in worst_text:
            lines.append(f"- **{r['image']}**: {_fmt(r['s_text_acc'])} — detected {r['s_matched']}/{r['s_expected']} elements")
        lines.append("")

    return "\n".join(lines)


def main():
    base_dir = sys.argv[1] if len(sys.argv) > 1 else "output/google-gemini-2-5-flash"
    results = load_scores(base_dir)
    md = generate_markdown(results)
    print(md)


if __name__ == "__main__":
    main()
