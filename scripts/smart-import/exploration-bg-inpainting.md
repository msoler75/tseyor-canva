# Exploration: Background Inpainting for Design Reconstruction

> **Date**: 2026-06-01
> **Scope**: Smart Import V5 — reconstruct original backgrounds from complex multi-element designs

---

## 1. Current State of Inpainting in the Codebase

### What exists today (V4)

The current `inpainter.py` implements **text removal inpainting** — it operates on individual **image crops** that have text overlaid on top. The pipeline:

1. Qwen3-VL detects all elements (text, images, shapes)
2. AABB overlap test finds which text bboxes overlap which image bboxes
3. Each image region is cropped from the source
4. A binary mask is created from overlapping text bboxes
5. The masked region is inpainted using one of three backends

**Key limitation**: This only handles **text-over-image** occlusion. It doesn't handle:
- Shapes (cards, badges, rectangles) overlapping images
- Multiple images overlapping each other
- Text or elements overlapping the **background** directly (not on an image)
- Reconstruction of the original background that existed BEFORE any elements were placed

### Current SceneGraph format

The SceneGraph (see `output/qwen-qwen3-vl-32b-instruct/v4/showcase-two-products/scene.json`) has:
- Flat `layers[]` array with `zIndex` values
- No depth/occlusion information beyond zIndex
- No "original background pixel data" stored
- Each layer has `bbox` but no knowledge of what's **underneath** it

```
SceneGraph layers (flat array):
  sh1 (zIndex=1)  → shape card
  sh2 (zIndex=2)  → shape card
  img1 (zIndex=15) → product photo (inpainted)
  img2 (zIndex=16) → product photo (inpainted)
  t1 (zIndex=27)  → text "DUO COLLECTION"
  ...
```

### zIndex assignment

In `pipeline_v3.py` `assemble_v3()` (line 293):
- Background: zIndex=0 (not a layer, stored as background color/kinda)
- Shapes: zIndex=1-9 (from Qwen shapes array)
- Images: zIndex=10-19
- Text elements: zIndex=20+

The zIndex follows a **kind-based heuristic**, not a true depth detection. Qwen3-VL doesn't explicitly detect which element is above/below another.

### Testing infrastructure

- `generate_fixtures.py` has 13 synthetic test images (7 original + 3 multi-photo + 3 inpainting-specific)
- `test_fixtures.py` verifies image dimensions, format, file size
- No tests exist for **background reconstruction quality** or **multi-layer inpainting**

---

## 2. Layer / Depth Detection Approaches

Given a composite design with overlapping elements, we need to determine **z-order** — which elements are on top of which others. The SceneGraph currently has zIndex but it's assigned heuristically, not detected from the actual image.

### Approach A: Qwen3-VL with explicit depth prompt

**How**: Modify the Qwen detection prompt to ask for:
- Element relationships: "element X is ON TOP OF element Y"
- Layer ordering numbers explicit in the response
- "Occlusion" flags: which elements hide parts of others

**Current prompt** doesn't ask for depth at all (pipeline_v3.py line 55-63):
```python
QWEN_DETECTION_PROMPT = """Analiza esta imagen de diseño gráfico y extrae en JSON:
- canvas: dimensiones totales
- background: tipo de fondo y color
- text_elements: array con cada texto → text, position {x,y,width,height}, color, font_style
- images: array con cada foto/ilustración → position, description
- shapes: array con cada forma/rectángulo → position, color, opacity
- caption: descripción general de la imagen"""
```

**Pros**:
- No extra model call needed
- Qwen3-VL already has strong visual reasoning
- Could detect complex occlusion (semi-transparent, partial overlap)

**Cons**:
- Qwen may be inaccurate for precise z-ordering
- Hard to validate accuracy
- The V4 analysis shows Qwen already has ~20% coordinate errors — adding depth could compound

**Effort**: Low (prompt engineering only)

### Approach B: Geometric occlusion analysis (OpenCV)

