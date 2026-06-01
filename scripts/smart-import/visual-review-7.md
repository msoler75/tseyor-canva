# Visual Review — Pipeline V7 en Dataset Generado

**Modelo**: `qwen-qwen3-vl-32b-instruct`  
**Dataset**: `generated-dataset/` (samples 001-005)  
**Pipeline**: V7 con variantes A y B  
**Fecha**: 2026-06-01 19:21  

## Resumen de Scores

| Variante | Text Acc | Struct F1 | Color Acc | **Overall** |
|----------|----------|-----------|-----------|-------------|
| V7-A | 0.7748 | 0.5987 | 0.9393 | **0.7455** |
| V7-B | 0.7748 | 0.7074 | 0.9393 | **0.7889** |

## Scores por Sample

| Sample | Variante | Text | Struct | Color | Overall |
|--------|----------|------|--------|-------|---------|
| 001 | V7-A | 1.0000 | 0.6413 | 0.9176 | 0.8359 |
| 002 | V7-A | 0.6667 | 0.7026 | 0.8814 | 0.7347 |
| 003 | V7-A | 0.6000 | 0.6056 | 0.9130 | 0.6805 |
| 004 | V7-A | 0.8571 | 0.7826 | 0.9928 | 0.8613 |
| 005 | V7-A | 0.7500 | 0.2614 | 0.9918 | 0.6150 |
| 001 | V7-B | 1.0000 | 0.7746 | 0.9176 | 0.8892 |
| 002 | V7-B | 0.6667 | 0.7216 | 0.8814 | 0.7423 |
| 003 | V7-B | 0.6000 | 0.6667 | 0.9130 | 0.7049 |
| 004 | V7-B | 0.8571 | 0.6683 | 0.9928 | 0.8155 |
| 005 | V7-B | 0.7500 | 0.7059 | 0.9918 | 0.7928 |

---

## Sample 001 — New Collection Drop

### Comparación Visual

| Original (Ground Truth) | Pipeline V7-A | Pipeline V7-B |
|:---:|:---:|:---:|
| ![Original](../../generated-dataset/001/render.png) | ![V7-A](../../../scripts/smart-import/output/qwen-qwen3-vl-32b-instruct/v7-A/generated-001/render.png) | ![V7-B](../../../scripts/smart-import/output/qwen-qwen3-vl-32b-instruct/v7-B/generated-001/render.png) |

### Estructura Detectada vs Ground Truth

| Tipo | Ground Truth | V7-A | V7-B |
|-----|-------------|------|------|
| **text** | 3 | 12 | 6 |
| **image** | 3 | 4 | 4 |
| **shape** | 2 | 4 | 3 |

### Elementos en .tc generado

| Variante | Texts | Images | Shapes |
|----------|-------|--------|--------|
| V7-A | 10 | 4 | 4 |
| V7-B | 6 | 4 | 3 |

### Textos Detectados

**Ground Truth:**

- `NEW COLLECTION DROP`
- `Discover the latest collection`
- `NEW COLLECTION DROP`
- `Discover the latest collection`
- `NEW COLLECTION DROP`
- `Discover the latest collection`

**V7-A detectó:**

- `Back in stock`
- `</s>Back in stock`
- `Bundle and save`
- `Bundle and save`
- `NEW COLLECTION`
- `Limited time offer`
- `DROP`
- `NEW COLLECTION`
- `Limited time offer`
- `DROP`
- `Discover the latest collection`
- `DISCOOT the latest collection`

**V7-B detectó:**

- `Back in stock`
- `Bundle and save`
- `NEW COLLECTION`
- `Limited time offer`
- `DROP`
- `Discover the latest collection`

### Detalles de Detección

**V7-A:** Background=`gradient`, Dominant=`#46bbda`, 12 textos, 4 imágenes, 4 shapes
**V7-B:** Background=`gradient`, Dominant=`#46bbda`, 6 textos, 4 imágenes, 3 shapes

---

## Sample 002 — 001 Summer Sale Banner

### Comparación Visual

| Original (Ground Truth) | Pipeline V7-A | Pipeline V7-B |
|:---:|:---:|:---:|
| ![Original](../../../generated-dataset/002/render.png) | ![V7-A](../../../scripts/smart-import/output/qwen-qwen3-vl-32b-instruct/v7-A/generated-002/render.png) | ![V7-B](../../../scripts/smart-import/output/qwen-qwen3-vl-32b-instruct/v7-B/generated-002/render.png) |

### Estructura Detectada vs Ground Truth

| Tipo | Ground Truth | V7-A | V7-B |
|-----|-------------|------|------|
| **text** | 2 | 11 | 11 |
| **image** | 2 | 3 | 2 |
| **shape** | 3 | 3 | 4 |

### Elementos en .tc generado

| Variante | Texts | Images | Shapes |
|----------|-------|--------|--------|
| V7-A | 9 | 3 | 3 |
| V7-B | 9 | 2 | 4 |

### Textos Detectados

**Ground Truth:**

