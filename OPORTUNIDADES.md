# Análisis Backend — Tseyor Canva

**Stack**: Laravel 12 + Inertia.js + Vue 3 + SQLite/MySQL + JWT (firebase/php-jwt)

---

## FALLOS CRÍTICOS

### 1. `isAdmin()` basado en `name === 'admin'`

**Archivos**: `app/Http/Controllers/DesignerController.php:51`, `app/Http/Controllers/DesignTemplateController.php:277`, `app/Http/Controllers/DesignTemplateController.php:46`

El rol admin se determina comparando el campo `name` del usuario con el string `'admin'`. No existe columna `role` ni `is_admin` en la tabla `users`. Si un usuario se registra con `name=admin` en el portal externo, obtiene acceso a crear/modificar plantillas y editar bases de diseño de cualquier dueño.

**Impacto**: cualquier persona con nombre `admin` es automáticamente superadmin.

**Solución propuesta**: NO HAREMOS NADA. ES REQUISITO FUNCIONAL TAL COMO ESTA.

---

### 2. Ruta de deploy expuesta por defecto

**Archivo**: `config/deploy.php:8`

`DEPLOY_ROUTE_ENABLED` = `true` por defecto. Si no se configura `DEPLOY_TOKEN`, cualquier request a `POST /deploy/build` es aceptado (la verificación en `DeployController:56-58` salta si el token configurado es vacío).

**Solución propuesta**: cambiar default a `false` o exigir token siempre.

---

### 4. Ausencia de rate limiting en endpoints de escritura

**Archivo**: `routes/web.php`

`POST/PUT /designer/state` (saveState), `POST /designer/designs` (store), `POST /designer/uploads` (storeUpload) no tienen middleware `throttle`. Permiten abuso de almacenamiento y CPU sin límites.

**Solución propuesta**: añadir `throttle:x,1` u otra política a estos endpoints, donde x es muy grande para el state (60 por minuto, y el resto 10 por minuto)

---

### 5. `selected_template_id` sin foreign key

**Archivo**: `app/Models/Design.php:78-80`

`designs.selected_template_id` es un `VARCHAR(120)` que referencia `design_templates.uuid`, pero no tiene constraint FK en la base de datos. El modelo usa `belongsTo(DesignTemplate::class, 'selected_template_id', 'uuid')` sin respaldo estructural.

**Solución propuesta**: añadir FK en migración o usar `id` autoincremental como clave.

---

## BUGS FUNCIONALES

### 6. Métodos privados no utilizados (código muerto)

- `app/Http/Controllers/AuthController.php:248` — `loginWithCredentials()`: no tiene ruta ni caller.
- `app/Http/Controllers/AuthController.php:234` — `authenticateFromToken()`: no llamado desde ningún punto.
- `app/Http/Controllers/DesignerController.php:639` — `resetState()`: la ruta `DELETE /designer/state` existe pero el método solo devuelve `['reset' => true]` sin limpiar sesión ni BD.

**Solución propuesta**: eliminar código no utilizado o implementar las rutas faltantes. Implementar `resetState` para que realmente limpie el estado.

---

### 7. `showUpload` con comentario engañoso y `dd()` comentado

**Archivo**: `app/Http/Controllers/DesignerController.php:712-714`

El comentario dice "Siempre usar el disco 'thumbnails'" pero el método usa `$disk = 'users'`. Hay un `//dd($path)` vestigial.


Expicación del tecnico: No pasa nada, porque los uploads van a  disco 'users' pero si esos uploads son de imagenes, y se crean thumbnails de esas imagenes, los thumbnails correspondientes siempre van al disco 'thumbnails'. Solo revisar que así sea. remover dd vestigial.

---

### 8. `recoverSessionDesign` — inconsistencia en carpeta de invitados

**Archivo**: `app/Http/Controllers/DesignerController.php:196`

Al mover imágenes temporales tras login, se usa `str_starts_with($storagePath, $sessionId.'/') || str_starts_with($storagePath, 'guest/')`. Pero en `storeUpload:661` la carpeta para invitados es `trim($request->session()->getId()) ?: 'guest'`, mientras que en `saveState:524` usa solo `$sessionId` sin el fallback. La inconsistencia puede causar pérdida de archivos al recuperar después de login. 

**Solución propuesta**: extraer la lógica de path de invitado a un helper compartido.

---

### 9. `pages_count` inconsistente en saves parciales

**Archivo**: `app/Models/Design.php:61-75`

El mutator `setStateAttribute` recalcula `pages_count` del array `$state['pages']`. Pero en `DesignController::update` y `DesignerController::saveState` se asigna `state` vía `fill()` después de la normalización, que solo contiene la página activa. Esto significa que `pages_count` se actualiza a 1 en cada save si `$state['pages']` no incluye todas las páginas.

**Solución propuesta**: preservar las páginas completas en el estado normalizado o calcular `pages_count` sin depender del mutator.

---

### 10. `resetState` no funcional

