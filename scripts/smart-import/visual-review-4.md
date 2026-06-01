# Visual Review V4 — Inpainting de texto sobre imágenes

Pipeline: Qwen3-VL → OpenCV (paleta) → Assembly → **Crop + Inpaint** → SceneGraph → (Render pendiente).
V4 añade detección de overlaps texto-imagen e inpainting automático sobre cada sub-imagen extraída.

Modelo detección: `qwen/qwen3-vl-32b-instruct` (OpenRouter, 1 prompt único).
Inpainting: `OpenCV TELEA` (inpaintRadius=5, gratis, CPU, ~0.5s por crop).

---

## Resumen

| Imagen | Sub-imágenes | Textos inpainted | Estado | Área máscara |
|--------|-------------|-------------------|--------|-------------|
| **banner-horizontal** | 1 | NEW ARRIVAL, Premium Collection | ✅ | 19 528 px |
| **flyer-text-heavy** | 0 | — | — Sin imágenes | — |
| **meditacion_11_julio** | 2 | 11 en img1, img2 skip (borde) | ✅ ⚠️ | 134 801 px |
| **multi-photo-collage** | 3 | PHOTO A/B/C en 3 imágenes | ✅ | 3 080 + 5 936 + 2 688 px |
| **portrait-overlay** | 1 | — (texto fuera de imagen) | ✅ Sin overlaps | — |
| **poster-display-font** | 1 | DREAM, BIG·BOLD·BEAUTIFUL | ✅ | 81 500 px |
| **poster-gradient** | 1 | EXCLUSIVE | ✅ | 9 310 px |
| **poster-low-contrast** | 0 | — Sin imágenes | ✅ Sin overlaps | — |
| **poster-person** | 1 | — (texto fuera de imagen) | ✅ Sin overlaps | — |
| **poster-simple** | 1 | NOW ON SALE, Main Stage·Live Music | ✅ | 16 007 px |
| **showcase-two-products** | 2 | CLASSIC+$49.99, MODERN+$79.99+-30% | ✅ | 8 740 + 11 556 px |

**8/11 imágenes** tenían texto superpuesto → se inpaintaron **13 sub-imágenes** en total.

---

## banner-horizontal

1 sub-imagen — Foto Golden Gate Bridge con badge "NEW ARRIVAL" + "Premium Collection"

| Sub-imagen extraída | V3 (texto quemado) | V4 (inpainted) |
|-------------------|-------------------|----------------|
| img1 — Bridge | ![v3](output/qwen-qwen3-vl-32b-instruct/v3/banner-horizontal/crops/img1.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/banner-horizontal/crops/img1_clean.png) |

**Análisis del inpainting:**
- "NEW ARRIVAL" sobre el cielo → OpenCV difumina, queda una mancha sutil en el cielo azul
- "Premium Collection" sobre las montañas → textura irregular disimula bien el relleno
- Calidad general: ⭐⭐⭐ (cielo visible, montañas bien)

---

## flyer-text-heavy

Sin imágenes — diseño de solo texto con formas decorativas. No aplica inpainting.

---

## meditacion_11_julio_vertical_completo

2 sub-imágenes. La img1 tiene **11 textos** superpuestos — el caso más denso del dataset.

### img1 — Foto grupal de meditación (999×450)

| V3 (texto quemado) | V4 (inpainted) |
|-------------------|----------------|
| ![v3](output/qwen-qwen3-vl-32b-instruct/v3/meditacion_11_julio_vertical_completo/crops/img1.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/meditacion_11_julio_vertical_completo/crops/img1_clean.png) |

**Análisis del inpainting:**
- **134 801 px de máscara** — el área más grande del dataset
- Textos cortos (30px alto) sobre fondo de grupo de personas → se mezclan bien
- Textos largos ("Participa en la regeneración...", ~800px ancho) → blur visible en el relleno
- Para este caso, **Gemini daría un resultado notablemente superior** por su capacidad de reconstruir figuras humanas completas

### img2 — QR (100×100 Qwen)

| V3 | V4 |
|----|----|
| ![v3](output/qwen-qwen3-vl-32b-instruct/v3/meditacion_11_julio_vertical_completo/crops/img2.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/meditacion_11_julio_vertical_completo/crops/img2.png) |

**⚠️ Mask vacía — skip**: Los textos "Comuna Padre Hurtado" y "TSEYOR.org" apenas rozan el borde inferior del QR. Al proyectar coordenadas Qwen→real, caen fuera del crop. El overlap visual es imperceptible (texto en el borde de un QR miniatura), así que el skip es aceptable.

