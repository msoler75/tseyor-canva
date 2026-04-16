// Configuración común para html-2-image en todo el proyecto

export const html2imageCssFilter = (href) => href ? href.includes('fonts.css') : false;

export const html2imageDefaultOptions = {
    // Solo permitir fonts.css en el escaneo de hojas de estilo:
    cssFilter: html2imageCssFilter,
};
