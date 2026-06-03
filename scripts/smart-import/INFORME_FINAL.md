# Híbrido OCR — Informe Final de Investigación

> **Proyecto**: tseyor-canva  
> **Área**: `scripts/smart-import/`  
> **Fecha**: 3 Junio 2026  
> **Autor**: Gentle AI — SDD Orchestrator  
> **Versiones exploradas**: v2 → v24 (24 iteraciones, 7 enfoques)

---

## 1. El Problema

Extraer elementos de texto (texto + bounding box) desde una imagen exportada de Canva. 
Cada elemento debe coincidir 1:1 con los elementos del canvas original: mismo texto exacto y misma posición.

### Dataset de prueba

Tres muestras de Canva, exportadas a 992×1240px (escala 0.9185 respecto al canvas 1080×1350):

| Muestra | Elementos | Textos únicos | Fondo |
|---------|:---------:|:-------------:|-------|
| `01-white.png` | 30 | 22 | Blanco |
| `02-gradient.jpg` | 33 | 20 | Degradado colorido |
| `03-forest.jpg` | 33 | 21 | Imagen de bosque |

Ground truth extraído del archivo `.tc` (exportación de Canva con metadatos).

---

## 2. Enfoques Probados

### 2.1 v2 — Gemini full-image + OCR hints ✅ VIABLE

**Score**: 0.838 raw / ~0.91 con norm fix (01-white), 1.00 (02-gradient)  
**API calls**: 1 Gemini por imagen  
**Pipeline**: PaddleOCR detecta fragmentos → Gemini lee imagen completa con hints de OCR → output JSON con elementos

```
PaddleOCR (59 fragments) ──→ Gemini 2.5 Flash ──→ 23 elementos con texto + bbox
         ↑                           ↑
   posiciones + texto          imagen completa (992x1240)
```

**Ventajas**:
- Gemini ve el diseño completo = agrupa fragmentos por contexto visual
- Lee texto directamente de la imagen (corrige errores de OCR)
- Score más alto de todos los enfoques

**Desventajas**:
- No-determinista: a veces output fragment-level (59 elementos), a veces element-level (~20)
- ~2-3 elementos perdidos consistentemente ("grid systems work", "sit")

**FIX CLAVE**: `norm()` debe colapsar todo whitespace incluyendo saltos de línea:
```python
def norm(t): return re.sub(r'\s+', ' ', t.strip().lower())
```
Sin esto, los textos largos con `\n` no matchean contra el GT plano.

---

### 2.2 v14-v19 — Crop-read de fragmentos ❌ INVIABLE

**Score**: 0.676-0.827  
**Pipeline**: PaddleOCR fragments → Gemini crop-read de cada fragmento

**Problema**: Los crops de fragmentos individuales son ~30×15px. Gemini no tiene contexto suficiente y alucina texto. Una línea de "DISPLAYED. THE ARRANGEMENT" fue leída como "DATA DISPLAYED. THE".

---

### 2.3 v15, v20 — Merge determinista por overlap ❌ INVIABLE

**Score**: 0.701-0.742  
**Pipeline**: PaddleOCR fragments → merge por x-overlap + y-proximidad

**Problema**: PaddleOCR tiene ±15px de jitter en posiciones. Fragmentos del mismo elemento caen en columnas diferentes. El overlap de x-ranges entre elementos de columnas adyacentes hace imposible la agrupación correcta.

Fragmentos que deberían estar juntos:
```
"TYPOGRAPHYIS"  x=369, w=277 → x2=646
"TECHNIQUE"     x=386, w=261 → x2=647  ← overlap 260px
"TYPE TO MAKE"  x=417, w=231 → x2=648  ← overlap 230px
```
Fragmentos que NO deberían estar juntos pero tienen overlap:
```
"Color" x=17, w=107 → x2=124
"Typography matters" x=17, w=186 → x2=203  ← mismo x, pero gap vertical de 152px
```

---

### 2.4 v21 — Proyección de columnas ❌ INVIABLE

**Score**: 0.516 (01-white), 0.000 (02-gradient)  
**Pipeline**: Proyección vertical (max sobre y) → columnas → proyección horizontal → elementos → Gemini crop-read

**Problema**:
- No funciona con fondos no-blancos (02-gradient, 03-forest)
- Elementos que spannean columnas llenan los gaps de proyección
- Columnas adyacentes tienen gap de solo 3px (indistinguible del ruido)
- Elementos en diferentes columnas al mismo Y se fusionan

---

### 2.5 v23 — Surya OCR ❌ INVIABLE

**Score**: 0.652 (01-white), 0.754 (02-gradient)  
**Pipeline**: Surya detection (59 líneas) → K-means clustering → Gemini crop-read

**Ventajas**: 
- Posiciones más precisas que PaddleOCR
- Detectó "grid systems work" que PaddleOCR perdió

**Problema**:
- Mismo over-merging que PaddleOCR: líneas de columnas adyacentes al mismo Y se fusionan en una sola línea ancha
- Surya línea [42] spannea x=14-443 (left + middle columns) porque detectó "Grid systems work" y "Hello" como una línea
- K-means no puede separar columnas cuando hay líneas que spannean

---

### 2.6 v22 — Gemini two-step (bbox → crop) ❌ INVIABLE

**Score**: 0.283 (01-white)  
**Pipeline**: Gemini detecta bboxes (sin texto) → Gemini crop-read cada bbox

