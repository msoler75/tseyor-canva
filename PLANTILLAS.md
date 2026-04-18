# PLANTILLAS

Este documento recoge las bases acordadas para el futuro modelo de plantillas de diseño en la aplicación.

La idea principal es mantener el sistema **simple, flexible y evolutivo**: una plantilla debe ayudar al usuario a crear un diseño propio rápidamente, sin convertir el editor en un motor complejo de branding, slots, responsive avanzado o configuración excesiva.

---

## 1. Concepto general

Una **plantilla** es un diseño base estable, publicado como recurso reutilizable, que el asistente puede usar para generar nuevos diseños personalizados.

Una plantilla:

- parte de un diseño base;
- está clasificada por categoría y objetivo;
- puede recibir campos de datos del asistente;
- puede mapear, reinterpretar o trasladar esos campos a elementos concretos del diseño;
- puede adaptarse automáticamente a cualquier formato;
- genera un nuevo diseño editable por el usuario.

La plantilla no debe entenderse como un simple duplicado de un diseño existente, sino como una **base preparada para reutilización**.

Técnicamente, usar una plantilla puede implicar clonar un diseño base, pero conceptualmente es distinto:

- **Clonar diseño**: copiar un diseño concreto para editarlo.
- **Usar plantilla**: crear un diseño nuevo a partir de una base estable, clasificada y preparada para recibir datos.

---

## 2. Entidad principal: `DesignTemplate`

El modelo recomendado es una entidad propia llamada `DesignTemplate`.

No se recomienda resolverlo únicamente con un campo como `design.isTemplate`, porque la plantilla necesita metadatos propios y comportamiento específico.

Modelo conceptual:

```ts
type DesignTemplate = {
  id: string;

  title: string;
  description?: string;

  baseDesignId: string;

  categoryIds: string[];
  objectiveIds: string[];

  adaptationMode: 'proportional';

  fieldMappings?: TemplateFieldMapping[];

  status: 'draft' | 'published' | 'archived';

  featured?: boolean;
  sortOrder?: number;

  createdAt: string;
  updatedAt: string;
  publishedAt?: string;
};
```

Notas:

- `baseDesignId` apunta al diseño base usado para generar nuevos diseños.
- `categoryIds` clasifica qué tipo de pieza es.
- `objectiveIds` indica para qué objetivos del usuario sirve.
- `fieldMappings` añade flexibilidad para adaptar campos de datos a la plantilla.
- `adaptationMode` de momento será proporcional.
- No se define por ahora una lista de formatos soportados, porque todas las plantillas deben poder usarse en cualquier formato.

---

## 3. Diseño base

Cada plantilla parte de un diseño base existente.

Ese diseño base contiene:

- elementos gráficos;
- textos;
- imágenes;
- figuras;
- capas;
- estilos;
- sombras;
- colores;
- fuentes;
- posiciones;
- tamaños;
- orden Z.

La plantilla no necesita redefinir colores, fuentes ni branding, porque esos valores ya forman parte del diseño base.

El usuario podrá modificar colores, fuentes, imágenes o cualquier elemento manualmente después de generar su diseño.

Por ahora no se añadirá configuración específica para:

- color principal;
- paleta;
- color de marca;
- branding;
- tema visual;
- estilos globales personalizables.

---

## 4. Categorías y objetivos

Las plantillas deben poder clasificarse según dos ejes distintos.

### Categoría

La categoría describe **qué tipo de pieza es**.

Ejemplos:

- cartel;
- invitación;
- comunicado;
- portada;
- diploma;
- imagen para redes;
- programa;
- ficha;
- folleto;
- certificado.

### Objetivo

El objetivo describe **para qué quiere el usuario crear el diseño**.

Ejemplos:

- anunciar un evento;
- invitar a participar;
- comunicar una noticia;
- compartir una reflexión;
- presentar una actividad;
- crear material para redes;
- agradecer;
- preparar documentación.

Una misma plantilla puede servir para varios objetivos.

