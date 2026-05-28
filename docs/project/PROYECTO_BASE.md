# TSEYOR Canva — Proyecto Base

Stack: Laravel 12, Vue 3 (Composition API), Inertia 3, Vite 7, Tailwind CSS 4, daisyUI 5, TipTap 3, MySQL.

## Estructura del proyecto

```
app/Http/Controllers/   — Auth, Design, Designer, Deploy, DesignAsset, DesignTemplate, Font, FrontendLog
app/Models/             — Design, DesignAsset, DesignTemplate, User
app/Services/           — DemoTemplateFactory, DeployHelper, DesignTemplateGenerator
resources/js/           — Vue SPA: Pages/ (Home, Designer/EditorPage), Components/designer/, composables/
routes/                 — web.php, console.php
tests/                  — Feature/, Unit/
```

## Arquitectura

- Monolito Laravel con Inertia como puente SPA
- Editor visual mantiene estado en cliente con autoguardado periódico a `PUT /designer/state`
- Diseños creados via `POST /designer/designs` desde Home
- JWT auth con portal externo TSEYOR

## Áreas funcionales

1. Autenticación JWT
2. Home / Gestor de diseños
3. Asistente de diseño (objetivo, formato, datos, plantilla)
4. Editor visual (lienzo, textos, imágenes, formas, fondo, undo/redo)
5. Plantillas (CRUD, generación demos)
6. Subida de imágenes
7. Exportación a imagen
8. Deploy de assets
9. Fuentes locales

## Convenciones

- PHP: PSR-4, Laravel Pint, controladores por recurso
- Vue: Composition API con `<script setup>`
- CSS: Tailwind utility + daisyUI
- Tests: PHPUnit

## Documentación

Ver `docs/` para documentación completa de usuario y técnica.