**Problema**: Pedir SOLO bboxes es más difícil que pedir bboxes+texto. Gemini alucinó bboxes de imágenes completamente diferentes ("RTL-SDR dongle", "SAMSUNG", etc.).

---

### 2.7 v24 — Prompt chain (contar → listar) ❌ INVIABLE

**Score**: 0.473 (01-white)  
**Pipeline**: Gemini cuenta elementos → Gemini lista exactamente N elementos

**Problema**: El texto truncado de OCR hints (15 chars) envenenó a Gemini. Copió los hints en vez de leer la imagen. La "cuenta" dio 26 (regular) pero el listado fue fragment-level con texto truncado.

---

## 3. Resultados Comparativos

| Enfoque | Iteración | 01-white | 02-gradient | 03-forest | Llamadas API | Determinista |
|---------|:---------:|:--------:|:-----------:|:---------:|:------------:|:------------:|
| **v2 + norm fix** | **v2** | **~0.91** | **~1.00** | **~0.85*** | **1 Gemini** | **No** |
| v2 raw | v2 | 0.838 | 0.953 | 0.728 | 1 Gemini | No |
| v4 crop trick | v4 | — | 0.968 | — | 2 Gemini | No |
| Surya + Gemini | v23 | 0.652 | 0.754 | — | 1 Surya + N Gemini | Sí† |
| Merge determinista | v15/v20 | 0.742 | 0.667 | — | 0 | Sí |
| Proyección | v21 | 0.516 | 0.000 | — | N Gemini | Sí† |
| Crop-read fragments | v14/v19 | 0.827 | 0.692 | — | 59 Gemini | Sí† |
| Prompt chain | v24 | 0.473 | 0.713 | 0.395 | 2 Gemini | No |
| Two-step bbox | v22 | 0.283 | — | — | 1+N Gemini | No |

*\*Estimado, no ejecutado con norm fix*  
*†Surya y proyección son deterministas, pero Gemini crop-read no*

---

## 4. Lecciones Aprendidas

### 4.1 Por qué es difícil

1. **Layout Analysis + OCR es un problema de investigación activa**. No hay modelo pre-entrenado que haga ambos bien para diseños tipo Canva.
2. **La posición es más difícil que el texto**. Leer texto es trivial (Gemini, PaddleOCR, Surya todos lo hacen bien). Decir dónde empieza y termina cada elemento es el problema real.
3. **Los bordes entre elementos son borrosos**. Dos elementos en columnas diferentes al mismo Y se ven como una línea continua. Sin acceso a la estructura interna del diseño, no hay forma de separarlos.
4. **Los modelos de layout (Surya, LayoutLM) están entrenados en documentos** (papers, facturas, formularios) donde las columnas tienen espacios grandes. Canva permite layouts mucho más densos.

### 4.2 Por qué Gemini gana

Gemini full-image gana porque es el **único enfoque que ve el diseño completo**. Cuando tiene los hints de PaddleOCR + la imagen completa, puede:
- Ver relaciones espaciales entre fragmentos
- Distinguir entre "gap entre párrafos" y "gap entre líneas"
- Leer texto directamente (no depende del OCR)
- Corregir errores de OCR ("Cotor" → "Color")

Ningún otro enfoque (proyección, overlap, Surya, two-step) tiene esta visión holística.

### 4.3 El talón de Aquiles: no-determinismo

Gemini 2.5 Flash a veces output fragment-level (59 elementos) y a veces element-level (~20). Esto no es culpa del prompt — es inherente al modelo. Las soluciones prácticas:

- **Temperature=0** si la API lo soporta (reduce pero no elimina la variabilidad)
- **Consensus 3x** (correr 3 veces, tomar mayoría)
- **Heurística post-hoc**: si output > 40 elementos, asumir fragment-level y mergear

---

## 5. Recomendación Final

### Para producción ahora: v2 + norm fix

```python
# Pipeline final recomendado
1. PaddleOCR → fragmentos con posiciones y texto
2. Gemini full-image con fragment hints → elementos (texto + bbox)
3. norm() que colapsa \n y whitespace
```

**Score esperado**: ~0.91 (01-white), ~0.95-1.00 (02-gradient)  
**Costo**: 1 llamada Gemini + 1 PaddleOCR por imagen  
**Tiempo**: ~20-30s por imagen  
**Complejidad**: ~200 líneas de Python

### Para mejorar de 0.91 a 0.99

Las únicas opciones reales:
1. **API de Canva** (acceso directo a estructura del diseño)
2. **Fine-tuning** de un modelo de layout detection en diseños Canva
3. **Temperature=0 + consensus 3x** (reduce no-determinismo)

---

## 6. Archivos Generados

| Archivo | Descripción |
|---------|-------------|
| `scripts/smart-import/output/ocr-samples/` | Muestras de test (01-white, 02-gradient, 03-forest) |
| `scripts/smart-import/output/ocr-samples/samples/*.tc` | Ground truth (exportación Canva) |
| `scripts/smart-import/openrouter.py` | Cliente OpenRouter para Gemini |
| `scripts/smart-import/v9_paddleocr.py` | Detector PaddleOCR |
| `scripts/smart-import/hybrid_v2.py` | **Pipeline recomendado** |

---

*Fin del informe. 24 iteraciones, 7 enfoques, 1 solución viable.*
