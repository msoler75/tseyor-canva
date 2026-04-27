<script setup>
import { ref, computed, nextTick, watch, onMounted, onBeforeUnmount } from 'vue';
import { toCanvasExport, toJpegExport, toPngExport } from '../../utils/useHtml2Image';
import { useDesignerState } from '../../composables/useDesignerState';
import { objectiveOptions, resolveObjectiveSizeOptions } from '../../data/designer';
import RichTextEditor from './RichTextEditor.vue';
import {
    BASE_TEXT_ELEMENT_IDS,
    applyFormatToDimensions,
    buildCanvasBackgroundStyle,
    buildCoverImageStyle,
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

const props = defineProps({ navigation: Object });
const emit = defineEmits(['close']);

// Cerrar con Escape
function handleKeydown(e) {
  if (e.key === 'Escape') {
    emit('close');
  }
}
onMounted(() => {
  window.addEventListener('keydown', handleKeydown);
});
onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown);
});

const state = useDesignerState();

const BASE_CANVAS_SHORT_SIDE = 368;
const BASE_CANVAS_LONG_SIDE = 620;
const baseTextElementIds = BASE_TEXT_ELEMENT_IDS;
const dpiOptions = [
    { value: 96, label: '96 DPI', helper: 'Web / estándar' },
    { value: 150, label: '150 DPI', helper: 'Calidad media' },
    { value: 300, label: '300 DPI', helper: 'Impresión alta' },
];
const objectiveTitle = computed(() => objectiveOptions.find((item) => item.id === state.objective)?.title ?? 'Genérico');
const selectedDpi = ref(96);
const selectedExportFormat = ref('png');
const jpgQuality = ref(0.95);
const isExporting = ref(false);
const exportError = ref('');
const exportSuccess = ref('');

const exportPreviewRef = ref(null);
const previewImageUrl = ref('');
// Genera un SVG transparente con las dimensiones deseadas y lo convierte a data-uri
function svgPlaceholder(width, height) {
  // SVG sin width/height, solo viewBox, para que el <img> lo escale igual que la imagen real
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 ${width} ${height}'></svg>`;
  return 'data:image/svg+xml;utf8,' + encodeURIComponent(svg);
}
const isPreviewRendering = ref(true);
const previewRenderError = ref('');
let previewTimer = null;
let previewRenderSeq = 0;

const resolvedSizeOption = computed(() => {
    const options = resolveObjectiveSizeOptions(state.objective, state.outputType);
    return options.find((option) => option.label === state.size) ?? null;
});

