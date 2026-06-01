#!/usr/bin/env python3
"""Batch render .tc files to PNG images using tc_render_standalone.js.

Usage:
    python batch_render.py --dataset generated-dataset/ --timeout 120
"""

import argparse
import json
import os
import subprocess
import sys
import time


def parse_args() -> argparse.Namespace:
    """Parse and return CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Batch render .tc design files to PNG images."
    )
    parser.add_argument(
        "--dataset",
        default="generated-dataset/",
        help="Path to dataset directory (default: generated-dataset/)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Per-render timeout in seconds (default: 120)",
    )
    return parser.parse_args()


def preflight_check(script_dir: str) -> str:
    """Verify Node.js and the render script are available. Returns the render script path.

    Exits with code 1 if either check fails.
    """
    # --- Check Node.js availability ---
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            print(
                "ERROR: Node.js is not available (node --version failed).",
                file=sys.stderr,
            )
            sys.exit(1)
    except FileNotFoundError:
        print(
            "ERROR: Node.js not found. Is it installed and on PATH?",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("ERROR: Node.js check timed out.", file=sys.stderr)
        sys.exit(1)

    # --- Check render script ---
    render_script = os.path.join(script_dir, "tc_render_standalone.js")
    if not os.path.isfile(render_script):
        print(
            f"ERROR: Render script not found at {render_script}",
            file=sys.stderr,
        )
        sys.exit(1)

    return render_script


def load_index(dataset_path: str) -> list[dict]:
    """Load and validate index.json from the dataset directory.

    Returns the list of sample metadata dicts.
    Exits with code 1 if the file is missing or malformed.
    """
    index_path = os.path.join(dataset_path, "index.json")
    if not os.path.isfile(index_path):
        print(f"ERROR: index.json not found at {index_path}", file=sys.stderr)
        sys.exit(1)

    with open(index_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(
                f"ERROR: index.json is not valid JSON — {e}",
                file=sys.stderr,
            )
            sys.exit(1)

    samples = data.get("samples")
    if not isinstance(samples, list):
        print(
            "ERROR: index.json is invalid — expected a 'samples' array.",
            file=sys.stderr,
        )
        sys.exit(1)

    return samples


def render_sample(
    sample: dict,
    idx: int,
    total: int,
    dataset_path: str,
    timeout: int,
    render_script: str,
) -> tuple[bool, str]:
    """Render a single sample to PNG.

    Returns (success, reason_or_None).
    """
    sample_id = sample.get("id", f"sample-{idx}")
    tc_rel = sample.get("path", f"{sample_id}/design.tc")
    tc_path = os.path.join(dataset_path, tc_rel)
    output_path = os.path.join(dataset_path, sample_id, "render.png")

    # --- Missing .tc file ---
    if not os.path.isfile(tc_path):
        print(f"[{idx}/{total}] WARN: {sample_id} — Missing .tc file, skipping")
        return False, "Missing .tc file"

    start = time.time()
    try:
        result = subprocess.run(
            ["node", render_script, "--tc", tc_path, "--output", output_path],
            capture_output=True,
            text=True,
            errors="backslashreplace",
            timeout=timeout,
        )
        elapsed = time.time() - start

        if result.returncode != 0:
            print(f"[{idx}/{total}] FAIL {sample_id} ({elapsed:.1f}s) — Non-zero exit code")
            return False, "Non-zero exit code"

        if not os.path.isfile(output_path):
            print(f"[{idx}/{total}] FAIL {sample_id} ({elapsed:.1f}s) — Output PNG not created")
            return False, "Output PNG not created"

        print(f"[{idx}/{total}] Rendered {sample_id} ({elapsed:.1f}s)")
        return True, ""

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        reason = f"Render timeout (exceeded {timeout}s)"
        print(f"[{idx}/{total}] FAIL {sample_id} ({elapsed:.1f}s) — {reason}")
        return False, reason

    except Exception as e:
        elapsed = time.time() - start
        reason = f"{type(e).__name__}: {e}"
        print(f"[{idx}/{total}] FAIL {sample_id} ({elapsed:.1f}s) — {reason}")
        return False, reason


def render_all(
    samples: list[dict],
    dataset_path: str,
    timeout: int,
    render_script: str,
) -> tuple[int, list[tuple[str, str]]]:
    """Render all samples sequentially.

    Returns (rendered_count, failures) where failures is a list of
    (sample_id, reason) tuples.
    """
    total = len(samples)
    rendered = 0
    failures: list[tuple[str, str]] = []

    for idx, sample in enumerate(samples, start=1):
        ok, reason = render_sample(sample, idx, total, dataset_path, timeout, render_script)
        if ok:
            rendered += 1
        else:
            sample_id = sample.get("id", f"sample-{idx}")
            failures.append((sample_id, reason))

    return rendered, failures


def print_report(
    dataset_path: str,
    total: int,
    rendered: int,
    failures: list[tuple[str, str]],
) -> None:
    """Print the summary report to stdout."""
    print()
    print("=== Batch Render Report ===")
    print(f"Dataset: {dataset_path}")
    print(f"Total samples: {total}")
    print(f"Rendered: {rendered}")
    print(f"Failed: {len(failures)}")
    for sample_id, reason in failures:
        print(f"  - {sample_id}: {reason}")


def main() -> None:
    args = parse_args()
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Preflight: verify Node.js + render script
    render_script = preflight_check(script_dir)

    # Normalize dataset path (strip trailing slash for consistency)
    dataset_path = args.dataset.rstrip("/\\")

    # Load and validate index
    samples = load_index(dataset_path)

    if len(samples) == 0:
        print("Nothing to render")
        sys.exit(0)

    # Render loop
    rendered, failures = render_all(samples, dataset_path, args.timeout, render_script)

    # Summary report
    print_report(dataset_path, len(samples), rendered, failures)


if __name__ == "__main__":
    main()
