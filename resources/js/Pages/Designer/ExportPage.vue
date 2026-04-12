<script setup>
import { toCanvas, toJpeg, toPng } from 'html-to-image';
import DesignerLayout from '../../Layouts/DesignerLayout.vue';
import StepFooter from '../../Components/designer/StepFooter.vue';
import RichTextEditor from '../../Components/designer/RichTextEditor.vue';
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { objectiveOptions, objectiveRecommendations } from '../../data/designer';
import { useDesignerState } from '../../composables/useDesignerState';

defineProps({ currentStep: String, steps: Array, navigation: Object });
const state = useDesignerState();

const BASE_CANVAS_SHORT_SIDE = 368;
const BASE_CANVAS_LONG_SIDE = 620;
const baseTextElementIds = new Set(['title', 'subtitle', 'meta', 'contact', 'extra']);
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

const canvasBackgroundStyle = computed(() => {
    const bg = state.elementLayout.background;
    if (bg?.fillMode === 'gradient') {
        return {
            background: `linear-gradient(${bg.gradientAngle || 135}deg, ${bg.gradientStart || '#0ea5e9'}, ${bg.gradientEnd || '#8b5cf6'})`,
        };
    }
    return {
        backgroundColor: bg?.backgroundColor || '#4338ca',
    };
});

const editorElements = computed(() => {
    const baseTextElements = [
        { id: 'title', type: 'text', label: 'Titulo', text: state.content.title },
        { id: 'subtitle', type: 'text', label: 'Subtitulo', text: state.content.subtitle },
        { id: 'meta', type: 'text', label: 'Fecha / hora', text: [state.content.date, state.content.time].filter(Boolean).join(' · ') },
        { id: 'contact', type: 'text', label: 'Contacto', text: state.content.contact },
        { id: 'extra', type: 'text', label: 'Texto adicional', text: state.content.extra },
    ];

    const customElements = Object.entries(state.customElements ?? {}).map(([id, element]) => ({
        id,
        type: element.type,
        label: element.label ?? 'Elemento',
        text: element.type === 'text' ? (element.text ?? '') : '',
        src: element.type === 'image' ? element.src : null,
        shapeKind: element.type === 'shape' ? element.shapeKind : null,
    }));

    return [...baseTextElements, ...customElements]
        .filter((item) => state.elementLayout[item.id])
        .sort((a, b) => (state.elementLayout[a.id]?.zIndex ?? 0) - (state.elementLayout[b.id]?.zIndex ?? 0));
});

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

