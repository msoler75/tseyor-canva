# TEXTO_EDITOR.md — Comportamiento del Editor de Texto y Floating Toolbar

## 1. Tres Estados de la Toolbar

### Estado A: Elemento de texto seleccionado (NO editando)
- El usuario hace click simple sobre una caja de texto
- La toolbar muestra **todos los controles** (tipografía, tamaño, color, bold, italic, etc.)
- Los controles reflejan el **estado general de TODO el texto** de la caja
  - Si todo el texto es **uniforme** en una propiedad → se muestra el valor único
  - Si hay **variedad** → se muestra el estado mixto (ver sección 2)
- Al cambiar un valor (fuente, tamaño, color, bold, etc.) se aplica a **TODO el texto** de la caja
- Para texto enlazado (`linkedText`), los cambios afectan al texto fuente completo (head de la cadena)

### Estado B: Editando texto (cursor activo, sin selección de rango)
- El usuario hace doble click o activa el modo edición
- La toolbar refleja las **propiedades del párrafo actual** donde está el cursor
- Los botones bold/italic/underline muestran el estado del **carácter/palabra actual**
- Al cambiar un valor, se aplica solo al **párrafo actual** (o carácter si es mark)
- **Effects y Opacity** no aparecen o se muestran deshabilitados (son propiedades de elemento, no de texto)

### Estado C: Texto seleccionado (rango marcado dentro del editor)
- El usuario selecciona texto con el mouse/teclado dentro del editor
- Bold/Italic/Underline/Color/Font-size/Font-family se aplican como **marks** (a nivel de selección)
- Alignment/Spacing/Lista se aplican a nivel de **párrafo** (a todos los párrafos afectados por la selección)

---

## 2. Estados Mixtos (Mixed State)

Cuando el texto de una caja contiene **múltiples valores** para una propiedad, la toolbar lo indica:

| Propiedad | Indicador visual de mixed state |
|-----------|-------------------------------|
| **Font-family** | Label muestra "**Varios**" en lugar del nombre de la fuente |
| **Font-size** | Input de tamaño aparece **vacío** (placeholder "—") |
| **Color** | Barra de color muestra un **gradiente** (rojo→verde→azul) |
| **Bold** | Botón en **gris** (`btn-neutral`) — ni activo (`btn-accent`) ni inactivo (`btn-outline`) |
| **Italic** | Botón en gris |
| **Underline** | Botón en gris |
| **Uppercase** | Botón en gris |
| **Alignment** | Icono muestra una **raya** (`ph:minus`) |
| **Spacing** | Botón en gris (si aplica) |

### Detección de mixed state
1. Se recorren **todos los párrafos** del documento completo de la caja
2. Para cada propiedad, se comparan los valores de todos los párrafos
3. Si algún párrafo difiere → mixed state
4. Si todos los párrafos tienen el mismo valor → se muestra ese valor

### Comportamiento al clickar en mixed state
- Si el usuario cambia un valor que está en mixed state, el nuevo valor se aplica a **TODO el texto**
- Bold: si parte del texto es bold y parte no, al clickar se pone **todo** en bold (o quita bold de todo al clickar de nuevo)
- Color: al seleccionar un color desde el panel, se aplica a todo
- Fuente: al seleccionar una fuente, se aplica a todo
- Tamaño: al escribir o arrastrar un tamaño, se aplica a todo
- Alineación: al ciclar, se aplica a todo
- Lista: al activar, se aplica a todo

---

## 3. Formato Bold/Italic/Underline — Tres Estados Visuales

| Estado | Significado | Clase CSS |
|--------|-------------|-----------|
| `btn-accent` | **Activo** — todo el texto tiene esta propiedad | `btn-accent` |
| `btn-outline` | **Inactivo** — ningún texto tiene esta propiedad | `btn-outline` |
| `btn-neutral gris` | **Mixto** — parte del texto tiene esta propiedad, parte no | `btn-neutral border-gray-400/50 text-gray-400` |

---

## 4. Pegado de Texto Enriquecido

### Flujo de pegado en cajas linkedText
1. El usuario entra en modo edición (doble click sobre la caja)
2. Pega texto (Ctrl+V / Cmd+V)
3. Si el portapapeles contiene **HTML con formato**, se muestra un diálogo de confirmación:
   > "Este texto tiene formato (negritas, listas, encabezados, etc.). ¿Quieres conservar el formato al pegarlo?"
4. Si el usuario elige **"Conservar formato"** → el HTML rico se pega con todos sus estilos inline
5. Si el usuario elige **"Pegar sin formato"** → solo se inserta el texto plano, sin formato

### Preservación de formato al salir del modo edición
- Los estilos inline del HTML pegado (font-size, font-family, color, bold, etc.) se **preservan** cuando el usuario sale del modo edición
- `mergeParagraphStylesIntoHtml()` **fusiona** los estilos del layout con los inline existentes:
  - Si el HTML pegado ya define una propiedad → esa propiedad **se preserva**
  - Solo se añaden propiedades del layout que **no existen** en el inline
