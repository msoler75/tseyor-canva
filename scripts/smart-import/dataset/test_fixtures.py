"""
Test fixture: Verify generated dataset images.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image

DATASET_DIR = Path(__file__).resolve().parent

EXPECTED_IMAGES = {
    "poster-simple.jpg": (1080, 1350, "Simple poster"),
    "poster-gradient.jpg": (1080, 1350, "Poster with gradient bg"),
    "flyer-text-heavy.jpg": (1080, 1350, "Flyer with 5-8 text blocks"),
    "poster-person.jpg": (1080, 1080, "Square post with person silhouette"),
    "banner-horizontal.jpg": (1920, 1080, "Horizontal banner"),
    "poster-display-font.jpg": (1080, 1350, "Display typography"),
    "poster-low-contrast.jpg": (1080, 1350, "Low contrast text/background"),
    "multi-photo-collage.jpg": (1080, 1350, "3 photos overlapping + transparencies"),
    "portrait-overlay.jpg": (1080, 1350, "Face + gradient overlay + transparency"),
    "showcase-two-products.jpg": (1080, 1350, "2 products + reflections + badges"),
}

MIN_FILE_SIZE_BYTES = 20_000
MIN_RESOLUTION = (600, 800)


def test_all_images_exist():
    missing = [f for f in EXPECTED_IMAGES if not (DATASET_DIR / f).exists()]
    assert not missing, f"Missing image files: {missing}"


def test_image_dimensions():
    failures = []
    for filename, (expected_w, expected_h, _desc) in EXPECTED_IMAGES.items():
        img = Image.open(DATASET_DIR / filename)
        w, h = img.size
        if w != expected_w or h != expected_h:
            failures.append(f"{filename}: expected {expected_w}x{expected_h}, got {w}x{h}")
    assert not failures, "\n".join(failures)


def test_jpeg_format():
    failures = []
    for filename in EXPECTED_IMAGES:
        img = Image.open(DATASET_DIR / filename)
        if img.format != "JPEG":
            failures.append(f"{filename}: expected JPEG, got {img.format}")
    assert not failures, "\n".join(failures)


def test_minimum_resolution():
    min_w, min_h = MIN_RESOLUTION
    failures = []
    for filename in EXPECTED_IMAGES:
        w, h = Image.open(DATASET_DIR / filename).size
        if w < min_w or h < min_h:
            failures.append(f"{filename}: {w}x{h} below minimum {min_w}x{min_h}")
    assert not failures, "\n".join(failures)


def test_file_size_non_trivial():
    failures = []
    for filename in EXPECTED_IMAGES:
        size_bytes = os.path.getsize(DATASET_DIR / filename)
        if size_bytes < MIN_FILE_SIZE_BYTES:
            failures.append(f"{filename}: {size_bytes}B below {MIN_FILE_SIZE_BYTES}B")
    assert not failures, "\n".join(failures)


def test_no_image_artifacts():
    failures = []
    for filename in EXPECTED_IMAGES:
        img = Image.open(DATASET_DIR / filename)
        if img.mode not in ("RGB", "RGBA"):
            failures.append(f"{filename}: expected RGB/RGBA, got {img.mode}")
    assert not failures, "\n".join(failures)


def test_orientation():
    checks = {
        "poster-simple.jpg": "portrait",
        "poster-gradient.jpg": "portrait",
        "flyer-text-heavy.jpg": "portrait",
        "poster-person.jpg": "square",
        "banner-horizontal.jpg": "landscape",
        "poster-display-font.jpg": "portrait",
        "poster-low-contrast.jpg": "portrait",
        "multi-photo-collage.jpg": "portrait",
        "portrait-overlay.jpg": "portrait",
        "showcase-two-products.jpg": "portrait",
    }
    failures = []
    for filename, expected in checks.items():
        w, h = Image.open(DATASET_DIR / filename).size
        if expected == "portrait" and w >= h:
            failures.append(f"{filename}: expected portrait, got {w}x{h}")
        elif expected == "landscape" and w <= h:
            failures.append(f"{filename}: expected landscape, got {w}x{h}")
        elif expected == "square" and w != h:
            failures.append(f"{filename}: expected square, got {w}x{h}")
    assert not failures, "\n".join(failures)


if __name__ == "__main__":
    tests = [
        test_all_images_exist,
        test_image_dimensions,
        test_jpeg_format,
        test_minimum_resolution,
        test_file_size_non_trivial,
        test_no_image_artifacts,
        test_orientation,
    ]
    failures = 0
    for fn in tests:
        try:
            fn()
            print(f"  [PASS] {fn.__name__}")
        except AssertionError as e:
            print(f"  [FAIL] {fn.__name__}: {e}")
            failures += 1
        except Exception as e:
            print(f"  [ERROR] {fn.__name__}: {e}")
            failures += 1
    print(f"\n{'=' * 40}")
    if failures:
        print(f"[FAIL] {failures} test(s) FAILED")
        sys.exit(1)
    else:
        print(f"[PASS] All {len(tests)} tests PASSED")
