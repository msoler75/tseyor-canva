# Spec: Smart Import Calibration Pipeline

## 1. Benchmark Dataset

### 1.1 Imágenes fixture (7 + expansión)

Fase experimental inicial con 7 imágenes (ya implementadas):

| ID | Archivo | Descripción | Formato | Complejidad |
|----|---------|-------------|---------|-------------|
| `img-01` | `poster-simple.jpg` | Cartel simple: fondo plano + título grande + foto | vertical | Baja |
| `img-02` | `poster-gradient.jpg` | Cartel con degradado de fondo + 2 textos + forma | vertical | Media |
| `img-03` | `flyer-text-heavy.jpg` | Flyer con 5-8 bloques de texto, 2 tamaños | vertical | Alta |
| `img-04` | `poster-person.jpg` | Post cuadrado con persona + título + metadata | cuadrado | Media |
| `img-05` | `banner-horizontal.jpg` | Banner horizontal con texto + foto | horizontal | Media |
| `img-06` | `poster-display-font.jpg` | Diseño con tipografía display decorativa | vertical | Alta |
| `img-07` | `poster-low-contrast.jpg` | Diseño con bajo contraste texto/fondo | vertical | Alta |

**Antes de fijar modelo por defecto**, expandir a **10-15 imágenes propias del dominio real** de la app (posts de redes sociales, flyers de eventos, banners promocionales reales).

### 1.2 Requisitos de las imágenes

- Resolución mínima: 600×800px
- Formato: JPEG calidad 90+
- Sin compresión excesiva ni artefactos visibles
- Nombres sin espacios ni caracteres especiales

## 2. OpenRouter Integration

### 2.1 Configuración

```env
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_VISION_MODEL=google/gemini-2.5-flash
DEFAULT_COMPILER_MODEL=google/gemini-2.5-flash-lite
JUDGE_MODEL=google/gemini-2.5-pro
```

### 2.2 Prompt A — Visión → SceneGraph

Endpoint: `POST /api/v1/chat/completions`

System prompt: El contenido del archivo `importacion-inteligente-imagenes-openrouter.md` sección "Prompt A sugerido" (líneas 447-466).

Response format: `{ "type": "json_object" }` o `response_format` con schema.

Output: SceneGraph JSON según schema `scene_schema.json`.

### 2.3 Schema SceneGraph v1

Ver `scene_schema.json` para schema completo. Estructura raíz:

```json
{
  "canvas": { "width": 1080, "height": 1350, "detectedFormat": "vertical" },
  "background": { "kind": "solid|gradient|image", "color": "#...", "gradient": {...}, "confidence": 0.0-1.0 },
  "layers": [
    {
      "id": "layer-N",
      "kind": "text|image|shape",
      "confidence": 0.0-1.0,
      "bbox": { "x": 0, "y": 0, "w": 100, "h": 50 },
      "text": "...",
      "style": { "fontFamilyGuess": "...", "fontSize": 24, ... },
      "description": "...",
      "cropFromSource": true
    }
  ],
  "warnings": ["..."],
  "usage": { "promptTokens": 0, "completionTokens": 0, "costUsd": 0.0 }
}
```

### 2.4 Modos de compilación V1

El pipeline soporta dos modos en V1. El modo se define con `--mode`:

| Modo | Incluye | Descripción |
|------|---------|-------------|
| `text_only` | capas de texto + fondo original | Extrae solo textos editables + fondo. Sin recortes de imágenes ni formas. |
| `basic_image_layers` | texto + fondo + fotos rectangulares de alta confianza | Además de textos, recorta imágenes con `confidence >= 0.5` y las inserta como recortes rectangulares. Sin inpainting. |

**V2 (futuro)**: se añadirá `advanced_restoration` con inpainting/repainting para elementos ocluidos y restauración avanzada.

### 2.5 Filtrado por confianza

El pipeline **descarta automáticamente** capas con `confidence < 0.5` en modo `basic_image_layers`. La confianza de cada capa se conserva en el SceneGraph para que la UI pueda mostrarla y permitir al usuario decidir si incluirla.

### 2.6 SceneGraph -> .tc Compiler

Compilador determinista (sin IA). Reglas:

1. `designSurface.width/height` ← `canvas`
2. Página única `smart-page-1`
3. `layer.kind=text` → `customElements[id].type=text` con `elementLayout[id]`
4. `layer.kind=image` → solo si modo `basic_image_layers` y `confidence >= 0.5` → `customElements[id].type=image` + recorte rectangular de asset
5. `layer.kind=shape` → solo si modo `basic_image_layers` y `confidence >= 0.5` → `customElements[id].type=shape`
6. Bbox mapeado a `elementLayout[id].{x,y,w,h}`
7. Estilos mapeados: color, fontSize, fontWeight, textAlign
8. zIndex incremental por orden de layers
9. Background mapeado a `elementLayout.background`
10. Assets image se recortan desde original usando bbox + se guardan como data URI mediante `image_utils.region_to_data_uri()`

### 2.7 Archivo .tc output

- `tcVersion: 2`
- Estructura completa con `content`, `elementLayout`, `customElements`, `pages`
- Assets inline como data URIs en `customElements[].src`

## 3. Headless Renderer

### 3.1 Mecanismo

- Usar Playwright para abrir la app build (Vite build)
- Navegar a `/designer/editor?imported=tc`
- Inyectar .tc en sessionStorage antes de la navegación
- Esperar a que el canvas renderice (selector visible)
- Hacer screenshot del canvas
- Guardar PNG en `output/screenshots/{image-id}-{model}.png`