function normalizePickerColor(value, fallback = '#ffffff') {
    if (typeof value !== 'string') return fallback;

    const trimmed = value.trim();
    if (/^#[\da-f]{6}$/i.test(trimmed)) return trimmed;
    if (/^#[\da-f]{3}$/i.test(trimmed)) {
        return `#${trimmed[1]}${trimmed[1]}${trimmed[2]}${trimmed[2]}${trimmed[3]}${trimmed[3]}`;
    }

    return fallback;
}

function blendHexWithWhite(hexColor, amountPercent = 40) {
    if (typeof hexColor !== 'string') return '#ffffff';

    const normalized = normalizePickerColor(hexColor, '#ffffff');
    const amount = clamp(Number(amountPercent), 0, 100) / 100;
    const channel = (index) => Number.parseInt(normalized.slice(index, index + 2), 16);
    const mix = (value) => Math.round(value + (255 - value) * amount).toString(16).padStart(2, '0');

    const r = mix(channel(1));
    const g = mix(channel(3));
    const b = mix(channel(5));
    return `#${r}${g}${b}`;
}

function parseSizeDetail(detail) {
    const source = String(detail || '').replace(',', '.').trim();

    const pxMatch = source.match(/(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*px/i);
    if (pxMatch) {
        return {
            unit: 'px',
            width: Number(pxMatch[1]),
            height: Number(pxMatch[2]),
        };
    }

    const cmMatch = source.match(/(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*cm/i);
    if (cmMatch) {
        return {
            unit: 'cm',
            width: Number(cmMatch[1]),
            height: Number(cmMatch[2]),
        };
    }

    return {
        unit: 'px',
        width: 1080,
        height: 1080,
    };
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

function getParagraphs(text) {
    const normalized = String(text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    const paragraphs = normalized.split('\n');
    return paragraphs.length ? paragraphs : [''];
}

function getParagraphStyleForElement(id, index) {
    const layout = state.elementLayout[id] ?? {};
    const style = layout.paragraphStyles?.[index] ?? {};

    return {
        fontSize: style.fontSize ?? layout.fontSize ?? 16,
        color: style.color ?? layout.color ?? '#ffffff',
        fontFamily: style.fontFamily ?? layout.fontFamily ?? 'Inter, sans-serif',
        fontWeight: style.fontWeight ?? layout.fontWeight ?? 'regular',
        italic: style.italic ?? layout.italic ?? false,
        uppercase: style.uppercase ?? layout.uppercase ?? false,
        textAlign: style.textAlign ?? layout.textAlign ?? 'left',
        letterSpacing: style.letterSpacing ?? layout.letterSpacing ?? 0,
        lineHeight: style.lineHeight ?? layout.lineHeight ?? 1.3,
    };
}

function buildTextShadow(layout = {}, textColor = null) {
    const shadows = [];
    const shadowOffset = clamp(Number(layout.shadowOffset ?? 20), 0, 100);
    const shadowBlur = clamp(Number(layout.shadowBlur ?? 25), 0, 100);
    const shadowOpacity = clamp(Number(layout.shadowOpacity ?? 65), 0, 100);
    const shadowAngle = ((Number(layout.shadowAngle ?? 135) % 360) + 360) % 360;
    const neonIntensity = clamp(Number(layout.neonIntensity ?? 55), 0, 100);

    const toShadowOffset = (distance) => {
        const rad = (shadowAngle * Math.PI) / 180;
        return {
            x: Math.round(Math.cos(rad) * distance),
            y: Math.round(Math.sin(rad) * distance),
        };
    };

    const applyAlphaToHex = (color, alphaPercent) => {
        if (typeof color !== 'string') return color;
        const value = color.trim();
        const alpha = clamp(100 - alphaPercent, 0, 100);

        if (/^#[\da-f]{3}$/i.test(value)) {
            const r = value[1];
            const g = value[2];
            const b = value[3];
            const a = Math.round((alpha / 100) * 255).toString(16).padStart(2, '0');
            return `#${r}${r}${g}${g}${b}${b}${a}`;
        }

        if (/^#[\da-f]{6}$/i.test(value)) {
            const a = Math.round((alpha / 100) * 255).toString(16).padStart(2, '0');
            return `${value}${a}`;
        }

        return value;
    };

    if (layout.border && !layout.hollowText) {
        const borderColor = layout.contourColor || '#7c3aed';
        const width = clamp(Number(layout.contourWidth ?? 2), 1, 12);
        const ring = Math.max(1, Math.round(width));
        for (let x = -ring; x <= ring; x++) {
            for (let y = -ring; y <= ring; y++) {
                if (x === 0 && y === 0) continue;
                if (x * x + y * y <= ring * ring) {
                    shadows.push(`${x}px ${y}px 0 ${borderColor}`);
                }
            }
        }
    }

    if (layout.textEffectMode === 'distort') {
        const primaryColor = layout.shadowColor || '#f0f';
        const secondaryColor = layout.neonColor || '#0ff';
        const distance = clamp(Math.round(clamp(Number(layout.shadowOffset ?? 15), 0, 20) * 0.2), 1, 20);
        const offset = toShadowOffset(distance);
        shadows.push(
            `${offset.x}px ${offset.y}px 0 ${primaryColor}`,
            `${-offset.x}px ${-offset.y}px 0 ${secondaryColor}`,
        );
    } else if (layout.shadow) {
        const color = layout.shadowColor || '#0f172a';
        const preset = layout.shadowPreset || 'soft';
        const colorWithAlpha = applyAlphaToHex(color, shadowOpacity);
        const isMisaligned = layout.textEffectMode === 'misaligned';

        if (isMisaligned) {
            const distance = Math.max(0, Math.round(shadowOffset * 0.25));
            const offset = toShadowOffset(distance);
            shadows.push(`${offset.x}px ${offset.y}px 0 ${colorWithAlpha}`);
        } else if (preset === 'hard') {
            const distance = Math.round(shadowOffset * 0.6);
            const offset = toShadowOffset(distance);
            shadows.push(`${offset.x}px ${offset.y}px 0 ${colorWithAlpha}`);
        } else if (preset === 'echo') {
            const distance = Math.max(1, Math.round(shadowOffset * 0.25));
            const offset = toShadowOffset(distance);
            shadows.push(
                `${offset.x}px ${offset.y}px 0 ${colorWithAlpha}`,
                `${offset.x * 2}px ${offset.y * 2}px 0 ${colorWithAlpha}`,
                `${offset.x * 3}px ${offset.y * 3}px 0 ${colorWithAlpha}`,
            );
        } else {
            const distance = Math.round(shadowOffset * 0.6);
            const blur = Math.round(shadowBlur * 0.8);
            const offset = toShadowOffset(distance);
            shadows.push(`${offset.x}px ${offset.y}px ${blur}px ${colorWithAlpha}`);
        }
    }

    if (layout.textEffectMode === 'neon' && !layout.hollowText) {
        const sourceColor = textColor || '#7c3aed';
        const blurSoft = Math.round(4 + neonIntensity / 5);
        const blurStrong = Math.round(10 + neonIntensity / 2.5);
        const glowColor = normalizePickerColor(sourceColor, '#7c3aed');
        shadows.push(`0 0 ${blurSoft}px ${glowColor}`, `0 0 ${blurStrong}px ${glowColor}`);
    } else if (layout.neonColor && layout.textEffectMode !== 'distort') {
        const blurSoft = Math.round(4 + neonIntensity / 6);
        const blurStrong = Math.round(12 + neonIntensity / 2);
        shadows.push(`0 0 ${blurSoft}px ${layout.neonColor}`, `0 0 ${blurStrong}px ${layout.neonColor}`);
    }

    return shadows.length ? shadows.join(', ') : 'none';
}

function buildBubbleShadow(layout = {}) {
    if (!layout.bubbleColor || layout.bubbleColor === 'transparent') return 'none';
    return `0 10px 20px ${layout.bubbleColor}55`;
}

function buildVisualShadow(layout = {}) {
    const shadows = [];
    const shadowIntensity = clamp(Number(layout.shadowIntensity ?? 45), 0, 100);
    const neonIntensity = clamp(Number(layout.neonIntensity ?? 55), 0, 100);

    if (layout.shadow) {
        const color = layout.shadowColor || '#0f172a';
        const preset = layout.shadowPreset || 'soft';

        if (preset === 'hard') {
            const distance = Math.round(1 + shadowIntensity / 12);
            shadows.push(`${distance}px ${distance}px 0 ${color}`);
        } else if (preset === 'lifted') {
            const y = Math.round(8 + shadowIntensity / 4);
            const blur = Math.round(10 + shadowIntensity / 2);
            shadows.push(`0 ${y}px ${blur}px ${color}66`);
        } else {
            const y = Math.round(4 + shadowIntensity / 6);
            const blur = Math.round(8 + shadowIntensity / 2);
            shadows.push(`0 ${y}px ${blur}px ${color}66`);
        }
    }

    if (layout.neonColor) {
        const blurSoft = Math.round(4 + neonIntensity / 6);
        const blurStrong = Math.round(12 + neonIntensity / 2);
        shadows.push(`0 0 ${blurSoft}px ${layout.neonColor}`, `0 0 ${blurStrong}px ${layout.neonColor}`);
    }

    if (layout.bubbleColor && layout.bubbleColor !== 'transparent') {
        shadows.push(`0 10px 20px ${layout.bubbleColor}55`);
    }

    return shadows.length ? shadows.join(', ') : 'none';
}

function elementBoxStyle(id) {
    const layout = state.elementLayout[id] ?? {};
    const isText = isTextElement(id);
    const rotation = Number(layout.rotation ?? 0);

    return {
        position: 'absolute',
        left: `${layout.x ?? 0}px`,
        top: `${layout.y ?? 0}px`,
        width: `${layout.w ?? 160}px`,
        height: isText ? 'auto' : `${layout.h ?? 140}px`,
        zIndex: `${layout.zIndex ?? 1}`,
        transform: `rotate(${rotation}deg)`,
        transformOrigin: 'center center',
    };
}

function elementContentStyle(id) {
    const layout = state.elementLayout[id] ?? {};
    const elementType = state.customElements?.[id]?.type ?? (baseTextElementIds.has(id) ? 'text' : null);

    if (elementType !== 'text') {
        return {
            opacity: `${(layout.opacity ?? 100) / 100}`,
            width: '100%',
            height: '100%',
        };
    }

    const hasBackground = layout.backgroundColor && layout.backgroundColor !== 'transparent';
    const backgroundOpacity = clamp(Number(layout.backgroundOpacity ?? 70), 0, 100);
    const backgroundExpand = clamp(Number(layout.backgroundPadding ?? 5), 0, 100);
    const backgroundAlphaHex = Math.round((backgroundOpacity / 100) * 255).toString(16).padStart(2, '0');
    const resolvedBackground = hasBackground && /^#[\da-f]{6}$/i.test(layout.backgroundColor)
        ? `${layout.backgroundColor}${backgroundAlphaHex}`
        : (hasBackground ? layout.backgroundColor : 'transparent');

    return {
        opacity: `${(layout.opacity ?? 100) / 100}`,
        backgroundColor: resolvedBackground,
        borderRadius: hasBackground ? `${Math.round(clamp(Number(layout.backgroundRoundness ?? 50), 0, 100) * 0.48)}px` : '0',
        padding: hasBackground ? `${backgroundExpand}px` : '0',
        margin: hasBackground ? `-${backgroundExpand}px` : '0',
        boxSizing: 'border-box',
        textAlign: 'left',
        textIndent: '0',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        color: undefined,
        textShadow: 'none',
        WebkitTextStroke: '0',
        boxShadow: buildBubbleShadow(layout),
    };
}

function richEditorContainerStyle(id) {
    const layout = state.elementLayout[id] ?? {};
    return {
        opacity: `${(layout.opacity ?? 100) / 100}`,
    };
}

function paragraphContentStyle(id, index) {
    const layout = state.elementLayout[id] ?? {};
    const paragraphStyle = getParagraphStyleForElement(id, index);
    const baseColor = paragraphStyle.color ?? layout.color ?? '#ffffff';
    const isNeon = layout.textEffectMode === 'neon' && !layout.hollowText;
    const displayColor = layout.hollowText
        ? 'transparent'
        : (isNeon ? '#ffffff' : baseColor);

    return {
        margin: '0',
        padding: '0',
        boxSizing: 'border-box',
        textIndent: '0',
        display: 'block',
        fontSize: `${paragraphStyle.fontSize}px`,
        color: displayColor,
        WebkitTextFillColor: layout.hollowText ? 'transparent' : undefined,
        fontFamily: paragraphStyle.fontFamily,
        fontStyle: paragraphStyle.italic ? 'italic' : 'normal',
        fontWeight: paragraphStyle.fontWeight === 'bold' ? '700' : '500',
        textAlign: paragraphStyle.textAlign,
        textTransform: paragraphStyle.uppercase ? 'uppercase' : 'none',
        letterSpacing: `${paragraphStyle.letterSpacing}px`,
        lineHeight: `${paragraphStyle.lineHeight}`,
        textShadow: buildTextShadow(layout, baseColor),
        WebkitTextStroke: layout.border && layout.hollowText ? `${layout.contourWidth || 1}px ${baseColor}` : '0',
        whiteSpace: 'pre-wrap',
    };
}

function shapeStyleFromKind(shapeKind, base) {
    if (shapeKind === 'circle' || shapeKind === 'ellipse') {
        return { ...base, borderRadius: '9999px' };
    }
    if (shapeKind === 'frame-rounded') {
        return {
            ...base,
            borderRadius: '22px',
            background: 'transparent',
            border: base.border === '0' ? '8px solid currentColor' : base.border,
        };
    }
    if (shapeKind === 'rectangle-outline') {
        return { ...base, borderRadius: '0' };
    }
    if (shapeKind === 'rectangle') {
        return { ...base, borderRadius: '10px' };
    }
    if (shapeKind === 'square') {
        return { ...base, borderRadius: '8px' };
    }

    const clipPath = SHAPE_CLIP_PATHS[shapeKind];
    if (clipPath) {
        return { ...base, clipPath, border: '0' };
    }

    return { ...base, borderRadius: '8px' };
}

function shapeStyle(item) {
    const layout = state.elementLayout[item.id] ?? {};
    const fill = layout.fillMode === 'gradient'
        ? `linear-gradient(${layout.gradientAngle || 135}deg, ${layout.gradientStart || '#0ea5e9'}, ${layout.gradientEnd || '#8b5cf6'})`
        : (layout.backgroundColor && layout.backgroundColor !== 'transparent' ? layout.backgroundColor : '#ffffff');

    const base = {
        width: '100%',
        height: '100%',
        background: fill,
        boxShadow: buildVisualShadow(layout),
        border: layout.border
            ? `${layout.contourWidth || 1}px solid ${layout.contourColor || '#ffffff'}`
            : '0',
    };

    return shapeStyleFromKind(item.shapeKind, base);
}

function imageFrameStyle(id) {
    const layout = state.elementLayout[id] ?? {};

    return {
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        borderRadius: '12px',
        backgroundColor: layout.backgroundColor && layout.backgroundColor !== 'transparent' ? layout.backgroundColor : 'rgba(255,255,255,0.2)',
        border: layout.border
            ? `${layout.contourWidth || 1}px solid ${layout.contourColor || '#ffffff'}`
            : '1px solid rgba(255,255,255,0.4)',
        boxShadow: buildVisualShadow(layout),
    };
}

function imageTintOverlayStyle(id) {
    const layout = state.elementLayout[id] ?? {};
    const tintStrength = clamp(Number(layout.imageTintStrength ?? 0), 0, 100);

    return {
        position: 'absolute',
        inset: '0',
        backgroundColor: layout.imageTintColor || '#0f172a',
        opacity: `${tintStrength / 100}`,
        mixBlendMode: 'multiply',
        pointerEvents: 'none',
    };
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
                                <div :style="shapeStyle(item)"></div>
                            </template>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    </DesignerLayout>
</template>
