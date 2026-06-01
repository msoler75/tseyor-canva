"""
compare_text_detection.py — v5: 
  - GT de posición: EasyOCR (agrupado, más fiable para bboxes)
  - GT de texto: .tc reference (sabe qué textos esperar)
  - EasyOCR como calibración, NO evaluado
"""
import json, sys, os, time, logging, argparse, re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import cv2
import easyocr

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
logger = logging.getLogger("compare")

def bbox_iou(a: dict, b: dict) -> float:
    ax1, ay1 = a["x"], a["y"]
    ax2, ay2 = a["x"] + a["w"], a["y"] + a["h"]
    bx1, by1 = b["x"], b["y"]
    bx2, by2 = b["x"] + b["w"], b["y"] + b["h"]
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union > 0 else 0.0

def text_norm(t: str) -> str:
    return t.strip().lower().replace("\u00b7", ".").replace("\u2022", ".").replace("</s>", "").strip()


# ═══════════════════════════════════════════════════════════════════════
# GROUND TRUTH
# ═══════════════════════════════════════════════════════════════════════

def load_tc_texts(image_path: Path) -> list[str]:
    """Get expected texts from the reference .tc file (ground truth of CONTENT)."""
    stem = image_path.stem
    tc_path = SCRIPT_DIR / "output" / "google-gemini-2-5-flash" / stem / "design.tc"
    if not tc_path.is_file():
        return []
    with open(tc_path) as f:
        match = re.search(r'({.*})', f.read(), re.DOTALL)
    if not match:
        return []
    tc = json.loads(match.group(1))
    content = tc.get("pages", [{}])[0].get("content", {})
    # content has: title, subtitle, meta, contact — filter out empty
    return [v for v in content.values() if v.strip()]


def build_position_gt(image_path: str) -> tuple[list[dict], list[dict]]:
    """Build position ground truth from EasyOCR (grouped).
    
    Returns (position_gt, raw_easy_detections) where position_gt has
    grouped texts + merged bboxes.
    """
    reader = easyocr.Reader(["en"], gpu=False)
    img = cv2.imread(image_path)
    h, w = img.shape[:2]
    raw = reader.readtext(img)
    
    entries = []
    for (coords, text, conf) in raw:
        xs = [p[0] for p in coords]
        ys = [p[1] for p in coords]
        entries.append({
            "text": text.strip(),
            "conf": conf,
            "x_min": min(xs), "x_max": max(xs),
            "y_min": min(ys), "y_max": max(ys),
        })
    
    # Sort by y, merge horizontally adjacent on same row
    entries.sort(key=lambda e: e["y_min"])
    merged = []
    for e in entries:
        if merged and abs(e["y_min"] - merged[-1]["y_min"]) < max(20, 0.03 * h):
            prev = merged[-1]
            if e["x_min"] - prev["x_max"] < 60:
                prev["text"] += " " + e["text"]
                prev["x_max"] = max(prev["x_max"], e["x_max"])
                prev["y_max"] = max(prev["y_max"], e["y_max"])
                continue
        merged.append(e)
    
    gt = []
    for m in merged:
        x = m["x_min"] / w
        y = m["y_min"] / h
        bw = (m["x_max"] - m["x_min"]) / w
        bh = (m["y_max"] - m["y_min"]) / h
        gt.append({
            "text": m["text"],
            "bbox": {"x": round(x, 4), "y": round(y, 4), "w": round(bw, 4), "h": round(bh, 4)},
        })
    
    # Raw dets for EasyOCR evaluation (ungrouped)
    raw_dets = []
    for (coords, text, conf) in raw:
        xs = [p[0] for p in coords]
        ys = [p[1] for p in coords]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        raw_dets.append({
            "text": text.strip(), "confidence": round(conf, 3),
            "bbox": {"x": round(x_min/w, 4), "y": round(y_min/h, 4),
                     "w": round((x_max-x_min)/w, 4), "h": round((y_max-y_min)/h, 4)}
        })
    
    logger.info("  [GT] %d position references (from %d EasyOCR raw)",
                len(gt), len(raw_dets))
    return gt, raw_dets


