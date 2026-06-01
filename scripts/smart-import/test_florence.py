"""Quick test of Florence-2 via Replicate."""
import os, json, sys
sys.path.insert(0, os.path.dirname(__file__))
# Token from env (set in .env or system environment)
assert os.environ.get("REPLICATE_API_TOKEN"), "Set REPLICATE_API_TOKEN in .env"

from florence_client import florence_ocr, florence_dense_regions, florence_caption

img = "scripts/smart-import/dataset/poster-simple.jpg"

print("=== CAPTION ===")
cap = florence_caption(img)
print(cap)

print("\n=== OCR_WITH_REGION ===")
ocr = florence_ocr(img, 1080, 1350)
for item in ocr[:8]:
    print(f'  {item["text"][:50]:50s}  x={item["bbox"]["x"]:.3f}  y={item["bbox"]["y"]:.3f}  w={item["bbox"]["w"]:.3f}  h={item["bbox"]["h"]:.3f}')
print(f"  ({len(ocr)} items)")

print("\n=== DENSE_REGION_CAPTION ===")
dense = florence_dense_regions(img, 1080, 1350)
for item in dense[:6]:
    print(f'  {item["description"][:50]:50s}  x={item["bbox"]["x"]:.3f}  y={item["bbox"]["y"]:.3f}  w={item["bbox"]["w"]:.3f}  h={item["bbox"]["h"]:.3f}')
print(f"  ({len(dense)} items)")
