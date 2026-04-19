# TSEYOR Canva

TSEYOR Canva es una aplicación Laravel + Inertia + Vue para crear, editar y exportar diseños gráficos desde el navegador. Incluye un asistente modal para configurar objetivo, formato, datos y plantilla, un editor visual con guardado automático, gestión de proyectos recientes, diseños públicos de comunidad, subida de imágenes y exportación a imagen.

## Stack principal

- **Backend:** Laravel 12, PHP 8.2+
- **Frontend:** Vue 3, Inertia, Vite
- **UI:** Tailwind CSS 4 + daisyUI
- **Editor rich text:** TipTap
- **Exportación de imagen:** html-to-image local en `resources/js/html-2-image`
- **Base de datos:** MySQL por defecto en `.env.example`

## Funcionalidades

- Home con proyectos recientes del usuario y diseños públicos de la comunidad.
- Asistente de diseño integrado en modal:
  - Objetivo
  - Formato/dimensiones
  - Campos/datos
  - Plantilla
- Editor visual con:
  - textos editables,
  - imágenes,
  - formas,
  - fondo sólido/degradado/imagen,
  - historial undo/redo,
  - autoguardado en `/designer/state`,
  - miniaturas automáticas.
- Exportación desde diálogo modal dentro del editor.
- Deploy remoto de `public/build` mediante comando Artisan y endpoint receptor.

## Requisitos

- PHP 8.2 o superior
- Composer
- Node.js + npm
- MySQL/MariaDB
- Extensiones PHP habituales de Laravel, más:
  - `zip` para crear/descomprimir el paquete de despliegue,
  - `curl` para enviar el ZIP con `php artisan deploy:build`.

## Instalación local

```bash
composer install
npm install
cp .env.example .env
php artisan key:generate
```

Configura la base de datos en `.env`:

```env
DB_CONNECTION=mysql
DB_HOST=localhost
DB_PORT=3306
DB_DATABASE=tseyor_canva
DB_USERNAME=root
DB_PASSWORD=
```

Ejecuta migraciones:

```bash
php artisan migrate
```

Compila assets:

```bash
npm run build
```

O levanta entorno de desarrollo:

```bash
composer run dev
```

Ese comando arranca, en paralelo:

- `php artisan serve`
- cola Laravel
- logs con `pail`
- Vite dev server

También puedes ejecutarlos por separado:

```bash
php artisan serve
npm run dev
```

## Variables de entorno relevantes

### Aplicación

```env
APP_NAME="TSEYOR Canva"
APP_ENV=local
APP_DEBUG=true
APP_URL=http://localhost:8000
```

### Fuentes locales

Para desarrollo con `php artisan serve`, puede ser útil servir fuentes desde Laravel:

```env
DESIGNER_SERVE_FONTS_ROUTE=true
```

Si está activo, se habilita:

```text
/fonts/{filename}
```

### Procesado de imágenes

```env
DESIGNER_IMAGE_MAX_WIDTH=2400
DESIGNER_IMAGE_MAX_HEIGHT=2400
DESIGNER_IMAGE_JPEG_QUALITY=95
DESIGNER_IMAGE_WEBP_QUALITY=95
```

### Login portal / JWT

```env
JWT_SECRET=
JWT_TTL=10080

PORTAL_LOGIN_URL=https://tseyor.org/tseyor-canva
PORTAL_LOGIN_CALLBACK_PARAMETER=from
```

## Comandos útiles

Tests:

```bash
php artisan test
```

Tests de la parte de editor/estado:

```bash
php artisan test tests/Feature/DesignerSessionStateTest.php
```

Formateo PHP:

```bash
vendor/bin/pint
```

Build frontend:

```bash
npm run build
```

Crear o actualizar 3 plantillas base genéricas para pruebas:

```bash
php artisan designer:create-demo-templates
```

Opciones útiles:

```bash
php artisan designer:create-demo-templates \
  --admin-email=admin@example.com \
  --admin-name=admin \
  --password=password \
  --status=published
```

El comando es idempotente: si se ejecuta varias veces, actualiza las mismas 3 plantillas y sus diseños base sin duplicarlos. `--status` acepta `draft`, `published` o `archived`.

## Estructura relevante

