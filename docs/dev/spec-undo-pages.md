# Spec: Undo/Redo Full — Include page operations

## Objective

Hacer que undo/redo capture TODAS las operaciones del editor: edición de contenido, estilos, borrado, clonación, creación/eliminación/movimiento de páginas, cambio de página activa, y arrastre de elementos.

## Implementation status ✅ COMPLETED

### Snapshot schema

Cada snapshot incluye:
```js
{
  content: {...},
  elementLayout: {...},
  customElements: {...},
  pages: [...],
  workingDocumentPageId: "page-xxx",
  selectedElementId: "el-xxx" | null,
  format: "vertical" | "brochure" | null,
  size: "A3" | null,
  designSurface: { width, height } | null,
  objective: "event_presential" | null,
  outputType: "print" | "digital" | null,
  designTitle: "Mi diseño",
  designTitleManual: false,
}
```

### buildHistorySnapshot

`syncActivePageSnapshot()` se llama antes de construir cada snapshot, para volcar el estado de la página activa al array `state.pages`. Esto garantiza que el snapshot contenga una copia fiel de todas las páginas (no solo la activa).

### History entries added

| Operación | Dónde | Tipo |
|-----------|-------|------|
| Edición de contenido (watcher) | Watcher principal `[content, elementLayout, customElements]` | `{ allowCoalesce: true }` — coalesce por categoría, sin debounce |
| Drag start | Watcher `drag.active` false→true | `{ force: true }` — estado pre-drag |
| Drag end | Watcher `drag.active` true→false | `{ force: true }` — estado post-drag |
| switchToPage | `switchToPage()` tras commitTextEdit + syncActivePageSnapshot | `{ force: true }` |
| addDocumentPage | `addDocumentPage()` tras syncActivePageSnapshot | `{ force: true }` |
| deleteDocumentPage | `deleteDocumentPage()` tras syncActivePageSnapshot | `{ force: true }` |
| moveDocumentPage | `moveDocumentPage()` tras syncActivePageSnapshot | `{ force: true }` |
| Element deletion | `deleteSelectedElement()` / `deleteElementsByIds()` (previo) | `{ force: true }` |
| Text commit | `commitTextEdit()` / `applyParagraphStyleField()` | `{ force: true }` |

### applyHistorySnapshot behavior

1. Cancelar pending timer (defensa contra phantom timer)
2. Reset linked text systems
3. `historyApplying = true`
4. Restaurar `state.pages`
5. Si pages están vacías o `workingDocumentPageId` no existe → llamar `ensureDocumentPages(true)` (crea página limpia e hidrata content/layout/customElements)
6. Si pages son válidas → restaurar `content`, `elementLayout`, `customElements`, `workingDocumentPageId`, `activePageId`, `visuallyFocusedPageId`
7. Llamar `refreshDocumentPageList()`
8. Restaurar `state.selectedElementId`
9. Si el elemento seleccionado no existe en el layout restaurado → clearSelection
10. `nextTick` → `historyApplying = false`

### Coalescing changes

- **Watcher principal**: `pushHistorySnapshot({ allowCoalesce: true })` — sin debounce de 180ms. El group key identifica la categoría de cambio (position, size, fontSize, color, etc.) y coalesce entradas consecutivas del mismo grupo.
- **Drag**: usa `isDragging` flag para que el watcher principal no dispare durante el arrastre. Un watcher separado en `drag.active` captura estado pre-drag (start) y post-drag (end), ambos con `force: true`.

### Code cleanup

- `scheduleHistorySnapshot()` eliminado (función muerta) — reemplazado por `pushHistorySnapshot({ allowCoalesce: true })` directo
- `historyTimer` solo se usa como defensa en `applyHistorySnapshot` (cancelar pending timer)

### Params passed to useEditorHistory

```js
useEditorHistory({
  state,
  editingElementId,
  commitTextEdit: (...args) => commitTextEdit(...args),
  clearSelection: () => clearSelection(),
  baseElementLabels,
  contentFieldLabels,
  syncActivePageSnapshot,
  refreshDocumentPageList,
  ensureDocumentPages,
  workingDocumentPageId,
  activePageId,
  visuallyFocusedPageId,
});
```

### Safety

- Si undo restaura pages inválidas (vacías o `workingDocumentPageId` inexistente), `ensureDocumentPages(true)` se encarga de crear una página limpia e hidratar todo el estado activo.
- `selectedElementId` se restaura del snapshot; si el elemento no existe en el layout restaurado, se llama `clearSelection()`.
- `historyApplying` flag evita que watchers reactivos muten el estado durante la restauración.
- `historyMuted` permite operaciones que no deben generar entradas de historial.

### Files changed

| File | Changes |
|------|---------|
| `useEditorHistory.js` | Snapshot schema expandido, `applyHistorySnapshot` restaura pages + page IDs + selectedElementId + safety con ensureDocumentPages, removed `scheduleHistorySnapshot` |
| `EditorPage.vue` | Pasa `ensureDocumentPages`, `isDragging` ref + watcher drag.active, page ops con pushSnapshot, removed scheduleHistorySnapshot destructure |

### Success criteria (all met)

- [x] Undo after creating a page removes that page from `state.pages`
- [x] Undo after deleting a page restores that page to `state.pages`
- [x] Undo after moving a page restores original order
- [x] Undo after switching pages returns to the previous page
- [x] Undo after editing still works (regression)
- [x] Undo after linked text edit still works (regression)
- [x] Undo after drag restores original position
- [x] Selection state restored after undo
- [x] Empty/invalid pages after undo handled safely
- [x] Format changes (brochure ↔ diptych ↔ vertical) reversible
- [x] Page dimension changes (custom size via wizard) reversible
- [x] Objective/outputType changes reversible
- [x] Design title changes reversible
- [x] Build succeeds (`npm run build`)
