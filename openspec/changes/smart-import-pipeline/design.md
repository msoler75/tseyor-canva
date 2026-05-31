# Design: Smart Import Calibration Pipeline

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     pipeline.py                           │
│  Orquestador: itera imágenes → modelos → reporte         │
└────┬───────────────────────────────────────────────┬─────┘
     │ 1. Analizar imagen                            │
     ▼                                                │
┌──────────────────┐                                   │
│  openrouter.py   │       ┌──────────────────┐        │
│  Chat API call   │       │  image_utils.py   │        │
│  → SceneGraph    │──────→│  region_to_data_uri│        │
│  → Log usage     │       │  extract_region    │        │
└──────┬───────────┘       └────────┬─────────┘        │
       │ 2. Validar SceneGraph      │ (reutilizable     │
       ▼                            │  por inpainting   │
┌──────────────────┐                │  en V2)           │
│  validator.py    │                │                   │
│  JSON schema     │                │                   │
│  + clamp + logs  │                │                   │
└──────┬───────────┘                │                   │
       │ 3. Compilar a .tc          │                   │
       ▼                            │                   │
┌──────────────────┐                │                   │
│  compiler.py     │────────────────┘                   │
│  Determinist     │   usa region_to_data_uri()         │
│  SceneGraph→.tc  │   para crop de assets              │
│  (mode-aware)    │                                    │
└──────┬───────────┘                                    │
       │ 4. Renderizar (opcional)                       │
       ▼                                                │
┌──────────────────┐                                    │
│  tc_render.js    │                                    │
│  Playwright      │                                    │
│  .tc → PNG       │                                    │
└──────┬───────────┘                                    │
       │ 5. Evaluar (opcional — offline/CI only)        │
       ▼                                                │
┌──────────────────┐                                    │
│  evaluate.py     │                                    │
│  Modelo juez     │                                    │
│  original+render │                                    │
│  → score.json    │                                    │
└──────┬───────────┘                                    │
       │ 6. Reporte                                     │
       ▼                                                │
┌──────────────────┐                                    │
│  report.py       │                                    │
│  Tablas MD +     │                                    │
│  JSON agregado   │                                    │
└──────────────────┘                                    │
```

## Module Design

### 1. `openrouter.py` — OpenRouter Client

```
class OpenRouterClient:
    - __init__(api_key: str, base_url: str, model: str)
    - chat_completion(messages: list, response_format: dict | None) -> ChatResponse
    - vision_analyze(image_path: str, prompt: str) -> SceneGraph
    - evaluate_images(original_path: str, render_path: str, scene: dict) -> JudgeScore
```

### 2. `scene_schema.json` — JSON Schema

- Draft 2020-12 / vocabulary
- Validación de tipos, required fields, rangos
- `additionalProperties: false` para evitar invenciones del modelo

### 3. `validator.py` — SceneGraph Validator

```
def validate_scene(scene: dict, mode: str = "basic_image_layers") -> ValidationResult:
    - schema validation
    - clamp coordinates to canvas
    - discard layers with confidence < threshold:
        - text_only: discard all non-text layers (images, shapes)
        - basic_image_layers: discard layers with confidence < 0.5
    - normalize colors (lowercase hex)
    - return { valid: bool, errors: [], warnings: [], fixed: dict }
```

### 4. `compiler.py` — SceneGraph → .tc Compiler

```
class SmartImportCompiler:
    - __init__(mode: str = "basic_image_layers")
    - compile(scene: SceneGraph, source_image: str) -> TcPackage
    - _build_background(scene) -> dict
    - _build_content(scene) -> dict
    - _build_element_layout(scene) -> dict
    - _build_custom_elements(scene, source_image) -> dict
      # delegates crop to image_utils.region_to_data_uri()
    - _map_font(category: str) -> str
    - _map_align(align: str) -> str
    - _map_weight(weight: str) -> str
    - export(tc: TcPackage, path: str) -> None
```

Modos:
- `text_only`: solo compila capas `kind=text` + background. Ignora imágenes y formas.
- `basic_image_layers`: compila texto + background + capas image/shape con `confidence >= 0.5`.

### 5. `tc_render.js` — Headless Renderer

```
class TcRenderer:
    - __init__(build_dir: str, browser: Browser)
    - render(tc_path: str, output_path: str) -> None
    - _inject_tc(page: Page, tc_path: str) -> None
    - _screenshot_canvas(page: Page) -> Buffer
    - cleanup() -> None
```

### 6. `evaluate.py` — Judge Evaluator (offline/benchmark only)

> El evaluador NO se ejecuta en el flujo normal del usuario. Solo para benchmark offline y CI nocturno.

```
class ImportJudge:
    - __init__(client: OpenRouterClient, model: str)
    - evaluate(original_path: str, render_path: str, scene: dict, tc_summary: dict) -> JudgeScore
    - _build_prompt(original_b64: str, render_b64: str, scene: dict) -> list
    - _parse_score(response: ChatResponse) -> JudgeScore
```

### 7. `report.py` — Report Generator

```
def generate_report(results: list[Result], output_dir: str) -> Report:
    - group by model
    - calculate averages per model
    - generate tables (markdown + JSON)
    - add cost summary
    - add ranking
```

### 9. `image_utils.py` — Image utility functions

Módulo independiente para operaciones de imagen reutilizables. Usado por el compilador y por futuros módulos de inpainting/restauración.

```
def _crop(source_path: str, bbox: dict) -> tuple[Image.Image, str]:
    # Internal: open, clamp, crop, return (cropped_img, format_string)