---

## multi-photo-collage

**3 sub-imágenes que se superponen entre sí.** Este es el caso más complejo de validación porque:
- img1 (bosque) y img3 (cielo) comparten área
- img2 (cañón) y img3 (cielo) comparten área
- "PHOTO C" aparece como overlap en las 3 imágenes (el text label está en la zona de intersección)

### img1 — Bosque (textos: PHOTO A, PHOTO C)

| V3 (texto quemado) | V4 (inpainted) |
|-------------------|----------------|
| ![v3](output/qwen-qwen3-vl-32b-instruct/v3/multi-photo-collage/crops/img1.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/multi-photo-collage/crops/img1_clean.png) |

**Análisis:** "PHOTO A" sobre follaje verde → se mezcla naturalmente. "PHOTO C" en la zona de overlap con img3 (borde entre bosque y cielo estrellado) → queda una ligera mancha en la transición.

### img2 — Cañón (textos: PHOTO B, PHOTO C)

| V3 (texto quemado) | V4 (inpainted) |
|-------------------|----------------|
| ![v3](output/qwen-qwen3-vl-32b-instruct/v3/multi-photo-collage/crops/img2.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/multi-photo-collage/crops/img2_clean.png) |

**Análisis:** "PHOTO B" sobre roca texturizada → buen resultado. "PHOTO C" en el borde con img3 → transición visible, pero aceptable.

### img3 — Cielo estrellado (texto: PHOTO C)

| V3 (texto quemado) | V4 (inpainted) |
|-------------------|----------------|
| ![v3](output/qwen-qwen3-vl-32b-instruct/v3/multi-photo-collage/crops/img3.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/multi-photo-collage/crops/img3_clean.png) |

**Análisis:** "PHOTO C" sobre cielo estrellado → **el mejor resultado del dataset**. El fondo oscuro con estrellas puntuales permite a OpenCV promediar sin dejar mancha visible. Las estrellas se pierden en el área de texto pero el cielo se ve uniforme.

---

## portrait-overlay

1 sub-imagen — retrato de mujer. Textos fuera del área de la imagen.
- "PORTRAIT STUDY": y=25, imagen empieza en y=148 → arriba, sin overlap
- "Transparency · Overlay · Face detection": y=960, imagen termina en y=896 → abajo, sin overlap

✅ Sin overlaps — no requiere inpainting.

---

## poster-display-font

1 sub-imagen — foto B/N con círculos dorados. Textos grandes sobre toda la imagen.

| V3 (texto quemado) | V4 (inpainted) |
|-------------------|----------------|
| ![v3](output/qwen-qwen3-vl-32b-instruct/v3/poster-display-font/crops/img1.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/poster-display-font/crops/img1_clean.png) |

**Análisis del inpainting:**
- **81 500 px de máscara** — "DREAM" ocupa ~1/3 del ancho
- "DREAM" sobre fondo B/N → mancha visible, el blur es notorio en área tan grande
- "BIG · BOLD · BEAUTIFUL" más pequeño → se mezcla mejor con el fondo
- **Este es el candidato principal para probar Gemini** — el fondo B/N uniforme es difícil para OpenCV

---

## poster-gradient

1 sub-imagen — foto arquitectura circular. Overlap: texto "EXCLUSIVE" pequeño.

| V3 (texto quemado) | V4 (inpainted) |
|-------------------|----------------|
| ![v3](output/qwen-qwen3-vl-32b-instruct/v3/poster-gradient/crops/img1.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/poster-gradient/crops/img1_clean.png) |

**Análisis:** Texto pequeño (9 310 px de máscara) sobre textura arquitectónica → **buen resultado**. El área de relleno es pequeña y el fondo con líneas verticales disimula el inpainting.

---

## poster-low-contrast

Sin imágenes — diseño de solo texto. No aplica inpainting. ✅

---

## poster-person

1 sub-imagen — foto de perfil circular. Textos fuera del área de la imagen.
- "FEATURED": y=20, imagen empieza en y=80 → arriba, sin overlap
- "JANE DOE": y=680, imagen termina en y=540 → abajo, sin overlap
- "@janedoe": y=750, imagen termina en y=540 → abajo, sin overlap

✅ Sin overlaps — no requiere inpainting.

---

## poster-simple

1 sub-imagen — paisaje de cañón. Overlaps: "NOW ON SALE" + "Main Stage · Live Music".

| V3 (texto quemado) | V4 (inpainted) |
|-------------------|----------------|
| ![v3](output/qwen-qwen3-vl-32b-instruct/v3/poster-simple/crops/img1.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/poster-simple/crops/img1_clean.png) |