# ═══════════════════════════════════════════════════════════════════════
# MATCHING
# ═══════════════════════════════════════════════════════════════════════

def match_model_to_gt(detections: list[dict], position_gt: list[dict],
                      expected_texts: list[str], model_name: str) -> dict:
    """Match model detections against position GT + expected texts.
    
    Metrics:
    - text_recall: % of expected texts found (by text content)
    - position_precision: % of detections with correct position (IoU > 0.15)
    - avg_iou: average IoU of position-matched texts
    """
    matched_gt_idx = set()
    text_found = {tn: False for tn in expected_texts}
    
    for det in detections:
        dtn = text_norm(det["text"])
        # Check for text match against expected texts
        for exp_text in expected_texts:
            tn = text_norm(exp_text)
            if dtn == tn or (len(set(dtn.split()) & set(tn.split())) / max(len(set(dtn.split())), len(set(tn.split()))) >= 0.8):
                text_found[exp_text] = True
                break
        
        # Check for position match
        best_iou, best_idx = 0.0, None
        for i, gt_ref in enumerate(position_gt):
            iou = bbox_iou(det["bbox"], gt_ref["bbox"])
            if iou > best_iou:
                best_iou, best_idx = iou, i
        if best_iou >= 0.15 and best_idx is not None:
            matched_gt_idx.add(best_idx)
    
    texts_expected = len(expected_texts)
    texts_detected = len(text_found)
    texts_recalled = sum(1 for v in text_found.values() if v)
    
    tp = len(matched_gt_idx)
    fp = len(detections) - tp
    fn = len(position_gt) - tp
    
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / len(position_gt) if position_gt else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    
    # Avg IoU of position matches
    ious = []
    for di, det in enumerate(detections):
        best_iou, _ = match_iou(det["bbox"], position_gt)
        if best_iou >= 0.15:
            ious.append(best_iou)
    avg_iou = sum(ious) / len(ious) if ious else 0.0
    
    text_recall = texts_recalled / texts_expected if texts_expected > 0 else 0.0
    
    logger.info(f"  [{model_name}] TextRecall={text_recall:.3f} ({texts_recalled}/{texts_expected}) "
                f"Pos: TP={tp} FP={fp} FN={fn} Prec={prec:.3f} Rec={rec:.3f} F1={f1:.3f} IoU={avg_iou:.3f}")
    
    return {
        "model": model_name,
        "texts_expected": texts_expected,
        "texts_recalled": texts_recalled,
        "text_recall": round(text_recall, 3),
        "texts_not_found": [t for t, v in text_found.items() if not v][:5],
        "position_tp": tp, "position_fp": fp, "position_fn": fn,
        "position_precision": round(prec, 3),
        "position_recall": round(rec, 3),
        "position_f1": round(f1, 3),
        "position_avg_iou": round(avg_iou, 3),
    }


def match_iou(bbox, gt_list):
    best_iou, best_idx = 0.0, None
    for i, g in enumerate(gt_list):
        iou = bbox_iou(bbox, g["bbox"])
        if iou > best_iou:
            best_iou, best_idx = iou, i
    return best_iou, best_idx


# ═══════════════════════════════════════════════════════════════════════
# MODEL RUNNERS
# ═══════════════════════════════════════════════════════════════════════

def run_florence(image_path):
    cache_path = os.path.join(SCRIPT_DIR, "output", "florence_fix_test", "cache.json")
    if not os.path.isfile(cache_path):
        return []
    with open(cache_path) as f:
        cache = json.load(f)
    dets = []
    for o in cache.get("ocr", []):
        b = o.get("bbox", {})
        dets.append({
            "text": o.get("text", ""),
            "confidence": o.get("confidence", 1.0),
            "bbox": dict(b),
        })
    return dets


