#!/usr/bin/env python3
"""
PaddleOCR + Gemini Hybrid v2: Better prompting for element-level boxes.
"""
import json, sys, os
from pathlib import Path
from collections import defaultdict

BASE = Path(r"D:\projects\tseyor-canva\scripts\smart-import")
sys.path.insert(0, str(BASE))

from v9_paddleocr import paddleocr_detect
from openrouter import OpenRouterClient, _encode_image

def intersect_area(a, b):
    ix1 = max(a[0], b[0]); iy1 = max(a[1], b[1])
    ix2 = min(a[2], b[2]); iy2 = min(a[3], b[3])
    return max(0, ix2 - ix1) * max(0, iy2 - iy1)

SAMPLES = {
    "01-white": "png",
    "02-gradient": "jpg",
    "03-forest": "jpg",
}

SYSTEM_PROMPT = """You are a Canva design reconstruction expert.

Your job: given an image of a Canva design AND word-level OCR detections, produce the COMPLETE list of ALL text elements with their EXACT text and FULL element bounding boxes.

## Rules for text reading (CRITICAL)
- Read text EXACTLY as it appears in the image — do NOT normalize case, fix typos, or "correct" the text.
- If the image shows "MAKE IT POP", output "MAKE IT POP", not "Make it pop".
- If the image shows "STYLE", output "STYLE", not "Style".
- Text case, spacing, and punctuation must match the image EXACTLY.

## Rules for element boxes
The OCR data shows WORD-level detections. Your task is to merge these into FULL ELEMENT BOXES.

A Canva text element's bounding box spans the FULL WIDTH of its column, not just the text pixels.
Multiple word-level fragments on the same row often belong to ONE text element that spans the column.

Use the IMAGE to determine:
1. The column boundaries — look at the visual layout to see where columns start and end
2. Whether multiple OCR fragments belong to the SAME text element (same row, same visual group)
3. The correct x and width for each element — expand the tight OCR bbox to the FULL column
4. The vertical position (y) and height (h) — use the OCR box as a guide but expand to cover the element's full vertical space (typically h=35-50 for standard text lines)

## Rules for completeness (CRITICAL)
- Do NOT miss any text. If the OCR missed something, YOU find it in the image.
- The image may have text the OCR didn't detect. Look carefully.
- If a text element appears multiple times (same text, different positions), include each instance separately.

## Output format
Return a JSON array:
[
  {"text": "exact text", "x": int, "y": int, "w": int, "h": int},
  ...
]
"""

