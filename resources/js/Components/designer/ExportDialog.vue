<script setup>
// Componente de exportación extraído de ExportPage.vue
import { ref, computed, nextTick, watch, onMounted, onBeforeUnmount } from 'vue';
import { toCanvasExport, toJpegExport, toPngExport } from '../../utils/useHtml2Image';
import { useDesignerState } from '../../composables/useDesignerState';
import { objectiveOptions, objectiveRecommendations } from '../../data/designer';
import StepFooter from './StepFooter.vue';
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
const generatedCanvasHostRef = ref(null);
const isPreviewRendering = ref(false);
const previewRenderError = ref('');
let previewTimer = null;
let previewRenderSeq = 0;

const resolvedSizeOption = computed(() => {
    const objectiveRules = objectiveRecommendations[state.objective] ?? objectiveRecommendations.generic;
    const options = objectiveRules[state.outputType] ?? [];
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
}));

async function buildRendererOptions(width, height) {
    return {};
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
        const canvas = await toCanvasExport(exportPreviewRef.value, {
            width: baseCanvasDimensions.value.width,
            height: baseCanvasDimensions.value.height,
        });
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
        const dataUrl = selectedExportFormat.value === 'jpg'
            ? await toJpegExport(node, {
                width,
                height,
                quality: clamp(Number(jpgQuality.value), 0.6, 1),
            })
            : await toPngExport(node, {
                width,
                height,
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
  <dialog open class="modal modal-open backdrop-blur">
    <div class="modal-box max-w-4xl w-full relative" @click.stop>
      <h3 class="font-bold text-xl mb-4">Exportar diseño</h3>
      <section class="grid gap-8 md:grid-cols-[1.5fr_0.8fr] items-start">
        <!-- Opciones de exportación -->
        <div class="glass soft-shadow rounded-4xl border border-white/70 p-6 sm:p-10 dark:border-slate-700/70">
          <div class="space-y-6">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary mb-1">Opciones de exportación</p>
              <h4 class="text-2xl font-bold mb-2">Elige cómo exportar tu diseño</h4>
              <p class="text-sm text-base-content/70 mb-2">Personaliza el formato, calidad y resolución de la imagen exportada.</p>
            </div>
            <div class="grid gap-4 md:grid-cols-2">
              <div class="rounded-2xl border border-white/20 bg-white/5 p-4">
                <p class="text-xs font-semibold uppercase tracking-[0.2em] text-white/70">Formato</p>
                <div class="mt-3 flex gap-2">
                  <button type="button" class="btn btn-sm rounded-xl flex-1" :class="selectedExportFormat === 'png' ? 'btn-primary' : 'btn-outline text-white border-white/40 hover:bg-white/10'" @click="selectedExportFormat = 'png'">PNG</button>
                  <button type="button" class="btn btn-sm rounded-xl flex-1" :class="selectedExportFormat === 'jpg' ? 'btn-primary' : 'btn-outline text-white border-white/40 hover:bg-white/10'" @click="selectedExportFormat = 'jpg'">JPG</button>
                </div>
                <p class="mt-2 text-xs text-white/70">PNG para máxima fidelidad; JPG para menor peso.</p>
              </div>
              <div v-if="selectedExportFormat === 'jpg'" class="rounded-2xl border border-white/20 bg-white/5 p-4">
                <p class="text-xs font-semibold uppercase tracking-[0.2em] text-white/70">Calidad JPG</p>
                <div class="mt-3 flex items-center gap-3">
                  <input v-model.number="jpgQuality" type="range" min="0.6" max="1" step="0.01" class="range range-primary flex-1" />
                  <span class="w-14 text-right text-sm font-semibold">{{ Math.round(jpgQuality * 100) }}%</span>
                </div>
              </div>
              <div class="rounded-2xl border border-white/20 bg-white/5 p-4 md:col-span-2">
                <p class="text-xs font-semibold uppercase tracking-[0.2em] text-white/70">Resolución (DPI / PPP)</p>
                <div class="mt-3 flex flex-wrap gap-2">
                  <button v-for="option in dpiOptions" :key="option.value" type="button" class="btn btn-sm h-auto rounded-xl px-3 py-2 text-left" :class="selectedDpi === option.value ? 'btn-primary' : 'btn-outline text-white border-white/40 hover:bg-white/10'" @click="selectedDpi = option.value">
                    <span class="block text-xs font-semibold">{{ option.label }}</span>
                    <span class="block text-[11px] opacity-75">{{ option.helper }}</span>
                  </button>
                </div>
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
            <button type="button" class="btn btn-primary w-full rounded-2xl text-lg py-3 mt-2" :disabled="isExporting" @click="downloadImage">
              {{ exportButtonLabel }}
            </button>
            <p v-if="exportSuccess" class="text-sm text-emerald-300">{{ exportSuccess }}</p>
            <p v-if="exportError" class="text-sm text-red-300">{{ exportError }}</p>
          </div>
          <!-- StepFooter eliminado -->
        </div>
        <!-- Preview reducida -->
        <div class="glass soft-shadow rounded-4xl border border-white/70 p-5 flex flex-col items-center dark:border-slate-700/70 mx-auto">
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary mb-2">Vista previa</p>
          <div class="mx-auto bg-white p-2 rounded-xl shadow-2xl dark:bg-slate-900 flex flex-col items-center w-full">
            <div ref="generatedCanvasHostRef" class="mx-auto w-full max-w-[220px]"></div>
            <p v-if="isPreviewRendering" class="mt-2 text-xs text-base-content/70">Actualizando preview...</p>
            <p v-if="previewRenderError" class="mt-2 text-xs text-red-500">{{ previewRenderError }}</p>
          </div>
          <!-- Canvas oculto para exportación -->
          <div class="pointer-events-none fixed top-0 opacity-0" style="left: -99999px;">
            <div ref="exportPreviewRef" class="relative overflow-hidden p-7 text-white" :style="{ ...canvasBackgroundStyle, width: `${baseCanvasDimensions.width}px`, height: `${baseCanvasDimensions.height}px` }">
              <div v-if="state.elementLayout.background?.backgroundImageSrc" class="pointer-events-none absolute inset-0 overflow-hidden">
                <img :src="state.elementLayout.background?.backgroundImageSrc" alt="Fondo del diseño" :style="canvasBackgroundImageStyle" class="pointer-events-none" crossorigin="anonymous" />
              </div>
              <div v-for="item in editorElements" :key="item.id" :style="elementBoxStyle(item.id)">
                <template v-if="item.type === 'text'">
                  <div :style="elementContentStyle(item.id)">
                    <RichTextEditor :paragraph-styles="state.elementLayout[item.id]?.paragraphStyles ?? []" :text="item.text ?? ''" :editable="false" :editor-style="richEditorContainerStyle(item.id)" :color-override="neonColorOverride(item.id)" :transparent-fill="!!state.elementLayout[item.id]?.hollowText" />
                  </div>
                </template>
                <template v-else-if="item.type === 'image'">
                  <div :style="imageFrameStyle(item.id)">
                    <img v-if="item.src" :src="item.src" :alt="item.label" class="h-full w-full object-cover" :style="imageRenderStyle(item.id)" crossorigin="anonymous" />
                    <div v-if="item.src && (state.elementLayout[item.id]?.imageTintStrength ?? 0) > 0" :style="imageTintOverlayStyle(item.id)"></div>
                  </div>
                </template>
                <template v-else>
                  <div class="relative h-full w-full">
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
