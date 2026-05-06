# Editor

## Pagina activa

La pagina activa es la pagina que tiene el foco operativo del editor. Puede venir de la visibilidad por scroll o de una seleccion explicita del usuario con el mouse.

Este foco no forma parte del documento guardado: es estado interno de la UI del editor. Su funcion es decidir donde se aplican acciones de insercion, por ejemplo al agregar textos, imagenes, figuras o elementos enlazables.

Regla importante: cambiar la pagina activa solo debe cambiar indicadores de UI, como un borde o sombra de pagina. No debe modificar contenido, estilos, alturas de cajas, splits de texto enlazable, snapshots del documento ni formato de ningun elemento.