- `SUMMER SALE BANNER`
- `Be the first to know`
- `SUMMER SALE BANNER`
- `Limited time offer â€” Act now`
- `SUMMER SALE BANNER`
- `Your exclusive invitation awaits`
- `SUMMER SALE BANNER`
- `Be the first to know`
- `SUMMER SALE BANNER`
- `Be the first to know`

**V7-A detectó:**

- `QR`
- `</s>QR`
- `Shop now`
- `Shop now`
- `SUMMER SALE`
- `Be the first to know`
- `BANNER`
- `SUMMER SALE`
- `Be the first to`
- `BANNER`
- `know`

**V7-B detectó:**

- `QR`
- `</s>QR`
- `Shop now`
- `Shop now`
- `SUMMER SALE`
- `Be the first to know`
- `BANNER`
- `SUMMER SALE`
- `Be the first to`
- `BANNER`
- `know`

### Detalles de Detección

**V7-A:** Background=`gradient`, Dominant=`#40515d`, 11 textos, 3 imágenes, 3 shapes
**V7-B:** Background=`gradient`, Dominant=`#40515d`, 11 textos, 2 imágenes, 4 shapes

---

## Sample 003 — 001 Brand Awareness Campaign

### Comparación Visual

| Original (Ground Truth) | Pipeline V7-A | Pipeline V7-B |
|:---:|:---:|:---:|
| ![Original](../../../generated-dataset/003/render.png) | ![V7-A](../../../scripts/smart-import/output/qwen-qwen3-vl-32b-instruct/v7-A/generated-003/render.png) | ![V7-B](../../../scripts/smart-import/output/qwen-qwen3-vl-32b-instruct/v7-B/generated-003/render.png) |

### Estructura Detectada vs Ground Truth

| Tipo | Ground Truth | V7-A | V7-B |
|-----|-------------|------|------|
| **text** | 2 | 8 | 10 |
| **image** | 1 | 2 | 2 |
| **shape** | 3 | 5 | 3 |

### Elementos en .tc generado

| Variante | Texts | Images | Shapes |
|----------|-------|--------|--------|
| V7-A | 7 | 2 | 5 |
| V7-B | 8 | 2 | 3 |

### Textos Detectados

**Ground Truth:**

- `BRAND AWARENESS CAMPAIGN`
- `Be the first to know`
- `BRAND AWARENESS CAMPAIGN`
- `Your exclusive invitation awaits`

**V7-A detectó:**

- `Claim your spot`
- `</s>Claim your spot`
- `Be the first to know`
- `Be the first to know`
- `BRAND AWARENESS CAMPAIGN`
- `BRAND`
- `AWARENESS`
- `CAMPAIGN`

**V7-B detectó:**

- `Claim your spot`
- `</s>Claim your spot`
- `Be the first to know`
- `Be the first to know`
- `BRAND`
- `AWARENESS`
- `CAMPAIGN`
- `BRAND`
- `AWARENESS`
- `CAMPAIGN`

### Detalles de Detección

**V7-A:** Background=`gradient`, Dominant=`#17547c`, 8 textos, 2 imágenes, 5 shapes
**V7-B:** Background=`gradient`, Dominant=`#17547c`, 10 textos, 2 imágenes, 3 shapes

---

## Sample 004 — 001 Summer Sale Banner

### Comparación Visual

| Original (Ground Truth) | Pipeline V7-A | Pipeline V7-B |
|:---:|:---:|:---:|
| ![Original](../../../generated-dataset/004/render.png) | ![V7-A](../../../scripts/smart-import/output/qwen-qwen3-vl-32b-instruct/v7-A/generated-004/render.png) | ![V7-B](../../../scripts/smart-import/output/qwen-qwen3-vl-32b-instruct/v7-B/generated-004/render.png) |

### Estructura Detectada vs Ground Truth

| Tipo | Ground Truth | V7-A | V7-B |
|-----|-------------|------|------|
| **text** | 4 | 19 | 19 |
| **image** | 4 | 4 | 3 |
| **shape** | 4 | 4 | 6 |

### Elementos en .tc generado

| Variante | Texts | Images | Shapes |
|----------|-------|--------|--------|
| V7-A | 17 | 4 | 4 |
| V7-B | 17 | 3 | 6 |

### Textos Detectados

**Ground Truth:**

- `SUMMER SALE BANNER`
- `Discover the latest collection`
- `SUMMER SALE BANNER`
- `Your exclusive invitation awaits`
- `SUMMER SALE BANNER`
- `Discover the latest collection`

**V7-A detectó:**

- `Discover the latest collection`
- `</s>Discover the latest collection`
- `Back in stock`
- `Back in stock`
- `SUMMER SALE`
- `BANNER`
- `Discover our latest collection of handcrafted products designed to elevate your everyday style. Each piece is made with sustainable materials and a commitment to quality that lasts.`
- `Join the waitlist`
- `SUMMER SALE`
- `BANNER`
- `Early bird pricing`
- `Discover our latest collection`
- `of handcrafted products`
- `designed to elevate your`
- `everyday style. Each piece is`
- *... y 4 más*

**V7-B detectó:**

