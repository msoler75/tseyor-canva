// Centraliza la lógica de incrustación de fuentes para exportación de imágenes/canvas

let cachedFontEmbedCssPromise = null;

export function collectAccessibleFontFaceRules() {
    const styleSheets = Array.from(document.styleSheets || []);
    const rules = [];
    styleSheets.forEach((sheet) => {
        const href = sheet.href;
        // Solo procesar la hoja fonts.css (evita app.css y otras)
        console.log('Revisando stylesheet:', href);
        if (!href || !href.includes('fonts.css')) return;
        console.log('Procesando stylesheet de fuentes:', href);
        let sheetRules;
        try {
            sheetRules = sheet.cssRules;
        } catch (err) {
            // SecurityError: No se puede acceder a cssRules de hojas remotas o CORS
            return;
        }
        if (!sheetRules) return;
        const baseUrl = sheet.href || window.location.href;
        Array.from(sheetRules).forEach((rule) => {
            if (rule.type === CSSRule.FONT_FACE_RULE) {
                rules.push({ cssText: rule.cssText, baseUrl });
            }
        });
    });
    return rules;
}

function guessMimeType(url, responseContentType) {
    if (responseContentType) {
        return responseContentType.split(';')[0].trim();
    }
    const lower = url.toLowerCase();
    if (lower.endsWith('.woff2')) return 'font/woff2';
    if (lower.endsWith('.woff')) return 'font/woff';
    if (lower.endsWith('.ttf')) return 'font/ttf';
    if (lower.endsWith('.otf')) return 'font/otf';
    if (lower.endsWith('.eot')) return 'application/vnd.ms-fontobject';
    if (lower.endsWith('.svg')) return 'image/svg+xml';
    return 'application/octet-stream';
}

function blobToDataUrl(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(blob);
    });
}

async function inlineFontFaceCss(cssText, baseUrl) {
    const urlRegex = /url\((['"]?)([^'")]+)\1\)/g;
    const replacements = new Map();
    let match;
    while ((match = urlRegex.exec(cssText)) !== null) {
        const originalUrl = match[2].trim();
        if (!originalUrl || originalUrl.startsWith('data:') || originalUrl.startsWith('#')) continue;
        if (originalUrl.startsWith('local(')) continue;
        let absoluteUrl;
        try {
            absoluteUrl = new URL(originalUrl, baseUrl).toString();
        } catch {
            continue;
        }
        if (replacements.has(originalUrl)) continue;
        try {
            const response = await fetch(absoluteUrl, { credentials: 'same-origin' });
            if (!response.ok) continue;
            const blob = await response.blob();
            const mimeType = guessMimeType(absoluteUrl, response.headers.get('content-type') || blob.type);
            const normalizedBlob = blob.type ? blob : new Blob([blob], { type: mimeType });
            const dataUrl = await blobToDataUrl(normalizedBlob);
            replacements.set(originalUrl, dataUrl);
        } catch {
            continue;
        }
    }
    let inlinedCss = cssText;
    replacements.forEach((dataUrl, originalUrl) => {
        const escaped = originalUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        inlinedCss = inlinedCss.replace(new RegExp(`url\\((['"]?)${escaped}\\1\\)`, 'g'), `url("${dataUrl}")`);
    });
    return inlinedCss;
}

async function buildExportFontEmbedCss() {
    const fontRules = collectAccessibleFontFaceRules();
    if (!fontRules.length) return '';
    const inlinedRules = await Promise.all(fontRules.map((entry) => inlineFontFaceCss(entry.cssText, entry.baseUrl)));
    return inlinedRules.join('\n');
}

export async function getExportFontEmbedCss() {
    if (!cachedFontEmbedCssPromise) {
        cachedFontEmbedCssPromise = buildExportFontEmbedCss();
    }
    return cachedFontEmbedCssPromise;
}

export function resetFontEmbedCssCache() {
    cachedFontEmbedCssPromise = null;
}
