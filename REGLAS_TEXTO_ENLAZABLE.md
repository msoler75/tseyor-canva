# REGLAS_TEXTO_ENLAZABLE.md

## Reglas de Comportamiento del Texto Enlazable

---


### -1. LOS TEXTOS ENLAZABLES ACTUAN COMO UN SOLO FLUJO

Se trata de un sistema de un flujo de texto, con una unica fuente de verdad, o texto original, que se distribuye en varias ventanas o marcos o "cajas" de forma secuencial.

Al igual que Microsoft Word distribuye el texto a lo largo de varias páginas y se puede editar el texto y así las palabras del texto se redistribuyen dinámicamente, ese flujo y adaptación dinámica es lo que perseguimos en los elementos de Texto enlazable y sus secuencias de elementos enlazados.

Se trata de crear secuencias de 1, 2 o más cajas de texto enlazable, que actúan como ventanas del texto fuente u original, que muestran cada una de las cajas el texto segun su espacio disponible, para dar cabida a las palabras del texto, sin desbordar dichas palabras más allá de los límites de cada caja de texto.

Cuando las cajas no tienen espacio suficiente para admitir todo el texto original, tiene que haber una forma visual de informar al usuario que el texto está "desbordando" (overflow) el espacio disponible de la secuencia de cajas. Más adelante se especifica el modo de visualizar esta situación.

### 0. LAS CAJAS DE TEXTO DE LOS ELEMENTOS DE TEXTO ENLAZABLE PUEDEN ENLAZARSE

Al final de cada caja de texto (abajo a la derecha) hay una flecha. si se pulsa con el mouse/touch y se arrastra, se visualiza una linea que puedes arrastrarla a otra caja y soltar el botón del mouse/touch. En cuyo caso has creado un vinculo entre dos cajas enlazables y una secuencia sagrada. se puede secuenciar más de dos cajas tomando de la ultima un enlace hacia una nueva caja de texto enlazable.

El enlace se visualiza con una linea, esa linea se puede ver solo cuando cualquiera de los elementos de una misma secuencia de textos enlazables está activada/seleccionada o en edición. La Linea va desde la flecha de enlace hacia la caja siguiente en su esquina superior izquierdo.

Se puede romper/cambiar un enlace arrastrando desde la flecha hacia otra ubicación/caja. En tal caso el texto se redistribuirá apropiadamente a la nueva secuencia.

Una caja que tenga texto propio perderá su texto cuando se le enlaza en la entrada un nuevo enlace procedente de una caja de texto enlazable "origen". 


### 1. REGLA FUNDAMENTAL: La caja NUNCA crece por sí sola

La caja de texto enlazable tiene unas dimensiones fijas (`w` y `h`) que **solo cambian cuando el usuario las redimensiona manualmente** (arrastrando los handles). El sistema de texto enlazable NUNCA modifica las dimensiones de la caja.

```
✅ CORRECTO: La caja mantiene siempre su tamaño
┌──────────────┐    ┌──────────────┐
│ Texto que    │    │ Texto que    │
│ cabe en la   │    │ cabe en la   │
│ caja         │    │ caja         │
└──────────────┘    └──────────────┘
  Texto restante      ← texto overflow 50% opacity (solo visible cuando elementos activos/focus)
  visible debajo
```

```
❌ INCORRECTO: La caja crece para ajustarse al texto
┌──────────────────┐
│ Texto que cabe   │
│ Texto que no     │  ← ¡NUNCA! La caja NO crece
│ cabía antes      │
└──────────────────┘
```

---

### 2. Flujo de Texto

El texto es un **flujo continuo** que se distribuye entre las cajas de la cadena:

1. El texto se escribe en la **primera caja** (head) de la cadena
2. Cuando la primera caja se llena, el texto restante fluye a la **siguiente caja**
3. Si no hay más cajas en la cadena, el texto restante se muestra como **overflow** con opacidad 50% (y solo se muestra si la cadena de elementos de texto está enfocada o activa)

