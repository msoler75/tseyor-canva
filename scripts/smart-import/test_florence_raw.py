"""Debug Florence-2 output - show raw responses."""
import os, sys, time, json

sys.path.insert(0, os.path.dirname(__file__))
# Token from env (set in .env or system environment)
assert os.environ.get("REPLICATE_API_TOKEN"), "Set REPLICATE_API_TOKEN in .env"

import replicate

img_path = "scripts/smart-import/dataset/poster-simple.jpg"

def encode_image(path):
    import base64
    ext = os.path.splitext(path)[1].lower()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime.get(ext.lstrip('.'), 'image/png')};base64,{b64}"

image_data = encode_image(img_path)

# Task: OCR
print("=== OCR ===")
output = replicate.run(
    "lucataco/florence-2-large:da53547e17d45b9cfb48174b2f18af8b83ca020fa76db62136bf9c6616762595",
    input={"image": image_data, "task_input": "OCR"},
)
print(f"  Type: {type(output).__name__}")
print(f"  Raw: {str(output)[:500]}")
print()

time.sleep(12)

# Task: OCR with Region
print("=== OCR WITH REGION ===")
output = replicate.run(
    "lucataco/florence-2-large:da53547e17d45b9cfb48174b2f18af8b83ca020fa76db62136bf9c6616762595",
    input={"image": image_data, "task_input": "OCR with Region"},
)
print(f"  Type: {type(output).__name__}")
print(f"  Raw: {str(output)[:500]}")
print()

time.sleep(12)

# Task: Dense Region Caption
print("=== DENSE REGION CAPTION ===")
output = replicate.run(
    "lucataco/florence-2-large:da53547e17d45b9cfb48174b2f18af8b83ca020fa76db62136bf9c6616762595",
    input={"image": image_data, "task_input": "Dense Region Caption"},
)
print(f"  Type: {type(output).__name__}")
print(f"  Raw: {str(output)[:500]}")
