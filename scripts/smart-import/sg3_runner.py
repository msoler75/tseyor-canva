"""
sg3_runner.py — Smart Import V2 con 3 prompts secuenciales.

Usa el sistema de 3 prompts (composición → texto → imágenes/formas) con
coordenadas normalizadas (0..1) para los 3 formatos: SceneGraph, SVG, HTML.

Uso:
    python sg3_runner.py --image-dir datasets --format scenegraph
    python sg3_runner.py --image-dir datasets --format svg --verbose
    python sg3_runner.py --image-dir datasets --format html --image poster-simple
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from typing import Any, Optional

from formats_v2 import (
    SYSTEM_PROMPT_1,
    ANALYSIS_PROMPT_1,
    build_prompt_2,
    SYSTEM_PROMPT_2,
    build_prompt_3,
    SYSTEM_PROMPT_3,
    assemble,
    generate_scenegraph,
    generate_svg,
    generate_html,
    validate_assembly,
    render_svg_v2,
    render_html_v2,
)
from openrouter import OpenRouterClient

logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
PLAYWRIGHT_SCRIPT = os.path.join(SCRIPT_DIR, "render_page.mjs")


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def parse_llm_json(raw: str) -> dict:
    """Parse JSON from LLM response, stripping markdown fences."""
    content = raw.strip()
    if content.startswith("```"):
        # Strip fences (```json ... ``` or just ``` ... ```)
        if "\n" in content:
            content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        content = content.strip()
    return json.loads(content)


def get_image_dimensions(image_path: str) -> tuple[float, float]:
    """Get image width and height in pixels."""
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            return float(img.width), float(img.height)
    except ImportError:
        # Fallback: try to get from file using image_utils
        logger.warning("Pillow not available, using default dimensions")
        return 1080.0, 1920.0


def find_images(dataset_dir: str, filter_image: str | None = None) -> list[tuple[str, str]]:
    """Find all images in the dataset directory.

    Supports flat and subdirectory layouts.
    """
    supported_exts = (".png", ".jpg", ".jpeg", ".webp")
    results: list[tuple[str, str]] = []

    # Try flat
    for fname in sorted(os.listdir(dataset_dir)):
        fpath = os.path.join(dataset_dir, fname)
        if not os.path.isfile(fpath):
            continue
        stem, ext = os.path.splitext(fname)
        if ext.lower() in supported_exts:
            if filter_image is None or stem == filter_image:
                results.append((fpath, stem))

    # Try subdirectory
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


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT PATHS
# ═══════════════════════════════════════════════════════════════════════════════

def _output_paths(output_dir: str, model_safe: str, fmt: str, image_id: str) -> dict:
    """Get all output paths for an image."""
    base = os.path.join(output_dir, model_safe, f"{fmt}-v2", image_id)
    return {
        "base": base,
        "prompt_1": os.path.join(base, "prompt-1-composition.json"),
        "prompt_2": os.path.join(base, "prompt-2-text.json"),
        "prompt_3": os.path.join(base, "prompt-3-shapes.json"),
        "assembly": os.path.join(base, "assembly.json"),
        "scene": os.path.join(base, "scene.json"),
        "render": os.path.join(base, "render.png"),
        "output": os.path.join(base, f"output.{'json' if fmt == 'scenegraph' else ('svg' if fmt == 'svg' else 'html')}"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def run_v2(
    image_path: str,
    image_id: str,
    fmt: str,
    model: str,
    model_safe: str,
    output_dir: str,
    skip_analysis: bool = False,
    skip_render: bool = False,
) -> dict:
    """Run the V2 pipeline for a single image.

    Returns status dict with keys:
        status, image_id, elapsed, paths, assembly, errors
    """
    paths = _output_paths(output_dir, model_safe, fmt, image_id)
    os.makedirs(paths["base"], exist_ok=True)

    client = OpenRouterClient(model=model)
    canvas_w, canvas_h = get_image_dimensions(image_path)

    result: dict = {
        "status": "success",
        "image_id": image_id,
        "paths": paths,
        "errors": [],
    }

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 1: Spatial Composition
    # ═══════════════════════════════════════════════════════════════════════
    p1: Optional[dict] = None
    if not skip_analysis and os.path.isfile(paths["prompt_1"]):
        with open(paths["prompt_1"], "r", encoding="utf-8") as f:
            p1 = json.load(f)
        logger.info("  [P1] Cached composition")

    if p1 is None:
        logger.info("  [P1] Spatial composition...")
        try:
            raw = client.vision_analyze(
                image_path=image_path,
                prompt=ANALYSIS_PROMPT_1,
                system_prompt=SYSTEM_PROMPT_1,
                model=model,
            )
            p1 = raw  # vision_analyze already returns dict
            with open(paths["prompt_1"], "w", encoding="utf-8") as f:
                json.dump(p1, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("  [P1] Failed: %s", e)
            return {"status": "failed", "errors": [f"P1: {e}"]}

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 2: Text Extraction
    # ═══════════════════════════════════════════════════════════════════════
    p2: Optional[dict] = None
    p1_json_str = json.dumps(p1, indent=2, ensure_ascii=False)

    if not skip_analysis and os.path.isfile(paths["prompt_2"]):
        with open(paths["prompt_2"], "r", encoding="utf-8") as f:
            p2 = json.load(f)
        logger.info("  [P2] Cached text")

    if p2 is None:
        prompt_2 = build_prompt_2(p1_json_str)
        logger.info("  [P2] Text extraction...")
        try:
            raw = client.vision_analyze(
                image_path=image_path,
                prompt=prompt_2,
                system_prompt=SYSTEM_PROMPT_2,
                model=model,
            )
            p2 = raw
            with open(paths["prompt_2"], "w", encoding="utf-8") as f:
                json.dump(p2, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("  [P2] Failed: %s", e)
            return {"status": "failed", "errors": [f"P2: {e}"]}

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 3: Images, Shapes & Effects
    # ═══════════════════════════════════════════════════════════════════════
    p3: Optional[dict] = None
    p2_json_str = json.dumps(p2, indent=2, ensure_ascii=False)

    if not skip_analysis and os.path.isfile(paths["prompt_3"]):
        with open(paths["prompt_3"], "r", encoding="utf-8") as f:
            p3 = json.load(f)
        logger.info("  [P3] Cached shapes/images")

    if p3 is None:
        prompt_3 = build_prompt_3(p1_json_str, p2_json_str)
        logger.info("  [P3] Images, shapes & effects...")
        try:
            raw = client.vision_analyze(
                image_path=image_path,
                prompt=prompt_3,
                system_prompt=SYSTEM_PROMPT_3,
                model=model,
            )
            p3 = raw
            with open(paths["prompt_3"], "w", encoding="utf-8") as f:
                json.dump(p3, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("  [P3] Failed: %s", e)
            return {"status": "failed", "errors": [f"P3: {e}"]}

    # ═══════════════════════════════════════════════════════════════════════
    # ASSEMBLY
    # ═══════════════════════════════════════════════════════════════════════
    logger.info("  Assembly...")
    assembly = assemble(p1, p2, p3)
    with open(paths["assembly"], "w", encoding="utf-8") as f:
        json.dump(assembly, f, indent=2, ensure_ascii=False)

    # Enrich canvas with actual dimensions
    assembly["canvas"]["width"] = canvas_w
    assembly["canvas"]["height"] = canvas_h

    # Validate
    valid, errors = validate_assembly(assembly)
    if not valid:
        logger.warning("  Assembly validation warnings: %s", errors)
        result["errors"].extend(errors)
        # Continue anyway — clamping handles minor violations

    # ═══════════════════════════════════════════════════════════════════════
    # FORMAT-SPECIFIC GENERATION
    # ═══════════════════════════════════════════════════════════════════════
    logger.info("  Generating %s...", fmt)

    if fmt == "scenegraph":
        sg = generate_scenegraph(assembly)
        with open(paths["scene"], "w", encoding="utf-8") as f:
            json.dump(sg, f, indent=2, ensure_ascii=False)
        with open(paths["output"], "w", encoding="utf-8") as f:
            json.dump(sg, f, indent=2, ensure_ascii=False)

    elif fmt == "svg":
        svg_content = generate_svg(assembly, canvas_w, canvas_h)
        with open(paths["output"], "w", encoding="utf-8") as f:
            f.write(svg_content)

        if not skip_render:
            logger.info("  Rendering SVG...")
            try:
                render_svg_v2(svg_content, paths["render"], PLAYWRIGHT_SCRIPT)
                logger.info("  Render: %s", paths["render"])
            except RuntimeError as e:
                logger.error("  Render failed: %s", e)
                result["errors"].append(str(e))
                result["status"] = "failed"
                return result

    elif fmt == "html":
        html_content = generate_html(assembly, canvas_w, canvas_h)
        with open(paths["output"], "w", encoding="utf-8") as f:
            f.write(html_content)

        if not skip_render:
            logger.info("  Rendering HTML...")
            try:
                render_html_v2(html_content, paths["render"], PLAYWRIGHT_SCRIPT)
                logger.info("  Render: %s", paths["render"])
            except RuntimeError as e:
                logger.error("  Render failed: %s", e)
                result["errors"].append(str(e))
                result["status"] = "failed"
                return result

    else:
        result["errors"].append(f"Unknown format: {fmt}")
        result["status"] = "failed"
        return result

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Smart Import V2 — 3-prompt system with normalized coordinates"
    )
    parser.add_argument(
        "--image-dir", "-d", required=True,
        help="Dataset directory with images",
    )
    parser.add_argument(
        "--format", "-f", required=True,
        choices=["scenegraph", "svg", "html"],
        help="Output format",
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
        help="Skip LLM calls, reuse cached prompt outputs",
    )
    parser.add_argument(
        "--skip-render",
        action="store_true",
        help="Skip rendering phase",
    )
    parser.add_argument(
        "--verbose", "-v",
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

    images = find_images(args.image_dir, args.image)
    if not images:
        logger.error("No images found in %s", args.image_dir)
        sys.exit(1)

    logger.info(
        "V2 Pipeline | Format: %s | Model: %s | Images: %d",
        args.format, model, len(images),
    )

    results: list[dict] = []
    for img_path, img_id in images:
        logger.info("\n[%s-v2] %s", args.format, img_id)
        t0 = time.monotonic()
        result = run_v2(
            image_path=img_path,
            image_id=img_id,
            fmt=args.format,
            model=model,
            model_safe=model_safe,
            output_dir=args.output,
            skip_analysis=args.skip_analysis,
            skip_render=args.skip_render,
        )
        elapsed = time.monotonic() - t0
        result["elapsed"] = round(elapsed, 1)
        results.append(result)

        icon = "OK" if result["status"] == "success" else "FAIL"
        logger.info("  [%s] %s  (%.1fs)", icon, result["status"], elapsed)

        if result.get("errors"):
            for e in result["errors"]:
                logger.info("    Error: %s", e)

    # Summary
    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")
    logger.info(
        "\nDone: %d success, %d failed, %d skipped  (total: %d)",
        success, failed,
        len(results) - success - failed,
        len(results),
    )
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
