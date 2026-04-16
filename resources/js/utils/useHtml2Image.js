// useHtml2Image.js
// Centraliza la construcción de opciones y wrappers DRY para html-2-image

import { toCanvas, toJpeg, toPng } from '../html-2-image/src/index';
import { html2imageDefaultOptions } from './html2imageConfig';
import { getExportFontEmbedCss } from './fontEmbed';

export async function buildHtml2ImageOptions({ width, height, fontEmbedCSS, pixelRatio, backgroundColor, preferredFontFormat, embedWebFonts = false, ...overrides }) {
  return {
    width,
    height,
    pixelRatio,
    backgroundColor: backgroundColor ?? null,
    preferredFontFormat: preferredFontFormat ?? 'woff2',
    fontEmbedCSS: fontEmbedCSS ?? (await getExportFontEmbedCss()),
    embedWebFonts,
    cacheBust: true,
    ...html2imageDefaultOptions,
    ...overrides,
  };
}

export async function toJpegExport(node, opts = {}) {
  const options = await buildHtml2ImageOptions(opts);
  return toJpeg(node, options);
}

export async function toPngExport(node, opts = {}) {
  const options = await buildHtml2ImageOptions(opts);
  return toPng(node, options);
}

export async function toCanvasExport(node, opts = {}) {
  const options = await buildHtml2ImageOptions(opts);
  return toCanvas(node, options);
}
