// Carga dinámica de fuentes locales (solo variantes necesarias)
// Uso: loadFont('Bebas Neue', 400, 'normal')
// Siempre usa rutas same-origin para evitar problemas CORS con html-2-image


// Detecta la ruta base de fuentes según variable global inyectada desde Blade
let FONT_BASE = '/fonts';
if (window && window.DESIGNER_FONTS_BASE) {
    FONT_BASE = window.DESIGNER_FONTS_BASE;
}

/**
 * Carga dinámicamente una variante de fuente local si no está ya cargada.
 * @param {string} family - Nombre de la fuente (ej: 'Bebas Neue')
 * @param {number} weight - Peso (ej: 400, 700)
 * @param {string} style - Estilo ("normal", "italic")
 * @returns {Promise<void>} Resuelve cuando la fuente está lista para usarse
 */
export async function loadFont(family, weight = 400, style = 'normal') {
    const fontId = `${family}-${weight}-${style}`.replace(/\s+/g, '_');
    if (document.getElementById('font-' + fontId)) return;

    // Construye la ruta al CSS de la variante
    // Ejemplo: /fonts/Bebas_Neue-400-normal.css
    const cssHref = `${FONT_BASE}/${family.replace(/\s+/g, '_')}-${weight}-${style}.css`;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = cssHref;
    link.id = 'font-' + fontId;
    link.crossOrigin = 'anonymous';
    document.head.appendChild(link);

    // Espera a que la fuente esté disponible (FontFaceSet API)
    const fontFace = `${style} ${weight} 1em '${family}'`;
    await document.fonts.load(fontFace);
}

// Ejemplo de uso en un componente Vue:
// await loadFont('Bebas Neue', 400, 'normal');
// await loadFont('Bebas Neue', 700, 'italic');
