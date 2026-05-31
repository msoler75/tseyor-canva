# Importación/Exportación de diseños (.tc)

## Formato de archivo

Los archivos `.tc` son JSON con la siguiente estructura:

```json
{
  "tcVersion": 2,
  "format": "horizontal",
  "size": "1080 × 1080 px",
  "designSurface": { "width": 1080, "height": 1080 },
  "designTitle": "Mi diseño",
  "designTitleManual": true,
  "objective": "Bienvenida",
  "outputType": "horizontal",
  "pages": [],
  "content": {},
  "elementLayout": {},
  "customElements": {},
  "userUploadedImages": [],
  "workingDocumentPageId": null
}
```

## Campos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `tcVersion` | `number` | Versión del formato. Actual: `2`. |
| `format` | `string|null` | Formato visual (`horizontal`, `vertical`, `square`). |
| `size` | `string|null` | Tamaño nominal (ej. `"1080 × 1080 px"`). |
| `designSurface` | `object|null` | Dimensiones reales del lienzo `{ width, height }`. |
| `designTitle` | `string` | Título del diseño. |
| `designTitleManual` | `boolean` | Si el título fue editado manualmente. |
| `objective` | `string|null` | Objetivo seleccionado en el asistente. |
| `outputType` | `string|null` | Tipo de salida. |
| `pages` | `array` | Páginas del diseño (cada una con su propio content/elementLayout/customElements). |
| `content` | `object` | Datos textuales (título, subtítulo, cuerpo, etc.). |
| `elementLayout` | `object` | Disposición y estilos de cada elemento del diseño (posición, tamaño, rotación, sombras, fondo, etc.). |
| `customElements` | `object` | Elementos personalizados (imágenes, botones, formas). Cada elemento imagen incrusta su src como data URI. |
| `userUploadedImages` | `array` | Registro central de imágenes subidas. Cada entrada contiene `src` (data URI), `intrinsicWidth`, `intrinsicHeight` y `label`. |
| `workingDocumentPageId` | `string|null` | ID de la página activa al exportar. |

## Manejo de imágenes

### Exportación

En `handleExportTc()` (`EditorPage.vue:6234`):

1. Se recopilan todas las URLs de imágenes que no sean data URI desde:
   - `customElements[].src` (elementos de tipo `image`)
   - `elementLayout[].background.backgroundImageSrc` (imagen de fondo)
   - `userUploadedImages[].src` (registro central)
2. Cada URL se descarga vía `fetch()` con timeout de 10s.
3. Las respuestas se convierten a data URI vía `FileReader.readAsDataURL()`.
4. Se actualizan todas las referencias en el snapshot clonado.
5. Si una descarga falla, se conserva la URL original.
6. `tcVersion` se establece a `2`.

La clonación se hace con `JSON.parse(JSON.stringify(...))` para mutar las URLs sin afectar el estado vivo.

### Importación

En `onMounted` de `EditorPage.vue`:

1. Se lee `sessionStorage.getItem('importedTcDesign')`.
2. Se limpian campos específicos del servidor anterior:
   - `assetId` → `null`
   - `storagePath` → `null`
   - `uploadStatus` → `'pending'`
   - `needsUpload` → `true`
   - `userUploadedImages` → `[]` (se reconstruirá automáticamente)
3. Si un `src` es data URI, se copia a `pendingDataUrl`.
4. Se aplica el estado con `Object.assign(state, data)`.
5. `syncPendingUploadsFromPersistedState()` (línea 5872) detecta las imágenes con data URI y:
   - Asigna nuevos `assetId` via `createElementId()`
   - Registra cada imagen en `userUploadedImages`
   - Las encola para subida asíncrona al servidor

### Flujo de subida post-importación

Las imágenes importadas pasan por el mismo pipeline que las imágenes recién arrastradas:

1. `syncPendingUploadsFromPersistedState` crea entradas en `userUploadedImages` con `uploadStatus: 'pending'`.
2. Los watchers de estado detectan los cambios y llaman a `queueUploadForAsset()`.
3. `uploadImageAsset()` envía cada imagen a `POST /designer/uploads`.
4. El backend guarda el archivo en `storage/app/public/users/{id}/{uuid}.{ext}`.
5. `replaceUploadedImageSourceEverywhere()` actualiza todas las referencias del data URI local a la URL servida.

## Flujo completo

```
Export:
  Editor → handleExportTc()
    ├─ commitTextEdit()
    ├─ syncActivePageSnapshot()
    ├─ clone state (elementLayout, customElements, userUploadedImages)
    ├─ fetch & convert server URLs → data URIs
    ├─ build snapshot JSON
    └─ download .tc file

Import:
  Home → Importar .tc → processImportedTc()
    ├─ FileReader.readAsText(file)
    ├─ JSON.parse → validate tcVersion
    ├─ sessionStorage.setItem('importedTcDesign')
    └─ window.location.href = '/designer/editor?imported=tc'
      └─ EditorPage → onMounted
        ├─ read sessionStorage
        ├─ clean server-specific fields
        ├─ Object.assign(state, data)
        └─ syncPendingUploadsFromPersistedState() → queue uploads
```

## Campos excluidos del export

| Campo | Motivo |
|-------|--------|
| `stateRevision` | Interno del estado vivo, no es parte del diseño. |
| `thumbnailDataUrl` | Específico de la sesión actual. |
| `currentDesignUuid` | No se transfiere (el diseño importado es nuevo en el destino). |
| `designSurface` se exporta | Sí se exporta (es parte del diseño). |

## Historial de versiones

| Versión | Cambios |
|---------|---------|
| 1 | Formato inicial (sin imágenes). |
| 2 | Se añade `userUploadedImages`. Las imágenes del servidor se convierten a data URI. |