def run_sample(name, ext):
    print(f"\n{'='*70}")
    print(f" SAMPLE: {name}")
    print(f"{'='*70}")
    
    # Load GT
    tc_path = BASE / f"output/ocr-samples/samples/{name}.tc"
    tc = json.loads(tc_path.read_text(encoding="utf-8"))
    layout = tc.get("elementLayout", {})
    custom = tc.get("customElements", {})
    
    text_map = {}
    for eid, el in custom.items():
        if el.get("type") == "text":
            text_map[eid] = el.get("text", "")
    
    gt_elements = []
    for eid in sorted(layout.keys()):
        if not eid.startswith("t"): continue
        el = layout[eid]
        text = text_map.get(eid, "")
        if text:
            gt_elements.append({
                "text": text,
                "x": el.get("x", 0), "y": el.get("y", 0),
                "w": el.get("w", 0), "h": el.get("h", 0) or 40,
            })
    
    # Run PaddleOCR
    img_path = str((BASE / f"output/ocr-samples/{name}.{ext}").resolve())
    print(f"  >>> Running PaddleOCR...")
    paddle_els = paddleocr_detect(img_path)
    print(f"  >>> Found {len(paddle_els)} fragments")
    
    paddle_els.sort(key=lambda e: (e.get("position", {}).get("y", 0), e.get("position", {}).get("x", 0)))
    
    paddle_json = json.dumps([
        {"id": i, "text": pe.get("text",""), "conf": round(pe.get("confidence",0),2),
         "x": pe.get("position",{}).get("x",0), "y": pe.get("position",{}).get("y",0),
         "w": round(pe.get("position",{}).get("width",0)), "h": round(pe.get("position",{}).get("height",0))}
        for i, pe in enumerate(paddle_els)
    ], indent=2)
    
    user_prompt = f"""Image: {name}.{ext} (1080x1350px)

The following text regions were detected by OCR at the WORD/FRAGMENT level:

```json
{paddle_json}
```

TASKS:
1. For each OCR region, verify the text by looking at the image. Correct any reading errors.
2. Merge fragments that belong to the same visual text element.
3. DETECT any text elements the OCR missed and add them.
4. For each element, output the FULL Canva element bounding box — expand the tight OCR bbox to cover the element's column width.
5. Output ALL instances — if the same text appears in multiple places, include each.

Return ONLY a JSON array of elements."""

    # Call Gemini
    print(f"  >>> Calling Gemini...")
    client = OpenRouterClient()
    img_b64 = _encode_image(img_path)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": [
            {"type": "text", "text": user_prompt},
            {"type": "image_url", "image_url": {"url": img_b64}},
        ]},
    ]
    
    resp = client.chat_completion(
        messages=messages,
        model="google/gemini-2.5-flash",
        response_format={"type": "json_object"},
        max_tokens=8192,
    )
    
    print(f"  >>> Responded in {resp.latency_ms}ms ({resp.usage.get('totalTokens','?')} tokens)")
    
    # Parse
    try:
        gemini_els = json.loads(resp.content)
        if isinstance(gemini_els, dict):
            for key in ("elements", "texts", "text_elements", "items"):
                if key in gemini_els:
                    gemini_els = gemini_els[key]
                    break
        if not isinstance(gemini_els, list):
            gemini_els = [gemini_els]
    except json.JSONDecodeError:
        print(f"  !!! JSON parse error")
        gemini_els = []
    
    # Evaluate
    gt_texts = set()
    gt_instances = defaultdict(list)
    for gte in gt_elements:
        tl = gte["text"].strip().lower()
        gt_texts.add(tl)
        gt_instances[tl].append(gte)
    
    gemini_texts = set()
    gemini_instances = defaultdict(list)
    for ge in gemini_els:
        tl = ge.get("text", "").strip().lower()
        if tl:
            gemini_texts.add(tl)
            gemini_instances[tl].append(ge)
    
    found = gt_texts & gemini_texts
    missing = gt_texts - gemini_texts
    extra = gemini_texts - gt_texts
    
    text_recall = len(found) / len(gt_texts) if gt_texts else 1.0
    text_precision = len(found) / len(gemini_texts) if gemini_texts else 1.0
    f1 = 2 * text_recall * text_precision / max(text_recall + text_precision, 1e-9)
    
    # Position: match by text, assign to closest GT instance
    pos_scores = []
    pos_details = []
    for ge in gemini_els:
        tl = ge.get("text", "").strip().lower()
        if tl not in found or tl not in gt_instances:
            continue
        gx, gy = ge.get("x", 0), ge.get("y", 0)
        gw, gh = ge.get("w", 1) or 1, ge.get("h", 40) or 40
        gc_x = gx + gw / 2
        gc_y = gy + gh / 2
        
        best_dist = float("inf")
        best_gt = None
        for gte in gt_instances[tl]:
            gtcx = gte["x"] + gte["w"] / 2
            gtcy = gte["y"] + gte["h"] / 2
            d = ((gc_x - gtcx)**2 + (gc_y - gtcy)**2)**0.5
            if d < best_dist:
                best_dist = d
                best_gt = gte
        
        if best_gt:
            diag = (1080**2 + 1350**2)**0.5
            score = max(0, 1 - (best_dist / diag) * 1.5)
            pos_scores.append(score)
            dl = abs(gx - best_gt["x"])
            dr = abs((gx+gw) - (best_gt["x"]+best_gt["w"]))
            dt = abs(gy - best_gt["y"])
            db = abs((gy+gh) - (best_gt["y"]+best_gt["h"]))
            pos_details.append({
                "text": ge.get("text",""), "score": score,
                "dl": dl, "dr": dr, "dt": dt, "db": db
            })
    
    pos_avg = sum(pos_scores) / len(pos_scores) if pos_scores else 0
    composite = (text_recall + text_precision + pos_avg) / 3
    
    print(f"\n  --- RESULTS ---")
    print(f"  GT unique texts:      {len(gt_texts)}")
    print(f"  Gemini output texts:  {len(gemini_texts)}")
    print(f"  Match exacto:         {len(found)}")
    missing_str = ' '.join(f'"{t}"' for t in sorted(missing)) if missing else 'NONE'
    extra_str = ' '.join(f'"{t}"' for t in sorted(extra)) if extra else 'NONE'
    print(f"  Missing:              {len(missing)} {missing_str}")
    print(f"  Extra/hallucinated:   {len(extra)} {extra_str}")
    print(f"  Position avg:         {pos_avg:.3f}")
    print(f"  Text Recall:          {text_recall:.3f}")
    print(f"  Text Precision:       {text_precision:.3f}")
    print(f"  F1:                   {f1:.3f}")
    print(f"  COMPOSITE:            {composite:.3f}")
    
    # Best/worst position
    if pos_details:
        pos_details.sort(key=lambda x: x["score"])
        print(f"\n  --- Position details ---")
        print(f"  Best 3:")
        for pd in pos_details[-3:]:
            gembox = next((ge for ge in gemini_els if ge.get("text","").strip().lower() == pd["text"].strip().lower()), None)
            if gembox:
                print(f'    "{pd["text"][:25]:25s}" score={pd["score"]:.3f} L={pd["dl"]:3.0f} R={pd["dr"]:3.0f} T={pd["dt"]:3.0f} B={pd["db"]:3.0f}')
        print(f"  Worst 3:")
        for pd in pos_details[:3]:
            gembox = next((ge for ge in gemini_els if ge.get("text","").strip().lower() == pd["text"].strip().lower()), None)
            if gembox:
                print(f'    "{pd["text"][:25]:25s}" score={pd["score"]:.3f} L={pd["dl"]:3.0f} R={pd["dr"]:3.0f} T={pd["dt"]:3.0f} B={pd["db"]:3.0f}')
    
    return {
        "sample": name,
        "gt_count": len(gt_texts),
        "gemini_count": len(gemini_texts),
        "match": len(found),
        "missing": sorted(missing),
        "extra": sorted(extra),
        "recall": text_recall,
        "precision": text_precision,
        "f1": f1,
        "position": pos_avg,
        "composite": composite,
    }

# Run all 3
results = []
for s, ext in SAMPLES.items():
    r = run_sample(s, ext)
    results.append(r)

print(f"\n\n{'='*70}")
print(" FINAL SUMMARY — PaddleOCR + Gemini 2.5 Flash Hybrid")
print(f"{'='*70}")
print(f"{'Sample':<15} {'Recall':<8} {'Prec':<8} {'F1':<8} {'Pos':<8} {'COMPOSITE':<10} {'Match':<8}")
print("-" * 65)
for r in results:
    print(f"{r['sample']:<15} {r['recall']:.3f}    {r['precision']:.3f}    {r['f1']:.3f}    {r['position']:.3f}    {r['composite']:.3f}     {r['match']}/{r['gt_count']}")
    if r['missing']:
        mstr = ' '.join(f'"{t}"' for t in r['missing'])
        print(f"  Missing: {mstr}")
    if r['extra']:
        estr = ' '.join(f'"{t}"' for t in r['extra'])
        print(f"  Extra:   {estr}")

avg_composite = sum(r['composite'] for r in results) / len(results)
print(f"\n{'AVERAGE':<15}                                   {avg_composite:.3f}")
