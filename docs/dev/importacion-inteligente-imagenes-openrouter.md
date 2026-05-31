# Investigación revisada: importación inteligente de imágenes tipo Google Stitch con OpenRouter

Esta versión corrige la investigación inicial. El objetivo ya no es solo “usar IA para importar imágenes”, sino diseñar un flujo comparable conceptualmente a Google Stitch: **imagen/prompts → interpretación visual estructurada → capas editables → formato interno `.tc`**.

La conclusión técnica es clara: para Tseyor Canva conviene separar el problema en dos llamadas/modelos:

1. **Visión / análisis de composición**: un modelo multimodal mira la imagen y devuelve una escena estructurada: textos, posiciones, colores, fuentes aproximadas, cajas, imágenes, formas, fondos, degradados y confianza por capa.
2. **Traducción a Tseyor Canva**: otro prompt —o, mejor aún, un compilador determinista asistido por modelo— convierte esa escena al contrato `.tc v2`: `designSurface`, `pages`, `content`, `elementLayout`, `customElements`, `userUploadedImages`.

NO conviene pedir al primer modelo que invente directamente un `.tc`. Eso mezcla percepción visual, decisiones de diseño y contrato interno en una sola caja negra. Esa es la receta para tener errores difíciles de depurar.

---

## 1. Qué sabemos de Google Stitch

### Evidencia pública

Google no publica la arquitectura interna completa de Stitch. Por tanto, cualquier afirmación de “cómo está implementado por dentro” debe marcarse como inferencia.

Lo que sí está documentado o reportado públicamente:

- Google Labs describe Stitch como un “AI design canvas” que transforma lenguaje natural en UI de alta fidelidad, editable e iterable. Fuente: https://labs.google/
- TechCrunch reportó en Google I/O 2025 que Stitch genera elementos de UI y código para frontends web/móvil, acepta prompts con texto o imagen, produce HTML/CSS y permite elegir Gemini 2.5 Pro o Gemini 2.5 Flash. Fuente: https://techcrunch.com/2025/05/20/google-launches-stitch-an-ai-powered-tool-to-help-design-apps/
- Google publicó que Gemini 2.5 Pro fue actualizado con capacidades mejoradas para construir web apps interactivas y que combina coding + razonamiento multimodal. Fuente: https://blog.google/products-and-platforms/products/gemini/gemini-2-5-pro-updates/
- Google publicó que Gemini 2.5 Flash es su modelo eficiente para velocidad/coste y que mejoró en razonamiento, multimodalidad, código y contexto largo. Fuente: https://blog.google/innovation-and-ai/models-and-research/google-deepmind/google-gemini-updates-io-2025/
- Google también publicó un modelo Computer Use construido sobre capacidades de visión y razonamiento de Gemini 2.5 Pro para interactuar con UIs. No es Stitch, pero confirma que Google está usando visión+razonamiento sobre interfaces como primitiva técnica. Fuente: https://blog.google/innovation-and-ai/models-and-research/google-deepmind/gemini-computer-use-model/
- Codecademy resume el uso observable de Stitch: texto o imagen/wireframe → UI responsive + HTML/CSS, Figma en ciertos modos, límites por modo, y limitaciones como errores en iconos/labels/alineación. Fuente: https://www.codecademy.com/article/google-stitch-tutorial-ai-powered-ui-design-tool

### Inferencia técnica razonable

Stitch probablemente no hace “una imagen final bonita” y ya. Por sus salidas editables y exportables, la forma técnica más probable es:

```text
Input del usuario
  ├─ prompt textual
  ├─ screenshot / wireframe / sketch
  ▼
Modelo multimodal
  ├─ interpreta intención
  ├─ detecta estructura visual
  ├─ deduce componentes
  ├─ deduce tokens de diseño: color, tipografía, spacing
  ▼
Representación intermedia
  ├─ árbol de pantallas
  ├─ componentes
  ├─ layout
  ├─ estilos
  ▼
Renderizadores
  ├─ canvas editable propio
  ├─ HTML/CSS
  └─ Figma / capas editables
```

La lección para Tseyor Canva es directa: **no imites la UI de Stitch; imita su pipeline conceptual**. Primero una representación intermedia semántica, después compiladores/exportadores.

---

## 2. Contrato actual de Tseyor Canva que debemos generar

La app ya tiene un formato admisible. No hay que inventar otro.

Evidencia local:

- `resources/js/data/designer.js:451` define `initialDesignerState`.
- `resources/js/data/designer.js:466` contempla `designSurface`.
- `resources/js/data/designer.js:467` contempla `content`.
- `resources/js/data/designer.js:479` contempla `elementLayout`.
- `resources/js/data/designer.js:487-488` contempla `pages` y `userUploadedImages`.
- `app/Support/DesignerStateRules.php:143` permite `customElements.*.type` en `text,image,shape,linkedText,qr`.
- `docs/dev/import-export.md` documenta `.tcVersion: 2` y el flujo de import/export.
- Hay fixtures reales:
  - `docs/dev/fixtures/qa-visual-test.tc`
  - `docs/dev/fixtures/qa-visual-effects-matrix.tc`

Por tanto, la salida final debe ser:

```json
{
  "tcVersion": 2,
  "format": "vertical",
  "size": "1080 × 1350 px",
  "designSurface": { "width": 1080, "height": 1350 },
  "designTitle": "Importado desde imagen",
  "objective": "generic",
  "outputType": "digital",
  "pages": [
    {
      "id": "smart-page-1",
      "content": {},
      "elementLayout": {},
      "customElements": {}
    }
  ],
  "content": {},
  "elementLayout": {},
  "customElements": {},
  "userUploadedImages": [],
  "workingDocumentPageId": "smart-page-1"
}
```

---

## 3. OpenRouter: modelos candidatos actuales

Consulta realizada el **2026-05-31** contra:

```text
https://openrouter.ai/api/v1/models?output_modalities=text
```

Filtro usado:

- `architecture.input_modalities` contiene `image`;
- `architecture.output_modalities` contiene `text`;
- `supported_parameters` contiene `response_format` o `structured_outputs`;
- precios calculados como USD por millón de tokens usando `pricing.prompt` y `pricing.completion`.

Documentación oficial de OpenRouter:

- Image inputs: https://openrouter.ai/docs/guides/overview/multimodal/image-understanding
- Structured outputs: https://openrouter.ai/docs/guides/features/structured-outputs
- Models API: https://openrouter.ai/docs/guides/overview/models
- API parameters: https://openrouter.ai/docs/api/reference/parameters

OpenRouter indica que las imágenes se envían por `/api/v1/chat/completions` como `image_url`, con URL o base64/data URL. También expone `response_format` con `json_schema` en modelos compatibles, y el Models API declara `input_modalities`, `output_modalities`, `supported_parameters` y precios.

### Modelos especialmente relevantes

| Modelo OpenRouter | Entrada | JSON/Schema | Contexto | Precio input / M | Precio output / M | Precio imagen | Uso recomendado |
|---|---|---:|---:|---:|---:|---:|---|
| `google/gemini-2.5-flash-lite` | text,image,file,audio,video | sí | 1,048,576 | $0.10 | $0.40 | $0.0000001 | MVP barato, OCR/layout razonable |
| `google/gemini-2.5-flash` | file,image,text,audio,video | sí | 1,048,576 | $0.30 | $2.50 | $0.0000003 | Buen equilibrio visión/coste |
| `google/gemini-2.5-pro` | text,image,file,audio,video | sí | 1,048,576 | $1.25 | $10.00 | $0.00000125 | Alta fidelidad para análisis difícil |
| `google/gemini-3.1-pro-preview` | audio,file,image,text,video | sí | 1,048,576 | $2.00 | $12.00 | $0.000002 | Candidato premium si se valida en pruebas |
| `qwen/qwen3-vl-30b-a3b-instruct` | text,image | sí | 262,144 | $0.13 | $0.52 | no expuesto | Candidato coste/calidad para visión |
| `qwen/qwen3-vl-235b-a22b-instruct` | text,image | sí | 262,144 | $0.20 | $0.88 | no expuesto | Visión fuerte con coste bajo |
| `mistralai/mistral-small-3.2-24b-instruct` | image,text | sí | 128,000 | $0.075 | $0.20 | no expuesto | Muy barato; validar precisión visual |
| `openai/gpt-4o-mini` | text,image,file | sí | 128,000 | $0.15 | $0.60 | no expuesto | Buen baseline barato |
| `openai/gpt-5-mini` | text,image,file | sí | 400,000 | $0.25 | $2.00 | no expuesto | Traductor/razonador intermedio |
| `anthropic/claude-sonnet-4.5` | text,image,file | sí | 1,000,000 | $3.00 | $15.00 | no expuesto | Excelente razonamiento; caro |
| `x-ai/grok-4.3` | text,image | sí | 1,000,000 | $1.25 | $2.50 | no expuesto | Candidato alternativo a probar |

### Lectura importante de precios

Los precios de imagen aparecen como `pricing.image` solo en algunos modelos. En otros aparece `null`; eso no significa “gratis”, sino que el coste puede estar incluido/contabilizado como tokens o depender del proveedor. En producción hay que guardar `usage` real por request.

### Extracción real de fotografías como capas

Hay que separar tres capacidades que suelen mezclarse:

| Capacidad | Qué hace | ¿La cubren los modelos visión de OpenRouter? | ¿Sirve para Tseyor Canva? |
|---|---|---:|---|
| Detección | “Hay una foto/persona en `x,y,w,h`” | Sí, con modelos visión como Gemini/Qwen/Mistral/OpenAI | Sí: permite crear una capa `image` usando un recorte rectangular |
| Segmentación/máscara | “Estos píxeles pertenecen a la persona/foto” | No está garantizado en chat vision genérico; requiere modelo/servicio de segmentación | Sí, pero como paso adicional |
| Extracción limpia bajo oclusiones | “Devuélveme la foto original sin el texto que la tapa” | No como extracción fiel; solo puede editar/inpaintar o reconstruir | Riesgoso: ya no es la foto original, es una imagen generada |

Consulta OpenRouter del 2026-05-31:

- Existen modelos con `output_modalities` que incluyen `image`, por ejemplo:
  - `google/gemini-2.5-flash-image`
  - `google/gemini-3.1-flash-image-preview`
  - `google/gemini-3-pro-image-preview`
  - `openai/gpt-5-image`
  - `openai/gpt-5-image-mini`