**How**: Use the detected bboxes and known zIndex heuristics to compute occlusion. If element A's bbox overlaps element B's bbox, and A has higher zIndex, then A is "on top" of B. The overlapping pixel region of B is "occluded" by A.

```python
def compute_occluded_regions(layers: list[dict]) -> dict:
    """Compute which pixel regions of each layer are hidden by higher-zIndex layers."""
    sorted_layers = sorted(layers, key=lambda l: l["zIndex"])
    occluded = {}
    for i, lower in enumerate(sorted_layers):
        hidden_pixels = []
        for j in range(i + 1, len(sorted_layers)):
            upper = sorted_layers[j]
            overlap = aabb_intersection(lower["bbox"], upper["bbox"])
            if overlap:
                hidden_pixels.append(overlap)
        occluded[lower["id"]] = hidden_pixels
    return occluded
```

**Pros**:
- Deterministic, zero cost, no model needed
- Exact pixel-precise overlap regions
- Works with existing SceneGraph data

**Cons**:
- Only works if we have accurate bboxes (Qwen errors propagate)
- Cannot detect occlusion by **semi-transparent** elements (alpha blending)
- Cannot detect when an element is visually "behind" but its bbox doesn't overlap
- Assumes zIndex heuristic is correct (which it may not be for some designs)

**Effort**: Low (pure algorithm, ~50 lines)

### Approach C: Visual comparison with inpainting ordering

**How**: Don't detect depth explicitly. Instead, inpaint from back-to-front using the assumed z-order:
1. Start with the full composite image
2. For each layer from lowest zIndex to highest:
   - Mask the region of this layer
   - Inpaint to reconstruct what's behind it
   - This "un-does" the layer

