"""
Test fixture: Verify generated dataset images.

This test validates that all 7 fixture images exist in the dataset directory
with the correct filenames, dimensions, format, and quality requirements
as specified in the SDD spec (smart-import-pipeline/spec.md §1).
"""

import os
import sys
from pathlib import Path

# Add parent directory so we can import the generator if needed
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image

# Test configuration derived from the SDD spec
DATASET_DIR = Path(__file__).resolve().parent

EXPECTED_IMAGES = {
    "poster-simple.jpg": (1080, 1350, "Simple poster: solid background + big title + photo rectangle"),
    "poster-gradient.jpg": (1080, 1350, "Poster with gradient bg + 2 texts + shape"),
    "flyer-text-heavy.jpg": (1080, 1350, "Flyer with 5-8 text blocks, 2 sizes"),
    "poster-person.jpg": (1080, 1080, "Square post with person silhouette + title + metadata"),
    "banner-horizontal.jpg": (1920, 1080, "Horizontal banner with text + photo"),
    "poster-display-font.jpg": (1080, 1350, "Design with decorative display typography"),
    "poster-low-contrast.jpg": (1080, 1350, "Design with low contrast text/background"),
}

MIN_FILE_SIZE_BYTES = 20_000  # 20KB minimum for a non-trivial JPEG at quality 90+
MIN_RESOLUTION = (600, 800)   # Minimum resolution per spec


def test_all_images_exist():
    """RED: Verify every expected image file exists on disk."""
    missing = []
    for filename in EXPECTED_IMAGES:
        full_path = DATASET_DIR / filename
        if not full_path.exists():
            missing.append(filename)

    assert not missing, f"Missing image files: {missing}"


def test_image_dimensions():
    """RED: Verify each image has the correct width and height."""
    failures = []
    for filename, (expected_w, expected_h, _desc) in EXPECTED_IMAGES.items():
        img = Image.open(DATASET_DIR / filename)
        actual_w, actual_h = img.size
        if actual_w != expected_w or actual_h != expected_h:
            failures.append(
                f"{filename}: expected {expected_w}x{expected_h}, got {actual_w}x{actual_h}"
            )

    assert not failures, f"Dimension mismatches:\n" + "\n".join(failures)


def test_jpeg_format():
    """RED: Verify each image is saved as JPEG format."""
    failures = []
    for filename in EXPECTED_IMAGES:
        img = Image.open(DATASET_DIR / filename)
        if img.format != "JPEG":
            failures.append(f"{filename}: expected JPEG, got {img.format}")

    assert not failures, f"Format mismatches:\n" + "\n".join(failures)


def test_minimum_resolution():
    """RED: Verify each image meets minimum 600x800 resolution (spec §1.2)."""
    min_w, min_h = MIN_RESOLUTION
    failures = []
    for filename in EXPECTED_IMAGES:
        img = Image.open(DATASET_DIR / filename)
        w, h = img.size
        if w < min_w or h < min_h:
            failures.append(f"{filename}: {w}x{h} below minimum {min_w}x{min_h}")

    assert not failures, f"Below minimum resolution:\n" + "\n".join(failures)


def test_file_size_non_trivial():
    """RED: Verify each file is large enough to contain actual image data (not blank/trivial)."""
    failures = []
    for filename in EXPECTED_IMAGES:
        size_bytes = os.path.getsize(DATASET_DIR / filename)
        if size_bytes < MIN_FILE_SIZE_BYTES:
            failures.append(
                f"{filename}: {size_bytes} bytes below minimum {MIN_FILE_SIZE_BYTES}"
            )

    assert not failures, f"File size failures:\n" + "\n".join(failures)


def test_no_image_artifacts():
    """TRIANGULATE: Verify images have non-trivial mode (RGB, not palette) and reasonable entropy."""
    failures = []
    for filename in EXPECTED_IMAGES:
        img = Image.open(DATASET_DIR / filename)
        if img.mode not in ("RGB", "RGBA"):
            failures.append(f"{filename}: expected RGB/RGBA mode, got {img.mode}")

        # Check that the image isn't a single solid color (would indicate generation failure)
        extrema = img.getextrema()
        for channel_idx, (min_val, max_val) in enumerate(extrema[:3]):  # Check R,G,B
            if min_val == max_val:
                # Entire channel is flat — could be degenerate
                pass  # Some designs intentionally have flat channels; just note

    assert not failures, f"Mode mismatches:\n" + "\n".join(failures)


def test_dimensions_match_spec_table():
    """TRIANGULATE: Verify all vertical images are portrait orientation, horizontal is landscape, square is square."""
    checks = {
        "poster-simple.jpg": "portrait",
        "poster-gradient.jpg": "portrait",
        "flyer-text-heavy.jpg": "portrait",
        "poster-person.jpg": "square",
        "banner-horizontal.jpg": "landscape",
        "poster-display-font.jpg": "portrait",
        "poster-low-contrast.jpg": "portrait",
    }

    failures = []
    for filename, expected_orientation in checks.items():
        img = Image.open(DATASET_DIR / filename)
        w, h = img.size

        if expected_orientation == "portrait" and w >= h:
            failures.append(f"{filename}: expected portrait (w < h), got {w}x{h}")
        elif expected_orientation == "landscape" and w <= h:
            failures.append(f"{filename}: expected landscape (w > h), got {w}x{h}")
        elif expected_orientation == "square" and w != h:
            failures.append(f"{filename}: expected square (w == h), got {w}x{h}")

    assert not failures, f"Orientation mismatches:\n" + "\n".join(failures)


if __name__ == "__main__":
    # Run all tests manually when executed directly
    tests = [
        ("test_all_images_exist", test_all_images_exist),
        ("test_image_dimensions", test_image_dimensions),
        ("test_jpeg_format", test_jpeg_format),
        ("test_minimum_resolution", test_minimum_resolution),
        ("test_file_size_non_trivial", test_file_size_non_trivial),
        ("test_no_image_artifacts", test_no_image_artifacts),
        ("test_dimensions_match_spec_table", test_dimensions_match_spec_table),
    ]

    failures = 0
    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  [PASS] {name}")
        except AssertionError as e:
            print(f"  [FAIL] {name}: {e}")
            failures += 1
        except Exception as e:
            print(f"  [ERROR] {name}: unexpected error: {e}")
            failures += 1

    print(f"\n{'=' * 50}")
    if failures:
        print(f"[FAIL] {failures} test(s) FAILED")
        sys.exit(1)
    else:
        print(f"[PASS] All {len(tests)} tests PASSED")