**Archivo**: `app/Http/Controllers/DesignerController.php:639`

La ruta `DELETE /designer/state` llama a `resetState()` que solo devuelve `['reset' => true]`. No limpia `session('designer.state')` ni hace nada en BD.

**Solución propuesta**: implementar la limpieza de sesión y diseño temporal.

---

## OPORTUNIDADES DE MEJORA — ARQUITECTURA

### 11. Controladores sobrecargados

**Archivo**: `app/Http/Controllers/DesignerController.php` (874 líneas)

Mezcla: gestión de estado, thumbnails, normalización de documentos, resolución de diseño, serialización de templates, versionado de assets y recuperación post-login.

**Solución propuesta**: extraer a servicios dedicados:
- `DesignerSessionService` — lógica de sesión invitado/autenticado
- `ThumbnailService` — gestión de miniaturas (store, serve, version)
- `DesignResolutionService` — `resolveRequestedDesign`

---

### 12. Código duplicado entre controladores

| Método | Archivos |
|--------|----------|
| `serializeTemplate()` | `DesignerController:764`, `DesignTemplateController:283` |
| `versionedThumbnailRoute()` | `DesignerController:792`, `DesignTemplateController:310` |
| `resolveAssetVersion()` | `DesignerController:808`, `DesignTemplateController:318` |
| `nextRevision()` | `DesignerController:290`, `DesignTemplateController:21` |

**Solución propuesta**: extraer a un trait `HasThumbnailRouting` y `HasRevisionTracking` o a un helper service.

---

### 13. Sin sistema de autorización (Gates / Policies)

Todas las verificaciones de propiedad son inline: `abort_unless($request->user()?->is($design->user), 404)`. Laravel soporta Policies y Gates nativos.

**Solución propuesta**: crear `DesignPolicy` y `DesignTemplatePolicy`, usar `$this->authorize()` en controladores.

---

### 14. Sin caché para plantillas publicadas

`publishedTemplates()` en `DesignerController:747` consulta `design_templates` + `designs` en cada render del editor y home. Son datos que cambian raramente.

**Solución propuesta**: cachear con `Cache::remember()` e invalidar en create/update de template.

---

### 15. Sin paginación en listados

`DesignController::index`, `DesignTemplateController::index`, `DesignAssetController::index` usan `->get()` sin límite.

**Solución propuesta**: usar `->paginate()` o `->cursorPaginate()`.

---

### 16. `fontFamilies()` lee archivo en cada request

`DesignerController::fontFamilies()` lee `resources/fonts_list.txt` del disco en cada petición al editor.

**Solución propuesta**: cachear la lista de fuentes en memoria (propiedad estática o `Cache::rememberForever`).

---

### 17. Estado del diseño como JSON monolítico

La columna `state` (JSON) contiene `content`, `elementLayout`, `customElements`, `pages`, `userUploadedImages`. Para diseños complejos multipágina con imágenes base64 puede alcanzar megabytes.

**Solución propuesta**: separar assets/imágenes en su propia tabla y referenciar por ID; limitar el tamaño máximo del JSON de estado.

---

### 18. Sin eventos de dominio

No se despachan eventos al crear diseño, publicar plantilla, etc. Los side-effects van inline en los controladores.

**Solución propuesta**: usar el sistema de eventos de Laravel (`DesignCreated`, `TemplatePublished`, `DesignDuplicated`) para desacoplar auditoría, notificaciones y caché.

---

### 19. Sin queues para tareas pesadas

La generación de thumbnails SVG y la adaptación de superficies (escalado posicional) se ejecutan sincrónicamente en el request HTTP.

**Solución propuesta**: mover `storeThumbnailSvg` y `adaptStateToSurface` a jobs (`GenerateDesignThumbnail`, `AdaptTemplateToSurface`).

**DECISION DEL CEO**: no podemos permitirnos ahora más jobs. Dejarlo todo sincrono.

---

### 20. Sin logging estructurado para auditoría

Hay uso abundante de `Log::info/debug`, pero las acciones críticas (cambio de plantilla, publicación, duplicación) no se registran de forma consistente con un canal dedicado.

**Solucion propuesta**: adoptar una solucion adecuada y profesional.
---

## OPORTUNIDADES DE MEJORA — BASE DE DATOS

### 21. Índices faltantes

- `designs.selected_template_id`: se usa en joins pero no tiene índice.
- `designs.public`: usado en `where('public', true)` en welcome, solo existe en índice compuesto `[user_id, updated_at]`.

**Solución propuesta**: añadir índices `INDEX selected_template_id` y `INDEX public` en `designs`. Para ello crear una migracion.

---

### 22. `unsignedTinyInteger` para `pages_count` restrictivo

Máximo 255 páginas. `unsignedSmallInteger` (65535) sería más seguro a futuro. 

**CEO**: no es necesario, es muy dificil que se creen documentos de mas de 200 paginas.

---

### 23. `design_assets.path` con constraint UNIQUE

