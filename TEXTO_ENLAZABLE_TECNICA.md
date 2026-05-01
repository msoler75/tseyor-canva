# TEXTO_ENLAZABLE_TECNICA.md

## Documentación Técnica del Sistema de Texto Enlazable

---

## 1. Arquitectura General: "Single Source, Multiple Viewports"

El sistema de texto enlazable sigue el principio de **una única fuente de verdad** con **múltiples ventanas de visualización** (viewports). Es análogo al flujo de texto de Microsoft Word a través de páginas: hay un solo documento de texto completo, y cada "caja enlazable" actúa como una ventana que muestra una porción secuencial del mismo.

```
┌─────────────────────────────────────────────────────────────┐
│                  TEXTO FUENTE ÚNICO (fullHtml)              │
│  "Lorem ipsum dolor sit elit,                               │
│   sed do eiusmod tempor dolore magna"                       │
└─────────────────────────────────────────────────────────────┘
         │                    │                   │
    ┌────▼─────┐         ┌────▼────┐         ┌────▼────┐
    │  CAJA 1  │ ──────► │  CAJA 2 │ ──────► │  CAJA 3 │
    │ "Lorem   │         │ "elit,  │         │ "dolore │
    │  ipsum   │         │  sed do │         │  magna" │
    │  dolor   │         │  eiusmod│         │         │
    │  sit"    │         │  tempor"│         │         |
    └──────────┘         └─────────┘         └─────────┘
```

### Componentes del sistema

| Archivo | Rol |
|---|---|
| `useLinkedTextBoxSystem.js` | Motor principal de fragmentación: parsea HTML, mide en DOM real, redistribuye texto entre cajas |
| `useLinkedTextFlow.js` | Gestor alternativo basado en Canvas (no usado actualmente en el flujo principal) |
| `RichTextEditor.vue` | Componente Vue que renderiza cada caja con su fragmento y gestiona el editor TipTap |

---

## 2. Fragment Properties (Propiedades del Fragmento)

Cada caja enlazable recibe un objeto de "fragmento" calculado por la función `redistribute()` en `useLinkedTextBoxSystem.js`. Estas son las propiedades:

### `html` → `displayHtml` (prop en RichTextEditor.vue)

**Definición:** El HTML del fragmento de texto que **cabe** dentro de esta caja específica.

**Cálculo:** Se determina mediante búsqueda binaria sobre unidades (palabras/signos/espacios) midiendo con el navegador (`offsetHeight`). Cada caja recibe exactamente las unidades que caben en su altura disponible.

**Uso:** Se renderiza en la capa superior (`linked-text-display`) del componente. Es lo que el usuario ve como contenido "normal" de la caja.

```
CAJA 1 (h=100px):  "Lorem ipsum dolor sit amet, consectetur"
                   └────────────────────────────────────────┘ ← displayHtml
CAJA 2 (h=100px):  "adipiscing elit, sed do eiusmod tempor"
                   └────────────────────────────────────────┘ ← displayHtml
```

---

### `overflowHtml`

**Definición:** El HTML del texto que **no cabe en ninguna caja** de la cadena.

**Regla clave (línea 450-451 de `useLinkedTextBoxSystem.js`):**
> Solo la **última caja** de la cadena puede tener `overflowHtml`. Las cajas intermedias tienen `overflowHtml: ''` porque el texto que no cabe en ellas fluye a la siguiente caja, no es "overflow" de esa caja.

```javascript
const isLastInChain = !layout.linkedTextNext;
const overflowHtml = isLastInChain ? buildHtmlFromUnitSlice(overflowSlice) : '';
```

**Uso:** Se renderiza en la **capa base** (`linked-text-base-layer`) con opacidad 45% y color gris, como indicador visual de que hay texto que desborda la cadena completa.

---

### `fullTextHtml`

**Definición:** El HTML **completo** de todo el documento de texto (todas las unidades, desde la primera hasta la última). Es idéntico para todas las cajas de una misma cadena.

**Cálculo:** `buildHtmlFromUnitSlice(allUnits)` — incluye TODAS las unidades, sin límite de altura.