- Esos modelos pueden generar/editar imágenes, según la guía oficial de OpenRouter Image Generation: https://openrouter.ai/docs/guides/overview/multimodal/image-generation
- Pero “generar/editar imagen” no equivale a “extraer el asset original oculto”. Si el texto tapa parte de una fotografía, los píxeles tapados no existen en la imagen de entrada. Cualquier resultado limpio en esa zona será reconstrucción/inpainting, no recuperación.

Implicación para la app:

1. Si el texto NO tapa la foto, o tapa poco:
   - modelo visión devuelve bbox de foto;
   - backend recorta la región desde la imagen original;
   - Tseyor Canva crea una capa `image` con ese recorte;
   - textos detectados se crean como capas `text` encima.
2. Si el texto tapa parte importante de la foto:
   - el recorte rectangular conservará el texto incrustado;
   - para quitarlo haría falta un paso de inpainting/generative edit;
   - esa imagen resultante debe marcarse como “reconstruida”, no como “fotografía original”.
3. Si se necesita la silueta de una persona sin fondo:
   - conviene integrar un modelo específico de segmentación/removal background;
   - el modelo visión puede sugerir la región, pero no debe ser el único responsable del recorte fino.

Para MVP, la opción robusta es:

```text
imagen original como fondo o referencia
+ capas de texto editables encima
+ recortes rectangulares de foto solo cuando la confianza sea alta
```

Para una versión avanzada:

```text
visión → bbox
+ segmentación/máscara
+ crop o background-removal
+ inpainting opcional si hay texto encima
+ capa image reconstruida con etiqueta de confianza
```

#### Pipeline avanzado con inpainting/repainting

La mejora propuesta es viable y debe modelarse como una rama explícita del pipeline:

```text
Imagen original
  ▼
Prompt A visión
  ├─ detecta texto: bbox, contenido, estilo, zIndex probable
  ├─ detecta fotografía: bbox, tipo de contenido, confianza
  └─ detecta oclusión: texto/shape encima de la foto
  ▼
Extractor determinista
  ├─ recorta bbox amplio de la fotografía
  ├─ genera máscara de zonas oclusoras dentro del recorte
  └─ conserva metadatos: cropBox, occlusionMask, sourceImageHash
  ▼
Modelo image-output / inpainting
  ├─ recibe crop + máscara + instrucción conservadora
  └─ devuelve asset restaurado/reconstruido
  ▼
SmartImportCompiler
  ├─ crea capa image con asset restaurado
  ├─ crea capa text editable por encima
  ├─ preserva zIndex correcto
  └─ añade metadata de confianza/reconstrucción
```

La máscara es la pieza crítica. No basta con decirle al modelo “quita el texto”: hay que indicarle exactamente qué zona debe repintar. Esa máscara puede salir de:

1. los bboxes de texto detectados por el modelo visión;
2. OCR/localización de texto adicional si se integra;
3. detección de formas oclusoras;
4. expansión/padding de seguridad para cubrir antialiasing, sombra y contorno del texto.

Ejemplo de metadata intermedia:

```json
{
  "id": "photo-1",
  "kind": "image",
  "bbox": { "x": 180, "y": 260, "w": 720, "h": 620 },
  "description": "fotografía de una persona",
  "occlusion": {
    "isOccluded": true,
    "occluders": [
      {
        "layerId": "text-1",
        "kind": "text",
        "bbox": { "x": 240, "y": 310, "w": 600, "h": 110 },
        "maskPadding": 12
      }
    ],
    "estimatedOccludedAreaPct": 8.5
  },
  "restoration": {
    "strategy": "inpaint_masked_crop",
    "mustPreserveUnmaskedPixels": true,
    "label": "reconstructed",
    "confidence": 0.72
  }
}
```

Resultado en `.tc`:

- capa `image`: usa el asset restaurado;
- capa `text`: texto editable colocado encima, con bbox/style del análisis;
- `zIndex`: la foto queda debajo y el texto encima;
- metadata interna opcional: marca el asset como `reconstructed`, con `confidence`.

Importante: para UX y depuración, la app debería ofrecer comparación:

| Vista | Propósito |
|---|---|
| Original | Ver la imagen de entrada intacta |
| Recorte fiel | Ver la fotografía tal como aparece, con oclusiones |
| Restaurado | Ver la versión inpainted/reconstruida |
| Diseño editable | Ver foto restaurada + texto editable recreado encima |

Regla de producto recomendada:

- Si la oclusión es baja, usar inpainting automático puede aportar mucho.
- Si la oclusión es alta o tapa caras/manos/detalles críticos, pedir confirmación al usuario.
- Si el modelo tiene baja confianza, usar recorte fiel o fondo original como fallback.

Modelos OpenRouter relevantes para esta rama:

| Tarea | Modelos candidatos |
|---|---|
| Detectar bbox/texto/foto/oclusión | `google/gemini-2.5-flash`, `google/gemini-2.5-pro`, `qwen/qwen3-vl-30b-a3b-instruct` |
| Generar/editar imagen restaurada | `google/gemini-2.5-flash-image`, `google/gemini-3.1-flash-image-preview`, `google/gemini-3-pro-image-preview`, `openai/gpt-5-image-mini`, `openai/gpt-5-image` |
| Traducir a `.tc` | `google/gemini-2.5-flash-lite`, `openai/gpt-5-mini` o `SmartImportCompiler` determinista |

