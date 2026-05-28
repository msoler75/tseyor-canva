# Sistema de Undo/Redo

(Fuente original: `UNDO.md`)

## Arquitectura

Snapshots completos del estado de diseño en pila (`historyStack`) con límite de 80 entradas. Cada snapshot contiene:

- `content`: campos de texto base (title, subtitle, meta, contact, extra)
- `elementLayout`: geometría, estilo, propiedades de cada elemento
- `customElements`: datos de elementos personalizados (html, text, type, src)
- `pages`: array completo de páginas con su contenido
- `workingDocumentPageId`: página activa al momento del snapshot
- `selectedElementId`: elemento seleccionado
- `format`, `size`, `designSurface`: formato y dimensiones del documento
- `objective`, `outputType`: configuración del asistente
- `designTitle`, `designTitleManual`: título del diseño

No se guarda UI state (selección múltiple, edición activa, paneles).

## Guardado automático (coalescing inmediato)

- Watcher detecta cambios profundos en content/elementLayout/customElements
- `pushHistorySnapshot({ allowCoalesce: true })` sin debounce
- Coalesce reemplaza el tope en vez de apilar → cambios rápidos de la misma categoría comparten entrada
- Durante drag: `isDragging` flag evita pushes intermedios; solo start y end

## Guardado forzado (force: true)

Acciones con entrada independiente (sin coalesce):

| Acción | Ubicación |
|--------|-----------|
| Borrar elemento | `deleteSelectedElement`, `deleteElementsByIds` |
| Cambiar estilo (toolbar) | `applyParagraphStyleField` |
| Confirmar edición texto | `commitTextEdit` |
| Crear/duplicar página | `addDocumentPage` |
| Eliminar página | `deleteDocumentPage` |
| Mover página | `moveDocumentPage` |
| Cambiar página activa | `switchToPage` |
| Inicio de drag | Watcher `drag.active` false→true |
| Fin de drag | Watcher `drag.active` true→false |

## Flujo de Undo

1. `performUndo`: decrementa historyIndex, aplica snapshot
2. `applyHistorySnapshot`:
   - `resetAllSystems()` (limpia fragmentos linkedText)
   - Restaura `state.pages`
   - Si pages inválidas → `ensureDocumentPages(true)` crea estado limpio
   - Si pages válidas → restaura content, elementLayout, customElements, page IDs, formato, dimensiones
   - `refreshDocumentPageList()` actualiza UI
   - Restaura `selectedElementId` (limpia si elemento no existe)
   - `historyApplying = true`, luego `false` en nextTick
3. Reactividad post-undo:
   - Computed `editorElements` se re-evalúa → linkedText recalcula
   - Watchers disparan `flushDesignerStateWithThumbnail`
   - Watch en `historyApplying` (true→false): sincroniza pages, recalcula linkedText

## Problemas resueltos

1. **Snapshot intermedio linked-text**: force:true antes de modificar en delete
2. **layout.fontSize desincronizado**: syncLinkedTextCanonicalFromHtml actualiza layout
3. **Nuevo head pierde fontSize**: removeLinkedTextFromChain copia layout fields
4. **displayHtml sin font-size**: displayStyle computed con fallback boxDimensions
5. **Coalescing excesivo**: force:true en acciones críticas
6. **Pages no capturadas**: snapshot expandido con pages + workingDocumentPageId
7. **Formato/dimensiones no capturadas**: snapshot expandido con format, size, designSurface, objective, outputType
8. **Drag llena historial**: isDragging flag + watcher drag.active (start/end)

## Limitaciones

- CancelTextEdit: cambios intermedios ya capturados, no descartables
- UI state: selección múltiple, edición activa, grupos no se restauran
- Scroll/zoom: no se recoloca tras undo
