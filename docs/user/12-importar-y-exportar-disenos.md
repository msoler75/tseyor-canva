# Importar y exportar diseños (.tc)

Tseyor Canva permite exportar e importar diseños completos usando archivos `.tc` (Tseyor Canvas). Es una forma de guardar tu trabajo localmente, compartirlo con otras personas o moverlo entre dispositivos.

## Exportar un diseño

1. Abre el diseño que quieras exportar en el editor.
2. En la barra superior, ve al menú de acciones (tres puntos verticales).
3. Selecciona **"Exportar como .tc"**.
4. El navegador descargará un archivo con el nombre de tu diseño y extensión `.tc`.

El archivo `.tc` contiene:
- El contenido textual y estructura del diseño
- La disposición y estilos de cada elemento
- Las imágenes (incrustadas como data URI, no como enlaces externos)
- La configuración de formato, tamaño y superficie de diseño

## Importar un diseño

1. En la pantalla de inicio, pulsa el botón **"Importar .tc"** (junto al botón CREAR).
2. Selecciona el archivo `.tc` que quieras importar.
3. El diseño se abrirá automáticamente en el editor, listo para modificar o exportar de nuevo.

## Limitaciones

- **Tamaño**: Los archivos `.tc` pueden ser grandes si contienen muchas imágenes de alta resolución, ya que éstas se incrustan en el propio archivo.
- **Imágenes externas**: Las imágenes alojadas en servidores externos (que no sean de Tseyor Canva) se intentarán descargar durante la exportación. Si no se puede acceder a ellas, se mantendrá la URL original.
- **Recursos del servidor**: Al importar un `.tc`, las imágenes se marcan para subirse al servidor. Si no hay conexión, aparecerán como datos locales pero no se conservarán al recargar la página.