```text
app/
  Http/Controllers/
    DesignerController.php   # Home, editor, estado, uploads, thumbnails
    DesignController.php     # CRUD de diseños guardados
    DeployController.php     # Endpoint receptor del deploy de public/build
  Services/
    DeployHelper.php         # ZIP, envío, validación y extracción de build

resources/js/
  Pages/
    Home.vue
    Designer/EditorPage.vue
  Components/designer/
    DesignerAssistant.vue
    EditorTopBar.vue
    EditorContextPanel.vue
    EditorCanvasStage.vue
    ExportDialog.vue

routes/
  web.php
  console.php
```

## Flujo de guardado de diseños

El flujo esperado es:

1. Home abre el asistente.
2. Al pulsar **Abrir editor**, Home crea un único diseño con:

   ```http
   POST /designer/designs
   ```

3. El editor actualiza siempre ese mismo diseño con:

   ```http
   PUT /designer/state
   ```

4. El estado debe incluir:

   ```json
   {
     "state": {
       "currentDesignUuid": "uuid-del-diseno"
     }
   }
   ```

El backend rechaza autoguardados autenticados sin `currentDesignUuid` para evitar crear diseños duplicados accidentalmente.

## Deployment de `public/build`

La app incluye un mecanismo simple para desplegar solo los assets compilados de Vite (`public/build`) desde una instalación local/origen hacia un servidor/destino.

### Variables de deploy

En el entorno que **envía**:

```env
DEPLOY_ENDPOINT=https://tu-servidor.com/deploy/build
DEPLOY_TOKEN=un-token-largo-y-secreto
DEPLOY_VERIFY_SSL=true
DEPLOY_TIMEOUT=1800
```

En el servidor que **recibe**:

```env
DEPLOY_TOKEN=un-token-largo-y-secreto
DEPLOY_ROUTE_ENABLED=true
```

Si quieres desactivar el endpoint receptor:

```env
DEPLOY_ROUTE_ENABLED=false
```

### Endpoint receptor

La ruta receptora está definida en `routes/web.php`:

```text
POST /deploy/build
```

Controlador:

```text
App\Http\Controllers\DeployController@build
```

El endpoint espera:

- `mode=public_build`
- `file` con un ZIP
- header opcional/normalmente requerido si hay token:

```http
X-Deploy-Token: un-token-largo-y-secreto
```

### Comando de deploy

Primero genera la build:

```bash
npm run build
```

Luego despliega:

```bash
php artisan deploy:build
```

También puedes pasar opciones explícitas:

```bash
php artisan deploy:build \
  --endpoint=https://tu-servidor.com/deploy/build \
  --token=un-token-largo-y-secreto
```

Opciones disponibles:

```bash
--endpoint=URL   # sobrescribe DEPLOY_ENDPOINT
--token=TOKEN    # sobrescribe DEPLOY_TOKEN
--insecure       # no verifica SSL al enviar
--keep-zip       # conserva el ZIP temporal local
```

### Qué hace internamente

El comando:

1. Comprime `public/build` en un ZIP temporal dentro de `storage/app`.
2. Envía el ZIP al endpoint configurado.
3. El servidor valida el token.
4. `DeployController` guarda el ZIP temporalmente.
5. `DeployHelper` valida las entradas del ZIP.
6. Crea backup del `public/build` actual en:

   ```text
   storage/app/deploy-backups/_backup_public_build_YYYYMMDDHHMMSS
   ```

7. Descomprime el ZIP en el `public/build` del servidor.
8. Mantiene los últimos 5 backups.

### Notas de seguridad

- Configura siempre `DEPLOY_TOKEN` en producción.
- Sirve `/deploy/build` solo por HTTPS.
- Si el endpoint no se va a usar, pon:

  ```env
  DEPLOY_ROUTE_ENABLED=false
  ```

- El ZIP se valida para evitar rutas inseguras, rutas absolutas, `../`, ficheros `.php`, `storage/` y `vendor/`.

## Troubleshooting

### `No existe public/build`

Ejecuta:

```bash
npm run build
```

### Error SSL al desplegar

Comprueba el certificado del servidor. Solo para pruebas puedes usar:

```bash
php artisan deploy:build --insecure
```

### 403 en `/deploy/build`

El token del cliente no coincide con el del servidor. Revisa:

```env
DEPLOY_TOKEN=
```

### 404 en `/deploy/build`

Revisa en el servidor:

```env
DEPLOY_ROUTE_ENABLED=true
```

Y confirma la ruta:

```bash
php artisan route:list --path=deploy
```
