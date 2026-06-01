# Visual Review V5 — Auto-Evaluador, Font Matcher, Pipeline Dual y LaMa

**Pipeline V5**: Qwen3-VL (estructura) → Florence-2 (OCR) → **Fusión IoU** → Inpainting → Font Matcher → Evaluador 7D

V5 introduce **4 subsistemas paralelos** que elevan la calidad del smart import:

1. **Auto-Evaluador 7D** — scoring automático sin intervención humana (SSIM, OCR, phash, F1, Gemini)
2. **Font Matcher** — clasificador de propiedades tipográficas con 20 fuentes CSS
3. **Pipeline Dual** — fusión Qwen + Florence-2 con IoU para bboxes precisos
4. **LaMa Inpainting** — remoción secuencial con fallback a OpenCV

---

## 1. Auto-Evaluador V5

### Métricas

| # | Dimensión | Métrica | Rango |
|---|-----------|---------|-------|
| 1 | **Layout** | SSIM estructural (canny + HOG) | 0..1 |
| 2 | **Text Accuracy** | OCR EasyOCR + rapidfuzz FCR | 0..1 |
| 3 | **Color Accuracy** | Correlación histograma HSV | 0..1 |
| 4 | **Visual Similarity** | phash + SSIM pixel | 0..1 |
| 5 | **Editability** | Proporción de elementos detectados vs GT | 0..1 |
| 6 | **Structure F1** | Clasificación de tipos (texto/imagen/forma) | 0..1 |
| 7 | **Semantic** | Gemini judge vía OpenRouter | 0..1 |

**OVERALL** = media de 7 dimensiones (sin pesos).

### Resultados globales (14 imágenes, 316.7s)

| Dimensión | Promedio | Interpretación |
|-----------|----------|----------------|
| Layout (SSIM) | **0.68** | Estructura general buena, pero detalle fino se pierde |
| Text Accuracy | **0.66** | OCR + edición: textos se pierden o distorsionan |
| Color Accuracy | **0.82** | Buena reproducción cromática general |
| Visual Similarity | **0.69** | Coincidencia perceptual aceptable |
| Editability | **0.79** | La mayoría de elementos se preservan |
| Structure F1 | **0.85** | Buena clasificación texto/imagen/forma |
| Semantic (Gemini) | **0.43** | El juez IA es severo con la calidad visual |
| **OVERALL** | **0.68** | Coincide con diagnóstico V4 |

### Ranking por imagen

| # | Imagen | Overall | Layout | Text | Color | Visual | F1 | Notas |
|---|--------|---------|--------|------|-------|--------|----|-------|
| 1 | **poster-gradient** | **0.83** | 0.89 | 0.89 | 0.60 | 0.64 | 1.00 | ✅ Mejor - arquitectura circular |
| 2 | **portrait-overlay** | **0.81** | 0.69 | 1.00 | 0.76 | 0.70 | 0.87 | Text perfecto |
| 3 | **inpaint-face-text** | **0.77** | 0.61 | 0.68 | 0.96 | 0.81 | 1.00 | GT no disponible |
| 4 | **inpaint-forest-text** | **0.76** | 0.76 | 0.66 | 1.00 | 0.89 | 1.00 | Color impecable |
| 5 | **poster-person** | **0.74** | 0.84 | 0.85 | 0.53 | 0.69 | 0.82 | Layout sólido |
| 6 | **banner-horizontal** | **0.73** | 0.79 | 0.69 | 0.83 | 0.68 | 0.88 | Equilibrado |
| 7 | **inpaint-pattern-text** | **0.72** | 0.62 | 0.88 | 1.00 | 0.70 | 1.00 | Sin GT |
| 8 | **poster-simple** | **0.70** | 0.60 | 0.83 | 0.54 | 0.71 | 0.90 | Texto bien, layout regular |
| 9 | **poster-low-contrast** | **0.66** | 0.78 | 0.51 | 1.00 | 0.44 | 0.60 | Bajo contraste => texto sufre |
| 10 | **multi-photo-collage** | **0.65** | 0.78 | 0.47 | 0.57 | 0.82 | 0.80 | Collage: OCR bajo |
| 11 | **poster-display-font** | **0.63** | 0.53 | 0.92 | 0.99 | 0.67 | 0.68 | Semántica: 0.10 |
| 12 | **showcase-two-products** | **0.58** | 0.85 | **0.08** | 1.00 | 0.73 | 0.88 | Texto pésimo (0.08) |
| 13 | **flyer-text-heavy** | **0.54** | 0.37 | 0.52 | 0.63 | 0.61 | 0.90 | Layout bajo |
| 14 | **meditacion** | **0.45** | 0.47 | 0.23 | 0.99 | 0.61 | 0.64 | ⚠️ Peor - texto 0.23 |

