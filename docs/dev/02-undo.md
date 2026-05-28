# Sistema de Undo/Redo

(Fuente original: `UNDO.md`)

## Arquitectura

Snapshots completos del estado de diseño en pila (`historyStack`) con límite de 80 entradas. Cada snapshot contiene:

- `content`: campos de texto base (title, subtitle, meta, contact, extra)
- `elementLayout`: geometría, estilo, propiedades de cada elemento
- `customElements`: datos de elementos personalizados (html, text, type, src)

No se guarda UI state (selección, edición activa, paneles).

## Guardado automático (debounced)

- Watcher detecta cambios profundos en content/elementLayout/customElements
- `scheduleHistorySnapshot()` con debounce 180ms y `allowCoalesce: true`
- Coalesce reemplaza el tope en vez de apilar → cambios rápidos comparten entrada

## Guardado forzado (force: true)

Acciones con entrada independiente (sin coalesce ni debounce):

| Acción | Ubicación |
|--------|-----------|
| Borrar elemento | `deleteSelectedElement`, `deleteElementsByIds` |
| Cambiar estilo (toolbar) | `applyParagraphStyleField` |
| Confirmar edición texto | `commitTextEdit` |

## Flujo de Undo

1. `performUndo`: decrementa historyIndex, aplica snapshot
2. `applyHistorySnapshot`:
   - `resetAllSystems()` (limpia fragmentos linkedText)
   - Reemplaza state.content, state.elementLayout, state.customElements
   - Limpia selección si elemento ya no existe
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

## Limitaciones

- CancelTextEdit: cambios intermedios ya capturados, no descartables
- state.pages: no se guarda en historial, depende de syncActivePageSnapshot()
- UI state: no se restaura
- Movimiento/redimension: sin force:true, sujetos a debounce 180ms