const selectedSizeDetail = computed(() => resolvedSizeOption.value?.detail ?? '1080 × 1080 px');
const baseCanvasDimensions = computed(() => {
    const parsed = applyFormatToDimensions(parseSizeDetail(selectedSizeDetail.value), state.format);
    if (parsed?.width > 0 && parsed?.height > 0) {
        const ratio = parsed.width / parsed.height;
        if (ratio >= 0.95 && ratio <= 1.05) {
            return { width: 500, height: 500 };
        }
        if (ratio > 1) {
            return { width: BASE_CANVAS_LONG_SIDE, height: Math.max(300, Math.min(BASE_CANVAS_LONG_SIDE, Math.round(BASE_CANVAS_LONG_SIDE / ratio))) };
        }
        return { width: Math.max(300, Math.min(BASE_CANVAS_LONG_SIDE, Math.round(BASE_CANVAS_LONG_SIDE * ratio))), height: BASE_CANVAS_LONG_SIDE };
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

const easingFns = {
    linear: (t) => t,
    'ease-in': (t) => t * t * t,
    'ease-out': (t) => 1 - ((1 - t) ** 3),
    'ease-in-out': (t) => (t < 0.5 ? 4 * t * t * t : 1 - ((-2 * t + 2) ** 3) / 2),
    quadratic: (t) => t * t,
    'quadratic-out': (t) => 1 - ((1 - t) * (1 - t)),
    smoothstep: (t) => t * t * (3 - 2 * t),
};

const prefixedTransparencyValue = (layout = {}, prefix = '', key, fallback) => {
    const prefixedKey = prefix ? `${prefix}${key[0].toUpperCase()}${key.slice(1)}` : key;
    return layout?.[prefixedKey] ?? fallback;
};

const hasAdvancedTransparency = (layout = {}, prefix = '') => {
    const type = prefixedTransparencyValue(layout, prefix, 'transparencyType', 'flat');
    return Boolean(type && type !== 'flat');
};

const svgTransparencyStops = (layout = {}, prefix = '') => {
    const endOpacity = clamp(Number(prefixedTransparencyValue(layout, prefix, 'transparencyFadeOpacity', 0)), 0, 100) / 100;
    const easing = prefixedTransparencyValue(layout, prefix, 'transparencyEasing', 'linear');
    const ease = easingFns[easing] ?? easingFns.linear;

    return Array.from({ length: 11 }, (_, index) => {
        const t = index / 10;
        const opacity = 1 + ((endOpacity - 1) * ease(t));
        return {
            offset: `${Math.round(t * 100)}%`,
            opacity: opacity.toFixed(4),
        };
    });
};

const svgTransparencyGradient = (layout = {}, prefix = '') => {
    const type = prefixedTransparencyValue(layout, prefix, 'transparencyType', 'flat');
    const centerX = clamp(Number(prefixedTransparencyValue(layout, prefix, 'transparencyCenterX', 50)), 0, 100);
    const centerY = clamp(Number(prefixedTransparencyValue(layout, prefix, 'transparencyCenterY', 50)), 0, 100);
    const radius = clamp(Number(prefixedTransparencyValue(layout, prefix, 'transparencyRadius', 70)), 1, 150);
    const radiusX = clamp(Number(prefixedTransparencyValue(layout, prefix, 'transparencyRadiusX', 70)), 1, 150);
    const radiusY = clamp(Number(prefixedTransparencyValue(layout, prefix, 'transparencyRadiusY', 45)), 1, 150);
    const rotation = Number(prefixedTransparencyValue(layout, prefix, 'transparencyRotation', 0));
    const startX = clamp(Number(prefixedTransparencyValue(layout, prefix, 'transparencyStartX', 0)), 0, 100);
    const startY = clamp(Number(prefixedTransparencyValue(layout, prefix, 'transparencyStartY', 50)), 0, 100);
    const endX = clamp(Number(prefixedTransparencyValue(layout, prefix, 'transparencyEndX', 100)), 0, 100);
    const endY = clamp(Number(prefixedTransparencyValue(layout, prefix, 'transparencyEndY', 50)), 0, 100);

    if (type === 'linear') {
        return { type, x1: startX, y1: startY, x2: endX, y2: endY };
    }

    return {
        type,
        cx: 0,
        cy: 0,
        r: 1,
        transform: `translate(${centerX} ${centerY}) rotate(${type === 'ellipse' ? rotation : 0}) scale(${type === 'ellipse' ? radiusX : radius} ${type === 'ellipse' ? radiusY : radius})`,
    };
};

const svgMaskIds = (id) => {
    const safeId = String(id ?? 'item').replace(/[^\w-]/g, '-');
    return {
        gradient: `transparency-gradient-${safeId}`,
        strokeGradient: `transparency-stroke-gradient-${safeId}`,
        mask: `transparency-mask-${safeId}`,
        fill: `shape-fill-${safeId}`,
    };
};

const exportShapeClipPaths = {
    diamond: 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)',
    parallelogram: 'polygon(20% 0%, 100% 0%, 80% 100%, 0% 100%)',
    trapezoid: 'polygon(15% 0%, 85% 0%, 100% 100%, 0% 100%)',
    'triangle-up': 'polygon(50% 0%, 100% 100%, 0% 100%)',
    'triangle-right-angle': 'polygon(0% 0%, 100% 100%, 0% 100%)',
    pentagon: 'polygon(50% 0%, 100% 38%, 82% 100%, 18% 100%, 0% 38%)',
    hexagon: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)',
    octagon: 'polygon(30% 0%, 70% 0%, 100% 30%, 100% 70%, 70% 100%, 30% 100%, 0% 70%, 0% 30%)',
    'star-5': 'polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)',
    'star-4': 'polygon(50% 0%, 60% 40%, 100% 50%, 60% 60%, 50% 100%, 40% 60%, 0% 50%, 40% 40%)',
    'star-6': 'polygon(50% 0%, 58% 17%, 79% 7%, 71% 26%, 93% 25%, 82% 43%, 100% 50%, 82% 57%, 93% 75%, 71% 74%, 79% 93%, 58% 83%, 50% 100%, 42% 83%, 21% 93%, 29% 74%, 7% 75%, 18% 57%, 0% 50%, 18% 43%, 7% 25%, 29% 26%, 21% 7%, 42% 17%)',
    'star-burst': 'polygon(50% 0%, 60% 22%, 82% 18%, 78% 40%, 100% 50%, 78% 60%, 82% 82%, 60% 78%, 50% 100%, 40% 78%, 18% 82%, 22% 60%, 0% 50%, 22% 40%, 18% 18%, 40% 22%)',
    'arrow-right': 'polygon(0% 25%, 60% 25%, 60% 0%, 100% 50%, 60% 100%, 60% 75%, 0% 75%)',
};

const polygonPointsFromClipPath = (shapeKind) => {
    const clipPath = exportShapeClipPaths[shapeKind];
    const match = clipPath?.match(/^polygon\((.+)\)$/i);
    if (!match) return null;

    return match[1]
        .split(',')
        .map((point) => point.trim().replace(/\s+/g, ' ').replace(/%/g, ''))
        .join(' ');
};

const shapeSvgFill = (id) => {
    const layout = state.elementLayout[id] ?? {};
    if (layout.fillMode === 'gradient') {
        return `url(#${svgMaskIds(id).fill})`;
    }
    return layout.backgroundColor && layout.backgroundColor !== 'transparent'
        ? layout.backgroundColor
        : '#ffffff';
};

const shapeSvgSolidColor = (id) => {
    const layout = state.elementLayout[id] ?? {};
    return layout.backgroundColor && layout.backgroundColor !== 'transparent'
        ? layout.backgroundColor
        : '#ffffff';
};

const shapeSvgStroke = (id) => {
    const layout = state.elementLayout[id] ?? {};
    return layout.border ? (layout.contourColor || '#ffffff') : 'none';
};

const shapeSvgStrokeColor = (id) => {
    const layout = state.elementLayout[id] ?? {};
    return layout.contourColor || '#ffffff';
};

const shapeSvgStrokeWidth = (id) => {
    const layout = state.elementLayout[id] ?? {};
    if (!layout.border) return 0;
    const width = Math.max(1, Number(layout.w ?? 160));
    const height = Math.max(1, Number(layout.h ?? 140));
    const viewBoxScale = 100 / Math.max(1, Math.min(width, height));
    return Math.max(0.5, Number(layout.contourWidth || 1) * viewBoxScale);
};

const shapeHasBorder = (id) => Boolean(state.elementLayout[id]?.border);

const shapeInnerTransform = (id) => {
    const layout = state.elementLayout[id] ?? {};
    if (!layout.border) return '';
    const width = Math.max(1, Number(layout.w ?? 160));
    const height = Math.max(1, Number(layout.h ?? 140));
    const borderWidth = Math.max(1, Number(layout.contourWidth || 1));
    const scaleX = Math.max(0.02, (width - (borderWidth * 2)) / width);
    const scaleY = Math.max(0.02, (height - (borderWidth * 2)) / height);
    return `translate(50 50) scale(${scaleX} ${scaleY}) translate(-50 -50)`;
};

const imageCornerRadii = (id) => {
    const layout = state.elementLayout[id] ?? {};
    const fallback = Number(layout.borderRadius ?? 12);
    return {
        topLeft: Number(layout.borderRadiusTopLeft ?? fallback),
        topRight: Number(layout.borderRadiusTopRight ?? fallback),
        bottomRight: Number(layout.borderRadiusBottomRight ?? fallback),
        bottomLeft: Number(layout.borderRadiusBottomLeft ?? fallback),
    };
};

const imageClipPathPath = (id) => {
    const layout = state.elementLayout[id] ?? {};
    const radii = imageCornerRadii(id);
    const width = Math.max(1, Number(layout.w ?? 160));
    const height = Math.max(1, Number(layout.h ?? 140));
    const toX = (radius) => clamp((Number(radius) / width) * 100, 0, 50);
    const toY = (radius) => clamp((Number(radius) / height) * 100, 0, 50);
    const tlx = toX(radii.topLeft);
    const tly = toY(radii.topLeft);
    const trx = toX(radii.topRight);
    const try_ = toY(radii.topRight);
    const brx = toX(radii.bottomRight);
    const bry = toY(radii.bottomRight);
    const blx = toX(radii.bottomLeft);
    const bly = toY(radii.bottomLeft);

    return [
        `M ${tlx} 0`,
        `H ${100 - trx}`,
        `Q 100 0 100 ${try_}`,
        `V ${100 - bry}`,
        `Q 100 100 ${100 - brx} 100`,
        `H ${blx}`,
        `Q 0 100 0 ${100 - bly}`,
        `V ${tly}`,
        `Q 0 0 ${tlx} 0`,
        'Z',
    ].join(' ');
};

function resolveTargetDimensions(detail, dpi) {
    dpi = dpi || 96;
    const parsed = applyFormatToDimensions(parseSizeDetail(detail), state.format);
    if (parsed.unit === 'cm') {
        return {
            width: Math.max(1, Math.round((parsed.width / 2.54) * dpi)),
            height: Math.max(1, Math.round((parsed.height / 2.54) * dpi)),
        };
    }
    if (dpi === 96) {
        return {
            width: Math.max(1, Math.round(parsed.width)),
            height: Math.max(1, Math.round(parsed.height)),
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

function elementContentStyle(id) {
    const layout = state.elementLayout[id] ?? {};
    const elementType = state.customElements?.[id]?.type ?? (baseTextElementIds.has(id) ? 'text' : null);
    return buildElementContentStyle(layout, { elementType });
}
function exportElementContentStyle(id) {
    const layout = state.elementLayout[id] ?? {};
    const elementType = state.customElements?.[id]?.type ?? (baseTextElementIds.has(id) ? 'text' : null);

    if ((elementType === 'image' || elementType === 'shape') && hasAdvancedTransparency(layout)) {
        return {
            width: '100%',
            height: '100%',
        };
    }

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
    return buildShapeStyle(state.elementLayout[item.id] ?? {}, item.shapeKind);
}
function shapeRenderModel(item) {
    return buildShapeRenderModel(state.elementLayout[item.id] ?? {}, item.shapeKind);
}
function shapeUsesSvgTransparency(id) {
    return hasAdvancedTransparency(state.elementLayout[id] ?? {});
}
function imageFrameStyle(id) {
    return buildImageFrameStyle(state.elementLayout[id] ?? {});
}
function imageRenderStyle(id) {
    const layout = state.elementLayout[id] ?? {};
    const element = state.customElements?.[id] ?? {};
    return buildCoverImageStyle({
        containerWidth: layout.w ?? 160,
        containerHeight: layout.h ?? 140,
        imageWidth: element.intrinsicWidth,
        imageHeight: element.intrinsicHeight,
        cropScale: layout.imageCropScale,
        cropOffsetX: layout.imageCropOffsetX,
        cropOffsetY: layout.imageCropOffsetY,
        flipX: layout.flipX,
        flipY: layout.flipY,
    });
}
function imageUsesSvgTransparency(id) {
    return hasAdvancedTransparency(state.elementLayout[id] ?? {});
}
function backgroundUsesSvgTransparency() {
    return hasAdvancedTransparency(state.elementLayout.background ?? {}, 'backgroundImage');
}
function imageTintOverlayStyle(id) {
    return buildImageTintOverlayStyle(state.elementLayout[id] ?? {});
}
const canvasBackgroundImageStyle = computed(() => buildCoverImageStyle({
    containerWidth: baseCanvasDimensions.value.width,
    containerHeight: baseCanvasDimensions.value.height,
    imageWidth: state.elementLayout.background?.backgroundImageWidth,
    imageHeight: state.elementLayout.background?.backgroundImageHeight,
    cropScale: state.elementLayout.background?.backgroundImageCropScale,
    cropOffsetX: state.elementLayout.background?.backgroundImageCropOffsetX,
    cropOffsetY: state.elementLayout.background?.backgroundImageCropOffsetY,
    flipX: state.elementLayout.background?.backgroundImageFlipX,
    flipY: state.elementLayout.background?.backgroundImageFlipY,
    opacity: state.elementLayout.background?.backgroundImageOpacity,
    transparencyLayout: state.elementLayout.background,
    transparencyPrefix: 'backgroundImage',
    transparencyOpacityKey: 'backgroundImageOpacity',
}));

async function buildRendererOptions(width, height) {
    return {};
}

async function renderGeneratedImagePreview() {
  if (!exportPreviewRef.value) return;
  const runId = ++previewRenderSeq;
  isPreviewRendering.value = true;
  previewRenderError.value = '';
  try {
    await nextTick();
    if (document.fonts?.ready) {
      await document.fonts.ready;
    }
    const node = exportPreviewRef.value;
    const { width, height } = targetDimensions.value;
    const baseWidth = baseCanvasDimensions.value.width;
    const baseHeight = baseCanvasDimensions.value.height;
    const prevWidth = node.style.width;
    const prevHeight = node.style.height;
    const prevTransform = node.style.transform;
    const scaleX = width / baseWidth;
    const scaleY = height / baseHeight;
    node.style.width = baseWidth + 'px';
    node.style.height = baseHeight + 'px';
    node.style.transformOrigin = 'top left';
    node.style.transform = `scale(${scaleX}, ${scaleY})`;
    // Determinar color de fondo
    let backgroundColor = null;
    if (state.elementLayout.background?.fillMode === 'solid') {
      backgroundColor = state.elementLayout.background?.backgroundColor || '#fff';
    }
    let dataUrl;
    if (selectedExportFormat.value === 'jpg') {
      dataUrl = await toJpegExport(node, {
        width,
        height,
        quality: clamp(Number(jpgQuality.value), 0.6, 1),
        backgroundColor,
      });
    } else {
      dataUrl = await toPngExport(node, {
        width,
        height,
        backgroundColor,
      });
    }
    if (runId !== previewRenderSeq) return;
    previewImageUrl.value = dataUrl;
    // Restaurar estilos
    node.style.width = prevWidth;
    node.style.height = prevHeight;
    node.style.transform = prevTransform;
  } catch (error) {
    if (runId !== previewRenderSeq) return;
    console.error('No se pudo renderizar la vista previa', error);
    previewRenderError.value = 'No se pudo actualizar la vista previa.';
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
    renderGeneratedImagePreview();
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
    const node = exportPreviewRef.value;
    const { width, height } = targetDimensions.value;
    const baseWidth = baseCanvasDimensions.value.width;
    const baseHeight = baseCanvasDimensions.value.height;
    const prevWidth = node.style.width;
    const prevHeight = node.style.height;
    const prevTransform = node.style.transform;
    const scaleX = width / baseWidth;
    const scaleY = height / baseHeight;
    node.style.width = baseWidth + 'px';
    node.style.height = baseHeight + 'px';
    node.style.transformOrigin = 'top left';
    node.style.transform = `scale(${scaleX}, ${scaleY})`;
    try {
        await nextTick();
        if (document.fonts?.ready) {
            await document.fonts.ready;
        }
        // Determinar color de fondo
        let backgroundColor = null;
        if (state.elementLayout.background?.fillMode === 'solid') {
          backgroundColor = state.elementLayout.background?.backgroundColor || '#fff';
        }
        const dataUrl = selectedExportFormat.value === 'jpg'
          ? await toJpegExport(node, {
            width,
            height,
            quality: clamp(Number(jpgQuality.value), 0.6, 1),
            backgroundColor,
          })
          : await toPngExport(node, {
            width,
            height,
            backgroundColor,
          });
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
        node.style.width = prevWidth;
        node.style.height = prevHeight;
        node.style.transform = prevTransform;
        isExporting.value = false;
    }
}

onMounted(() => {
  isPreviewRendering.value = true;
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
  <dialog open class="modal modal-open backdrop-blur" @click="emit('close')">
    <div class="modal-box max-w-4xl w-full relative" @click.stop>
      <!-- Botón de cierre -->
      <button @click="emit('close')" aria-label="Cerrar" class="absolute top-3 right-3 z-20 btn btn-sm btn-circle btn-ghost text-xl">
        <span aria-hidden="true">&times;</span>
      </button>
      <h3 class="font-bold text-xl mb-4">Exportar diseño</h3>
      <section class="grid gap-8 md:grid-cols-[1.5fr_0.8fr] items-start">
        <!-- Opciones de exportación -->
        <div class="glass soft-shadow rounded-4xl border border-base-300/70 p-6 text-base-content sm:p-10">
          <div class="space-y-6">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary mb-1">Opciones de exportación</p>
              <h4 class="text-2xl font-bold mb-2">Elige cómo exportar tu diseño</h4>
              <p class="text-sm text-base-content/70 mb-2">Personaliza el formato, calidad y resolución de la imagen exportada.</p>
            </div>
            <div class="grid gap-4 md:grid-cols-2">
              <div class="rounded-2xl border border-base-300 bg-base-100/70 p-4">
                <p class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/70">Formato</p>
                <div class="mt-3 flex gap-2">
                  <button type="button" class="btn btn-sm rounded-xl flex-1" :class="selectedExportFormat === 'png' ? 'btn-primary' : 'btn-outline'" @click="selectedExportFormat = 'png'">PNG</button>
                  <button type="button" class="btn btn-sm rounded-xl flex-1" :class="selectedExportFormat === 'jpg' ? 'btn-primary' : 'btn-outline'" @click="selectedExportFormat = 'jpg'">JPG</button>
                </div>
                <p class="mt-2 text-xs text-base-content/70">PNG para máxima fidelidad; JPG para menor peso.</p>
              </div>
              <div v-if="selectedExportFormat === 'jpg'" class="rounded-2xl border border-base-300 bg-base-100/70 p-4">
                <p class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/70">Calidad JPG</p>
                <div class="mt-3 flex items-center gap-3">
                  <input v-model.number="jpgQuality" type="range" min="0.6" max="1" step="0.01" class="range range-primary flex-1" />
                  <span class="w-14 text-right text-sm font-semibold">{{ Math.round(jpgQuality * 100) }}%</span>
                </div>
              </div>
              <div class="rounded-2xl border border-base-300 bg-base-100/70 p-4 md:col-span-2">
                <p class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/70">Resolución (DPI / PPP)</p>
                <div class="mt-3 flex flex-wrap gap-2">
                  <button v-for="option in dpiOptions" :key="option.value" type="button" class="btn btn-sm h-auto rounded-xl px-3 py-2 text-left" :class="selectedDpi === option.value ? 'btn-primary' : 'btn-outline'" @click="selectedDpi = option.value">
                    <span class="block text-xs font-semibold">{{ option.label }}</span>
                    <span class="block text-[11px] opacity-75">{{ option.helper }}</span>
                  </button>
                </div>
              </div>
            </div>
            <div class="rounded-2xl border border-base-300 bg-base-100/70 p-4 text-sm text-base-content">
              <p>
                Tamaño base: <strong>{{ state.size || 'Sin tamaño' }}</strong>
                <span class="opacity-80">· {{ selectedSizeDetail }}</span>
              </p>
              <p class="mt-1">
                Salida final: <strong>{{ targetDimensions.width }} × {{ targetDimensions.height }} px</strong>
              </p>
              <p class="mt-1 opacity-80">Objetivo: {{ objectiveTitle }}</p>
            </div>
            <button type="button" class="btn btn-primary w-full rounded-2xl text-lg py-3 mt-2" :disabled="isExporting" @click="downloadImage">
              {{ exportButtonLabel }}
            </button>
            <p v-if="exportSuccess" class="text-sm text-success">{{ exportSuccess }}</p>
            <p v-if="exportError" class="text-sm text-error">{{ exportError }}</p>
          </div>
        </div>
        <!-- Preview reducida -->
        <div class="glass soft-shadow rounded-4xl border border-base-300/70 p-5 flex flex-col items-center mx-auto">
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary mb-2">Vista previa</p>
          <div
            class="mx-auto bg-white p-2 rounded-xl shadow-2xl dark:bg-slate-900 flex flex-col items-center w-full"
            :style="{
              aspectRatio: `${targetDimensions.width} / ${targetDimensions.height}`,
              maxWidth: '220px',
              width: '100%'
            }"
          >
            <img
              :src="isPreviewRendering
                ? svgPlaceholder(targetDimensions.width, targetDimensions.height)
                : previewImageUrl"
              :alt="isPreviewRendering ? 'Cargando preview...' : 'Preview exportación'"
              class="w-full rounded-md border border-base-200 shadow"
              style="display:block;object-fit:contain;"
              :style="isPreviewRendering ? 'opacity:0.5;' : ''"
            />
            <p v-if="previewRenderError" class="mt-2 text-xs text-red-500">{{ previewRenderError }}</p>
          </div>
          <!-- DOM oculto para exportación/preview -->
          <div class="pointer-events-none fixed top-0 opacity-0" style="left: -99999px;">
            <div ref="exportPreviewRef" class="relative overflow-hidden p-7 text-white" :style="{ ...canvasBackgroundStyle, width: `${baseCanvasDimensions.width}px`, height: `${baseCanvasDimensions.height}px` }">
              <div v-if="state.elementLayout.background?.backgroundImageSrc" class="pointer-events-none absolute inset-0 overflow-hidden">
                <svg
                  v-if="backgroundUsesSvgTransparency()"
                  :style="canvasBackgroundImageStyle"
                  class="pointer-events-none"
                  viewBox="0 0 100 100"
                  preserveAspectRatio="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <defs>
                    <linearGradient
                      v-if="svgTransparencyGradient(state.elementLayout.background, 'backgroundImage').type === 'linear'"
                      :id="svgMaskIds('background').gradient"
                      gradientUnits="userSpaceOnUse"
                      :x1="svgTransparencyGradient(state.elementLayout.background, 'backgroundImage').x1"
                      :y1="svgTransparencyGradient(state.elementLayout.background, 'backgroundImage').y1"
                      :x2="svgTransparencyGradient(state.elementLayout.background, 'backgroundImage').x2"
                      :y2="svgTransparencyGradient(state.elementLayout.background, 'backgroundImage').y2"
                    >
                      <stop v-for="stop in svgTransparencyStops(state.elementLayout.background, 'backgroundImage')" :key="stop.offset" :offset="stop.offset" stop-color="#fff" :stop-opacity="stop.opacity" />
                    </linearGradient>
                    <radialGradient
                      v-else
                      :id="svgMaskIds('background').gradient"
                      gradientUnits="userSpaceOnUse"
                      :cx="svgTransparencyGradient(state.elementLayout.background, 'backgroundImage').cx"
                      :cy="svgTransparencyGradient(state.elementLayout.background, 'backgroundImage').cy"
                      :r="svgTransparencyGradient(state.elementLayout.background, 'backgroundImage').r"
                      :gradientTransform="svgTransparencyGradient(state.elementLayout.background, 'backgroundImage').transform"
                    >
                      <stop v-for="stop in svgTransparencyStops(state.elementLayout.background, 'backgroundImage')" :key="stop.offset" :offset="stop.offset" stop-color="#fff" :stop-opacity="stop.opacity" />
                    </radialGradient>
                    <mask :id="svgMaskIds('background').mask" maskUnits="userSpaceOnUse" maskContentUnits="userSpaceOnUse">
                      <rect width="100" height="100" :fill="`url(#${svgMaskIds('background').gradient})`" />
                    </mask>
                  </defs>
                  <image :href="state.elementLayout.background?.backgroundImageSrc" width="100" height="100" preserveAspectRatio="none" :mask="`url(#${svgMaskIds('background').mask})`" crossorigin="anonymous" />
                </svg>
                <img v-else :src="state.elementLayout.background?.backgroundImageSrc" alt="Fondo del dise?o" :style="canvasBackgroundImageStyle" class="pointer-events-none" crossorigin="anonymous" />
              </div>
              <div v-for="item in editorElements" :key="item.id" :style="elementBoxStyle(item.id)">
                <template v-if="item.type === 'text'">
                  <div :style="elementContentStyle(item.id)">
                    <RichTextEditor :paragraph-styles="state.elementLayout[item.id]?.paragraphStyles ?? []" :text="item.text ?? ''" :editable="false" :editor-style="richEditorContainerStyle(item.id)" :color-override="neonColorOverride(item.id)" :transparent-fill="!!state.elementLayout[item.id]?.hollowText" />
                  </div>
                </template>
                <template v-else-if="item.type === 'image'">
                  <div :style="exportElementContentStyle(item.id)">
                    <div :style="imageFrameStyle(item.id)">
                      <svg
                        v-if="item.src && imageUsesSvgTransparency(item.id)"
                        class="pointer-events-none h-full w-full"
                        viewBox="0 0 100 100"
                        preserveAspectRatio="none"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <defs>
                          <linearGradient
                            v-if="svgTransparencyGradient(state.elementLayout[item.id]).type === 'linear'"
                            :id="svgMaskIds(item.id).gradient"
                            gradientUnits="userSpaceOnUse"
                            :x1="svgTransparencyGradient(state.elementLayout[item.id]).x1"
                            :y1="svgTransparencyGradient(state.elementLayout[item.id]).y1"
                            :x2="svgTransparencyGradient(state.elementLayout[item.id]).x2"
                            :y2="svgTransparencyGradient(state.elementLayout[item.id]).y2"
                          >
                            <stop v-for="stop in svgTransparencyStops(state.elementLayout[item.id])" :key="stop.offset" :offset="stop.offset" stop-color="#fff" :stop-opacity="stop.opacity" />
                          </linearGradient>
                          <radialGradient
                            v-else
                            :id="svgMaskIds(item.id).gradient"
                            gradientUnits="userSpaceOnUse"
                            :cx="svgTransparencyGradient(state.elementLayout[item.id]).cx"
                            :cy="svgTransparencyGradient(state.elementLayout[item.id]).cy"
                            :r="svgTransparencyGradient(state.elementLayout[item.id]).r"
                            :gradientTransform="svgTransparencyGradient(state.elementLayout[item.id]).transform"
                          >
                            <stop v-for="stop in svgTransparencyStops(state.elementLayout[item.id])" :key="stop.offset" :offset="stop.offset" stop-color="#fff" :stop-opacity="stop.opacity" />
                          </radialGradient>
                          <mask :id="svgMaskIds(item.id).mask" maskUnits="userSpaceOnUse" maskContentUnits="userSpaceOnUse">
                            <rect width="100" height="100" :fill="`url(#${svgMaskIds(item.id).gradient})`" />
                          </mask>
                        </defs>
                        <image
                          :href="item.src"
                          width="100"
                          height="100"
                          preserveAspectRatio="xMidYMid slice"
                          :mask="`url(#${svgMaskIds(item.id).mask})`"
                          crossorigin="anonymous"
                        />
                      </svg>
                      <img v-else-if="item.src" :src="item.src" :alt="item.label" class="h-full w-full object-cover" :style="imageRenderStyle(item.id)" crossorigin="anonymous" />
                      <div v-if="item.src && (state.elementLayout[item.id]?.imageTintStrength ?? 0) > 0" :style="imageTintOverlayStyle(item.id)"></div>
                    </div>
                  </div>
                </template>
                <template v-else>
                  <div v-if="shapeUsesSvgTransparency(item.id)" :style="exportElementContentStyle(item.id)">
                    <svg class="h-full w-full overflow-visible" viewBox="0 0 100 100" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
                      <defs>
                        <linearGradient
                          v-if="svgTransparencyGradient(state.elementLayout[item.id]).type === 'linear'"
                          :id="svgMaskIds(item.id).gradient"
                          gradientUnits="userSpaceOnUse"
                          :x1="svgTransparencyGradient(state.elementLayout[item.id]).x1"
                          :y1="svgTransparencyGradient(state.elementLayout[item.id]).y1"
                          :x2="svgTransparencyGradient(state.elementLayout[item.id]).x2"
                          :y2="svgTransparencyGradient(state.elementLayout[item.id]).y2"
                        >
                          <stop v-for="stop in svgTransparencyStops(state.elementLayout[item.id])" :key="stop.offset" :offset="stop.offset" :stop-color="shapeSvgSolidColor(item.id)" :stop-opacity="stop.opacity" />
                        </linearGradient>
                        <linearGradient
                          v-if="svgTransparencyGradient(state.elementLayout[item.id]).type === 'linear'"
                          :id="svgMaskIds(item.id).strokeGradient"
                          gradientUnits="userSpaceOnUse"
                          :x1="svgTransparencyGradient(state.elementLayout[item.id]).x1"
                          :y1="svgTransparencyGradient(state.elementLayout[item.id]).y1"
                          :x2="svgTransparencyGradient(state.elementLayout[item.id]).x2"
                          :y2="svgTransparencyGradient(state.elementLayout[item.id]).y2"
                        >
                          <stop v-for="stop in svgTransparencyStops(state.elementLayout[item.id])" :key="stop.offset" :offset="stop.offset" :stop-color="shapeSvgStrokeColor(item.id)" :stop-opacity="stop.opacity" />
                        </linearGradient>
                        <radialGradient
                          v-if="svgTransparencyGradient(state.elementLayout[item.id]).type !== 'linear'"
                          :id="svgMaskIds(item.id).gradient"
                          gradientUnits="userSpaceOnUse"
                          :cx="svgTransparencyGradient(state.elementLayout[item.id]).cx"
                          :cy="svgTransparencyGradient(state.elementLayout[item.id]).cy"
                          :r="svgTransparencyGradient(state.elementLayout[item.id]).r"
                          :gradientTransform="svgTransparencyGradient(state.elementLayout[item.id]).transform"
                        >
                          <stop v-for="stop in svgTransparencyStops(state.elementLayout[item.id])" :key="stop.offset" :offset="stop.offset" :stop-color="shapeSvgSolidColor(item.id)" :stop-opacity="stop.opacity" />
                        </radialGradient>
                        <radialGradient
                          v-if="svgTransparencyGradient(state.elementLayout[item.id]).type !== 'linear'"
                          :id="svgMaskIds(item.id).strokeGradient"
                          gradientUnits="userSpaceOnUse"
                          :cx="svgTransparencyGradient(state.elementLayout[item.id]).cx"
                          :cy="svgTransparencyGradient(state.elementLayout[item.id]).cy"
                          :r="svgTransparencyGradient(state.elementLayout[item.id]).r"
                          :gradientTransform="svgTransparencyGradient(state.elementLayout[item.id]).transform"
                        >
                          <stop v-for="stop in svgTransparencyStops(state.elementLayout[item.id])" :key="stop.offset" :offset="stop.offset" :stop-color="shapeSvgStrokeColor(item.id)" :stop-opacity="stop.opacity" />
                        </radialGradient>
                      </defs>
                      <ellipse
                        v-if="shapeHasBorder(item.id) && (item.shapeKind === 'circle' || item.shapeKind === 'ellipse')"
                        cx="50"
                        cy="50"
                        rx="50"
                        ry="50"
                        :fill="`url(#${svgMaskIds(item.id).strokeGradient})`"
                      />
                      <polygon
                        v-else-if="shapeHasBorder(item.id) && polygonPointsFromClipPath(item.shapeKind)"
                        :points="polygonPointsFromClipPath(item.shapeKind)"
                        :fill="`url(#${svgMaskIds(item.id).strokeGradient})`"
                      />
                      <rect
                        v-else-if="shapeHasBorder(item.id)"
                        x="0"
                        y="0"
                        width="100"
                        height="100"
                        :rx="item.shapeKind === 'rectangle-outline' ? 0 : 8"
                        :fill="`url(#${svgMaskIds(item.id).strokeGradient})`"
                      />

                      <ellipse
                        v-if="item.shapeKind === 'circle' || item.shapeKind === 'ellipse'"
                        cx="50"
                        cy="50"
                        rx="50"
                        ry="50"
                        :fill="`url(#${svgMaskIds(item.id).gradient})`"
                        :transform="shapeInnerTransform(item.id)"
                      />
                      <polygon
                        v-else-if="polygonPointsFromClipPath(item.shapeKind)"
                        :points="polygonPointsFromClipPath(item.shapeKind)"
                        :fill="`url(#${svgMaskIds(item.id).gradient})`"
                        :transform="shapeInnerTransform(item.id)"
                      />
                      <rect
                        v-else
                        x="0"
                        y="0"
                        width="100"
                        height="100"
                        :rx="item.shapeKind === 'rectangle-outline' ? 0 : 8"
                        :fill="`url(#${svgMaskIds(item.id).gradient})`"
                        :transform="shapeInnerTransform(item.id)"
                      />
                    </svg>
                  </div>
                  <div v-else class="relative h-full w-full" :style="exportElementContentStyle(item.id)">
                    <div class="h-full w-full" :style="shapeRenderModel(item).outerStyle"></div>
                    <div v-if="shapeRenderModel(item).innerStyle" class="pointer-events-none absolute inset-0" :style="shapeRenderModel(item).innerStyle"></div>
                    <svg v-if="shapeRenderModel(item).svgStroke" class="pointer-events-none absolute inset-0 h-full w-full overflow-visible" viewBox="0 0 100 100" preserveAspectRatio="none">
                      <polygon :points="shapeRenderModel(item).svgStroke.points" fill="none" :stroke="shapeRenderModel(item).svgStroke.stroke" :stroke-width="shapeRenderModel(item).svgStroke.strokeWidth" :stroke-dasharray="shapeRenderModel(item).svgStroke.dasharray" :stroke-linecap="shapeRenderModel(item).svgStroke.linecap" :stroke-linejoin="shapeRenderModel(item).svgStroke.linejoin" vector-effect="non-scaling-stroke" />
                    </svg>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </dialog>
</template>
