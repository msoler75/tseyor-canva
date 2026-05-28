# Texto Enlazable

(Fuente original: `REGLAS_TEXTO_ENLAZABLE.md`)

## Concepto

Las cajas de texto enlazable actúan como un **único flujo de texto** distribuido en múltiples ventanas. Similar al flujo de texto de Word entre páginas: el texto escrito en la primera caja continúa automáticamente en la siguiente cuando se llena.

## Cómo crear una secuencia

1. Crear un elemento de "texto enlazable" desde el panel de inserción
2. Crear otra caja de texto enlazable
3. Arrastrar la flecha 🔽 de la primera caja a la segunda
4. La línea de enlace confirma la conexión

## Reglas fundamentales

- **Las cajas nunca crecen solas**: el tamaño es fijo, cambia solo al redimensionar
- **El texto fluye en secuencia**: C1 → C2 → C3 (no hay bifurcaciones)
- **Cada caja tiene una sola entrada**: una caja no puede recibir de dos orígenes
- **Al enlazar, se pierde el texto propio**: si una caja tenía texto propio, se reemplaza por el flujo entrante

## Modo display

- Cada caja muestra solo el fragmento que le cabe
- El overflow (texto sobrante) se ve gris semitransparente solo cuando la cadena está activa

## Modo edición

- El editor TipTap muestra todo el texto, con scroll
- Al salir, el texto se redistribuye automáticamente entre las cajas
- Los estilos (negrita, color, tamaño) se preservan en la redistribución

## Editar desde cualquier caja

Al hacer doble click en una caja intermedia, el editor se posiciona exactamente donde empieza el texto de esa caja.

## Visualización de enlaces

- La línea de enlace se ve solo cuando algún elemento de la cadena está seleccionado
- La línea va desde la flecha de salida a la esquina superior izquierda de la caja destino

## Romper/cambiar enlaces

Arrastrar la flecha 🔽 a otra caja o al vacío:
- Si suelta en otra caja: el enlace se redirige
- Si suelta en vacío: el enlace se rompe, la caja siguiente se independiza

## Clonación

- Clonar una caja enlazable con `linkedTextNext` → el clon se añade al **final** de la cadena
- La ubicación depende del tamaño: si la caja supera el 60% de la página, el clon va a la siguiente página/panel

## Overflow

El texto que no cabe en la cadena se muestra:
- Solo en la última caja
- Con opacidad reducida
- Solo visible si hay un elemento de la cadena seleccionado

## Duplicación de páginas

Al duplicar una página con cajas enlazables, cada caja duplicada se convierte en **independiente** (pierde sus enlaces). Esto evita referencias entre páginas.