La instrucción al modelo de imagen debe ser conservadora:

```text
Rellena únicamente las zonas enmascaradas para reconstruir la fotografía de fondo.
No cambies píxeles fuera de la máscara.
Mantén iluminación, perspectiva, textura, color y estilo fotográfico.
No añadas texto, logos ni elementos nuevos.
Devuelve solo la imagen restaurada.
```

El nombre correcto del asset no debería ser `original`, sino:

- `restoredPhoto`;
- `reconstructedPhoto`;
- `inpaintedPhoto`;
- o `photoAssetRestored`.

Esto importa porque el sistema debe poder explicar al usuario cuándo una imagen fue recuperada por recorte y cuándo fue generada parcialmente.

Estimación orientativa por una imagen simple:

Suposición:

- Prompt visión: 6k tokens de entrada + imagen.
- Salida escena: 4k tokens.
- Prompt traducción: 5k tokens de entrada.
- Salida `.tc`: 8k tokens.

Coste aproximado solo tokens:

| Pipeline | Visión | Traducción | Coste aprox. |
|---|---|---|---:|
| Barato | `mistral-small-3.2` + `gemini-2.5-flash-lite` | 6k\*$0.075/M + 4k\*$0.20/M + 5k\*$0.10/M + 8k\*$0.40/M | ~$0.005 |
| Equilibrado | `gemini-2.5-flash` + `gemini-2.5-flash-lite` | 6k\*$0.30/M + 4k\*$2.50/M + 5k\*$0.10/M + 8k\*$0.40/M | ~$0.016 |
| Fiel | `gemini-2.5-pro` + `gemini-2.5-flash-lite` | 6k\*$1.25/M + 4k\*$10/M + 5k\*$0.10/M + 8k\*$0.40/M | ~$0.051 |
| Premium razonamiento | `claude-sonnet-4.5` + `gpt-5-mini` | 6k\*$3/M + 4k\*$15/M + 5k\*$0.25/M + 8k\*$2/M | ~$0.095 |

Esto es barato por unidad, pero NO es gratis a escala. 10.000 importaciones/mes a $0.016 son ~$160/mes solo en tokens aproximados. Hay que medir uso real.

---

## 4. Diseño técnico recomendado: dos prompts + validación

### Fase A — Prompt de visión

Responsabilidad: extraer “lo que ve” el modelo. Nada de `.tc`.

Debe devolver:

- tamaño del canvas original;
- fondo:
  - color dominante;
  - degradado si existe;
  - imagen de fondo si conviene;
- bloques de texto:
  - texto OCR;
  - bbox;
  - color;
  - tamaño aproximado;
  - peso;
  - estilo;
  - alineación;
  - fuente aproximada o categoría;
  - confianza;
- regiones de imagen/foto:
  - bbox;
  - descripción;
  - si debe recortarse desde la fuente;
  - confianza;
- formas:
  - rectángulos, círculos, líneas, chips, paneles;
  - color, borde, radio, opacidad;
- efectos:
  - sombras;
  - degradados;
  - opacidades;
  - tintes;
- orden visual aproximado / `zIndex`.

#### Schema intermedio propuesto

```json
{
  "canvas": {
    "width": 1080,
    "height": 1350,
    "detectedFormat": "vertical"
  },
  "background": {
    "kind": "solid|gradient|image|unknown",
    "color": "#ffffff",
    "gradient": {
      "from": "#111827",
      "to": "#4338ca",
      "angle": 135
    },
    "confidence": 0.8
  },
  "layers": [
    {
      "id": "layer-1",
      "kind": "text",
      "confidence": 0.92,
      "bbox": { "x": 120, "y": 80, "w": 820, "h": 130 },
      "text": "Curso de meditación",
      "style": {
        "fontFamilyGuess": "Montserrat",
        "fontCategory": "sans|serif|display|handwriting|monospace",
        "fontSize": 64,
        "fontWeight": "regular|medium|bold",
        "italic": false,
        "uppercase": false,
        "color": "#ffffff",
        "textAlign": "left|center|right|justify",
        "lineHeight": 1.1,
        "letterSpacing": 0,
        "shadow": false
      }
    },
    {
      "id": "layer-2",
      "kind": "image",
      "confidence": 0.84,
      "bbox": { "x": 240, "y": 320, "w": 600, "h": 520 },
      "description": "fotografía de una persona",
      "cropFromSource": true,
      "mask": { "shape": "rectangle", "borderRadius": 24 }
    },
    {
      "id": "layer-3",
      "kind": "shape",
      "confidence": 0.76,
      "bbox": { "x": 80, "y": 950, "w": 920, "h": 120 },
      "shape": "rectangle",
      "style": {
        "fill": "#111827",
        "opacity": 70,
        "borderRadius": 32
      }
    }
  ],
  "warnings": [
    "La fuente exacta no puede identificarse con certeza."
  ]
}
```

#### Prompt A sugerido