def region_to_data_uri(source_path: str, bbox: dict) -> str:
    # Crop + encode as base64 data URI
    # Returns empty string on failure (missing file, zero-area, etc.)

def extract_region(source_path: str, bbox: dict, output_path: str | None = None) -> str | None:
    # Crop + save to file
    # If output_path is None, creates a temp file
    # Returns the file path, or None on failure
```

Usos previstos (V1 + V2):
- **V1**: `region_to_data_uri()` para incrustar assets en `.tc`
- **V2**: `extract_region()` para extraer regiones como entrada al pipeline de inpainting

### 10. `pipeline.py` — Orchestrator

```
class SmartImportPipeline:
    - __init__(config: dict)  # incluye mode, cache_dir
    - run(dataset_dir, model, compiler_model, judge_model, output_dir, mode, flags)
    - _process_single(image_path, model, mode, ...) -> Result
    - _cache_key(image_path: str) -> str  # sha256(image) + pipelineVersion + modelId
    - _load_from_cache(cache_key: str, phase: str) -> dict | None
    - _save_to_cache(cache_key: str, phase: str, data: dict) -> None
    - _save_artifact(path, data)
```

La caché se implementa como archivos planos en `output/.cache/{safe_cache_key}/{phase}.json`. La clave lógica sigue siendo `smart-import:{sha256}:{pipelineVersion}:{modelId}`, pero en disco se sanitiza porque `:` no es válido en nombres de archivo de Windows y los modelos OpenRouter incluyen `/`. Cada carpeta guarda `cache-key.json` con la clave lógica original. Se consulta antes de cada fase. Si el artefacto existe en caché, se reusa sin llamar a la API.

## Data Flow

### Image → SceneGraph

1. Read image, validate format/size
2. Encode as base64 data URI
3. Build messages array with system prompt + image
4. Call OpenRouter with `response_format: { type: "json_object" }`
5. Parse response, validate against schema
6. If invalid: log error, attempt repair, or fail gracefully
7. Save `scene.json`

### SceneGraph → .tc

1. Extract canvas dimensions → `designSurface`
2. Build `content` from text layers
3. Build `elementLayout` from all layer bboxes + styles
4. Build `customElements` from text/image/shape layers
5. For image layers: crop from source image → base64 data URI
6. Build `background` from scene background
7. Assemble full .tc structure
8. Validate with `DesignerStateRules` compatible check
9. Save `design.tc`

### .tc → Screenshot

1. Build app: `npm run build`
2. Launch Playwright browser (headless)
3. Navigate to `/designer/editor`
4. Inject .tc into sessionStorage
5. Reload with `?imported=tc` param
6. Wait for canvas element to appear
7. Screenshot the `.editor-canvas` element
8. Save as PNG

### Original + Screenshot → Score

1. Encode both images as base64
2. Build judge prompt with both images + scene summary
3. Call judge model with `response_format: { type: "json_object" }`
4. Parse score JSON
5. Save `score.json`

## Design Decisions

| Decisión | Opción | Razón |
|----------|--------|-------|
| Lenguaje pipeline | Python 3.11+ | Mejor soporte para ML/IA scripting |
| Render headless | Playwright + JS | Necesita Node para correr la app build |
| Comunicación Python→JS | Subprocess | Simple y directo, solo 1 punto de interacción |
| Assets en .tc | Data URIs | Autocontenido, no requiere red |
| Caché | sha256 + pipelineVersion + modelId | Invalida automáticamente cuando cambia prompt, modelo o compilador |
| Lugar de caché | `output/.cache/` | Junto a los outputs, fácil de inspeccionar y limpiar |
| Schema SceneGraph | JSON Schema draft-2020 | Validación estándar, portátil |
| Modo V1 | `text_only` → `basic_image_layers` | MVP pequeño: texto + fondo, luego añadir imágenes |
| Judge | Solo offline/CI | No añade latencia/coste al flujo del usuario |
| Capas dudosas | `confidence < 0.5` se descartan | Evita elementos espurios en el diseño importado |

## File Output Structure

```
output/{model-name}/
├── {image-id}/
│   ├── scene.json          ← SceneGraph crudo del modelo
│   ├── scene-fixed.json    ← SceneGraph después de validar/reparar
│   ├── design.tc           ← .tc compilado
│   ├── render.png          ← Screenshot del render
│   ├── score.json          ← Score del juez
│   └── openrouter.json     ← Log de la llamada OpenRouter (usage, latency)
├── model-report.json       ← Scores agregados para este modelo
└── model-report.md
output/report.json          ← Reporte global multi-modelo
output/report.md
```

## OpenRouter Usage Logging

Cada llamada debe registrar:
- `model`: string
- `promptTokens`: int
- `completionTokens`: int
- `totalTokens`: int
- `costUsd`: float (calcular desde precios del modelo)
- `latencyMs`: int
- `timestamp`: ISO 8601
- `status`: success | error
- `errorMessage`: string | null

## Error Handling

| Escenario | Acción |
|-----------|--------|
| Modelo devuelve JSON inválido | Intentar reparación básica (quitar markdown fences), si falla → marcar como `scene_valid: false` |
| SceneGraph no parseable | Crear .tc con fondo plano + texto "Error de análisis" |
| Render timeout | Marcar como `render_failed`, score automático 0 |
| Juez devuelve JSON inválido | Score default 0.5 + warning |
| OpenAI API error | Retry 3 veces con backoff exponencial |
