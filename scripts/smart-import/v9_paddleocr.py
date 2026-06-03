"""
v9_paddleocr.py — PaddleOCR PP-OCRv3/v4 wrapper for Smart Import pipeline.

Replaces Qwen3-VL-32B for text detection + recognition.
Outputs text_elements in pipeline-compatible format.

Usage:
    from v9_paddleocr import paddleocr_detect
    texts = paddleocr_detect("poster.png")
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy singleton
# ---------------------------------------------------------------------------
_ocr_instance = None


def _get_ocr(**kwargs):
    global _ocr_instance
    if _ocr_instance is None:
        os.environ.setdefault("FLAGS_use_mkldnn", "0")
        from paddleocr import PaddleOCR

        _ocr_instance = PaddleOCR(
            use_angle_cls=True,
            lang="en",
            det_db_thresh=kwargs.get("det_thresh", 0.3),
            det_db_box_thresh=kwargs.get("box_thresh", 0.5),
            rec_batch_num=kwargs.get("rec_batch", 6),
        )
    return _ocr_instance


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def paddleocr_detect(
    image_path: str,
    det_thresh: float = 0.3,
    box_thresh: float = 0.5,
    min_text_height: float = 8.0,
    min_text_width: float = 8.0,
) -> list[dict[str, Any]]:
    """Run PaddleOCR on an image and return text_elements in pipeline format.

    Returns a list matching the ``text_elements`` schema used by V8 pipeline:
        [
            {
                "id": "t1",
                "text": "...",
                "position": {"x": ..., "y": ..., "width": ..., "height": ...},
                "colorHex": "",       # filled later by palette extraction
                "fontSize": 0,        # filled later
                "rotation": 0.0,
                "isCompleteText": True,
                "confidence": 0.99,
            },
            ...
        ]
    """
    ocr = _get_ocr(det_thresh=det_thresh, box_thresh=box_thresh)

    logger.info("  [PaddleOCR] Running PP-OCR on %s ...", os.path.basename(image_path))
    t0 = time.time()
    result = ocr.ocr(image_path)
    elapsed = time.time() - t0

    if not result or result[0] is None:
        logger.info("  [PaddleOCR] No text detected (%.2fs)", elapsed)
        return []

    detections = result[0]  # first page
    elements: list[dict[str, Any]] = []

    # Load image for orientation context
    img = cv2.imread(image_path)
    img_h, img_w = img.shape[:2] if img is not None else (1080, 1350)

    for i, det in enumerate(detections):
        bbox_quad = det[0]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        text, confidence = det[1]

        if not text or confidence < 0.5:
            continue

        # Quad → axis-aligned bounding box
        xs = [p[0] for p in bbox_quad]
        ys = [p[1] for p in bbox_quad]
        x = min(xs)
        y = min(ys)
        w = max(xs) - x
        h = max(ys) - y

        if w < min_text_width or h < min_text_height:
            continue

        # Estimate rotation from the quad's top edge
        dx = bbox_quad[1][0] - bbox_quad[0][0]
        dy = bbox_quad[1][1] - bbox_quad[0][1]
        angle = math.degrees(math.atan2(dy, dx)) if abs(dx) > 0.5 else 0.0

        elements.append({
            "id": f"t{i + 1}",
            "text": text.strip(),
            "position": {
                "x": round(x, 1),
                "y": round(y, 1),
                "width": round(w, 1),
                "height": round(h, 1),
            },
            "colorHex": "",              # filled by palette analysis
            "fontSize": round(h),         # estimate: height ≈ font size in px
            "rotation": round(angle, 1),
            "isCompleteText": True,
            "confidence": round(confidence, 4),
            "source": "paddleocr",
        })

    logger.info("  [PaddleOCR] %d text(s) detected (%.2fs)", len(elements), elapsed)
    return elements


def draw_detections(image_path: str, elements: list[dict], output_path: str):
    """Draw detected text boxes on image for visual debugging."""
    img = cv2.imread(image_path)
    if img is None:
        logger.warning("  [PaddleOCR] Cannot read %s for drawing", image_path)
        return

    for el in elements:
        pos = el["position"]
        x, y, w, h = int(pos["x"]), int(pos["y"]), int(pos["width"]), int(pos["height"])
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(img, el["text"][:30], (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    cv2.imwrite(output_path, img)
    logger.info("  [PaddleOCR] Debug image saved to %s", output_path)


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    import sys
    img = sys.argv[1] if len(sys.argv) > 1 else "generated-dataset/001/render.png"
    texts = paddleocr_detect(img)
    print(json.dumps(texts, indent=2))
