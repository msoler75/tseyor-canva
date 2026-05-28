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