```text
Eres un analizador de composición gráfica para reconstruir una imagen como diseño editable.

Tu tarea NO es crear un diseño nuevo. Tu tarea es describir con precisión lo visible.

Devuelve SOLO JSON que cumpla el schema.

Reglas:
- Usa coordenadas absolutas en píxeles respecto a la imagen original.
- Detecta todos los textos legibles con OCR.
- Agrupa texto por bloques editables, no por letras.
- No inventes texto que no esté visible.
- Estima estilo: color, tamaño, peso, alineación, categoría de fuente, lineHeight, letterSpacing.
- Detecta fotos/ilustraciones como capas image con bbox y descripción.
- Detecta formas simples: rectángulos, círculos, líneas, chips, paneles, iconos simples si son relevantes.
- Detecta degradados, sombras, transparencias y bordes cuando sean relevantes.
- Usa confidence 0..1 por cada capa.
- Si algo es incierto, informa en warnings.
- Prioriza precisión espacial por encima de creatividad.
```

### Fase B — Prompt de traducción a `.tc`

Responsabilidad: transformar la escena intermedia a Tseyor Canva.

Aquí hay dos opciones:

#### Opción recomendada: compilador determinista

`SmartImportCompiler` en PHP/JS traduce `SceneGraph` a `.tc`.

Ventaja:

- reproducible;
- testeable;
- sin alucinaciones;
- respeta `DesignerStateRules`.

#### Opción aceptable: prompt B + validador

Un modelo genera un borrador `.tc`, pero la app valida y normaliza.

Regla de oro: **el output del modelo nunca entra directo al editor sin validar**.

#### Prompt B sugerido

```text
Eres un compilador de SceneGraph a formato Tseyor Canva .tc v2.

Recibirás:
1. Un SceneGraph de importación inteligente.
2. El contrato permitido de Tseyor Canva.

Devuelve SOLO JSON .tc v2 válido.

Reglas:
- Crea tcVersion: 2.
- Usa designSurface.width/height desde canvas.
- Crea una única página smart-page-1 salvo que se indique otra cosa.
- Convierte layer.kind=text a customElements[id].type=text.
- Convierte layer.kind=image a customElements[id].type=image.
- Convierte layer.kind=shape a customElements[id].type=shape.
- Copia bbox.x/y/w/h a elementLayout.
- Mapea fontCategory a familias disponibles:
  - sans → "Montserrat, sans-serif" o "Manrope, sans-serif"
  - display → "Bebas Neue, sans-serif"
  - serif → "Merriweather, serif"
- Clampa coordenadas dentro del canvas.
- Si falta h en texto, úsala solo cuando venga en bbox; si no, omítela.
- Usa zIndex incremental por orden visual.
- No añadas campos fuera del contrato.
- Si una capa tiene confidence < 0.45, inclúyela solo si es texto legible.
```

---

## 5. Pipeline final recomendado para Tseyor Canva

```text
POST /designer/smart-import/image/analyze
  │
  ├─ valida archivo: mime, tamaño, dimensiones
  ├─ reduce imagen para análisis si excede límite
  ├─ guarda original temporal/asset
  │
  ▼
OpenRouter Prompt A
  modelo visión
  salida: SceneGraph JSON
  │
  ▼
Validador SceneGraph
  ├─ JSON schema
  ├─ clamp coordenadas
  ├─ descarta capas imposibles
  ├─ normaliza colores/fuentes
  │
  ▼
Recorte de assets
  ├─ para image layers con cropFromSource=true
  ├─ genera data URI o DesignAsset
  │
  ▼
Prompt B o SmartImportCompiler
  salida: .tc v2
  │
  ▼
Validador .tc
  ├─ DesignerStateRules
  ├─ límites de capas
  ├─ límites de tamaño
  │
  ▼
Editor
  ├─ preview
  ├─ aceptar
  ├─ regenerar
  └─ editar manualmente
```

---

## 5.1 MVP estricto

El MVP debe ser deliberadamente pequeño. Si intentamos meter todo desde el primer sprint, destruimos la viabilidad del producto.

### Lo que SÍ entra en V1

- detectar textos visibles;
- crear capas `text` editables;
- mantener la imagen original como fondo o referencia;
- extraer recortes rectangulares de fotografías solo con confianza alta;
- compilar a `.tc v2`;
- mostrar confianza por capa;
- permitir ocultar o descartar capas problemáticas;
- ofrecer modo **solo texto**;
- cachear resultados por hash de imagen.

### Lo que NO entra en V1

- inpainting/repainting automático;
- segmentación fina de personas/objetos;
- background removal avanzado;
- reconstrucción de fotos tapadas;
- exportación a Figma;
- iteración visual automática multi-paso;
- fidelidad “tipo Stitch” prometida como si fuera un clon perfecto.

### Regla de oro del MVP

```text
imagen original + texto editable + recortes rectangulares confiables
```

Nada más. El resto es V2.

### UX honesta obligatoria

El riesgo principal no es técnico; es de expectativa. “Importación inteligente” suena a magia, así que la interfaz debe ser explícita:

- mostrar confianza por capa;
- marcar capas dudosas;
- permitir desactivar capas problemáticas;
- ofrecer modo `text_only` como primer paso;
- avisar que las fuentes son aproximaciones;
- avisar que la fidelidad visual no será perfecta en tipografías complejas o textos sobre fotos;
- explicar que el resultado es un **punto de partida editable**, no un clon perfecto.

---

## 6. Qué modelo usar en cada fase

### Matriz de decisión por etapa

Precios verificados en OpenRouter el **2026-05-31**. Los importes son USD por millón de tokens (`prompt_M` / `completion_M`) según la API de modelos. Cuando `image_each` aparece como `null`, OpenRouter no expone precio de imagen separado para ese modelo; hay que medir `usage` real en producción.

