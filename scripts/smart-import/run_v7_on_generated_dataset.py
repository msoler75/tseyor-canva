"""
run_v7_on_generated_dataset.py -- Batch runner for pipeline_v7 on the generated dataset.

Stages:
  1. Stage render images from generated-dataset/ into a temp staging directory
     (scripts/smart-import/dataset_generated/) with image_id names like generated-001.png.
  2. Run pipeline_v7 (process_image_v7) for each sample x variant.
  3. Collect results, timing, and write a summary report JSON.

Usage:
    python scripts/smart-import/run_v7_on_generated_dataset.py
    python scripts/smart-import/run_v7_on_generated_dataset.py --variant A
    python scripts/smart-import/run_v7_on_generated_dataset.py --variant B
    python scripts/smart-import/run_v7_on_generated_dataset.py --variant all --samples 5-15
    python scripts/smart-import/run_v7_on_generated_dataset.py --keep-temp --model "google/gemini-2.5-flash"
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import time
from typing import Any

# Ensure scripts/smart-import is on sys.path so we can import pipeline_v7 directly
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from pipeline_v7 import process_image_v7, PROMPT_VARIANTS

logger = logging.getLogger("run_v7_generated")
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    stream=sys.stdout,
)

# ----------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------
DATASET_DIR = os.path.normpath(
    os.path.join(SCRIPT_DIR, "..", "..", "generated-dataset")
)
STAGING_DIR = os.path.join(SCRIPT_DIR, "dataset_generated")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
REPORT_PATH = os.path.join(OUTPUT_DIR, "v7_generated_batch_report.json")

SAMPLE_IDS = [f"{i:03d}" for i in range(1, 21)]  # 001 ... 020

VARIANTS: tuple[str, ...] = ("A", "B")


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def parse_sample_range(spec: str) -> list[str]:
    """Parse a range string like '1-5' or '3' into a list of zero-padded IDs."""
    spec = spec.strip()
    if "-" in spec:
        parts = spec.split("-", 1)
        lo = int(parts[0])
        hi = int(parts[1])
        return [f"{i:03d}" for i in range(lo, hi + 1)]
    else:
        return [f"{int(spec):03d}"]


def stage_images(sample_ids: list[str]) -> str:
    """Copy render.png from each sample to the staging dir as generated-XXX.png.

    Returns the staging directory path.
    """
    os.makedirs(STAGING_DIR, exist_ok=True)
    for sid in sample_ids:
        src = os.path.join(DATASET_DIR, sid, "render.png")
        dst = os.path.join(STAGING_DIR, f"generated-{sid}.png")
        if not os.path.isfile(src):
            logger.warning("  [STAGE] Missing render for sample %s -- skipping", sid)
            continue
        shutil.copy2(src, dst)
        logger.info("  [STAGE] %s -> generated-%s.png", src, sid)
    return STAGING_DIR


def cleanup_staging(keep: bool = False) -> None:
    """Remove the staging directory unless --keep-temp was passed."""
    if keep:
        logger.info("  [CLEANUP] Keeping staging directory: %s", STAGING_DIR)
        return
    if os.path.isdir(STAGING_DIR):
        shutil.rmtree(STAGING_DIR)
        logger.info("  [CLEANUP] Removed staging directory: %s", STAGING_DIR)
    else:
        logger.info("  [CLEANUP] No staging directory to clean up.")


def run_batch(
    sample_ids: list[str],
    variants: list[str],
    model: str,
    render: bool = False,
) -> list[dict[str, Any]]:
    """Sequentially run process_image_v7 for each sample x variant.

    Returns a list of result dictionaries (one per run).
    """
    total_runs = len(sample_ids) * len(variants)
    results: list[dict[str, Any]] = []
    run_idx = 0

    for sid in sample_ids:
        image_path = os.path.join(STAGING_DIR, f"generated-{sid}.png")
        if not os.path.isfile(image_path):
            for v in variants:
                run_idx += 1
                logger.error(
                    "[%d/%d] variant=%s sample=%s ... FAIL (staged image not found)",
                    run_idx, total_runs, v, sid,
                )
                results.append({
                    "sample": sid,
                    "variant": v,
                    "image_id": f"generated-{sid}",
                    "status": "failed",
                    "errors": [f"Staged image not found: {image_path}"],
                    "elapsed_seconds": 0.0,
                })
            continue

        for v in variants:
            run_idx += 1
            t0 = time.monotonic()

            try:
                r = process_image_v7(
                    image_path=image_path,
                    output_dir=OUTPUT_DIR,
                    prompt_variant=v,
                    detection_model=model,
                    reconstructor_model=None,
                    inpaint_method="opencv",
                    skip_detection=False,
                    skip_render=not render,
                    skip_text_analyzer=False,
                )
                elapsed = time.monotonic() - t0
                status = r.get("status", "failed")
                if status == "success":
                    logger.info(
                        "[%d/%d] variant=%s sample=%s ... OK  (%.1fs)",
                        run_idx, total_runs, v, sid, elapsed,
                    )
                else:
                    logger.error(
                        "[%d/%d] variant=%s sample=%s ... FAIL (%.1fs)  %s",
                        run_idx, total_runs, v, sid, elapsed,
                        r.get("errors", []),
                    )

                results.append({
                    "sample": sid,
                    "variant": v,
                    "image_id": f"generated-{sid}",
                    "status": status,
                    "errors": r.get("errors", []),
                    "elapsed_seconds": round(elapsed, 2),
                })

            except Exception as exc:
                elapsed = time.monotonic() - t0
                logger.error(
                    "[%d/%d] variant=%s sample=%s ... EXCEPTION (%.1fs)  %s",
                    run_idx, total_runs, v, sid, elapsed, exc,
                )
                results.append({
                    "sample": sid,
                    "variant": v,
                    "image_id": f"generated-{sid}",
                    "status": "exception",
                    "errors": [str(exc)],
                    "elapsed_seconds": round(elapsed, 2),
                })

    return results


def build_report(
    results: list[dict[str, Any]],
    sample_ids: list[str],
    variants: list[str],
    model: str,
    total_elapsed: float,
) -> dict[str, Any]:
    """Aggregate results into a summary report dictionary."""
    total = len(results)
    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] in ("failed", "exception"))

    runs: list[dict[str, Any]] = []
    for r in results:
        runs.append({
            "sample": r["sample"],
            "variant": r["variant"],
            "image_id": r["image_id"],
            "status": r["status"],
            "errors": r.get("errors", []),
            "elapsed_seconds": r.get("elapsed_seconds", 0.0),
        })

    # Per-sample summary
    per_sample: dict[str, dict[str, Any]] = {}
    for r in results:
        sid = r["sample"]
        if sid not in per_sample:
            per_sample[sid] = {
                "sample": sid,
                "variants": {},
                "any_failed": False,
            }
        per_sample[sid]["variants"][r["variant"]] = {
            "status": r["status"],
            "errors": r.get("errors", []),
            "elapsed_seconds": r.get("elapsed_seconds", 0.0),
        }
        if r["status"] != "success":
            per_sample[sid]["any_failed"] = True

    return {
        "dataset": "generated-dataset",
        "model": model,
        "skip_render": True,
        "staging_dir": STAGING_DIR,
        "total_samples": len(sample_ids),
        "variants_run": list(variants),
        "total_runs": total,
        "successful_runs": success,
        "failed_runs": failed,
        "total_elapsed_seconds": round(total_elapsed, 2),
        "runs": runs,
        "per_sample": sorted(per_sample.values(), key=lambda x: x["sample"]),
    }


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------


def main() -> None:
    p = argparse.ArgumentParser(
        description="Run pipeline_v7 on the generated dataset (samples 001-020)."
    )
    p.add_argument(
        "--variant",
        default="all",
        choices=["A", "B", "all"],
        help="Which prompt variant(s) to run (default: all).",
    )
    p.add_argument(
        "--samples",
        default=None,
        help="Range of samples to process, e.g. '1-5' or '3' (default: all 001-020).",
    )
    p.add_argument(
        "--keep-temp",
        action="store_true",
        help="Do NOT delete the staging directory after the run.",
    )
    p.add_argument(
        "--render",
        action="store_true",
        help="Also compile to .tc and render (default: skip render).",
    )
    p.add_argument(
        "--model",
        default="qwen/qwen3-vl-32b-instruct",
        help="Detection model override (default: qwen/qwen3-vl-32b-instruct).",
    )
    args = p.parse_args()

    # -- Resolve sample IDs --------------------------------------------
    if args.samples:
        sample_ids = parse_sample_range(args.samples)
    else:
        sample_ids = list(SAMPLE_IDS)

    # Validate that each requested sample exists on disk.
    valid_ids: list[str] = []
    for sid in sample_ids:
        sample_dir = os.path.join(DATASET_DIR, sid)
        if os.path.isdir(sample_dir):
            valid_ids.append(sid)
        else:
            logger.warning("  [INIT] Sample directory not found, skipping: %s", sample_dir)
    sample_ids = valid_ids

    if not sample_ids:
        logger.error("No valid samples found. Aborting.")
        sys.exit(1)

    # -- Resolve variants ----------------------------------------------
    if args.variant == "all":
        variants = list(VARIANTS)
    else:
        variants = [args.variant]

    logger.info("=" * 60)
    logger.info("V7 Generated Dataset Batch Runner")
    logger.info("  Samples : %s -- %s (%d total)", sample_ids[0], sample_ids[-1], len(sample_ids))
    logger.info("  Variants: %s", variants)
    logger.info("  Model   : %s", args.model)
    logger.info("  Staging : %s", STAGING_DIR)
    logger.info("  Output  : %s", OUTPUT_DIR)
    logger.info("  Keep tmp: %s", args.keep_temp)
    logger.info("  Render  : %s", args.render)
    logger.info("=" * 60)

    t_start = time.monotonic()

    # -- Stage images --------------------------------------------------
    logger.info("\n-- Stage images --")
    stage_images(sample_ids)

    # -- Run pipeline --------------------------------------------------
    logger.info("\n-- Running pipeline_v7 --")
    results = run_batch(
        sample_ids=sample_ids,
        variants=variants,
        model=args.model,
        render=args.render,
    )

    total_elapsed = time.monotonic() - t_start

    # -- Build & write report ------------------------------------------
    report = build_report(results, sample_ids, variants, args.model, total_elapsed)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # -- Summary -------------------------------------------------------
    logger.info("\n" + "=" * 60)
    logger.info("BATCH COMPLETE")
    logger.info("  Total runs : %d", report["total_runs"])
    logger.info("  Succeeded  : %d", report["successful_runs"])
    logger.info("  Failed     : %d", report["failed_runs"])
    logger.info("  Elapsed    : %.1fs (%.1f min)", total_elapsed, total_elapsed / 60)
    logger.info("  Report     : %s", REPORT_PATH)
    logger.info("=" * 60)

    # -- Cleanup -------------------------------------------------------
    cleanup_staging(keep=args.keep_temp)


if __name__ == "__main__":
    main()
