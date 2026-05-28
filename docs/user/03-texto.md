# Editor de Texto

(Fuente original: `TEXTO_EDITOR.md`)

## Tres estados de la toolbar

### Estado A: Elemento seleccionado (no editando)

- Click simple sobre caja de texto
- Toolbar muestra **todos los controles** (tipografía, tamaño, color, bold, etc.)
- Reflejan estado de **TODO el texto**
- Si el texto es uniforme → valor único; si hay variedad → estado mixto
- Al cambiar: se aplica a **TODO el texto**

### Estado B: Editando (cursor activo)

- Doble click para entrar en edición
- Toolbar refleja propiedades del **párrafo actual**
- Bold/italic/underline: estado del carácter/palabra actual
- Al cambiar: se aplica solo al **párrafo actual**

### Estado C: Texto seleccionado

- Selección con mouse/teclado dentro del editor
- Bold/Italic/Color/Font-size/Font-family → marks (nivel selección)
- Alignment/Spacing/Lista → nivel de párrafo

## Estados mixtos

Cuando el texto contiene múltiples valores para una propiedad:

| Propiedad | Indicador visual |
|-----------|-----------------|
| Font-family | Label muestra "Varios" |
| Font-size | Input vacío (placeholder "—") |
| Color | Gradiente en barra |
| Bold/Italic/Underline | Botón gris (ni activo ni inactivo) |
| Alignment | Icono raya |
| Spacing | Botón gris |

Al clickar en mixed state, el nuevo valor se aplica a **todo el texto**.

## Pegado de texto enriquecido

En cajas linkedText, al pegar texto con formato (Ctrl+V):
- Si el HTML contiene formato, se muestra diálogo de confirmación
- **Conservar formato**: mantiene estilos inline
- **Pegar sin formato**: solo texto plano

## Atajos

- Ctrl+B: Bold
- Ctrl+I: Italic
- Ctrl+U: Underline
- Ctrl+Z: Undo
- Shift+Ctrl+Z: Redo
