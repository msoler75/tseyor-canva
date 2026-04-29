<script setup>
import { ref, computed, nextTick, watch, onMounted, onBeforeUnmount } from 'vue';
import { toCanvasExport, toJpegExport, toPngExport } from '../../utils/useHtml2Image';
import { useDesignerState } from '../../composables/useDesignerState';
import { brochurePrintPairForPhysicalPage, isBrochureFormat, isHorizontalFormat, objectiveOptions, resolveObjectiveSizeOptions } from '../../data/designer';
import RichTextEditor from './RichTextEditor.vue';
import {
    BASE_TEXT_ELEMENT_IDS,
    SHAPE_CLIP_PATHS,
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
const documentPages = computed(() => (Array.isArray(state.pages) && state.pages.length
    ? state.pages
    : [{
        id: state.activePageId ?? 'page-1',
        content: state.content,
        elementLayout: state.elementLayout,
        customElements: state.customElements ?? {},
    }]
));
const hasMultiplePages = computed(() => documentPages.value.length > 1);
const isBrochureExport = computed(() => isBrochureFormat(state.format));
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
let isRenderingPageSnapshot = false;

const resolvedSizeOption = computed(() => {
    const options = resolveObjectiveSizeOptions(state.objective, state.outputType, state.format);
    return options.find((option) => option.label === state.size) ?? null;
});

const selectedSizeDetail = computed(() => resolvedSizeOption.value?.detail ?? state.size ?? '1080 ? 1080 px');
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
    if (isHorizontalFormat(state.format)) {
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

const baseFileName = computed(() => `${sanitizeFileName(state.designTitle || state.content.title || 'diseno')}-${selectedDpi.value}dpi`);
const fileName = computed(() => {
    if (selectedExportFormat.value === 'pdf') return `${baseFileName.value}.pdf`;
    if (hasMultiplePages.value) return `${baseFileName.value}-${selectedExportFormat.value}.zip`;
    return `${baseFileName.value}.${selectedExportFormat.value}`;
});
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

const exportShapeClipPaths = SHAPE_CLIP_PATHS;
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

const shapeSvgStrokeDasharray = (id) => {
    const layout = state.elementLayout[id] ?? {};
    if (!layout.border) return null;
    const strokeWidth = shapeSvgStrokeWidth(id);
    if (layout.borderStyle === 'dashed') return `${strokeWidth * 4} ${strokeWidth * 2}`;
    if (layout.borderStyle === 'dotted') return `0 ${strokeWidth * 2.2}`;
    return null;
};

const shapeSvgStrokeLinecap = (id) => (
    state.elementLayout[id]?.borderStyle === 'dotted' ? 'round' : 'butt'
);

const shapeInnerTransform = () => '';

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
    return buildShapeStyle(state.elementLayout[item.id] ?? {}, item.shapeKind, exportShapeClipPaths);
}
function shapeRenderModel(item) {
    return buildShapeRenderModel(state.elementLayout[item.id] ?? {}, item.shapeKind, exportShapeClipPaths);
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

const clonePlain = (value) => JSON.parse(JSON.stringify(value ?? null));
const dataUrlToBytes = (dataUrl) => {
    const [, base64 = ''] = String(dataUrl).split(',');
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
};
const bytesToBinaryString = (bytes) => {
    let result = '';
    const chunkSize = 0x8000;
    for (let i = 0; i < bytes.length; i += chunkSize) {
        result += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
    }
    return result;
};
const downloadBlob = (blob, name) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = name;
    link.href = url;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
};
const withRenderedPage = async (page, callback) => {
    isRenderingPageSnapshot = true;
    const previous = {
        activePageId: state.activePageId,
        content: clonePlain(state.content),
        elementLayout: clonePlain(state.elementLayout),
        customElements: clonePlain(state.customElements ?? {}),
    };

    state.activePageId = page.id;
    state.content = clonePlain(page.content ?? {});
    state.elementLayout = clonePlain(page.elementLayout ?? {});
    state.customElements = clonePlain(page.customElements ?? {});

    await nextTick();
    if (document.fonts?.ready) {
        await document.fonts.ready;
    }

    try {
        return await callback();
    } finally {
        state.activePageId = previous.activePageId;
        state.content = previous.content;
        state.elementLayout = previous.elementLayout;
        state.customElements = previous.customElements;
        await nextTick();
        isRenderingPageSnapshot = false;
    }
};
const renderCurrentPreviewNode = async (format) => {
    if (!exportPreviewRef.value) {
        throw new Error('No export preview node');
    }

    const node = exportPreviewRef.value;
    const { width, height } = targetDimensions.value;
    const baseWidth = baseCanvasDimensions.value.width;
    const baseHeight = baseCanvasDimensions.value.height;
    const prevWidth = node.style.width;
    const prevHeight = node.style.height;
    const prevTransform = node.style.transform;
    const prevTransformOrigin = node.style.transformOrigin;
    const scaleX = width / baseWidth;
    const scaleY = height / baseHeight;

    node.style.width = baseWidth + 'px';
    node.style.height = baseHeight + 'px';
    node.style.transformOrigin = 'top left';
    node.style.transform = `scale(${scaleX}, ${scaleY})`;

    try {
        const backgroundColor = state.elementLayout.background?.fillMode === 'solid'
            ? (state.elementLayout.background?.backgroundColor || '#fff')
            : null;

        return format === 'jpg'
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
    } finally {
        node.style.width = prevWidth;
        node.style.height = prevHeight;
        node.style.transform = prevTransform;
        node.style.transformOrigin = prevTransformOrigin;
    }
};

const loadImageFromDataUrl = (dataUrl) => new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = dataUrl;
});

