"""Run Florence-2 OCR test with 15s delay between calls (rate limit: burst=1, 6/min)."""
import os, sys, time

sys.path.insert(0, os.path.dirname(__file__))
# Token from env (set in .env or system environment)
assert os.environ.get("REPLICATE_API_TOKEN"), "Set REPLICATE_API_TOKEN in .env"

from florence_client import florence_ocr, florence_dense_regions, florence_caption

img = "scripts/smart-import/dataset/poster-simple.jpg"

print("=== CAPTION ===")
cap = florence_caption(img)
print(f"  {cap}")
print("  (waiting 15s...)")
time.sleep(15)

print("\n=== OCR_WITH_REGION ===")
ocr = florence_ocr(img, 1080, 1350)
for item in ocr[:10]:
    text = item["text"][:50]
    bbox = item["bbox"]
    print(f"  {text:50s}  x={bbox['x']:.3f}  y={bbox['y']:.3f}  w={bbox['w']:.3f}  h={bbox['h']:.3f}")
print(f"  ({len(ocr)} items total)")
print("  (waiting 15s...)")
time.sleep(15)

print("\n=== DENSE_REGION_CAPTION ===")
dense = florence_dense_regions(img, 1080, 1350)
for item in dense[:6]:
    desc = item["description"][:50]
    bbox = item["bbox"]
    print(f"  {desc:50s}  x={bbox['x']:.3f}  y={bbox['y']:.3f}  w={bbox['w']:.3f}  h={bbox['h']:.3f}")
print(f"  ({len(dense)} items total)")

print("\n=== DONE ===")
