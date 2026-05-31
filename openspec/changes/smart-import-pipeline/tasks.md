# Tasks: Smart Import Calibration Pipeline

## Task 1 — Scaffolding y configuración

**Archivos**: `scripts/smart-import/` directorios, `scripts/smart-import/.env.example`, `scripts/smart-import/requirements.txt`

**Descripción**: Crear estructura de directorios, .env.example con todas las variables, requirements.txt con dependencias Python, y scripts/smart-import/dataset/ con placeholder README.

**Dependencias**: Ninguna

**Criterios de aceptación**:
- [x] Directorio `scripts/smart-import/` con subdirectorios `dataset/`, `output/`
- [x] `.env.example` con OPENROUTER_API_KEY, modelos por defecto
- [x] `requirements.txt` con openai, pillow, jsonschema, requests
- [x] `dataset/` con archivo .gitkeep y README.md listando las 7 imágenes requeridas

---

## Task 2 — Schema SceneGraph y validador

**Archivos**: `scripts/smart-import/scene_schema.json`, `scripts/smart-import/validator.py`

**Descripción**: Definir JSON Schema para SceneGraph v1 y escribir el validador que verifica tipos, rangos, required fields, clamps coordenadas, descarta capas de baja confianza y normaliza colores.

**Dependencias**: Task 1

**Criterios de aceptación**:
- [x] `scene_schema.json` valida contra draft-2020-12
- [x] `validator.validate_scene()` retorna `ValidationResult` con valid, errors, warnings, fixed
- [x] Clampa coordenadas negativas o fuera del canvas
- [x] Descarta capas según modo: `text_only` descarta todo lo que no sea texto; `basic_image_layers` descarta capas con confidence < 0.5
- [x] Normaliza colores a lowercase hex de 6 dígitos
- [x] Tests unitarios con casos válidos, inválidos y borde

---

## Task 3 — OpenRouter Client

**Archivos**: `scripts/smart-import/openrouter.py`

**Descripción**: Cliente Python para OpenRouter API. Soporta chat completions con imágenes (base64/URL), response_format JSON, logging de usage (tokens, coste, latencia). Implementa retry con backoff exponencial.

**Dependencias**: Task 1

**Criterios de aceptación**:
- [x] `OpenRouterClient.chat_completion()` envía request y parsea response
- [x] `vision_analyze()` codifica imagen a base64 y construye messages
- [x] `evaluate_images()` envía dos imágenes (original + render) al juez
- [x] Logging de usage con coste calculado desde precios del modelo
- [x] Retry 3 veces con backoff en caso de error 429/5xx
- [x] Tests con mocking de HTTP

---

## Task 4 — Compilador SceneGraph → .tc ✅

**Archivos**: `scripts/smart-import/compiler.py`

**Descripción**: Compilador determinista que transforma SceneGraph validado a .tc v2. Maneja text/image/shape layers, background, recorte de assets image desde la imagen original, mapeo de fuentes/colores/alineación.

**Dependencias**: Task 2, Task 3

**Criterios de aceptación**:
- [x] `SmartImportCompiler.compile()` produce estructura .tc v2 válida
- [x] Capas text → customElements.type=text + elementLayout con estilo
- [x] Capas image → customElements.type=image + recorte data URI
- [x] Capas shape → customElements.type=shape
- [x] Background mapeado a elementLayout.background
- [x] zIndex incremental
- [x] Fuentes mapeadas a familias disponibles (Montserrat, Manrope, etc.)
- [x] Tests con SceneGraphs de fixture (válidos)
- [x] .tc generado debe ser importable en la app (pasa DesignerStateRules)

---

## Task 5 — Headless Renderer (.tc → PNG)

**Archivos**: `scripts/smart-import/tc_render.js`, `scripts/smart-import/tc_render.sh` (wrapper)

**Descripción**: Script Node/Playwright que lanza la app build, inyecta un .tc en sessionStorage, navega con `?imported=tc`, espera que el canvas renderice, y hace screenshot. Incluye timeout y cleanup.

**Dependencias**: Task 1, la app debe tener build funcional