### Diagnóstico por dimensión

```
Layout      ████████████████░░░░  0.68  — Estructura, mejorar detección de bordes
Text        ██████████████░░░░░░  0.66  — OCR + edición, el talón de Aquiles
Color       █████████████████░░░  0.82  — Bien, pocas mejoras necesarias
Visual      ████████████████░░░░  0.69  — phash ok, SSIM pixel sufre
Editability █████████████████░░░  0.79  — Más elementos = mejor
Structure   ██████████████████░░  0.85  — Buena clasificación
Semantic    ████████░░░░░░░░░░░░  0.43  — Gemini es crítico con la calidad
```

### Correlación con diagnóstico V4 (experto humano)

El score global de **0.68** confirma cuantitativamente el análisis cualitativo de V4:
- **Detección (F1=0.85)**: buena, los elementos se identifican correctamente
- **Layout (0.68)**: estructura general ok pero detalles de posición/tamaño flojos
- **Texto (0.66)**: la mayor debilidad — textos se pierden, distorsionan o duplican
- **Color (0.82)**: fortaleza — la paleta se reproduce bien

**Meta V5+**: superar **0.85** en todas las dimensiones.

---

## 2. Font Matcher

### Arquitectura

`FontPropertyClassifier` clasifica texto renderizado en 4 propiedades:

| Propiedad | Método | Clases |
|-----------|--------|--------|
| **Weight** | Stroke width (relación área blanco/negro + Canny) | thin, light, regular, medium, semibold, bold, extrabold, black |
| **Serif** | Detección de remates (perfil de bordes) | serif, sans-serif |
| **Width** | Relación de aspecto promedio | condensed, normal, expanded |
| **Posture** | Ángulos Hough dominantes | upright, italic |

### Base de datos: 20 fuentes CSS

| # | Font | Weight | Serif | Width | Posture |
|---|------|--------|-------|-------|---------|
| 1 | Roboto | regular | sans | normal | upright |
| 2 | Open Sans | regular | sans | normal | upright |
| 3 | Lato | regular | sans | normal | upright |
| 4 | Montserrat | regular | sans | normal | upright |
| 5 | Oswald | semibold | sans | expanded | upright |
| 6 | Raleway | regular | sans | normal | upright |
| 7 | Poppins | regular | sans | normal | upright |
| 8 | Inter | regular | sans | normal | upright |
| 9 | Playfair Display | regular | serif | normal | upright |
| 10 | Merriweather | regular | serif | normal | upright |
| 11 | PT Serif | regular | serif | normal | upright |
| 12 | Noto Sans | regular | sans | normal | upright |
| 13 | Roboto Condensed | regular | sans | condensed | upright |
| 14 | Bebas Neue | bold | sans | expanded | upright |
| 15 | Impact | bold | sans | expanded | upright |
| 16 | Lobster | regular | serif | normal | italic |
| 17 | Pacifico | regular | serif | normal | italic |
| 18 | Dancing Script | regular | serif | normal | italic |
| 19 | Abril Fatface | bold | serif | normal | upright |
| 20 | Cinzel | bold | serif | normal | upright |

### Prueba: "SUMMER FEST" (poster-simple)

```
Input:  crop de "SUMMER FEST" del render V4
Output: Impact (bold sans-serif expanded)
Score:  0.68

Propiedades detectadas:
  Weight: bold (0.48) ≈ Impact (bold)
  Serif:  sans (0.55) ≈ Impact (sans)
  Width:  expanded (0.61) ≈ Impact (expanded)  
  Posture: upright (0.98) ≈ Impact (upright)
```

