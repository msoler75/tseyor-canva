"""Batch comparison: test Qwen across all dataset images"""
import sys, json, time, logging
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import cv2
import easyocr

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
logger = logging.getLogger("batch")

from compare_text_detection import (
    load_tc_texts, build_position_gt, match_model_to_gt, bbox_iou, text_norm
)

# ── Run Qwen on an image ──

def run_qwen(image_path):
    stem = Path(image_path).stem
    for variant in ["v6-D", "v6-B", "v4", "v3"]:
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

# ── Run Florence-2 (if cache exists) ──

def run_florence(image_path):
    cache_path = SCRIPT_DIR / "output" / "florence_fix_test" / "cache.json"
    if not cache_path.is_file():
        return None  # signal "no data"
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


# ── Images with .tc references ──

IMAGES = [
    "poster-simple.jpg",
    "poster-gradient.jpg",
    "poster-person.jpg",
    "poster-display-font.jpg",
    "poster-low-contrast.jpg",
    "banner-horizontal.jpg",
    "flyer-text-heavy.jpg",
    "portrait-overlay.jpg",
    "multi-photo-collage.jpg",
    "showcase-two-products.jpg",
]

results = []
for img_name in IMAGES:
    image_path = SCRIPT_DIR / "dataset" / img_name
    if not image_path.is_file():
        logger.warning("Skip: %s not found", image_path)
        continue
    
    image_id = image_path.stem
    logger.info("\n%s", "=" * 60)
    logger.info("Image: %s", image_id)
    logger.info("%s", "=" * 60)
    
    expected = load_tc_texts(image_path)
    if not expected:
        logger.warning("  No .tc reference — skipping")
        continue
    
    pos_gt, _ = build_position_gt(str(image_path))
    
    # Qwen
    qwen_dets = run_qwen(str(image_path))
    if qwen_dets:
        qwen_r = match_model_to_gt(qwen_dets, pos_gt, expected, "Qwen3-VL-32B")
    else:
        qwen_r = None
    
    # Florence (only poster-simple has cache)
    florence_dets = run_florence(str(image_path))
    if florence_dets is not None:
        f_r = match_model_to_gt(florence_dets, pos_gt, expected, "Florence-2 (fixed)")
    else:
        f_r = None
    
    results.append({
        "image": image_id,
        "qwen": qwen_r,
        "florence": f_r,
    })

# ── Summary ──
print("\n\n")
print("=" * 110)
print("BATCH SUMMARY — Qwen Text Detection Across Dataset")
print("=" * 110)
hdr = f"{'Image':30s} {'TRec':>5s} {'TPos':>4s} {'FPos':>4s} {'FNPos':>4s} {'Prec':>6s} {'Rec':>6s} {'F1':>6s} {'IoU':>6s}"
print(hdr)
print("-" * 75)
for r in results:
    for model_key, label in [("qwen", "Qwen")]:
        m = r.get(model_key)
        if m:
            print(f"{r['image']:30s} {m['text_recall']:>5.3f} "
                  f"{m['position_tp']:>4d} {m['position_fp']:>4d} {m['position_fn']:>4d} "
                  f"{m['position_precision']:>6.3f} {m['position_recall']:>6.3f} "
                  f"{m['position_f1']:>6.3f} {m['position_avg_iou']:>6.3f}")
print("-" * 75)

# Averages
qwen_avg = {"trec": [], "prec": [], "rec": [], "f1": [], "iou": []}
for r in results:
    m = r.get("qwen")
    if m:
        qwen_avg["trec"].append(m["text_recall"])
        qwen_avg["prec"].append(m["position_precision"])
        qwen_avg["rec"].append(m["position_recall"])
        qwen_avg["f1"].append(m["position_f1"])
        qwen_avg["iou"].append(m["position_avg_iou"])

if qwen_avg["trec"]:
    import statistics
    print(f"\n{'QWEN AVERAGE':30s} {statistics.mean(qwen_avg['trec']):>5.3f} "
          f"{'':>4s} {'':>4s} {'':>4s} "
          f"{statistics.mean(qwen_avg['prec']):>6.3f} {statistics.mean(qwen_avg['rec']):>6.3f} "
          f"{statistics.mean(qwen_avg['f1']):>6.3f} {statistics.mean(qwen_avg['iou']):>6.3f}")
