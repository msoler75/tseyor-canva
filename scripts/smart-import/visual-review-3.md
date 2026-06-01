# Visual Review V3 — Qwen3-VL Detection (Single Prompt + Pixel Coords + Image Crops)

Modelo: `qwen/qwen3-vl-32b-instruct` (OpenRouter).
Todos los elementos detectados con un solo prompt, coordenadas en píxeles, extracción de regiones de imagen con Pillow, compilación a `.tc` con `SmartImportCompiler`.

Base path: `scripts/smart-import/`

| Imagen | Original | V1 Gemini SVG | V2 Gemini SVG | V3 Qwen Render | Notas |
|--------|----------|---------------|---------------|----------------|-------|
| **banner-horizontal** | ![original](dataset/banner-horizontal.jpg) | ![v1-svg](output/google-gemini-2-5-flash/svg/banner-horizontal/render.png) | ![v2-svg](output/google-gemini-2-5-flash/svg-v2/banner-horizontal/render.png) | ![v3-qwen](output/qwen-qwen3-vl-32b-instruct/v3/banner-horizontal/render.png) | Canvas 1920×1080. **6 textos**: "SALE", "UP TO 50% OFF", "Limited time · Select items", "SHOP NOW →", "NEW ARRIVAL", "Premium Collection" — todos correctos. **1 imagen**: Golden Gate Bridge (1420×1080, crop de source). Background split naranja+imagen. Shapes: badge amarillo "NEW ARRIVAL", botón azul "SHOP NOW". Detección completa y precisa. |
| **flyer-text-heavy** | ![original](dataset/flyer-text-heavy.jpg) | ![v1-svg](output/google-gemini-2-5-flash/svg/flyer-text-heavy/render.png) | ![v2-svg](output/google-gemini-2-5-flash/svg-v2/flyer-text-heavy/render.png) | ![v3-qwen](output/qwen-qwen3-vl-32b-instruct/v3/flyer-text-heavy/render.png) | Canvas 1024×1366. **9 textos**: "COMMUNITY MEETUP", "Tech & Innovation Summit 2026", fecha, venue, hora, 3 talks, CTA "Free entry · Register now!". **0 imágenes** (correcto, es texto puro con formas decorativas). **3 shapes**: círculos translúcidos decorativos. Background gradient dark purple→dark blue. |
| **meditacion_11_julio_vertical_completo** | ![original](dataset/meditacion_11_julio_vertical_completo.jpg) | ![v1-svg](output/google-gemini-2-5-flash/svg/meditacion_11_julio_vertical_completo/render.png) | ![v2-svg](output/google-gemini-2-5-flash/svg-v2/meditacion_11_julio_vertical_completo/render.png) | ![v3-qwen](output/qwen-qwen3-vl-32b-instruct/v3/meditacion_11_julio_vertical_completo/render.png) | Canvas 999×1500. **17 textos** — el dataset más complejo. Todos los textos del cartel TSEYOR detectados: "Mundo Armónico TSEYOR Chile", "ONG sin ánimo de lucro", "Meditación para la sanación del planeta Tierra", fecha/hora/lugar, "Biblioteca de libre descarga", "TSEYOR.org", "Actividad libre y gratuita", "¡Súmate espontáneamente al pasar!", y 3 tags. **2 imágenes**: foto grupal meditando (999×450) + QR (100×100). **6 shapes**: rectángulos fondo azul claro. Colores precisos (#003366, #0066cc). |
| **multi-photo-collage** | ![original](dataset/multi-photo-collage.jpg) | ![v1-svg](output/google-gemini-2-5-flash/svg/multi-photo-collage/render.png) | ![v2-svg](output/google-gemini-2-5-flash/svg-v2/multi-photo-collage/render.png) | ![v3-qwen](output/qwen-qwen3-vl-32b-instruct/v3/multi-photo-collage/render.png) | Canvas 1000×1300. **3 textos**: "PHOTO COLLAGE", "Multi-image recognition test", labels. **3 imágenes**: Foto A (bosque, 550×550), Foto B (cañón, 500×450), Foto C (cielo estrellado, 400×400) — las 3 detectadas y croped con overlap correcto. **Punto fuerte**: detección de múltiples imágenes con overlaps. |
| **portrait-overlay** | ![original](dataset/portrait-overlay.jpg) | ![v1-svg](output/google-gemini-2-5-flash/svg/portrait-overlay/render.png) | ![v2-svg](output/google-gemini-2-5-flash/svg-v2/portrait-overlay/render.png) | ![v3-qwen](output/qwen-qwen3-vl-32b-instruct/v3/portrait-overlay/render.png) | Canvas 1024×1366. **2 textos**: "PORTRAIT STUDY" (título), "Transparency · Overlay · Face detection". **1 imagen**: mujer de espaldas frente a un tren (860×748, crop). **1 shape**: rectángulo blanco semitransparente (opacity 0.3) para overlay diagonal. Background gradient purple→pink. |
| **poster-display-font** | ![original](dataset/poster-display-font.jpg) | ![v1-svg](output/google-gemini-2-5-flash/svg/poster-display-font/render.png) | ![v2-svg](output/google-gemini-2-5-flash/svg-v2/poster-display-font/render.png) | ![v3-qwen](output/qwen-qwen3-vl-32b-instruct/v3/poster-display-font/render.png) | Canvas 1024×1366. **2 textos**: "DREAM" (grande, central), "BIG · BOLD · BEAUTIFUL". **1 imagen**: fondo full-canvas con desenfoque B/N y círculos dorados (1024×1366). **5 shapes**: líneas horizontales decorativas doradas (#D4AF37). |
| **poster-gradient** | ![original](dataset/poster-gradient.jpg) | ![v1-svg](output/google-gemini-2-5-flash/svg/poster-gradient/render.png) | ![v2-svg](output/google-gemini-2-5-flash/svg-v2/poster-gradient/render.png) | ![v3-qwen](output/qwen-qwen3-vl-32b-instruct/v3/poster-gradient/render.png) | Canvas 1000×1333. **4 textos**: "NEW COLLECTION", "Spring 2026 · Limited Edition", "EXCLUSIVE", "SHOP NOW →". **1 imagen**: foto arquitectura formato circular (450×450). **1 shape**: máscara circular blanca. Background gradient purple→pink. |
| **poster-low-contrast** | ![original](dataset/poster-low-contrast.jpg) | ![v1-svg](output/google-gemini-2-5-flash/svg/poster-low-contrast/render.png) | ![v2-svg](output/google-gemini-2-5-flash/svg-v2/poster-low-contrast/render.png) | ![v3-qwen](output/qwen-qwen3-vl-32b-instruct/v3/poster-low-contrast/render.png) | Canvas 1000×1300. **5 textos**: "Whisper Collection", "barely visible elegance", párrafo, "— Design Philosophy, 2026", "www.whisper-design.studio". **0 imágenes**. **1 shape**: línea horizontal. Background #f5f5f5, textos en #d9d9d9. **Logro**: Qwen detectó texto de bajo contraste que otros modelos pierden. |
| **poster-person** | ![original](dataset/poster-person.jpg) | ![v1-svg](output/google-gemini-2-5-flash/svg/poster-person/render.png) | ![v2-svg](output/google-gemini-2-5-flash/svg-v2/poster-person/render.png) | ![v3-qwen](output/qwen-qwen3-vl-32b-instruct/v3/poster-person/render.png) | Canvas 1000×1000 (cuadrado). **3 textos**: "FEATURED", "JANE DOE", "@janedoe • 12k followers". **1 imagen**: foto circular de perfil (460×460, atardecer, silueta). **3 shapes**: círculos decorativos verde oscuro. Background gradient #008080 (teal). |
| **poster-simple** | ![original](dataset/poster-simple.jpg) | ![v1-svg](output/google-gemini-2-5-flash/svg/poster-simple/render.png) | ![v2-svg](output/google-gemini-2-5-flash/svg-v2/poster-simple/render.png) | ![v3-qwen](output/qwen-qwen3-vl-32b-instruct/v3/poster-simple/render.png) | Canvas 1024×1366. **4 textos**: "SUMMER FEST", "AUGUST 15-17 · CENTRAL PARK", "NOW ON SALE", "Main Stage · Live Music". **1 imagen**: paisaje cañón atardecer (884×884, crop). **1 shape**: overlay negro semitransparente para legibilidad. Background azul (#1A2A80). |
| **showcase-two-products** | ![original](dataset/showcase-two-products.jpg) | ![v1-svg](output/google-gemini-2-5-flash/svg/showcase-two-products/render.png) | ![v2-svg](output/google-gemini-2-5-flash/svg-v2/showcase-two-products/render.png) | ![v3-qwen](output/qwen-qwen3-vl-32b-instruct/v3/showcase-two-products/render.png) | Canvas 1000×1300. **7 textos**: "DUO COLLECTION", "CLASSIC" / "$49.99", "MODERN" / "$79.99", "-30%" badge, "SHOP THE DUO · FREE SHIPPING". **2 imágenes**: flor amarilla (circular, 420×420) + acantilado marino (420×420). **3 shapes**: info boxes grises + footer azul (#3a4a8d). |

---

## Key Improvements in V3

### 1. Single prompt detection
**Qwen3-VL** detecta texto, imágenes y formas en **una sola llamada** con un prompt unificado. V1 y V2 requerían 3 prompts separados (texto, imagen, color/estructura), lo que duplicaba latencia y coste.

### 2. Natural pixel coordinates
Qwen3-VL recibe la imagen a su resolución nativa y **estima coordenadas naturales en píxeles**. No requiere normalización forzada como V1/V2 que pedían coordenadas 0‑1 para después escalar. Las coordenadas son más intuitivas y consistentes con el espacio real del diseño.

### 3. Real image cropping with Pillow
Las imágenes detectadas se **extraen físicamente** de la fuente original con `PIL.Image.crop()` usando las coordenadas (x, y, w, h) devueltas por Qwen. En V1/V2, las imágenes se perdían o se insertaban con descripciones textuales; en V3 se conservan como `cropFromSource=true` y se compilan directamente al `.tc`.

### 4. Direct SmartImportCompiler (no subprocess)
El pipeline V3 llama al **compilador Python directamente** (`SmartImportCompiler().compile(data)`), eliminando el frágil subprocess de V2 que provocaba errores de serialización, encoding y path resolution. Más rápido y robusto.

### 5. Canvas scaling from OpenCV
Qwen estima el canvas ideal en píxeles, y **OpenCV confirma las dimensiones reales** de la imagen fuente. Si hay discrepancia, se escala proporcionalmente manteniendo aspect ratio. V1/V2 asumían dimensiones arbitrarias.

### Summary Metrics (11 imágenes)

| Aspecto | V1 Gemini SVG | V2 Gemini SVG | V3 Qwen-Qwen3-VL |
|---------|--------------|---------------|------------------|
| Prompts por imagen | 3 (secuenciales) | 3 (secuenciales) | **1** |
| Coordenadas | Normalizadas (0‑1) | Normalizadas (0‑1) | **Píxeles naturales** |
| Crop de imágenes | ❌ No | ❌ No | ✅ **Sí (Pillow)** |
| Compilación | SVG manual | Subprocess frágil | **API directa** |
| Escalado canvas | Fijo | Fijo | **OpenCV dinámico** |
| Texto bajo contraste | ❌ Falla | ⚠️ Parcial | ✅ **Detecta** |
| Múltiples imágenes | ❌ Falla | ⚠️ Inconsistente | ✅ **3/3 collage OK** |
| Latencia total | Alta (3 rondas) | Alta (3 rondas) | **1 ronda** |

<style>
table img { max-width: 160px; max-height: 130px; object-fit: contain; }
</style>