**Uso:** Concebido originalmente para la capa base (como "ghost" del texto completo). Actualmente el template usa `overflowHtml` en la capa base (no `fullTextHtml`), pero la propiedad se mantiene disponible para futuros usos.

---

### `editorTopOffset`

**Definición:** Desplazamiento vertical (en píxeles) desde el inicio del texto completo hasta el punto donde **empieza el contenido de esta caja**. Representa cuánto hay que "subir" el editor TipTap para que el texto visible coincida con el fragmento de esta caja.

**Cálculo (`measureEditorTopOffset`, línea 357):**
1. Renderiza el HTML de las unidades **anteriores** a esta caja (`prefixHtml`) en el div de medición
2. Mide `offsetHeight` → altura real del contenido precedente
3. Como refinamiento, inserta un marcador invisible (`<span data-linked-text-flow-marker>`) en la posición exacta del split y mide su `getBoundingClientRect().top` relativo al contenedor
4. Devuelve `max(prefixHeight, markerTop)` en píxeles

**Uso en RichTextEditor.vue:**
- Se aplica como `transform: translateY(-${editorTopOffset}px)` al wrapper cuando está en modo edición (`wrapperStyle`, línea 165)
- Se aplica como `transform: translate3d(0, -${editorTopOffset}px, 0)` al contenido interno del editor (`linkedTextEditorInnerStyle`, línea 187)
- Efecto: el editor TipTap (que contiene el texto completo) se desplaza hacia arriba para que la porción visible corresponda exactamente a esta caja

```
                     editorTopOffset = 0            editorTopOffset = 72px
                          │                                │
    ┌──────────────────┐   │        ┌──────────────────┐   │
    │ Lorem ipsum dolor│   │        │                  │   │
    │ sit amet, consec │   │        │ adipiscing elit, │ ← visible
    │ tetur adipiscing │   │   ─ ─ ─│ sed do eiusmod   │   ─ ─ ─
    │ elit, sed do     │   │        │ tempor incididunt│
    │ eiusmod tempor   │   │  ┌─────┤ ut labore et     │
    │ incididunt ut... │   │  │     │ dolore magna     │
    └──────────────────┘   │  │     └──────────────────┘
                           │  │
                     EDITOR TIPTAK (texto completo)
                     │                       │
                     ├── CAJA 1: translateY(0)
                     └── CAJA 2: translateY(-72px)
```

---

### `editorTextOffset`

**Definición:** Número de caracteres que hay **antes** del contenido de esta caja en el texto fuente completo.

**Cálculo (línea 415-417):**
```javascript
const editorTextOffset = prefixUnits
  .filter((unit) => unit.type === 'word')
  .reduce((total, unit) => total + String(unit.word ?? '').length, 0);
```
Suma la longitud de todas las palabras en las unidades precedentes.

**Uso en RichTextEditor.vue:**
- Se usa para posicionar el cursor de TipTap al iniciar la edición en una caja que no es la primera (`focusAtPosition`, línea 374)
- La función `docPositionFromTextOffset` (línea 351) convierte este offset de caracteres en una posición del documento TipTap (recorriendo los nodos de texto)

```
Texto completo: "Hola mundo, esto es un ejemplo de texto enlazable."
                 └─── 11 chars ──┘└────── 35 chars ────────────┘
                 
CAJA 1: editorTextOffset = 0
CAJA 2: editorTextOffset = 12  (el cursor empieza en "esto es un...")
```

---

### `fitsInBox`

**Definición:** Booleano. `true` **solo si** esta es la última caja de la cadena **Y** todo el texto cabe dentro de la cadena (no hay overflow).

**Cálculo (línea 455):**
```javascript
const fitsInBox = isLastInChain && (unitIdx + fitUnits) >= totalUnits;
```

**Uso:** Indicador de que el sistema de overflow no necesita mostrarse. Si `fitsInBox === true`, significa que no hay texto sobrante.

---

## 3. Props de RichTextEditor.vue

