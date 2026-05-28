# Editor de Texto — Documentación Técnica

(Fuente original: `TEXTO_EDITOR.md`)

## Propiedades por Nivel

| Propiedad | Nivel | Almacenamiento |
|-----------|-------|----------------|
| Opacidad, Efectos, Borde, Rotación | Elemento | `elementLayout[id].*` |
| Tipo/Tamaño fuente, Color | Párrafo/carácter | `paragraphStyles[].fontFamily/fontSize/color` |
| Bold, Cursiva, Subrayado | Párrafo/carácter | `paragraphStyles[].fontWeight/fontStyle/textDecoration` |
| Mayúsculas, Alineación, Interlineado, Espaciado, Lista | Párrafo | `paragraphStyles[].uppercase/textAlign/lineHeight/letterSpacing/listType` |

## Comportamiento para Texto Enlazado

- Texto fuente en `customElements[headId].html` (head de cadena)
- `paragraphStyles` completos residen en head
- Desde Estado A (no editando): modifica paragraphStyles de TODOS los párrafos
- Desde Estado B/C (editando): modifica solo párrafo actual o selección

## Archivos Relacionados

| Archivo | Rol |
|---------|-----|
| `RichTextEditor.vue` | Editor TipTap, marks, paste handling, mixed state |
| `EditorFloatingToolbar.vue` | Toolbar flotante 3 estados, mixed state display |
| `EditorPage.vue` | Orquestador, `selectedTextStyle`, `applyParagraphStyleField` |
| `useEditorInteractions.js` | cycleAlignment, cycleList |
| `useEditorSelection.js` | hasTextSelection, selectedElementType |
| `useLinkedTextBoxSystem.js` | Fragmentación linked text (NO modificar) |

## Notas Técnicas

- `detectMixedState()` compara valores de párrafos con Set
- `textMixedState` computed tiene fallback: editor → paragraphStyles → head cadena
- `handlePaste` detecta formato rico con `htmlContainsRichFormatting()`
- `mergeParagraphStylesIntoHtml` fusiona (no reemplaza) estilos inline