| Etapa | Objetivo | Opción coste bajo | Opción equilibrada | Opción máxima fidelidad | Recomendación |
|---|---|---|---|---|---|
| A. Análisis visual / SceneGraph | Detectar textos, bbox, colores, foto, formas, oclusiones | `mistralai/mistral-small-3.2-24b-instruct` ($0.075/M in, $0.20/M out) o `qwen/qwen3-vl-8b-instruct` ($0.08/M, $0.50/M) | `google/gemini-2.5-flash` ($0.30/M, $2.50/M) o `qwen/qwen3-vl-30b-a3b-instruct` ($0.13/M, $0.52/M) | `google/gemini-2.5-pro` ($1.25/M, $10/M), `google/gemini-3.1-pro-preview` ($2/M, $12/M), `anthropic/claude-sonnet-4.5` ($3/M, $15/M) | Empezar con `gemini-2.5-flash`; comparar contra `qwen3-vl-30b` por coste |
| B. Detección de oclusión | Decidir si texto/forma tapa una foto y generar bboxes de máscara | `qwen/qwen3-vl-30b-a3b-instruct` | `google/gemini-2.5-flash` | `google/gemini-2.5-pro` | Usar el mismo modelo de A al principio; luego separar si falla |
| C. Máscara determinista | Convertir bboxes de oclusores en máscara de inpainting | Sin modelo: código propio | Sin modelo: código propio + OCR si se integra | Modelo solo como auditor, no como generador de máscara final | Debe ser determinista; la IA propone, el código pinta la máscara |
| D. Inpainting / repainting | Reconstruir zona de foto tapada | `google/gemini-2.5-flash-image` ($0.30/M, $2.50/M) | `google/gemini-3.1-flash-image-preview` ($0.50/M, $3/M) o `openai/gpt-5-image-mini` ($2.50/M, $2/M) | `google/gemini-3-pro-image-preview` ($2/M, $12/M), `openai/gpt-5-image` ($10/M, $10/M), `openai/gpt-5.4-image-2` ($8/M, $15/M) | Empezar con `gemini-2.5-flash-image`; reservar Pro/OpenAI para casos difíciles |
| E. Traducción SceneGraph → `.tc` | Convertir escena validada al contrato Tseyor Canva | `google/gemini-2.5-flash-lite` ($0.10/M, $0.40/M) | `openai/gpt-5-mini` ($0.25/M, $2/M) | `openai/gpt-5.1` ($1.25/M, $10/M) o `claude-sonnet-4.5` | Mejor: `SmartImportCompiler` determinista; modelo solo como fallback |
| F. QA automático / juez multimodal | Comparar imagen original vs render importado y puntuar fidelidad/editabilidad | `google/gemini-2.5-flash` | `google/gemini-2.5-pro` | `claude-sonnet-4.5`, `google/gemini-3.1-pro-preview`, `openai/gpt-5.1` | Usar juez premium offline/en calibración, no en cada importación de usuario |

### Recomendación inicial por modo de producto

| Modo | Pipeline | Coste | Fidelidad | Cuándo usar |
|---|---|---:|---:|---|
| Rápido/barato | `qwen3-vl-30b` → `SmartImportCompiler` | Bajo | Media | Importaciones simples, fondos limpios, muchos usuarios |
| Equilibrado | `gemini-2.5-flash` → `SmartImportCompiler` | Medio-bajo | Alta | Default recomendado |
| Equilibrado + restauración | `gemini-2.5-flash` → máscara determinista → `gemini-2.5-flash-image` → compiler | Medio | Alta si la oclusión es moderada | Foto parcialmente tapada por texto |
| Alta fidelidad | `gemini-2.5-pro` → `gemini-3-pro-image-preview` → compiler → juez premium | Alto | Máxima | Importaciones complejas o modo pago |
| Calibración interna | varios candidatos → compiler → render app → juez premium | Alto pero offline | Mide eficacia real | Benchmark, no usuario final |

### Recomendación inicial

| Fase | Modelo recomendado | Por qué |
|---|---|---|
| Prompt A visión, MVP | `google/gemini-2.5-flash` | Está alineado con lo que usa Stitch conceptualmente: Gemini multimodal, buen coste/calidad |
| Prompt A visión, barato | `qwen/qwen3-vl-30b-a3b-instruct` o `mistralai/mistral-small-3.2-24b-instruct` | Coste muy bajo; hay que validar OCR/layout |
| Prompt A visión, máxima fidelidad | `google/gemini-2.5-pro` | Mejor para composición compleja, jerarquía visual y razonamiento multimodal |
| Prompt B traducción | `google/gemini-2.5-flash-lite` o `openai/gpt-5-mini` | Ya no necesita visión; necesita obedecer schema y generar JSON |
| Producción robusta | Prompt B sustituido por `SmartImportCompiler` | Menos coste y más determinismo |

### Modo recomendado para V1

| Submodo | Qué hace | Nota |
|---|---|---|
| `text_only` | Extrae solo textos editables y deja la imagen original como fondo | Debe ser el primer submodo a lanzar |
| `basic_image_layers` | Además detecta una foto principal y la inserta como recorte rectangular | Solo con confianza alta |
| `advanced_restoration` | Usa inpainting/repainting para zonas ocluidas | V2, no MVP |