| Prop | Tipo | Default | Descripción |
|---|---|---|---|
| `paragraphStyles` | `Array` | required | Array de objetos de estilo por párrafo (fontSize, color, fontFamily, fontWeight, italic, underline, uppercase, textAlign, letterSpacing, lineHeight) |
| `text` | `String` | required | Texto plano (con `\n` como separadores de línea) |
| `editorClass` | `String` | `''` | Clase CSS adicional para el editor |
| `editorStyle` | `Object` | `{}` | Estilos CSS inline para el editor (fontSize, color, fontFamily, etc.) |
| `colorOverride` | `String` | `null` | Color de override para efecto neón (se aplica a `--neon-override-color`) |
| `transparentFill` | `Boolean` | `false` | Si el texto debe ser transparente (efecto hollow/contorno) |
| `isLinkedText` | `Boolean` | `false` | Si este elemento es de tipo texto enlazable |
| `linkedTextNext` | `String` | `null` | ID de la siguiente caja enlazada en la cadena |
| `boxDimensions` | `Object` | `null` | Dimensiones de la caja `{w, h}` |
| `editable` | `Boolean` | `false` | Si el texto es editable en este momento |
| `displayMode` | `Boolean` | `false` | `true` = modo display/idle (HTML estático), `false` = modo edición (TipTap activo) |
| `displayHtml` | `String` | `''` | HTML del fragmento que cabe en la caja (equivale a la propiedad `html` del fragmento) |
| `overflowHtml` | `String` | `''` | HTML del texto que desborda la cadena (solo en la última caja). Renderizado en la capa base |
| `fullTextHtml` | `String` | `''` | HTML completo del texto fuente (idéntico para todas las cajas de una cadena) |
| `showOverflow` | `Boolean` | `false` | Si se debe mostrar el texto overflow (cadena activa/seleccionada) |
| `linkedTextActive` | `Boolean` | `false` | Si algún elemento de la cadena está seleccionado/activo/edición |
| `editorTopOffset` | `Number` | `0` | Desplazamiento vertical en px para alinear el editor TipTap con el fragmento de esta caja |
| `editorTextOffset` | `Number` | `0` | Offset de caracteres para posicionar el cursor en la posición correcta al editar |

### Eventos emitidos

| Evento | Payload | Cuándo |
|---|---|---|
| `update:text` | `String` | Al editar texto (onUpdate de TipTap) |
| `update:paragraphStyles` | `Array` | Al editar texto o cambiar displayMode |
| `update:html` | `String` | Al editar texto (HTML completo del editor) |
| `selectionChange` | `{ paragraphIndex, selectedIndexes }` | Al cambiar la selección/cursor |
| `blur` | `Event` | Al perder el foco |

### Métodos expuestos (`defineExpose`)

| Método | Parámetros | Descripción |
|---|---|---|
| `applyStyle(field, value)` | `field: String, value: any` | Aplica un estilo a los párrafos seleccionados |
| `applyStyleAll(field, value)` | `field: String, value: any` | Aplica un estilo a todos los párrafos |
| `getActiveAttrs()` | — | Devuelve los atributos del párrafo actual |
| `focusAtEnd()` | — | Mueve el cursor al final del texto |
| `focusAtPosition(pos)` | `pos: Number` | Mueve el cursor a una posición de caracteres |
| `getPlainText()` | — | Devuelve el texto plano del editor |
| `getParagraphStyles()` | — | Devuelve los estilos de párrafo del editor |
| `getHtml()` | — | Devuelve el HTML del editor |
| `applyMarkStyle(markType, attrs)` | `markType: String, attrs: Object` | Aplica un mark (bold, italic, etc.) a la selección |
| `removeMarkStyle(markType)` | `markType: String` | Elimina un mark de la selección |
| `toggleMarkStyle(markType, attrs)` | `markType: String, attrs: Object` | Alterna un mark en la selección |
| `setContentDirect(html)` | `html: String` | Reemplaza el contenido del editor directamente |

---

## 4. Algoritmo de Split (Fragmentación)

### Resumen del enfoque

El sistema decide qué texto cabe en cada caja mediante **búsqueda binaria con medición real del DOM del navegador**.

### Pipeline completo

