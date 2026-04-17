<!DOCTYPE html>
<html lang="es" class="h-full">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title inertia>TSEYOR Canva</title>
        <!-- Fuentes locales generadas: solo variantes normales -->
        <link rel="stylesheet" href="/{{ config('designer.serve_fonts_route') ? 'fonts/fonts.css' : 'fontsx/fonts.css' }}" crossorigin="anonymous" />
        <!-- Fin fuentes locales -->
        <script>
            window.DESIGNER_FONTS_BASE = "/{{ config('designer.serve_fonts_route') ? 'fonts' : 'fontsx' }}";
        </script>
        @vite(['resources/css/app.css', 'resources/js/app.js'])
        @inertiaHead
    </head>
    <body class="h-full antialiased">
        @inertia
    </body>
</html>
