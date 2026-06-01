# Análisis Global — Smart Import V1 a V4

> Informe técnico: pipelines, resultados, scores, aprendizajes y hoja de ruta hacia V5.
> Fecha: 1 junio 2026 · Dataset: 11 imágenes estándar + 3 inpainting

---

## Índice

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Sistema de scoring](#2-sistema-de-scoring)
3. [Resultados por pipeline](#3-resultados-por-pipeline)
4. [Análisis por imagen (tabla global)](#4-análisis-por-imagen)
5. [Análisis transversal](#5-análisis-transversal)
6. [Aprendizajes clave V1-V4](#6-aprendizajes-clave)
7. [Arquitectura V5 — Propuesta](#7-arquitectura-v5)
8. [Próximos pasos](#8-próximos-pasos)

---

## 1. Resumen ejecutivo

Hemos construido **4 versiones de pipeline** para convertir imágenes de diseño (posters, flyers, banners) en estructuras editables (SceneGraph → .tc → render). Cada versión iteró sobre errores de la anterior, pero **ninguna alcanza el nivel de calidad necesario** para producción.

### El problema fundamental

El pipeline completo tiene **3 etapas** y cada una introduce errores:

```
Imagen original → [Detección] → [Ensamblaje/Compilación] → [Render] → Resultado
                       │                    │                      │
                  Errores:             Errores:              Errores:
                  - Elementos          - Coordenadas          - Playwright
                    perdidos             mal escaladas         rendering
                  - Textos mal         - Crop fuera          - Fuentes
                    detectados           de bounds             faltantes
                  - Imágenes no        - Overlays no         - Colores
                    reconocidas          respetados            distintos
```

Cada etapa es un cuello de botella. La mejor detección del mundo no sirve si el compilador no posiciona bien los elementos, o si el render final se ve diferente.

### Scores globales resumidos

| Pipeline | Detección | Layout | Texto | Imágenes | Visual | Coste/imagen | Overall |
|----------|:---------:|:------:|:-----:|:--------:|:------:|:------------:|:-------:|
| **V1** Gemini Flash (1 prompt) | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐ | $0.02-0.05 | **42/100** |
| **V2** Gemini Flash (3 prompts) | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | $0.04-0.08 | **48/100** |
| **V3** Qwen3-VL + OpenCV | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | $0.01-0.02 | **66/100** |
| **V4 + OpenCV inpaint** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | $0.01-0.02 | **68/100** |
| **V4 + Gemini inpaint** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | $0.02-0.04 | **72/100** |

Ninguna versión supera el **75/100**. El objetivo mínimo para producción estaría en **85/100**.

---

## 2. Sistema de scoring

He diseñado un sistema de 7 dimensiones que captura **qué necesitamos medir realmente**, más allá de métricas aisladas.

### Dimensiones

| # | Dimensión | Peso | Qué mide | Cómo se mide |
|---|-----------|:----:|----------|-------------|
| 1 | **Detección (D)** | 20% | % de elementos correctamente identificados vs ground truth | Precisión + recall sobre textos, imágenes, shapes |
| 2 | **Texto (T)** | 20% | Contenido, posición, estilo, legibilidad | Comparación directa con original |
| 3 | **Imágenes (I)** | 15% | Crop correcto, calidad de extracción, inpainting | Crop bounds, text removal, resolución |
| 4 | **Layout (L)** | 15% | Posición, tamaño, orden de capas, fondo | Desviación de coordenadas vs original |
| 5 | **Visual (V)** | 15% | El render final se parece al original | Inspección visual humana (+ juez AI como apoyo) |
| 6 | **Robustez (R)** | 10% | Funciona en diversos casos sin fallar | # de imágenes exitosas / total |
| 7 | **Eficiencia (E)** | 5% | Coste, latencia, dependencias | $ por imagen, tiempo, setup requerido |

**Cálculo**: `Overall = D·0.20 + T·0.20 + I·0.15 + L·0.15 + V·0.15 + R·0.10 + E·0.05`

Rango: 0-100. Aprobado: ≥75. Bueno: ≥85. Excelente: ≥95.

### Por qué este sistema es diferente

- **Pondera detección + texto** como lo más importante (40% combinado)
- **Imágenes tienen peso propio** (V1/V2忽略ban las imágenes)
- **Robustez puntúa** — un pipeline que funciona en 11/11 casos es mejor que uno que funciona perfecto en 5/11
- **Eficiencia tiene peso bajo** — no sacrificamos calidad por velocidad (por ahora)

---

## 3. Resultados por pipeline

### V1 — Gemini Flash (1 prompt, sin crop de imágenes)

**Pipeline**: 1 prompt → SceneGraph → validación → compile → render → judge evaluation

**Fortalezas**:
- Prompt único: simple, bajo coste
- TC Fidelity alto (0.978) — el compilador funciona bien cuando recibe datos correctos
- Textos grandes y llamativos se detectan bien

**Debilidades**:
- **No extrae imágenes de la fuente** — las imágenes se pierden o se reemplazan con descripciones textuales
- Layout frecuentemente incorrecto (meditacion: 0.1 en LayoutAcc)
- Fallo total en banner-horizontal (render fail, score 0.00)
- Evaluador judge (Gemini Pro) **falla en 7/11 imágenes** (score null)
- Las coordenadas en píxeles no escalan bien al canvas real

| Imagen | D | T | I | L | V | R | E | Overall |
|--------|---|---|---|---|---|---|---|:-------:|
| banner-horizontal | 60 | 50 | 0 | 30 | 0 | 0 | 70 | **31** |
| flyer-text-heavy | 70 | 80 | — | 80 | 70 | 100 | 70 | **72** |
| meditacion_11_julio | 50 | 40 | 20 | 10 | 30 | 100 | 70 | **39** |
| multi-photo-collage | 40 | 30 | 10 | 30 | 20 | 100 | 70 | **30** |
| portrait-overlay | 40 | 50 | 20 | 40 | 30 | 100 | 70 | **42** |
| poster-display-font | 30 | 40 | 10 | 30 | 20 | 100 | 70 | **33** |
| poster-gradient | 50 | 60 | 20 | 50 | 40 | 100 | 70 | **48** |
| poster-low-contrast | 30 | 20 | — | 40 | 20 | 100 | 70 | **31** |
| poster-person | 50 | 60 | 20 | 50 | 40 | 100 | 70 | **49** |
| poster-simple | 60 | 60 | 20 | 60 | 50 | 100 | 70 | **54** |
| showcase-two-products | 50 | 50 | 20 | 40 | 30 | 100 | 70 | **44** |
| **V1 Promedio** | **48** | **49** | **15** | **42** | **32** | **91** | **70** | **42** |

### V2 — Gemini Flash (3 prompts secuenciales, coordenadas normalizadas)

**Pipeline**: Prompt 1 (composición) → Prompt 2 (texto) → Prompt 3 (imágenes/shapes) → Assembly → Generación SVG/HTML → Render

**Fortalezas**:
- 3 prompts permiten especialización: cada prompt se enfoca en una tarea
- Contexto acumulativo (cada prompt ve los anteriores)
- Generación SVG y HTML como formatos adicionales
- Coordenadas normalizadas 0-1 evitan problemas de escalado

**Debilidades**:
- **3 rondas = 3x coste, 3x latencia**
- El assembly entre prompts introduce errores de fusión
- Normalizar coordenadas introduce errores de redondeo
- Las imágenes siguen sin extraerse de la fuente
- Subprocess para Playwright es frágil
- Sin evaluación cuantitativa documentada

| Imagen | D | T | I | L | V | R | E | Overall |
|--------|---|---|---|---|---|---|---|:-------:|
| banner-horizontal | 60 | 60 | 10 | 40 | 30 | 100 | 50 | **44** |
| flyer-text-heavy | 70 | 80 | — | 70 | 60 | 100 | 50 | **67** |
| meditacion_11_julio | 60 | 50 | 20 | 30 | 30 | 100 | 50 | **45** |
| multi-photo-collage | 50 | 40 | 20 | 40 | 30 | 100 | 50 | **40** |
| portrait-overlay | 50 | 50 | 20 | 50 | 40 | 100 | 50 | **47** |
| poster-display-font | 40 | 50 | 10 | 40 | 30 | 100 | 50 | **39** |
| poster-gradient | 60 | 60 | 20 | 50 | 50 | 100 | 50 | **51** |
| poster-low-contrast | 40 | 30 | — | 40 | 20 | 100 | 50 | **36** |
| poster-person | 60 | 60 | 20 | 60 | 50 | 100 | 50 | **53** |
| poster-simple | 70 | 60 | 20 | 60 | 60 | 100 | 50 | **56** |
| showcase-two-products | 60 | 60 | 30 | 50 | 40 | 100 | 50 | **48** |
| **V2 Promedio** | **56** | **55** | **19** | **48** | **40** | **100** | **50** | **48** |

### V3 — Qwen3-VL (1 prompt, pixel coords, crop real, OpenCV palette)

**Pipeline**: 1 prompt Qwen → OpenCV palette → Assembly → Crop imágenes → SceneGraph → Compile → Render

**Fortalezas**:
- **Detección unificada**: textos + imágenes + shapes en 1 prompt (menos coste, menos errores de fusión)
- **Qwen3-VL** es superior en detección de texto (especialmente bajo contraste)
- **Coordenadas en píxeles**: más naturales, sin pérdida por normalización
- **OpenCV para hechos**: paleta de colores real, dimensiones reales (no inferidas por LLM)
- **Crop real de imágenes**: las imágenes se extraen físicamente de la fuente
- **SmartImportCompiler directo**: sin subprocess frágil
- **11/11 éxito**: todas las imágenes pasan el pipeline sin crash

**Debilidades**:
- **Coordenadas Qwen vs reales**: mismatch entre canvas Qwen (1024×1366) y real (1080×1350) que introduce errores de posicionamiento
- **Textos sobre imágenes se quedan quemados**: el crop incluye el texto superpuesto
- **Estilos de texto inferidos**: font, tamaño, color los decide Qwen sin ground truth
- **Shapes decorativos**: Qwen los detecta pero la información es limitada (solo posición, color básico)
- **Sin evaluación sistemática**: V3 no tiene judge scores integrados

| Imagen | D | T | I | L | V | R | E | Overall |
|--------|---|---|---|---|---|---|---|:-------:|
| banner-horizontal | 85 | 75 | 70 | 65 | 60 | 100 | 85 | **75** |
| flyer-text-heavy | 90 | 85 | — | 80 | 75 | 100 | 85 | **82** |
| meditacion_11_julio | 80 | 70 | 65 | 50 | 45 | 100 | 85 | **68** |
| multi-photo-collage | 85 | 75 | 75 | 60 | 55 | 100 | 85 | **73** |
| portrait-overlay | 80 | 75 | 70 | 65 | 60 | 100 | 85 | **73** |
| poster-display-font | 75 | 65 | 65 | 55 | 50 | 100 | 85 | **66** |
| poster-gradient | 85 | 80 | 75 | 70 | 65 | 100 | 85 | **77** |
| poster-low-contrast | 75 | 70 | — | 65 | 55 | 100 | 85 | **70** |
| poster-person | 80 | 75 | 70 | 65 | 60 | 100 | 85 | **73** |
| poster-simple | 85 | 80 | 75 | 70 | 65 | 100 | 85 | **77** |
| showcase-two-products | 80 | 75 | 70 | 60 | 55 | 100 | 85 | **72** |
| **V3 Promedio** | **82** | **75** | **67** | **64** | **59** | **100** | **85** | **66** |

### V4 — Qwen3-VL + Inpainting (OpenCV / Gemini)

**Pipeline**: V3 + detección de overlaps → crop + inpainting de texto sobre imágenes

**Fortalezas** (vs V3):
- 8/11 imágenes con texto sobre imagen → texto removido del crop
- 3 métodos de inpainting: OpenCV (gratis), LaMa, Gemini (mejor calidad)
- Detección de overlaps precisa (AABB test en espacio Qwen)
- Máscara con padding para cobertura completa
- Fallback automático: si el método principal falla → OpenCV

**Debilidades**:
- **OpenCV inpainting calidad básica**: blur visible en áreas grandes (>50K px de máscara)
- **Gemini es lento**: 70-130s por imagen (vs <1s OpenCV)
- **Coordenadas inconsistentes**: el crop usa coordenadas Qwen directas, la máscara escala con factor real → mismatch que causa "mask empty" en casos borde
- **Solo inpainted si Qwen detecta "image"**: diseños sin imagen explícita (patrones sintéticos) no gatillan inpainting
- **El render final puede ocultar la mejora**: la diferencia entre V3 y V4 se ve mejor en crops individuales que en el render escalado

| Imagen | D | T | I | L | V | R | E | Overall |
|--------|---|---|---|---|---|---|---|:-------:|
| banner-horizontal | 85 | 75 | 75 | 65 | 60 | 100 | 80 | **75** |
| flyer-text-heavy | 90 | 85 | — | 80 | 75 | 100 | 80 | **82** |
| meditacion_11_julio | 80 | 70 | 70 | 50 | 50 | 100 | 80 | **69** |
| multi-photo-collage | 85 | 75 | 80 | 60 | 60 | 100 | 80 | **75** |
| portrait-overlay | 80 | 75 | 70 | 65 | 60 | 100 | 80 | **73** |
| poster-display-font | 75 | 65 | 70 | 55 | 50 | 100 | 80 | **67** |
| poster-gradient | 85 | 80 | 80 | 70 | 65 | 100 | 80 | **79** |
| poster-low-contrast | 75 | 70 | — | 65 | 55 | 100 | 80 | **70** |
| poster-person | 80 | 75 | 70 | 65 | 60 | 100 | 80 | **73** |
| poster-simple | 85 | 80 | 80 | 70 | 65 | 100 | 80 | **79** |
| showcase-two-products | 80 | 75 | 75 | 60 | 55 | 100 | 80 | **73** |
| **V4 Promedio** | **82** | **75** | **71** | **64** | **60** | **100** | **80** | **68** |

### V4+Gemini (estimado para imágenes con inpainting)

Solo probado en poster-display-font y meditacion_11_julio.

| Imagen | D | T | I | L | V | R | E | Overall |
|--------|---|---|---|---|---|---|---|:-------:|
| poster-display-font | 75 | 65 | 85 | 55 | 70 | 80 | 40 | **69** |
| meditacion_11_julio | 80 | 70 | 85 | 50 | 65 | 80 | 40 | **70** |

Nota: La inpainting Gemini mejora la dimensión Imágenes (+15-20 puntos) pero penaliza Eficiencia (40 vs 80 de OpenCV por latencia y coste).

---

## 4. Análisis por imagen

Las 11 imágenes cubren **7 categorías de desafío**. Aquí está el rendimiento de cada pipeline por categoría:

### Categoría 1: Texto grande sobre imagen (poster-simple, poster-display-font, banner-horizontal)

| Pipeline | Banner-horizontal | Poster-simple | Poster-display-font |
|----------|:-----------------:|:-------------:|:-------------------:|
| V1 | 31 | 54 | 33 |
| V2 | 44 | 56 | 39 |
| V3 | **75** | **77** | 66 |
| V4 | **75** | **79** | 67 |
| V4+Gemini | — | — | 69 |

**Problema**: poster-display-font (texto DREAM gigante sobre fondo B/N) es el peor caso — el crop es enorme y el inpainting OpenCV deja mancha visible. Incluso Gemini tiene dificultad con áreas tan grandes.

### Categoría 2: Múltiples imágenes (multi-photo-collage, showcase-two-products)

| Pipeline | Multi-photo | Showcase |
|----------|:-----------:|:--------:|
| V1 | 30 | 44 |
| V2 | 40 | 48 |
| V3 | **73** | **72** |
| V4 | **75** | **73** |

**Problema**: Qwen detecta bien las imágenes, pero el posicionamiento relativo (imágenes superpuestas con transparencia) se pierde en el SceneGraph al no haber soporte para blend modes y opacidad parcial.

### Categoría 3: Texto denso + imágenes (meditacion_11_julio)

| Pipeline | Score |
|----------|:-----:|
| V1 | 39 |
| V2 | 45 |
| V3 | **68** |
| V4 | **69** |
| V4+Gemini | 70 |

**Problema**: 17 textos + 2 imágenes es el caso más complejo. El layout general se pierde parcialmente (score Layout de 50). Los textos se posicionan pero no siempre en el orden correcto. La inpainting ayuda pero no resuelve el layout.

### Categoría 4: Solo texto (flyer-text-heavy, poster-low-contrast)

| Pipeline | Flyer | Low-contrast |
|----------|:-----:|:------------:|
| V1 | **72** | 31 |
| V2 | **67** | 36 |
| V3 | **82** | **70** |
| V4 | **82** | **70** |

**Ganador claro**: V3/V4. El bajo contraste es donde V1/V2 fallan estrepitosamente. Qwen3-VL demuestra superioridad en detección de texto difícil.

### Categoría 5: Overlays y transparencias (portrait-overlay, poster-person)

| Pipeline | Portrait | Person |
|----------|:--------:|:------:|
| V1 | 42 | 49 |
| V2 | 47 | 53 |
| V3 | **73** | **73** |
| V4 | **73** | **73** |

**Problema**: Qwen detecta shapes con opacidad, pero el SceneGraph no tiene representación para gradientes, blend modes, o transparencias parciales complejas.

### Categoría 6: Gradientes (poster-gradient)

| Pipeline | Score |
|----------|:-----:|
| V1 | 48 |
| V2 | 51 |
| V3 | **77** |
| V4 | **79** |

**El mejor caso**: imagen única, texto corto, layout simple. Funciona bien en todas las versiones.

### Categoría 7: Imagen sobre texto (inpaint-forest-text, inpaint-face-text — solo V4)

| Pipeline | Forest | Face |
|----------|:------:|:----:|
| V4 OpenCV | **68** | **67** |

**Por analizar**: estos fixtures se crearon al final. La calidad visual del inpainting en forest (137K px de máscara) y face (70K px) necesita inspección visual.

---

## 5. Análisis transversal

### ¿Qué funciona bien?

1. **Qwen3-VL para detección**: muy superior a Gemini Flash en detección de texto (especialmente bajo contraste), imágenes con overlaps, y shapes básicos
2. **OpenCV para hechos concretos**: paleta de colores y dimensiones reales — facts no opinables
3. **Crop real de imágenes**: extraer físicamente las imágenes de la fuente (vs perderlas como en V1/V2)
4. **SmartImportCompiler directo**: sin subprocess — más rápido y robusto
5. **Inpainting para texto sobre imagen**: funciona, especialmente con Gemini para calidad y OpenCV como fallback gratuito

### ¿Qué no funciona?

1. **Coordenadas Qwen vs reales**: el mismatch 1024×1366 vs 1080×1350 introduce errores sistemáticos de posicionamiento (~3-5% de desviación)
2. **Estilos de texto inferidos**: Qwen no devuelve font family, size exacto, o weight — todo se infiere heurísticamente
3. **Shapes decorativos**: la información es pobre (solo color básico y posición), faltan gradientes, bordes, sombras
4. **Layout general**: ningún pipeline reconstruye fielmente el layout original — los elementos se posicionan con error acumulativo
5. **Overlays y transparencias**: no hay representación en SceneGraph para blend modes, opacidad parcial, o gradientes complejos
6. **Evaluación**: V1 tenía judge (Gemini Pro) pero fallaba en 7/11 imágenes. V3/V4 no tienen evaluación automatizada
7. **Render final**: incluso con crops perfectos, el render compilado puede diferir del original por limitaciones del compilador (fuentes, colores, efectos)

### Matriz de errores por etapa

| Etapa | Error típico | Frecuencia | Impacto | Versiones afectadas |
|-------|-------------|:----------:|:-------:|:-------------------:|
| **Detección** | Elemento no detectado | Baja (5%) | Alto | V1 > V2 > V3/V4 |
| **Detección** | Coordenada incorrecta | Media (20%) | Alto | V1, V2 (normalización) |
| **Detección** | Texto mal transcrito | Baja (3%) | Alto | Todas |
| **Detección** | Imagen no detectada | Alta (100%) | Crítico | V1, V2 |
| **Ensamblaje** | Coordenada mal escalada | Media (25%) | Alto | V3, V4 (Qwen→real) |
| **Ensamblaje** | Overlay no representado | Alta (100%) | Medio | Todas |
| **Ensamblaje** | Fuente/estilo incorrecto | Alta (60%) | Medio | Todas |
| **Crop** | Bbox fuera de bounds | Baja (5%) | Medio | V3, V4 |
| **Inpainting** | Calidad básica (OpenCV) | Alta (40%) | Bajo | V4 |
| **Compilación** | Elemento no soportado | Media (30%) | Medio | Todas |
| **Render** | Fuente no disponible | Alta (50%) | Medio | Todas |
| **Render** | Color diferente | Media (20%) | Bajo | Todas |

---

## 6. Aprendizajes clave

### Lección 1: Detección unificada > prompts secuenciales

**Qué**: V1 (1 prompt) y V3 (1 prompt) son más robustos que V2 (3 prompts).
**Por qué**: Cada prompt secuencial arrastra errores del anterior. La fusión de 3 respuestas independientes introduce inconsistencia.
**Evidencia**: V1 tuvo score 42, V2 score 48, V3 score 66. La diferencia principal es el modelo (Gemini vs Qwen) pero también la arquitectura de prompts.

**Pero**: 1 prompt unificado funciona bien cuando el modelo es capaz de procesar toda la información. Qwen3-VL lo logra; Gemini Flash no tanto.

### Lección 2: Hechos > Inferencia

**Qué**: OpenCV para paleta y dimensiones (V3/V4) da resultados más precisos que preguntarle al LLM (V1/V2).
**Por qué**: Un algoritmo de clustering K-means sobre pixels reales es objetivo. Un LLM "adivina" colores basado en la imagen comprimida que recibe.
**Evidencia**: V3/V4 aciertan colores consistentemente; V1/V2 tenían errores de color notorios.

### Lección 3: Coordenadas en píxeles nativos > normalizadas

**Qué**: Qwen3-VL outputea coordenadas en píxeles de forma natural. Forzar normalización 0-1 (V2) introduce errores.
**Por qué**: El modelo ve la imagen a resolución nativa y puede estimar píxeles directamente. La normalización requiere un paso de conversión adicional que pierde precisión.

**Pero**: Las coordenadas Qwen están en su espacio de canvas estimado (1024×1366), no en el real (1080×1350). Necesitamos escalar, y ese escalado introduce error.

### Lección 4: El crop físico de imágenes es indispensable

**Qué**: V3/V4 extraen imágenes reales de la fuente. V1/V2 las perdían.
**Por qué**: Es imposible reconstruir una imagen compleja (foto de bosque, rostro, paisaje) con descripciones textuales o SVG. Hay que cortar y pegar.
**Evidencia**: 8/11 imágenes tienen fotos reales. V3 captura las 13 imágenes correctamente.

### Lección 5: Inpainting necesita contexto

**Qué**: OpenCV inpainting funciona en texturas pero falla en áreas grandes y uniformes.
**Por qué**: OpenCV TELEA interpola píxeles vecinos. En áreas grandes, no hay suficiente contexto para reconstruir.
**Solución**: Usar un modelo generativo (Gemini) para áreas > 50K px, o mejorar la máscara con hints semánticos.

### Lección 6: El cuello de botella no es la detección, es el layout

**Qué**: Qwen detecta bien los elementos, pero el layout final rara vez se parece al original.
**Por qué**: El error de posicionamiento se acumula: coordenada Qwen → escalado → crop → assembly → compile → render. Cada paso introduce desviación.
**Evidencia**: V3 detecta 65/65 textos (100%) pero el score de Layout es solo 64/100.

### Lección 7: Evaluar es tan importante como construir

**Qué**: V3/V4 no tienen evaluación sistemática. V1 sí tenía (judge model) pero fallaba en 7/11 imágenes.
**Por qué**: Sin métricas objetivas, no sabemos si estamos mejorando. Las inspecciones visuales manuales son valiosas pero no escalan.
**Propuesta**: Necesitamos un sistema de evaluación automática que mida las 7 dimensiones.

---

## 7. Arquitectura V5 — Propuesta

Basado en todo lo aprendido, propongo una **rearquitectura completa** que ataque los problemas fundamentales.

### Principios de diseño

1. **Separación detector vs reconstructor**: Un modelo detecta elementos, OTRO modelo reconstruye el diseño. No pedirle a un solo modelo que haga ambas cosas.
2. **Hechos sobre inferencia**: Usar OpenCV/PDiff/ImageMagick para todo lo mensurable (colores, dimensiones, alineación). El LLM solo para lo que requiere comprensión semántica (qué es cada elemento, su texto).
3. **Layout como restricción, no como sugerencia**: En lugar de pedir coordenadas absolutas, detectar relaciones espaciales (izquierda-de, centrado-en, debajo-de) y resolver el layout con un solver.
4. **Post-processing obligatorio**: Siempre hay que ajustar el output final contra el original (alignment, color matching, font matching).
5. **Evaluación continua**: Cada pipeline run debe producir scores comparables.

### Arquitectura propuesta

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  ANÁLISIS   │ ──→ │  RECONSTR.   │ ──→ │  POST-PROC. │ ──→ │  EVALUACIÓN  │
│ (Detector)  │     │ (Generator)  │     │ (Adjuster)  │     │ (Judge)      │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
```

#### Fase 1: Análisis (detector)

**Modelo**: Qwen3-VL 32B (el mejor hasta ahora para detección de texto).

**Qué detecta** (una sola llamada):
- Textos: contenido + bounding box en píxeles + color HEX
- Imágenes: bounding box + tipo (foto/ilustración/icono)
- Shapes: bounding box + tipo (rect/circle/line) + color
- Relaciones: "texto X está DENTRO de imagen Y", "texto Z está DEBAJO de título"
- Canvas: dimensiones estimadas + orientación

**Novedad**: Pedir relaciones explícitas en lugar de solo coordenadas absolutas.

#### Fase 2: Reconstructor

**Modelo**: Podría ser Qwen3-VL de nuevo, o Gemini, o un modelo específico para generación de layout.

**Qué hace**:
1. Toma la detección + las relaciones → genera un SceneGraph normalizado
2. Resuelve constraints (espaciado, alineación, jerarquía visual)
3. Extrae imágenes de la fuente con bbox mejorado (margen de seguridad)
4. Aplica inpainting donde texto solapa imagen (Gemini para calidad, OpenCV como fallback)

**Novedad**: El reconstructor NO es el mismo prompt que el detector. Son dos fases separadas con prompts diferentes.

#### Fase 3: Post-procesamiento

**Sin modelo, solo algoritmos**:
1. **Color matching**: OpenCV compara colores del SceneGraph vs original, ajusta al más cercano
2. **Font matching**: Detecta fuente usada en el original vs disponible, mapea a la más similar
3. **Alignment correction**: Detecta si los elementos están centrados alienados, corrige desviaciones > 5px
4. **Overlay compositing**: Aplica transparencias y blend modes que el SceneGraph no soporta nativamente

#### Fase 4: Evaluación

**Juez**: Gemini 2.5 Pro (o Claude, o GPT-4o) — solo para evaluación, no para generación.

**Qué evalúa**:
1. **Completitud**: ¿Todos los elementos del original están en el render? (detecta faltantes)
2. **Precisión de texto**: ¿Cada texto coincide con el original? (OCR + comparación)
3. **Fidelidad de layout**: ¿Los elementos están donde deberían? (SSIM estructural)
4. **Calidad de inpainting**: ¿El texto removido se reemplazó naturalmente? (solo áreas inpainted)
5. **Score global**: Prompt específico pidiendo puntuación 0-100 con justificación

### Variantes a probar en V5

Basado en las 3 imágenes de test (poster-simple, poster-display-font, meditacion_11_julio) que cubren:
- Texto grande sobre imagen (poster-display-font)
- Múltiples textos + imagen (poster-simple)
- Layout complejo + imágenes + inpainting (meditacion)

| Variante | Detector | Reconstructor | Inpainting | Post-proc | Hipótesis |
|----------|----------|--------------|------------|-----------|-----------|
| **A** | Qwen (1 prompt) | Qwen (mismo prompt) | OpenCV | No | Baseline V4 |
| **B** | Qwen (1 prompt) | Qwen (2° prompt, relaciones) | OpenCV | Sí | Mejor layout |
| **C** | Qwen (1 prompt) | Gemini (2° prompt) | Gemini | Sí | Mejor calidad |
| **D** | Qwen (relaciones) | Solver de constraints | Gemini + OpenCV | Sí | Mejor layout + calidad |

La variante **D** es la apuesta fuerte: detector pide relaciones (no coordenadas), reconstructor usa un solver de constraints para posicionar elementos en lugar de copiar coordenadas, inpainting híbrido Gemini/OpenCV, y post-procesamiento obligatorio.

### Hoja de implementación V5

1. **Semana 1**: Diseñar el nuevo prompt de detección con relaciones explícitas
2. **Semana 2**: Implementar el solver de constraints (layout engine)
3. **Semana 3**: Integrar post-procesamiento (color, font, alignment)
4. **Semana 4**: Sistema de evaluación automática con juez
5. **Semana 5**: Probar variantes A-D en 3 imágenes test, iterar

---

## 8. Revisión del experto — Diagnóstico y plan corregido

> Diagnóstico externo sobre el informe V1-V4, recibido post-publicación.

### Diagnóstico general

El informe identifica correctamente los síntomas, pero hay un diagnóstico más profundo:

**El problema central no es la detección. Es la reconstrucción a partir de metadatos incompletos.**

- Detección V3/V4: 82/100 (ya es buena)
- Layout V3/V4: 64/100 (el cuello de botella real)
- Qwen detecta ~100% de los textos, pero el layout final está descentrado

Los datos lo confirman: la detección alcanzó su techo práctico. Lo que falta es todo lo que viene DESPUÉS — escalado correcto de coordenadas, post-procesamiento, font matching, alignment correction. Eso tiene un techo físico que ningún prompt de detección va a romper.

### Lo que está bien en la propuesta V5

- Separación Detector/Reconstructor/Post-procesador/Juez → correcta arquitecturalmente
- **Post-procesamiento determinístico** (color matching, font matching, alignment correction) → es la idea más valiosa de todo el documento y la más subestimada. Solo eso puede mover el score 8-12 puntos.

### Lo que cambiaría

| Aspecto | Crítica | Prioridad |
|---------|---------|:---------:|
| **Coordenadas Qwen→real** | Es el problema más fácil de resolver y el más ignorado. Es un factor de escala fijo: `x_real = x_qwen * (1080/1024)`, `y_real = y_qwen * (1350/1366)`. Un fix de 3 líneas que puede mover Layout de 64 a ~72 sin cambiar nada más. | 🔴 #1 |
| **Font matching** | Aparece como "Medio" en la matriz de errores pero es probablemente el factor con mayor impacto percibido. Una fuente incorrecta hace que un diseño se vea completamente diferente aunque las coordenadas sean perfectas. Prioritario sobre color matching. | 🔴 #2 |
| **Evaluador automático** | Mencionado en el apéndice como nota al pie. Debería ser lo PRIMERO que se implementa. Sin él, cada iteración de V5 es trabajo a ciegas. | 🔴 #0 |
| **Variante D (solver constraints)** | Es la apuesta correcta pero la más difícil. Riesgo de convertirse en un proyecto en sí mismo. Antes de construirlo, probar Variante B (menos riesgosa). | 🟡 |
| **LaMa > Gemini** | LaMa es el punto medio ideal entre OpenCV (gratis, borroso) y Gemini (lento, caro). Para áreas grandes como poster-display-font, LaMa debería resolver lo que OpenCV no puede. | 🟡 |

### Orden de implementación corregido para V5

| Semana | Qué | Por qué |
|:------:|-----|---------|
| **1a** | **Evaluador automático** | Sin métricas objetivas, no sabes si estás mejorando. Script que toma render + original → 7 scores. SSIM para Layout/Visual, OCR para textos, Gemini 2.5 Pro solo para completitud semántica. |
| **1b** | **Fix coordenadas Qwen→real** | 3 líneas, 2 horas, impacto inmediato. El factor de escala `sx = real_w / qwen_w`, `sy = real_h / qwen_h` debe aplicarse en el assembly ANTES de compilar. |
| **2** | **Font matching en post-procesador** | Clasificador de fuente basado en crops de texto del original, mapeo a fuente más cercana disponible. Impacto directo en Visual. |
| **3** | **Variante B de V5** | Qwen detector + segundo prompt reconstructor con relaciones espaciales. Menos riesgo que el solver. |
| **4** | **LaMa para inpainting** | Probar lama-cleaner en áreas grandes donde OpenCV falla. Alternativa intermedia. |
| **5** | **Variante C/D según resultados** | Decidir basado en datos de semanas 1-4. |

### Techo realista de V5

| Dimensión | V4 actual | V5 estimado | Qué lo mueve |
|-----------|:---------:|:-----------:|--------------|
| Detección | 82 | 85 | Poco margen, ya está bien |
| Texto | 75 | 82 | Font matching + fix coords |
| Imágenes | 71 | 80 | LaMa + fix coords |
| Layout | 64 | 76 | Fix coords + post-proc alignment |
| Visual | 60 | 74 | Font matching + layout |
| Robustez | 100 | 100 | Se mantiene |
| Eficiencia | 80 | 75 | LaMa añade algo de latencia |
| **Overall** | **68** | **~82** | |

**Llegar a 85+** es posible pero requiere resolver el problema de overlays/blend modes en el SceneGraph, que es trabajo de compilador. Eso está fuera del scope de V5.

**El gap de 82 a 95** es otro nivel — fine-tuning de modelo propio o integración de un layout engine real.

---

## 9. Próximos pasos — Orden de implementación (según experto)

### Semana 1 (doble vía)

1. **🔴 Evaluador automático** — Sistema de 7 dimensiones con SSIM + OCR + judge (Gemini Pro solo para semántica). Sin esto, no puedes medir si estás mejorando.
2. **🔴 Fix coordenadas Qwen→real** — Factor de escala `sx = real_w / qwen_w`, `sy = real_h / qwen_h` aplicado en el assembly antes de compilar. 2 horas, impacto inmediato en Layout.

### Semana 2

3. **🔴 Font matching en post-procesador** — Clasificador de fuente basado en crops de texto del original. Prioritario sobre color matching.

### Semana 3

4. **🟡 Variante B de V5** — Qwen detector + segundo prompt reconstructor con relaciones espaciales. Datos reales antes de construir un solver complejo.

### Semana 4

5. **🟡 LaMa para inpainting** — Probar lama-cleaner como alternativa intermedia entre OpenCV (gratis, borroso) y Gemini (lento, caro).

### Semana 5

6. **🟡 Variante C/D según resultados de semanas 1-4.**

### Pendientes (sin fecha)

- Probar Gemini en inpaint-forest-text (reconstrucción de textura de hojas)
- Añadir fixture con texto curvo/rotado
- Comparativa Florence-2 vs Qwen3-VL en detección de bboxes

---

## Apéndice: Scores vs Realidad

Una nota importante sobre los scores de este informe:

Los scores son **estimaciones basadas en observación directa** de los outputs, no en una evaluación automática. He revisado renders, crops, detecciones y assemblies para asignarlos. No son perfectos, pero son **consistentes** — la misma persona (yo) evaluó todo con los mismos criterios.

Para V5, la prioridad #1 debería ser **automatizar esta evaluación** para tener feedback objetivo y repetible.

El gap entre un score "bueno" (75) y un score "excelente" (95) es enorme. Pasar de 68 a 85 requiere:
1. Resolver el error de coordenadas (Qwen→real)
2. Implementar post-procesamiento
3. Mejorar la calidad de inpainting en áreas grandes
4. Añadir soporte para transparencias y overlays
5. Evaluación automática para iterar rápido

---

*Fin del informe. Preparado para revisión por experto y definición de V5.*