### Por qué NO usar solo un modelo

Porque son dos problemas distintos:

- Ver y describir una imagen requiere percepción multimodal.
- Generar `.tc` válido requiere obedecer un contrato interno.

Mezclarlos en un prompt único aumenta errores: textos inventados, coordenadas inconsistentes, campos fuera del schema, assets imposibles, etc.

---

## 7. Estrategia de extracción de imágenes/fotos

El modelo puede detectar una región:

```json
{
  "kind": "image",
  "bbox": { "x": 250, "y": 300, "w": 580, "h": 520 },
  "description": "fotografía de una persona",
  "cropFromSource": true
}
```

Pero el modelo NO debe crear el asset. La app debe:

1. abrir la imagen original;
2. recortar el bbox;
3. guardar como data URI o `DesignAsset`;
4. crear:

```json
{
  "customElements": {
    "smart-image-1": {
      "id": "smart-image-1",
      "type": "image",
      "label": "Fotografía importada",
      "src": "data:image/png;base64,...",
      "intrinsicWidth": 580,
      "intrinsicHeight": 520,
      "uploadStatus": "pending",
      "needsUpload": true
    }
  },
  "elementLayout": {
    "smart-image-1": {
      "x": 250,
      "y": 300,
      "w": 580,
      "h": 520,
      "zIndex": 20,
      "borderRadius": 24,
      "opacity": 100,
      "imageCropScale": 1,
      "imageCropOffsetX": 0,
      "imageCropOffsetY": 0
    }
  }
}
```

Para el primer MVP, si la imagen es compleja, lo más sólido es:

- usar la imagen original completa como fondo;
- extraer textos editables encima;
- recortar fotos solo con confianza alta.

Esto no es un atajo flojo. Es la base que evita prometer “Photoshop automático” cuando aún no tenemos segmentación fiable.

---

## 8. Evaluación necesaria antes de implementar

Crear un benchmark propio con 10-20 imágenes:

1. cartel simple: fondo plano + título + foto;
2. cartel con degradado;
3. flyer con 5-8 bloques de texto;
4. post cuadrado con persona;
5. banner horizontal;
6. imagen con tipografía display;
7. imagen con bajo contraste;
8. imagen con varios logos/iconos;
9. diseño con bloques translúcidos;
10. diseño con texto rotado o decorativo.

Medir:

- OCR exacto;
- error medio de bbox;
- color aproximado;
- cantidad de capas útiles;
- JSON válido;
- `.tc` importable;
- tiempo;
- coste real reportado por OpenRouter;
- satisfacción visual tras abrir en editor.

Métrica práctica:

| Métrica | Umbral MVP |
|---|---:|
| JSON SceneGraph válido | > 95% |
| `.tc` importable | 100% |
| Texto principal detectado | > 90% |
| BBox texto con error tolerable | > 75% |
| Colores razonables | > 70% |
| Capas inútiles | < 20% |
| Coste por importación equilibrada | < $0.03 |

### Evaluación automática con modelo juez

Para calibrar el pipeline no basta con comprobar que el `.tc` sea válido. Necesitamos evaluar si el diseño importado **se parece al original** y si además es **editable de forma útil**.

Pipeline de evaluación:

```text
Imagen fixture original
  ▼
Pipeline de importación
  ├─ SceneGraph
  ├─ assets recortados/restaurados
  └─ .tc generado
  ▼
Tseyor Canva
  ├─ importa .tc
  └─ renderiza screenshot del diseño resultante
  ▼
Modelo juez multimodal
  ├─ compara original vs screenshot importado
  ├─ inspecciona SceneGraph y .tc
  └─ devuelve score + errores accionables
```

Entradas del juez:

1. imagen original;
2. screenshot renderizado por la app después de importar el `.tc`;
3. `SceneGraph` generado;
4. resumen del `.tc` generado: número de capas, tipos, bboxes, fuentes, assets reconstruidos;
5. opcionalmente, crop/restauración de fotos si hubo inpainting.

Salida esperada:

```json
{
  "overallScore": 0.82,
  "visualSimilarity": 0.78,
  "textAccuracy": 0.94,
  "layoutAccuracy": 0.81,
  "colorAccuracy": 0.74,
  "photoLayerQuality": 0.70,
  "editability": 0.86,
  "tcValidity": true,
  "criticalIssues": [
    "El bloque de título está 40px demasiado alto.",
    "La fotografía restaurada conserva artefactos cerca del borde izquierdo."
  ],
  "recommendations": [
    "Aumentar padding de máscara de texto de 8px a 14px.",
    "Usar modelo de inpainting premium cuando occlusionAreaPct > 12."
  ]
}
```

Modelos juez recomendados:

| Uso | Modelo juez | Motivo | Coste |
|---|---|---|---:|
| Evaluación barata en desarrollo | `google/gemini-2.5-flash` | Multimodal, rápido, coste razonable | Medio-bajo |
| Evaluación default de benchmark | `google/gemini-2.5-pro` | Mejor razonamiento visual y comparación compleja | Medio-alto |
| Evaluación adversarial premium | `anthropic/claude-sonnet-4.5` o `openai/gpt-5.1` | Buen razonamiento y crítica estructurada | Alto |
| Evaluación experimental | `google/gemini-3.1-pro-preview` | Candidato premium multimodal según disponibilidad | Alto |

