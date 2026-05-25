# PROYECTO_BASE.md — TSEYOR Canva

## session_id
PENDIENTE — se asignara al crear el primer agente desde opencode

## Stack tecnologico
- **Backend:** Laravel 12, PHP 8.2+
- **Frontend:** Vue 3 (Composition API, `<script setup>`), Inertia 3, Vite 7
- **UI:** Tailwind CSS 4 + daisyUI 5
- **Editor rich text:** TipTap 3 (con extensiones color, font-family, text-align, text-style)
- **Iconos:** Iconify Vue 5
- **Exportacion:** html-to-image (local en resources/js/html-2-image)
- **Auth:** JWT (firebase/php-jwt 7) + portal login externo
- **QR:** qrcode 1.5
- **BD:** MySQL
- **Tests:** PHPUnit 11
- **Code style:** Laravel Pint

## Estructura del proyecto
```
app/
  Http/Controllers/
    AuthController.php         # Login JWT con portal externo
    Controller.php             # Base controller
    DeployController.php       # Endpoint receptor de build
    DesignAssetController.php  # Subida de imagenes
    DesignController.php       # CRUD diseños
    DesignerController.php     # Home, editor, estado, thumbnails
    DesignTemplateController.php# CRUD plantillas
    FontController.php         # Servir fuentes locales
    FrontendLogController.php  # Logs desde frontend
  Models/
    Design.php
    DesignAsset.php
    DesignTemplate.php
    User.php
  Services/
    DemoTemplateFactory.php
    DeployHelper.php           # ZIP, envio, validacion build
    DesignTemplateGenerator.php
  Providers/
  Support/

bootstrap/
config/
  app.php, auth.php, cache.php, database.php, deploy.php,
  designer.php, filesystems.php, jwt.php, logging.php,
  mail.php, portal.php, queue.php, services.php, session.php

database/
  migrations/
  factories/
  seeders/

resources/
  js/
    app.js
    bootstrap.js
    Layouts/
    Pages/
      Home.vue
      Designer/EditorPage.vue
      Designer/Templates/
      Error.vue
    Components/
      Avatar.vue
      Modal.vue
      TimeAgo.vue
      User.vue
      designer/
        ChoiceCard.vue
        ColorPaletteSection.vue
        ColorValueField.vue
        DesignerAssistant.vue
        EditorCanvasStage.vue
        EditorContextPanel.vue
        EditorFloatingToolbar.vue
        EditorInsertSidebar.vue
        EditorTopBar.vue
        ExportDialog.vue
        FillColorPanel.vue
        GradientPaletteSection.vue
        RichTextEditor.vue
        SelectionIndicator.vue
        SelectionOverlay.vue
        StepFooter.vue
        TemplateAdjustmentsPanel.vue
        TemplateCard.vue
        TemplateFormModal.vue
    composables/
    data/
    utils/
    html-2-image/             # Libreria local de exportacion
  css/
  views/                      # Blade views (layouts para Inertia)

routes/
  web.php                     # Rutas web
  console.php                 # Comandos Artisan

public/
  build/                      # Assets compilados por Vite

tests/
  Feature/
  Unit/

vendor/
node_modules/
storage/
```

## Arquitectura
- **Monolito Laravel** con Inertia como puente SPA
- Las rutas web.php definen endpoints: API de diseño, auth, editor, deploy
- El frontend Vue 3 se comunica con el backend via Inertia (no axios directo, excepto para autoguardado)
- El editor visual mantiene estado en cliente, con autoguardado periodico a `PUT /designer/state`
- Los disenos se crean via `POST /designer/designs` desde Home, y se actualizan en el editor

## Convenciones
- **PHP:** PSR-4, Laravel Pint, controladores agrupados por recurso
- **Vue:** Composition API con `<script setup>`, componentes en `resources/js/Components/`
- **CSS:** Tailwind utility classes + daisyUI componentes
- **Rutas:** Nombradas con `Route::name()` en web.php
- **Migraciones:** Con timestamps, nombres descriptivos
- **Tests:** PHPUnit, tests en `tests/Feature/`

## Areas funcionales
1. **Autenticacion** — Login JWT con portal externo (TSEYOR)
   - Archivos: app/Http/Controllers/AuthController.php, config/jwt.php, config/portal.php
2. **Home/Gestor de disenos** — Listado de proyectos recientes, disenos publicos de la comunidad
   - Archivos: app/Http/Controllers/DesignController.php, resources/js/Pages/Home.vue
3. **Asistente de diseno** — Modal wizard para configurar objetivo, formato, datos y plantilla
   - Archivos: resources/js/Components/designer/DesignerAssistant.vue, StepFooter.vue
4. **Editor visual** — Lienzo con textos, imagenes, formas, fondo, undo/redo, autoguardado
   - Archivos: resources/js/Pages/Designer/EditorPage.vue, resources/js/Components/designer/*.vue, app/Http/Controllers/DesignerController.php
5. **Plantillas** — CRUD de plantillas base, generacion de demos
   - Archivos: app/Http/Controllers/DesignTemplateController.php, app/Models/DesignTemplate.php, app/Services/DesignTemplateGenerator.php, app/Services/DemoTemplateFactory.php
6. **Subida de imagenes** — Assets para disenos
   - Archivos: app/Http/Controllers/DesignAssetController.php, app/Models/DesignAsset.php
7. **Exportacion** — Exportar diseno a imagen
   - Archivos: resources/js/Components/designer/ExportDialog.vue, resources/js/html-2-image/
8. **Deploy** — Compresion y envio de public/build a servidor remoto
   - Archivos: app/Http/Controllers/DeployController.php, app/Services/DeployHelper.php, config/deploy.php
9. **Fuentes** — Servir fuentes locales para el editor
   - Archivos: app/Http/Controllers/FontController.php, config/designer.php

## Documentacion relevante
- README.md — Instalacion, configuracion, comandos utiles
- TODO.md — Tareas pendientes
- OPORTUNIDADES.md — Mejoras potenciales
- PLANTILLAS.md — Guia de plantillas
- EDITOR.md — Detalles del editor
- REGLAS_TEXTO_ENLAZABLE.md — Reglas de negocio para texto enlazable
- TEXTO_ENLAZABLE_TECNICA.md — Detalle tecnico de texto enlazable