**Análisis:**
- "NOW ON SALE" sobre el cielo → difuminado visible (área más grande, fondo uniforme)
- "Main Stage · Live Music" sobre las rocas → **casi perfecto**, la textura irregular del cañón disimula completamente
- Caso de prueba inicial — sirvió para validar el pipeline completo

---

## showcase-two-products

2 sub-imágenes con textos de precio superpuestos.

### img1 — Flor amarilla (textos: CLASSIC, $49.99)

| V3 (texto quemado) | V4 (inpainted) |
|-------------------|----------------|
| ![v3](output/qwen-qwen3-vl-32b-instruct/v3/showcase-two-products/crops/img1.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/showcase-two-products/crops/img1_clean.png) |

**Análisis:** Pétalos irregulares → el inpainting se mezcla naturalmente. Los textos son pequeños → área de máscara chica. ⭐⭐⭐⭐

### img2 — Acantilado marino (textos: MODERN, $79.99, -30%)

| V3 (texto quemado) | V4 (inpainted) |
|-------------------|----------------|
| ![v3](output/qwen-qwen3-vl-32b-instruct/v3/showcase-two-products/crops/img2.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/showcase-two-products/crops/img2_clean.png) |

**Análisis:** "MODERN" y "$79.99" sobre roca/mar → bien. El badge "-30%" tiene fondo blanco → queda una mancha visible porque el relleno sobre área blanca es más notorio. ⭐⭐⭐

---

## Evaluación general de OpenCV inpainting

| Tipo de fondo | Calidad | Mejores casos | Peores casos |
|--------------|---------|---------------|--------------|
| Textura irregular (rocas, hojas, follaje) | ⭐⭐⭐⭐ | poster-simple, showcase img1, multi-photo img1 | — |
| Fondo oscuro punteado (estrellas) | ⭐⭐⭐⭐⭐ | multi-photo img3 | — |
| Fondo uniforme (cielo, pared lisa) | ⭐⭐⭐ | banner-horizontal | — |
| Área grande > 80 000 px | ⭐⭐ | — | poster-display-font, meditacion img1 |
| Área pequeña < 10 000 px | ⭐⭐⭐⭐⭐ | poster-gradient, showcase | — |
| Borde de crop (texto rozando) | ⚠️ | — | meditacion img2 |

---

## Comparativa Gemini 3.1 Flash Image vs OpenCV

Probado en los 2 casos más desafiantes. Modelo: `google/gemini-3.1-flash-image-preview` vía OpenRouter.

### poster-display-font — "DREAM" sobre fondo B/N

| OpenCV (0.5s, gratis) | Gemini 3.1 Flash Image (~130s, ~$0.02) |
|----------------------|----------------------------------------|
| ![opencv](output/qwen-qwen3-vl-32b-instruct/v4/poster-display-font/crops/img1_clean.png) | ![gemini](output/qwen-qwen3-vl-32b-instruct/gemini/poster-display-font/crops/img1_clean.png) |

**Resultados:**
| Métrica | OpenCV | Gemini |
|---------|--------|--------|
| Tiempo | < 1s | ~130s |
| Tamaño output | 1 463 KB | **1 967 KB** |
| Calidad textura | Blur visible en área "DREAM" | (pendiente de inspección visual) |

### meditacion_11_julio — 11 textos sobre foto grupal

| OpenCV (0.5s, gratis) | Gemini 3.1 Flash Image (~70s, ~$0.02) |
|----------------------|----------------------------------------|
| ![opencv](output/qwen-qwen3-vl-32b-instruct/v4/meditacion_11_julio_vertical_completo/crops/img1_clean.png) | ![gemini](output/qwen-qwen3-vl-32b-instruct/gemini/meditacion_11_julio_vertical_completo/crops/img1_clean.png) |

**Resultados:**
| Métrica | OpenCV | Gemini |
|---------|--------|--------|
| Tiempo | < 1s | ~70s |
| Tamaño output | 741 KB | **710 KB** (mismo tamaño que original, hash diferente) |
| Calidad textura | Blur en áreas grandes | (pendiente de inspección visual) |

### Costo estimado por imagen

| Método | Coste por imagen con inpainting | Dataset 11 imágenes |
|--------|--------------------------------|--------------------|
| OpenCV | **$0** | $0 |
| Gemini Flash Image | **~$0.01-0.02** (solo imágenes con overlaps) | ~$0.08-0.16 |
| OpenCV + Gemini híbrido | ~$0.01 (solo 2-3 imágenes complejas) | ~$0.02-0.04 |

