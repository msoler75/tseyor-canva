# Smart Import Calibration Pipeline

Pipeline autónomo que procesa imágenes mediante visión IA → SceneGraph → compilador `.tc` → render headless → evaluación automática. Diseñado para **calibrar** el pipeline de importación inteligente antes de integrarlo en la app Tseyor Canva.

---

## 1. Installation

### Requisitos del sistema

- **Python 3.11+**
- **Node.js 22+** (para el renderizador headless)
- **PHP 8.1+** con Composer dependencies (para la app Laravel)
- **MySQL/MariaDB** (requerido por la app)
- **Playwright** con Chromium (para screenshots headless)

### Python dependencies

```bash
cd scripts/smart-import
pip install -r requirements.txt
```

Dependencias instaladas: `openai`, `pillow`, `jsonschema`, `requests`, `python-dotenv`.

### Node dependencies (headless renderer)

El script `tc_render.js` usa Playwright para lanzar Chromium headless:

```bash
# Desde la raíz del proyecto
npm install --save-dev playwright
npx playwright install chromium
```

> **Nota**: Asegúrate de que las dependencias de Composer de la app Laravel estén instaladas
> (`composer install` en la raíz del proyecto) y que MySQL/MariaDB esté corriendo.

### Build de la app

El renderer necesita el build de Vite. Si no existe, intenta reconstruirlo automáticamente;
también puedes hacerlo manualmente:

```bash
npm run build
```

### Environment

```bash
cp scripts/smart-import/.env.example scripts/smart-import/.env
```

Edita `.env` y configura al menos `OPENROUTER_API_KEY`.

---

## 2. Configuration