const drawBrochurePanel = (context, sourceImages, brochurePageNumber, destinationX, width, height) => {
    const sourceSpreadIndex = brochurePageNumber === (sourceImages.length * 2)
        ? 0
        : Math.floor(brochurePageNumber / 2);
    const sourceIsLeftPanel = brochurePageNumber === (sourceImages.length * 2)
        || brochurePageNumber % 2 === 0;
    const sourceX = sourceIsLeftPanel ? 0 : width;
    context.drawImage(sourceImages[sourceSpreadIndex], sourceX, 0, width, height, destinationX, 0, width, height);
};

const renderBrochurePrintPages = async (format) => {
    const pages = documentPages.value;
    const renderedPages = [];

    for (const page of pages) {
        renderedPages.push(await withRenderedPage(page, () => renderCurrentPreviewNode(format)));
    }

    if (renderedPages.length <= 2) {
        return renderedPages;
    }

    const sourceImages = await Promise.all(renderedPages.map((dataUrl) => loadImageFromDataUrl(dataUrl)));
    const { width, height } = targetDimensions.value;
    const panelWidth = Math.floor(width / 2);
    const outputMime = format === 'jpg' ? 'image/jpeg' : 'image/png';

    return pages.map((_, pageIndex) => {
        const [leftBrochurePage, rightBrochurePage] = brochurePrintPairForPhysicalPage(pageIndex, pages.length);
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const context = canvas.getContext('2d');

        if (format === 'jpg') {
            context.fillStyle = '#ffffff';
            context.fillRect(0, 0, width, height);
        }

        drawBrochurePanel(context, sourceImages, leftBrochurePage, 0, panelWidth, height);
        drawBrochurePanel(context, sourceImages, rightBrochurePage, panelWidth, panelWidth, height);

        return format === 'jpg'
            ? canvas.toDataURL(outputMime, jpgQuality.value)
            : canvas.toDataURL(outputMime);
    });
};