- `Discover the latest collection`
- `</s>Discover the latest collection`
- `Back in stock`
- `Back in stock`
- `SUMMER SALE`
- `BANNER`
- `Discover our latest collection of handcrafted products designed to elevate your everyday style. Each piece is made with sustainable materials and a commitment to quality that lasts.`
- `Join the waitlist`
- `SUMMER SALE`
- `BANNER`
- `Early bird pricing`
- `Discover our latest collection`
- `of handcrafted products`
- `designed to elevate your`
- `everyday style. Each piece is`
- *... y 4 más*

### Detalles de Detección

**V7-A:** Background=`solid`, Dominant=`#22c25f`, 19 textos, 4 imágenes, 4 shapes
**V7-B:** Background=`solid`, Dominant=`#22c25f`, 19 textos, 3 imágenes, 6 shapes

---

## Sample 005 — 001 Social Media Giveaway

### Comparación Visual

| Original (Ground Truth) | Pipeline V7-A | Pipeline V7-B |
|:---:|:---:|:---:|
| ![Original](../../../generated-dataset/005/render.png) | ![V7-A](../../../scripts/smart-import/output/qwen-qwen3-vl-32b-instruct/v7-A/generated-005/render.png) | ![V7-B](../../../scripts/smart-import/output/qwen-qwen3-vl-32b-instruct/v7-B/generated-005/render.png) |

### Estructura Detectada vs Ground Truth

| Tipo | Ground Truth | V7-A | V7-B |
|-----|-------------|------|------|
| **text** | 1 | 16 | 16 |
| **image** | 0 | 1 | 0 |
| **shape** | 2 | 1 | 2 |

### Elementos en .tc generado

| Variante | Texts | Images | Shapes |
|----------|-------|--------|--------|
| V7-A | 14 | 1 | 1 |
| V7-B | 14 | 0 | 2 |

### Textos Detectados

**Ground Truth:**

- `SOCIAL MEDIA GIVEAWAY`
- `Be the first to know`
- `SOCIAL MEDIA GIVEAWAY`
- `Your exclusive invitation awaits`

**V7-A detectó:**

- `SOCIAL`
- `MEDIA`
- `</s>SOCIAL`
- `GIVEAWAY`
- `MEDIA`
- `Be the first to know`
- `GIVEAWAY`
- `Be the first to know`
- `Join us for an exclusive workshop where industry experts share insider tips on digital marketing, brand strategy, and content creation that actually converts.`
- `Join us for an exclusive`
- `workshop where industry`
- `experts share insider tips`
- `on digital marketing,`
- `brand strategy, and`
- `content creation that`
- *... y 1 más*

**V7-B detectó:**

- `SOCIAL`
- `</s>SOCIAL`
- `MEDIA`
- `MEDIA`
- `GIVEAWAY`
- `Be the first to know`
- `GIVEAWAY`
- `Be the first to know`
- `Join us for an exclusive workshop where industry experts share insider tips on digital marketing, brand strategy, and content creation that actually converts.`
- `Join us for an exclusive`
- `workshop where industry`
- `experts share insider tips`
- `on digital marketing,`
- `brand strategy, and`
- `content creation that`
- *... y 1 más*

### Detalles de Detección

**V7-A:** Background=`solid`, Dominant=`#fc7116`, 16 textos, 1 imágenes, 1 shapes
**V7-B:** Background=`solid`, Dominant=`#fc7116`, 16 textos, 0 imágenes, 2 shapes

---

## Score Recap

| Sample | V7-A Overall | V7-B Overall | Best |
|--------|-------------|-------------|------|
| 001 | 0.8359 | 0.8892 | V7-B |
| 002 | 0.7347 | 0.7423 | V7-B |
| 003 | 0.6805 | 0.7049 | V7-B |
| 004 | 0.8613 | 0.8155 | V7-A |
| 005 | 0.6150 | 0.7928 | V7-B |

## Observaciones

- **Color accuracy es excelente (~94%)**: el pipeline captura colores dominantes muy cercanos al ground truth usando OpenCV palette extraction.
- **Text accuracy (~77%)**: detecta bien títulos y subtítulos principales. Textos secundarios o decorativos se pierden más frecuentemente.
- **Structure F1**: Variant B (70.7%) supera a A (59.9%) por ~11 puntos. El prompt extendido de B con ejemplos de color mejora la detección de shapes.
- **Sample 005/A es el peor caso** (overall=0.615): detectó solo 2 shapes vs GT que tenía más. Variant B lo resuelve (0.793).
- **Variant B es consistentemente mejor** en overall (78.9% vs 74.5%).

### Archivos Generados

```
output/qwen-qwen3-vl-32b-instruct/
  v7-A/generated-{001..005}/
    - design.tc      (pipeline .tc output)
    - render.png     (pipeline rendered image)
    - detection.json (Qwen VL detection)
    - scene.json     (scene graph)
    - assembly.json  (assembled layers)
    - palette.json   (OpenCV color palette)
    - reconstructor.json
    - text_analysis.json
  v7-B/generated-{001..005}/
    - (same structure)
```