```
fullHtml (HTML fuente)
    │
    ▼
parseHtmlIntoParagraphs()     ← Convierte HTML en array de párrafos con estilos
    │
    ▼
allUnits[]                    ← Aplana párrafos en unidades (palabras, signos, espacios, párrafos vacíos)
    │                         ← Cada unidad es { type: 'word'|'paragraph', word, paragraphIndex, paragraph }
    │
    ▼
Búsqueda binaria por caja     ← Para cada caja de la cadena, secuencialmente:
    │                           1. Configura div de medición con mismo width, font, etc.
    │                           2. left=0, right=unidades restantes
    │                           3. WHILE left <= right:
    │                              a. mid = floor((left+right)/2)
    │                              b. Renderiza mid unidades en el div de medición
    │                              c. Mide offsetHeight
    │                              d. Si altura <= maxHeight → bestFit = mid, left = mid+1
    │                              e. Si altura > maxHeight  → right = mid-1
    │                           4. visibleSlice = unidades[0..bestFit]
    │                           5. overflowSlice = unidades[bestFit..fin]
    │                           6. Avanza unitIdx += bestFit para la siguiente caja
    │
    ▼
Fragmentos                     ← { html, overflowHtml, fullTextHtml, editorTopOffset, editorTextOffset, fitsInBox }
```

### Tokenización de unidades

El texto no se fragmenta por palabras ingenuamente. Se tokeniza preservando:

| Tipo | Ejemplo | Tokens |
|---|---|---|
| Palabras | `Hola` | `["Hola"]` |
| Signos de puntuación | `,` `!` `?` `...` | `[","]` `["!"]` `["?"]` `["…"]` |
| Espacios | ` ` | `[" "]` |
| Emojis y otros | `🚀` | `["🚀"]` |

Esto permite que signos de puntuación y espacios sean unidades independientes, por lo que el split es **preciso a nivel de carácter** y no rompe palabras.

### Búsqueda binaria

Complejidad: **O(log n)** donde n = número de unidades.

| Unidades | Iteraciones | Tiempo estimado |
|---|---|---|
| 100 | ~7 | ~7ms |
| 1,000 | ~10 | ~10ms |
| 10,000 | ~14 | ~14ms |
| 100,000 | ~17 | ~17ms |

Frente a la búsqueda secuencial O(n), que para 1,000 unidades requeriría ~1,000 renders (~1-2 segundos).

### Div de medición

Se usa un **único div reutilizado** (`#measure`) posicionado fuera de pantalla (`left: -10000px`, `visibility: hidden`):
- Se clonan dinámicamente estilos de fuente (fontSize, fontFamily, lineHeight, letterSpacing, fontWeight, fontStyle, color)
- Se calcula el ancho a partir del elemento real si existe en el DOM, o se usa `layout.w` como fallback
- Se le aplica la clase `.linked-text-display` para heredar estilos CSS del modo display
- **Sin padding** para no alterar el ancho de medición

### Medición del editorTopOffset

Para calcular cuánto desplazar el editor TipTap verticalmente:

1. Se renderiza el HTML de las unidades anteriores a esta caja (`prefixHtml`) → se mide `offsetHeight`
2. Se inserta un marcador invisible (`<span data-linked-text-flow-marker>`) en la posición exacta del split dentro del texto completo
3. Se mide `marker.getBoundingClientRect().top - container.getBoundingClientRect().top`
4. Se toma `max(prefixHeight, markerTop)` como offset definitivo

Esto da la posición en píxeles donde empieza el contenido de la caja dentro del texto completo.

---

## 5. Trucos Visuales: El Sistema de 2 Capas

### El problema

Necesitamos mostrar visualmente al usuario que hay texto que **no cabe** en la cadena de cajas (overflow), pero el texto "normal" debe verse correctamente recortado a la caja.

### La solución: Arquitectura de 2 capas superpuestas

```
┌──────────────────────────────────┐
│  CAJA (contenedor principal)     │
│                                  │
│  ┌────────────────────────────┐  │
│  │ CAPA BASE (z-index: 5)     │  │ ← linked-text-base-layer
│  │ overflowHtml               │  │   Posición: absolute, top:0
│  │ Color: gray                │  │   Opacidad: 0.45
│  │ "texto que sobra..."       │  │   Muestra el overflow como
│  │ "más texto que sobra..."   │  │   "fantasma" gris
│  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │
│  │ CAPA DISPLAY (z-index: 20) │  │ ← linked-text-display
│  │ displayHtml                │  │   Color normal
│  │ "Lorem ipsum dolor sit"    │  │   overflow: hidden (recorta a
│  │ "amet, consectetur"        │  │   la altura de la caja)
│  └────────────────────────────┘  │
│                                  │
└──────────────────────────────────┘
         │
         │ overflow visible fuera de la caja (si está activa)
         ▼
    "adipiscing elit, sed do..."  ← texto gris al 45% continuando
    "eiusmod tempor incididunt"      debajo de la caja
```