def run_qwen(image_path):
    stem = Path(image_path).stem
    for variant in ["v6-D", "v6-B", "v4"]:
        det_path = SCRIPT_DIR / "output" / "qwen-qwen3-vl-32b-instruct" / variant / stem / "detection.json"
        if det_path.is_file():
            break
    if not det_path.is_file():
        return []
    
    with open(det_path) as f:
        det = json.load(f)
    canvas = det.get("canvas", {})
    cw = float(canvas.get("width", 1080))
    ch = float(canvas.get("height", 1350))
    dets = []
    for t in det.get("text_elements", []):
        pos = t.get("position", {})
        x = float(pos.get("x", 0))
        y = float(pos.get("y", 0))
        w = float(pos.get("width", pos.get("w", 0)))
        h = float(pos.get("height", pos.get("h", 0)))
        if max(x, y, w, h) <= 1:
            bbox = {"x": x, "y": y, "w": w, "h": h}
        else:
            bbox = {"x": x/cw, "y": y/ch, "w": w/cw, "h": h/ch}
        dets.append({"text": t.get("text",""), "confidence": 1.0, "bbox": bbox})
    return dets


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def run_all(image_path_str: str):
    image_path = Path(image_path_str) if Path(image_path_str).is_absolute() else SCRIPT_DIR / image_path_str
    image_id = image_path.stem

    if not image_path.is_file():
        logger.error("Image not found: %s", image_path)
        return

    # Ground truths
    expected_texts = load_tc_texts(image_path)
    pos_gt, easy_dets = build_position_gt(str(image_path))

    if not expected_texts:
        logger.error("No .tc reference for %s", image_id)
        return

    logger.info("\n%s", "=" * 70)
    logger.info("Text Detection Comparison — %s", image_id)
    logger.info("%s", "=" * 70)
    logger.info("Expected texts (from .tc): %d", len(expected_texts))
    for t in expected_texts:
        logger.info("  '%s'", t)
    logger.info("Position references (EasyOCR grouped): %d", len(pos_gt))
    for g in pos_gt:
        b = g["bbox"]
        logger.info("  '%s' -> (% .3f, % .3f) % .3fx % .3f",
                    g["text"][:30], b["x"], b["y"], b["w"], b["h"])

    results = []
    runners = [
        ("Florence-2 (fixed)", run_florence),
        ("Qwen3-VL-32B", run_qwen),
    ]
    for name, runner in runners:
        logger.info("\n--- %s ---", name)
        t0 = time.monotonic()
        dets = runner(str(image_path))
        elapsed = time.monotonic() - t0
        r = match_model_to_gt(dets, pos_gt, expected_texts, name)
        r["time_sec"] = round(elapsed, 1)
        results.append(r)

    logger.info("\n%s", "=" * 70)
    logger.info("SUMMARY — Text Detection on %s", image_id)
    logger.info("%s", "=" * 70)
    hdr = (f"{'Model':25s} {'TRec':>5s} {'TPos':>4s} {'FPos':>4s} {'FNPos':>4s} "
           f"{'Prec':>6s} {'Rec':>6s} {'F1':>6s} {'IoU':>6s} {'Time':>6s}")
    logger.info(hdr)
    logger.info("-" * 78)
    for r in results:
        logger.info(f"{r['model']:25s} {r['text_recall']:>5.3f} {r['position_tp']:>4d} "
                    f"{r['position_fp']:>4d} {r['position_fn']:>4d} "
                    f"{r['position_precision']:>6.3f} {r['position_recall']:>6.3f} "
                    f"{r['position_f1']:>6.3f} {r['position_avg_iou']:>6.3f}  {r['time_sec']:>5.1f}s")
    
    return results

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--image", default="dataset/poster-simple.jpg")
    args = p.parse_args()
    run_all(args.image)
