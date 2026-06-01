# Visual Review V6 — Pipeline Multi-Variante con Reconstructor, Font Matcher y Constraint Solver

**Pipeline V6**: 3 variantes (B, C, D) sobre Qwen3-VL + Florence-2 con:
- Reconstructor (Qwen o Gemini) para z-order y jerarquía
- Font Matcher integrado (crops → propiedades → fuente CSS)
- Corrección de alineación (center snap + bounds clamp)
- Constraint solver para espaciado y alineación (V6-D)

**Fix crítico V6**: Corrección de *double-scaling* en `to_scenegraph()` — coordenadas se escalaban 2× (Qwen canvas + real canvas), ahora protegido con flag `coordsScaled`.

---

## 1. Evaluador V6 — Nuevas Métricas

### Cambios vs V5

| Métrica | V5 (old) | V6 (new) | Cambio |
|---------|----------|----------|--------|
| **textAccuracy** | OCR original vs render (fragile) | Textos esperados del detection vs render OCR | ✅ Más robusto |
| **semantic** (Gemini judge) | Gemini vía OpenRouter, siempre 0.5 | ❌ Eliminado | — |
| **posterQuality** (new) | — | Legibilidad + Contraste + CTA (automático, sin API) | ✅ Nuevo |

**posterQuality** mide si el render **preserva la calidad** del original en 3 sub-dimensiones:
- **Legibilidad** (0.40): % de textos esperados legibles en original vs render
- **Contraste** (0.35): Similitud de contraste texto/fondo entre original y render
- **CTA** (0.25): Prominencia de llamadas a la acción (original vs render)

Score = 1 − |orig_quality − render_quality|. Si original y render tienen la misma calidad → 1.0, aunque ambos sean "bajos".

### Pesos finales

| Dimensión | Peso |
|-----------|:----:|
| Layout | 0.20 |
| Text Accuracy | 0.20 |
| Color Accuracy | 0.10 |
| Visual Similarity | 0.15 |
| Editability | 0.10 |
| Structure F1 | 0.10 |
| **Poster Quality** | **0.15** |

---

## 2. Comparativa de Variantes — poster-simple

| Dimensión | **V5 Base** | **V6-B** (Qwen→Qwen) | **V6-C** (Qwen→Gemini) | **V6-D** (Qwen→Solver) |
|-----------|:----------:|:--------------------:|:----------------------:|:----------------------:|
| Layout | 0.5998 | **0.8085** 🔥 | **0.7879** 🔥 | **0.7542** 🔥 |
| Text Accuracy | 0.8304 | **1.0000** ✅ | **1.0000** ✅ | 0.7500 |
| Color Accuracy | 0.5441 | 0.6095 | 0.6213 | **0.6284** |
| Visual Similarity | 0.7087 | **0.7921** | 0.7839 | 0.7798 |
| Editability | 0.8571 | **0.2857** ❌ | 0.4286 ❌ | **0.8571** ✅ |
| Structure F1 | **0.9048** | 0.7143 ❌ | 0.7489 ❌ | **0.9048** ✅ |
| Poster Quality | — | 0.5740 | 0.4800 | **0.7088** |
| **OVERALL** | **0.6979** | **0.7276** | **0.7271** | **0.7632** 🏆 |

### Análisis por variante

#### V6-B: Qwen detector + Qwen reconstructor + Font Matcher + Alignment
- **Layout**: +0.21 sobre V5 (coordinate fix + reconstructor zonifican mejor)
- **Text Accuracy**: **1.0** — los 4 textos de Qwen se renderizan correctamente
- **Editability**: **0.29** — el reconstructor Qwen cambia la estructura (de 4 textos a 8 capas)
- **posterQuality**: 0.5740 — el render tiene MEJOR legibilidad que el original (+0.25), pero el contraste es diferente

#### V6-C: Qwen detector + Gemini reconstructor + Font Matcher + Alignment
- Similar a B pero con Gemini como reconstructor
- **Editability**: 0.43 (mejor que B, peor que D) — Gemini es más conservador
- **Structure F1**: 0.75 — clasificación decente
- **posterQuality**: **0.48** — el peor, porque Gemini cambia colores y contrastes

#### V6-D 🏆: Qwen detector + Qwen reconstructor + Font Matcher + **Constraint Solver**
- **Editability**: 0.86 — el constraint solver preserva la estructura original
- **Structure F1**: **0.90** — igual que V5
- **posterQuality**: **0.71** — el que mejor preserva la calidad del original
- **OVERALL**: **0.7632** — el más alto

### ¿Por qué gana V6-D?

El constraint solver en D aplica:
1. **Detección de filas**: agrupa elementos por coordenada Y
2. **Alineación de bordes**: izquierda/derecha/centro
3. **Espaciado uniforme**: distribuye equitativamente

Esto mantiene la estructura de elementos del detection original, a diferencia del reconstructor en B/C que reordena capas.