Ejemplo:

```ts
objectiveIds: [
  'announce-event',
  'invite-participants',
  'share-reflection'
]
```

Esto evita duplicar plantillas casi iguales para usos parecidos.

---

## 5. Formatos

Por ahora, todas las plantillas deben poder usarse en cualquier formato.

No se añade todavía un campo como:

```ts
supportedFormats: TemplateFormat[];
```

La razón es que, en esta fase, el objetivo es que toda plantilla pueda adaptarse automáticamente al formato elegido.

Más adelante, si se detecta que ciertas plantillas no quedan bien en algunos formatos, se podrá añadir configuración para activar o desactivar formatos concretos.

La decisión actual es:

> Toda plantilla se intenta adaptar a cualquier formato mediante recolocación proporcional automática.

---

## 6. Campos de datos

El asistente ya trabaja con campos de datos. La plantilla debe reutilizar esos campos, no crear necesariamente un segundo modelo paralelo.

Ejemplos de campos de datos:

```ts
{
  title: 'Encuentro de meditación',
  subtitle: 'Una jornada de interiorización',
  date: '2026-05-12',
  location: 'Barcelona',
  datos1: 'contacto@ejemplo.org'
}
```

Si el diseño base ya contiene elementos asociados a campos de datos, esos vínculos pueden reutilizarse directamente.

Ejemplo conceptual:

```ts
type DesignElement = {
  id: string;
  type: 'text' | 'image' | 'shape' | string;

  x: number;
  y: number;
  width: number;
  height: number;

  zIndex: number;

  dataField?: string;
};
```

Ejemplo:

```ts
{
  id: 'main-title',
  type: 'text',
  dataField: 'title'
}
```

Al generar un diseño desde plantilla, el sistema puede reemplazar automáticamente el contenido de los elementos que tengan `dataField`.

---

## 7. Mapeo de campos

Aunque los diseños puedan tener campos nombrados, sí interesa añadir un mecanismo de mapeo para casos más flexibles.

El mapeo permite que una plantilla pueda:

- trasladar un campo de datos a una ubicación concreta del diseño;
- usar un campo genérico con otro significado dentro de la plantilla;
- interpretar un campo como otro;
- adaptar plantillas a distintos conjuntos de datos;
- reutilizar plantillas aunque los nombres originales de campos no coincidan exactamente.

Ejemplo:

> Interpretar `datos1` como “datos de contacto” dentro de una plantilla.

Modelo simple:

```ts
type TemplateFieldMapping = {
  sourceField: string;
  targetField?: string;
  elementId?: string;
  property?: 'text' | 'src';
  label?: string;
};
```

Ejemplos:

```ts
{
  sourceField: 'datos1',
  targetField: 'contactInfo'
}
```

```ts
{
  sourceField: 'datos1',
  elementId: 'footer-contact',
  property: 'text',
  label: 'Datos de contacto'
}
```

```ts
{
  sourceField: 'image',
  elementId: 'main-image',
  property: 'src'
}
```

El mapeo debe entenderse como una capa de flexibilidad, no como una obligación para todos los casos.

Orden recomendado:

1. Si existe un `fieldMapping`, se aplica.
2. Si no existe, se usan los `dataField` ya definidos en los elementos del diseño.

---

## 8. No usar slots por ahora

El concepto de slot es interesante, pero no se considera imprescindible en esta fase.

Un slot implicaría modelar espacios o huecos del diseño, por ejemplo:

- zona de imagen principal;
- zona de título;
- zona de datos de contacto.

Eso puede ser útil en el futuro, pero también exige más interfaz de configuración en el editor.

Por ahora se prefiere algo más simple:

> Usar campos de datos existentes y, cuando haga falta, mappings entre campos y elementos.

Esto mantiene el modelo más fácil de implementar y entender.

---

## 9. Adaptación proporcional automática

La capacidad más importante de las plantillas será adaptarse automáticamente al formato elegido.