**Pros**:
- Direct approach to the problem (we don't need depth, we need the background)
- Works with current SceneGraph structure

**Cons**:
- If z-order is wrong, reconstructions will be wrong
- Each inpainting step accumulates errors

**Effort**: Medium (implementation)

### Approach D: Multi-modal depth estimation model

**How**: Use a dedicated **depth estimation** model (e.g., Depth Anything V2, ZoeDepth) to infer depth ordering from the 2D image. Elements closer to the camera (or more foreground) get higher depth values.

**Pros**:
- Model-based depth is more accurate than heuristics
- Can detect partial transparency and complex ordering

**Cons**:
- Additional model dependency (GPU recommended)
- Depth models estimate **scene depth**, not **graphic design layer order**
- A gradient overlay "above" a photo has the same depth as the photo — depth models don't understand compositing layers

**Effort**: High (new model integration, validation)

### Recommendation for V5

**Approach B (geometric occlusion)** as the primary mechanism — it's deterministic, free, and works with existing data. Use **Approach A (Qwen depth prompt)** as a secondary signal to adjust zIndex when the geometric analysis is ambiguous (overlapping same-kind elements, e.g., two overlapping images).

**Not recommended**: Approach D (depth model) — graphic design layers are not 3D depth maps.

---

## 3. Background Reconstruction Strategies

The fundamental problem: given a composite image with N elements layered on top of each other, reconstruct the original background that existed before any elements were placed.

### Strategy 1: Layer-by-layer inpainting (back to front)

**Algorithm**:
```
Given: composite image I, layers L[0..n] sorted by zIndex (background first)
Given: bbox for each layer

result = copy of I
for i = n-1 down to 0:  # from top to bottom
    layer = L[i]
    # Create mask covering this layer's pixels
    mask = layer_bbox_to_mask(layer.bbox)
    # But DON'T mask higher layers (they're on top)
    for j > i:  # layers above this one
        mask -= layer_bbox_to_mask(L[j].bbox)
    # Inpaint the non-occluded part of this layer
    result = inpaint(result, mask)
```

**What this does**: Starting from the top layer, it removes elements one by one, reconstructing what's behind each one. When it reaches the background, the result is what the design looked like before any elements were placed.

**Example with showcase-two-products**:
1. Remove text elements (zIndex 27-33) → reveal shapes/image areas underneath
2. Remove images (zIndex 15-16) → reveal shapes/background underneath
3. Remove shapes (zIndex 1-4) → reveal original background
4. Result: clean background with no elements

**Challenge**: Step 2 requires inpainting the image area, but the image is over shapes. The inpainter needs to know that "under the photo, there's a shape card" — not free-form background. This is a **content-aware inpainting** problem.

**Pros**:
- Intuitive, matches how designers think about layers
- Reuses existing inpainting backends
- Each step is a bounded inpainting problem

**Cons**:
- Error accumulation: each layer's mistakes propagate to the next
- Requires accurate z-order
- Semi-transparent layers break the assumption (a 50% overlay partially shows what's behind)

### Strategy 2: Single-shot generative reconstruction

**How**: Send the entire composite image to a powerful generative model (Gemini 3.1 Flash, DALL-E, Stable Diffusion) with a prompt like:

> "Reconstruct the original background of this design. Remove all text, images, shapes, and decorative elements. Return ONLY the clean background, exactly as it would appear with no design elements on it."

**Pros**:
- Simple: one API call
- Model handles occlusion, transparency, overlapping inherently
- Can reconstruct textures, gradients, patterns

**Cons**:
- Very expensive for high-resolution (cost per image)
- Model may hallucinate what's behind elements (invent content)
- No guarantee of pixel fidelity to original background
- Hard to validate correctness (we don't have ground truth background)
- Inconsistent results across calls (non-deterministic)

### Strategy 3: Hybrid — geometric occlusion + targeted inpainting

**How**: Combine both approaches:
1. Use geometric occlusion (Strategy 1) to compute what's underneath each layer
2. For each "hole" in the background, determine what **type** of content is behind:
   - If behind a shape with known fill color → fill with that color (deterministic)
   - If behind an image → use generative/ML inpainting to reconstruct the missing image pixels
   - If behind text → use existing text removal inpainting
   - If behind semi-transparent overlay → extract underlying pixels (if we know opacity)
3. Compositing: reconstruct the full background by layering deterministically-known regions first, then inpainting the unknown regions

**Example flow** for showcase-two-products:
```
Original: [bg_white] + [sh1_card] + [sh3_blue_bar] + [img1_photo] + [t1_text]

Step 1: Remove text t1 on top of img1
  → Use existing text-inpainter on img1 region
Step 2: Remove img1 on top of sh1_card
  → The photo covers part of sh1. We know sh1 fill=#f5f5f5.
  → Fill the img1 bbox area with #f5f5f5 (deterministic!)
Step 3: Remove sh1_card on top of bg_white
  → sh1 bbox area should be white. Fill with bg color. (deterministic!)
Step 4: Result = pure white background (bg=#ffffff)

Total: No generative inpainting needed at all!
```

**Key insight**: For many designs, the background under elements is just a solid color, a simple gradient, or other shapes that we already have in the SceneGraph. True generative inpainting is only needed when a **photo** is partially occluded by other elements — and even then, we only need to inpaint the **occluded portion** of the photo, not the entire image.

**Pros**:
- Minimizes generative inpainting (cost + quality)
- Deterministic fills for shapes/background → pixel-perfect
- Only uses generative models where truly needed
- Graceful degradation: if generative fails, fall back to color fill

**Cons**:
- More complex implementation
- Requires accurate knowledge of fill colors, opacities
- Gradient backgrounds are harder (need to reconstruct the gradient function)

### Recommendation for V5

**Strategy 3 (Hybrid)** is the clear winner. It recognizes that most backgrounds in typical designs are simple (solid colors, gradients, or solid shapes) and only uses expensive generative inpainting for the minority of cases where a real photo is partially occluded.

---

## 4. Dataset Design for Inpainting Tests

### Current dataset gaps

The current `generate_fixtures.py` has 13 images, of which 3 specifically test inpainting:
- `inpaint-forest-text.jpg` — large text over dense forest photo
- `inpaint-face-text.jpg` — text over face photo
- `inpaint-pattern-text.jpg` — text over geometric pattern

These test **text removal**, not **background reconstruction**. None of them have:
- Multiple overlapping elements
- Images overlapping other images
- Cards/shapes over photos
- Semi-transparent overlays over complex backgrounds
- Text directly on the background (not on an image)

### Proposed new fixtures for V5 background inpainting

#### Fixture 1: `bg-card-over-photo.jpg`
- **Size**: 1080×1350
- **Description**: A real photo background with a semi-transparent card (rectangle) on the right side, and text on the card. The card has a known fill color with opacity.
- **Test**: Can the pipeline recognize that underneath the card is photo content (needs inpainting), while underneath the text is a card (deterministic fill)?
- **Challenge level**: Medium

```python
def build_bg_card_over_photo(size=(1080, 1350)):
    w, h = size
    # Full photo background
    photo = _get_photo(w, h, seed="bg-card-photo")
    draw = ImageDraw.Draw(photo)
    
    # Card overlay (right side, semi-transparent)
    card = Image.new("RGBA", (w, h), (0,0,0,0))
    cdraw = ImageDraw.Draw(card)
    card_x, card_y = int(w*0.55), int(h*0.15)
    card_w, card_h = int(w*0.40), int(h*0.70)
    cdraw.rounded_rectangle(
        [card_x, card_y, card_x+card_w, card_y+card_h],
        radius=20, fill=(255, 255, 255, 200)  # semi-transparent white
    )
    photo = Image.alpha_composite(photo.convert("RGBA"), card).convert("RGB")
    draw = ImageDraw.Draw(photo)
    
    # Text on the card
    F_TITLE = _get_font(48, bold=True)
    F_BODY = _get_font(28)
    draw.text((card_x+30, card_y+40), "SPECIAL OFFER", fill=(0,0,0), font=F_TITLE)
    draw.text((card_x+30, card_y+120), "Limited time only", fill=(80,80,80), font=F_BODY)
    
    return photo
```

**Ground truth background**: The original photo before the card and text were added (can be saved separately as a "clean" version for comparison).

#### Fixture 2: `bg-photo-behind-shapes.jpg`
- **Size**: 1080×1350
- **Description**: A photo background with multiple opaque colored shapes (rectangles, circles) on top. Each shape has a known fill color. Text elements on some shapes.
- **Test**: Can the pipeline reconstruct the photo behind the shapes by inpainting only the shape-covered regions?
- **Challenge level**: Medium-High

```python
def build_bg_photo_behind_shapes(size=(1080, 1350)):
    w, h = size
    photo = _get_photo(w, h, seed="bg-shapes-photo")
    
    # Colored shapes overlaying the photo
    overlay = Image.new("RGBA", (w, h), (0,0,0,0))
    odraw = ImageDraw.Draw(overlay)
    # Red rectangle top-left
    odraw.rectangle([50, 50, 350, 250], fill=(220, 50, 50, 255))
    # Blue circle bottom-right
    odraw.ellipse([w-350, h-300, w-50, h-50], fill=(50, 80, 200, 255))
    # Teal rounded rect center
    odraw.rounded_rectangle([w//4, h//3, 3*w//4, 2*h//3], radius=30, fill=(20, 180, 160, 255))
    
    photo = Image.alpha_composite(photo.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(photo)
    
    # Text on shapes
    F_TITLE = _get_font(40, bold=True)
    draw.text((100, 100), "SALE", fill=(255,255,255), font=F_TITLE)
    draw.text((3*w//4-80, h-220), "NEW", fill=(255,255,255), font=_get_font(36, bold=True))
    draw.text((w//2-80, h//2-20), "LIMITED", fill=(255,255,255), font=_get_font(48, bold=True))
    
    return photo
```

**Ground truth background**: The photo without shapes, with precise bbox info for each shape and its fill color.

#### Fixture 3: `bg-gradient-card-overlap.jpg`
- **Size**: 1080×1350
- **Description**: A gradient background (purple-to-pink), with two cards that overlap each other. The top card has text. Tests whether the overlapping region of the lower card can be reconstructed.
- **Test**: Can the pipeline handle element-element occlusion (not just element-background)?
- **Challenge level**: High

```python
def build_bg_gradient_card_overlap(size=(1080, 1350)):
    w, h = size
    img = Image.new("RGB", size, (0,0,0))
    draw = ImageDraw.Draw(img)
    _draw_gradient(draw, 0, 0, w, h, (100, 50, 180), (220, 80, 150))
    
    # Card 1 (left, lower zIndex)
    overlay1 = Image.new("RGBA", (w, h), (0,0,0,0))
    o1draw = ImageDraw.Draw(overlay1)
    o1draw.rounded_rectangle([50, 200, 550, 900], radius=20, fill=(255, 255, 255, 230))
    
    # Card 2 (right, overlaps card 1, higher zIndex)
    overlay2 = Image.new("RGBA", (w, h), (0,0,0,0))
    o2draw = ImageDraw.Draw(overlay2)
    o2draw.rounded_rectangle([350, 400, 1000, 1000], radius=20, fill=(240, 240, 255, 240))
    
    img = Image.alpha_composite(img.convert("RGBA"), overlay1).convert("RGB")
    img = Image.alpha_composite(img.convert("RGBA"), overlay2).convert("RGB")
    draw = ImageDraw.Draw(img)
    
    # Text on both cards
    F_TITLE = _get_font(40, bold=True)
    F_BODY = _get_font(24)
    draw.text((100, 250), "WELCOME", fill=(30,30,30), font=F_TITLE)
    draw.text((100, 320), "To the event", fill=(80,80,80), font=F_BODY)
    draw.text((400, 450), "FEATURED", fill=(30,30,30), font=F_TITLE)
    draw.text((400, 520), "Guest speaker", fill=(80,80,80), font=F_BODY)
    
    return img
```

**Ground truth background**: The gradient + the lower card (without the top card). This tests whether we can reconstruct the gradient region that the top card covers on the lower card.

#### Fixture 4: `bg-text-on-background.jpg`
- **Size**: 1080×1350
- **Description**: Text directly on a textured background (no image layer). Tests: can we remove text that isn't "on an image" but rather on the design's background?
- **Test**: Background-level inpainting (the background is the canvas, not a detected image)
- **Challenge level**: Medium

```python
def build_bg_text_on_background(size=(1080, 1350)):
    w, h = size
    # Textured background (synthetic noise + gradient)
    img = Image.new("RGB", size, (240, 235, 230))
    draw = ImageDraw.Draw(img)
    # Subtle noise texture
    for _ in range(20000):
        px = random.randint(0, w-1)
        py = random.randint(0, h-1)
        r, g, b = img.getpixel((px, py))
        delta = random.randint(-10, 10)
        img.putpixel((px, py), (max(0,min(255,r+delta)), max(0,min(255,g+delta)), max(0,min(255,b+delta))))
    
    # Horizontal color bands (decorative)
    draw.rectangle([(0, 0), (w, 8)], fill=(200, 180, 160))
    draw.rectangle([(0, h-8), (w, h)], fill=(200, 180, 160))
    
    # Large text directly on background
    F_MAIN = _get_font(100, bold=True)
    F_SUB = _get_font(40)
    draw.text((w//2-350, h//2-80), "HELLO WORLD", fill=(60, 50, 40), font=F_MAIN)
    draw.text((w//2-200, h//2+50), "background inpainting test", fill=(120, 110, 100), font=F_SUB)
    
    return img
```

**Ground truth background**: The textured background without any text.

#### Fixture 5: `bg-complex-design.jpg`
- **Size**: 1080×1350
- **Description**: A complex design with: photo background → gradient overlay (semi-transparent) → card with opacity → text on card → decorative shape overlapping the card → badge on top. 5+ layers with different opacities.
- **Test**: End-to-end background reconstruction with multiple overlapping elements of different kinds.
- **Challenge level**: Very High

### How fixtures help testing

Each fixture should ship with:
1. **The composite image** (the "design" the pipeline sees)
2. **The clean background** (ground truth — the image before elements were placed)
3. **Per-element metadata** (position, zIndex, fill color, opacity, type)
4. **Occlusion map** (which pixels of each layer are hidden)

This allows:
- **Pixel-level comparison** between reconstructed background and ground truth
- **Per-layer accuracy** metrics (was the gradient behind the card correctly reconstructed?)
- **Ablation** (test with/without shape fill knowledge, with/without generative inpainting)

### Implementation in generate_fixtures.py

Each builder returns a tuple `(composite_image, clean_background, metadata_dict)` instead of just the composite. The registration in `GENERATORS` would change to include a flag for ground-truth-available.

---

## 5. Comparison of Inpainting Models

### Current backends

| Method | Cost | Quality | Speed | Deps | Best for |
|--------|:----:|:-------:|:-----:|:----:|:---------|
| OpenCV TELEA/NS | Free | Low | <1s | OpenCV | Small masks (<5K px), uniform backgrounds |
| LaMa (lama-cleaner) | Free | Medium | 2-5s (CPU) | PyTorch, lama-cleaner | Textured backgrounds, patterns |
| Gemini 3.1 Flash Image | ~$0.01/img | High | 70-130s | OpenRouter API key | Complex textures, faces, large masks |

### For background reconstruction (not text removal)

The requirements change significantly:

| Requirement | Text removal | Background reconstruction |
|------------|--------------|--------------------------|
| Mask size | Small (text-sized) | Large (element-sized) |
| Content type | Texture guess | Known fill color OR texture guess |
| Accuracy needed | Convincing fill | Pixel-accurate (for deterministic fills) |
| Context | Local pixels only | Global design knowledge |
| Semi-transparency | Not handled | Critical (overlays) |

### Additional models to consider

#### a. Stable Diffusion Inpainting (via Replicate or local)

- **Model**: `stabilityai/stable-diffusion-2-inpainting` or SDXL inpainting
- **Cost**: ~$0.002/image via Replicate, free if local (GPU)
- **Quality**: Good for filling large regions with realistic textures
- **Speed**: 5-15s via Replicate, 10-30s local GPU
- **Best for**: Reconstructing photo regions behind opaque elements
- **Limitation**: Can hallucinate, needs careful prompt engineering. May not match original photo style exactly.

#### b. OpenRouter Gemini 3.1 Flash Image (already have)

- Already integrated, used in V4
- Good quality but expensive and slow
- For background reconstruction, could send a targeted prompt per layer

#### c. OpenRouter Gemini 3.1 Pro (text + image)

- More expensive than Flash but potentially better reasoning
- Could be useful for "planning" the reconstruction (figuring out what's behind what)
- Not cost-effective for pixel-level inpainting

#### d. LaMa (lama-cleaner)

- Already in code (imported but not tested in analysis)
- Good for medium-sized masked regions
- CPU-only mode exists but is slow on large masks
- Decent texture continuation (better than OpenCV TELEA)

#### e. ClipDrop / StabilityAI API

- Purpose-built inpainting via API
- Cost: ~$0.01-0.05 per image
- Good quality but another API dependency

### Comparative analysis for V5 use cases

| Use case | OpenCV | LaMa | Gemini Flash | SD Inpaint |
|----------|:------:|:----:|:------------:|:----------:|
| Solid color fill (known) | N/A (direct fill) | N/A | N/A | N/A |
| Gradient fill (known endpoints) | N/A (reconstruct) | N/A | N/A | N/A |
| Small texture (<10K px) | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Medium texture (10K-50K px) | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Large texture (>50K px) | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Photo reconstruction behind element | ⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Pattern continuation | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Face reconstruction | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Text removal | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Semi-transparent overlay removal | ⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ |

### Recommendation for V5

**Hybrid approach** using a **tiered system**:

```
For each "hole" in the background:
  If we KNOW the fill (shape color, bg color):
    → Direct fill (0 cost, pixel-perfect)
  Else if mask < 5K px:
    → OpenCV TELEA (fast, free)
  Else if mask < 50K px OR pattern background:
    → LaMa (good pattern continuation)
  Else (large mask, photo background):
    → Gemini 3.1 Flash Image (best quality)
    → Fallback: SD Inpaint via Replicate (if Gemini unavailable)
```

---

## 6. Recommended Approach for V5 Inpainting

### Architecture

```
                     ┌──────────────────────────────┐
                     │  1. SceneGraph with zIndex    │
                     │  (from Qwen3-VL detection)    │
                     └──────────┬───────────────────┘
                                │
                                ▼
                     ┌──────────────────────────────┐
                     │  2. Occlusion Analyzer        │
                     │  Compute per-pixel what's     │
                     │  occluded by higher layers    │
                     │  (geometric AABB)             │
                     └──────────┬───────────────────┘
                                │
                                ▼
                     ┌──────────────────────────────┐
                     │  3. Layer Removal Planner     │
                     │  For each layer (back→front): │
                     │  - Known fill? → direct       │
                     │  - Gradient? → reconstruct    │
                     │  - Photo? → generative        │
                     │  - Text? → inpainter          │
                     └──────────┬───────────────────┘
                                │
                                ▼
                     ┌──────────────────────────────┐
                     │  4. Background Composer       │
                     │  Build clean background:      │
                     │  direct fills first, then     │
                     │  inpaint remaining holes      │
                     └──────────┬───────────────────┘
                                │
                                ▼
                     ┌──────────────────────────────┐
                     │  5. Validation                │
                     │  Compare vs ground truth      │
                     │  (PSNR, SSIM, masked regions) │
                     └──────────────────────────────┘
```

### Key design decisions

1. **Occlusion computation is geometric, not visual**: Use bbox intersections, not pixel analysis. This is deterministic and fast.

2. **Explicit background representation**: The background is NOT just a color string. It's represented as a **pixel buffer** that gets progressively refined as layers are removed.

3. **Shape fill colors are ground truth**: When a shape covers a region, the `fill` field tells us what color that region should be. No inpainting needed.

4. **Background gradient reconstruction**: If the background is a gradient (purple-to-pink), and a shape covers part of it, we can reconstruct the gradient function from the visible portions. A simple heuristic: bisect the gradient endpoints and interpolate.

5. **Photo-inpainting as last resort**: Only invoke generative models when a real photo is occluded by another element and we need to guess what's behind.

### New module: `bg_inpainter.py`

Would contain:
- `build_occlusion_map(layers, canvas_size)` → pixel map of what's hidden
- `reconstruct_background(composite, scene_graph)` → clean background image
- `_fill_known_region(background, bbox, fill_color)` → direct fill
- `_reconstruct_gradient(background, visible_gradient_bbox)` → gradient interpolation
- `_inpaint_photo_region(background, mask, method)` → generative inpainting

### Integration with existing pipeline

The V5 pipeline would add a new phase between Assembly and SceneGraph generation:

```
V4 Flow:  Detection → Assembly → Crop+Inpaint → SceneGraph → Compile → Render
V5 Flow:  Detection → Assembly → BG Reconstruction → Crop+Inpaint → SceneGraph → Compile → Render
                                              ↑
                                        New phase
```

The BG Reconstruction phase:
1. Takes the assembled layers (with zIndex, fill colors, bboxes)
2. Computes the occlusion map
3. Reconstructs the background using the tiered approach
4. Returns: `{ "background_pixels": np.ndarray, "occlusion_map": dict, "reconstruction_log": [...] }`
5. The reconstructed background can be stored as a `_bg_clean.png` alongside the design

---

## 7. Risks and Unknowns

### High risk

1. **Qwen's bounding box inaccuracy**: The V4 analysis shows ~20% coordinate errors in Qwen detections. If bboxes are wrong, the occlusion analysis (which depends on precise bbox intersections) will be wrong too. A shape that's 10px off could cause the wrong pixels to be filled with the wrong color.

2. **Gradient reconstruction is hard**: We can detect the **overall** background gradient from visible portions, but if a large central shape covers the gradient, we lose the middle. Interpolating the gradient may produce visible seams.

3. **Semi-transparent elements** (e.g., a 50% opacity overlay on a photo): The current approach doesn't model alpha blending. To reconstruct what's "under" a semi-transparent layer, you need to mathematically undo the alpha blend — which requires knowing the exact overlay color AND the exact alpha value. Errors in either produce wrong results.

### Medium risk

4. **Error accumulation**: Layer-by-layer reconstruction means errors compound. A incorrect fill on the 3rd layer back will affect all subsequent layers. Need to isolate errors per layer.

5. **Photo-inpainting quality on large areas**: If a large shape covers a significant portion of a photo (e.g., 60% of the photo area), generative inpainting must reconstruct details that never existed in the visible portion. This will be especially problematic for faces (eyes, mouth) and text (letters).

6. **Performance**: Gemini inpainting already takes 70-130s per image. Adding multiple generative calls (one per occluded photo region) could make this several minutes per design. Need a cost/time budget per design.

7. **No ground truth for real-world images**: The reconstruction quality can only be precisely measured on synthetic fixtures (where we have the clean original). For real-world images, we need proxy metrics.

### Low risk

8. **Shape detection quality**: Qwen detects shapes but with limited metadata (color, opacity). We may need richer shape information (border radius, gradient fill, border color) for better reconstruction.

9. **Performance on CPU**: LaMa and OpenCV are fine on CPU. Only generative models need GPU/API. The tiered approach minimizes generative calls.

10. **Integration complexity**: The new modules are cleanly separable. The `bg_inpainter.py` module has clear inputs (SceneGraph layers + composite image) and output (clean background image). Integration risk is low.

### Unknowns requiring experimentation

1. **What types of occlusion patterns occur in real designs?** Our synthetic fixtures may not capture all real-world patterns. Need to test on actual user designs.

2. **How accurate does the zIndex need to be?** ±1 zIndex for same-kind elements doesn't matter (two overlapping shapes at z=2 vs z=3 is fine). But if a shape is assigned zIndex lower than the background (z=0), the reconstruction breaks.

3. **Can we detect gradient endpoints automatically?** Using OpenCV edge detection on the visible background portions may or may not reliably find gradient boundaries.

4. **Is LaMa fast enough on CPU for the pattern-continuation use case?** The V4 analysis mentions LaMa but doesn't report actual benchmarks. Need to measure on the new fixtures.

---

## Ready for Proposal

**Yes** — this exploration identifies a clear technical approach (hybrid geometric + generative, tiered inpainting) with known risks and mitigations. The orchestrator should proceed to the **proposal phase** with a focus on:

1. Adding 5 new background-inpainting fixture images to the dataset
2. Implementing `bg_inpainter.py` with the layered occlusion model
3. Adding the BG Reconstruction phase to the V5 pipeline
4. Integrating existing inpainting backends into the tiered system
5. Building a validation harness that compares reconstruction against ground truth

**Cost estimate for proposal**: Low-Medium effort. The heavy work is the `bg_inpainter.py` module (~300-400 lines) and the occlusion analyzer (~100 lines). Fixture generation is ~200 lines. Integration with V5 pipeline is ~50 lines.