---

## 3. Font Matcher Integrado (V6)

El `FontMatcher` se integra en el pipeline V6 para todos los textos:

### Flujo
```
Detection Qwen (textos + estilos)
  ↓ Crop de cada región de texto del render
  ↓ FontPropertyClassifier → weight, serif, width, posture
  ↓ Cosine similarity vs DB de 20 fuentes CSS
  ↓ Font + propiedades → assembly.json
```

### Resultados en poster-simple

| Texto | Fuente asignada | Score | Propiedades detectadas |
|-------|----------------|:-----:|----------------------|
| "SUMMER FEST" | **Impact** | 0.74 | bold, sans, expanded, upright |
| "AUGUST 15-17 · CENTRAL PARK" | **Oswald** | 0.65 | semibold, sans, expanded, upright |
| "NOW ON SALE" | **Bebas Neue** | 0.67 | bold, sans, expanded, upright |
| "Main Stage · Live Music" | **Montserrat** | 0.71 | regular, sans, normal, upright |

### Problemas detectados
- **Crops pequeños**: textos < 30px de alto → features poco fiables
- **Color de fondo interfiere**: crops con background complejo distorsionan features
- **Training-free**: el clasificador usa heurísticas (stroke width, Hough angles), no ML

---

## 4. Problemas Detectados → Roadmap V7

### 🔴 Críticos

| # | Problema | Impacto | Variante | Solución propuesta |
|---|----------|---------|----------|-------------------|
| 1 | **Duplicados Florence-2** en assembly | TextAccuracy NO se ve afectado (nueva métrica usa detection), pero Editability y estructura sí | B/C/D | Dedup por contenido normalizado + IoU |
| 2 | **Contraste 0** en algunos textos del render | 2/4 textos tienen render_contrast=0.0 → color texto = color fondo | B/C/D | Pipeline debe preservar color de texto del detection |
| 3 | **Reconstructor cambia estructura** | Editability 0.29-0.43 en B/C | B, C | No usar reconstructor para textos, solo para z-order |

### 🟡 Mejoras

| # | Problema | Impacto | Prioridad |
|---|----------|---------|:---------:|
| 4 | Texto "Main Stage · Live Music" OCR dividido (60% match) | Legibilidad parcial | Alta |
| 5 | postQuality legibilidad: original score 0.5 (2/4), render 0.75 (3/4) | Render mejor que original! | Baja |
| 6 | Font matcher: crops pequeños no fiables | Fuente incorrecta en textos pequeños | Media |
| 7 | Sin detección de efectos de texto (shadow, border, outline) | El pipeline no reproduce efectos visuales | Alta |

### 🆕 Propuestas para V7

El usuario ha definido el foco de V7:

> **V7**: mejorar la detección y fiabilidad y reconocimiento de textos, así como su tamaño, fuente, estilo, color, efectos (sombra, borde, etc.)

1. **Deduplicación robusta**: Normalizar textos (punctuation, case, whitespace) + filtro IoU + similitud semántica
2. **Metadata de texto en Qwen prompt**: Detectar explícitamente fontSize, fontWeight, fontFamily, textColor, textEffects (shadow, border, outline)
3. **Preservación de color**: Asegurar que el color del texto en el render coincide con el detection
4. **Soporte de efectos**: Detectar shadow/blur/outline en Qwen prompt y aplicar en render
5. **Reconstructor text-safe**: No modificar textos, solo z-index y jerarquía visual
6. **Evaluación extendida**: poster-gradient, meditacion y más imágenes

---

## 5. Resumen V5 → V6

| Componente | V5 | V6 |
|------------|----|----|
| Pipeline | Qwen + Florence-2 (IoU) | Qwen + Florence-2 + **Reconstructor** |
| Variantes | 1 | **3** (B: Qwen, C: Gemini, D: Solver) |
| Font Matcher | Independiente | **Integrado** en pipeline |
| Evaluador | 7D (Gemini semantic) | **7D** (posterQuality automático) |
| Text Accuracy (poster-simple) | 0.83 | **0.75–1.0** |
| Overall (poster-simple) | 0.70 | **0.7276–0.7632** 🏆 |

### Pendiente para V7

- [ ] Dedup Florence-2 en assembly (normalized text + IoU)
- [ ] Preservar color de texto del detection en el render
- [ ] Detectar fontSize, fontWeight, fontFamily en Qwen prompt
- [ ] Detectar efectos de texto (shadow, border, outline)
- [ ] Reconstructor text-safe: no modificar textos
- [ ] Corregir contraste 0 en render (t3, t4)
- [ ] Extender evaluación a poster-gradient y meditacion
- [ ] Documentar API de V7 en PROYECTO_BASE.md

---

<style>
table img { max-width: 240px; max-height: 200px; object-fit: contain; }
table td { vertical-align: middle; text-align: center; }
</style>
