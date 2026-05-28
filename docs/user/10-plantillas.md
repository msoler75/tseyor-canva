# Plantillas

(Fuente original: `PLANTILLAS.md`)

## Concepto

Una plantilla es un diseño base preparado para reutilización. Al usar una plantilla:

1. Se selecciona según objetivo y categoría
2. Se adapta automáticamente al formato elegido
3. Se rellenan los datos desde el asistente
4. Se genera un nuevo diseño editable

## Categorías

Las plantillas se clasifican por:
- **Categoría**: tipo de pieza (cartel, folleto, invitación, diploma, etc.)
- **Objetivo**: para qué sirve (anunciar evento, invitar, comunicar, etc.)
- Una plantilla puede tener múltiples objetivos

## Uso desde el asistente

1. Abrir el asistente de diseño
2. Definir objetivo y formato
3. Elegir plantilla de las disponibles (filtradas por páginas si aplica)
4. Rellenar datos (título, subtítulo, contacto, etc.)
5. El sistema adapta la plantilla al formato

## Crear plantillas (admin)

Solo usuarios admin pueden:
- Publicar un diseño como plantilla
- Definir categorías y objetivos
- Configurar mapeo de campos

## Demo

Para generar plantillas de prueba:
```bash
php artisan designer:create-demo-templates
```

Crea 3 plantillas genéricas con sus diseños base. Es idempotente.