**Criterios de aceptación**:
- [x] Acepta .tc file path y output PNG path como argumentos
- [x] Lanza Chromium headless
- [x] Inyecta .tc en sessionStorage antes de navegar
- [x] Espera hasta 30s a que el canvas sea visible
- [x] Screenshot del canvas con resolución correcta
- [x] Cierra browser al finalizar
- [x] Manejo de errores: timeouts, rutas inválidas, .tc corrupto

---

## Task 6 — Evaluador (Modelo Juez)

**Archivos**: `scripts/smart-import/evaluate.py`

**Descripción**: Evaluador que usa un modelo juez multimodal para comparar imagen original vs screenshot renderizado. Construye prompt con ambas imágenes y el SceneGraph, parsea score JSON estructurado.

**Dependencias**: Task 3, Task 5

**Nota**: Este evaluador es exclusivamente para benchmark offline y CI nocturno. NO se integra en el flujo normal del usuario.

**Criterios de aceptación**:
- [x] `ImportJudge.evaluate()` toma original_path, render_path, scene, tc_summary
- [x] Codifica ambas imágenes a base64 para la llamada
- [x] Prompt pide scores 0..1 en 5 dimensiones
- [x] Parsea respuesta JSON o intenta reparación
- [x] Retorna JudgeScore con overallScore, visualSimilarity, textAccuracy, layoutAccuracy, colorAccuracy, editability, criticalIssues, recommendations
- [x] Tests con fixtures

---

## Task 7 — Generador de Reporte

**Archivos**: `scripts/smart-import/report.py`

**Descripción**: Genera reporte markdown + JSON con tabla comparativa por imagen y modelo, promedios, costes totales, ranking de modelos. Agrupa resultados por modelo.

**Dependencias**: Task 6

**Criterios de aceptación**:
- [x] `generate_report()` agrupa resultados por modelo
- [x] Calcula promedios de cada métrica por modelo
- [x] Tabla markdown con scores, coste, latencia
- [x] JSON con datos estructurados
- [x] Ranking de modelos por overallScore/coste
- [x] Output en `output/report.md` y `output/report.json`

---

## Task 8 — Orquestador Principal ✅

**Archivos**: `scripts/smart-import/pipeline.py`, `scripts/smart-import/tests/test_pipeline.py`

**Descripción**: Script principal que orquesta el flujo completo. Itera imágenes del dataset, llama a openrouter.py → validator → compiler → tc_render (opcional) → evaluate (opcional) → report. Soporta flags para saltar fases y usar SceneGraph cacheados.

**Dependencias**: Tasks 1–7

**Criterios de aceptación**:
- [x] `pipeline.py --dataset ... --model ...` corre el flujo completo
- [x] `--skip-analysis` reusa SceneGraph cacheados
- [x] `--skip-render` salta renderizado
- [x] `--skip-eval` salta evaluación
- [x] Output estructurado en `output/{model-name}/{image-id}/`
- [x] Reporte global al finalizar
- [x] Logging progresivo a stdout
- [x] Manejo de errores por imagen (no detiene todo el pipeline)

---

## Task 9 — Dataset de 7 imágenes fixture

**Archivos**: `scripts/smart-import/dataset/` (7 imágenes)

**Descripción**: Crear o recopilar 7 imágenes representativas para el benchmark. Si no hay originales disponibles, generar imágenes sintéticas con Python (Pillow) que cubran los casos del spec.

**Dependencias**: Task 1

**Criterios de aceptación**:
- [x] 7 imágenes en `dataset/` con nombres según spec
- [x] Cada imagen cubre un caso de complejidad distinto
- [x] Resolución mínima 600×800px
- [x] Formato JPEG calidad 90+
- [ ] Expandir a 10-15 imágenes propias del dominio real antes de fijar modelo por defecto

---

## Task 10 — README y documentación de uso ✅

**Archivos**: `scripts/smart-import/README.md`

**Descripción**: Documentación completa de cómo usar el pipeline: instalación, configuración, flags, ejemplo de uso, interpretación de resultados, troubleshooting.