---

### 3. Modo Edición (Edit)

Cuando el usuario está editando un texto enlazable:

- **La caja mantiene sus dimensiones fijas** (NO crece)
- El editor TipTap permite escribir **todo el texto que se quiera**
- El texto que desborda la caja es **visible** (overflow: visible) cuando cualquier caja de texto enlazable de una misma cadena está seleccionada o en edición, para que el usuario pueda ver lo que escribe. 
- Si no hay ningun elemento de texto enlazable de la cadena seleccionado, activo o en edición, el texto overflow es **invisible**! (es como que se aplica overflow: hidden en la caja)
- El cursor inicia al final del texto, permitiendo seguir escribiendo, incluido espacios. Luego se puede mover el cursor libremente hacia otros puntos del texto.
- **se redistribuye** texto entre cajas **dinámicamente** después **de cada edición, inserción o modificación del texto o su estilo**

---

### 4. Modo Display (Idle)

Cuando el usuario NO está editando:

- Cada caja muestra **solo el fragmento de texto que le corresponde**
- El fragmento se calcula midiendo palabra por palabra con el navegador
- El texto que no cabe en ninguna caja de la cadena **no se muestra**, a menos que esté el elemento de texto seleccionado, entonces se muestra como **overflow** con opacidad 50%
- El overflow solo se muestra en la **última caja** de la cadena
- El concepto 'overflow' no significa necesariamente CSS overflow, significa que es texto que excede la capacidad del contenedor

---

### 5. Redistribución

La redistribución del texto ocurre cuando:

- El usuario **termina cualquier edición, por leve que sea** (commitTextEdit)
- El usuario **redimensiona** una caja de la cadena
- Se **conectan o desconectan** cajas enlazadas

La redistribución NO ocurre:
- Mientras el usuario arrastra/mueve una caja

---

### 6. Overflow (Texto Desbordado)

El texto que no cabe en la cadena de cajas se muestra como overflow:

- Solo aparece en la **última caja** de la cadena (si hay algun elemento de la cadena seleccionado)
- Se renderiza con **opacidad 50%**
- Se posiciona **debajo** de la última caja (no la tapa) como si el texto continuara
- Se actualiza cada vez que se redistribuye el texto

---

### 7. Estilos

- Los estilos se aplican a nivel de **toda la caja** (todo el texto del elemento), a nivel de **párrafo** (cada línea de texto) o a nivel de **palabra** o **carácter**. Pero depende del estilo.
    - Estilos que se aplican a nivel de **párrafo** son: alineación (derecha, izquierda, centro, justificado), espaciado+interlineado, tipo de fuente, mayúsculas (si/no).
    - Estilos que se aplican a nivel de **palabra** o **caracter** son: color, negrita, cursiva, tamaño de fuente, 
    - Estilos que se aplican a **toda la caja** son: opacidad/transparencia, efectos, posicion, borde.
- Los estilos se **preservan** durante la fragmentación y redistribución, partiendo el texto en **palabras**. Si un párrafo se parte entonces se crea otro párrafo en el siguiente elemento de la cadena de texto enlazable, con los mismos estilos de párrafo y la siguiente palabra del corte, y el resto del texto a continuación.
- Se sugiere usar `<span>` para definir estilos concretos de palabras o caracteres.
- El HTML fragmentado mantiene los atributos `style` de cada `<p>` y de cada `<span>`

---

### 8. Medición de Fragmentación

El sistema de fragmentación:

1. Parsea el HTML en párrafos con sus estilos
2. Crea un contenedor temporal **fuera de la pantalla** con las mismas dimensiones y estilos que la caja
3. Añade palabras una por una y mide la **altura real** con `offsetHeight`
4. Cuando una palabra excede la altura del frame, corta y pasa al siguiente frame
5. El navegador hace el layout → resultado pixel-perfect

---

### 9. Unicidad de Fuente