### 3.2 Requisitos

- Debe correr en headless mode (sin display)
- Timeout por render: 30s
- Resolución de screenshot: la del designSurface
- El build de la app debe estar actualizado

### 3.3 Flujo

```js
// 1. Lanzar browser
// 2. Ir a /designer/editor
// 3. Inyectar .tc en sessionStorage
// 4. Recargar con ?imported=tc
// 5. Esperar a que el canvas cargue
// 6. Hacer screenshot del canvas element
// 7. Guardar PNG
// 8. Cerrar browser
```

## 4. Evaluator (Modelo Juez)

> **IMPORTANTE**: El modelo juez es exclusivamente para **benchmark offline y CI nocturno**. NO forma parte del flujo normal del usuario. Su propósito es calibrar prompts y modelos, no evaluar importaciones individuales.

### 4.1 Input

- Imagen original (path)
- Screenshot renderizado (path)
- SceneGraph generado (path)
- Resumen del .tc: capas, tipos, bboxes

### 4.2 Output

```json
{
  "overallScore": 0.82,
  "visualSimilarity": 0.78,
  "textAccuracy": 0.94,
  "layoutAccuracy": 0.81,
  "colorAccuracy": 0.74,
  "editability": 0.86,
  "criticalIssues": [],
  "recommendations": []
}
```

### 4.3 Prompt del juez

```
Compara la IMAGEN ORIGINAL con el RENDER IMPORTADO (captura de pantalla del editor después de importar el .tc generado automáticamente).

Evalúa:
1. Similitud visual global (colores, disposición, proporciones)
2. Precisión de textos (OCR: ¿están todos los textos y son correctos?)
3. Precisión de layout (posiciones, tamaños, espaciado)
4. Precisión de colores (fondo, texto, formas)
5. Editabilidad (los textos son capas editables, no imagen plana)

Devuelve SOLO JSON con scores 0..1 y lista de issues críticos y recomendaciones.
```

### 4.4 Modelo juez recomendado

- Default: `google/gemini-2.5-pro` (balance)
- Premium: `anthropic/claude-sonnet-4.5` (máxima calidad)
- Barato: `google/gemini-2.5-flash` (desarrollo rápido)

## 5. Pipeline Orchestrator

### 5.1 Entry point

```bash
python scripts/smart-import/pipeline.py \
  --dataset scripts/smart-import/dataset/ \
  --model google/gemini-2.5-flash \
  --output scripts/smart-import/output/
```

### 5.2 Flags

| Flag | Default | Descripción |
|------|---------|-------------|
| `--dataset` | `dataset/` | Directorio con imágenes |
| `--model` | `gemini-2.5-flash` | Modelo visión para Prompt A |
| `--mode` | `basic_image_layers` | Modo de compilación: `text_only` \| `basic_image_layers` |
| `--compiler-model` | `gemini-2.5-flash-lite` | Modelo para compilar a .tc (si no se usa determinista) |
| `--skip-analysis` | false | Usar SceneGraph cacheados (para re-compilar) |
| `--skip-render` | false | Saltar renderizado (solo .tc) |
| `--skip-eval` | false | Saltar evaluación (solo .tc + render) |
| `--judge-model` | `gemini-2.5-pro` | Modelo juez |
| `--output` | `output/` | Directorio de salida |

### 5.3 Output structure

```
output/
├── {model-name}/
│   ├── img-01/
│   │   ├── scene.json
│   │   ├── design.tc
│   │   ├── render.png
│   │   ├── score.json
│   │   └── openrouter.json
│   ├── img-02/
│   │   └── ...
│   └── ...
├── report.json
└── report.md
```

## 6. Cache por hash

### 6.1 Motivación

- Evitar llamadas repetidas a la API si la misma imagen se reimporta
- Reducir coste en producción
- Acelerar el reintento del usuario

### 6.2 Clave de caché

```
smart-import:{sha256}:{pipelineVersion}:{modelId}
```

Donde:
- `sha256`: hash SHA-256 del contenido binario de la imagen
- `pipelineVersion`: semver del pipeline (e.g. `1.0.0`)
- `modelId`: identificador del modelo OpenRouter usado

### 6.3 Artefactos cacheados

- SceneGraph generado (`scene.json`)
- `.tc` compilado (`design.tc`)
- Score del juez (`score.json`), si aplica

### 6.4 Invalidación

Cambiar cualquiera de estos invalida la caché automáticamente:
- El prompt de visión
- El compilador SceneGraph → .tc
- El modelo de visión
- El contrato `.tc`
- La lógica de máscara/recorte

Al implementar la caché, NO se cachean respuestas del modelo de forma implícita. Es el pipeline quien decide explícitamente qué guardar y qué omitir según los flags `--skip-analysis`, `--skip-eval`.

### 6.5 Implementación

La caché es un diccionario simple en el orquestador (archivos en `output/.cache/`). La clave lógica es la definida arriba, pero el directorio físico usa una versión sanitizada para compatibilidad Windows (`:` y `/` no son seguros como nombre de carpeta). Cada carpeta incluye `cache-key.json` con la clave lógica original. Antes de llamar a la API, el pipeline calcula el hash y verifica si existe el artefacto en caché.

## 7. Report

### 6.1 Formato

Tabla markdown con columnas:

| Imagen | Score Visual | Texto | Layout | Color | Editab. | Coste $ | Tiempo s |
|--------|-------------|-------|--------|-------|---------|---------|----------|

### 6.2 Resumen

- Promedio de cada métrica por modelo
- Coste total por modelo
- Ranking de modelos por overallScore/coste
