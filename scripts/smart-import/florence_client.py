"""
florence_client.py — Florence-2 via Replicate para extracción de datos de imágenes.

Tareas principales:
  - OCR_WITH_REGION: Detecta texto + bboxes en la imagen
  - DENSE_REGION_CAPTION: Detecta regiones visuales con descripciones
  - CAPTION: Descripción general de la imagen
  - OCR: Solo texto sin regiones

Formato de salida de Replicate:
  replicate.run() devuelve un dict con {'img': ..., 'text': "<Python-repr string>"}
  El text contiene un dict en formato Python repr (comillas simples, no JSON).
  Usamos ast.literal_eval() para parsearlo.
"""

from __future__ import annotations

import ast
import base64
import json
import logging
import os
import re
from typing import Any

import replicate

logger = logging.getLogger(__name__)

# Model identifier on Replicate
FLORENCE_MODEL = "lucataco/florence-2-large:da53547e17d45b9cfb48174b2f18af8b83ca020fa76db62136bf9c6616762595"


def _encode_image(image_path: str) -> str:
    """Return a base64 data URI for the given image."""
    ext = os.path.splitext(image_path)[1].lower()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime.get(ext.lstrip('.'), 'image/png')};base64,{b64}"


def _extract_text(output: Any) -> str:
    """Extract the text payload from replicate.run() output.
    
    Replicate returns either:
      - A dict with 'text' key: {'img': ..., 'text': '...'}
      - A list of strings
      - A plain string
    """
    if isinstance(output, dict):
        return output.get("text", str(output))
    if isinstance(output, list):
        return " ".join(str(item) for item in output)
    return str(output)


def _parse_python_repr(raw: str) -> dict | None:
    """Try to parse a Python-repr string (single quotes) into a dict.
    
    Example input: "{'<OCR_WITH_REGION>': {'quad_boxes': [...], 'labels': [...]}}"
    Returns None if parsing fails.
    """
    try:
        return ast.literal_eval(raw)
    except (ValueError, SyntaxError, MemoryError):
        return None


def _extract_bboxes_labels(data: dict) -> tuple[list, list]:
    """Extract bboxes and labels from a parsed Florence-2 data dict.
    
    Handles different key formats:
      - bboxes / labels (DENSE_REGION_CAPTION)
      - quad_boxes / labels (OCR_WITH_REGION)
    """
    bboxes = data.get("bboxes") or data.get("quad_boxes") or []
    labels = data.get("labels") or []
    return bboxes, labels


def _parse_boxes_text(raw: str) -> list[dict]:
    """Parse Florence-2 OCR_WITH_REGION output.
    
    Expected format in Python repr:
      {'<OCR_WITH_REGION>': {'quad_boxes': [[x0,y0,x1,y1,...]], 'labels': ['text1', 'text2']}}
    
    Returns list of {text, bbox: {x,y,w,h} normalized 0..1}
    """
    results: list[dict] = []

    # Try JSON first (standard format)
    try:
        data = json.loads(raw)
        ocr_data = data.get("OCR_WITH_REGION") or data.get("OCR") or data.get("OCRWithRegion") or data
        bboxes, labels = _extract_bboxes_labels(ocr_data)
        for bbox, label in zip(bboxes, labels):
            results.append({
                "text": label.strip(),
                "bbox": _normalize_bbox(bbox),
                "confidence": 1.0,
            })
        if results:
            return results
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

    # Try Python repr format (Replicate output)
    parsed = _parse_python_repr(raw)
    if isinstance(parsed, dict):
        for task_key in ("OCR_WITH_REGION", "OCR", "OCRWithRegion"):
            task_data = parsed.get(task_key) or parsed.get(f"<{task_key}>")
            if isinstance(task_data, dict):
                bboxes, labels = _extract_bboxes_labels(task_data)
                for bbox, label in zip(bboxes, labels):
                    results.append({
                        "text": label.strip(),
                        "bbox": _normalize_bbox(bbox),
                        "confidence": 1.0,
                    })
                if results:
                    return results

    # Fallback: text<coords> format
    pattern = re.compile(r"([^<]+)<([\d.\s]+)>")
    for match in pattern.finditer(raw):
        text = match.group(1).strip()
        coords_str = match.group(2).strip()
        coords = [float(c) for c in coords_str.split() if c.strip()]
        if len(coords) >= 4:
            results.append({
                "text": text,
                "bbox": _normalize_bbox(coords),
                "confidence": 1.0,
            })

    return results


