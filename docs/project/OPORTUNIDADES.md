# Análisis de Oportunidades — Backend

## Fallos críticos

- **isAdmin() por name === 'admin'**: requisito funcional, no se cambia
- **Ruta de deploy expuesta**: cambiar default DEPLOY_ROUTE_ENABLED a false
- **Sin rate limiting** en endpoints de escritura
- **selected_template_id sin FK**: añadir migración

## Bugs funcionales

- Métodos privados no utilizados (loginWithCredentials, authenticateFromToken, resetState no funcional)
- Inconsistencia carpeta guest en recoverSessionDesign
- pages_count inconsistente en saves parciales

## Mejoras arquitectura

- Controladores sobrecargados (DesignerController: 874 líneas)
- Código duplicado entre DesignerController y DesignTemplateController
- Sin caché para plantillas publicadas
- Sin paginación en listados
- fontFamilies() lee archivo en cada request
- Estado del diseño como JSON monolítico
- Sin eventos de dominio
- Sin queues para tareas pesadas

## Base de datos

- Índices faltantes (selected_template_id, public)
- unsignedTinyInteger restrictivo para pages_count
- UNIQUE en design_assets.path

## Testing

- Cobertura insuficiente (muchos servicios sin tests)
- TestCase sobreescribe variables de entorno

## Seguridad adicional

- Imágenes base64 en sesión
- Sin validación MIME real en uploads
- Path sin sanitizar en showThumbnail/showUpload

(Detalles completos en archivo original en `docs/`)

---

# Análisis de Completitud — Frontend (v1.0)

## Gaps funcionales para v1.0

### UX / Feedback

| Gap | Impacto | Dónde |
|-----|---------|-------|
| Sin indicador de autoguardado | Usuario no sabe si su diseño se guardó | EditorPage |
| Sin feedback de undo/redo | La acción ocurre sin confirmación visual | useEditorHistory |
| Sin skeletons / loading states | Pantalla en blanco mientras cargan templates/designs | Home, Designer |
| Sin estados vacíos | No hay mensaje "sin diseños" en galerías | Home |
| Sin error boundaries | Un error en un componente rompe toda la página | App.vue / EditorPage |
| Sin advertencia al salir con cambios sin guardar | Pérdida de datos si cierra pestaña | EditorPage (beforeunload) |
| Sin tour / onboarding | Usuario nuevo no sabe por dónde empezar | Home |

### Editor

| Gap | Impacto | Dónde |
|-----|---------|-------|
| CancelTextEdit no descarta cambios intermedios | Undo no puede deshacer edición activa (gap conocido) | useEditorHistory |
| Sin zoom controls | No se puede alejar/acercar en desktop | EditorPage |
| Sin contador de palabras/caracteres | Útil para copys de impresión | RichTextEditor |
| Sin crop/aspect-ratio en imágenes | Usuario no puede recortar imágenes subidas | ElementHandles / useEditorInteractions |

### Accesibilidad

| Gap | Impacto |
|-----|---------|
| Faltan aria-labels en toolbar, handles, panels | Navegación por screen reader limitada |
| Sin focus trapping en modales | Usuario de teclado queda atrapado fuera del modal |
| Sin keyboard shortcut cheatsheet | Usuarios avanzados no descubren atajos |
| Sin high-contrast / reduced-motion | No respeta preferencias del sistema |

### Performance

| Gap | Impacto |
|-----|---------|
| Imágenes sin lazy loading | Carga innecesaria de imágenes fuera de viewport en galerías |
| Sin paginación en listados de templates/diseños | Degradación con muchos diseños |
| Sin code splitting | Bundle grande en carga inicial |

## Testing

| Área | Estado |
|------|--------|
| E2E undo/redo | ✅ 245 líneas |
| E2E linked text | ✅ Existen tests |
| E2E pages, drag, toolbar | ❌ Sin cubrir |
| PHP Unit controllers/services | ❌ Cobertura insuficiente |
