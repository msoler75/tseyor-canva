<script setup>
import { toCanvas, toJpeg, toPng } from 'html-to-image';
import DesignerLayout from '../../Layouts/DesignerLayout.vue';
import StepFooter from '../../Components/designer/StepFooter.vue';
import RichTextEditor from '../../Components/designer/RichTextEditor.vue';
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { objectiveOptions, objectiveRecommendations } from '../../data/designer';
import { useDesignerState } from '../../composables/useDesignerState';
import {
    BASE_TEXT_ELEMENT_IDS,
    buildCanvasBackgroundStyle,
    buildEditorElements,
    buildElementBoxStyle,
    buildElementContentStyle,
    buildImageFrameStyle,
    buildImageTintOverlayStyle,
    buildRichEditorContainerStyle,
    buildShapeRenderModel,
    buildShapeStyle,
    neonColorOverrideFromLayout,
    parseSizeDetail,
} from '../../utils/editorShared';

defineProps({ currentStep: String, steps: Array, navigation: Object });
const state = useDesignerState();

const BASE_CANVAS_SHORT_SIDE = 368;
const BASE_CANVAS_LONG_SIDE = 620;
const baseTextElementIds = BASE_TEXT_ELEMENT_IDS;
const dpiOptions = [
    { value: 72, label: '72 DPI', helper: 'Web / borrador' },
    { value: 150, label: '150 DPI', helper: 'Calidad media' },
    { value: 300, label: '300 DPI', helper: 'Impresion alta' },
];
const SHAPE_CLIP_PATHS = {
    diamond: 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)',
    parallelogram: 'polygon(20% 0%, 100% 0%, 80% 100%, 0% 100%)',
    trapezoid: 'polygon(15% 0%, 85% 0%, 100% 100%, 0% 100%)',
    'trapezoid-inv': 'polygon(0% 0%, 100% 0%, 85% 100%, 15% 100%)',
    'triangle-up': 'polygon(50% 0%, 100% 100%, 0% 100%)',
    'triangle-right-angle': 'polygon(0% 0%, 100% 100%, 0% 100%)',
    'triangle-down': 'polygon(0% 0%, 100% 0%, 50% 100%)',
    'triangle-right': 'polygon(0% 0%, 100% 50%, 0% 100%)',
    'triangle-left': 'polygon(100% 0%, 0% 50%, 100% 100%)',
    pentagon: 'polygon(50% 0%, 100% 38%, 82% 100%, 18% 100%, 0% 38%)',
    hexagon: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)',
    octagon: 'polygon(30% 0%, 70% 0%, 100% 30%, 100% 70%, 70% 100%, 30% 100%, 0% 70%, 0% 30%)',
    'star-5': 'polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)',
    'star-4': 'polygon(50% 0%, 60% 40%, 100% 50%, 60% 60%, 50% 100%, 40% 60%, 0% 50%, 40% 40%)',
    'star-6': 'polygon(50% 0%, 58% 17%, 79% 7%, 71% 26%, 93% 25%, 82% 43%, 100% 50%, 82% 57%, 93% 75%, 71% 74%, 79% 93%, 58% 83%, 50% 100%, 42% 83%, 21% 93%, 29% 74%, 7% 75%, 18% 57%, 0% 50%, 18% 43%, 7% 25%, 29% 26%, 21% 7%, 42% 17%)',
    'star-burst': 'polygon(50% 0%, 60% 22%, 82% 18%, 78% 40%, 100% 50%, 78% 60%, 82% 82%, 60% 78%, 50% 100%, 40% 78%, 18% 82%, 22% 60%, 0% 50%, 22% 40%, 18% 18%, 40% 22%)',
    'arrow-right': 'polygon(0% 25%, 60% 25%, 60% 0%, 100% 50%, 60% 100%, 60% 75%, 0% 75%)',
    'arrow-curved': 'polygon(70% 0%, 100% 22%, 82% 22%, 82% 50%, 62% 72%, 34% 72%, 24% 62%, 24% 46%, 40% 46%, 40% 56%, 56% 56%, 66% 46%, 66% 22%, 48% 22%)',
    'arrow-left': 'polygon(40% 0%, 40% 25%, 100% 25%, 100% 75%, 40% 75%, 40% 100%, 0% 50%)',
    'arrow-up': 'polygon(25% 40%, 0% 40%, 50% 0%, 100% 40%, 75% 40%, 75% 100%, 25% 100%)',
    'arrow-down': 'polygon(25% 0%, 75% 0%, 75% 60%, 100% 60%, 50% 100%, 0% 60%, 25% 60%)',
    'arrow-double-h': 'polygon(0% 50%, 20% 0%, 20% 35%, 80% 35%, 80% 0%, 100% 50%, 80% 100%, 80% 65%, 20% 65%, 20% 100%)',
    'arrow-double-v': 'polygon(50% 0%, 100% 20%, 65% 20%, 65% 80%, 100% 80%, 50% 100%, 0% 80%, 35% 80%, 35% 20%, 0% 20%)',
    'chevron-right': 'polygon(0% 0%, 70% 0%, 100% 50%, 70% 100%, 0% 100%, 30% 50%)',
    'chevron-left': 'polygon(30% 0%, 100% 0%, 70% 50%, 100% 100%, 30% 100%, 0% 50%)',
    cross: 'polygon(33% 0%, 67% 0%, 67% 33%, 100% 33%, 100% 67%, 67% 67%, 67% 100%, 33% 100%, 33% 67%, 0% 67%, 0% 33%, 33% 33%)',
    'x-mark': 'polygon(10% 0%, 50% 40%, 90% 0%, 100% 10%, 60% 50%, 100% 90%, 90% 100%, 50% 60%, 10% 100%, 0% 90%, 40% 50%, 0% 10%)',
    heart: 'polygon(50% 30%, 20% 5%, 0% 25%, 0% 50%, 50% 95%, 100% 50%, 100% 25%, 80% 5%)',
    badge: 'polygon(50% 0%, 63% 12%, 79% 8%, 83% 25%, 98% 33%, 91% 50%, 98% 67%, 83% 75%, 79% 92%, 63% 88%, 50% 100%, 37% 88%, 21% 92%, 17% 75%, 2% 67%, 9% 50%, 2% 33%, 17% 25%, 21% 8%, 37% 12%)',
    ribbon: 'polygon(0% 0%, 100% 0%, 100% 55%, 80% 55%, 100% 100%, 50% 73%, 0% 100%, 20% 55%, 0% 55%)',
    frame: 'polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%, 12% 12%, 12% 88%, 88% 88%, 88% 12%, 12% 12%)',
    'frame-thick': 'polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%, 18% 18%, 18% 82%, 82% 82%, 82% 18%, 18% 18%)',
    'frame-thin': 'polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%, 8% 8%, 8% 92%, 92% 92%, 92% 8%, 8% 8%)',
    'frame-notch': 'polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%, 14% 8%, 86% 8%, 92% 14%, 92% 86%, 86% 92%, 14% 92%, 8% 86%, 8% 14%, 14% 8%)',
    callout: 'polygon(0% 0%, 100% 0%, 100% 75%, 55% 75%, 50% 100%, 45% 75%, 0% 75%)',
    'callout-ellipse': 'polygon(8% 42%, 12% 25%, 24% 12%, 40% 6%, 60% 6%, 76% 12%, 88% 25%, 92% 40%, 88% 55%, 76% 68%, 66% 76%, 70% 94%, 54% 82%, 38% 82%, 24% 76%, 12% 64%, 8% 52%)',
    'callout-cloud': 'polygon(14% 60%, 8% 46%, 14% 33%, 26% 28%, 32% 18%, 46% 14%, 58% 18%, 70% 14%, 82% 22%, 88% 34%, 86% 46%, 92% 58%, 86% 70%, 74% 76%, 62% 76%, 56% 92%, 46% 78%, 32% 78%, 22% 72%)',
    'callout-burst': 'polygon(6% 18%, 26% 10%, 44% 0%, 58% 12%, 80% 8%, 90% 24%, 100% 40%, 92% 56%, 100% 74%, 84% 84%, 68% 96%, 54% 84%, 34% 90%, 20% 82%, 6% 70%, 0% 52%, 8% 38%)',
    'callout-top': 'polygon(0% 25%, 45% 25%, 50% 0%, 55% 25%, 100% 25%, 100% 100%, 0% 100%)',
    'callout-left': 'polygon(20% 0%, 100% 0%, 100% 100%, 20% 100%, 20% 60%, 0% 50%, 20% 40%)',
    'callout-right': 'polygon(0% 0%, 80% 0%, 80% 40%, 100% 50%, 80% 60%, 80% 100%, 0% 100%)',
};

