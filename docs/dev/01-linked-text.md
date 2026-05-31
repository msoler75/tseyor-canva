# Sistema de Texto Enlazable — Documentación Técnica

(Fuente original: `TEXTO_ENLAZABLE_TECNICA.md`)

## Arquitectura: Single Source, Multiple Viewports

Una única fuente de verdad (fullHtml) con múltiples viewports (cajas enlazables). Análogo al flujo de texto de Word entre páginas.

```
Texto fuente único → Caja 1 → Caja 2 → Caja 3 → overflow
```

### Componentes

| Archivo | Rol |
|---------|-----|
| `useLinkedTextBoxSystem.js` | Motor de fragmentación: parsea HTML, mide en DOM real, redistribuye |
| `useLinkedTextFlow.js` | Gestor alternativo basado en Canvas (no usado en flujo principal) |
| `RichTextEditor.vue` | Renderiza cada caja con su fragmento y gestiona TipTap |

## Fragment Properties

Cada caja recibe un fragmento calculado por `redistribute()`:

| Propiedad | Descripción |
|-----------|-------------|
| `html` → `displayHtml` | HTML del texto que cabe en esta caja |
| `overflowHtml` | HTML del texto que no cabe en ninguna caja (solo última) |
| `fullTextHtml` | HTML completo del texto fuente (idéntico para todas las cajas) |
| `tailHtml` | HTML desde inicio de esta caja hasta el final |
| `editorTextOffset` | Número de caracteres antes del contenido de esta caja |
| `fitsInBox` | Booleano: true si todo el texto cabe en la cadena |

## Algoritmo de Split (Fragmentación)

Búsqueda binaria con medición real del DOM del navegador:

1. Parsear fullHtml en párrafos con estilos
2. Aplanar en unidades (palabras, signos, espacios, párrafos vacíos)
3. Para cada caja, búsqueda binaria midiendo `offsetHeight` en div de medición
4. Complejidad O(log n) — 10-14 iteraciones para 1K-10K unidades

## Sistema de 2 Capas (visual)

- **Capa base** (`linked-text-base-layer`): overflowHtml, gris 45% opacidad (eliminada visualmente, datos preservados)
- **Capa display** (`linked-text-display`): displayHtml, color normal, overflow:hidden cuando inactivo

## Redistribución

Se dispara al: commitTextEdit, redimensionar caja, conectar/desconectar enlace.

Flujo: fullHtml → parseHtmlIntoParagraphs → allUnits → búsqueda binaria por caja → fragmentos

## Robustez

- **Eliminación**: `removeLinkedTextFromChain` repara enlaces automáticamente; head hereda html/text
- **Rotura de enlace**: arrastrar flecha al vacío → tailHtml se asigna como nuevo head
- **Re-enlazado**: arrastrar flecha A→B rompe enlaces previos, unifica groupId, recalcula
- **Clonación**: ver sección de clonación en docs/user/04-texto-enlazable.md
- **Undo/Redo**: `resetAllSystems()` antes de restaurar estado, fragmentos se recalculan

## Preservación de estilos

`mergeParagraphStylesIntoHtml` fusiona (no reemplaza) estilos del layout con inline existentes. Propiedades del HTML pegado tienen prioridad sobre layout.

### Styled spans en texto overflow

**Problema**: `Range.cloneContents()` NO preserva el `<span>` padre cuando el text node está completamente seleccionado (`startOffset=0`, `endOffset=textContent.length`). Esto causaba pérdida de color (C2) y otros estilos en texto overflow de párrafos con estilos por carácter.

**Solución en `extractStyledSlice`**: detectar cuándo `cloneContents()` pierde el span padre comparando `clone.childNodes.length` vs `1`. Si perdió el span, construir el HTML desde `startParent.outerHTML` en vez del clone.

**Solución en `sliceInnerHtml`/`assignRichHtmlToFragments`**: mismo patrón — usar `cloneNode(true)` del párrafo original cuando `cloneContents()` devuelve solo texto plano sin span.

### Propagación de marks carácter a carácter

`buildHtmlFromUnitSlice` reconstruye el HTML de un slice de unidades preservando TODOS los styled spans originales del párrafo fuente. Cada unidad (palabra, espacio, signo) mantiene su span wrapper original con estilos inline completos.

Fixes relacionados:
- `672526d`: marks de styledText se preservan en toda la cadena linked (texto normal + enlazado)
- `5963770`: cambios de estilo (color, bold, italic) durante Ctrl+A select-all se propagan a todas las cajas linked

## Sincronización con Canvas

Canvas/export renderer (html-2-image) usa la propiedad `html` del elemento, NO `fragment.html` del sistema de texto. Por tanto:

### Element field sync

En `recalculateLinkedTextAllocations`, tras `assignRichHtmlToFragments`, se itera sobre las cajas no-head y se asigna `customElements[boxId].html = fragment.html`. Esto garantiza que el render de canvas tenga el HTML correcto por caja.

### text-align-last en canvas

**Problema**: El renderer de canvas/export NO soporta CSS `text-align-last`. La última línea de un párrafo justificado aparecía alineada a la izquierda en exportación.

**Solución**: En `recalculateLinkedTextAllocations`, tras construir el displayHtml de la caja head, se añade inline `text-align-last:justify` al estilo del párrafo final si está justificado. Detectado por `isSplitJustify()`.

### Font-size mismatch en html-2-image

**Problema** (`251b0d1`): html-2-image aplicaba `style="font-size: Xpx"` con un redondeo que reducía 0.1px el font-size, causando text wrapping distinto entre editor y PDF export.

**Solución**: Eliminar la reducción de 0.1px en el inline style generado por el clon.
