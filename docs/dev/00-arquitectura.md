# Arquitectura del Editor

## Visión General

Editor visual SPA construido sobre Laravel + Inertia + Vue 3. El estado del diseño se mantiene en cliente con autoguardado periódico al servidor.

## Flujo de Datos

```
Usuario → EditorPage.vue → state (reactivo) → autoguardado → PUT /designer/state
                                  ↓
                           undo/redo stack (80 snapshots)
                                  ↓
                           linked text system (fragmentación)
```

## Estado del Diseño

Tres objetos reactivos principales:

| Objeto | Contenido |
|--------|-----------|
| `state.content` | Campos de texto base (title, subtitle, meta, contact, extra) |
| `state.elementLayout` | Geometría, estilo, propiedades por elemento (x, y, w, h, fontSize, paragraphStyles, linkedTextNext/Prev) |
| `state.customElements` | Datos específicos por tipo (html/text para linkedText, src para imágenes, shapeType para figuras) |

## Sistema de Historial

Ver `docs/dev/02-undo.md`

## Sistema de Texto Enlazable

Ver `docs/dev/01-linked-text.md`

## Editor de Texto

Ver `docs/dev/03-text-editor.md`

## Persistencia

| Evento | Mecanismo |
|--------|-----------|
| Autoguardado | Debounced watcher → `flushDesignerStateWithThumbnail()` → `PUT /designer/state` |
| Salir del editor | Petición síncrona de guardado |
| Crear diseño | `POST /designer/designs` desde Home |
| Subir imagen | `POST /designer/uploads` |
| Guardar plantilla | Admin → endpoint DesignTemplate |