**Dependencias**: Tasks 1–9

**Criterios de aceptación**:
- [x] Instrucciones de instalación (requirements.txt, .env, npm build, Playwright)
- [x] Tabla de configuración con todas las variables .env
- [x] Ejemplos de uso completo (flags combinados, wrapper bash)
- [x] Tabla de flags CLI con defaults y descripciones
- [x] Explicación del output structure con árbol de directorios
- [x] Score dimensions explicadas con rangos de interpretación
- [x] Calibration workflow (cómo iterar, comparar modelos, identificar debilidades)
- [x] Architecture overview con diagrama ASCII y tabla de módulos
- [x] Troubleshooting (API errors, render issues, pipeline errors, comandos de diagnóstico)
- [x] Sección de desarrollo (cómo añadir imágenes, modelos, ejecutar tests)

---

## Task 11 — Caché por hash

**Archivos**: `scripts/smart-import/pipeline.py` (modificar), `scripts/smart-import/tests/test_cache.py`

**Descripción**: Implementar caché basada en SHA-256 de la imagen + `pipelineVersion` + `modelId`. Evita re-analizar imágenes repetidas y re-evaluar renders idénticos.

**Dependencias**: Task 8

**Criterios de aceptación**:
- [x] `_cache_key(image_path)` calcula sha256 del contenido binario
- [x] Clave de caché: `smart-import:{sha256}:{pipelineVersion}:{modelId}`
- [x] Cachea scene.json, design.tc, score.json en `output/.cache/{cache_key}/`
- [x] `--skip-analysis` consulta caché antes de llamar a OpenRouter
- [x] `--skip-eval` consulta caché de score antes de llamar al juez
- [x] Invalidación automática al cambiar pipelineVersion o modelId
- [x] Tests de integración: imagen repetida no llama API dos veces

---

## Task 12 — `image_utils.py` — utilidad de extracción de regiones

**Archivos**: `scripts/smart-import/image_utils.py`, `scripts/smart-import/tests/test_image_utils.py`

**Descripción**: Módulo independiente con funciones para extraer regiones de una imagen dadas coordenadas (bbox). Soporta salida a archivo temporal (para inpainting) y a data URI (para .tc). Extraído del compilador para que sea reutilizable por futuros módulos.

**Dependencias**: Ninguna

**Criterios de aceptación**:
- [x] `region_to_data_uri(source, bbox)` extrae región y retorna data URI base64
- [x] `extract_region(source, bbox, output_path=None)` extrae región y guarda a archivo (temp file si no se especifica ruta)
- [x] Clampa coordenadas a los límites de la imagen
- [x] Bbox negativo o área cero retorna error (string vacío / None)
- [x] Preserva el formato original (JPEG → JPEG, PNG → PNG, etc.)
- [x] `region_to_data_uri` retorna string vacío en caso de error
- [x] `extract_region` retorna None en caso de error
- [x] Compilador delega recorte a `image_utils.region_to_data_uri()`
- [x] Tests unitarios para ambos modos de salida y casos borde

---

## Task 13 — Modos de compilación V1

**Archivos**: `scripts/smart-import/pipeline.py` (modificar), `scripts/smart-import/compiler.py` (modificar), `scripts/smart-import/validator.py` (modificar)

**Descripción**: Implementar los dos modos V1: `text_only` y `basic_image_layers`. El modo se propaga desde el CLI a través del pipeline, validador y compilador.

**Dependencias**: Tasks 4, 8, 11

**Criterios de aceptación**:
- [x] Flag `--mode text_only|basic_image_layers` en CLI
- [x] `text_only`: compilador solo produce capas de texto + background. Ignora imágenes y formas.
- [x] `basic_image_layers`: compilador produce texto + background + imágenes/shapes con confidence >= 0.5
- [x] Validador descarta capas según modo (text_only: no texto; basic_image_layers: confidence < 0.5)
- [x] El modo se propaga desde pipeline → validator → compiler
- [x] Tests para ambos modos con fixture images
- [x] Documentación actualizada en README con ejemplos de uso de cada modo