const objectiveTitle = computed(() => objectiveOptions.find((item) => item.id === state.objective)?.title ?? 'Genérico');
const selectedDpi = ref(150);
const selectedExportFormat = ref('png');
const jpgQuality = ref(0.95);
const isExporting = ref(false);
const exportError = ref('');
const exportSuccess = ref('');
const exportPreviewRef = ref(null);
const generatedCanvasHostRef = ref(null);
const isPreviewRendering = ref(false);
const previewRenderError = ref('');
let cachedFontEmbedCssPromise = null;
let previewTimer = null;
let previewRenderSeq = 0;

const resolvedSizeOption = computed(() => {
    const objectiveRules = objectiveRecommendations[state.objective] ?? objectiveRecommendations.generic;
    const options = objectiveRules[state.outputType] ?? [];
    return options.find((option) => option.label === state.size) ?? null;
});

const selectedSizeDetail = computed(() => resolvedSizeOption.value?.detail ?? '1080 × 1080 px');
const baseCanvasDimensions = computed(() => {
    const parsed = parseSizeDetail(selectedSizeDetail.value);

    if (parsed?.width > 0 && parsed?.height > 0) {
        const ratio = parsed.width / parsed.height;

        if (ratio >= 0.95 && ratio <= 1.05) {
            return {
                width: 500,
                height: 500,
            };
        }

        if (ratio > 1) {
            return {
                width: BASE_CANVAS_LONG_SIDE,
                height: Math.max(300, Math.min(BASE_CANVAS_LONG_SIDE, Math.round(BASE_CANVAS_LONG_SIDE / ratio))),
            };
        }

        return {
            width: Math.max(300, Math.min(BASE_CANVAS_LONG_SIDE, Math.round(BASE_CANVAS_LONG_SIDE * ratio))),
            height: BASE_CANVAS_LONG_SIDE,
        };
    }

    if (state.format === 'horizontal') {
        return { width: BASE_CANVAS_LONG_SIDE, height: BASE_CANVAS_SHORT_SIDE };
    }

    if (state.format === 'square') {
        return { width: 500, height: 500 };
    }

    return { width: BASE_CANVAS_SHORT_SIDE, height: BASE_CANVAS_LONG_SIDE };
});