Regla de coste:

- No ejecutar juez premium en cada importación de usuario.
- Usarlo en benchmarks, CI nocturno, calibración de prompts y comparación de modelos.
- En producción, usar juez barato solo si el usuario pide “mejorar fidelidad” o si el pipeline detecta baja confianza.

### Juez offline, no online

El juez multimodal debe quedar fuera del flujo interactivo del usuario. Su lugar correcto es:

- CI nocturno;
- calibración de prompts;
- comparación de candidatos;
- regresión visual entre versiones del pipeline.

No debe correr por cada importación. Si lo haces online:

- sube el coste;
- sube la latencia;
- y el usuario no obtiene un beneficio proporcional.

Métricas de benchmark por modelo:

| Métrica | Qué mide |
|---|---|
| `scene_valid_rate` | Porcentaje de SceneGraph JSON válido |
| `tc_import_rate` | Porcentaje de `.tc` que abre sin errores |
| `text_ocr_score` | Exactitud del texto detectado |
| `bbox_iou_text` | Solapamiento entre bbox detectado y ubicación real del texto |
| `photo_crop_score` | Calidad del recorte/restauración de fotos |
| `visual_similarity_score` | Parecido global original vs render importado |
| `editability_score` | Si los elementos importantes son capas editables |
| `cost_per_successful_import` | Coste real dividido por importaciones aceptables |
| `latency_p95` | Tiempo p95 de importación |

La métrica más importante no es “parecido visual” aislado. Es:

```text
utilidad = fidelidad visual × editabilidad × coste aceptable
```

Un diseño 95% parecido pero con todo aplanado como imagen NO cumple el objetivo. Y un diseño 100% editable pero visualmente roto tampoco.

---

## 9. Decisión arquitectónica revisada

La arquitectura correcta para Tseyor Canva es:

```text
Imagen → SceneGraph IA → Validación → Compilación .tc → Preview editable
```

No:

```text
Imagen → IA → .tc directo → editor
```

La segunda opción parece más rápida, pero es una trampa. Cuando falle, no sabremos si falló OCR, razonamiento visual, traducción, contrato `.tc` o validación.

---

## 10. Plan de implementación recomendado

### Paso 1 — Investigación experimental

- Crear script local que llame OpenRouter con 3 modelos:
  - `google/gemini-2.5-flash`
  - `qwen/qwen3-vl-30b-a3b-instruct`
  - `google/gemini-2.5-pro`
- Usar 5 imágenes fixture.
- Guardar salidas `scene.json`.
- Comparar manualmente.
- Antes de fijar modelo por defecto, hacer benchmark con 10-15 imágenes propias del dominio real de la app.

### Paso 1.1 — Caché por hash desde el día uno

Antes de escalar a producción, el pipeline debe calcular un hash SHA-256 de la imagen y cachear:

- SceneGraph generado;
- máscara de oclusión;
- crop/asset restaurado;
- `.tc` compilado;
- score del juez, si aplica.

Objetivo:

- evitar llamadas repetidas a la API si la misma imagen se reimporta;
- reducir coste en producción;
- acelerar el reintento del usuario.

Clave recomendada:

```text
smart-import:{sha256}:{pipelineVersion}:{modelId}
```

Eso permite invalidar cuando cambie:

- el prompt;
- el compilador;
- el modelo;
- la lógica de máscara;
- el contrato `.tc`.

### Paso 2 — Schema y validador

- Definir `SmartImportScene.schema.json`.
- Validar respuesta del modelo.
- Reparar JSON solo si es parseable y seguro.

### Paso 3 — Compilador SceneGraph → `.tc`

- Implementar sin IA.
- Tests unitarios contra fixtures.
- Confirmar que todo `.tc` generado abre en editor.

### Paso 4 — UI de importación

- Botón “Importar desde imagen”.
- Selector de modo:
  - rápido;
  - equilibrado;
  - alta fidelidad.
- Preview antes de aplicar.

### Paso 5 — Optimización

- Guardar coste real por importación.
- Cachear análisis por hash de imagen.
- Permitir regenerar solo una fase:
  - reanalizar imagen;
  - recompilar `.tc`;
  - ajustar prompts.

---

## Conclusión

Tu planteamiento de dos pasos es el correcto:

1. **modelo visión**: “dime qué ves, dónde está, qué color/tamaño/fuente parece tener, qué imágenes/formas/fondos hay”;
2. **modelo o compilador**: “convierte esa descripción al formato `.tc` de Tseyor Canva”.

Eso se parece mucho más al enfoque técnico que se puede inferir de Stitch: entrada multimodal, representación editable intermedia, exportadores a formatos concretos.

Recomendación práctica:

- empezar con `google/gemini-2.5-flash` para Prompt A;
- comparar contra `qwen/qwen3-vl-30b-a3b-instruct` por coste;
- usar `google/gemini-2.5-flash-lite` o un compilador determinista para Prompt B;
- reservar `google/gemini-2.5-pro` para modo “alta fidelidad”.

La prueba de fuego NO será que el JSON “se vea bonito”. La prueba de fuego será que el `.tc` generado abra en Tseyor Canva, tenga capas editables útiles y permita al usuario terminar el diseño más rápido que haciéndolo desde cero.
