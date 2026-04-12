<script setup>
import { Icon } from '@iconify/vue';
import DesignerLayout from '../../Layouts/DesignerLayout.vue';
import StepFooter from '../../Components/designer/StepFooter.vue';
import RichTextEditor from '../../Components/designer/RichTextEditor.vue';
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useDesignerState } from '../../composables/useDesignerState';

defineProps({ currentStep: String, steps: Array, navigation: Object });
const state = useDesignerState();
if (!state.customElements) {
  state.customElements = {};
}
if (!state.userUploadedImages) {
  state.userUploadedImages = [];
}
const canvasRef = ref(null);
const imageInputRef = ref(null);
const imageUrlInput = ref('');
const imagePanelOpen = ref(false);
const imagePanelTab = ref('insert');
const shapePanelOpen = ref(false);
const textPanelOpen = ref(false);
const shapeCategoryFilter = ref('all');
const elementMeasurements = reactive({});
const elementObservers = new Map();
const richEditorRefs = ref({});
const editingElementId = ref(null);
const editingBoxHeight = ref(null);
const selectedParagraphIndex = ref(0);
const paragraphSelection = reactive({ start: 0, end: 0, active: false });
const activePropertyPanel = ref(null);
const toolbarPosition = reactive({ x: 16, y: 16 });
const toolbarDrag = reactive({ active: false, pointerId: null, startX: 0, startY: 0, originX: 0, originY: 0 });
let longPressTimer = null;
const drag = reactive({
    active: false,
    mode: 'move',
    pointerId: null,
    elementId: null,
    handle: null,
    offsetX: 0,
    offsetY: 0,
    startClientX: 0,
    startClientY: 0,
    startX: 0,
    startY: 0,
    startW: 0,
    startH: 0,
    startRotation: 0,
    startAngle: 0,
    centerX: 0,
    centerY: 0,
    lastClientX: 0,
    lastClientY: 0,
    startFontSize: 0,
    startParagraphStyles: [],
});
const touchIntent = reactive({
    pointerId: null,
    startX: 0,
    startY: 0,
});

const colorOptions = [
    '#ffffff', '#f8fafc', '#111827', '#0f172a', '#7c3aed', '#8b5cf6', '#6366f1', '#3b82f6',
    '#0ea5e9', '#06b6d4', '#14b8a6', '#10b981', '#22c55e', '#84cc16', '#eab308', '#f59e0b',
    '#f97316', '#ef4444', '#f43f5e', '#ec4899', '#d946ef', '#c4b5fd', '#f9a8d4', '#67e8f9', '#fde68a',
];
const backgroundOptions = [
    'transparent', '#ffffff', '#f8fafc', '#e2e8f0', '#111827', '#0f172a', '#7c3aed', '#8b5cf6',
    '#0ea5e9', '#14b8a6', '#22c55e', '#f59e0b', '#f43f5e', '#fef3c7', '#fecdd3', '#ddd6fe',
];
const shapeGradientOptions = [
  { id: 'g1', start: '#0ea5e9', end: '#8b5cf6' },
  { id: 'g2', start: '#22c55e', end: '#0ea5e9' },
  { id: 'g3', start: '#f59e0b', end: '#ef4444' },
  { id: 'g4', start: '#f43f5e', end: '#8b5cf6' },
  { id: 'g5', start: '#14b8a6', end: '#22c55e' },
  { id: 'g6', start: '#111827', end: '#6366f1' },
  { id: 'g7', start: '#67e8f9', end: '#7c3aed' },
  { id: 'g8', start: '#fde68a', end: '#f43f5e' },
];
const shapeGradientDirections = [
  { value: 0, label: 'Arriba → abajo', icon: 'ph:arrow-down' },
  { value: 90, label: 'Izquierda → derecha', icon: 'ph:arrow-right' },
  { value: 135, label: 'Diagonal ↘', icon: 'ph:arrow-down-right' },
  { value: 45, label: 'Diagonal ↗', icon: 'ph:arrow-up-right' },
  { value: 180, label: 'Abajo → arriba', icon: 'ph:arrow-up' },
  { value: 270, label: 'Derecha → izquierda', icon: 'ph:arrow-left' },
];
const fontOptions = [
    { label: 'Poppins', family: 'Poppins, sans-serif' },
    { label: 'Montserrat', family: 'Montserrat, sans-serif' },
    { label: 'Raleway', family: 'Raleway, sans-serif' },
    { label: 'Playfair Display', family: '"Playfair Display", serif' },
    { label: 'Pacifico', family: 'Pacifico, cursive' },
    { label: 'Work Sans', family: '"Work Sans", sans-serif' },
    { label: 'Manrope', family: 'Manrope, sans-serif' },
    { label: 'Rubik', family: 'Rubik, sans-serif' },
    { label: 'Quicksand', family: 'Quicksand, sans-serif' },
    { label: 'Ubuntu', family: 'Ubuntu, sans-serif' },
    { label: 'Oswald', family: 'Oswald, sans-serif' },
    { label: 'Nunito', family: 'Nunito, sans-serif' },
    { label: 'Inter', family: 'Inter, sans-serif' },
    { label: 'Lobster', family: 'Lobster, cursive' },
    { label: 'Bebas Neue', family: '"Bebas Neue", sans-serif' },
    { label: 'Anton', family: 'Anton, sans-serif' },
    { label: 'Source Sans 3', family: '"Source Sans 3", sans-serif' },
    { label: 'Merriweather', family: 'Merriweather, serif' },
    { label: 'Roboto Slab', family: '"Roboto Slab", serif' },
    { label: 'Libre Baskerville', family: '"Libre Baskerville", serif' },
    { label: 'Caveat', family: 'Caveat, cursive' },
];
const textPropertyTabs = [
    { id: 'typography', label: 'Fuente' , class: 'order-first'},
    { id: 'color', label: 'A', labelClass:'border-b-5 border-blue-500 text-xl',class: '' },
    { id: 'opacity', icon: 'carbon:opacity', class: 'order-last' },
    { id: 'effects', label: 'Efectos', class: 'order-last' },
    { id: 'arrange', label: 'Posición' , class: 'order-last'},
];
const visualPropertyTabs = [
  { id: 'color', icon: 'mdi:palette-outline', label: 'Color', class: 'order-first' },
  { id: 'opacity', icon: 'carbon:opacity', class: 'order-last' },
  { id: 'effects', label: 'Efectos', class: 'order-last' },
  { id: 'arrange', label: 'Posición', class: 'order-last' },
];
const backgroundPropertyTabs = [
  { id: 'color', icon: 'mdi:palette-outline', label: 'Color', class: 'order-first' },
];

const baseTextElementIds = new Set(['title', 'subtitle', 'meta', 'contact', 'extra']);
const textPresets = [
  {
    id: 'heading',
    label: 'Título',
    preview: 'Agrega un titulo',
    fontSize: 52,
    fontWeight: 'bold',
    lineHeight: 1,
    width: 320,
  },
  {
    id: 'medium',
    label: 'Subtítulo',
    preview: 'Agrega un subtitulo',
    fontSize: 28,
    fontWeight: 'bold',
    lineHeight: 1.2,
    width: 300,
  },
  {
    id: 'normal',
    label: 'Texto normal',
    preview: 'Escribe tu texto aqui',
    fontSize: 18,
    fontWeight: 'regular',
    lineHeight: 1.4,
    width: 280,
  },
];
const shapeCategories = [
  {
    id: 'basicas',
    label: 'Básicas',
    shapes: [
      { id: 'square', label: 'Cuadrado' },
      { id: 'rectangle', label: 'Rectángulo' },
      { id: 'circle', label: 'Círculo' },
      { id: 'ellipse', label: 'Elipse' },
      { id: 'diamond', label: 'Rombo' },
      { id: 'parallelogram', label: 'Paralelogramo' },
      { id: 'trapezoid', label: 'Trapecio' },
      { id: 'trapezoid-inv', label: 'Trapecio inv.' },
    ],
  },
  {
    id: 'poligonos',
    label: 'Polígonos',
    shapes: [
      { id: 'triangle-up', label: 'Triángulo' },
      { id: 'triangle-down', label: 'Triángulo inv.' },
      { id: 'triangle-right', label: 'Triángulo der.' },
      { id: 'triangle-left', label: 'Triángulo izq.' },
      { id: 'pentagon', label: 'Pentágono' },
      { id: 'hexagon', label: 'Hexágono' },
      { id: 'octagon', label: 'Octágono' },
    ],
  },
  {
    id: 'estrellas',
    label: 'Estrellas',
    shapes: [
      { id: 'star-5', label: 'Estrella 5' },
      { id: 'star-4', label: 'Estrella 4' },
      { id: 'star-6', label: 'Estrella 6' },
      { id: 'star-burst', label: 'Destello' },
    ],
  },
  {
    id: 'flechas',
    label: 'Flechas',
    shapes: [
      { id: 'arrow-right', label: 'Flecha →' },
      { id: 'arrow-left', label: 'Flecha ←' },
      { id: 'arrow-up', label: 'Flecha ↑' },
      { id: 'arrow-down', label: 'Flecha ↓' },
      { id: 'arrow-double-h', label: 'Doble H' },
      { id: 'arrow-double-v', label: 'Doble V' },
      { id: 'chevron-right', label: 'Chevron →' },
      { id: 'chevron-left', label: 'Chevron ←' },
    ],
  },
  {
    id: 'especiales',
    label: 'Especiales',
    shapes: [
      { id: 'cross', label: 'Cruz' },
      { id: 'x-mark', label: 'Aspa' },
      { id: 'heart', label: 'Corazón' },
      { id: 'badge', label: 'Escudo' },
      { id: 'ribbon', label: 'Cinta' },
      { id: 'frame', label: 'Marco' },
      { id: 'callout', label: 'Bocadillo' },
    ],
  },
];
// Lookup plano de todas las figuras
const shapePresets = shapeCategories.flatMap((cat) => cat.shapes.map((s) => ({ ...s, category: cat.id })));

const SHAPE_CLIP_PATHS = {
  diamond:           'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)',
  parallelogram:     'polygon(20% 0%, 100% 0%, 80% 100%, 0% 100%)',
  trapezoid:         'polygon(15% 0%, 85% 0%, 100% 100%, 0% 100%)',
  'trapezoid-inv':   'polygon(0% 0%, 100% 0%, 85% 100%, 15% 100%)',
  'triangle-up':     'polygon(50% 0%, 100% 100%, 0% 100%)',
  'triangle-down':   'polygon(0% 0%, 100% 0%, 50% 100%)',
  'triangle-right':  'polygon(0% 0%, 100% 50%, 0% 100%)',
  'triangle-left':   'polygon(100% 0%, 0% 50%, 100% 100%)',
  pentagon:          'polygon(50% 0%, 100% 38%, 82% 100%, 18% 100%, 0% 38%)',
  hexagon:           'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)',
  octagon:           'polygon(30% 0%, 70% 0%, 100% 30%, 100% 70%, 70% 100%, 30% 100%, 0% 70%, 0% 30%)',
  'star-5':          'polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)',
  'star-4':          'polygon(50% 0%, 60% 40%, 100% 50%, 60% 60%, 50% 100%, 40% 60%, 0% 50%, 40% 40%)',
  'star-6':          'polygon(50% 0%, 58% 17%, 79% 7%, 71% 26%, 93% 25%, 82% 43%, 100% 50%, 82% 57%, 93% 75%, 71% 74%, 79% 93%, 58% 83%, 50% 100%, 42% 83%, 21% 93%, 29% 74%, 7% 75%, 18% 57%, 0% 50%, 18% 43%, 7% 25%, 29% 26%, 21% 7%, 42% 17%)',
  'star-burst':      'polygon(50% 0%, 54% 35%, 65% 9%, 60% 43%, 79% 21%, 65% 50%, 91% 38%, 67% 57%, 97% 57%, 68% 65%, 93% 75%, 64% 71%, 79% 93%, 57% 79%, 58% 100%, 50% 80%, 42% 100%, 43% 79%, 21% 93%, 36% 71%, 7% 75%, 32% 65%, 3% 57%, 33% 57%, 9% 38%, 35% 50%, 21% 21%, 40% 43%, 35% 9%, 46% 35%)',
  'arrow-right':     'polygon(0% 25%, 60% 25%, 60% 0%, 100% 50%, 60% 100%, 60% 75%, 0% 75%)',
  'arrow-left':      'polygon(40% 0%, 40% 25%, 100% 25%, 100% 75%, 40% 75%, 40% 100%, 0% 50%)',
  'arrow-up':        'polygon(25% 40%, 0% 40%, 50% 0%, 100% 40%, 75% 40%, 75% 100%, 25% 100%)',
  'arrow-down':      'polygon(25% 0%, 75% 0%, 75% 60%, 100% 60%, 50% 100%, 0% 60%, 25% 60%)',
  'arrow-double-h':  'polygon(0% 50%, 20% 0%, 20% 35%, 80% 35%, 80% 0%, 100% 50%, 80% 100%, 80% 65%, 20% 65%, 20% 100%)',
  'arrow-double-v':  'polygon(50% 0%, 100% 20%, 65% 20%, 65% 80%, 100% 80%, 50% 100%, 0% 80%, 35% 80%, 35% 20%, 0% 20%)',
  'chevron-right':   'polygon(0% 0%, 70% 0%, 100% 50%, 70% 100%, 0% 100%, 30% 50%)',
  'chevron-left':    'polygon(30% 0%, 100% 0%, 70% 50%, 100% 100%, 30% 100%, 0% 50%)',
  cross:             'polygon(33% 0%, 67% 0%, 67% 33%, 100% 33%, 100% 67%, 67% 67%, 67% 100%, 33% 100%, 33% 67%, 0% 67%, 0% 33%, 33% 33%)',
  'x-mark':          'polygon(10% 0%, 50% 40%, 90% 0%, 100% 10%, 60% 50%, 100% 90%, 90% 100%, 50% 60%, 10% 100%, 0% 90%, 40% 50%, 0% 10%)',
  heart:             'polygon(50% 30%, 20% 5%, 0% 25%, 0% 50%, 50% 95%, 100% 50%, 100% 25%, 80% 5%)',
  badge:             'polygon(50% 0%, 63% 12%, 79% 8%, 83% 25%, 98% 33%, 91% 50%, 98% 67%, 83% 75%, 79% 92%, 63% 88%, 50% 100%, 37% 88%, 21% 92%, 17% 75%, 2% 67%, 9% 50%, 2% 33%, 17% 25%, 21% 8%, 37% 12%)',
  ribbon:            'polygon(0% 0%, 100% 0%, 100% 55%, 80% 55%, 100% 100%, 50% 73%, 0% 100%, 20% 55%, 0% 55%)',
  frame:             'polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%, 12% 12%, 12% 88%, 88% 88%, 88% 12%, 12% 12%)',
  callout:           'polygon(0% 0%, 100% 0%, 100% 75%, 55% 75%, 50% 100%, 45% 75%, 0% 75%)',
};
const imagePanelTabs = [
  { id: 'insert', label: 'Insertar' },
  { id: 'library', label: 'Libreria' },
  { id: 'uploads', label: 'Subidas' },
];
const imageLibrary = [
  { id: 'lib-1', src: 'https://picsum.photos/seed/tseyor1/900/600', label: 'Biblioteca 1' },
  { id: 'lib-2', src: 'https://picsum.photos/seed/tseyor2/900/600', label: 'Biblioteca 2' },
  { id: 'lib-3', src: 'https://picsum.photos/seed/tseyor3/900/600', label: 'Biblioteca 3' },
  { id: 'lib-4', src: 'https://picsum.photos/seed/tseyor4/900/600', label: 'Biblioteca 4' },
  { id: 'lib-5', src: 'https://picsum.photos/seed/tseyor5/900/600', label: 'Biblioteca 5' },
  { id: 'lib-6', src: 'https://picsum.photos/seed/tseyor6/900/600', label: 'Biblioteca 6' },
];