const targetDimensions = computed(() => resolveTargetDimensions(selectedSizeDetail.value, selectedDpi.value));

const canvasBackgroundStyle = computed(() => buildCanvasBackgroundStyle(state.elementLayout.background));

const editorElements = computed(() => buildEditorElements(state));

const sanitizeFileName = (value) => {
    const normalized = (value || 'diseno').trim().toLowerCase();
    return normalized
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '') || 'diseno';
};

const fileName = computed(() => `${sanitizeFileName(state.content.title || 'diseno')}-${selectedDpi.value}dpi.${selectedExportFormat.value}`);

const exportButtonLabel = computed(() => {
    const ext = selectedExportFormat.value.toUpperCase();
    return isExporting.value ? `Generando ${ext}...` : `Descargar ${ext}`;
});

function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

function resolveTargetDimensions(detail, dpi) {
    const parsed = parseSizeDetail(detail);

    if (parsed.unit === 'cm') {
        return {
            width: Math.max(1, Math.round((parsed.width / 2.54) * dpi)),
            height: Math.max(1, Math.round((parsed.height / 2.54) * dpi)),
        };
    }

    const scale = dpi / 96;
    return {
        width: Math.max(1, Math.round(parsed.width * scale)),
        height: Math.max(1, Math.round(parsed.height * scale)),
    };
}