let crcTable = null;
const getCrcTable = () => {
    if (crcTable) return crcTable;
    crcTable = new Uint32Array(256);
    for (let n = 0; n < 256; n += 1) {
        let c = n;
        for (let k = 0; k < 8; k += 1) {
            c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
        }
        crcTable[n] = c >>> 0;
    }
    return crcTable;
};
const crc32 = (bytes) => {
    const table = getCrcTable();
    let crc = 0xffffffff;
    bytes.forEach((byte) => {
        crc = table[(crc ^ byte) & 0xff] ^ (crc >>> 8);
    });
    return (crc ^ 0xffffffff) >>> 0;
};
const writeUint16 = (array, offset, value) => {
    array[offset] = value & 0xff;
    array[offset + 1] = (value >>> 8) & 0xff;
};
const writeUint32 = (array, offset, value) => {
    array[offset] = value & 0xff;
    array[offset + 1] = (value >>> 8) & 0xff;
    array[offset + 2] = (value >>> 16) & 0xff;
    array[offset + 3] = (value >>> 24) & 0xff;
};
const createZipBlob = (files) => {
    const encoder = new TextEncoder();
    const chunks = [];
    const central = [];
    let offset = 0;

    files.forEach((file) => {
        const nameBytes = encoder.encode(file.name);
        const data = file.bytes;
        const crc = crc32(data);
        const local = new Uint8Array(30 + nameBytes.length);
        writeUint32(local, 0, 0x04034b50);
        writeUint16(local, 4, 20);
        writeUint16(local, 6, 0);
        writeUint16(local, 8, 0);
        writeUint16(local, 10, 0);
        writeUint16(local, 12, 0);
        writeUint32(local, 14, crc);
        writeUint32(local, 18, data.length);
        writeUint32(local, 22, data.length);
        writeUint16(local, 26, nameBytes.length);
        writeUint16(local, 28, 0);
        local.set(nameBytes, 30);
        chunks.push(local, data);

        const centralHeader = new Uint8Array(46 + nameBytes.length);
        writeUint32(centralHeader, 0, 0x02014b50);
        writeUint16(centralHeader, 4, 20);
        writeUint16(centralHeader, 6, 20);
        writeUint16(centralHeader, 8, 0);
        writeUint16(centralHeader, 10, 0);
        writeUint16(centralHeader, 12, 0);
        writeUint16(centralHeader, 14, 0);
        writeUint32(centralHeader, 16, crc);
        writeUint32(centralHeader, 20, data.length);
        writeUint32(centralHeader, 24, data.length);
        writeUint16(centralHeader, 28, nameBytes.length);
        writeUint16(centralHeader, 30, 0);
        writeUint16(centralHeader, 32, 0);
        writeUint16(centralHeader, 34, 0);
        writeUint16(centralHeader, 36, 0);
        writeUint32(centralHeader, 38, 0);
        writeUint32(centralHeader, 42, offset);
        centralHeader.set(nameBytes, 46);
        central.push(centralHeader);
        offset += local.length + data.length;
    });

    const centralOffset = offset;
    central.forEach((chunk) => {
        chunks.push(chunk);
        offset += chunk.length;
    });
    const end = new Uint8Array(22);
    writeUint32(end, 0, 0x06054b50);
    writeUint16(end, 8, files.length);
    writeUint16(end, 10, files.length);
    writeUint32(end, 12, offset - centralOffset);
    writeUint32(end, 16, centralOffset);
    writeUint16(end, 20, 0);
    chunks.push(end);

    return new Blob(chunks, { type: 'application/zip' });
};
const createPdfBlob = (jpegDataUrls, width, height) => {
    const objects = [];
    objects.push('<< /Type /Catalog /Pages 2 0 R >>');
    const pageObjectIds = jpegDataUrls.map((_, index) => 3 + index * 3);
    objects.push(`<< /Type /Pages /Kids [${pageObjectIds.map((id) => `${id} 0 R`).join(' ')}] /Count ${jpegDataUrls.length} >>`);

    jpegDataUrls.forEach((dataUrl, index) => {
        const pageId = 3 + index * 3;
        const contentId = pageId + 1;
        const imageId = pageId + 2;
        const imageName = `Im${index + 1}`;
        const commands = `q\n${width} 0 0 ${height} 0 0 cm\n/${imageName} Do\nQ\n`;
        const imageBytes = dataUrlToBytes(dataUrl);
        objects.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${width} ${height}] /Resources << /XObject << /${imageName} ${imageId} 0 R >> >> /Contents ${contentId} 0 R >>`);
        objects.push(`<< /Length ${commands.length} >>\nstream\n${commands}endstream`);
        objects.push(`<< /Type /XObject /Subtype /Image /Width ${width} /Height ${height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${imageBytes.length} >>\nstream\n${bytesToBinaryString(imageBytes)}\nendstream`);
    });

    let pdf = '%PDF-1.4\n';
    const offsets = [0];
    objects.forEach((object, index) => {
        offsets.push(pdf.length);
        pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
    });
    const xrefOffset = pdf.length;
    pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
    offsets.slice(1).forEach((offset) => {
        pdf += `${String(offset).padStart(10, '0')} 00000 n \n`;
    });
    pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`;
    const bytes = new Uint8Array(pdf.length);
    for (let i = 0; i < pdf.length; i += 1) {
        bytes[i] = pdf.charCodeAt(i) & 0xff;
    }
    return new Blob([bytes], { type: 'application/pdf' });
};

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
    const previewFormat = selectedExportFormat.value === 'jpg' ? 'jpg' : 'png';
    const dataUrl = await withRenderedPage(documentPages.value[0], () => renderCurrentPreviewNode(previewFormat));
    if (runId !== previewRenderSeq) return;
    previewImageUrl.value = dataUrl;
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
  if (isRenderingPageSnapshot) {
    return;
  }
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
    const { width, height } = targetDimensions.value;
    try {
        const pages = documentPages.value;
        const exportPages = isBrochureExport.value
            ? await renderBrochurePrintPages(selectedExportFormat.value === 'pdf' ? 'jpg' : selectedExportFormat.value)
            : null;

        if (selectedExportFormat.value === 'pdf') {
            const jpegPages = [];
            if (exportPages) {
                jpegPages.push(...exportPages);
            } else {
                for (const page of pages) {
                    jpegPages.push(await withRenderedPage(page, () => renderCurrentPreviewNode('jpg')));
                }
            }
            downloadBlob(createPdfBlob(jpegPages, width, height), fileName.value);
            exportSuccess.value = `PDF generado con ${jpegPages.length} página${jpegPages.length === 1 ? '' : 's'}${isBrochureExport.value ? ' impuestas para folleto' : ''}.`;
            return;
        }

        if (pages.length > 1 || exportPages) {
            const files = [];
            let index = 1;
            const renderedPages = exportPages ?? [];

            if (!renderedPages.length) {
                for (const page of pages) {
                    renderedPages.push(await withRenderedPage(page, () => renderCurrentPreviewNode(selectedExportFormat.value)));
                }
            }

            for (const dataUrl of renderedPages) {
                files.push({
                    name: `${baseFileName.value}-pagina-${String(index).padStart(2, '0')}.${selectedExportFormat.value}`,
                    bytes: dataUrlToBytes(dataUrl),
                });
                index += 1;
            }
            downloadBlob(createZipBlob(files), fileName.value);
            exportSuccess.value = `ZIP generado con ${files.length} imágenes ${selectedExportFormat.value.toUpperCase()}${isBrochureExport.value ? ' impuestas para folleto' : ''}.`;
            return;
        }

        const dataUrl = await withRenderedPage(pages[0], () => renderCurrentPreviewNode(selectedExportFormat.value));
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
                  <button type="button" class="btn btn-sm rounded-xl flex-1" :class="selectedExportFormat === 'pdf' ? 'btn-primary' : 'btn-outline'" @click="selectedExportFormat = 'pdf'">PDF</button>
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
                        fill="none"
                        :stroke="`url(#${svgMaskIds(item.id).strokeGradient})`"
                        :stroke-width="shapeSvgStrokeWidth(item.id)"
                        :stroke-dasharray="shapeSvgStrokeDasharray(item.id)"
                        :stroke-linecap="shapeSvgStrokeLinecap(item.id)"
                        stroke-linejoin="round"
                      />
                      <polygon
                        v-else-if="shapeHasBorder(item.id) && polygonPointsFromClipPath(item.shapeKind)"
                        :points="polygonPointsFromClipPath(item.shapeKind)"
                        fill="none"
                        :stroke="`url(#${svgMaskIds(item.id).strokeGradient})`"
                        :stroke-width="shapeSvgStrokeWidth(item.id)"
                        :stroke-dasharray="shapeSvgStrokeDasharray(item.id)"
                        :stroke-linecap="shapeSvgStrokeLinecap(item.id)"
                        stroke-linejoin="round"
                      />
                      <rect
                        v-else-if="shapeHasBorder(item.id)"
                        x="0"
                        y="0"
                        width="100"
                        height="100"
                        :rx="item.shapeKind === 'rectangle-outline' ? 0 : 8"
                        fill="none"
                        :stroke="`url(#${svgMaskIds(item.id).strokeGradient})`"
                        :stroke-width="shapeSvgStrokeWidth(item.id)"
                        :stroke-dasharray="shapeSvgStrokeDasharray(item.id)"
                        :stroke-linecap="shapeSvgStrokeLinecap(item.id)"
                        stroke-linejoin="round"
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
                    <svg v-if="shapeRenderModel(item).svgStroke" class="pointer-events-none absolute inset-0 h-full w-full overflow-visible" viewBox="0 0 100 100" preserveAspectRatio="none">
                      <polygon :points="shapeRenderModel(item).svgStroke.points" fill="none" :stroke="shapeRenderModel(item).svgStroke.stroke" :stroke-width="shapeRenderModel(item).svgStroke.strokeWidth" :stroke-dasharray="shapeRenderModel(item).svgStroke.dasharray" :stroke-linecap="shapeRenderModel(item).svgStroke.linecap" :stroke-linejoin="shapeRenderModel(item).svgStroke.linejoin" vector-effect="non-scaling-stroke" />
                    </svg>
                    <div class="relative h-full w-full" :style="shapeRenderModel(item).outerStyle"></div>
                    <div v-if="shapeRenderModel(item).innerStyle" class="pointer-events-none absolute inset-0" :style="shapeRenderModel(item).innerStyle"></div>
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