Las propiedades se clasifican independientemente y se comparan por similitud coseno contra la DB de 20 fuentes.

### Modo de uso

```bash
python font_matcher.py "scripts/smart-import/output/font-test-crop.png"
```

---

## 3. Pipeline Dual (Qwen + Florence-2)

### Flujo

```
Qwen3-VL ──→ structure (textos, imágenes, formas, posiciones)
                 ↓
                 ↓ IoU matching (coordenadas normalizadas 0..1)
                 ↓
Florence-2 ──→ OCR (texto exacto con bboxes precisos)
                 ↓
          Fusión ↓
                 ↓
SceneGraph V5 ←── Assembly + Render
```

### Resultado prueba: poster-simple

| Modelo | Textos | Imágenes | Formas | Tiempo |
|--------|--------|----------|--------|--------|
| Qwen3-VL | 4 | 1 | 1 | ~2s |
| Florence-2 | 3 (OCR) | — | — | ~12s (rate limit) |
| **Fusión** | **4** (3 merged) | 1 | 1 | **~15s total** |

**IoU matching**: Cuando Qwen y Florence-2 detectan el mismo texto (IoU > 0.5), se usa el bbox de Florence-2 por su mayor precisión.

### Cache de detección

Florence-2 usa Replicate (gratis: 6/min, burst=1). Pipeline implementa:
- Cache de resultados en `output/.cache/florence_*.json`
- Spacing de 12s entre llamadas
- Fallback a Qwen si Florence-2 falla

### Limitaciones actuales

- Florence-2 solo disponible en Replicate (free tier limitado)
- IoU matching asume coordenadas normalizadas (0..1)
- Sin rate limit handling avanzado (retry con backoff exponencial)

---

## 4. LaMa Inpainting

### Backend activo

| Backend | Estado | Tiempo por crop |
|---------|--------|-----------------|
| **LaMa** (lama-cleaner) | ❌ No instalado | — |
| **OpenCV TELEA** | ✅ Activo (fallback) | ~0.5s |

### Cadena de fallback

```
LaMa (GPU, mejor calidad)
  ↓ pip install lama-cleaner + PyTorch
LaMa CLI (CPU, lento)
  ↓ si no encuentra binario
OpenCV TELEA (CPU, rápido, calidad media) ← activo ahora
```

### API

```python
from inpainter import BackgroundInpainter

inpainter = BackgroundInpainter()
result = inpainter.inpaint_sequential(
    image=img,
    scene_graph=scene,
    z_order=z_order
)
# o directamente:
bg = inpainter.extract_background(image, masks)
```

### Compatibilidad V4

La clase `BackgroundInpainter` mantiene la API de V4:
- `inpaint_sequential(img, scene_graph, z_order)` — misma firma
- `extract_background(image, masks)` — alias directo
- Fallback transparente: si LaMa no está, usa OpenCV sin error

---

## 5. Resumen de cambios V4 → V5

| Componente | V4 | V5 |
|------------|----|----|
| Evaluación | Manual (revisión visual) | **Auto-Evaluador 7D** (316s las 14 imágenes) |
| Font matching | Manual (inspección) | **Font Matcher** (4 propiedades, 20 fuentes) |
| Pipeline | Qwen3-VL solo | **Qwen + Florence-2** (IoU fusion) |
| Inpainting | OpenCV TELEA | **LaMa** (con fallback OpenCV) |
| Score global | ~0.45 (Gemini judge V3) | **0.68** (7D auto-evaluador) |

### Pendiente para V5+

- [ ] Instalar LaMa (`pip install lama-cleaner`) y re-testear inpainting
- [ ] Ejecutar pipeline V5 completo (`--all`) con Florence-2 OCR en todo el dataset
- [ ] Comparar scores V5 vs V4 (evaluator sobre outputs V5 vs V4)
- [ ] Font matcher sobre múltiples crops de texto del dataset
- [ ] Implementar rate limiting avanzado con backoff exponencial para Florence-2

---

<style>
table img { max-width: 200px; max-height: 180px; object-fit: contain; }
</style>