function isTextElement(id) {
    if (baseTextElementIds.has(id)) return true;
    return state.customElements?.[id]?.type === 'text';
}

function getElementText(id) {
    switch (id) {
        case 'title':
        case 'subtitle':
        case 'contact':
        case 'extra':
            return state.content[id] ?? '';
        case 'meta':
            return [state.content.date, state.content.time].filter(Boolean).join(' · ');
        default:
            return state.customElements?.[id]?.text ?? '';
    }
}

function elementContentStyle(id) {
    const layout = state.elementLayout[id] ?? {};
    const elementType = state.customElements?.[id]?.type ?? (baseTextElementIds.has(id) ? 'text' : null);
    return buildElementContentStyle(layout, { elementType });
}

function elementBoxStyle(id) {
    const layout = state.elementLayout[id] ?? {};
    return buildElementBoxStyle(layout, { isText: isTextElement(id) });
}

function richEditorContainerStyle(id) {
    return buildRichEditorContainerStyle(state.elementLayout[id] ?? {});
}

function neonColorOverride(id) {
    return neonColorOverrideFromLayout(state.elementLayout[id] ?? {});
}

function shapeStyle(item) {
    return buildShapeStyle(state.elementLayout[item.id] ?? {}, item.shapeKind, SHAPE_CLIP_PATHS);
}

function shapeRenderModel(item) {
    return buildShapeRenderModel(state.elementLayout[item.id] ?? {}, item.shapeKind, SHAPE_CLIP_PATHS);
}

function imageFrameStyle(id) {
    return buildImageFrameStyle(state.elementLayout[id] ?? {});
}

function imageTintOverlayStyle(id) {
    return buildImageTintOverlayStyle(state.elementLayout[id] ?? {});
}