Impide que dos assets apunten al mismo archivo. Si dos usuarios comparten contenido con el mismo path, fallará.

**Solución propuesta**: eliminar el UNIQUE de `path` o añadir `user_id` al constraint compuesto.

**CEO**: Nunca se compartirán assets entre usuarios. Pero sí diseños o templates. No hacer nada.

---

## OPORTUNIDADES DE MEJORA — TESTING

### 24. Cobertura de tests insuficiente

| Tipo | Estado |
|------|--------|
| `tests/Unit/ExampleTest.php` | Placeholder vacío |
| `DesignTemplateGenerator` | Sin tests unitarios |
| `JwtService` | Sin tests unitarios |
| `DeployHelper` | Sin tests |
| `DesignerStateSync` | Sin tests |
| `DesignerStateRules` | Sin tests |
| `DemoTemplateFactory` | Sin tests |
| `FontController` | Sin tests |
| `FrontendLogController` | Sin tests |
| `DeployController` | Sin tests |
| Tests de integración con portal JWT | No existen |
| Tests de carga/performance | No existen |

---

### 25. `TestCase` sobreescribe variables de entorno redundantemente

`tests/TestCase.php:26-44` usa `putenv()` y modifica `$_ENV`/`$_SERVER` antes de crear la app. `phpunit.xml` ya define las mismas variables; la sobreescritura es redundante.

---

## OPORTUNIDADES DE MEJORA — SEGURIDAD ADICIONAL

### 26. Imágenes base64 en sesión

`saveState` para invitados guarda `thumbnailDataUrl` (base64) en la sesión. Las sesiones se persisten en BD (`SESSION_DRIVER=database`) y pueden crecer enormemente.

**Solución propuesta**: limitar o mover thumbnails a disco antes de guardar en sesión.

**CEO**:  no hacer nada. Habrá pocos usuarios.

---

### 27. Sin validación de tipo MIME real en uploads

`storeUpload` valida `'file' => ['file', 'image']` pero no verifica el contenido real del archivo más allá de la extensión.

**Solución propuesta**: usar validación de contenido con `finfo` o librerías de validación de imágenes.

**CEO**: no hacer nada.

---

### 28. `showThumbnail` / `showUpload` sin sanitización explícita de path

Aunque usan `Storage::disk()->exists($path)` y Laravel protege contra path traversal, conviene validar que el path no contenga `../` ni barras sospechosas.

**CEO**: es vital añadir comprobación.

---

### 29. `CACHE_STORE=database` y `QUEUE_CONNECTION=database` en `.env.example`

Usar BD para colas y caché en producción es subóptimo frente a Redis.

**CEO**: No habrá jobs ni queues en este proyecto.

---

## RESUMEN DE PRIORIDADES

| # | Hallazgo | Tipo | Prioridad |
|---|----------|------|-----------|
| 1 | `isAdmin()` por `name === 'admin'` | Seguridad | **Crítica** |
| 2 | Deploy sin token por defecto | Seguridad | **Crítica** |
| 3 | `dd()` en AuthController | Bug/Mantenibilidad | **Alta** |
| 4 | Sin rate limiting en endpoints | Seguridad | **Alta** |
| 5 | Sin FK en `selected_template_id` | Integridad datos | **Alta** |
| 11 | Controladores de 800+ líneas | Arquitectura | **Alta** |
| 10 | `resetState` no funcional | Bug | **Alta** |
| 9 | `pages_count` inconsistente | Bug | **Alta** |
| 6 | Métodos no utilizados | Mantenibilidad | **Media** |
| 8 | Inconsistencia carpeta guest | Bug | **Media** |
| 12 | Código duplicado | Mantenibilidad | **Media** |
| 14 | Sin caché en templates | Rendimiento | **Media** |
| 15 | Sin paginación en listados | Rendimiento | **Media** |
| 16 | FontFamilies sin caché | Rendimiento | **Media** |
| 21 | Índices faltantes | Rendimiento | **Media** |
| 24 | Tests insuficientes | Calidad | **Media** |
| 13 | Sin Gates/Policies | Arquitectura | **Baja** |
| 17 | JSON monolítico de estado | Arquitectura | **Baja** |
| 18 | Sin eventos de dominio | Arquitectura | **Baja** |
| 19 | Sin queues para tareas pesadas | Arquitectura | **Baja** |
| 20 | Sin logging de auditoría | Operaciones | **Baja** |
| 22 | `pages_count` tipo restrictivo | Base de datos | **Baja** |
| 23 | UNIQUE en `design_assets.path` | Base de datos | **Baja** |
| 25 | Redundancia en TestCase | Testing | **Baja** |
| 26 | Base64 en sesión | Seguridad | **Baja** |
| 27 | Validación MIME débil | Seguridad | **Baja** |
| 28 | Path sin sanitizar en serve | Seguridad | **Baja** |
| 29 | Cache/Queue en BD | Rendimiento | **Baja** |