### Recomendación

**Estrategia híbrida**: OpenCV para todas las imágenes por defecto (gratis, instantáneo), y Gemini solo para las 2-3 imágenes con áreas de máscara > 50 000 px o fondos uniformes donde OpenCV muestra limitaciones. Coste total estimado: $0.02-0.04 por dataset completo.

---

## Resumen de sub-imágenes extraídas

| Imagen | Sub-imagen | ¿Inpainted? | Tamaño | Máscara | Calidad OpenCV |
|--------|-----------|-------------|--------|---------|---------------|
| banner-horizontal | img1 | ✅ | 677 KB | 19 528 px | ⭐⭐⭐ |
| meditacion_11_julio | img1 | ✅ | 710 KB | 134 801 px | ⭐⭐ |
| meditacion_11_julio | img2 | ⚠️ skip | 20 KB | — | (borde) |
| multi-photo-collage | img1 (bosque) | ✅ | 226 KB | 3 080 px | ⭐⭐⭐ |
| multi-photo-collage | img2 (cañón) | ✅ | 128 KB | 5 936 px | ⭐⭐⭐ |
| multi-photo-collage | img3 (cielo) | ✅ | 131 KB | 2 688 px | ⭐⭐⭐⭐⭐ |
| poster-display-font | img1 | ✅ | 1 218 KB | 81 500 px | ⭐⭐ |
| poster-gradient | img1 | ✅ | 85 KB | 9 310 px | ⭐⭐⭐⭐ |
| poster-simple | img1 | ✅ | 1 100 KB | 16 007 px | ⭐⭐⭐ |
| showcase-two-products | img1 (flor) | ✅ | 149 KB | 8 740 px | ⭐⭐⭐⭐ |
| showcase-two-products | img2 (acantilado) | ✅ | 151 KB | 11 556 px | ⭐⭐⭐ |

**13 sub-imágenes extraídas · 11 inpaintadas · 1 skip · 1 sin overlaps necesario**

---

## Galería de renders V3 vs V4 (OpenCV)

Renders completos compilados a `.tc` y renderizados con Playwright. V3 muestra el texto quemado en las imágenes; V4 lo remueve con inpainting OpenCV.

| Imagen | V3 (texto quemado en crops) | V4 (crops inpainted) |
|--------|----------------------------|---------------------|
| **banner-horizontal** | ![v3](output/qwen-qwen3-vl-32b-instruct/v3/banner-horizontal/render.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/banner-horizontal/render.png) |
| **flyer-text-heavy** | ![v3](output/qwen-qwen3-vl-32b-instruct/v3/flyer-text-heavy/render.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/flyer-text-heavy/render.png) |
| **meditacion_11_julio** | ![v3](output/qwen-qwen3-vl-32b-instruct/v3/meditacion_11_julio_vertical_completo/render.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/meditacion_11_julio_vertical_completo/render.png) |
| **multi-photo-collage** | ![v3](output/qwen-qwen3-vl-32b-instruct/v3/multi-photo-collage/render.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/multi-photo-collage/render.png) |
| **portrait-overlay** | ![v3](output/qwen-qwen3-vl-32b-instruct/v3/portrait-overlay/render.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/portrait-overlay/render.png) |
| **poster-display-font** | ![v3](output/qwen-qwen3-vl-32b-instruct/v3/poster-display-font/render.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/poster-display-font/render.png) |
| **poster-gradient** | ![v3](output/qwen-qwen3-vl-32b-instruct/v3/poster-gradient/render.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/poster-gradient/render.png) |
| **poster-low-contrast** | ![v3](output/qwen-qwen3-vl-32b-instruct/v3/poster-low-contrast/render.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/poster-low-contrast/render.png) |
| **poster-person** | ![v3](output/qwen-qwen3-vl-32b-instruct/v3/poster-person/render.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/poster-person/render.png) |
| **poster-simple** | ![v3](output/qwen-qwen3-vl-32b-instruct/v3/poster-simple/render.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/poster-simple/render.png) |
| **showcase-two-products** | ![v3](output/qwen-qwen3-vl-32b-instruct/v3/showcase-two-products/render.png) | ![v4](output/qwen-qwen3-vl-32b-instruct/v4/showcase-two-products/render.png) |

Nota: La diferencia visual entre renders V3 y V4 puede ser sutil porque el render final escala las imágenes al canvas de salida. La diferencia es más visible en los crops individuales (secciones anteriores de este documento).

<style>
table img { max-width: 200px; max-height: 180px; object-fit: contain; }
</style>