function collectAccessibleFontFaceRules() {
    const styleSheets = Array.from(document.styleSheets || []);
    const rules = [];

    styleSheets.forEach((sheet) => {
        let sheetRules;
        try {
            sheetRules = sheet.cssRules;
        } catch {
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
        if (!originalUrl || originalUrl.startsWith('data:') || originalUrl.startsWith('#')) {
            continue;
        }
        if (originalUrl.startsWith('local(')) {
            continue;
        }

        let absoluteUrl;
        try {
            absoluteUrl = new URL(originalUrl, baseUrl).toString();
        } catch {
            continue;
        }

        if (replacements.has(originalUrl)) {
            continue;
        }

        try {
            const response = await fetch(absoluteUrl, { credentials: 'same-origin' });
            if (!response.ok) {
                continue;
            }
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
    if (!fontRules.length) {
        return '';
    }

    const inlinedRules = await Promise.all(fontRules.map((entry) => inlineFontFaceCss(entry.cssText, entry.baseUrl)));
    return inlinedRules.join('\n');
}

async function getExportFontEmbedCss() {
    if (!cachedFontEmbedCssPromise) {
        cachedFontEmbedCssPromise = buildExportFontEmbedCss();
    }
    return cachedFontEmbedCssPromise;
}

async function buildRendererOptions(width, height) {
    const fontEmbedCSS = await getExportFontEmbedCss();
    const baseWidth = baseCanvasDimensions.value.width;
    const baseHeight = baseCanvasDimensions.value.height;
    const scale = Math.max(width / baseWidth, height / baseHeight);
    return {
        cacheBust: true,
        pixelRatio: scale,
        width: baseWidth,
        height: baseHeight,
        backgroundColor: null,
        preferredFontFormat: 'woff2',
        // Embebe archivos de fuente como data URI para mantener fidelidad tipografica.
        fontEmbedCSS,
    };
}

function mountPreviewCanvas(canvas) {
    const host = generatedCanvasHostRef.value;
    if (!host) return;
    host.innerHTML = '';
    canvas.className = 'h-auto w-full';
    canvas.style.width = '100%';
    canvas.style.height = 'auto';
    host.appendChild(canvas);
}

async function renderGeneratedCanvasPreview() {
    if (!exportPreviewRef.value || !generatedCanvasHostRef.value) return;

    const runId = ++previewRenderSeq;
    isPreviewRendering.value = true;
    previewRenderError.value = '';

    try {
        await nextTick();
        if (document.fonts?.ready) {
            await document.fonts.ready;
        }

        const rendererOptions = await buildRendererOptions(baseCanvasDimensions.value.width, baseCanvasDimensions.value.height);
        const canvas = await toCanvas(exportPreviewRef.value, rendererOptions);
        if (runId !== previewRenderSeq) return;
        mountPreviewCanvas(canvas);
    } catch (error) {
        if (runId !== previewRenderSeq) return;
        console.error('No se pudo renderizar la vista de canvas', error);
        previewRenderError.value = 'No se pudo actualizar la vista del canvas generado.';
    } finally {
        if (runId === previewRenderSeq) {
            isPreviewRendering.value = false;
        }
    }
}

function schedulePreviewRender() {
    if (previewTimer) {
        clearTimeout(previewTimer);
    }
    previewTimer = setTimeout(() => {
        renderGeneratedCanvasPreview();
    }, 120);
}

async function downloadImage() {
    exportError.value = '';
    exportSuccess.value = '';

    if (!exportPreviewRef.value) {
        exportError.value = 'No se encontro la vista previa para exportar.';
        return;
    }

    isExporting.value = true;

    try {
        await nextTick();
        if (document.fonts?.ready) {
            await document.fonts.ready;
        }

        const { width, height } = targetDimensions.value;

        const rendererOptions = await buildRendererOptions(width, height);

        const dataUrl = selectedExportFormat.value === 'jpg'
            ? await toJpeg(exportPreviewRef.value, {
                ...rendererOptions,
                quality: clamp(Number(jpgQuality.value), 0.6, 1),
            })
            : await toPng(exportPreviewRef.value, rendererOptions);

        const link = document.createElement('a');
        link.download = fileName.value;
        link.href = dataUrl;
        link.click();

        const ext = selectedExportFormat.value.toUpperCase();
        exportSuccess.value = `${ext} generado: ${width} × ${height} px (${selectedDpi.value} DPI).`;
    } catch (error) {
        console.error('No se pudo exportar la imagen', error);
        exportError.value = 'No se pudo exportar la imagen. Si usas imagenes externas, revisa que permitan CORS.';
    } finally {
        isExporting.value = false;
    }
}

onMounted(() => {
    schedulePreviewRender();
});

onBeforeUnmount(() => {
    if (previewTimer) {
        clearTimeout(previewTimer);
        previewTimer = null;
    }
});

watch([selectedDpi, selectedExportFormat, jpgQuality], () => {
    schedulePreviewRender();
});

watch(() => state.content, () => {
    schedulePreviewRender();
}, { deep: true });

watch(() => state.customElements, () => {
    schedulePreviewRender();
}, { deep: true });

watch(() => state.elementLayout, () => {
    schedulePreviewRender();
}, { deep: true });
</script>

<template>
    <DesignerLayout
        title="Exportar"
        eyebrow="Pantalla 7"
        description="Elige cómo descargar el diseño."
        :current-step="currentStep"
        :steps="steps"
        :dark-mode="state.darkMode"
        @toggle-dark="state.darkMode = !state.darkMode"
    >
        <section class="grid gap-6 xl:grid-cols-[1fr_340px]">
            <div class="glass soft-shadow rounded-4xl border border-white/70 p-6 sm:p-8 dark:border-slate-700/70">
                <div class="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
                    <div class="rounded-[28px] bg-neutral p-6 text-neutral-content">
                        <p class="text-xs font-semibold uppercase tracking-[0.22em] text-white/60">Exportar</p>
                        <h3 class="mt-3 text-3xl font-semibold">Imagen fiel al diseño</h3>
                        <p class="mt-4 text-sm leading-6 text-white/78">
                            Se renderiza el diseño con html-to-image para respetar capas, tipografías, sombras, formas e imágenes.
                        </p>

                        <div class="mt-6 space-y-4">
                            <div class="rounded-2xl border border-white/20 bg-white/5 p-4">
                                <p class="text-xs font-semibold uppercase tracking-[0.2em] text-white/70">Formato</p>
                                <div class="mt-3 grid grid-cols-2 gap-2">
                                    <button
                                        type="button"
                                        class="btn btn-sm rounded-xl"
                                        :class="selectedExportFormat === 'png' ? 'btn-primary' : 'btn-outline text-white border-white/40 hover:bg-white/10'"
                                        @click="selectedExportFormat = 'png'"
                                    >PNG</button>
                                    <button
                                        type="button"
                                        class="btn btn-sm rounded-xl"
                                        :class="selectedExportFormat === 'jpg' ? 'btn-primary' : 'btn-outline text-white border-white/40 hover:bg-white/10'"
                                        @click="selectedExportFormat = 'jpg'"
                                    >JPG</button>
                                </div>
                                <p class="mt-2 text-sm text-white/70">PNG para máxima fidelidad; JPG para menor peso.</p>
                            </div>

                            <div v-if="selectedExportFormat === 'jpg'" class="rounded-2xl border border-white/20 bg-white/5 p-4">
                                <p class="text-xs font-semibold uppercase tracking-[0.2em] text-white/70">Calidad JPG</p>
                                <div class="mt-3 flex items-center gap-3">
                                    <input
                                        v-model.number="jpgQuality"
                                        type="range"
                                        min="0.6"
                                        max="1"
                                        step="0.01"
                                        class="range range-primary flex-1"
                                    />
                                    <span class="w-14 text-right text-sm font-semibold">{{ Math.round(jpgQuality * 100) }}%</span>
                                </div>
                            </div>

                            <div class="rounded-2xl border border-white/20 bg-white/5 p-4">
                                <p class="text-xs font-semibold uppercase tracking-[0.2em] text-white/70">Resolución (DPI / PPP)</p>
                                <div class="mt-3 grid gap-2 sm:grid-cols-3">
                                    <button
                                        v-for="option in dpiOptions"
                                        :key="option.value"
                                        type="button"
                                        class="btn btn-sm h-auto rounded-xl px-3 py-2 text-left"
                                        :class="selectedDpi === option.value ? 'btn-primary' : 'btn-outline text-white border-white/40 hover:bg-white/10'"
                                        @click="selectedDpi = option.value"
                                    >
                                        <span class="block text-xs font-semibold">{{ option.label }}</span>
                                        <span class="block text-[11px] opacity-75">{{ option.helper }}</span>
                                    </button>
                                </div>
                            </div>

                            <div class="rounded-2xl border border-white/20 bg-white/5 p-4 text-sm">
                                <p>
                                    Tamaño base: <strong>{{ state.size || 'Sin tamaño' }}</strong>
                                    <span class="opacity-80">· {{ selectedSizeDetail }}</span>
                                </p>
                                <p class="mt-1">
                                    Salida final: <strong>{{ targetDimensions.width }} × {{ targetDimensions.height }} px</strong>
                                </p>
                                <p class="mt-1 opacity-80">Objetivo: {{ objectiveTitle }}</p>
                            </div>

                            <button
                                type="button"
                                class="btn btn-primary w-full rounded-2xl"
                                :disabled="isExporting"
                                @click="downloadImage"
                            >
                                {{ exportButtonLabel }}
                            </button>

                            <p v-if="exportSuccess" class="text-sm text-emerald-300">{{ exportSuccess }}</p>
                            <p v-if="exportError" class="text-sm text-red-300">{{ exportError }}</p>
                        </div>
                    </div>

                </div>
                <StepFooter :previous-url="navigation.previous" />
            </div>

            <div class="glass soft-shadow rounded-4xl border border-white/70 p-6 dark:border-slate-700/70">
                <p class="text-sm font-semibold uppercase tracking-[0.22em] text-primary">Vista del canvas generado</p>
                <div class="mx-auto mt-5 max-w-100 bg-white p-4 shadow-2xl dark:bg-slate-900">
                    <div ref="generatedCanvasHostRef" class="mx-auto w-full"></div>
                    <p v-if="isPreviewRendering" class="mt-3 text-xs text-base-content/70">Actualizando canvas generado...</p>
                    <p v-if="previewRenderError" class="mt-3 text-xs text-red-500">{{ previewRenderError }}</p>
                </div>

                <div class="pointer-events-none fixed top-0 opacity-0" style="left: -99999px;">
                    <div
                        ref="exportPreviewRef"
                        class="relative overflow-hidden p-7 text-white"
                        :style="{ ...canvasBackgroundStyle, width: `${baseCanvasDimensions.width}px`, height: `${baseCanvasDimensions.height}px` }"
                    >
                        <div
                            v-for="item in editorElements"
                            :key="item.id"
                            :style="elementBoxStyle(item.id)"
                        >
                            <template v-if="item.type === 'text'">
                                <div :style="elementContentStyle(item.id)">
                                    <RichTextEditor
                                        :paragraph-styles="state.elementLayout[item.id]?.paragraphStyles ?? []"
                                        :text="item.text ?? ''"
                                        :editable="false"
                                        :editor-style="richEditorContainerStyle(item.id)"
                                        :color-override="neonColorOverride(item.id)"
                                        :transparent-fill="!!state.elementLayout[item.id]?.hollowText"
                                    />
                                </div>
                            </template>

                            <template v-else-if="item.type === 'image'">
                                <div :style="imageFrameStyle(item.id)">
                                    <img
                                        v-if="item.src"
                                        :src="item.src"
                                        :alt="item.label"
                                        class="h-full w-full object-cover"
                                        crossorigin="anonymous"
                                    />
                                    <div
                                        v-if="item.src && (state.elementLayout[item.id]?.imageTintStrength ?? 0) > 0"
                                        :style="imageTintOverlayStyle(item.id)"
                                    ></div>
                                </div>
                            </template>

                            <template v-else>
                                <div class="relative h-full w-full">
                                    <div class="h-full w-full" :style="shapeRenderModel(item).outerStyle"></div>
                                    <div
                                        v-if="shapeRenderModel(item).innerStyle"
                                        class="pointer-events-none absolute inset-0"
                                        :style="shapeRenderModel(item).innerStyle"
                                    ></div>
                                    <svg
                                        v-if="shapeRenderModel(item).svgStroke"
                                        class="pointer-events-none absolute inset-0 h-full w-full overflow-visible"
                                        viewBox="0 0 100 100"
                                        preserveAspectRatio="none"
                                    >
                                        <polygon
                                            :points="shapeRenderModel(item).svgStroke.points"
                                            fill="none"
                                            :stroke="shapeRenderModel(item).svgStroke.stroke"
                                            :stroke-width="shapeRenderModel(item).svgStroke.strokeWidth"
                                            :stroke-dasharray="shapeRenderModel(item).svgStroke.dasharray"
                                            :stroke-linecap="shapeRenderModel(item).svgStroke.linecap"
                                            :stroke-linejoin="shapeRenderModel(item).svgStroke.linejoin"
                                            vector-effect="non-scaling-stroke"
                                        />
                                    </svg>
                                </div>
                            </template>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    </DesignerLayout>
</template>