### Cómo funciona cada capa

#### Capa base: `.linked-text-base-layer`

```css
.linked-text-base-layer {
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
    pointer-events: auto;
    z-index: 5;
    color: gray !important;
    opacity: 0.45 !important;
    white-space: pre-wrap;
    word-break: break-word;
    overflow-wrap: break-word;
}
```

- **Posicionamiento:** `absolute` dentro del wrapper, en `top: 0, left: 0`
- **Contenido:** `overflowHtml` — el texto que no cabe en la cadena
- **Efecto visual:** Texto gris al 45% de opacidad
- **Truco clave:** Como el `overflowHtml` empieza donde termina el `displayHtml`, el texto gris aparece **debajo** del texto normal, creando la ilusión de que el texto continúa más allá del borde de la caja
- **Condición de visibilidad:** Solo se renderiza si `isLinkedText && showOverflow && fullTextHtml`

#### Capa superior: `.linked-text-display`

```css
.linked-text-display {
    outline: none;
    white-space: pre-wrap;
    word-break: break-word;
    overflow-wrap: break-word;
    cursor: text;
    color: inherit;
    text-shadow: inherit;
    overflow: visible;
    position: relative;
    z-index: 20;
}
```

- **Posicionamiento:** `relative` (flujo normal), `z-index: 20` (por encima de la capa base)
- **Contenido:** `displayHtml` — solo el texto que cabe
- **Comportamiento de overflow:**
  - Cuando la cadena NO está activa: `overflow: hidden` → el texto se recorta limpiamente a la altura de la caja
  - Cuando la cadena SÍ está activa: `overflow: visible` → el texto se ve completo (útil en modo edición)

### Interacción entre capas

```
Estado INACTIVO (nada seleccionado):
┌──────────────────┐
│ Lorem ipsum dolor│ ← displayHtml (visible, recortado)
│ sit amet, consec │
└──────────────────┘
  (overflowHtml invisible)

Estado ACTIVO (elemento seleccionado):
┌──────────────────┐
│ Lorem ipsum dolor│ ← displayHtml (z-index: 20, color normal)
│ sit amet, consec │
└──────────────────┘
│ adipiscing elit, │ ← overflowHtml (z-index: 5, gray 45%)
│ sed do eiusmod   │   El texto gris "fantasma" aparece debajo
│ tempor incididunt│   indicando que hay más contenido
```

### Modo edición: El truco del Viewport

Cuando el usuario edita una caja que **no es la primera**, el editor TipTap contiene TODO el texto, pero solo debe verse la porción de esa caja:

```
┌────────── Editor Viewport ──────────┐
│ overflow: hidden (recorta a la caja)│
│                                     │
│  ┌─── Editor Content ────────────┐  │
│  │ translateY(-editorTopOffset)  │  │
│  │                               │  │
│  │ "Lorem ipsum dolor sit amet,  │  │ ← Oculto (fuera del viewport)
│  │  consectetur adipiscing elit, │  │ ← Oculto
│  │  ──────────────────────────── │  │ ← Borde del viewport
│  │  sed do eiusmod tempor        │  │ ← VISIBLE (dentro del viewport)
│  │  incididunt ut labore et      │  │ ← VISIBLE
│  │  dolore magna aliqua."        │  │ ← VISIBLE
│  │  ──────────────────────────── │  │ ← Borde del viewport
│  │  Ut enim ad minim veniam...   │  │ ← Oculto
│  └───────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘
```

- **`linked-text-editor-viewport`**: Contenedor con `overflow: hidden` y dimensiones de la caja
- **`linked-text-editor-content`**: Contenedor interno con `transform: translateY(-editorTopOffset)` que desplaza el editor hacia arriba
- **Efecto:** Solo la porción de texto que corresponde a esta caja es visible en el viewport

