# Visual Review V2 — 3-Format Comparison (3-Prompt System + Normalized Coords)

V2 usa **3 prompts secuenciales** (composición → texto → imágenes/formas) con
**coordenadas normalizadas 0..1** y schema aplanado con categorías cerradas.

Modelo: `google/gemini-2.5-flash` para las 11 imágenes.

| Imagen | Original | SceneGraph V2 (assembly) | SVG V2 | HTML V2 |
|--------|----------|--------------------------|--------|---------|
| banner-horizontal | ![original](dataset/banner-horizontal.jpg) | [assembly.json](output/google-gemini-2-5-flash/scenegraph-v2/banner-horizontal/assembly.json) | ![svg-v2](output/google-gemini-2-5-flash/svg-v2/banner-horizontal/render.png) | ![html-v2](output/google-gemini-2-5-flash/html-v2/banner-horizontal/render.png) |
| flyer-text-heavy | ![original](dataset/flyer-text-heavy.jpg) | [assembly.json](output/google-gemini-2-5-flash/scenegraph-v2/flyer-text-heavy/assembly.json) | ![svg-v2](output/google-gemini-2-5-flash/svg-v2/flyer-text-heavy/render.png) | ![html-v2](output/google-gemini-2-5-flash/html-v2/flyer-text-heavy/render.png) |
| meditacion_11_julio_vertical_completo | ![original](dataset/meditacion_11_julio_vertical_completo.jpg) | [assembly.json](output/google-gemini-2-5-flash/scenegraph-v2/meditacion_11_julio_vertical_completo/assembly.json) | ![svg-v2](output/google-gemini-2-5-flash/svg-v2/meditacion_11_julio_vertical_completo/render.png) | ![html-v2](output/google-gemini-2-5-flash/html-v2/meditacion_11_julio_vertical_completo/render.png) |
| multi-photo-collage | ![original](dataset/multi-photo-collage.jpg) | [assembly.json](output/google-gemini-2-5-flash/scenegraph-v2/multi-photo-collage/assembly.json) | ![svg-v2](output/google-gemini-2-5-flash/svg-v2/multi-photo-collage/render.png) | ![html-v2](output/google-gemini-2-5-flash/html-v2/multi-photo-collage/render.png) |
| portrait-overlay | ![original](dataset/portrait-overlay.jpg) | [assembly.json](output/google-gemini-2-5-flash/scenegraph-v2/portrait-overlay/assembly.json) | ![svg-v2](output/google-gemini-2-5-flash/svg-v2/portrait-overlay/render.png) | ![html-v2](output/google-gemini-2-5-flash/html-v2/portrait-overlay/render.png) |
| poster-display-font | ![original](dataset/poster-display-font.jpg) | [assembly.json](output/google-gemini-2-5-flash/scenegraph-v2/poster-display-font/assembly.json) | ![svg-v2](output/google-gemini-2-5-flash/svg-v2/poster-display-font/render.png) | ![html-v2](output/google-gemini-2-5-flash/html-v2/poster-display-font/render.png) |
| poster-gradient | ![original](dataset/poster-gradient.jpg) | [assembly.json](output/google-gemini-2-5-flash/scenegraph-v2/poster-gradient/assembly.json) | ![svg-v2](output/google-gemini-2-5-flash/svg-v2/poster-gradient/render.png) | ![html-v2](output/google-gemini-2-5-flash/html-v2/poster-gradient/render.png) |
| poster-low-contrast | ![original](dataset/poster-low-contrast.jpg) | [assembly.json](output/google-gemini-2-5-flash/scenegraph-v2/poster-low-contrast/assembly.json) | ![svg-v2](output/google-gemini-2-5-flash/svg-v2/poster-low-contrast/render.png) | ![html-v2](output/google-gemini-2-5-flash/html-v2/poster-low-contrast/render.png) |
| poster-person | ![original](dataset/poster-person.jpg) | [assembly.json](output/google-gemini-2-5-flash/scenegraph-v2/poster-person/assembly.json) | ![svg-v2](output/google-gemini-2-5-flash/svg-v2/poster-person/render.png) | ![html-v2](output/google-gemini-2-5-flash/html-v2/poster-person/render.png) |
| poster-simple | ![original](dataset/poster-simple.jpg) | [assembly.json](output/google-gemini-2-5-flash/scenegraph-v2/poster-simple/assembly.json) | ![svg-v2](output/google-gemini-2-5-flash/svg-v2/poster-simple/render.png) | ![html-v2](output/google-gemini-2-5-flash/html-v2/poster-simple/render.png) |
| showcase-two-products | ![original](dataset/showcase-two-products.jpg) | [assembly.json](output/google-gemini-2-5-flash/scenegraph-v2/showcase-two-products/assembly.json) | ![svg-v2](output/google-gemini-2-5-flash/svg-v2/showcase-two-products/render.png) | ![html-v2](output/google-gemini-2-5-flash/html-v2/showcase-two-products/render.png) |

## Estructura de archivos V2 (por imagen)

```
output/<model>/<formato>-v2/<imagen>/
├── prompt-1-composition.json   # Composición espacial (regiones)
├── prompt-2-text.json          # Textos extraídos
├── prompt-3-shapes.json        # Imágenes y formas
├── assembly.json               # Fusión de los 3 prompts
├── output.<ext>                # Formato final (JSON / SVG / HTML)
└── render.png                  # Render (solo SVG y HTML)
```

> SceneGraph V2 no tiene render propio porque necesita compilación a .tc.
> Para ver los renders SVG y HTML, abre este archivo con Markdown Preview en VS Code.

<style>
table img { max-width: 160px; max-height: 130px; object-fit: contain; }
</style>