| Variable | Requerida | Default | Descripción |
|----------|-----------|---------|-------------|
| `OPENROUTER_API_KEY` | **Sí** | — | API key de OpenRouter ([openrouter.ai/keys](https://openrouter.ai/keys)) |
| `OPENROUTER_BASE_URL` | No | `https://openrouter.ai/api/v1` | Base URL del API de OpenRouter |
| `DEFAULT_VISION_MODEL` | No | `google/gemini-2.5-flash` | Modelo visión para análisis imagen → SceneGraph |
| `DEFAULT_COMPILER_MODEL` | No | `google/gemini-2.5-flash-lite` | Modelo compilador (reserva, no usado en modo determinista) |
| `JUDGE_MODEL` | No | `google/gemini-2.5-pro` | Modelo juez para evaluación de calidad |

Variables de entorno adicionales para el renderer (`tc_render.js`):

| Variable | Default | Descripción |
|----------|---------|-------------|
| `TC_RENDER_PORT` | `8080` | Puerto del servidor PHP dev |
| `TC_RENDER_HOST` | `localhost` | Host del servidor PHP dev |
| `TC_RENDER_TIMEOUT` | `30` | Timeout máximo en segundos para el render |

---

## 3. Usage

### Full pipeline (todas las imágenes, modelo por defecto)

```bash
python scripts/smart-import/pipeline.py
```

### Modelo específico

```bash
python scripts/smart-import/pipeline.py --model google/gemini-2.5-pro
```

### Modos V1

```bash
# MVP barato y robusto: fondo original + textos editables
python scripts/smart-import/pipeline.py --mode text_only

# Default: textos + fotos/formas rectangulares con confidence >= 0.5
python scripts/smart-import/pipeline.py --mode basic_image_layers
```

`text_only` es el modo más seguro para calibrar OCR/layout. `basic_image_layers`
añade recortes rectangulares de imagen y formas cuando el SceneGraph tiene
confianza suficiente. V1 no hace inpainting ni restauración avanzada.

### Skip render (solo análisis + compilación)

```bash
python scripts/smart-import/pipeline.py --skip-render
```

### Reutilizar SceneGraph cacheados (solo re-compilar)

```bash
python scripts/smart-import/pipeline.py --skip-analysis
```

### Imagen individual

```bash
python scripts/smart-import/pipeline.py --image img-03
```

El flag `--image` recibe el *stem* del filename (sin extensión). Por ejemplo para
`flyer-text-heavy.jpg` usarías `--image flyer-text-heavy`.

### Modo verbose

```bash
python scripts/smart-import/pipeline.py --verbose
```

### Combinaciones típicas

```bash
# Evaluar un modelo nuevo sin re-analizar (reusa SceneGraphs)
python scripts/smart-import/pipeline.py --model anthropic/claude-sonnet-4.5 --skip-analysis

# Solo re-compilar y re-renderizar (sin re-analizar ni re-evaluar)
python scripts/smart-import/pipeline.py --skip-analysis --skip-eval

# Pipeline completo para una imagen con modelo específico
python scripts/smart-import/pipeline.py --image poster-simple --model google/gemini-2.5-pro

# Importación básica de texto editable sobre fondo, sin capas de imagen
python scripts/smart-import/pipeline.py --mode text_only --skip-render --skip-eval

# Usar wrapper bash para render directo
bash scripts/smart-import/tc_render.sh output/model/img-01/design.tc output/model/img-01/render.png
```

---

## 4. Pipeline Flags

| Flag | Default | Descripción |
|------|---------|-------------|
| `--dataset DIR` | `scripts/smart-import/dataset/` | Directorio con imágenes de entrada |
| `--model NAME` | `DEFAULT_VISION_MODEL` env \| `google/gemini-2.5-flash` | Modelo visión para análisis |
| `--compiler-model NAME` | `DEFAULT_COMPILER_MODEL` env \| `google/gemini-2.5-flash-lite` | Modelo para compilación (reserva) |
| `--judge-model NAME` | `JUDGE_MODEL` env \| `google/gemini-2.5-pro` | Modelo juez para evaluación |
| `--output DIR` | `scripts/smart-import/output/` | Directorio raíz de salida |
| `--mode text_only\|basic_image_layers` | `basic_image_layers` | Modo V1: solo texto editable o texto + capas rectangulares de alta confianza |
| `--skip-analysis` | `false` | Saltar análisis → reusar caché por hash o SceneGraph locales |
| `--skip-render` | `false` | Saltar renderizado (solo .tc) |
| `--skip-eval` | `false` | Saltar evaluación. Si existe score en caché por hash, lo reusa en el resultado |
| `--image ID` | `null` (todas) | Procesar solo una imagen por su ID (stem del filename) |
| `--verbose`, `-v` | `false` | Logging DEBUG (muestra reparaciones, warnings detallados) |

---

## 5. Output Structure

```
output/
├── .cache/                       ← Caché por hash SHA-256 + versión + modelo/modo
│   └── smart-import_.../
│       ├── cache-key.json        ← Clave lógica original de caché
│       ├── scene.json
│       ├── scene-fixed.json
│       ├── design.tc
│       └── score.json
├── {model-name}/
│   ├── {image-id}/
│   │   ├── scene.json            ← SceneGraph crudo devuelto por el modelo visión
│   │   ├── scene-fixed.json      ← SceneGraph después de validar, reparar y normalizar
│   │   ├── design.tc             ← Archivo .tc v2 compilado (importable en la app)
│   │   ├── render.png            ← Screenshot del render en el editor (si --skip-render es false)
│   │   ├── score.json            ← Score de evaluación del modelo juez (si --skip-eval es false)
│   │   └── openrouter.json       ← Log de usage de API (tokens, coste, latencia, timestamps)
│   └── model-report.md           ← Reporte markdown por modelo
│   └── model-report.json         ← Reporte JSON por modelo
├── report.json                   ← Reporte global multi-modelo (máquina)
└── report.md                     ← Reporte global multi-modelo (humano)
```

### Explicación de cada archivo

| Archivo | Contenido |
|---------|-----------|
| `scene.json` | Respuesta JSON cruda del modelo visión. Puede contener errores de schema. |
| `scene-fixed.json` | SceneGraph después de pasar por `validator.py`: reparado, colores normalizados, capas de baja confianza descartadas, bboxes clampados al canvas. **Este es el que usa el compilador.** |
| `design.tc` | Archivo `.tc` v2 generado por el compilador determinista. Contiene `tcVersion`, `designSurface`, `pages` con `content`, `elementLayout`, `customElements`. Assets de imagen inline como data URIs. |
| `render.png` | Captura de pantalla del `.tc` renderizado en el editor Tseyor Canva vía Playwright headless. |
| `score.json` | Score estructurado del modelo juez: `overallScore`, `visualSimilarity`, `textAccuracy`, `layoutAccuracy`, `colorAccuracy`, `editability`, `criticalIssues`, `recommendations`. |
| `openrouter.json` | Array de usage logs. Cada entrada: `model`, `promptTokens`, `completionTokens`, `totalTokens`, `costUsd`, `latencyMs`, `timestamp`, `status`, `errorMessage`. |
| `report.md` / `report.json` | Reporte agregado: tabla comparativa por imagen y modelo, promedios, ranking, costes totales, log de issues críticos. |
| `.cache/` | Artefactos reutilizables por hash de imagen. Evita repetir llamadas a OpenRouter cuando la misma imagen/modelo/modo ya fue procesada. En Windows se usa un nombre de carpeta seguro y `cache-key.json` conserva la clave lógica. |

---

## 6. Interpreting Results

### Score dimensions

Cada dimensión se evalúa en escala **0.0 – 1.0**:

| Dimensión | Qué mide |
|-----------|----------|
| `overallScore` | Promedio general de todas las dimensiones. **Métrica principal.** |
| `visualSimilarity` | Similitud visual global: colores, disposición, proporciones. |
| `textAccuracy` | Precisión de textos: ¿están todos los textos presentes y correctos? (OCR) |
| `layoutAccuracy` | Precisión de layout: posiciones, tamaños, espaciado vs original. |
| `colorAccuracy` | Precisión de colores: fondo, texto, formas. |
| `editability` | ¿Los textos son capas editables (no imagen plana)? |

Además incluye:
- `criticalIssues`: lista de problemas específicos que reducen la fidelidad
- `recommendations`: mejoras accionables para el pipeline

### Qué esperar de los scores

| Rango | Interpretación |
|-------|----------------|
| **0.90 – 1.00** | Excelente. El import captura fielmente el diseño original. |
| **0.75 – 0.89** | Bueno. Pequeñas diferencias en colores o espaciado, textos correctos. |
| **0.50 – 0.74** | Aceptable. Varios elementos desplazados, algún texto faltante o colores incorrectos. |
| **0.25 – 0.49** | Malo. Varios textos faltantes, layout significativamente diferente. |
| **0.00 – 0.24** | Muy malo. El import no captura el diseño (o el render falló). |

### Cómo usar el reporte

El reporte generado (`report.md`) te da una vista general:

```
| Image         | Visual | Text | Layout | Color | Edit. | Overall | Cost     | Time |
|---------------|--------|------|--------|-------|-------|---------|----------|------|
| poster-simple | 0.92   | 0.95 | 0.90   | 0.88  | 0.98  | 0.93    | $0.0021  | 3.2s |
| flyer-text... | 0.65   | 0.45 | 0.70   | 0.80  | 0.85  | 0.69    | $0.0045  | 5.1s |
```

Busca patrones:
- **Bajo `textAccuracy`** → el prompt de análisis necesita mejorarse para capturar más texto
- **Bajo `layoutAccuracy`** → los bboxes no se están calculando bien
- **Bajo `colorAccuracy`** → el modelo no está detectando colores correctamente
- **Bajo `editability`** → el compilador está fusionando capas de texto

---

## 7. Calibration Workflow

### Iterar: cambiar prompt → re-compilar → comparar scores

El flujo típico de calibración:

```bash
# 1. Ejecutar pipeline completo (primera vez)
python scripts/smart-import/pipeline.py --model google/gemini-2.5-flash

# 2. Revisar report.md → identificar debilidades (ej: textAccuracy bajo)

# 3. Modificar SYSTEM_PROMPT_A o ANALYSIS_PROMPT en pipeline.py

# 4. Re-ejecutar SOLO el análisis (no re-renderiza)
python scripts/smart-import/pipeline.py --model google/gemini-2.5-flash

# 5. Comparar scores nuevos con anteriores
```

### Re-compilar sin re-analizar (ahorra coste API)

```bash
# Después del primer análisis exitoso:
python scripts/smart-import/pipeline.py --model google/gemini-2.5-flash --skip-analysis
```

Esto consulta primero `output/.cache/` por hash SHA-256 de imagen + versión de
pipeline + modelo/modo. Si no hay caché por hash, cae al `scene.json` local del
directorio de la imagen. Así se puede reintentar o reimportar una imagen
idéntica sin pagar otra llamada de visión.

### Comparar modos V1

```bash
# Calibración OCR/layout primero: fondo + textos editables
python scripts/smart-import/pipeline.py --mode text_only

# Añadir fotos/formas rectangulares de alta confianza
python scripts/smart-import/pipeline.py --mode basic_image_layers
```

El benchmark debe comparar ambos modos. `text_only` suele dar más editabilidad
y menos ruido; `basic_image_layers` mejora fidelidad visual, pero puede añadir
recortes imperfectos si el SceneGraph detecta capas dudosas.

### Comparar modelos

```bash
# Modelo rápido
python scripts/smart-import/pipeline.py --model google/gemini-2.5-flash

# Modelo premium
python scripts/smart-import/pipeline.py --model anthropic/claude-sonnet-4.5

# Ver ranking en output/report.md
```

El reporte global incluye ranking de modelos por `overallScore/coste`.

### Identificar debilidades específicas

1. Revisa `criticalIssues` en cada `score.json` — te dice exactamente qué falló
2. Mira el `render.png` visualmente vs el original en `dataset/`
3. Compara `scene.json` (crudo) vs `scene-fixed.json` (reparado) para ver qué corrigió el validador
4. Busca patrones por tipo de imagen (carteles vs flyers vs banners)

---

## 8. Architecture Overview

### Módulos

| Módulo | Responsabilidad |
|--------|-----------------|
| **`pipeline.py`** | Orquestador principal. Itera imágenes, coordina fases, aplica modo V1, gestiona caché por hash y genera reporte. |
| **`openrouter.py`** | Cliente OpenRouter API. Chat completions con imágenes, retry con backoff, logging de usage y coste. |
| **`validator.py`** | Valida SceneGraph contra JSON Schema. Repara campos faltantes, normaliza colores, filtra capas según modo/confianza, clampa bboxes. |
| **`compiler.py`** | Compilador **determinista** (sin IA). SceneGraph validado → estructura `.tc` v2. Respeta `text_only`/`basic_image_layers` y recorta assets image como data URIs. |
| **`tc_render.js`** | Renderer headless con Playwright. Inyecta `.tc` en sessionStorage, navega al editor, hace screenshot del canvas. |
| **`evaluate.py`** | Evaluador juez multimodal. Compara original vs render, produce score estructurado con 6 dimensiones. |
| **`report.py`** | Genera reportes markdown + JSON. Tablas por modelo, promedios, ranking, costes, issues críticos. |
| **`scene_schema.json`** | JSON Schema draft-2020-12 del SceneGraph v1. |
| **`tests/`** | Tests unitarios Python + JS para cada módulo. |

### Diagrama de flujo

```
┌──────────────────────────────────────────────────────────────────┐
│                        pipeline.py                               │
│  Orquestador: itera imágenes → fases → reporte                   │
└────┬───────────────────────────────────────────────────────┬─────┘
     │ 1. Analizar imagen (--skip-analysis la salta)         │
     ▼                                                        │
┌──────────────────┐                                          │
│  openrouter.py   │  Visión IA → SceneGraph JSON            │
│  vision_analyze  │  + log de usage (tokens, coste)         │
└──────┬───────────┘                                          │
       │ 2. Validar SceneGraph                                │
       ▼                                                      │
┌──────────────────┐                                          │
│  validator.py    │  JSON Schema + reparar + normalizar      │
│  validate_scene  │  + descartar low-confidence              │
└──────┬───────────┘                                          │
       │ 3. Compilar a .tc (determinista)                     │
       ▼                                                      │
┌──────────────────┐                                          │
│  compiler.py     │  SceneGraph → .tc v2                     │
│  SmartImport     │  + crop assets → data URIs               │
│  Compiler        │  + z-index, content keys                 │
└──────┬───────────┘                                          │
       │ 4. Renderizar (--skip-render la salta)               │
       ▼                                                      │
┌──────────────────┐                                          │
│  tc_render.js    │  Playwright headless                     │
│  .tc → PNG       │  PHP dev server + editor screenshot      │
└──────┬───────────┘                                          │
       │ 5. Evaluar (--skip-eval la salta)                    │
       ▼                                                      │
┌──────────────────┐                                          │
│  evaluate.py     │  Modelo juez multimodal                  │
│  ImportJudge     │  original + render → score.json          │
└──────┬───────────┘                                          │
       │ 6. Reporte                                            │
       ▼                                                      │
┌──────────────────┐                                          │
│  report.py       │  Tablas markdown + JSON                  │
│  generate_report │  Promedios, ranking, costes              │
└──────────────────┘                                          │
```

### Decisiones de diseño clave

| Decisión | Opción | Razón |
|----------|--------|-------|
| Compilador determinista | Sin IA | Consistente, predecible, sin coste API. El SceneGraph ya tiene toda la info. |
| Assets en .tc | Data URIs | Autocontenido, no requiere red, funciona offline. |
| Render headless | Playwright + PHP dev server | Reusa el editor real de la app, máxima fidelidad. |
| Comunicación Python→JS | Subprocess | Simple, directo, un solo punto de integración. |
| Caché de artefactos | SHA-256 + pipelineVersion + modelId/modo | Evita llamadas repetidas a OpenRouter, permite reintentos baratos y funciona con imágenes duplicadas. |
| Modos V1 | `text_only` y `basic_image_layers` | Mantiene un MVP honesto: primero texto editable robusto; después capas rectangulares de alta confianza. |
| Validación SceneGraph | JSON Schema + reparación | El modelo a veces devuelve JSON inválido o incompleto. |

---

## 9. Troubleshooting

### OpenRouter API errors

| Error | Causa probable | Solución |
|-------|----------------|----------|
| `API key not provided` | `OPENROUTER_API_KEY` no está configurada | Verifica `.env` en `scripts/smart-import/.env` |
| `Rate limited (429)` | Demasiadas requests seguidas | El cliente ya hace retry automático con backoff. Espera o usa modelo más barato. |
| `Server error (5xx)` | Problema temporal de OpenRouter | Retry automático 3 veces. Si persiste, espera unos minutos. |
| `Model not found` | Nombre de modelo incorrecto | Verifica el nombre exacto en [openrouter.ai/models](https://openrouter.ai/models) |
| `Insufficient credits` | Saldo insuficiente en OpenRouter | Recarga créditos en openrouter.ai |
| `Content filtered` | La imagen fue rechazada por content moderation | Verifica que la imagen no tenga contenido sensible |

### Render issues

| Error | Causa probable | Solución |
|-------|----------------|----------|
| `Render script not found` | `tc_render.js` no está en el directorio | Verifica que `scripts/smart-import/tc_render.js` existe |
| `PHP not found` | PHP no está instalado o no en PATH | Instala PHP 8.1+ y asegúrate de que `php -v` funciona |
| `Build not found` | `npm run build` no se ha ejecutado | Corre `npm run build` desde la raíz del proyecto |
| `Editor page returned an error` | MySQL no está corriendo o DB no configurada | Inicia MySQL, verifica `.env` de la app Laravel |
| `Canvas element not found` | Timeout esperando al editor | Aumenta `TC_RENDER_TIMEOUT`. Verifica que el build de la app es correcto. |
| `Empty screenshot (0 bytes)` | El canvas no se renderizó | Verifica que el `.tc` es válido. Prueba importarlo manualmente en la app. |

### Pipeline errors

| Error | Causa probable | Solución |
|-------|----------------|----------|
| `No images found` | Directorio dataset vacío o ruta incorrecta | Verifica `--dataset` apunta a `scripts/smart-import/dataset/` |
| `Scene validation errors` | El modelo devolvió SceneGraph inválido | El validador intenta reparar automáticamente. Revisa `warnings`. |
| `Judge response is empty` | El modelo juez no devolvió contenido | Verifica que el modelo juez soporta imágenes. Algunos modelos son solo texto. |
| `Score missing required keys` | El juez no siguió el schema de respuesta | Se asigna score 0.5 por defecto. Verifica el prompt del juez. |

### Comandos de diagnóstico

```bash
# Verificar que Python dependencies están instaladas
pip list | grep -E "openai|pillow|jsonschema|requests|python-dotenv"

# Verificar que Node/Playwright están disponibles
node scripts/smart-import/tests/test_tc_render.js

# Verificar las imágenes del dataset
python scripts/smart-import/dataset/test_fixtures.py

# Regenerar imágenes sintéticas
python scripts/smart-import/dataset/generate_fixtures.py

# Ver estructura de output
tree scripts/smart-import/output/
```

---

## 10. Development

### Cómo añadir nuevas imágenes de test

1. **Crea la imagen** en `scripts/smart-import/dataset/` (JPEG, mínimo 600×800px, calidad 90+).

2. **Registra la imagen** en `dataset/README.md` siguiendo el formato de la tabla existente.

3. **Opcional: generador sintético.** Si quieres generarla con código, añade una función en
   `dataset/generate_fixtures.py` y regístrala en el diccionario `GENERATORS`.

4. **Verifica** con:
   ```bash
   python scripts/smart-import/dataset/test_fixtures.py
   ```

5. **Ejecuta el pipeline** con la nueva imagen:
   ```bash
   python scripts/smart-import/pipeline.py --image <nombre-de-la-imagen>
   ```

### Cómo añadir nuevos modelos

1. **Añade el pricing** en `openrouter.py` dentro del diccionario `MODEL_PRICING`:
   ```python
   "proveedor/nuevo-modelo": {"input": 0.000_10, "output": 0.000_40},
   ```
   Los precios son USD por cada 1K tokens. Consúltalos en [openrouter.ai/prices](https://openrouter.ai/prices).

2. **Pruébalo**:
   ```bash
   python scripts/smart-import/pipeline.py --model proveedor/nuevo-modelo
   ```

3. **Establécelo como default** (opcional) en `.env`:
   ```env
   DEFAULT_VISION_MODEL=proveedor/nuevo-modelo
   ```

### Cómo ejecutar los tests

**Tests Python** (todos los módulos):

```bash
# Desde scripts/smart-import/
python -m pytest tests/ -v

# O con unittest directamente
python -m unittest discover -s tests -v

# Tests de un módulo específico
python -m pytest tests/test_compiler.py -v
python -m pytest tests/test_openrouter.py -v
python -m pytest tests/test_pipeline.py -v
python -m pytest tests/test_validator.py -v

# Tests de fixtures del dataset
python scripts/smart-import/dataset/test_fixtures.py
```

**Tests JavaScript** (renderer):

```bash
node scripts/smart-import/tests/test_tc_render.js
```

**Nota**: Los tests de `test_tc_render.js` verifican parsing de argumentos y manejo de errores
sin lanzar un browser. Para probar el render completo necesitas el stack Laravel completo.

### Estructura de tests

```
tests/
├── __init__.py
├── test_compiler.py        # SceneGraph → .tc compilation
├── test_openrouter.py      # OpenRouter client (mocked HTTP)
├── test_pipeline.py        # Full pipeline orchestration (mocked)
├── test_validator.py       # SceneGraph validation & repair
├── test_evaluate.py        # Judge evaluator
├── test_report.py          # Report generation
├── test_tc_render.js       # Headless renderer (no browser)
└── test_tc_render.sh       # Shell wrapper tests
```

### Principios de diseño

- **Compilador determinista**: Sin llamadas a IA en la compilación. Consistente y reproducible.
- **Fases independientes**: Cada fase del pipeline puede fallar sin detener las demás.
- **Caché por hash**: SceneGraph, `.tc` y score se cachean por SHA-256 + versión + modelo/modo para evitar coste API repetido.
- **Sin estado compartido**: Cada ejecución es independiente. El output es la única fuente de verdad.
- **Tests con mocking**: Ningún test real hace llamadas reales a OpenRouter.