const metaLine = computed(() => [state.content.date, state.content.time].filter(Boolean).join(' · '));
const editorElements = computed(() => {
  const baseTextElements = [
    { id: 'title', type: 'text', label: 'Titulo', text: state.content.title },
    { id: 'subtitle', type: 'text', label: 'Subtitulo', text: state.content.subtitle },
    { id: 'meta', type: 'text', label: 'Fecha / hora', text: metaLine.value },
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
const selectedElement = computed(() => state.elementLayout[state.selectedElementId]);
const hasSelection = computed(() => Boolean(state.selectedElementId && selectedElement.value));
const activeElementLabel = computed(() => {
  if (state.selectedElementId === 'background') return 'Fondo';
  return editorElements.value.find((item) => item.id === state.selectedElementId)?.label ?? 'Elemento';
});
const selectedElementType = computed(() => editorElements.value.find((item) => item.id === state.selectedElementId)?.type ?? null);
const hasTextSelection = computed(() => hasSelection.value && selectedElementType.value === 'text');
const selectedPropertyTabs = computed(() => {
  if (!hasSelection.value) return textPropertyTabs;
  if (state.selectedElementId === 'background') return backgroundPropertyTabs;
  return selectedElementType.value === 'text' ? textPropertyTabs : visualPropertyTabs;
});
const activePropertyTitle = computed(() => selectedPropertyTabs.value.find((tab) => tab.id === activePropertyPanel.value)?.label ?? 'Propiedades');
const orderedLayerIds = computed(() => Object.keys(state.elementLayout).sort((a, b) => {
    const zA = state.elementLayout[a]?.zIndex ?? 0;
    const zB = state.elementLayout[b]?.zIndex ?? 0;

    if (zA === zB) {
        return a.localeCompare(b);
    }

    return zA - zB;
}));

watch([selectedElementType, hasSelection], () => {
  if (!hasSelection.value) {
    activePropertyPanel.value = null;
    return;
  }

  const availableTabIds = selectedPropertyTabs.value.map((tab) => tab.id);
  if (activePropertyPanel.value && !availableTabIds.includes(activePropertyPanel.value)) {
    activePropertyPanel.value = null;
  }
}, { immediate: true });

const paragraphStyleFields = new Set([
    'fontSize',
    'color',
    'fontFamily',
    'fontWeight',
    'italic',
    'uppercase',
    'textAlign',
    'letterSpacing',
    'lineHeight',
]);

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
const getParagraphs = (text) => String(text ?? '').replace(/\r\n/g, '\n').split('\n');
const buildParagraphStyle = (layout, fallback = {}) => ({
    fontSize: fallback.fontSize ?? layout.fontSize ?? 16,
    color: fallback.color ?? layout.color ?? '#ffffff',
    fontFamily: fallback.fontFamily ?? layout.fontFamily ?? 'Inter, sans-serif',
    fontWeight: fallback.fontWeight ?? layout.fontWeight ?? 'regular',
    italic: fallback.italic ?? layout.italic ?? false,
    uppercase: fallback.uppercase ?? layout.uppercase ?? false,
    textAlign: fallback.textAlign ?? layout.textAlign ?? 'left',
    letterSpacing: fallback.letterSpacing ?? layout.letterSpacing ?? 0,
    lineHeight: fallback.lineHeight ?? layout.lineHeight ?? 1.3,
});
const ensureParagraphStyles = (layout, text = '') => {
    const paragraphs = getParagraphs(text);

    if (!Array.isArray(layout.paragraphStyles)) {
        layout.paragraphStyles = [];
    }

    paragraphs.forEach((_, index) => {
        const current = layout.paragraphStyles[index];
        const previous = layout.paragraphStyles[index - 1];
        const normalized = buildParagraphStyle(layout, current ?? previous ?? {});

        if (!current) {
            layout.paragraphStyles[index] = normalized;
            return;
        }

        Object.entries(normalized).forEach(([key, value]) => {
            if (current[key] === undefined) {
                current[key] = value;
            }
        });
    });

    if (layout.paragraphStyles.length > paragraphs.length) {
        layout.paragraphStyles.splice(paragraphs.length);
    }

    return layout.paragraphStyles;
};
const getTextSourceForSelectedElement = () => {
    if (!state.selectedElementId) return '';
    return getElementText(state.selectedElementId);
};
const getParagraphStyleForElement = (id, index = 0, text = null) => {
    const layout = state.elementLayout[id];
    if (!layout) return null;

    const sourceText = text ?? getElementText(id);
    const styles = ensureParagraphStyles(layout, sourceText);

    return styles[clamp(index, 0, Math.max(0, styles.length - 1))] ?? buildParagraphStyle(layout);
};
const applyParagraphStyleField = (field, value) => {
    if (!selectedElement.value || !state.selectedElementId) return;

    const editorRef = richEditorRefs.value[state.selectedElementId];
    if (!editorRef) return;

    if (editingElementId.value === state.selectedElementId) {
        editorRef.applyStyle(field, value);
    } else {
        editorRef.applyStyleAll(field, value);
    }
};
const selectedTextStyle = computed(() => {
    if (!state.selectedElementId) return {};

  const fallbackStyle = selectedElement.value
    ? (getParagraphStyleForElement(
      state.selectedElementId,
      selectedParagraphIndex.value,
      getTextSourceForSelectedElement(),
    ) ?? buildParagraphStyle(selectedElement.value))
    : {};

    const editorRef = richEditorRefs.value[state.selectedElementId];
  const activeAttrs = editorRef?.getActiveAttrs() ?? {};
  const mergedAttrs = Object.fromEntries(
    Object.entries(activeAttrs).filter(([, value]) => value !== null && value !== undefined)
  );
  const attrs = buildParagraphStyle(selectedElement.value ?? {}, {
    ...fallbackStyle,
    ...mergedAttrs,
  });

  return new Proxy(attrs, {
        get(target, key) {
            return target[key];
        },
        set(_, key, value) {
            if (typeof key !== 'string') return true;
            if (paragraphStyleFields.has(key)) {
                applyParagraphStyleField(key, value);
            }
            return true;
        },
    });
});
const paragraphCount = computed(() => {
    if (!selectedElement.value || !state.selectedElementId) return 0;
    return selectedElement.value.paragraphStyles?.length
        || getParagraphs(getElementText(state.selectedElementId)).length;
});
const activeParagraphLabel = computed(() => {
    if (!paragraphCount.value) return 'Párrafo 1 de 1';

    if (editingElementId.value !== state.selectedElementId) {
        return paragraphCount.value === 1 ? 'Todo el texto (1 párrafo)' : `Todo el texto (${paragraphCount.value} párrafos)`;
    }

    const n = paragraphCount.value;
    const first = paragraphSelection.start + 1;
    const last = paragraphSelection.end + 1;

    if (!paragraphSelection.active || first === last) {
        return `Párrafo ${selectedParagraphIndex.value + 1} de ${n}`;
    }

    return `Párrafos ${Math.min(first, last)}-${Math.max(first, last)} de ${n}`;
});

const normalizePickerColor = (value, fallback = '#ffffff') => {
    if (typeof value !== 'string') return fallback;

    const trimmed = value.trim();

    if (/^#[\da-f]{6}$/i.test(trimmed)) return trimmed;
    if (/^#[\da-f]{3}$/i.test(trimmed)) {
        return `#${trimmed[1]}${trimmed[1]}${trimmed[2]}${trimmed[2]}${trimmed[3]}${trimmed[3]}`;
    }

    return fallback;
};
const setSelectedColor = (field, value) => {
    if (paragraphStyleFields.has(field)) {
        applyParagraphStyleField(field, value);
        return;
    }

    if (!selectedElement.value) return;
    selectedElement.value[field] = value;
};
  const applyShapeGradientPreset = (start, end) => {
    if (!selectedElement.value || selectedElementType.value !== 'shape') return;
    selectedElement.value.fillMode = 'gradient';
    selectedElement.value.gradientStart = start;
    selectedElement.value.gradientEnd = end;
  };
  const swapShapeGradientStops = () => {
    if (!selectedElement.value || selectedElementType.value !== 'shape') return;
    const start = selectedElement.value.gradientStart || '#0ea5e9';
    selectedElement.value.gradientStart = selectedElement.value.gradientEnd || '#8b5cf6';
    selectedElement.value.gradientEnd = start;
  };
const clampToolbar = () => {
    toolbarPosition.x = clamp(toolbarPosition.x, 8, 700);
    toolbarPosition.y = clamp(toolbarPosition.y, 8, 180);
};

const buildTextShadow = (layout) => {
    const shadows = [];

    if (layout.shadow) {
        const color = layout.shadowColor || '#0f172a';
        const preset = layout.shadowPreset || 'soft';

        if (preset === 'hard') shadows.push(`4px 4px 0 ${color}`);
        else if (preset === 'lifted') shadows.push(`0 14px 24px ${color}`);
        else shadows.push(`0 10px 24px ${color}`);
    }

    if (layout.neonColor) {
        shadows.push(`0 0 8px ${layout.neonColor}`, `0 0 18px ${layout.neonColor}`);
    }

    return shadows.length ? shadows.join(', ') : 'none';
};

const buildBubbleShadow = (layout) => {
    if (!layout.bubbleColor || layout.bubbleColor === 'transparent') return 'none';
    return `0 10px 20px ${layout.bubbleColor}55`;
};

const buildVisualShadow = (layout) => {
  const shadows = [];

  if (layout.shadow) {
    const color = layout.shadowColor || '#0f172a';
    const preset = layout.shadowPreset || 'soft';

    if (preset === 'hard') shadows.push(`4px 4px 0 ${color}`);
    else if (preset === 'lifted') shadows.push(`0 14px 24px ${color}66`);
    else shadows.push(`0 10px 24px ${color}66`);
  }

  if (layout.neonColor) {
    shadows.push(`0 0 8px ${layout.neonColor}`, `0 0 18px ${layout.neonColor}`);
  }

  if (layout.bubbleColor && layout.bubbleColor !== 'transparent') {
    shadows.push(`0 10px 20px ${layout.bubbleColor}55`);
  }

  return shadows.length ? shadows.join(', ') : 'none';
};

const isTextElement = (id) => {
  if (baseTextElementIds.has(id)) return true;
  return state.customElements?.[id]?.type === 'text';
};

const getMaxZIndex = () => Object.values(state.elementLayout).reduce((max, layout) => Math.max(max, layout?.zIndex ?? 0), 0);
const getCanvasBounds = () => ({
  width: canvasRef.value?.clientWidth ?? 360,
  height: canvasRef.value?.clientHeight ?? 620,
});
const createElementId = (prefix) => {
  const suffix = Math.random().toString(36).slice(2, 9);
  return `${prefix}-${Date.now().toString(36)}-${suffix}`;
};
const buildDefaultLayout = (overrides = {}) => ({
  x: 24,
  y: 40,
  w: 280,
  rotation: 0,
  zIndex: getMaxZIndex() + 10,
  fontSize: 18,
  color: '#ffffff',
  shadow: false,
  border: false,
  fontFamily: 'Inter, sans-serif',
  opacity: 100,
  fontWeight: 'regular',
  italic: false,
  uppercase: false,
  textAlign: 'left',
  letterSpacing: 0,
  lineHeight: 1.4,
  shadowPreset: 'soft',
  shadowColor: '#0f172a',
  contourWidth: 0,
  contourColor: '#ffffff',
  neonColor: '',
  bubbleColor: 'transparent',
  backgroundColor: 'transparent',
  fillMode: 'solid',
  gradientStart: '#0ea5e9',
  gradientEnd: '#8b5cf6',
  gradientAngle: 135,
  imageTintColor: '#0f172a',
  imageTintStrength: 0,
  ...overrides,
});
const placeInsideCanvas = (layout) => {
  const bounds = getCanvasBounds();
  const width = Math.max(40, layout.w ?? 0);
  const height = Math.max(40, layout.h ?? 50);

  layout.x = Math.round(clamp(layout.x ?? 0, 0, Math.max(0, bounds.width - width - 8)));
  layout.y = Math.round(clamp(layout.y ?? 0, 18, Math.max(18, bounds.height - height - 8)));
};

const addTextElement = (presetId) => {
  const preset = textPresets.find((item) => item.id === presetId);
  if (!preset) return;

  const id = createElementId('text');
  const layout = buildDefaultLayout({
    w: preset.width,
    fontSize: preset.fontSize,
    fontWeight: preset.fontWeight,
    lineHeight: preset.lineHeight,
    color: '#ffffff',
    shadow: presetId === 'heading',
    x: 28,
    y: 90,
    paragraphStyles: [{
      fontSize: preset.fontSize,
      color: '#ffffff',
      fontFamily: 'Poppins, sans-serif',
      fontWeight: preset.fontWeight,
      italic: false,
      uppercase: false,
      textAlign: 'left',
      letterSpacing: 0,
      lineHeight: preset.lineHeight,
    }],
  });

  placeInsideCanvas(layout);
  state.customElements[id] = {
    type: 'text',
    label: preset.label,
    text: preset.preview,
  };
  state.elementLayout[id] = layout;
  state.selectedElementId = id;
};

const openImagePanel = () => {
  imagePanelOpen.value = true;
  imagePanelTab.value = 'insert';
};

const closeImagePanel = () => {
  imagePanelOpen.value = false;
  imageUrlInput.value = '';
};

const openShapePanel = () => {
  shapePanelOpen.value = true;
  shapeCategoryFilter.value = 'all';
};

const closeShapePanel = () => {
  shapePanelOpen.value = false;
};

const openTextPanel = () => {
  textPanelOpen.value = true;
};

const closeTextPanel = () => {
  textPanelOpen.value = false;
};

const addImageElementFromSrc = (src, label = 'Imagen') => {
  if (!src) return;

  const id = createElementId('image');
  const layout = buildDefaultLayout({
    w: 220,
    h: 160,
    x: 36,
    y: 120,
    backgroundColor: '#ffffff',
    color: '#ffffff',
  });

  placeInsideCanvas(layout);
  state.customElements[id] = {
    type: 'image',
    label,
    src,
  };
  state.elementLayout[id] = layout;
  state.selectedElementId = id;
  closeImagePanel();
};

const triggerImagePicker = () => {
  imageInputRef.value?.click();
};

const onImagePicked = (event) => {
  const input = event.target;
  const file = input?.files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = () => {
    const src = typeof reader.result === 'string' ? reader.result : '';
    if (!src) return;

    state.userUploadedImages.unshift({
      id: createElementId('upload'),
      src,
      label: file.name || 'Subida',
    });
    addImageElementFromSrc(src, file.name || 'Imagen');
  };
  reader.readAsDataURL(file);
  input.value = '';
};

const addImageFromUrl = () => {
  const src = imageUrlInput.value.trim();
  if (!src) return;

  state.userUploadedImages.unshift({
    id: createElementId('upload-url'),
    src,
    label: 'URL',
  });
  addImageElementFromSrc(src, 'Imagen URL');
};

const addLibraryImage = (image) => {
  addImageElementFromSrc(image?.src, image?.label || 'Imagen de libreria');
};

const addUploadedImage = (image) => {
  addImageElementFromSrc(image?.src, image?.label || 'Imagen subida');
};

const addShapeElement = (shapeKind) => {
  const shape = shapePresets.find((item) => item.id === shapeKind);
  if (!shape) return;

  const isRectangle = shapeKind === 'rectangle';
  const layout = buildDefaultLayout({
    w: isRectangle ? 220 : 140,
    h: isRectangle ? 120 : 140,
    x: 44,
    y: 150,
    backgroundColor: '#38bdf8',
    opacity: 90,
    shadow: true,
    border: false,
  });
  placeInsideCanvas(layout);

  const id = createElementId('shape');
  state.customElements[id] = {
    type: 'shape',
    label: shape.label,
    shapeKind,
  };
  state.elementLayout[id] = layout;
  state.selectedElementId = id;
};

// Genera estilo CSS para una figura según su shapeKind
const shapeStyleFromKind = (shapeKind, base) => {
  if (shapeKind === 'circle' || shapeKind === 'ellipse') {
    return { ...base, borderRadius: '9999px' };
  }
  if (shapeKind === 'rectangle') {
    return { ...base, borderRadius: '18px' };
  }
  if (shapeKind === 'square') {
    return { ...base, borderRadius: '8px' };
  }
  const clipPath = SHAPE_CLIP_PATHS[shapeKind];
  if (clipPath) {
    return { ...base, clipPath, border: '0' };
  }
  return { ...base, borderRadius: '8px' };
};

const shapeStyle = (item) => {
  const layout = state.elementLayout[item.id];
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
};

const imageFrameStyle = (id) => {
  const layout = state.elementLayout[id];
  if (!layout) return {};

  return {
    backgroundColor: layout.backgroundColor && layout.backgroundColor !== 'transparent' ? layout.backgroundColor : 'rgba(255,255,255,0.2)',
    border: layout.border
      ? `${layout.contourWidth || 1}px solid ${layout.contourColor || '#ffffff'}`
      : '1px solid rgba(255,255,255,0.4)',
    boxShadow: buildVisualShadow(layout),
  };
};

const imageTintOverlayStyle = (id) => {
  const layout = state.elementLayout[id];
  if (!layout) return {};

  const tintStrength = clamp(Number(layout.imageTintStrength ?? 0), 0, 100);

  return {
    backgroundColor: layout.imageTintColor || '#0f172a',
    opacity: `${tintStrength / 100}`,
    mixBlendMode: 'multiply',
  };
};

const elementBoxStyle = (id) => {
    const layout = state.elementLayout[id];
  const isText = isTextElement(id);
  const rotation = Number(layout.rotation ?? 0);

    return {
        left: `${layout.x}px`,
        top: `${layout.y}px`,
        width: `${layout.w}px`,
    height: isText ? 'auto' : `${layout.h ?? 140}px`,
        zIndex: `${layout.zIndex ?? 1}`,
    transform: `rotate(${rotation}deg)`,
    transformOrigin: 'center center',
    };
};

const getEstimatedTextHeight = (layout, text = '') => ensureParagraphStyles(layout, text)
    .reduce((total, style) => total + Math.max((style.fontSize ?? layout.fontSize ?? 16) * (style.lineHeight ?? 1.3), 16), 0);

const selectedOverlayStyle = computed(() => {
    if (!state.selectedElementId) {
        return {};
    }

    const layout = state.elementLayout[state.selectedElementId];
    const text = getElementText(state.selectedElementId);
    const measured = elementMeasurements[state.selectedElementId] ?? null;
    const measuredWidth = measured?.width ?? layout.w;
    const measuredHeight = measured?.height ?? getEstimatedTextHeight(layout, text);
  const rotation = Number(layout.rotation ?? 0);

    return {
        left: `${layout.x}px`,
        top: `${layout.y}px`,
        width: `${measuredWidth}px`,
        height: `${measuredHeight}px`,
        zIndex: '6000',
    transform: `rotate(${rotation}deg)`,
    transformOrigin: 'center center',
    };
});

const updateElementMeasurement = (id, node) => {
    if (!node) return;

    elementMeasurements[id] = {
        width: node.offsetWidth,
        height: node.offsetHeight,
    };
};

const refreshElementObservers = async () => {
    await nextTick();

    elementObservers.forEach((observer) => observer.disconnect());
    elementObservers.clear();

    if (!canvasRef.value) {
        return;
    }

    editorElements.value.forEach((item) => {
        const node = canvasRef.value.querySelector(`[data-editor-id="${item.id}"]`);

        if (!node) {
            delete elementMeasurements[item.id];
            return;
        }

        updateElementMeasurement(item.id, node);

        const observer = new ResizeObserver(() => {
            updateElementMeasurement(item.id, node);
        });

        observer.observe(node);
        elementObservers.set(item.id, observer);
    });
};

const elementContentStyle = (id) => {
    const layout = state.elementLayout[id];
  const elementType = state.customElements?.[id]?.type ?? (baseTextElementIds.has(id) ? 'text' : null);

  if (elementType !== 'text') {
    return {
      opacity: `${(layout.opacity ?? 100) / 100}`,
    };
  }

    return {
        opacity: `${(layout.opacity ?? 100) / 100}`,
        backgroundColor: layout.backgroundColor && layout.backgroundColor !== 'transparent' ? layout.backgroundColor : 'transparent',
        borderRadius: layout.backgroundColor && layout.backgroundColor !== 'transparent' ? '16px' : '0',
        padding: '0',
        textShadow: buildTextShadow(layout),
        WebkitTextStroke: layout.border ? `${layout.contourWidth || 1}px ${layout.contourColor || '#ffffff'}` : '0',
        boxShadow: buildBubbleShadow(layout),
    };
};

const paragraphContentStyle = (id, index, text = null) => {
    const layout = state.elementLayout[id];
    const paragraphStyle = getParagraphStyleForElement(id, index, text);

    return {
        display: 'block',
        fontSize: `${paragraphStyle?.fontSize ?? layout.fontSize}px`,
        color: paragraphStyle?.color ?? layout.color,
        fontFamily: paragraphStyle?.fontFamily ?? layout.fontFamily ?? 'Inter, sans-serif',
        fontStyle: paragraphStyle?.italic ? 'italic' : 'normal',
        fontWeight: paragraphStyle?.fontWeight === 'bold' ? '700' : '500',
        textAlign: paragraphStyle?.textAlign ?? 'left',
        textTransform: paragraphStyle?.uppercase ? 'uppercase' : 'none',
        letterSpacing: `${paragraphStyle?.letterSpacing ?? 0}px`,
        lineHeight: `${paragraphStyle?.lineHeight ?? 1.3}`,
        textShadow: buildTextShadow(layout),
        WebkitTextStroke: layout.border ? `${layout.contourWidth || 1}px ${layout.contourColor || '#ffffff'}` : '0',
        whiteSpace: 'pre-wrap',
    };
};

const richEditorContainerStyle = (id) => {
    const layout = state.elementLayout[id];
    return {
        opacity: `${(layout.opacity ?? 100) / 100}`,
        minHeight: editingBoxHeight.value
            ? `${editingBoxHeight.value}px`
            : undefined,
        overflow: 'hidden',
    };
};

const setDragDocumentState = (active) => {
    document.documentElement.style.userSelect = active ? 'none' : '';
    document.documentElement.style.touchAction = active ? 'none' : '';
};

const startToolbarDrag = (event) => {
    toolbarDrag.active = true;
    toolbarDrag.pointerId = event.pointerId;
    toolbarDrag.startX = event.clientX;
    toolbarDrag.startY = event.clientY;
    toolbarDrag.originX = toolbarPosition.x;
    toolbarDrag.originY = toolbarPosition.y;
    setDragDocumentState(true);
    event.currentTarget?.setPointerCapture?.(event.pointerId);
    event.preventDefault();
};

const getElementText = (id) => {
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
};

const handleElementClick = (id) => {
    if (editingElementId.value && editingElementId.value !== id) {
        commitTextEdit();
    }

  if (!isTextElement(id)) {
    state.selectedElementId = id;
    return;
  }

    // Patrón clic-para-seleccionar / clic-de-nuevo-para-editar
    // (igual que Figma/Canva: no depende del dblclick del navegador)
    if (state.selectedElementId === id && editingElementId.value !== id) {
        beginTextEdit(id);
        return;
    }

    state.selectedElementId = id;
    selectedParagraphIndex.value = 0;
    paragraphSelection.start = 0;
    paragraphSelection.end = 0;
    paragraphSelection.active = false;
};

const onRichEditorSelectionChange = (id, { paragraphIndex, selectedIndexes }) => {
    if (editingElementId.value !== id) return;

    selectedParagraphIndex.value = clamp(paragraphIndex, 0, Math.max(0, paragraphCount.value - 1));
    paragraphSelection.active = selectedIndexes.length > 1;

    if (paragraphSelection.active) {
        paragraphSelection.start = selectedIndexes[0];
        paragraphSelection.end = selectedIndexes[selectedIndexes.length - 1];
    } else {
        paragraphSelection.start = paragraphIndex;
        paragraphSelection.end = paragraphIndex;
    }
};

const onRichEditorTextUpdate = (id, newText) => {
    if (!state.elementLayout[id]) return;
    switch (id) {
        case 'title':
        case 'subtitle':
        case 'contact':
        case 'extra':
            state.content[id] = newText;
            break;
        case 'meta': {
            const parts = newText.split('\n');
            state.content.date = (parts[0] ?? '').trim();
            state.content.time = (parts[1] ?? '').trim();
            break;
        }
        default:
          if (state.customElements?.[id]?.type === 'text') {
            state.customElements[id].text = newText;
          }
    }
};

const onRichEditorStylesUpdate = (id, newStyles) => {
    const layout = state.elementLayout[id];
    if (!layout) return;
    layout.paragraphStyles = newStyles;
};

const beginTextEdit = async (id) => {
  if (!isTextElement(id)) return;

    state.selectedElementId = id;
    editingBoxHeight.value = elementMeasurements[id]?.height ?? null;
    selectedParagraphIndex.value = 0;
    paragraphSelection.start = 0;
    paragraphSelection.end = 0;
    paragraphSelection.active = false;
    editingElementId.value = id;
    clearLongPress();
    await nextTick();
    richEditorRefs.value[id]?.$el?.querySelector('[contenteditable]')?.focus();
};

const commitTextEdit = () => {
    if (!editingElementId.value) return;

    paragraphSelection.start = selectedParagraphIndex.value;
    paragraphSelection.end = selectedParagraphIndex.value;
    paragraphSelection.active = false;
    editingElementId.value = null;
    editingBoxHeight.value = null;
};

const cancelTextEdit = () => {
    editingElementId.value = null;
    editingBoxHeight.value = null;
    paragraphSelection.start = selectedParagraphIndex.value;
    paragraphSelection.end = selectedParagraphIndex.value;
    paragraphSelection.active = false;
};
const onRichEditorBlur = (id, event) => {
    const nextTarget = event?.relatedTarget ?? null;
    if (nextTarget instanceof Element) {
        // Clic en control de propiedades → mantener edición y re-enfocar
        if (nextTarget.closest('[data-editor-keep-selection="true"]')) {
            // Si el foco va a un input/select/textarea: NO robar el foco de vuelta.
            // Mantenemos editingElementId para que applyStyle sepa en qué párrafo actuar.
            const isFocusableInput = nextTarget.closest('input,select,textarea');
            if (!isFocusableInput) {
              // Botón u otro control no focusable: re-enfocar TipTap
              nextTick(() => {
                if (editingElementId.value === id) {
                  richEditorRefs.value[id]?.$el?.querySelector('[contenteditable]')?.focus();
                }
              });
            }
            // En ambos casos: mantener estado de edición, no deseleccionar
            return;
        }
        // Clic en handle de resize/drag → salir de edición pero mantener selección
        if (nextTarget.closest('[data-editor-control="true"]')) {
            commitTextEdit();
            return;
        }
        // Clic en otro elemento editable → solo salir del modo edición (handleElementClick re-seleccionará)
        if (nextTarget.closest('[data-editor-element="true"]')) {
            commitTextEdit();
            return;
        }
    }
    // Clic en fondo del canvas, fuera del canvas o en cualquier otro lugar → salir Y deseleccionar
    clearSelection();
};
const onRichEditorKeydown = (event) => {
    if (event.key === 'Escape') return cancelTextEdit();
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        commitTextEdit();
    }
};

const clearLongPress = () => {
    if (longPressTimer) {
        clearTimeout(longPressTimer);
        longPressTimer = null;
    }
    touchIntent.pointerId = null;
};

const startTouchEditIntent = (event, id) => {
  if (event.pointerType !== 'touch' || drag.active || !isTextElement(id)) return;
    clearLongPress();
    touchIntent.pointerId = event.pointerId;
    touchIntent.startX = event.clientX;
    touchIntent.startY = event.clientY;
    longPressTimer = setTimeout(() => beginTextEdit(id), 450);
};

const startDrag = (event, id) => {
    const canvas = canvasRef.value;
    const layout = state.elementLayout[id];
    if (!canvas || !layout) return;

    state.selectedElementId = id;
    drag.active = true;
    drag.mode = 'move';
    drag.pointerId = event.pointerId;
    drag.elementId = id;
    drag.handle = null;
    drag.startClientX = event.clientX;
    drag.startClientY = event.clientY;
    drag.startX = layout.x;
    drag.startY = layout.y;
    drag.startW = layout.w;
    drag.startH = layout.h ?? 140;
    drag.startFontSize = layout.fontSize;
    clearLongPress();
    setDragDocumentState(true);

    event.currentTarget?.setPointerCapture?.(event.pointerId);
    event.stopPropagation();
    event.preventDefault();
};

const startResize = (event, id, handle) => {
    const layout = state.elementLayout[id];
    if (!layout) return;

    // Si estamos en modo edición, commiteamos antes de redimensionar para evitar
    // inconsistencias entre el estado interno de TipTap y paragraphStyles
    if (editingElementId.value) commitTextEdit();

    state.selectedElementId = id;
    drag.active = true;
    drag.mode = 'resize';
    drag.pointerId = event.pointerId;
    drag.elementId = id;
    drag.handle = handle;
    drag.startClientX = event.clientX;
    drag.startClientY = event.clientY;
    drag.startX = layout.x;
    drag.startY = layout.y;
    drag.startW = layout.w;
    drag.startH = layout.h ?? 140;
    drag.startFontSize = layout.fontSize;
    drag.startParagraphStyles = ensureParagraphStyles(layout, getElementText(id)).map((style) => ({ ...style }));
    clearLongPress();
    setDragDocumentState(true);

    event.currentTarget?.setPointerCapture?.(event.pointerId);
    event.stopPropagation();
    event.preventDefault();
};

  const getPointerAngle = (event, centerX, centerY) => Math.atan2(event.clientY - centerY, event.clientX - centerX) * (180 / Math.PI);

  const startRotate = (event, id) => {
    const layout = state.elementLayout[id];
    const measured = elementMeasurements[id];
    if (!layout) return;

    if (editingElementId.value) commitTextEdit();

    const width = measured?.width ?? layout.w ?? 0;
    const height = measured?.height ?? layout.h ?? 44;
    const centerX = layout.x + (width / 2);
    const centerY = layout.y + (height / 2);

    state.selectedElementId = id;
    drag.active = true;
    drag.mode = 'rotate';
    drag.pointerId = event.pointerId;
    drag.elementId = id;
    drag.handle = null;
    drag.startRotation = Number(layout.rotation ?? 0);
    drag.centerX = centerX;
    drag.centerY = centerY;
    drag.startAngle = getPointerAngle(event, centerX, centerY);
    drag.lastClientX = event.clientX;
    drag.lastClientY = event.clientY;
    clearLongPress();
    setDragDocumentState(true);

    event.currentTarget?.setPointerCapture?.(event.pointerId);
    event.stopPropagation();
    event.preventDefault();
  };

  const resetRotation = (id) => {
    const layout = state.elementLayout[id];
    if (!layout) return;
    layout.rotation = 0;
  };

const moveDrag = (event) => {
    if (toolbarDrag.active && toolbarDrag.pointerId === event.pointerId) {
        toolbarPosition.x = toolbarDrag.originX + (event.clientX - toolbarDrag.startX);
        toolbarPosition.y = toolbarDrag.originY + (event.clientY - toolbarDrag.startY);
        clampToolbar();
        if (event.cancelable) event.preventDefault();
        return;
    }

    if (!drag.active || drag.pointerId !== event.pointerId || !drag.elementId || !canvasRef.value) {
        if (touchIntent.pointerId === event.pointerId) {
            const moved = Math.hypot(event.clientX - touchIntent.startX, event.clientY - touchIntent.startY);
            if (moved > 8) clearLongPress();
        }
        return;
    }

    const rect = canvasRef.value.getBoundingClientRect();
    const layout = state.elementLayout[drag.elementId];
    const isText = isTextElement(drag.elementId);

    if (drag.mode === 'rotate') {
      const dx = event.clientX - drag.lastClientX;
      const dy = event.clientY - drag.lastClientY;
      const currentRotation = Number(layout.rotation ?? 0);
      const theta = (currentRotation * Math.PI) / 180;

      // Tangente local del asa superior: arrastrar en ese sentido incrementa el giro horario.
      const tangentX = Math.cos(theta);
      const tangentY = Math.sin(theta);
      const projectedDelta = (dx * tangentX) + (dy * tangentY);
      const sensitivity = 0.8;
      const nextRotation = currentRotation + (projectedDelta * sensitivity);

      layout.rotation = Math.round(((nextRotation) + 540) % 360 - 180);
      drag.lastClientX = event.clientX;
      drag.lastClientY = event.clientY;
      if (event.cancelable) event.preventDefault();
      return;
    }

    if (drag.mode === 'resize') {
        if (event.cancelable) event.preventDefault();
        const deltaX = event.clientX - drag.startClientX;
        const deltaY = event.clientY - drag.startClientY;
        const handle = drag.handle ?? 'se';
        const isSideHandle = handle === 'e' || handle === 'w';
        const isHorizontalBarHandle = handle === 'n-width' || handle === 's-width';
        const horizontalDelta = handle.includes('e') ? deltaX : -deltaX;

      if (!isText) {
            const currentHeight = drag.startH || layout.h || 140;
        const minHeight = 40;
        const minWidth = 40;

        if (isHorizontalBarHandle) {
          const nextWidth = clamp(Math.round(drag.startW + deltaX), minWidth, 460);
          const centeredX = drag.startX - ((nextWidth - drag.startW) / 2);
          layout.w = nextWidth;
          layout.x = Math.round(clamp(centeredX, 0, Math.max(0, rect.width - nextWidth - 8)));
          return;
        }

        if (isSideHandle) {
          const nextWidth = clamp(Math.round(drag.startW + horizontalDelta), minWidth, 460);
          layout.w = nextWidth;

          if (handle === 'w') {
            layout.x = Math.round(clamp(drag.startX + (drag.startW - nextWidth), 0, Math.max(0, rect.width - nextWidth - 8)));
          } else {
            layout.x = Math.round(clamp(drag.startX, 0, Math.max(0, rect.width - nextWidth - 8)));
          }

          return;
        }

        const verticalDelta = handle.includes('s') ? deltaY : -deltaY;
        const nextWidth = clamp(Math.round(drag.startW + horizontalDelta), minWidth, 460);
        const nextHeight = clamp(Math.round(currentHeight + verticalDelta), minHeight, 460);
        layout.w = nextWidth;
        layout.h = nextHeight;

        if (handle.includes('w')) {
          layout.x = Math.round(clamp(drag.startX + (drag.startW - nextWidth), 0, Math.max(0, rect.width - nextWidth - 8)));
        } else {
          layout.x = Math.round(clamp(drag.startX, 0, Math.max(0, rect.width - nextWidth - 8)));
        }
        if (handle.includes('n')) {
          layout.y = Math.round(clamp(drag.startY + (currentHeight - nextHeight), 18, Math.max(18, rect.height - nextHeight - 8)));
        } else {
          layout.y = Math.round(clamp(drag.startY, 18, Math.max(18, rect.height - nextHeight - 8)));
        }

        return;
      }

        if (isSideHandle) {
            const nextWidth = clamp(Math.round(drag.startW + horizontalDelta), 120, 340);
            layout.w = nextWidth;

            if (handle === 'w') {
                layout.x = Math.round(clamp(drag.startX + (drag.startW - nextWidth), 0, Math.max(0, rect.width - nextWidth - 8)));
            } else {
                layout.x = Math.round(clamp(drag.startX, 0, Math.max(0, rect.width - nextWidth - 8)));
            }

            return;
        }

        const widthDelta = horizontalDelta + (deltaY * 0.35);
        const nextWidth = clamp(Math.round(drag.startW + widthDelta), 120, 340);
        const scale = nextWidth / Math.max(drag.startW, 1);

        layout.w = nextWidth;
        layout.fontSize = clamp(Math.round(drag.startFontSize * scale), 14, 72);
        layout.paragraphStyles = (drag.startParagraphStyles?.length ? drag.startParagraphStyles : ensureParagraphStyles(layout, getElementText(drag.elementId)).map((style) => ({ ...style })))
            .map((style) => ({
                ...style,
                fontSize: clamp(Math.round((style.fontSize ?? drag.startFontSize) * scale), 8, 200),
            }));

        if (handle.includes('w')) layout.x = Math.round(clamp(drag.startX + (drag.startW - nextWidth), 0, Math.max(0, rect.width - nextWidth - 8)));
        else layout.x = Math.round(clamp(drag.startX, 0, Math.max(0, rect.width - nextWidth - 8)));

        if (handle.includes('n')) layout.y = Math.round(clamp(drag.startY - ((layout.fontSize - drag.startFontSize) * 0.6), 18, Math.max(18, rect.height - 44)));
        return;
    }

    const deltaX = event.clientX - drag.startClientX;
    const deltaY = event.clientY - drag.startClientY;
    layout.x = Math.round(clamp(drag.startX + deltaX, 0, Math.max(0, rect.width - layout.w - 8)));
    layout.y = Math.round(clamp(drag.startY + deltaY, 18, Math.max(18, rect.height - (layout.h ?? 44))));
    if (event.cancelable) event.preventDefault();
};

const endDrag = (event) => {
    if (toolbarDrag.active && toolbarDrag.pointerId === event.pointerId) {
        toolbarDrag.active = false;
        toolbarDrag.pointerId = null;
        setDragDocumentState(false);
        return;
    }

    if (drag.pointerId !== null && event.pointerId !== undefined && drag.pointerId !== event.pointerId) return;
    drag.active = false;
    drag.mode = 'move';
    drag.pointerId = null;
    drag.elementId = null;
    drag.handle = null;
    drag.startH = 0;
    drag.startRotation = 0;
    drag.startAngle = 0;
    drag.centerX = 0;
    drag.centerY = 0;
    drag.lastClientX = 0;
    drag.lastClientY = 0;
    clearLongPress();
    setDragDocumentState(false);
};

const cycleAlignment = () => {
    const order = ['left', 'center', 'right', 'justify'];
    const current = selectedTextStyle.value?.textAlign ?? 'left';
    const index = order.indexOf(current);
    applyParagraphStyleField('textAlign', order[(index + 1) % order.length]);
};

const currentAlignmentIcon = computed(() => {
    const icons = {
        left: 'ph:text-align-left',
        center: 'ph:text-align-center',
        right: 'ph:text-align-right',
        justify: 'ph:text-align-justify',
    };
    const editorRef = state.selectedElementId ? richEditorRefs.value[state.selectedElementId] : null;
    const align = editorRef?.getActiveAttrs()?.textAlign ?? 'left';
    return icons[align];
});

const changeLayer = (mode) => {
    const currentId = state.selectedElementId;
    const ordered = [...orderedLayerIds.value];
    const currentIndex = ordered.indexOf(currentId);

    if (currentIndex === -1) {
        return;
    }

    const reordered = [...ordered];
    reordered.splice(currentIndex, 1);

    if (mode === 'front') reordered.push(currentId);
    else if (mode === 'back') reordered.unshift(currentId);
    else if (mode === 'forward') reordered.splice(Math.min(currentIndex + 1, reordered.length), 0, currentId);
    else if (mode === 'backward') reordered.splice(Math.max(currentIndex - 1, 0), 0, currentId);

    reordered.forEach((id, index) => {
        state.elementLayout[id].zIndex = (index + 1) * 10;
    });
};

const clearSelection = () => {
  if (editingElementId.value) {
    commitTextEdit();
  }
    state.selectedElementId = null;
    activePropertyPanel.value = null;
};

const handleCanvasPointerDown = (event) => {
    if (drag.active) return;
    if (event.target.closest('[data-editor-element="true"]') || event.target.closest('[data-editor-control="true"]')) return;

    // Si el fondo ya está seleccionado, permitir deseleccionar con clic
    if (state.selectedElementId === 'background') {
        clearSelection();
        return;
    }

    // Permitir seleccionar el fondo con doble clic
    if (event.detail === 2) {
        state.selectedElementId = 'background';
        activePropertyPanel.value = 'color';
        return;
    }

    clearSelection();
};

const handleGlobalPointerDown = (event) => {
    if (drag.active || !state.selectedElementId) return;

    const target = event.target;
    if (!(target instanceof Element)) return;

    const preserveSelectionTarget = target.closest(
        '[data-editor-element="true"],[data-editor-control="true"],[data-editor-keep-selection="true"],nav,header,[role="navigation"]'
    );

    if (preserveSelectionTarget) {
        return;
    }

    clearSelection();
};

onMounted(() => {
    document.addEventListener('pointerdown', handleGlobalPointerDown, true);
    document.addEventListener('pointermove', moveDrag, { passive: false });
    document.addEventListener('pointerup', endDrag);
    document.addEventListener('pointercancel', endDrag);
    refreshElementObservers();
});

onBeforeUnmount(() => {
    document.removeEventListener('pointerdown', handleGlobalPointerDown, true);
    document.removeEventListener('pointermove', moveDrag);
    document.removeEventListener('pointerup', endDrag);
    document.removeEventListener('pointercancel', endDrag);
    elementObservers.forEach((observer) => observer.disconnect());
    elementObservers.clear();
    clearLongPress();
    setDragDocumentState(false);
});

watch(editorElements, () => {
    refreshElementObservers();
}, { deep: true });
</script>

<template>
  <DesignerLayout
    title="Editor simplificado"
    eyebrow="Pantalla 6"
    description="Selecciona un texto para editarlo."
    :current-step="currentStep"
    :steps="steps"
    :dark-mode="state.darkMode"
    @toggle-dark="state.darkMode = !state.darkMode"
  >
    <section class="relative glass soft-shadow rounded-[32px] border border-white/70 p-6 sm:p-8 dark:border-slate-700/70">
      <div class="overflow-hidden rounded-[32px] border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
        <div
          v-if="hasSelection"
          data-editor-keep-selection="true"
          class="pointer-events-none absolute z-[7000]"
          :style="{ left: toolbarPosition.x + 'px', top: toolbarPosition.y + 'px' }"
        >
          <div data-editor-keep-selection="true" class="pointer-events-auto card glass soft-shadow border border-base-300/70 bg-base-100/90">
            <div class="card-body p-1.5">
                <div class="flex flex-wrap items-center gap-3">
                    <button type="button" class="order-first btn btn-ghost text-lg cursor-grab active:cursor-grabbing" @pointerdown="startToolbarDrag">⋮⋮</button>
                  <button v-for="tab in selectedPropertyTabs" :key="tab.id" type="button" class="btn border-0 py-1 px-2" :class="[activePropertyPanel === tab.id ? 'btn-primary' : 'btn-outline', tab.class]"
                        @click="activePropertyPanel = tab.id">
                        <span v-if="tab.label" class="text-sm text-base-100-accent" :class="tab.labelClass">{{ tab.label }}</span>
                        <Icon v-if="tab.icon" :icon="tab.icon" class="text-2xl"/>
                    </button>
                  <template v-if="hasTextSelection">
                    <input v-model.number="selectedTextStyle.fontSize" type="number" min="8" max="200" step="1" class="input input-bordered join-item w-12 text-center order-first" />
                    <button type="button" class="btn text-lg" :class="selectedTextStyle.fontWeight === 'bold' ? 'btn-primary' : 'btn-outline'" @click="selectedTextStyle.fontWeight = selectedTextStyle.fontWeight === 'bold' ? 'regular' : 'bold'">B</button>
                    <button type="button" class="btn text-lg italic" :class="selectedTextStyle.italic ? 'btn-primary' : 'btn-outline'" @click="selectedTextStyle.italic = !selectedTextStyle.italic">I</button>
                    <button type="button" class="btn text-lg w-12" :class="selectedTextStyle.uppercase ? 'btn-primary' : 'btn-outline'" @click="selectedTextStyle.uppercase = !selectedTextStyle.uppercase">Aa</button>
                    <button type="button" class="btn text-lg btn-outline" @click="cycleAlignment">
                      <Icon :icon="currentAlignmentIcon" class="scale-150"/>
                    </button>
                    <span class="rounded-full border border-base-300 bg-base-100 px-2 py-1 text-[11px] font-medium text-base-content/70">{{ activeParagraphLabel }}</span>
                  </template>
                  <template v-else>
                    <span class="rounded-full border border-base-300 bg-base-100 px-3 py-1 text-[11px] font-medium text-base-content/70">{{ activeElementLabel }}</span>
                  </template>
                </div>
            </div>
          </div>
        </div>

        <div class="grid gap-0 xl:grid-cols-[320px_1fr]">
          <aside data-editor-keep-selection="true" class="border-b border-base-300 bg-base-100 p-5 xl:border-b-0 xl:border-r">
            <div class="space-y-5">
              <div>
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Panel contextual</p>
                    <h3 class="mt-2 text-xl font-semibold text-base-content">{{ hasSelection && activePropertyPanel ? activePropertyTitle : 'Elementos' }}</h3>
                    <p v-if="hasSelection && activePropertyPanel" class="mt-2 text-sm leading-6 text-base-content/75">Elige una propiedad arriba para ver sus opciones.</p>
                  </div>
                  <button
                    v-if="hasSelection && activePropertyPanel"
                    type="button"
                    class="btn btn-ghost btn-sm btn-circle"
                    aria-label="Cerrar propiedad activa"
                    @click="activePropertyPanel = null"
                  >
                    <Icon icon="mdi:close" class="text-lg" />
                  </button>
                </div>
              </div>

              <!-- Panel de inserción (siempre visible cuando no hay selección) -->
              <div v-if="!hasSelection || !activePropertyPanel" class="space-y-3">
                <!-- Botón para seleccionar el fondo -->
                <button
                  type="button"
                  class="w-full rounded-xl border-2 p-3 transition"
                  :class="state.selectedElementId === 'background' ? 'border-primary bg-primary/15 text-primary' : 'border-base-300 bg-base-100/70 hover:border-primary/50 hover:bg-primary/10'"
                  @click="state.selectedElementId = 'background'; activePropertyPanel = 'color'"
                >
                  <div class="flex items-center gap-3">
                    <div class="h-8 w-8 rounded-lg border border-base-300" :style="{ backgroundColor: state.elementLayout.background?.backgroundColor }"></div>
                    <div class="text-left">
                      <p class="text-xs font-semibold uppercase tracking-[0.15em]">Fondo</p>
                      <p class="text-[11px] text-base-content/60">{{ state.elementLayout.background?.backgroundColor }}</p>
                    </div>
                  </div>
                </button>

                <!-- Grid de acciones -->
                <div class="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    class="flex flex-col items-center gap-2 rounded-2xl border p-4 transition"
                    :class="textPanelOpen ? 'border-primary bg-primary/10 text-primary' : 'border-base-300 bg-base-100/80 hover:border-primary/50 hover:bg-primary/10'"
                    @click="textPanelOpen = !textPanelOpen; imagePanelOpen = false; shapePanelOpen = false"
                  >
                    <span class="flex h-10 w-10 items-center justify-center rounded-xl text-2xl font-bold leading-none"
                      :class="textPanelOpen ? 'bg-primary/20' : 'bg-base-200'">T</span>
                    <span class="text-xs font-medium">Texto</span>
                  </button>

                  <button
                    type="button"
                    class="flex flex-col items-center gap-2 rounded-2xl border p-4 transition"
                    :class="imagePanelOpen ? 'border-primary bg-primary/10 text-primary' : 'border-base-300 bg-base-100/80 hover:border-primary/50 hover:bg-primary/10'"
                    @click="imagePanelOpen = !imagePanelOpen; textPanelOpen = false; shapePanelOpen = false"
                  >
                    <span class="flex h-10 w-10 items-center justify-center rounded-xl"
                      :class="imagePanelOpen ? 'bg-primary/20' : 'bg-base-200'">
                      <Icon icon="mdi:image-outline" class="text-2xl" />
                    </span>
                    <span class="text-xs font-medium">Imagen</span>
                  </button>

                  <button
                    type="button"
                    class="flex flex-col items-center gap-2 rounded-2xl border p-4 transition"
                    :class="shapePanelOpen ? 'border-primary bg-primary/10 text-primary' : 'border-base-300 bg-base-100/80 hover:border-primary/50 hover:bg-primary/10'"
                    @click="shapePanelOpen = !shapePanelOpen; textPanelOpen = false; imagePanelOpen = false"
                  >
                    <span class="flex h-10 w-10 items-center justify-center rounded-xl"
                      :class="shapePanelOpen ? 'bg-primary/20' : 'bg-base-200'">
                      <Icon icon="mdi:shape-outline" class="text-2xl" />
                    </span>
                    <span class="text-xs font-medium">Figura</span>
                  </button>
                </div>

                <!-- Opciones de texto (inline) -->
                <div v-if="textPanelOpen" class="space-y-1">
                  <button
                    v-for="preset in textPresets"
                    :key="preset.id"
                    type="button"
                    class="w-full rounded-xl border border-base-300/70 bg-base-100/70 px-4 py-3 text-left transition hover:border-primary/50 hover:bg-primary/10"
                    @click="addTextElement(preset.id)"
                  >
                    <span
                      :style="{ fontSize: Math.min(preset.fontSize, 32) + 'px', fontWeight: preset.fontWeight === 'bold' ? '700' : '400', lineHeight: preset.lineHeight }"
                      class="block text-base-content"
                    >{{ preset.label }}</span>
                  </button>
                </div>

                <!-- Opciones de imagen (inline) -->
                <div v-if="imagePanelOpen" class="card border border-base-300 bg-base-100/80">
                  <div class="card-body p-4">
                    <div class="flex flex-wrap gap-2">
                      <button
                        v-for="tab in imagePanelTabs"
                        :key="tab.id"
                        type="button"
                        class="btn btn-sm rounded-full"
                        :class="imagePanelTab === tab.id ? 'btn-primary' : 'btn-outline'"
                        @click="imagePanelTab = tab.id"
                      >
                        {{ tab.label }}
                      </button>
                    </div>

                    <div v-if="imagePanelTab === 'insert'" class="mt-4 space-y-4">
                      <div class="rounded-xl border border-base-300/70 bg-base-100/60 p-3">
                        <p class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Desde tu disco</p>
                        <button type="button" class="btn btn-primary mt-3 w-full rounded-xl" @click="triggerImagePicker">
                          <Icon icon="mdi:folder-image" class="text-xl" />
                          Seleccionar archivo
                        </button>
                        <input ref="imageInputRef" type="file" accept="image/*" class="hidden" @change="onImagePicked" />
                      </div>
                      <div class="rounded-xl border border-base-300/70 bg-base-100/60 p-3">
                        <p class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Desde una URL</p>
                        <div class="mt-3 flex items-center gap-2">
                          <input
                            v-model="imageUrlInput"
                            type="url"
                            placeholder="https://ejemplo.com/imagen.jpg"
                            class="input input-bordered input-sm flex-1"
                          />
                          <button type="button" class="btn btn-outline btn-sm" @click="addImageFromUrl">Insertar</button>
                        </div>
                      </div>
                    </div>

                    <div v-else-if="imagePanelTab === 'library'" class="mt-4 grid grid-cols-2 gap-2">
                      <button
                        v-for="image in imageLibrary"
                        :key="image.id"
                        type="button"
                        class="group overflow-hidden rounded-xl border border-base-300/70 bg-base-100/70"
                        @click="addLibraryImage(image)"
                      >
                        <img :src="image.src" :alt="image.label" class="h-20 w-full object-cover transition group-hover:scale-105" />
                        <span class="block px-2 py-1 text-[11px] text-base-content/70">{{ image.label }}</span>
                      </button>
                    </div>

                    <div v-else class="mt-4">
                      <div v-if="state.userUploadedImages.length" class="grid grid-cols-2 gap-2">
                        <button
                          v-for="image in state.userUploadedImages"
                          :key="image.id"
                          type="button"
                          class="group overflow-hidden rounded-xl border border-base-300/70 bg-base-100/70"
                          @click="addUploadedImage(image)"
                        >
                          <img :src="image.src" :alt="image.label" class="h-20 w-full object-cover transition group-hover:scale-105" />
                          <span class="block truncate px-2 py-1 text-[11px] text-base-content/70">{{ image.label }}</span>
                        </button>
                      </div>
                      <div v-else class="rounded-xl border border-base-300/70 bg-base-100/70 p-3 text-xs text-base-content/65">
                        Aún no tienes imágenes subidas. Añade una desde la pestaña Insertar.
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Opciones de figuras (inline) -->
                <div v-if="shapePanelOpen" class="card border border-base-300 bg-base-100/80">
                  <div class="card-body p-4">
                    <div class="flex flex-wrap gap-1.5">
                      <button
                        type="button"
                        class="btn btn-xs rounded-full"
                        :class="shapeCategoryFilter === 'all' ? 'btn-primary' : 'btn-outline'"
                        @click="shapeCategoryFilter = 'all'"
                      >
                        Todas
                      </button>
                      <button
                        v-for="cat in shapeCategories"
                        :key="cat.id"
                        type="button"
                        class="btn btn-xs rounded-full"
                        :class="shapeCategoryFilter === cat.id ? 'btn-primary' : 'btn-outline'"
                        @click="shapeCategoryFilter = cat.id"
                      >
                        {{ cat.label }}
                      </button>
                    </div>

                    <template v-for="cat in shapeCategories" :key="cat.id">
                      <div v-if="shapeCategoryFilter === 'all' || shapeCategoryFilter === cat.id" class="mt-4">
                        <p class="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-base-content/55">{{ cat.label }}</p>
                        <div class="grid grid-cols-4 gap-2">
                          <button
                            v-for="shape in cat.shapes"
                            :key="shape.id"
                            type="button"
                            class="group flex flex-col items-center gap-1.5 rounded-xl border border-base-300/70 bg-base-100/70 p-2 transition hover:border-primary/60 hover:bg-primary/10"
                            :title="shape.label"
                            @click="addShapeElement(shape.id)"
                          >
                            <div class="h-8 w-8 shrink-0">
                              <div
                                class="h-full w-full text-primary"
                                :style="shapeStyleFromKind(shape.id, { width: '100%', height: '100%', background: 'currentColor', border: '0' })"
                              />
                            </div>
                            <span class="w-full truncate text-center text-[10px] leading-tight text-base-content/70 group-hover:text-primary">{{ shape.label }}</span>
                          </button>
                        </div>
                      </div>
                    </template>
                  </div>
                </div>
              </div>

              <div v-else-if="activePropertyPanel === 'typography' && hasTextSelection" class="card border border-base-300 bg-base-100/80">
                <div class="card-body p-4">
                  <div class="flex items-center justify-between gap-3">
                    <p class="text-sm font-semibold text-base-content">Tipo de fuente</p>
                    <span class="rounded-full border border-base-300 bg-base-100 px-2 py-1 text-[11px] font-medium text-base-content/70">
                      {{ fontOptions.length }} fuentes
                    </span>
                  </div>
                  <p class="mt-1 text-xs text-base-content/60">Lista simple: una fuente por línea y mostrada con su propio tipo de letra.</p>
                  <p class="mt-2 text-xs font-medium text-primary/80">Estos ajustes se aplican al {{ activeParagraphLabel.toLowerCase() }}.</p>
                  <div class="mt-3 max-h-80 overflow-y-auto border-y border-base-300/70">
                    <button
                      v-for="font in fontOptions"
                      :key="font.family"
                      type="button"
                      class="block w-full border-b border-base-300/70 px-1 py-3 text-left transition last:border-b-0"
                      :class="selectedTextStyle.fontFamily === font.family
                        ? 'bg-primary/10 text-primary'
                        : 'bg-transparent text-base-content hover:bg-base-200/50'"
                      @click="selectedTextStyle.fontFamily = font.family"
                    >
                      <span class="block text-xl leading-tight" :style="{ fontFamily: font.family }">{{ font.label }}</span>
                    </button>
                  </div>
                  <div class="mt-4 space-y-3">
                    <label class="block text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Interletrado</label>
                    <div class="flex items-center gap-3">
                      <input v-model.number="selectedTextStyle.letterSpacing" type="range" min="-5" max="40" step="1" class="range range-primary flex-1" />
                      <input v-model.number="selectedTextStyle.letterSpacing" type="number" min="-5" max="40" step="1" class="input input-bordered input-sm w-20" />
                    </div>
                  </div>
                  <div class="mt-4 space-y-3">
                    <label class="block text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Interlineado</label>
                    <div class="flex items-center gap-3">
                      <input v-model.number="selectedTextStyle.lineHeight" type="range" min="0.6" max="3" step="0.1" class="range range-primary flex-1" />
                      <input v-model.number="selectedTextStyle.lineHeight" type="number" min="0.6" max="3" step="0.1" class="input input-bordered input-sm w-20" />
                    </div>
                  </div>
                </div>
              </div>

              <div v-else-if="activePropertyPanel === 'color'" class="card border border-base-300 bg-base-100/80">
                <div class="card-body p-4 space-y-4">
                  <div v-if="state.selectedElementId === 'background'">
                    <div class="flex items-center justify-between gap-3">
                      <div>
                        <p class="text-sm font-semibold text-base-content">Color del fondo</p>
                        <p class="text-xs text-base-content/60">Elige un color sólido para el fondo del diseño.</p>
                      </div>
                      <span class="rounded-full border border-base-300 bg-base-100 px-2 py-1 text-[11px] font-medium text-base-content/70">
                        {{ state.elementLayout.background?.backgroundColor }}
                      </span>
                    </div>
                    <div class="mt-4 grid grid-cols-6 gap-2">
                      <button
                        v-for="color in backgroundOptions"
                        :key="color"
                        type="button"
                        class="h-9 w-9 rounded-full transition hover:scale-105"
                        :class="state.elementLayout.background?.backgroundColor === color ? 'ring-2 ring-primary ring-offset-2 ring-offset-base-100' : 'ring-1 ring-slate-200 dark:ring-slate-700'"
                        :style="{ backgroundColor: color === 'transparent' ? '#ffffff' : color }"
                        :title="color"
                        @click="state.elementLayout.background.backgroundColor = color"
                      ></button>
                    </div>
                    <div class="mt-4 grid gap-3 sm:grid-cols-[auto_1fr] sm:items-center">
                      <label class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Color custom</label>
                      <div class="flex items-center gap-2">
                        <input
                          type="color"
                          class="h-10 w-12 cursor-pointer rounded-xl border border-base-300 bg-base-100 p-1"
                          :value="normalizePickerColor(state.elementLayout.background?.backgroundColor || '#4338ca', '#4338ca')"
                          @input="state.elementLayout.background.backgroundColor = $event.target.value"
                        />
                        <input
                          :value="state.elementLayout.background?.backgroundColor"
                          type="text"
                          placeholder="#4338ca"
                          class="input input-bordered input-sm flex-1"
                          @input="state.elementLayout.background.backgroundColor = $event.target.value"
                        />
                      </div>
                    </div>
                  </div>

                  <div v-else-if="hasTextSelection">
                    <div class="flex items-center justify-between gap-3">
                      <div>
                        <p class="text-sm font-semibold text-base-content">Color del texto</p>
                        <p class="text-xs text-base-content/60">Paleta ampliada y color personalizado.</p>
                      </div>
                      <span class="rounded-full border border-base-300 bg-base-100 px-2 py-1 text-[11px] font-medium text-base-content/70">
                        {{ selectedTextStyle.color }}
                      </span>
                    </div>
                    <p class="mt-2 text-xs font-medium text-primary/80">El color se aplica al {{ activeParagraphLabel.toLowerCase() }}.</p>
                    <div class="mt-4 grid grid-cols-6 gap-2">
                      <button
                        v-for="color in colorOptions"
                        :key="color"
                        type="button"
                        class="h-9 w-9 rounded-full transition hover:scale-105"
                        :class="selectedTextStyle.color === color ? 'ring-2 ring-primary ring-offset-2 ring-offset-base-100' : 'ring-1 ring-slate-200 dark:ring-slate-700'"
                        :style="{ backgroundColor: color }"
                        :title="color"
                        @click="selectedTextStyle.color = color"
                      ></button>
                    </div>
                    <div class="mt-4 grid gap-3 sm:grid-cols-[auto_1fr] sm:items-center">
                      <label class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Color custom</label>
                      <div class="flex items-center gap-2">
                        <input
                          type="color"
                          class="h-10 w-12 cursor-pointer rounded-xl border border-base-300 bg-base-100 p-1"
                          :value="normalizePickerColor(selectedTextStyle.color, '#ffffff')"
                          @input="setSelectedColor('color', $event.target.value)"
                        />
                        <input
                          :value="selectedTextStyle.color"
                          type="text"
                          placeholder="#7c3aed"
                          class="input input-bordered input-sm flex-1"
                          @input="setSelectedColor('color', $event.target.value)"
                        />
                      </div>
                    </div>
                  </div>

                  <div v-else-if="selectedElementType === 'shape'">
                    <div class="flex items-center justify-between gap-3">
                      <div>
                        <p class="text-sm font-semibold text-base-content">Color de la figura</p>
                        <p class="text-xs text-base-content/60">Puedes usar color sólido o degradado.</p>
                      </div>
                      <span class="rounded-full border border-base-300 bg-base-100 px-2 py-1 text-[11px] font-medium text-base-content/70">
                        {{ selectedElement.fillMode === 'gradient' ? 'degradado' : (selectedElement.backgroundColor || 'transparent') }}
                      </span>
                    </div>

                    <div class="mt-3 flex flex-wrap gap-2">
                      <button
                        type="button"
                        class="btn btn-sm rounded-full"
                        :class="selectedElement.fillMode !== 'gradient' ? 'btn-primary' : 'btn-outline'"
                        @click="selectedElement.fillMode = 'solid'"
                      >
                        Sólido
                      </button>
                      <button
                        type="button"
                        class="btn btn-sm rounded-full"
                        :class="selectedElement.fillMode === 'gradient' ? 'btn-primary' : 'btn-outline'"
                        @click="selectedElement.fillMode = 'gradient'"
                      >
                        Degradado
                      </button>
                    </div>

                    <div v-if="selectedElement.fillMode !== 'gradient'" class="space-y-4">
                      <div class="mt-4 grid grid-cols-6 gap-2">
                        <button
                          v-for="color in backgroundOptions"
                          :key="'element-color-' + color"
                          type="button"
                          class="h-9 w-9 rounded-full transition hover:scale-105"
                          :class="selectedElement.backgroundColor === color ? 'ring-2 ring-primary ring-offset-2 ring-offset-base-100' : 'ring-1 ring-slate-200 dark:ring-slate-700'"
                          :style="{ backgroundColor: color === 'transparent' ? '#ffffff' : color }"
                          :title="color"
                          @click="selectedElement.fillMode = 'solid'; selectedElement.backgroundColor = color"
                        ></button>
                      </div>
                      <div class="mt-4 grid gap-3 sm:grid-cols-[auto_1fr] sm:items-center">
                        <label class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Color custom</label>
                        <div class="flex items-center gap-2">
                          <input
                            type="color"
                            class="h-10 w-12 cursor-pointer rounded-xl border border-base-300 bg-base-100 p-1"
                            :value="normalizePickerColor(selectedElement.backgroundColor, '#ffffff')"
                            @input="selectedElement.fillMode = 'solid'; setSelectedColor('backgroundColor', $event.target.value)"
                          />
                          <input
                            :value="selectedElement.backgroundColor"
                            type="text"
                            placeholder="transparent o #0ea5e9"
                            class="input input-bordered input-sm flex-1"
                            @input="selectedElement.fillMode = 'solid'; setSelectedColor('backgroundColor', $event.target.value)"
                          />
                        </div>
                      </div>
                    </div>

                    <div v-else class="space-y-4">
                      <div class="grid grid-cols-2 gap-2">
                        <button
                          v-for="preset in shapeGradientOptions"
                          :key="preset.id"
                          type="button"
                          class="h-10 rounded-xl border border-base-300/70 transition hover:scale-[1.01]"
                          :class="selectedElement.gradientStart === preset.start && selectedElement.gradientEnd === preset.end ? 'ring-2 ring-primary ring-offset-2 ring-offset-base-100' : ''"
                          :style="{ background: `linear-gradient(135deg, ${preset.start}, ${preset.end})` }"
                          @click="applyShapeGradientPreset(preset.start, preset.end)"
                        ></button>
                      </div>
                      <div class="grid gap-3 sm:grid-cols-2">
                        <div class="flex items-center gap-2">
                          <span class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Inicio</span>
                          <input
                            type="color"
                            class="h-10 w-12 cursor-pointer rounded-xl border border-base-300 bg-base-100 p-1"
                            :value="normalizePickerColor(selectedElement.gradientStart || '#0ea5e9', '#0ea5e9')"
                            @input="selectedElement.gradientStart = $event.target.value"
                          />
                        </div>
                        <div class="flex items-center gap-2">
                          <span class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Final</span>
                          <input
                            type="color"
                            class="h-10 w-12 cursor-pointer rounded-xl border border-base-300 bg-base-100 p-1"
                            :value="normalizePickerColor(selectedElement.gradientEnd || '#8b5cf6', '#8b5cf6')"
                            @input="selectedElement.gradientEnd = $event.target.value"
                          />
                        </div>
                      </div>
                      <div class="grid gap-3 sm:grid-cols-[auto_1fr] sm:items-center">
                        <label class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Dirección</label>
                        <div class="grid grid-cols-3 gap-2 rounded-xl border border-base-300/70 bg-base-100/70 p-2">
                          <button
                            v-for="direction in shapeGradientDirections"
                            :key="direction.value"
                            type="button"
                            class="group flex items-center justify-center rounded-lg border p-2 transition"
                            :class="selectedElement.gradientAngle === direction.value
                              ? 'border-primary bg-primary/15 text-primary'
                              : 'border-base-300/70 bg-base-100/80 text-base-content/70 hover:border-primary/50 hover:text-primary'"
                            :title="direction.label"
                            :aria-label="direction.label"
                            @click="selectedElement.gradientAngle = direction.value"
                          >
                            <Icon :icon="direction.icon" class="text-xl" />
                          </button>
                        </div>
                      </div>
                      <div class="flex flex-wrap gap-2">
                        <button type="button" class="btn btn-outline btn-sm rounded-full" @click="swapShapeGradientStops">Alternar inicio/fin</button>
                        <div class="h-8 flex-1 min-w-28 rounded-full border border-base-300/70" :style="{ background: `linear-gradient(${selectedElement.gradientAngle || 135}deg, ${selectedElement.gradientStart || '#0ea5e9'}, ${selectedElement.gradientEnd || '#8b5cf6'})` }"></div>
                      </div>
                    </div>
                  </div>

                  <div v-else>
                    <div class="rounded-2xl border border-base-300/70 bg-base-100/60 p-3">
                      <div class="flex items-center justify-between gap-3">
                        <div>
                          <p class="text-sm font-semibold text-base-content">Color del marco/fondo</p>
                          <p class="text-xs text-base-content/60">Color del contenedor de la imagen.</p>
                        </div>
                        <span class="rounded-full border border-base-300 bg-base-100 px-2 py-1 text-[11px] font-medium text-base-content/70">
                          {{ selectedElement.backgroundColor || 'transparent' }}
                        </span>
                      </div>
                      <div class="mt-4 grid grid-cols-6 gap-2">
                        <button
                          v-for="color in backgroundOptions"
                          :key="'image-frame-' + color"
                          type="button"
                          class="h-9 w-9 rounded-full transition hover:scale-105"
                          :class="selectedElement.backgroundColor === color ? 'ring-2 ring-primary ring-offset-2 ring-offset-base-100' : 'ring-1 ring-slate-200 dark:ring-slate-700'"
                          :style="{ backgroundColor: color === 'transparent' ? '#ffffff' : color }"
                          :title="color"
                          @click="selectedElement.backgroundColor = color"
                        ></button>
                      </div>
                    </div>

                    <div class="rounded-2xl border border-base-300/70 bg-base-100/60 p-3">
                      <div class="flex items-center justify-between gap-3">
                        <div>
                          <p class="text-sm font-semibold text-base-content">Tinte de imagen</p>
                          <p class="text-xs text-base-content/60">Superposición de color sobre la foto.</p>
                        </div>
                        <span class="rounded-full border border-base-300 bg-base-100 px-2 py-1 text-[11px] font-medium text-base-content/70">
                          {{ selectedElement.imageTintStrength ?? 0 }}%
                        </span>
                      </div>
                      <div class="mt-3 grid grid-cols-6 gap-2">
                        <button
                          v-for="color in colorOptions"
                          :key="'image-tint-' + color"
                          type="button"
                          class="h-9 w-9 rounded-full transition hover:scale-105"
                          :class="selectedElement.imageTintColor === color ? 'ring-2 ring-primary ring-offset-2 ring-offset-base-100' : 'ring-1 ring-slate-200 dark:ring-slate-700'"
                          :style="{ backgroundColor: color }"
                          :title="color"
                          @click="selectedElement.imageTintColor = color"
                        ></button>
                      </div>
                      <div class="mt-4 grid gap-3 sm:grid-cols-[auto_1fr] sm:items-center">
                        <label class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Color custom</label>
                        <div class="flex items-center gap-2">
                          <input
                            type="color"
                            class="h-10 w-12 cursor-pointer rounded-xl border border-base-300 bg-base-100 p-1"
                            :value="normalizePickerColor(selectedElement.imageTintColor || '#0f172a', '#0f172a')"
                            @input="setSelectedColor('imageTintColor', $event.target.value)"
                          />
                          <input
                            :value="selectedElement.imageTintColor || '#0f172a'"
                            type="text"
                            placeholder="#0f172a"
                            class="input input-bordered input-sm flex-1"
                            @input="setSelectedColor('imageTintColor', $event.target.value)"
                          />
                        </div>
                      </div>
                      <div class="mt-4 space-y-2">
                        <label class="block text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Intensidad del tinte</label>
                        <div class="flex items-center gap-3">
                          <input v-model.number="selectedElement.imageTintStrength" type="range" min="0" max="100" step="1" class="range range-primary flex-1" />
                          <input v-model.number="selectedElement.imageTintStrength" type="number" min="0" max="100" step="1" class="input input-bordered input-sm w-20" />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div v-else-if="activePropertyPanel === 'effects'" class="card border border-base-300 bg-base-100/80">
                <div class="card-body p-4 space-y-4">
                  <p class="text-xs font-medium text-primary/80">Estos efectos se aplican al elemento completo seleccionado.</p>
                  <div class="rounded-2xl border border-base-300/70 bg-base-100/60 p-3">
                    <div class="flex items-center justify-between gap-3">
                      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Sombra</p>
                      <span class="text-[11px] text-base-content/60">{{ selectedElement.shadow ? (selectedElement.shadowColor || '#0f172a') : 'desactivada' }}</span>
                    </div>
                    <div class="mt-2 flex flex-wrap gap-2">
                      <button type="button" class="btn btn-outline btn-sm rounded-full" :class="selectedElement.shadow && selectedElement.shadowPreset === 'soft' ? 'btn-primary' : ''" @click="selectedElement.shadow = true; selectedElement.shadowPreset = 'soft'">Suave</button>
                      <button type="button" class="btn btn-outline btn-sm rounded-full" :class="selectedElement.shadow && selectedElement.shadowPreset === 'hard' ? 'btn-primary' : ''" @click="selectedElement.shadow = true; selectedElement.shadowPreset = 'hard'">Dura</button>
                      <button type="button" class="btn btn-outline btn-sm rounded-full" :class="selectedElement.shadow && selectedElement.shadowPreset === 'lifted' ? 'btn-primary' : ''" @click="selectedElement.shadow = true; selectedElement.shadowPreset = 'lifted'">Elevada</button>
                      <button type="button" class="btn btn-outline btn-sm rounded-full" @click="selectedElement.shadow = false">Sin sombra</button>
                    </div>
                    <div class="mt-3 grid grid-cols-6 gap-2">
                      <button
                        v-for="color in colorOptions"
                        :key="'shadow-' + color"
                        type="button"
                        class="h-8 w-8 rounded-full transition hover:scale-105"
                        :class="selectedElement.shadow && selectedElement.shadowColor === color ? 'ring-2 ring-primary ring-offset-1 ring-offset-base-100' : 'ring-1 ring-slate-200 dark:ring-slate-700'"
                        :style="{ backgroundColor: color }"
                        :title="color"
                        @click="selectedElement.shadow = true; selectedElement.shadowColor = color"
                      ></button>
                    </div>
                    <div class="mt-3 flex items-center gap-2">
                      <input
                        type="color"
                        class="h-10 w-12 cursor-pointer rounded-xl border border-base-300 bg-base-100 p-1"
                        :value="normalizePickerColor(selectedElement.shadowColor || '#0f172a', '#0f172a')"
                        @input="selectedElement.shadow = true; setSelectedColor('shadowColor', $event.target.value)"
                      />
                      <input
                        :value="selectedElement.shadowColor || '#0f172a'"
                        type="text"
                        placeholder="#0f172a"
                        class="input input-bordered input-sm flex-1"
                        @input="selectedElement.shadow = true; setSelectedColor('shadowColor', $event.target.value)"
                      />
                    </div>
                  </div>

                  <div class="rounded-2xl border border-base-300/70 bg-base-100/60 p-3">
                    <div class="flex items-center justify-between gap-3">
                      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Contorno</p>
                      <span class="text-[11px] text-base-content/60">{{ selectedElement.border ? `${selectedElement.contourWidth || 0}px` : 'apagado' }}</span>
                    </div>
                    <div class="mt-2 flex flex-wrap gap-2">
                      <button type="button" class="btn btn-outline btn-sm rounded-full" @click="selectedElement.border = !selectedElement.border">{{ selectedElement.border ? 'Quitar' : 'Activar' }}</button>
                      <button type="button" class="btn btn-outline btn-sm rounded-full" @click="selectedElement.contourWidth = clamp((selectedElement.contourWidth || 0) - 1, 0, 12)">Grosor -</button>
                      <button type="button" class="btn btn-outline btn-sm rounded-full" @click="selectedElement.contourWidth = clamp((selectedElement.contourWidth || 0) + 1, 0, 12)">Grosor +</button>
                    </div>
                    <div class="mt-3 grid grid-cols-6 gap-2">
                      <button
                        v-for="color in colorOptions"
                        :key="'contour-' + color"
                        type="button"
                        class="h-8 w-8 rounded-full transition hover:scale-105"
                        :class="selectedElement.border && selectedElement.contourColor === color ? 'ring-2 ring-primary ring-offset-1 ring-offset-base-100' : 'ring-1 ring-slate-200 dark:ring-slate-700'"
                        :style="{ backgroundColor: color }"
                        :title="color"
                        @click="selectedElement.border = true; selectedElement.contourColor = color"
                      ></button>
                    </div>
                    <div class="mt-3 flex items-center gap-2">
                      <input
                        type="color"
                        class="h-10 w-12 cursor-pointer rounded-xl border border-base-300 bg-base-100 p-1"
                        :value="normalizePickerColor(selectedElement.contourColor || '#ffffff', '#ffffff')"
                        @input="selectedElement.border = true; setSelectedColor('contourColor', $event.target.value)"
                      />
                      <input
                        :value="selectedElement.contourColor || '#ffffff'"
                        type="text"
                        placeholder="#ffffff"
                        class="input input-bordered input-sm flex-1"
                        @input="selectedElement.border = true; setSelectedColor('contourColor', $event.target.value)"
                      />
                    </div>
                  </div>

                  <div class="rounded-2xl border border-base-300/70 bg-base-100/60 p-3">
                    <div class="flex items-center justify-between gap-3">
                      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Neón</p>
                      <button type="button" class="btn btn-ghost btn-xs rounded-full" @click="selectedElement.neonColor = ''">Sin neón</button>
                    </div>
                    <div class="mt-3 grid grid-cols-6 gap-2">
                      <button
                        v-for="color in colorOptions"
                        :key="'neon-' + color"
                        type="button"
                        class="h-8 w-8 rounded-full transition hover:scale-105"
                        :class="selectedElement.neonColor === color ? 'ring-2 ring-primary ring-offset-1 ring-offset-base-100' : 'ring-1 ring-slate-200 dark:ring-slate-700'"
                        :style="{ backgroundColor: color }"
                        :title="color"
                        @click="selectedElement.neonColor = color"
                      ></button>
                    </div>
                    <div class="mt-3 flex items-center gap-2">
                      <input
                        type="color"
                        class="h-10 w-12 cursor-pointer rounded-xl border border-base-300 bg-base-100 p-1"
                        :value="normalizePickerColor(selectedElement.neonColor || '#7c3aed', '#7c3aed')"
                        @input="setSelectedColor('neonColor', $event.target.value)"
                      />
                      <input
                        :value="selectedElement.neonColor"
                        type="text"
                        placeholder="#7c3aed"
                        class="input input-bordered input-sm flex-1"
                        @input="setSelectedColor('neonColor', $event.target.value)"
                      />
                    </div>
                  </div>

                  <div class="rounded-2xl border border-base-300/70 bg-base-100/60 p-3">
                    <div class="flex items-center justify-between gap-3">
                      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Burbuja</p>
                      <button type="button" class="btn btn-ghost btn-xs rounded-full" @click="selectedElement.bubbleColor = 'transparent'">Sin burbuja</button>
                    </div>
                    <div class="mt-3 grid grid-cols-6 gap-2">
                      <button
                        v-for="color in backgroundOptions"
                        :key="'bubble-' + color"
                        type="button"
                        class="h-8 w-8 rounded-full transition hover:scale-105"
                        :class="selectedElement.bubbleColor === color ? 'ring-2 ring-primary ring-offset-1 ring-offset-base-100' : 'ring-1 ring-slate-200 dark:ring-slate-700'"
                        :style="{ backgroundColor: color === 'transparent' ? '#ffffff' : color }"
                        :title="color"
                        @click="selectedElement.bubbleColor = color"
                      ></button>
                    </div>
                    <div class="mt-3 flex items-center gap-2">
                      <input
                        type="color"
                        class="h-10 w-12 cursor-pointer rounded-xl border border-base-300 bg-base-100 p-1"
                        :value="normalizePickerColor(selectedElement.bubbleColor, '#7c3aed')"
                        @input="setSelectedColor('bubbleColor', $event.target.value)"
                      />
                      <input
                        :value="selectedElement.bubbleColor"
                        type="text"
                        placeholder="transparent o #7c3aed"
                        class="input input-bordered input-sm flex-1"
                        @input="setSelectedColor('bubbleColor', $event.target.value)"
                      />
                    </div>
                  </div>

                  <div class="rounded-2xl border border-base-300/70 bg-base-100/60 p-3">
                    <div class="flex items-center justify-between gap-3">
                      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Fondo</p>
                      <button type="button" class="btn btn-ghost btn-xs rounded-full" @click="selectedElement.backgroundColor = 'transparent'">Sin fondo</button>
                    </div>
                    <div class="mt-3 grid grid-cols-6 gap-2">
                      <button
                        v-for="color in backgroundOptions"
                        :key="'bg-' + color"
                        type="button"
                        class="h-8 w-8 rounded-full transition hover:scale-105"
                        :class="selectedElement.backgroundColor === color ? 'ring-2 ring-primary ring-offset-1 ring-offset-base-100' : 'ring-1 ring-slate-200 dark:ring-slate-700'"
                        :style="{ backgroundColor: color === 'transparent' ? '#ffffff' : color }"
                        :title="color"
                        @click="selectedElement.backgroundColor = color"
                      ></button>
                    </div>
                    <div class="mt-3 flex items-center gap-2">
                      <input
                        type="color"
                        class="h-10 w-12 cursor-pointer rounded-xl border border-base-300 bg-base-100 p-1"
                        :value="normalizePickerColor(selectedElement.backgroundColor, '#ffffff')"
                        @input="setSelectedColor('backgroundColor', $event.target.value)"
                      />
                      <input
                        :value="selectedElement.backgroundColor"
                        type="text"
                        placeholder="transparent o #0ea5e9"
                        class="input input-bordered input-sm flex-1"
                        @input="setSelectedColor('backgroundColor', $event.target.value)"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div v-else-if="activePropertyPanel === 'opacity'" class="card border border-base-300 bg-base-100/80">
                <div class="card-body p-4">
                  <p class="text-sm font-semibold text-base-content">Transparencia</p>
                  <div class="mt-3 flex flex-wrap gap-2">
                    <input v-model="selectedElement.opacity" type="range" min="0" max="100" step="1" class="range range-primary flex-1" />
                    <input v-model="selectedElement.opacity" type="number" min="0" max="100" step="1" class="input input-bordered input-sm w-24" />
                  </div>
                </div>
              </div>

              <div v-else-if="activePropertyPanel === 'arrange'" class="card border border-base-300 bg-base-100/80">
                <div class="card-body p-4">
                  <p class="text-sm font-semibold text-base-content">Posición</p>
                  <div class="mt-3 flex flex-wrap gap-2">
                    <button type="button" class="btn btn-outline btn-sm rounded-full" @click="changeLayer('forward')">Adelante</button>
                    <button type="button" class="btn btn-outline btn-sm rounded-full" @click="changeLayer('backward')">Atrás</button>
                    <button type="button" class="btn btn-outline btn-sm rounded-full" @click="changeLayer('front')">Al frente</button>
                    <button type="button" class="btn btn-outline btn-sm rounded-full" @click="changeLayer('back')">Al fondo</button>
                  </div>
                </div>
              </div>

              <div class="alert border border-base-300 bg-base-100/80 text-sm leading-6 text-base-content/80">
                Doble click para editar texto. Enter crea un nuevo parrafo; al hacer clic fuera, el texto se guarda automaticamente. Ctrl+Enter tambien confirma y Esc cancela. En touch, mantén pulsado para editar. Usa el icono inferior para mover, las esquinas para redimensionar y el icono superior para girar (doble click para volver a 0°).
              </div>
            </div>
          </aside>

          <div class="canvas-grid min-h-[680px] bg-slate-100 p-6 dark:bg-slate-950 sm:p-10">
            <div class="mx-auto max-w-[400px] bg-white p-4 shadow-2xl dark:bg-slate-900">
              <div ref="canvasRef" class="relative h-[620px] overflow-hidden p-7 text-white select-none touch-none" :style="{ backgroundColor: state.elementLayout.background?.backgroundColor || '#4338ca' }" @pointerdown="handleCanvasPointerDown">
                <button
                  type="button"
                  class="absolute inset-0 z-0 cursor-default bg-transparent"
                  aria-label="Deseleccionar elemento"
                  @pointerdown.stop="clearSelection"
                ></button>

                <div
                  v-for="item in editorElements"
                  :key="item.id"
                  data-editor-element="true"
                  :data-editor-id="item.id"
                  class="absolute rounded-[18px] p-0 text-left"
                  :style="elementBoxStyle(item.id)"
                  :class="state.selectedElementId === item.id
                    ? (editingElementId === item.id
                        ? 'border-2 border-solid border-cyan-300 bg-white/10 shadow-[0_0_0_3px_rgba(103,232,249,.35)] editor-editing-pulse'
                        : (drag.active && drag.elementId === item.id
                            ? 'border-2 border-dashed border-cyan-300 bg-white/10 shadow-[0_0_0_3px_rgba(103,232,249,.18)]'
                            : 'border-2 border-dashed border-cyan-300 bg-white/8 shadow-[0_0_0_3px_rgba(103,232,249,.18)]'))
                    : 'z-10 border border-transparent hover:border-white/20'"
                  @click="handleElementClick(item.id)"
                  @dblclick="beginTextEdit(item.id)"
                  @pointerdown="startTouchEditIntent($event, item.id)"
                >
                  <div class="relative" :class="item.type === 'text' ? '' : 'h-full w-full'" :style="elementContentStyle(item.id)">
                    <template v-if="item.type === 'text'">
                      <RichTextEditor
                        :ref="(el) => { if (el) richEditorRefs[item.id] = el; else delete richEditorRefs[item.id]; }"
                        :paragraph-styles="state.elementLayout[item.id].paragraphStyles ?? []"
                        :text="item.text"
                        :editable="editingElementId === item.id"
                        :editor-style="richEditorContainerStyle(item.id)"
                        @update:text="onRichEditorTextUpdate(item.id, $event)"
                        @update:paragraph-styles="onRichEditorStylesUpdate(item.id, $event)"
                        @selection-change="onRichEditorSelectionChange(item.id, $event)"
                        @blur="onRichEditorBlur(item.id, $event)"
                        @keydown.escape.stop="cancelTextEdit"
                        @keydown.ctrl.enter.stop="commitTextEdit"
                        @keydown.meta.enter.stop="commitTextEdit"
                        @pointerdown.stop
                        @mousedown.stop
                        @dblclick.stop="beginTextEdit(item.id)"
                        @click.stop="editingElementId === item.id ? null : handleElementClick(item.id)"
                      />
                    </template>
                    <template v-else-if="item.type === 'image'">
                      <div class="relative h-full w-full overflow-hidden rounded-xl" :style="imageFrameStyle(item.id)">
                        <img
                          v-if="item.src"
                          :src="item.src"
                          :alt="item.label"
                          class="h-full w-full object-cover"
                          draggable="false"
                        />
                        <div
                          v-if="item.src && (state.elementLayout[item.id]?.imageTintStrength ?? 0) > 0"
                          class="pointer-events-none absolute inset-0"
                          :style="imageTintOverlayStyle(item.id)"
                        ></div>
                        <div v-else class="flex h-full w-full items-center justify-center text-xs font-semibold text-white/80">
                          Imagen
                        </div>
                      </div>
                    </template>
                    <template v-else>
                      <div class="h-full w-full" :style="shapeStyle(item)"></div>
                    </template>
                  </div>
                </div>

                <div v-if="state.selectedElementId" data-editor-control="true" class="pointer-events-none absolute" :style="selectedOverlayStyle">
                  <button
                    data-editor-control="true"
                    type="button"
                    class="pointer-events-auto absolute -top-10 left-1/2 z-40 flex h-8 w-8 -translate-x-1/2 items-center justify-center rounded-full border-2 border-white bg-cyan-300 text-slate-950 shadow-md cursor-grab active:cursor-grabbing touch-none"
                    title="Girar elemento"
                    @pointerdown="startRotate($event, state.selectedElementId)"
                    @dblclick.stop.prevent="resetRotation(state.selectedElementId)"
                  >
                    <Icon icon="ph:arrow-clockwise-bold" class="text-lg" />
                  </button>
                  <span
                    v-if="selectedElementType !== 'text'"
                    data-editor-control="true"
                    class="pointer-events-auto absolute -top-2 left-1/2 z-30 h-3 w-16 -translate-x-1/2 cursor-ew-resize rounded-full border-2 border-white bg-cyan-300 touch-none"
                    @pointerdown="startResize($event, state.selectedElementId, 'n-width')"
                  ></span>
                  <span
                    v-if="selectedElementType !== 'text'"
                    data-editor-control="true"
                    class="pointer-events-auto absolute -bottom-2 left-1/2 z-30 h-3 w-16 -translate-x-1/2 cursor-ew-resize rounded-full border-2 border-white bg-cyan-300 touch-none"
                    @pointerdown="startResize($event, state.selectedElementId, 's-width')"
                  ></span>
                  <span data-editor-control="true" class="pointer-events-auto absolute -left-2 top-1/2 z-30 h-8 w-3 -translate-y-1/2 cursor-ew-resize rounded-full border-2 border-white bg-cyan-300 touch-none" @pointerdown="startResize($event, state.selectedElementId, 'w')"></span>
                  <span data-editor-control="true" class="pointer-events-auto absolute -right-2 top-1/2 z-30 h-8 w-3 -translate-y-1/2 cursor-ew-resize rounded-full border-2 border-white bg-cyan-300 touch-none" @pointerdown="startResize($event, state.selectedElementId, 'e')"></span>
                  <span data-editor-control="true" class="pointer-events-auto absolute -left-2 -top-2 z-30 h-4 w-4 cursor-nwse-resize rounded-full border-2 border-white bg-cyan-300 touch-none" @pointerdown="startResize($event, state.selectedElementId, 'nw')"></span>
                  <span data-editor-control="true" class="pointer-events-auto absolute -right-2 -top-2 z-30 h-4 w-4 cursor-nesw-resize rounded-full border-2 border-white bg-cyan-300 touch-none" @pointerdown="startResize($event, state.selectedElementId, 'ne')"></span>
                  <span data-editor-control="true" class="pointer-events-auto absolute -bottom-2 -left-2 z-30 h-4 w-4 cursor-nesw-resize rounded-full border-2 border-white bg-cyan-300 touch-none" @pointerdown="startResize($event, state.selectedElementId, 'sw')"></span>
                  <span data-editor-control="true" class="pointer-events-auto absolute -bottom-2 -right-2 z-30 h-4 w-4 cursor-nwse-resize rounded-full border-2 border-white bg-cyan-300 touch-none" @pointerdown="startResize($event, state.selectedElementId, 'se')"></span>
                  <button data-editor-control="true" type="button" class="pointer-events-auto absolute -bottom-10 left-1/2 z-40 flex h-8 w-8 -translate-x-1/2 items-center justify-center rounded-full border-2 border-white bg-cyan-300 text-sm font-black text-slate-950 shadow-md cursor-grab active:cursor-grabbing touch-none" @pointerdown="startDrag($event, state.selectedElementId)" title="Mover caja">✥</button>
                </div>
                <div class="pointer-events-none absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-cyan-200/30"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <StepFooter :previous-url="navigation.previous" :next-url="navigation.next" />
    </section>
  </DesignerLayout>
</template>

<style>
@keyframes editor-pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(103, 232, 249, 0.5), 0 0 0 4px rgba(103, 232, 249, 0.15);
  }
  50% {
    box-shadow: 0 0 0 5px rgba(103, 232, 249, 0.2), 0 0 0 10px rgba(103, 232, 249, 0);
  }
}
.editor-editing-pulse {
  animation: editor-pulse 1.4s ease-in-out infinite;
}
</style>