El texto en modo display y modo edición debe verse **idéntico**:

- Mismo `font-family`
- Mismo `font-size`
- Mismo `line-height`
- Mismo `letter-spacing`
- Mismo `color`
- Mismo `white-space` y `word-break`

Para garantizar esto, los estilos CSS de `.ProseMirror` (edición) y `.linked-text-display` (display) deben ser **idénticos**.

---

### 10. Duplicación de páginas con texto enlazable

Cuando se duplica una página que contiene cajas de texto enlazable (`linkedText`), **todas las cajas enlazables de la página duplicada se convierten en cajas independientes (standalone)**, sin enlaces entre sí ni con las cajas de la página original.

**Reglas:**
- A cada caja `linkedText` del clon se le asigna un **nuevo `linkedTextGroupId`** único
- Se limpian `linkedTextNext`, `linkedTextPrev` y `linkedTextChainIndex` (valor por defecto: 0)
- Se copia el contenido visible (`html`/`text`) del fragmento que mostraba esa caja en la página original. Si el fragmento no está disponible (página no activa), se usa el texto completo del `head` de la cadena original como fallback
- Esto evita colisiones de identidad entre páginas y cadenas corruptas cross-page

**Motivo:** `clonePlain` (deep clone via `JSON.parse(JSON.stringify(...))`) preserva los `linkedTextGroupId`, `linkedTextNext` y `linkedTextPrev` originales, creando referencias fantasma entre dos páginas distintas. La sanitización rompe estos enlaces explícitamente.

---

### 11. Clonación de caja grande (>60% altura de página)

Al clonar una caja de texto enlazable cuya altura (`h`) supera el **60% de la altura de la página** (`editorCanvasDimensions.height`), la nueva caja clonada **se coloca en la siguiente "página" lógica** (misma posición relativa), en lugar de en la página actual con offset.

- **Documento normal:** la caja va a `state.pages[currentIndex + 1]`, misma posición `(x, y)`
- **Formato folleto:** cada página física tiene dos paneles (izquierdo y derecho) que representan dos páginas de folleto consecutivas en el flujo de lectura:
  - Si la caja está en el **panel izquierdo** (`x < halfWidth`): el clon va al **panel derecho** de la **misma** página física, en `x + halfWidth`
  - Si la caja está en el **panel derecho** (`x >= halfWidth`): el clon va al **panel izquierdo** de la **siguiente** página física, en `x - halfWidth`
- Si **no hay página/panel siguiente**, se aplica el comportamiento normal (offset +18px en la misma página)
- La caja clonada se **intercala en la cadena** entre la caja origen y su antiguo `next` (cadena cross-page, soportada por `linkedTextLayoutFromAnyPage()`)

**Motivo:** Una caja que ocupa más del 60% de la página probablemente está llena de texto. Su clon natural es una continuación en la página siguiente (o panel siguiente en folleto), imitando el flujo de texto entre páginas.

---

### 12. Robustez ante undo/redo

Al aplicar undo o redo (`applyHistorySnapshot`), el sistema de texto enlazable limpia su caché interno de fragmentos (`linkedTextBoxSystem.resetAllSystems()`) **antes** de restaurar el estado. Esto fuerza que los fragmentos se recalculen desde cero a partir del estado restaurado, evitando datos stale.

- El **texto global** (`html`/`text` en `customElements[headId]`) se preserva íntegramente porque está almacenado en el snapshot de historial
- La caché de fragmentos (`systemsMap`, `fragments`) es **datos derivados** que se reconstruyen bajo demanda cuando `getLinkedTextBoxText()` detecta el sistema vacío
- El watcher de redistribución (línea 5073) también reactiva el recálculo para toda cadena detectada en `state.elementLayout`

**Motivo:** El singleton `useLinkedTextBoxSystem` retiene fragmentos calculados del estado previo al undo. Sin limpieza, `getLinkedTextBoxText()` encuentra fragmentos stale que no corresponden al estado restaurado.

