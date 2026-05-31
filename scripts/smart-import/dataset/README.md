# Smart Import Pipeline — Benchmark Dataset

7 synthetic test images for calibrating the Smart Import pipeline.
Generated with Python/Pillow — no external assets required.

## Image Catalog

| # | File | Description | Format | Size | Complexity |
|---|------|-------------|--------|------|------------|
| 1 | `poster-simple.jpg` | Simple poster: solid dark blue background, big "SUMMER FEST" title, gray photo rectangle placeholder, subtitle line. Tests basic text + photo detection. | Portrait | 1080×1350 | Low |
| 2 | `poster-gradient.jpg` | Poster with vertical purple→pink gradient background, "NEW COLLECTION" title, "Spring 2026" subtitle, decorative ellipse rings, CTA button. Tests gradient background detection. | Portrait | 1080×1350 | Medium |
| 3 | `flyer-text-heavy.jpg` | Light-background flyer with 7 structured text blocks (date, venue, time, keynote, workshops, networking, registration), header, divider. Tests dense text layout with 2 font sizes. | Portrait | 1080×1350 | High |
| 4 | `poster-person.jpg` | Square post with teal background, decorative circles, person silhouette (circle head + trapezoid body), "JANE DOE" title, metadata line, gold verified badge. Tests person/silhouette detection. | Square | 1080×1080 | Medium |
| 5 | `banner-horizontal.jpg` | Horizontal banner with orange→amber gradient (left→right), "SALE / UP TO 50% OFF" text stack, SHOP NOW button, product photo placeholder on right. Tests horizontal/landscape detection. | Landscape | 1920×1080 | Medium |
| 6 | `poster-display-font.jpg` | Dark background with concentric decorative circles, gold star motifs (✦), decorative lines, large "DREAM" title, ornamental underline. Tests decorative typography and non-text elements. | Portrait | 1080×1350 | High |
| 7 | `poster-low-contrast.jpg` | Light gray background with subtle noise, text in near-matching gray — deliberately hard to read. "Whisper Collection" title, body paragraphs, metadata. Tests low-contrast text detection. | Portrait | 1080×1350 | High |

## Regeneration

To regenerate all images (e.g., after modifying the generator):

```bash
cd scripts/smart-import/dataset
python generate_fixtures.py
```

Options:
- `--output-dir DIR` — custom output directory
- `--quality N` — JPEG quality (default: 95, minimum 90 per spec)
- `--list` — preview which images would be generated

## Verification

Run the automated tests to verify images meet spec requirements:

```bash
cd scripts/smart-import/dataset
python test_fixtures.py
```

Tests check: file existence, dimensions, JPEG format, minimum resolution (600×800),
file size (>20 KB ensures non-trivial content), and orientation (portrait/landscape/square).