---

## 6. CSS Classes de Referencia

| Clase | Propósito |
|---|---|
| `.linked-text-base-layer` | Capa inferior: renderiza `overflowHtml` en gris al 45% como indicador de overflow |
| `.linked-text-display` | Capa superior en modo display: renderiza `displayHtml` con estilos normales |
| `.linked-text-display-mode` | Clase del wrapper en modo display (idle) |
| `.linked-text-clipped` | Subclase de display cuando la cadena NO está activa: aplica `overflow: hidden` |
| `.linked-text-active` | Clase del wrapper cuando la cadena está activa/seleccionada |
| `.linked-text-overflow` | Estilo para contenedor de overflow (position absolute, top 100%, opacity 0.5) |
| `.linked-text-editor-viewport` | Viewport que recorta el editor TipTap a las dimensiones de la caja |
| `.linked-text-editor-content` | Contenedor interno del viewport con transform para desplazar el editor |
| `.ProseMirror` | Clase del editor TipTap. Sus estilos deben ser **idénticos** a `.linked-text-display` (misma font, line-height, white-space, word-break) para garantizar que el texto se vea igual en modo display y modo edición |

### Requisito de equivalencia de estilos

Para que el texto se vea **idéntico** en modo display y modo edición, las clases `.ProseMirror` y `.linked-text-display` comparten exactamente las mismas propiedades:

```css
/* Ambas clases comparten: */
white-space: pre-wrap;
word-break: break-word;
overflow-wrap: break-word;
color: inherit;
text-shadow: inherit;
-webkit-text-stroke: inherit;
/* Y ambas tienen p { margin: 0; padding: 0; text-shadow: inherit; } */
```

---

## 7. Flujo de Redistribución

```
Evento disparador                     Función llamada
─────────────────────                 ────────────────
• commitTextEdit (terminar edición)   
• redimensionar caja                  → linkedTextBoxSystem.redistribute(groupId, fullHtml, chainLayouts)
• conectar/desconectar enlace         

         │
         ▼
  1. Obtener fullHtml del head de la cadena
  2. Obtener chainLayouts (w, h, estilos de cada caja)
  3. Llamar a redistribute()
         │
         ▼
  4. Parsear fullHtml en párrafos (parseHtmlIntoParagraphs)
  5. Aplanar en unidades (allUnits)
  6. Para cada caja secuencialmente:
     a. Configurar div de medición con estilos de la caja
     b. Búsqueda binaria para encontrar cuántas unidades caben
     c. Calcular editorTopOffset con medición de marcador
     d. Calcular editorTextOffset sumando caracteres previos
     e. Asignar fragmento al sistema (system.fragments[boxId])
     f. Avanzar unitIdx += unidades que cupieron
         │
         ▼
  7. Los fragmentos están disponibles en system.fragments
  8. Cada RichTextEditor.vue consume su fragmento vía props
     (displayHtml, overflowHtml, fullTextHtml, editorTopOffset, editorTextOffset, fitsInBox)
```

---

## 8. Notas de Implementación

### Párrafos vacíos

Los párrafos vacíos (línea en blanco por presionar ENTER) se tratan como unidades de tipo `'paragraph'` sin palabras. Esto permite que ocupen altura real en la medición (se renderizan con `<br>`) y empujen correctamente el contenido a la siguiente caja.

### Marcador de medición (`data-linked-text-flow-marker`)

Para medir el `editorTopOffset` con precisión, se inserta un `<span>` invisible con `height: 1em` en la posición exacta del split. Midiendo su `getBoundingClientRect().top` relativo al contenedor, se obtiene el desplazamiento en píxeles sin depender de conteo de líneas.

### Scroll reset en editor

`syncEditorViewportOffset()` (línea 192) fuerza `scrollTop = 0` en el viewport del editor tras montar o cambiar offset. Esto evita que el navegador reposicione el scroll automáticamente, manteniendo la alineación controlada por `transform`.

### Sistema singleton

`useLinkedTextBoxSystem` es un singleton (módulo ES con variable `let singleton = null`). Todas las cajas comparten el mismo mapa de sistemas (`systemsMap`), permitiendo que cualquier componente acceda a los fragmentos de cualquier grupo.
