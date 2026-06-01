"""
run_format.py — Run the Smart Import pipeline for SVG or HTML formats.

Usage:
    python run_format.py --image-dir datasets/my-designs --format svg
    python run_format.py --image-dir datasets/my-designs --format html \\
        --model google/gemini-2.5-flash --verbose

Output is saved to scripts/smart-import/output/<model>/<image>/ alongside
SceneGraph pipeline outputs for easy comparison.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time

from formats import FORMATS, get_format
from openrouter import OpenRouterClient

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def _encode_image(image_path: str) -> str:
    """Return a data URI for the given image file."""
    import base64

    ext = os.path.splitext(image_path)[1].lower()
    mime_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    mime = mime_types.get(ext, "image/png")
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def clean_llm_output(raw: str) -> str:
    """Strip markdown fences and whitespace from LLM output."""
    result = raw.strip()
    if result.startswith("```"):
        result = result.split("\n", 1)[-1] if "\n" in result else result[3:]
        result = result.rsplit("```", 1)[0] if "```" in result else result
    return result.strip()


def run_format(
    image_path: str,
    image_id: str,
    fmt_name: str,
    model: str,
    model_safe: str,
    output_dir: str,
    playwright_script: str,
    skip_analysis: bool = False,
    skip_render: bool = False,
) -> dict:
    """Run a single image through the format pipeline.

    Returns a status dict with keys: status, output_path, errors.
    """
    fmt = get_format(fmt_name)
    output_image_dir = os.path.join(output_dir, model_safe, fmt_name, image_id)
    os.makedirs(output_image_dir, exist_ok=True)

    scene_path = os.path.join(output_image_dir, "scene.json")
    raw_output_path = os.path.join(output_image_dir, f"raw{fmt['file_extension']}")
    render_path = os.path.join(output_image_dir, "render.png")

    if skip_analysis and os.path.isfile(raw_output_path):
        with open(raw_output_path, "r", encoding="utf-8") as f:
            raw_content = f.read()
        logger.info("  Using cached %s from %s", fmt_name, raw_output_path)
    else:
        client = OpenRouterClient(model=model)
        image_data_uri = _encode_image(image_path)

        messages = [
            {"role": "system", "content": fmt["system_prompt"]},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": fmt["analysis_prompt"]},
                    {"type": "image_url", "image_url": {"url": image_data_uri}},
                ],
            },
        ]

        logger.info("  Analysing with %s...", model)
        response = client.chat_completion(messages=messages)

        if response.status == "error":
            return {"status": "failed", "error": f"LLM call failed: {response.error_message}"}

        raw_content = clean_llm_output(response.content)

        # Save raw output
        with open(raw_output_path, "w", encoding="utf-8") as f:
            f.write(raw_content)
        logger.info("  Saved %s output: %s", fmt_name, raw_output_path)

    # Validate
    if fmt["validate"] is not None:
        valid, errors = fmt["validate"](raw_content)
        if not valid:
            logger.warning("  %s validation errors: %s", fmt_name, errors)
            return {"status": "failed", "error": f"Validation errors: {errors}", "output_path": raw_output_path}

    # Render
    if skip_render:
        logger.info("  Skipping render (--skip-render)")
        return {"status": "skipped", "output_path": raw_output_path}

    if fmt["render"] is not None:
        logger.info("  Rendering...")
        try:
            fmt["render"](raw_content, render_path, playwright_script)
            logger.info("  Render saved: %s", render_path)
        except RuntimeError as e:
            logger.error("  Render failed: %s", e)
            return {"status": "failed", "error": str(e), "output_path": raw_output_path}
    else:
        logger.warning("  No renderer for format '%s'", fmt_name)
        return {"status": "skipped", "output_path": raw_output_path}

    return {"status": "success", "output_path": raw_output_path, "render_path": render_path}


def find_images(dataset_dir: str, filter_image: str | None = None) -> list[tuple[str, str]]:
    """Find all images in the dataset directory.

    Supports two layouts:
    - Subdirectory per image:  dataset/<id>/<id>.png
    - Flat:                   dataset/<id>.jpg

    Returns list of (image_path, image_id) tuples.
    """
    supported_exts = (".png", ".jpg", ".jpeg", ".webp")
    results: list[tuple[str, str]] = []

    # Try flat structure first
    for fname in sorted(os.listdir(dataset_dir)):
        fpath = os.path.join(dataset_dir, fname)
        if not os.path.isfile(fpath):
            continue
        stem, ext = os.path.splitext(fname)
        if ext.lower() in supported_exts:
            if filter_image is None or stem == filter_image:
                results.append((fpath, stem))

    # If flat found nothing, try subdirectory-per-image
    if not results:
        for entry in sorted(os.listdir(dataset_dir)):
            entry_path = os.path.join(dataset_dir, entry)
            if not os.path.isdir(entry_path):
                continue
            for ext in supported_exts:
                img_path = os.path.join(entry_path, f"{entry}{ext}")
                if os.path.isfile(img_path):
                    if filter_image is None or entry == filter_image:
                        results.append((img_path, entry))
                    break

    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run SVG/HTML format pipeline")
    parser.add_argument(
        "--image-dir",
        "-d",
        required=True,
        help="Dataset directory containing image subdirectories",
    )
    parser.add_argument(
        "--format",
        "-f",
        required=True,
        choices=[k for k in FORMATS if k != "scenegraph"],
        help="Output format to test",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Vision model (default: from env or google/gemini-2.5-flash)",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--image",
        default=None,
        metavar="ID",
        help="Specific image ID to process (default: all)",
    )
    parser.add_argument(
        "--skip-analysis",
        action="store_true",
        help="Skip LLM call, reuse cached raw output",
    )
    parser.add_argument(
        "--skip-render",
        action="store_true",
        help="Skip rendering phase",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="DEBUG-level logging",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )

    model = args.model or os.getenv("DEFAULT_VISION_MODEL", "google/gemini-2.5-flash")
    model_safe = model.replace("/", "-").replace(".", "-")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    playwright_script = os.path.join(script_dir, "render_page.mjs")

    images = find_images(args.image_dir, args.image)
    if not images:
        logger.error("No images found in %s", args.image_dir)
        sys.exit(1)

    logger.info("Format: %s  |  Model: %s  |  Images: %d", args.format, model, len(images))

    results: list[dict] = []
    for img_path, img_id in images:
        logger.info("\n[%s] %s", args.format, img_id)
        t0 = time.monotonic()
        result = run_format(
            image_path=img_path,
            image_id=img_id,
            fmt_name=args.format,
            model=model,
            model_safe=model_safe,
            output_dir=args.output,
            playwright_script=playwright_script,
            skip_analysis=args.skip_analysis,
            skip_render=args.skip_render,
        )
        elapsed = time.monotonic() - t0
        result["image_id"] = img_id
        result["elapsed"] = round(elapsed, 1)
        results.append(result)

        status_icon = "OK" if result["status"] == "success" else "FAIL"
        logger.info("  [%s] %s  (%.1fs)", status_icon, result["status"], elapsed)

    # Summary
    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")
    logger.info(
        "\nDone: %d success, %d failed, %d skipped  (total: %d)",
        success,
        failed,
        len(results) - success - failed,
        len(results),
    )
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