La idea no es construir un motor responsive complejo, sino recolocar los elementos de forma proporcional e inteligente.

Principios:

- no configurar anclajes manuales;
- no deformar imágenes ni figuras;
- conservar el orden Z;
- conservar estilos, sombras, colores, opacidades y rotaciones;
- recolocar elementos según su ubicación relativa al centro del diseño base;
- escalar tamaños con criterios conservadores;
- tratar fondos de forma especial;
- permitir que el resultado sea editable manualmente.

---

## 10. Recolocación relativa al centro

La recolocación se calculará automáticamente a partir de la posición del elemento.

No se guardarán anclajes como `top`, `bottom`, `left`, `right`.

Algoritmo conceptual:

1. Calcular el centro del diseño base.
2. Calcular el centro de cada elemento.
3. Calcular la distancia del elemento respecto al centro del diseño base.
4. Escalar esa distancia según el nuevo formato.
5. Colocar el elemento alrededor del centro del nuevo formato.

Ejemplo conceptual:

```ts
function repositionFromCenter(element, baseSize, targetSize, newSize) {
  const baseCenter = {
    x: baseSize.width / 2,
    y: baseSize.height / 2,
  };

  const targetCenter = {
    x: targetSize.width / 2,
    y: targetSize.height / 2,
  };

  const elementCenter = {
    x: element.x + element.width / 2,
    y: element.y + element.height / 2,
  };

  const scaleX = targetSize.width / baseSize.width;
  const scaleY = targetSize.height / baseSize.height;

  const dx = elementCenter.x - baseCenter.x;
  const dy = elementCenter.y - baseCenter.y;

  const newCenter = {
    x: targetCenter.x + dx * scaleX,
    y: targetCenter.y + dy * scaleY,
  };

  return {
    x: newCenter.x - newSize.width / 2,
    y: newCenter.y - newSize.height / 2,
  };
}
```

Este enfoque mantiene la intención compositiva:

- lo que estaba arriba sigue arriba;
- lo que estaba abajo sigue abajo;
- lo que estaba a la derecha sigue a la derecha;
- lo que estaba a la izquierda sigue a la izquierda;
- lo que estaba centrado sigue centrado.

---

## 11. Escalado de elementos

No se debe deformar por defecto.

Se calcularán:

```ts
scaleX = targetWidth / baseWidth;
scaleY = targetHeight / baseHeight;
uniformScale = Math.min(scaleX, scaleY);
```

### Imágenes

Las imágenes deben mantener proporción.

```ts
newWidth = element.width * uniformScale;
newHeight = element.height * uniformScale;
```

Si el editor ya soporta modos como `cover`, `contain` o recorte interno, se deben respetar.

### Figuras

Las figuras tampoco deberían deformarse por defecto.

```ts
newWidth = element.width * uniformScale;
newHeight = element.height * uniformScale;
```

### Textos

Los textos pueden adaptar su caja al nuevo formato, pero la fuente debe escalar con prudencia.

Ejemplo:

```ts
newWidth = element.width * scaleX;
newFontSize = element.fontSize * clamp(uniformScale, 0.85, 1.15);
```

La altura del texto puede mantenerse, recalcularse o depender del comportamiento actual del editor.

### Fondos

Los fondos son la excepción.

Si un elemento ocupa prácticamente todo el diseño base, debe tratarse como fondo.

Regla orientativa:

```ts
isBackgroundLike =
  element.width >= baseWidth * 0.9 &&
  element.height >= baseHeight * 0.9;
```

En ese caso:

```ts
x = 0;
y = 0;
width = targetWidth;
height = targetHeight;
```

---

## 12. Orden de capas y estilos

La adaptación de formato no debe modificar:

- `zIndex`;
- orden de capas;
- colores;
- sombras;
- opacidad;
- rotación;
- bordes;
- fuentes;
- filtros;
- estilos visuales.

Solo debería afectar, cuando corresponda, a:

- tamaño del canvas;
- `x`;
- `y`;
- `width`;
- `height`;
- tamaño de fuente, con límites prudentes.

Esto permite que un diseño bien construido se adapte sin perder su intención visual.

Por ejemplo, si una imagen de una maceta está por debajo del título en el orden Z, seguirá por debajo después de la adaptación.

---

## 13. Generación de diseño desde plantilla

Flujo recomendado:

1. Cargar la `DesignTemplate`.
2. Cargar el diseño base indicado por `baseDesignId`.
3. Clonar el diseño base.
4. Cambiar el canvas al formato elegido.
5. Recolocar y escalar elementos proporcionalmente.
6. Aplicar mappings de campos, si existen.
7. Aplicar campos de datos vinculados directamente a elementos.
8. Guardar el resultado como un nuevo `Design`.

El diseño generado:

- pertenece al usuario;
- es editable;
- no es una plantilla automáticamente;
- puede guardar una referencia a la plantilla de origen.

Ejemplo:

```ts
type Design = {
  id: string;
  name: string;
  ownerId: string;

  sourceTemplateId?: string;

  // resto del modelo actual de diseño
};
```

---

## 14. Flujo de administración

Si el usuario iniciado tiene `name === 'admin'`, tendrá opciones adicionales en el menú de diseño.

Opciones posibles:

- publicar como plantilla;
- editar datos de plantilla;
- despublicar plantilla;
- archivar plantilla.

Flujo básico:

1. Admin crea o abre un diseño base.
2. Configura los campos de datos en los elementos, si procede.
3. Publica el diseño como plantilla.
4. Define título y descripción.
5. Define categorías.
6. Define objetivos compatibles.
7. Añade mappings de campos si son necesarios.
8. Publica la plantilla.

---

## 15. Flujo de usuario en el asistente

Flujo previsto:

1. El usuario indica su objetivo.
2. El asistente muestra plantillas compatibles con ese objetivo.
3. El usuario elige una plantilla.
4. El usuario elige el formato deseado.
5. El sistema adapta la plantilla al formato.
6. El sistema rellena los campos disponibles.
7. Se crea un nuevo diseño editable.

La plantilla debe servir como punto de partida, no como resultado cerrado.

---

## 16. Validaciones recomendadas

Antes de publicar una plantilla, conviene validar:

- que tiene título;
- que tiene diseño base;
- que tiene al menos una categoría;
- que tiene al menos un objetivo;
- que el diseño base existe;
- que los mappings apuntan a elementos existentes;
- que las propiedades mapeadas son compatibles con el tipo de elemento;
- que no hay mappings duplicados ambiguos.

Ejemplos:

- No mapear una imagen a la propiedad `text`.
- No mapear un texto a la propiedad `src`.
- No apuntar a un `elementId` que ya no existe.

---

## 17. Decisiones explícitas

### Sí se incluye

- Entidad `DesignTemplate`.
- Diseño base mediante `baseDesignId`.
- Categorías.
- Objetivos múltiples.
- Mapeo opcional de campos.
- Adaptación proporcional automática.
- Recolocación relativa al centro.
- Escalado sin deformar imágenes ni figuras.
- Conservación de capas y estilos.
- Todas las plantillas utilizables en cualquier formato.

### No se incluye por ahora

- Slots.
- Anclajes configurables.
- Branding.
- Paletas de marca.
- `primaryColor` o colores configurables desde el asistente.
- Variantes manuales por formato.
- Lista configurable de formatos soportados.
- Motor responsive avanzado.
- Reglas condicionales complejas.

---

## 18. Definición final

Una `DesignTemplate` es:

> Un diseño base estable, publicado por admin como recurso reutilizable, clasificado por categorías y objetivos, que el asistente puede rellenar mediante campos de datos y mappings opcionales, y adaptar automáticamente a cualquier formato recolocando los elementos de forma proporcional respecto al centro del diseño, sin deformar imágenes ni figuras y manteniendo capas y estilos originales.
