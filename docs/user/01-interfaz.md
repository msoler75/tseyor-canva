# Interfaz del Editor

## Layout general

```
┌────────────────────────────────────────────────┐
│  EditorTopBar (guardar, deshacer, exportar...) │
├──────────────────┬─────────────────────────────┤
│  InsertSidebar   │  Canvas (lienzo)            │
│  (texto, img,    │  ┌─── Página activa ───┐   │
│   forma, QR,     │  │                      │   │
│   capas)         │  │  Elementos           │   │
│                  │  │                      │   │
│                  │  └──────────────────────┘   │
│                  │                             │
├──────────────────┴─────────────────────────────┤
│  FloatingToolbar (formato de texto)            │
└────────────────────────────────────────────────┘
```

## Panel izquierdo (InsertSidebar)

Permite añadir nuevos elementos al diseño:
- **Texto normal**: título, subtítulo, texto, texto enlazable
- **Imagen**: subir desde el equipo
- **Forma**: figuras predefinidas
- **Código QR**: generar desde datos
- **Capas**: orden Z de los elementos

## Barra superior (EditorTopBar)

- Deshacer/Rehacer
- Guardar
- Exportar
- Cambiar de plantilla
- Ajustes de página

## Página activa

La página activa tiene un borde destacado. Solo una página puede estar activa a la vez. Las acciones de inserción (añadir texto, imagen, etc.) se aplican siempre a la página activa. El cambio de página activa es solo visual y no modifica el contenido.