def _parse_dense_caption(raw: str) -> list[dict]:
    """Parse DENSE_REGION_CAPTION output.
    
    Expected format in Python repr:
      {'<DENSE_REGION_CAPTION>': {'bboxes': [[x0,y0,x1,y1,...]], 'labels': ['desc1']}}
    
    Returns list of {description, bbox: {x,y,w,h} normalized 0..1}
    """
    results: list[dict] = []

    # Try JSON first
    try:
        data = json.loads(raw)
        task_data = data.get("DENSE_REGION_CAPTION") or data.get("DenseRegionCaption") or data
        bboxes, labels = _extract_bboxes_labels(task_data)
        for bbox, label in zip(bboxes, labels):
            results.append({
                "description": label.strip(),
                "bbox": _normalize_bbox(bbox),
                "confidence": 1.0,
            })
        if results:
            return results
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

    # Try Python repr format
    parsed = _parse_python_repr(raw)
    if isinstance(parsed, dict):
        for task_key in ("DENSE_REGION_CAPTION", "DenseRegionCaption"):
            task_data = parsed.get(task_key) or parsed.get(f"<{task_key}>")
            if isinstance(task_data, dict):
                bboxes, labels = _extract_bboxes_labels(task_data)
                for bbox, label in zip(bboxes, labels):
                    results.append({
                        "description": label.strip(),
                        "bbox": _normalize_bbox(bbox),
                        "confidence": 1.0,
                    })
                if results:
                    return results

    # Fallback: text<coords> format
    pattern = re.compile(r"([^<]+)<([\d.\s]+)>")
    for match in pattern.finditer(raw):
        desc = match.group(1).strip()
        coords_str = match.group(2).strip()
        coords = [float(c) for c in coords_str.split() if c.strip()]
        if len(coords) >= 4:
            results.append({
                "description": desc,
                "bbox": _normalize_bbox(coords),
                "confidence": 1.0,
            })

    return results


def _normalize_bbox(quad: list[float]) -> dict:
    """Convert quad box (x0,y0,x1,y1,x2,y2,x3,y3) to normalized (x,y,w,h)."""
    if len(quad) == 4:
        # Already x,y,w,h
        xs = [quad[0], quad[0] + quad[2]]
        ys = [quad[1], quad[1] + quad[3]]
    else:
        xs = quad[0::2]
        ys = quad[1::2]

    x_min = min(xs)
    y_min = min(ys)
    x_max = max(xs)
    y_max = max(ys)

    # Return normalized 0..1
    return {
        "x": round(max(0.0, x_min), 4),
        "y": round(max(0.0, y_min), 4),
        "w": round(max(0.0, x_max - x_min), 4),
        "h": round(max(0.0, y_max - y_min), 4),
    }


def _normalize_single_quad(quad: list[float], canvas_w: float, canvas_h: float) -> dict:
    """Convert pixel quad to normalized bbox 0..1."""
    if not quad:
        return {"x": 0, "y": 0, "w": 1, "h": 1}
    if len(quad) == 4:
        return {
            "x": max(0.0, min(1.0, quad[0] / canvas_w)),
            "y": max(0.0, min(1.0, quad[1] / canvas_h)),
            "w": max(0.0, min(1.0, quad[2] / canvas_w)),
            "h": max(0.0, min(1.0, quad[3] / canvas_h)),
        }
    xs = quad[0::2]
    ys = quad[1::2]
    return {
        "x": max(0.0, min(1.0, min(xs) / canvas_w)),
        "y": max(0.0, min(1.0, min(ys) / canvas_h)),
        "w": max(0.0, min(1.0, (max(xs) - min(xs)) / canvas_w)),
        "h": max(0.0, min(1.0, (max(ys) - min(ys)) / canvas_h)),
    }


def _run_florence(image_path: str, task: str) -> Any:
    """Execute a Florence-2 task via Replicate and return raw output."""
    return replicate.run(
        FLORENCE_MODEL,
        input={
            "image": _encode_image(image_path),
            "task_input": task,
        },
    )


def florence_ocr(image_path: str, canvas_w: float, canvas_h: float) -> list[dict]:
    """Run Florence-2 OCR with Region via Replicate.

    Returns list of {text, bbox: {x,y,w,h} normalized 0..1, confidence}
    """
    output = _run_florence(image_path, "OCR with Region")
    raw = _extract_text(output)
    logger.debug("Florence OCR raw (first 300): %s…", raw[:300])

    parsed = _parse_boxes_text(raw)

    # Normalize pixel values if not already 0..1
    for entry in parsed:
        bb = entry["bbox"]
        if bb["x"] > 1 or bb["y"] > 1:
            entry["bbox"] = _normalize_single_quad(
                [bb["x"], bb["y"], bb["x"] + bb["w"], bb["y"] + bb["h"]],
                canvas_w, canvas_h,
            )

    return parsed


def florence_dense_regions(image_path: str, canvas_w: float, canvas_h: float) -> list[dict]:
    """Run Florence-2 Dense Region Caption via Replicate.

    Returns list of {description, bbox: {x,y,w,h} normalized 0..1}
    """
    output = _run_florence(image_path, "Dense Region Caption")
    raw = _extract_text(output)
    logger.debug("Florence Dense raw (first 300): %s…", raw[:300])

    parsed = _parse_dense_caption(raw)

    for entry in parsed:
        bb = entry["bbox"]
        if bb["x"] > 1 or bb["y"] > 1:
            entry["bbox"] = _normalize_single_quad(
                [bb["x"], bb["y"], bb["x"] + bb["w"], bb["y"] + bb["h"]],
                canvas_w, canvas_h,
            )

    return parsed


def florence_caption(image_path: str) -> str:
    """Get a general caption of the image."""
    output = _run_florence(image_path, "Caption")
    raw = _extract_text(output)
    # Parse Python repr to extract just the caption text
    parsed = _parse_python_repr(raw)
    if isinstance(parsed, dict):
        # Extract from {'<CAPTION>': '...'}
        for key in ("CAPTION", "Caption"):
            val = parsed.get(key) or parsed.get(f"<{key}>")
            if val:
                return str(val)
    return raw