- El texto en modo display se ve **idéntico** al modo edición

### Cobertura del confirm dialog
El `handlePaste` en `RichTextEditor.vue` detecta formato rico mediante la función `htmlContainsRichFormatting()` que busca:
- Atributos `style` o `class` en el HTML
- Tags como `<strong>`, `<b>`, `<em>`, `<i>`, `<u>`, `<span>`, `<font>`, `<h1>`-`<h6>`, `<ul>`, `<ol>`, `<li>`, `<table>`, `<blockquote>`, `<code>`, `<a>`

---

## 5. Efectos y Transparencia

- Los paneles de **Effects** y **Opacity** (Transparencia) solo aplican a **nivel de elemento** (toda la caja), no afectan al contenido del texto
- Cuando el usuario está en modo edición (Estado B o C), estos paneles:
  - Pueden mostrarse pero deben indicar que aplican al elemento completo, no al texto
  - No deben interferir con los controles de formato de texto

---

## 6. Propiedades por Nivel

| Propiedad | Nivel | Dónde se almacena |
|-----------|-------|-------------------|
| Opacidad | Elemento | `elementLayout[id].opacity` |
| Efectos (neón, hollow, sombra) | Elemento | `elementLayout[id].effect*` |
| Posición (x, y) | Elemento | `elementLayout[id].x/y` |
| Borde | Elemento | `elementLayout[id].border*` |
| Rotación | Elemento | `elementLayout[id].rotation` |
| **Tipo de fuente** | Párrafo / Carácter | `paragraphStyles[].fontFamily` / mark `styledText.fontFamily` |
| **Tamaño de fuente** | Párrafo / Carácter | `paragraphStyles[].fontSize` / mark `styledText.fontSize` |
| **Color** | Párrafo / Carácter | `paragraphStyles[].color` / mark `styledText.color` |
| **Bold** | Párrafo / Carácter | `paragraphStyles[].fontWeight` / mark `styledText.fontWeight` |
| **Cursiva** | Párrafo / Carácter | `paragraphStyles[].italic` / mark `styledText.fontStyle` |
| **Subrayado** | Párrafo / Carácter | `paragraphStyles[].underline` / mark `styledText.textDecoration` |
| **Mayúsculas** | Párrafo | `paragraphStyles[].uppercase` |
| **Alineación** | Párrafo | `paragraphStyles[].textAlign` |
| **Interlineado** | Párrafo | `paragraphStyles[].lineHeight` |
| **Espaciado** | Párrafo | `paragraphStyles[].letterSpacing` |
| **Lista** | Párrafo | `paragraphStyles[].listType` |

---

## 7. Comportamiento para Texto Enlazado (linkedText)

- El texto fuente se almacena en `customElements[headId].html` (head de la cadena)
- Los `paragraphStyles` completos residen en el head de la cadena
- Al cambiar un estilo desde el Estado A (elemento seleccionado, no editando):
  1. Se modifica `paragraphStyles` de **todos** los párrafos
  2. Se actualiza `elementLayout[headId].paragraphStyles` con el array completo
  3. Se llama a `recalculateLinkedTextAllocations(headId)` para redistribuir
- Al cambiar un estilo desde Estado B o C (editando):
  1. Se modifica solo el párrafo actual o selección
  2. Se actualiza el HTML completo (`headElement.html`)
  3. Se redistribuye el texto entre las cajas de la cadena
- Los estilos inline de fragmentos individuales se preservan durante la redistribución

---

## 8. Archivos Relacionados

| Archivo | Rol |
|---------|-----|
| `resources/js/Components/designer/RichTextEditor.vue` | Editor TipTap con soporte para linkedText, marks, paste handling, mixed state detection |
| `resources/js/Components/designer/EditorFloatingToolbar.vue` | Toolbar flotante con 3 estados, mixed state display, 3-state buttons |
| `resources/js/Pages/Designer/EditorPage.vue` | Orquestador: conecta toolbar con editor, `selectedTextStyle` Proxy, `textMixedState`, `applyParagraphStyleField` |
| `resources/js/composables/useEditorInteractions.js` | `cycleAlignment`, `cycleList`, `currentAlignmentIcon`, `currentListType` |
| `resources/js/composables/useEditorSelection.js` | `hasTextSelection`, `selectedElementType` |
| `resources/js/composables/useLinkedTextBoxSystem.js` | Fragmentación y redistribución de texto enlazado (NO modificar) |

---

## 9. Notas Técnicas

- `detectMixedState()` compara valores de todos los párrafos usando `Set` para detectar variedad
- `getMixedState()` en RichTextEditor expone el mixed state basado en el documento TipTap actual
- El `textMixedState` computed en EditorPage.vue tiene fallback: primero editor, luego `paragraphStyles` del layout/head de cadena
- Cuando `editingElementId === selectedElementId`, `textMixedState` retorna `{}` (vacío) para que los controles reflejen el cursor
- El `handlePaste` en `editorProps` usa la firma correcta de ProseMirror `(view, event)` y accede a `editor.value` para obtener la instancia TipTap
