<script setup>
import { Icon } from '@iconify/vue';
import DesignerLayout from '../../Layouts/DesignerLayout.vue';
import RichTextEditor from '../../Components/designer/RichTextEditor.vue';
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { objectiveRecommendations } from '../../data/designer';
import { useDesignerState } from '../../composables/useDesignerState';

defineProps({ currentStep: String, steps: Array, navigation: Object });
const state = useDesignerState();
if (!state.customElements || Array.isArray(state.customElements)) {
  state.customElements = Object.fromEntries(Object.entries(state.customElements ?? {}));
}
if (!state.userUploadedImages) {
  state.userUploadedImages = [];
}
const canvasRef = ref(null);
const zoomLevel = ref(100);
const imageInputRef = ref(null);
const imageUrlInput = ref('');
const imagePanelOpen = ref(false);
const imagePanelTab = ref('insert');
const shapePanelOpen = ref(false);
const textPanelOpen = ref(false);
const optionsPanelOpen = ref(true);
const shapeCategoryFilter = ref('all');
const elementMeasurements = reactive({});
const elementObservers = new Map();
const richEditorRefs = ref({});
const editingElementId = ref(null);
const editingBoxHeight = ref(null);
const selectedParagraphIndex = ref(0);
const paragraphSelection = reactive({ start: 0, end: 0, active: false });
const activePropertyPanel = ref(null);
const toolbarPosition = reactive({ x: 0, y: 3 });
const toolbarDrag = reactive({ active: false, pointerId: null, startX: 0, startY: 0, originX: 0, originY: 0 });
let longPressTimer = null;
const drag = reactive({
    active: false,
    mode: 'move',
    pointerId: null,
    elementId: null,
  groupId: null,
  groupSnapshot: null,
  multiSnapshot: null,
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
const dragIntent = reactive({
  active: false,
  pointerId: null,
  elementId: null,
  groupId: null,
  targetType: 'element',
  startX: 0,
  startY: 0,
});
const suppressElementClickUntil = ref(0);
const preserveEditorSelectionUntil = ref(0);
const multiSelectionIds = ref([]);
const marqueePreviewIds = ref([]);
const selectedGroupId = ref(null);
const groupedElements = reactive({});
const selectionMarquee = reactive({
  active: false,
  pointerId: null,
  startX: 0,
  startY: 0,
  currentX: 0,
  currentY: 0,
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
const textEffectOptions = [
  { id: 'shadow1', label: 'Sombra 1' },
  { id: 'shadow2', label: 'Sombra 2' },
  { id: 'shadow', label: 'Sombreado' },
  { id: 'glow', label: 'Brillante' },
  { id: 'echo', label: 'Eco' },
  { id: 'outline', label: 'Contorno' },
  { id: 'background', label: 'Fondo' },
  { id: 'misaligned', label: 'Desalineado' },
  { id: 'hollow', label: 'Sin relleno' },
  { id: 'neon', label: 'Neon' },
  { id: 'distort', label: 'Distorsion' },
];
const textEffectCardFontFamily = '"Avenir Next", "Trebuchet MS", "Segoe UI", sans-serif';
const BASE_CANVAS_SHORT_SIDE = 368;
const BASE_CANVAS_LONG_SIDE = 620;
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
      { id: 'rectangle', label: 'Rectángulo' },
      { id: 'rectangle-outline', label: 'Rectángulo recto' },
      { id: 'circle', label: 'Círculo' },
      { id: 'triangle-up', label: 'Triángulo' },
      { id: 'triangle-right-angle', label: 'Triángulo rectángulo' },
      { id: 'parallelogram', label: 'Paralelogramo' },
      { id: 'trapezoid', label: 'Trapecio' },
    ],
  },
  {
    id: 'poligonos',
    label: 'Polígonos',
    shapes: [
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
      { id: 'arrow-curved', label: 'Flecha curva' },
      { id: 'arrow-double-h', label: 'Doble H' },
      { id: 'chevron-right', label: 'Chevron →' },
    ],
  },
  {
    id: 'bocadillos',
    label: 'Bocadillos',
    shapes: [
      { id: 'callout', label: 'Bocadillo clásico' },
      { id: 'callout-ellipse', label: 'Bocadillo elipse' },
      { id: 'callout-cloud', label: 'Bocadillo nube' },
      { id: 'callout-burst', label: 'Bocadillo explosión' },
    ],
  },
  {
    id: 'marcos',
    label: 'Marcos',
    shapes: [
      { id: 'frame', label: 'Marco clásico' },
      { id: 'frame-rounded', label: 'Marco redondeado' },
      { id: 'frame-thick', label: 'Marco grueso' },
      { id: 'frame-thin', label: 'Marco fino' },
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
  'triangle-right-angle': 'polygon(0% 0%, 100% 100%, 0% 100%)',
  'triangle-down':   'polygon(0% 0%, 100% 0%, 50% 100%)',
  'triangle-right':  'polygon(0% 0%, 100% 50%, 0% 100%)',
  'triangle-left':   'polygon(100% 0%, 0% 50%, 100% 100%)',
  pentagon:          'polygon(50% 0%, 100% 38%, 82% 100%, 18% 100%, 0% 38%)',
  hexagon:           'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)',
  octagon:           'polygon(30% 0%, 70% 0%, 100% 30%, 100% 70%, 70% 100%, 30% 100%, 0% 70%, 0% 30%)',
  'star-5':          'polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)',
  'star-4':          'polygon(50% 0%, 60% 40%, 100% 50%, 60% 60%, 50% 100%, 40% 60%, 0% 50%, 40% 40%)',
  'star-6':          'polygon(50% 0%, 58% 17%, 79% 7%, 71% 26%, 93% 25%, 82% 43%, 100% 50%, 82% 57%, 93% 75%, 71% 74%, 79% 93%, 58% 83%, 50% 100%, 42% 83%, 21% 93%, 29% 74%, 7% 75%, 18% 57%, 0% 50%, 18% 43%, 7% 25%, 29% 26%, 21% 7%, 42% 17%)',
  'star-burst':      'polygon(50% 0%, 60% 22%, 82% 18%, 78% 40%, 100% 50%, 78% 60%, 82% 82%, 60% 78%, 50% 100%, 40% 78%, 18% 82%, 22% 60%, 0% 50%, 22% 40%, 18% 18%, 40% 22%)',
  'arrow-right':     'polygon(0% 25%, 60% 25%, 60% 0%, 100% 50%, 60% 100%, 60% 75%, 0% 75%)',
  'arrow-curved':    'polygon(70% 0%, 100% 22%, 82% 22%, 82% 50%, 62% 72%, 34% 72%, 24% 62%, 24% 46%, 40% 46%, 40% 56%, 56% 56%, 66% 46%, 66% 22%, 48% 22%)',
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
  'frame-thick':     'polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%, 18% 18%, 18% 82%, 82% 82%, 82% 18%, 18% 18%)',
  'frame-thin':      'polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%, 8% 8%, 8% 92%, 92% 92%, 92% 8%, 8% 8%)',
  'frame-notch':     'polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%, 14% 8%, 86% 8%, 92% 14%, 92% 86%, 86% 92%, 14% 92%, 8% 86%, 8% 14%, 14% 8%)',
  callout:           'polygon(0% 0%, 100% 0%, 100% 75%, 55% 75%, 50% 100%, 45% 75%, 0% 75%)',
  'callout-ellipse': 'polygon(8% 42%, 12% 25%, 24% 12%, 40% 6%, 60% 6%, 76% 12%, 88% 25%, 92% 40%, 88% 55%, 76% 68%, 66% 76%, 70% 94%, 54% 82%, 38% 82%, 24% 76%, 12% 64%, 8% 52%)',
  'callout-cloud':   'polygon(14% 60%, 8% 46%, 14% 33%, 26% 28%, 32% 18%, 46% 14%, 58% 18%, 70% 14%, 82% 22%, 88% 34%, 86% 46%, 92% 58%, 86% 70%, 74% 76%, 62% 76%, 56% 92%, 46% 78%, 32% 78%, 22% 72%)',
  'callout-burst':   'polygon(6% 18%, 26% 10%, 44% 0%, 58% 12%, 80% 8%, 90% 24%, 100% 40%, 92% 56%, 100% 74%, 84% 84%, 68% 96%, 54% 84%, 34% 90%, 20% 82%, 6% 70%, 0% 52%, 8% 38%)',
  'callout-top':     'polygon(0% 25%, 45% 25%, 50% 0%, 55% 25%, 100% 25%, 100% 100%, 0% 100%)',
  'callout-left':    'polygon(20% 0%, 100% 0%, 100% 100%, 20% 100%, 20% 60%, 0% 50%, 20% 40%)',
  'callout-right':   'polygon(0% 0%, 80% 0%, 80% 40%, 100% 50%, 80% 60%, 80% 100%, 0% 100%)',
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
const isGroupSelection = computed(() => Boolean(selectedGroupId.value && groupedElements[selectedGroupId.value]));
const selectedGroup = computed(() => {
  if (!selectedGroupId.value) return null;
  return groupedElements[selectedGroupId.value] ?? null;
});
const activeSelectionIds = computed(() => {
  if (isGroupSelection.value) {
    return [...(selectedGroup.value?.elementIds ?? [])];
  }
  if (multiSelectionIds.value.length > 1) {
    return [...multiSelectionIds.value];
  }
  if (state.selectedElementId) {
    return [state.selectedElementId];
  }
  return [];
});
const hasMultiSelection = computed(() => activeSelectionIds.value.length > 1);
const overlayControlTargetId = computed(() => (isGroupSelection.value ? selectedGroupId.value : state.selectedElementId));
const activeElementLabel = computed(() => {
  if (isGroupSelection.value) {
    return `Grupo (${selectedGroup.value?.elementIds?.length ?? 0})`;
  }
  if (state.selectedElementId === 'background') return 'Fondo';
  return editorElements.value.find((item) => item.id === state.selectedElementId)?.label ?? 'Elemento';
});
const selectedElementType = computed(() => editorElements.value.find((item) => item.id === state.selectedElementId)?.type ?? null);
const hasTextSelection = computed(() => hasSelection.value && selectedElementType.value === 'text');
const activeTextEffectId = computed(() => {
  if (!hasTextSelection.value || !selectedElement.value) return 'none';

  const mode = selectedElement.value.textEffectMode;
  if (mode) return mode;

  if (selectedElement.value.hollowText) return 'hollow';
  if (selectedElement.value.backgroundColor && selectedElement.value.backgroundColor !== 'transparent') return 'background';
  if (selectedElement.value.border) return 'outline';
  if (selectedElement.value.shadow && selectedElement.value.shadowPreset === 'echo') return 'echo';
  if (selectedElement.value.neonColor) return 'neon';
  if (selectedElement.value.shadow) return 'shadow';

  return 'none';
});
const textEffectRows = computed(() => {
  const rows = [];
  for (let index = 0; index < textEffectOptions.length; index += 3) {
    rows.push(textEffectOptions.slice(index, index + 3));
  }
  return rows;
});
const selectedPropertyTabs = computed(() => {
  if (isGroupSelection.value || hasMultiSelection.value) return [];
  if (!hasSelection.value) return textPropertyTabs;
  if (state.selectedElementId === 'background') return backgroundPropertyTabs;
  return selectedElementType.value === 'text' ? textPropertyTabs : visualPropertyTabs;
});
const activePropertyTitle = computed(() => selectedPropertyTabs.value.find((tab) => tab.id === activePropertyPanel.value)?.label ?? 'Propiedades');
const canvasBackgroundStyle = computed(() => {
  const bg = state.elementLayout.background;
  if (bg?.fillMode === 'gradient') {
    return {
      background: `linear-gradient(${bg.gradientAngle || 135}deg, ${bg.gradientStart || '#0ea5e9'}, ${bg.gradientEnd || '#8b5cf6'})`
    };
  }
  return {
    backgroundColor: bg?.backgroundColor || '#4338ca'
  };
});
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
const blendHexWithWhite = (hexColor, amountPercent = 40) => {
  if (typeof hexColor !== 'string') return '#ffffff';

  const normalized = normalizePickerColor(hexColor, '#ffffff');
  const amount = clamp(Number(amountPercent), 0, 100) / 100;
  const channel = (index) => Number.parseInt(normalized.slice(index, index + 2), 16);
  const mix = (value) => Math.round(value + (255 - value) * amount).toString(16).padStart(2, '0');

  const r = mix(channel(1));
  const g = mix(channel(3));
  const b = mix(channel(5));
  return `#${r}${g}${b}`;
};
const setSelectedColor = (field, value) => {
    if (paragraphStyleFields.has(field)) {
        applyParagraphStyleField(field, value);
        return;
    }

    if (!selectedElement.value) return;
    selectedElement.value[field] = value;
};
const getTextEffectStrokeWidth = (layout) => {
  const mode = layout?.textEffectMode;
  const isTextEffectStrokeMode = mode === 'outline' || mode === 'hollow' || mode === 'misaligned';

  if (!isTextEffectStrokeMode) {
    return clamp(Number(layout?.contourWidth ?? 2), 1, 12);
  }

  return (clamp(Number(layout?.contourWidth ?? 0), 0, 100) / 100) * 12;
};
const setTextEffect = (effectId) => {
  if (!selectedElement.value || !hasTextSelection.value) return;

  const layout = selectedElement.value;
  const nextEffectId = activeTextEffectId.value === effectId ? 'none' : effectId;
  layout.textEffectMode = nextEffectId;

  if (nextEffectId === 'none') {
    layout.shadow = false;
    layout.border = false;
    layout.neonColor = '';
    layout.bubbleColor = 'transparent';
    layout.backgroundColor = 'transparent';
    layout.hollowText = false;
    return;
  }

  layout.hollowText = false;

  if (nextEffectId === 'shadow1') {
    layout.shadow = true;
    layout.shadowPreset = 'hard';
    layout.shadowColor = layout.shadowColor || '#000000';
    layout.shadowAngle = 135;
    layout.shadowOffset = 10;
    layout.shadowBlur = 0;
    layout.shadowOpacity = 20;
    layout.border = false;
    layout.neonColor = '';
    layout.backgroundColor = 'transparent';
  } else if (nextEffectId === 'shadow2') {
    layout.shadow = true;
    layout.shadowPreset = 'soft';
    layout.shadowColor = layout.shadowColor || '#000000';
    layout.shadowAngle = 145;
    layout.shadowOffset = 12;
    layout.shadowBlur = 6;
    layout.shadowOpacity = 35;
    layout.border = false;
    layout.neonColor = '';
    layout.backgroundColor = 'transparent';
  } else if (nextEffectId === 'shadow') {
    layout.shadow = true;
    layout.shadowPreset = 'soft';
    layout.shadowColor = layout.shadowColor || '#0f172a';
    layout.shadowAngle = 135;
    layout.shadowOffset = 22;
    layout.shadowBlur = 15;
    layout.shadowOpacity = 55;
    layout.border = false;
    layout.neonColor = '';
    layout.backgroundColor = 'transparent';
  } else if (nextEffectId === 'glow') {
    layout.shadow = false;
    layout.neonColor = layout.neonColor || '#8b5cf6';
    layout.neonIntensity = layout.neonIntensity ?? 65;
    layout.border = false;
    layout.backgroundColor = 'transparent';
  } else if (nextEffectId === 'echo') {
    layout.shadow = true;
    layout.shadowPreset = 'echo';
    layout.shadowColor = layout.shadowColor || '#0f172a';
    layout.shadowAngle = 60;
    layout.shadowOffset = 15;
    layout.shadowBlur = 0;
    layout.shadowOpacity = 40;
    layout.neonColor = '';
    layout.border = false;
    layout.backgroundColor = 'transparent';
  } else if (nextEffectId === 'outline') {
    layout.shadow = false;
    layout.border = true;
    layout.contourColor = layout.contourColor || '#7c3aed';
    layout.contourWidth = 17;
    layout.neonColor = '';
    layout.backgroundColor = 'transparent';
  } else if (nextEffectId === 'background') {
    layout.shadow = false;
    layout.border = false;
    layout.neonColor = '';
    layout.backgroundColor = layout.backgroundColor && layout.backgroundColor !== 'transparent'
      ? layout.backgroundColor
      : '#ddd6fe';
    layout.backgroundRoundness = layout.backgroundRoundness ?? 50;
    layout.backgroundPadding = 5;
    layout.backgroundOpacity = layout.backgroundOpacity ?? 70;
  } else if (nextEffectId === 'misaligned') {
    layout.shadow = true;
    layout.shadowPreset = 'soft';
    layout.shadowColor = layout.shadowColor || '#7c3aed';
    layout.shadowAngle = 45;
    layout.shadowOffset = 33;
    layout.shadowOpacity = 20;
    layout.shadowBlur = 0;
    layout.misalignedThickness = 2;
    layout.contourWidth = 2;
    layout.contourColor = layout.contourColor || '#7c3aed';
    layout.neonColor = '';
    layout.border = true;
    layout.hollowText = true;
    layout.backgroundColor = 'transparent';
  } else if (nextEffectId === 'hollow') {
    layout.shadow = false;
    layout.border = true;
    layout.hollowText = true;
    layout.contourColor = layout.contourColor || '#7c3aed';
    layout.contourWidth = 2;
    layout.neonColor = '';
    layout.backgroundColor = 'transparent';
  } else if (nextEffectId === 'neon') {
    layout.shadow = false;
    layout.border = false;
    layout.neonColor = '';
    layout.neonIntensity = layout.neonIntensity ?? 80;
    layout.backgroundColor = 'transparent';
  } else if (nextEffectId === 'distort') {
    layout.shadow = true;
    layout.shadowPreset = 'hard';
    layout.shadowColor = '#f0f';
    layout.shadowAngle = 0;
    layout.shadowOffset = 15;
    layout.shadowBlur = 0;
    layout.shadowOpacity = 0;
    layout.shadowIntensity = 0;
    layout.neonColor = '#0ff';
    layout.neonIntensity = 0;
    layout.border = false;
    layout.backgroundColor = 'transparent';
  }
};
const textEffectPreviewStyle = (effectId) => {
  const base = {
    color: '#7c3aed',
    fontSize: '2.25rem',
    fontWeight: '700',
    lineHeight: '1',
    display: 'inline-block',
    padding: '0.12rem 0.24rem',
    borderRadius: '0.75rem',
    textShadow: 'none',
    WebkitTextStroke: '0',
    backgroundColor: 'transparent',
    transform: 'none',
  };

  if (effectId === 'shadow1') {
    return { ...base, textShadow: '4px 4px 0 #00000099' };
  }
  if (effectId === 'shadow2') {
    return { ...base, textShadow: '3px 4px 5px #000000aa' };
  }
  if (effectId === 'shadow') {
    return { ...base, textShadow: '0 10px 16px #8b5cf680' };
  }
  if (effectId === 'glow') {
    return { ...base, textShadow: '0 0 8px #c4b5fd, 0 0 18px #a855f7' };
  }
  if (effectId === 'echo') {
    return { ...base, textShadow: '2px 2px 0 #a855f7, 5px 5px 0 #c084fc' };
  }
  if (effectId === 'outline') {
    return { ...base, color: '#7c3aed80', WebkitTextStroke: '2px #7c3aed' };
  }
  if (effectId === 'background') {
    return { ...base, backgroundColor: '#ddd6fe' };
  }
  if (effectId === 'misaligned') {
    return {
      ...base,
      fontWeight: '500',
      color: 'transparent',
      WebkitTextStroke: '2px #7c3aed',
      textShadow: '4px 5px 0 #7c3aed33',
    };
  }
  if (effectId === 'hollow') {
    return { ...base, fontWeight: '500', color: 'transparent', WebkitTextStroke: '2px #7c3aed' };
  }
  if (effectId === 'neon') {
    return { ...base, color: '#f5f3ff', textShadow: '0 0 8px #c4b5fd, 0 0 18px #a855f7, 0 0 30px #7c3aed' };
  }
  if (effectId === 'distort') {
    return { ...base, textShadow: '-2px 0 0 #f0f, 2px 0 0 #0ff' };
  }

  return base;
};
  const applyGradientPreset = (target, start, end) => {
    if (target === 'background') {
      state.elementLayout.background.fillMode = 'gradient';
      state.elementLayout.background.gradientStart = start;
      state.elementLayout.background.gradientEnd = end;
    } else if (target === 'shape' && selectedElement.value) {
      selectedElement.value.fillMode = 'gradient';
      selectedElement.value.gradientStart = start;
      selectedElement.value.gradientEnd = end;
    }
  };
  const swapGradientStops = (target) => {
    if (target === 'background') {
      const start = state.elementLayout.background.gradientStart || '#0ea5e9';
      state.elementLayout.background.gradientStart = state.elementLayout.background.gradientEnd || '#8b5cf6';
      state.elementLayout.background.gradientEnd = start;
    } else if (target === 'shape' && selectedElement.value) {
      const start = selectedElement.value.gradientStart || '#0ea5e9';
      selectedElement.value.gradientStart = selectedElement.value.gradientEnd || '#8b5cf6';
      selectedElement.value.gradientEnd = start;
    }
  };
  const applyShapeGradientPreset = (start, end) => {
    applyGradientPreset('shape', start, end);
  };
  const swapShapeGradientStops = () => {
    swapGradientStops('shape');
  };
const clampToolbar = () => {
    // Sin restricciones de movimiento - libertad de arrastre completa
};

const buildTextShadow = (layout, textColor = null) => {
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
      const width = getTextEffectStrokeWidth(layout);
      if (width <= 0) {
        return shadows.length ? shadows.join(', ') : 'none';
      }
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
};

const buildBubbleShadow = (layout) => {
    if (!layout.bubbleColor || layout.bubbleColor === 'transparent') return 'none';
    return `0 10px 20px ${layout.bubbleColor}55`;
};

const buildVisualShadow = (layout) => {
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

  if (layout.neonColor && layout.textEffectMode !== 'distort') {
    const blurSoft = Math.round(4 + neonIntensity / 6);
    const blurStrong = Math.round(12 + neonIntensity / 2);
    shadows.push(`0 0 ${blurSoft}px ${layout.neonColor}`, `0 0 ${blurStrong}px ${layout.neonColor}`);
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

const isAspectLockedResizeElement = (id) => {
  const type = state.customElements?.[id]?.type;
  return type === 'shape' || type === 'image';
};

const getMaxZIndex = () => Object.values(state.elementLayout).reduce((max, layout) => Math.max(max, layout?.zIndex ?? 0), 0);
const resolvedSizeOption = computed(() => {
  const objectiveRules = objectiveRecommendations[state.objective] ?? objectiveRecommendations.generic;
  const options = objectiveRules[state.outputType] ?? [];
  return options.find((option) => option.label === state.size) ?? null;
});
const selectedSizeDetail = computed(() => resolvedSizeOption.value?.detail ?? '1080 × 1080 px');
const parseSizeDetail = (detail) => {
  if (!detail) return null;

  const normalized = String(detail).replace(',', '.').trim();
  const pxMatch = normalized.match(/(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*px/i);
  if (pxMatch) {
    return { width: Number(pxMatch[1]), height: Number(pxMatch[2]) };
  }

  const cmMatch = normalized.match(/(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*cm/i);
  if (cmMatch) {
    return { width: Number(cmMatch[1]), height: Number(cmMatch[2]) };
  }

  return null;
};
const editorCanvasDimensions = computed(() => {
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
const canvasGridStyle = computed(() => ({
  minHeight: `${editorCanvasDimensions.value.height + 96}px`,
}));
const editorGridStyle = computed(() => ({
  gridTemplateColumns: optionsPanelOpen.value ? '70px 320px 1fr' : '70px 1fr',
}));
const canvasFrameStyle = computed(() => ({
  width: `${editorCanvasDimensions.value.width + 32}px`,
  maxWidth: '100%',
}));
const canvasZoomStyle = computed(() => ({
  transform: `scale(${zoomLevel.value / 100})`,
  transformOrigin: 'top center',
}));
const zoomScale = computed(() => Math.max(0.25, zoomLevel.value / 100));
const controlZoomStyle = computed(() => ({
  transform: `scale(${Math.max(0.1, Math.min(4, 100 / zoomLevel.value))})`,
  transformOrigin: 'center center',
}));
const canvasElementStyle = computed(() => ({
  width: `${editorCanvasDimensions.value.width}px`,
  height: `${editorCanvasDimensions.value.height}px`,
}));
const setZoomLevel = (value) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return;
  zoomLevel.value = Math.round(clamp(parsed, 25, 200));
};
const getCanvasBounds = () => ({
  width: canvasRef.value?.clientWidth ?? editorCanvasDimensions.value.width,
  height: canvasRef.value?.clientHeight ?? editorCanvasDimensions.value.height,
});
const getInsertX = (elementWidth = 280) => {
  const bounds = getCanvasBounds();
  const width = Math.max(40, elementWidth);
  const maxX = Math.max(0, bounds.width - width - 8);
  const centeredX = Math.round((bounds.width - width) / 2);
  return Math.round(clamp(centeredX, 0, maxX));
};
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
  hollowText: false,
  neonColor: '',
  shadowAngle: 135,
  shadowOffset: 22,
  shadowBlur: 28,
  shadowOpacity: 65,
  misalignedThickness: 6,
  neonIntensity: 55,
  bubbleColor: 'transparent',
  backgroundColor: 'transparent',
  backgroundRoundness: 50,
  backgroundPadding: 5,
  backgroundOpacity: 70,
  textEffectMode: 'none',
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
    x: getInsertX(preset.width),
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
  state.customElements = {
    ...(state.customElements ?? {}),
    [id]: {
    id,
    type: 'text',
    label: preset.label,
    text: preset.preview,
    },
  };
  state.elementLayout = {
    ...(state.elementLayout ?? {}),
    [id]: layout,
  };
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
    x: getInsertX(220),
    y: 120,
    backgroundColor: '#ffffff',
    color: '#ffffff',
  });

  placeInsideCanvas(layout);
  state.customElements = {
    ...(state.customElements ?? {}),
    [id]: {
    id,
    type: 'image',
    label,
    src,
    },
  };
  state.elementLayout = {
    ...(state.elementLayout ?? {}),
    [id]: layout,
  };
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

  const isRectangle = shapeKind === 'rectangle' || shapeKind === 'rectangle-outline';
  const isRoundedFrame = shapeKind === 'frame-rounded';
  const layout = buildDefaultLayout({
    // El rectángulo base nace cuadrado; luego el usuario puede deformarlo libremente.
    w: isRectangle ? 140 : 140,
    h: isRectangle ? 140 : 140,
    x: getInsertX(140),
    y: 150,
    backgroundColor: isRoundedFrame ? 'transparent' : '#38bdf8',
    opacity: 90,
    shadow: true,
    border: isRoundedFrame,
    contourWidth: isRoundedFrame ? 10 : 0,
    contourColor: '#38bdf8',
  });
  placeInsideCanvas(layout);

  const id = createElementId('shape');
  state.customElements = {
    ...(state.customElements ?? {}),
    [id]: {
    id,
    type: 'shape',
    label: shape.label,
    shapeKind,
    },
  };
  state.elementLayout = {
    ...(state.elementLayout ?? {}),
    [id]: layout,
  };
  state.selectedElementId = id;
};

// Genera estilo CSS para una figura según su shapeKind
const shapeStyleFromKind = (shapeKind, base) => {
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
    const ids = activeSelectionIds.value;
    if (!ids.length) return {};

    const bounds = getSelectionBounds(ids);
    if (!bounds) return {};
    let rotation = 0;
    if (isGroupSelection.value) {
      rotation = Number(selectedGroup.value?.layout?.rotation ?? 0);
    } else if (ids.length === 1) {
      rotation = Number(state.elementLayout[ids[0]]?.rotation ?? 0);
    }

    return {
        left: `${bounds.x}px`,
        top: `${bounds.y}px`,
        width: `${bounds.w}px`,
        height: `${bounds.h}px`,
        zIndex: '6000',
        transform: `rotate(${rotation}deg)`,
        transformOrigin: 'center center',
    };
});

  const selectedActionBarStyle = computed(() => {
    const ids = activeSelectionIds.value;
    if (!ids.length || state.selectedElementId === 'background') {
      return {};
    }

    const bounds = getSelectionBounds(ids);
    if (!bounds) return {};
    const top = bounds.y - 74;

    return {
      left: `${bounds.x + (bounds.w / 2)}px`,
      top: `${top}px`,
      zIndex: '6100',
      transform: 'translateX(-50%)',
    };
  });

const selectedHandleMetrics = computed(() => {
  const ids = activeSelectionIds.value;
  const bounds = ids.length ? getSelectionBounds(ids) : null;
  const width = Math.max(1, bounds?.w ?? 120);
  const height = Math.max(1, bounds?.h ?? 120);
  const minSide = Math.min(width, height);

  const cornerSize = clamp(Math.round(minSide * 0.28), 8, 16);
  const sideThickness = clamp(Math.round(minSide * 0.12), 2, 12);
  const sideLength = clamp(Math.round(height * 0.45), 10, 32);
  const barThickness = clamp(Math.round(minSide * 0.12), 2, 10);
  const barLength = clamp(Math.round(width * 0.45), 14, 64);

  return {
    cornerSize: `${cornerSize}px`,
    cornerOffset: `${-Math.round(cornerSize / 2)}px`,
    sideThickness: `${sideThickness}px`,
    sideOffset: `${-Math.round(sideThickness / 2)}px`,
    sideLength: `${sideLength}px`,
    barThickness: `${barThickness}px`,
    barOffset: `${-Math.round(barThickness / 2)}px`,
    barLength: `${barLength}px`,
  };
});

const marqueeRectStyle = computed(() => {
  if (!selectionMarquee.active) return {};
  const left = Math.min(selectionMarquee.startX, selectionMarquee.currentX);
  const top = Math.min(selectionMarquee.startY, selectionMarquee.currentY);
  const width = Math.abs(selectionMarquee.currentX - selectionMarquee.startX);
  const height = Math.abs(selectionMarquee.currentY - selectionMarquee.startY);
  return {
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`,
  };
});

const updateElementMeasurement = (id, node) => {
    if (!node) return;

    elementMeasurements[id] = {
        width: node.offsetWidth,
        height: node.offsetHeight,
    };
};

  const cloneSelectedElement = () => {
    const sourceId = state.selectedElementId;
    if (!sourceId || sourceId === 'background') return;

    if (editingElementId.value) {
      commitTextEdit();
    }

    const sourceLayout = state.elementLayout[sourceId];
    const sourceElement = editorElements.value.find((item) => item.id === sourceId);
    if (!sourceLayout || !sourceElement) return;

    const cloneId = createElementId(sourceElement.type || 'element');
    const cloneLayout = {
      ...sourceLayout,
      x: (sourceLayout.x ?? 0) + 18,
      y: (sourceLayout.y ?? 0) + 18,
      zIndex: getMaxZIndex() + 10,
      paragraphStyles: Array.isArray(sourceLayout.paragraphStyles)
        ? sourceLayout.paragraphStyles.map((style) => ({ ...style }))
        : undefined,
    };

    placeInsideCanvas(cloneLayout);

    if (sourceElement.type === 'text') {
      state.customElements[cloneId] = {
        type: 'text',
        label: `${sourceElement.label} copia`,
        text: getElementText(sourceId),
      };
    } else if (sourceElement.type === 'image') {
      state.customElements[cloneId] = {
        type: 'image',
        label: `${sourceElement.label} copia`,
        src: sourceElement.src,
      };
    } else if (sourceElement.type === 'shape') {
      state.customElements[cloneId] = {
        type: 'shape',
        label: `${sourceElement.label} copia`,
        shapeKind: sourceElement.shapeKind,
      };
    } else {
      return;
    }

    state.elementLayout[cloneId] = cloneLayout;
    state.selectedElementId = cloneId;
  };

  const deleteSelectedElement = () => {
    const id = state.selectedElementId;
    if (!id || id === 'background') return;

    if (editingElementId.value === id) {
      commitTextEdit();
    }

    if (state.customElements?.[id]) {
      delete state.customElements[id];
    }

    if (state.elementLayout?.[id]) {
      delete state.elementLayout[id];
    }

    if (elementMeasurements[id]) {
      delete elementMeasurements[id];
    }

    if (richEditorRefs.value[id]) {
      delete richEditorRefs.value[id];
    }

    state.selectedElementId = null;
    activePropertyPanel.value = null;
  };

  const cloneElementsByIds = (ids) => {
    const clonedIds = [];

    ids.forEach((sourceId) => {
      const sourceLayout = state.elementLayout[sourceId];
      const sourceElement = editorElements.value.find((item) => item.id === sourceId);
      if (!sourceLayout || !sourceElement) return;

      const cloneId = createElementId(sourceElement.type || 'element');
      const cloneLayout = {
        ...sourceLayout,
        x: (sourceLayout.x ?? 0) + 18,
        y: (sourceLayout.y ?? 0) + 18,
        zIndex: getMaxZIndex() + 10,
        paragraphStyles: Array.isArray(sourceLayout.paragraphStyles)
          ? sourceLayout.paragraphStyles.map((style) => ({ ...style }))
          : undefined,
      };

      placeInsideCanvas(cloneLayout);

      if (sourceElement.type === 'text') {
        state.customElements[cloneId] = {
          type: 'text',
          label: `${sourceElement.label} copia`,
          text: getElementText(sourceId),
        };
      } else if (sourceElement.type === 'image') {
        state.customElements[cloneId] = {
          type: 'image',
          label: `${sourceElement.label} copia`,
          src: sourceElement.src,
        };
      } else if (sourceElement.type === 'shape') {
        state.customElements[cloneId] = {
          type: 'shape',
          label: `${sourceElement.label} copia`,
          shapeKind: sourceElement.shapeKind,
        };
      } else {
        return;
      }

      state.elementLayout[cloneId] = cloneLayout;
      clonedIds.push(cloneId);
    });

    return clonedIds;
  };

  const groupSelectedElements = () => {
    if (multiSelectionIds.value.length < 2) return;

    const ids = [...new Set(multiSelectionIds.value)].filter((id) => state.elementLayout[id]);
    if (ids.length < 2) return;
    if (ids.some((id) => getGroupIdForElement(id))) return;

    const bounds = getSelectionBounds(ids);
    if (!bounds) return;

    const groupId = createElementId('group');
    groupedElements[groupId] = {
      id: groupId,
      elementIds: ids,
      layout: {
        x: bounds.x,
        y: bounds.y,
        w: bounds.w,
        h: bounds.h,
        rotation: 0,
      },
    };

    selectGroup(groupId);
  };

  const cloneCurrentSelection = () => {
    if (isGroupSelection.value) {
      const sourceIds = [...selectedGroup.value.elementIds];
      const clonedIds = cloneElementsByIds(sourceIds);
      if (clonedIds.length < 2) return;
      selectedGroupId.value = null;
      multiSelectionIds.value = clonedIds;
      state.selectedElementId = null;
      groupSelectedElements();
      return;
    }

    if (multiSelectionIds.value.length > 1) {
      const clonedIds = cloneElementsByIds(multiSelectionIds.value);
      if (!clonedIds.length) return;
      if (clonedIds.length === 1) {
        state.selectedElementId = clonedIds[0];
        multiSelectionIds.value = [];
      } else {
        state.selectedElementId = null;
        multiSelectionIds.value = clonedIds;
      }
      return;
    }

    cloneSelectedElement();
  };

  const deleteElementsByIds = (ids) => {
    ids.forEach((id) => {
      if (editingElementId.value === id) {
        commitTextEdit();
      }
      if (state.customElements?.[id]) {
        delete state.customElements[id];
      }
      if (state.elementLayout?.[id]) {
        delete state.elementLayout[id];
      }
      if (elementMeasurements[id]) {
        delete elementMeasurements[id];
      }
      if (richEditorRefs.value[id]) {
        delete richEditorRefs.value[id];
      }
    });
  };

  const deleteCurrentSelection = () => {
    if (isGroupSelection.value) {
      deleteElementsByIds(selectedGroup.value.elementIds);
      delete groupedElements[selectedGroupId.value];
      selectedGroupId.value = null;
      return;
    }

    if (multiSelectionIds.value.length > 1) {
      deleteElementsByIds(multiSelectionIds.value);
      multiSelectionIds.value = [];
      return;
    }

    deleteSelectedElement();
  };

  const editSelectedTextElement = () => {
    if (!state.selectedElementId || selectedElementType.value !== 'text') return;
    beginTextEdit(state.selectedElementId, true);
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
      color: layout.hollowText ? 'transparent' : undefined,
        textShadow: 'none',
        WebkitTextStroke: '0',
        boxShadow: buildBubbleShadow(layout),
    };
};

const paragraphContentStyle = (id, index, text = null) => {
    const layout = state.elementLayout[id];
    const paragraphStyle = getParagraphStyleForElement(id, index, text);

    const baseColor = paragraphStyle?.color ?? layout.color ?? '#ffffff';
    const isNeon = layout.textEffectMode === 'neon' && !layout.hollowText;
    const displayColor = layout.hollowText
      ? 'transparent'
      : (isNeon ? '#ffffff' : baseColor);

    const strokeWidth = getTextEffectStrokeWidth(layout);

    return {
        display: 'block',
        fontSize: `${paragraphStyle?.fontSize ?? layout.fontSize}px`,
      color: displayColor,
      WebkitTextFillColor: layout.hollowText ? 'transparent' : undefined,
        fontFamily: paragraphStyle?.fontFamily ?? layout.fontFamily ?? 'Inter, sans-serif',
        fontStyle: paragraphStyle?.italic ? 'italic' : 'normal',
        fontWeight: paragraphStyle?.fontWeight === 'bold' ? '700' : '500',
        textAlign: paragraphStyle?.textAlign ?? 'left',
        textTransform: paragraphStyle?.uppercase ? 'uppercase' : 'none',
        letterSpacing: `${paragraphStyle?.letterSpacing ?? 0}px`,
        lineHeight: `${paragraphStyle?.lineHeight ?? 1.3}`,
        textShadow: buildTextShadow(layout, baseColor),
        WebkitTextStroke: layout.border && layout.hollowText && strokeWidth > 0 ? `${strokeWidth}px ${baseColor}` : '0',
        whiteSpace: 'pre-wrap',
    };
};

const richEditorContainerStyle = (id) => {
    const layout = state.elementLayout[id];
  const firstParagraphColor = layout?.paragraphStyles?.[0]?.color ?? layout?.color ?? '#ffffff';
  const strokeWidth = getTextEffectStrokeWidth(layout);
    return {
        opacity: `${(layout.opacity ?? 100) / 100}`,
    textShadow: buildTextShadow(layout, firstParagraphColor),
    WebkitTextStroke: layout?.border && layout?.hollowText && strokeWidth > 0
      ? `${strokeWidth}px ${firstParagraphColor}`
      : '0',
    WebkitTextFillColor: layout?.hollowText ? 'transparent' : undefined,
    color: layout?.hollowText ? 'transparent' : undefined,
    };
};

const neonColorOverride = (id) => {
  const layout = state.elementLayout[id];
  if (!layout || layout.textEffectMode !== 'neon' || layout.hollowText) return null;
  return '#ffffff';
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

const handleElementClick = (event, id) => {
  if (Date.now() < suppressElementClickUntil.value) {
    return;
  }

  // Shift+click: ya gestionado en pointerdown, no interferir
  if (event?.shiftKey) return;

  const groupId = getGroupIdForElement(id);
  if (groupId) {
    selectGroup(groupId);
    return;
  }

    if (editingElementId.value && editingElementId.value !== id) {
        commitTextEdit();
    }

  selectedGroupId.value = null;
  multiSelectionIds.value = [];

  if (!isTextElement(id)) {
    state.selectedElementId = id;
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
  const normalizedText = newText == null ? '' : String(newText);

    switch (id) {
        case 'title':
        case 'subtitle':
        case 'contact':
        case 'extra':
      state.content[id] = normalizedText;
            break;
        case 'meta': {
      const parts = normalizedText.split('\n');
            state.content.date = (parts[0] ?? '').trim();
            state.content.time = (parts[1] ?? '').trim();
            break;
        }
        default:
          if (state.customElements?.[id]?.type === 'text') {
      state.customElements[id].text = normalizedText;
          }
    }
};

const onRichEditorStylesUpdate = (id, newStyles) => {
    const layout = state.elementLayout[id];
    if (!layout) return;
    layout.paragraphStyles = newStyles;
};

const beginTextEdit = async (id, focusToEnd = false) => {
  if (!isTextElement(id)) return;
  const groupId = getGroupIdForElement(id);
  if (groupId) {
    selectGroup(groupId);
    return;
  }

    state.selectedElementId = id;
    editingBoxHeight.value = elementMeasurements[id]?.height ?? null;
    selectedParagraphIndex.value = 0;
    paragraphSelection.start = 0;
    paragraphSelection.end = 0;
    paragraphSelection.active = false;
    editingElementId.value = id;
    clearLongPress();
    await nextTick();
    if (focusToEnd) {
      richEditorRefs.value[id]?.focusAtEnd?.();
      return;
    }
    richEditorRefs.value[id]?.$el?.querySelector('[contenteditable]')?.focus();
};

const commitTextEdit = () => {
    if (!editingElementId.value) return;

    const id = editingElementId.value;
    const editorRef = richEditorRefs.value[id];

    if (editorRef?.getPlainText) {
      onRichEditorTextUpdate(id, editorRef.getPlainText());
    }

    if (editorRef?.getParagraphStyles) {
      onRichEditorStylesUpdate(id, editorRef.getParagraphStyles());
    }

    paragraphSelection.start = selectedParagraphIndex.value;
    paragraphSelection.end = selectedParagraphIndex.value;
    paragraphSelection.active = false;
    editingElementId.value = null;
    editingBoxHeight.value = null;
};

  const markEditorControlInteraction = () => {
    preserveEditorSelectionUntil.value = Date.now() + 300;
  };

const cancelTextEdit = () => {
    editingElementId.value = null;
    editingBoxHeight.value = null;
    paragraphSelection.start = selectedParagraphIndex.value;
    paragraphSelection.end = selectedParagraphIndex.value;
    paragraphSelection.active = false;
};
const onRichEditorBlur = (id, event) => {
    if (Date.now() < preserveEditorSelectionUntil.value) {
      commitTextEdit();
      return;
    }

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

const clearDragIntent = () => {
    dragIntent.active = false;
    dragIntent.pointerId = null;
    dragIntent.elementId = null;
  dragIntent.groupId = null;
  dragIntent.targetType = 'element';
    dragIntent.startX = 0;
    dragIntent.startY = 0;
};

const clearSelectionMarquee = () => {
  selectionMarquee.active = false;
  selectionMarquee.pointerId = null;
  selectionMarquee.startX = 0;
  selectionMarquee.startY = 0;
  selectionMarquee.currentX = 0;
  selectionMarquee.currentY = 0;
  marqueePreviewIds.value = [];
};

const getGroupIdForElement = (id) => {
  for (const [groupId, group] of Object.entries(groupedElements)) {
    if (group.elementIds.includes(id)) return groupId;
  }
  return null;
};

const getSelectionBounds = (ids = []) => {
  const bounds = ids.map((id) => {
    const layout = state.elementLayout[id];
    if (!layout) return null;
    const measured = elementMeasurements[id] ?? null;
    const width = measured?.width ?? layout.w ?? 0;
    const height = measured?.height ?? layout.h ?? 44;
    return {
      left: layout.x,
      top: layout.y,
      right: layout.x + width,
      bottom: layout.y + height,
    };
  }).filter(Boolean);

  if (!bounds.length) return null;
  const left = Math.min(...bounds.map((item) => item.left));
  const top = Math.min(...bounds.map((item) => item.top));
  const right = Math.max(...bounds.map((item) => item.right));
  const bottom = Math.max(...bounds.map((item) => item.bottom));
  return {
    x: left,
    y: top,
    w: Math.max(1, right - left),
    h: Math.max(1, bottom - top),
  };
};

const isElementSelected = (id) => {
  if (marqueePreviewIds.value.includes(id)) return true;
  if (isGroupSelection.value) {
    return selectedGroup.value?.elementIds?.includes(id) ?? false;
  }
  if (multiSelectionIds.value.length > 1) {
    return multiSelectionIds.value.includes(id);
  }
  return state.selectedElementId === id;
};

const startSelectionMarquee = (event) => {
  if (!canvasRef.value) return;
  const rect = canvasRef.value.getBoundingClientRect();
  selectionMarquee.active = true;
  selectionMarquee.pointerId = event.pointerId;
  selectionMarquee.startX = clamp(event.clientX - rect.left, 0, rect.width);
  selectionMarquee.startY = clamp(event.clientY - rect.top, 0, rect.height);
  selectionMarquee.currentX = selectionMarquee.startX;
  selectionMarquee.currentY = selectionMarquee.startY;
  marqueePreviewIds.value = [];
  event.currentTarget?.setPointerCapture?.(event.pointerId);
  setDragDocumentState(true);
};

const updateSelectionMarqueePreview = () => {
  const left = Math.min(selectionMarquee.startX, selectionMarquee.currentX);
  const top = Math.min(selectionMarquee.startY, selectionMarquee.currentY);
  const right = Math.max(selectionMarquee.startX, selectionMarquee.currentX);
  const bottom = Math.max(selectionMarquee.startY, selectionMarquee.currentY);

  marqueePreviewIds.value = editorElements.value
    .map((item) => {
      const layout = state.elementLayout[item.id];
      if (!layout) return null;
      const measured = elementMeasurements[item.id] ?? null;
      const width = measured?.width ?? layout.w ?? 0;
      const height = measured?.height ?? layout.h ?? 44;
      const intersects = !(
        layout.x + width < left
        || layout.x > right
        || layout.y + height < top
        || layout.y > bottom
      );
      return intersects ? item.id : null;
    })
    .filter(Boolean);
};

const finalizeSelectionMarquee = () => {
  const picked = [...new Set(marqueePreviewIds.value)];
  clearSelectionMarquee();

  if (!picked.length) {
    clearSelection();
    return;
  }

  if (picked.length === 1) {
    selectedGroupId.value = null;
    multiSelectionIds.value = [];
    state.selectedElementId = picked[0];
    return;
  }

  state.selectedElementId = null;
  selectedGroupId.value = null;
  multiSelectionIds.value = picked;
  activePropertyPanel.value = null;
};

const selectGroup = (groupId) => {
  if (!groupedElements[groupId]) return;
  const bounds = getSelectionBounds(groupedElements[groupId].elementIds);
  if (bounds) {
    groupedElements[groupId].layout.x = bounds.x;
    groupedElements[groupId].layout.y = bounds.y;
    groupedElements[groupId].layout.w = bounds.w;
    groupedElements[groupId].layout.h = bounds.h;
  }
  selectedGroupId.value = groupId;
  state.selectedElementId = null;
  multiSelectionIds.value = [];
  activePropertyPanel.value = null;
};

const buildGroupResizeSnapshot = (groupId) => {
  const group = groupedElements[groupId];
  if (!group) return null;

  return {
    x: group.layout.x,
    y: group.layout.y,
    w: group.layout.w,
    h: group.layout.h,
    members: group.elementIds.map((id) => {
      const layout = state.elementLayout[id];
      if (!layout) return null;
      const measured = elementMeasurements[id] ?? null;
      const measuredHeight = measured?.height ?? layout.h ?? getEstimatedTextHeight(layout, getElementText(id));
      return {
        id,
        isText: isTextElement(id),
        x: layout.x,
        y: layout.y,
        w: layout.w ?? measured?.width ?? 40,
        h: layout.h ?? measuredHeight,
        fontSize: layout.fontSize ?? 16,
        paragraphStyles: ensureParagraphStyles(layout, getElementText(id)).map((style) => ({ ...style })),
      };
    }).filter(Boolean),
  };
};

const beginElementDrag = ({ pointerId, clientX, clientY }, id, captureTarget = null) => {
    const canvas = canvasRef.value;
    const layout = state.elementLayout[id];
    if (!canvas || !layout) return;

    state.selectedElementId = id;
  selectedGroupId.value = null;
  multiSelectionIds.value = [];
    drag.active = true;
    drag.mode = 'move';
    drag.pointerId = pointerId;
    drag.elementId = id;
  drag.groupId = null;
  drag.groupSnapshot = null;
    drag.handle = null;
    drag.startClientX = clientX;
    drag.startClientY = clientY;
    drag.startX = layout.x;
    drag.startY = layout.y;
    drag.startW = layout.w;
    drag.startH = layout.h ?? 140;
    drag.startFontSize = layout.fontSize;
    clearLongPress();
    clearDragIntent();
    setDragDocumentState(true);

    captureTarget?.setPointerCapture?.(pointerId);
  };

  const handleElementPointerDown = (event, id) => {
    if (event.button !== undefined && event.button !== 0) return;
    if (editingElementId.value === id) return;

    const groupId = getGroupIdForElement(id);
    if (groupId) {
      selectGroup(groupId);
      dragIntent.active = true;
      dragIntent.pointerId = event.pointerId;
      dragIntent.elementId = null;
      dragIntent.groupId = groupId;
      dragIntent.targetType = 'group';
      dragIntent.startX = event.clientX;
      dragIntent.startY = event.clientY;
      clearLongPress();
      return;
    }

    // Shift+click: añadir/quitar de la selección múltiple
    if (event.shiftKey) {
      const current = multiSelectionIds.value.length > 1
        ? [...multiSelectionIds.value]
        : state.selectedElementId
          ? [state.selectedElementId]
          : [];

      if (current.includes(id)) {
        // Deseleccionar este elemento
        const next = current.filter((elId) => elId !== id);
        if (next.length === 1) {
          state.selectedElementId = next[0];
          selectedGroupId.value = null;
          multiSelectionIds.value = [];
        } else if (next.length === 0) {
          state.selectedElementId = null;
          selectedGroupId.value = null;
          multiSelectionIds.value = [];
        } else {
          state.selectedElementId = null;
          selectedGroupId.value = null;
          multiSelectionIds.value = next;
        }
      } else {
        // Añadir a la selección
        const next = [...current, id];
        state.selectedElementId = null;
        selectedGroupId.value = null;
        multiSelectionIds.value = next;
        dragIntent.active = true;
        dragIntent.pointerId = event.pointerId;
        dragIntent.elementId = id;
        dragIntent.groupId = null;
        dragIntent.targetType = 'multi';
        dragIntent.startX = event.clientX;
        dragIntent.startY = event.clientY;
        clearLongPress();
      }
      return;
    }

    // Si el elemento pertenece a la multi-selección activa, arrastrar todos juntos
    if (multiSelectionIds.value.length > 1 && multiSelectionIds.value.includes(id)) {
      dragIntent.active = true;
      dragIntent.pointerId = event.pointerId;
      dragIntent.elementId = id;
      dragIntent.groupId = null;
      dragIntent.targetType = 'multi';
      dragIntent.startX = event.clientX;
      dragIntent.startY = event.clientY;
      clearLongPress();
      return;
    }

    state.selectedElementId = id;
    selectedGroupId.value = null;
    multiSelectionIds.value = [];
    dragIntent.active = true;
    dragIntent.pointerId = event.pointerId;
    dragIntent.elementId = id;
    dragIntent.groupId = null;
    dragIntent.targetType = 'element';
    dragIntent.startX = event.clientX;
    dragIntent.startY = event.clientY;

    clearLongPress();
};

const startResize = (event, id, handle) => {
  const group = groupedElements[id] ?? null;
  const layout = group ? group.layout : state.elementLayout[id];
    if (!layout) return;

  markEditorControlInteraction();

    // Si estamos en modo edición, commiteamos antes de redimensionar para evitar
    // inconsistencias entre el estado interno de TipTap y paragraphStyles
    if (editingElementId.value) commitTextEdit();

    if (group) {
      selectGroup(id);
      state.selectedElementId = null;
      multiSelectionIds.value = [];
    } else {
      state.selectedElementId = id;
      selectedGroupId.value = null;
      multiSelectionIds.value = [];
    }
    drag.active = true;
    drag.mode = 'resize';
    drag.pointerId = event.pointerId;
    drag.elementId = group ? null : id;
    drag.groupId = group ? id : null;
    drag.groupSnapshot = null;
    drag.handle = handle;
    drag.startClientX = event.clientX;
    drag.startClientY = event.clientY;
    drag.startX = layout.x;
    drag.startY = layout.y;
    drag.startW = layout.w;
    drag.startH = layout.h ?? 140;
    drag.startFontSize = layout.fontSize;
    drag.startParagraphStyles = group
      ? []
      : ensureParagraphStyles(layout, getElementText(id)).map((style) => ({ ...style }));
    drag.groupSnapshot = group ? buildGroupResizeSnapshot(id) : null;
    clearLongPress();
    setDragDocumentState(true);

    event.currentTarget?.setPointerCapture?.(event.pointerId);
    event.stopPropagation();
    event.preventDefault();
};

  const getPointerAngle = (event, centerX, centerY) => Math.atan2(event.clientY - centerY, event.clientX - centerX) * (180 / Math.PI);

  const startRotate = (event, id) => {
    const group = groupedElements[id] ?? null;
    const layout = group ? group.layout : state.elementLayout[id];
    const measured = group ? { width: layout.w, height: layout.h } : elementMeasurements[id];
    if (!layout) return;

    markEditorControlInteraction();

    if (editingElementId.value) commitTextEdit();

    const width = measured?.width ?? layout.w ?? 0;
    const height = measured?.height ?? layout.h ?? 44;
    const centerX = layout.x + (width / 2);
    const centerY = layout.y + (height / 2);

    if (group) {
      selectGroup(id);
      state.selectedElementId = null;
    } else {
      state.selectedElementId = id;
      selectedGroupId.value = null;
      multiSelectionIds.value = [];
    }
    drag.active = true;
    drag.mode = 'rotate';
    drag.pointerId = event.pointerId;
    drag.elementId = group ? null : id;
    drag.groupId = group ? id : null;
    drag.groupSnapshot = null;
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
    if (groupedElements[id]) {
      groupedElements[id].layout.rotation = 0;
      groupedElements[id].elementIds.forEach((memberId) => {
        const memberLayout = state.elementLayout[memberId];
        if (memberLayout) memberLayout.rotation = 0;
      });
      return;
    }

    const layout = state.elementLayout[id];
    if (!layout) return;
    layout.rotation = 0;
  };

const moveDrag = (event) => {
  if (selectionMarquee.active && selectionMarquee.pointerId === event.pointerId && canvasRef.value) {
    const rect = canvasRef.value.getBoundingClientRect();
    const logicalBounds = getCanvasBounds();
    const boundsWidth = logicalBounds.width;
    const boundsHeight = logicalBounds.height;
    selectionMarquee.currentX = clamp(event.clientX - rect.left, 0, rect.width);
    selectionMarquee.currentY = clamp(event.clientY - rect.top, 0, rect.height);
    updateSelectionMarqueePreview();
    if (event.cancelable) event.preventDefault();
    return;
  }

    if (toolbarDrag.active && toolbarDrag.pointerId === event.pointerId) {
        toolbarPosition.x = toolbarDrag.originX + (event.clientX - toolbarDrag.startX);
        toolbarPosition.y = toolbarDrag.originY + (event.clientY - toolbarDrag.startY);
        clampToolbar();
        if (event.cancelable) event.preventDefault();
        return;
    }

    if (!drag.active && dragIntent.active && dragIntent.pointerId === event.pointerId && (dragIntent.elementId || dragIntent.groupId)) {
      const moved = Math.hypot(event.clientX - dragIntent.startX, event.clientY - dragIntent.startY);

      if (moved > 6) {
        if (dragIntent.targetType === 'group' && dragIntent.groupId) {
          const group = groupedElements[dragIntent.groupId];
          if (group) {
            drag.active = true;
            drag.mode = 'move';
            drag.pointerId = event.pointerId;
            drag.elementId = null;
            drag.groupId = dragIntent.groupId;
            drag.handle = null;
            drag.startClientX = event.clientX;
            drag.startClientY = event.clientY;
            drag.startX = group.layout.x;
            drag.startY = group.layout.y;
            drag.startW = group.layout.w;
            drag.startH = group.layout.h;
            setDragDocumentState(true);
            clearDragIntent();
          }
        } else if (dragIntent.targetType === 'multi' && dragIntent.elementId) {
          const snapshot = multiSelectionIds.value
            .map((elId) => { const l = state.elementLayout[elId]; return l ? { id: elId, startX: l.x, startY: l.y } : null; })
            .filter(Boolean);
          drag.active = true;
          drag.mode = 'multi';
          drag.pointerId = event.pointerId;
          drag.elementId = dragIntent.elementId;
          drag.groupId = null;
          drag.multiSnapshot = snapshot;
          drag.handle = null;
          drag.startClientX = event.clientX;
          drag.startClientY = event.clientY;
          setDragDocumentState(true);
          clearDragIntent();
        } else if (dragIntent.elementId) {
          beginElementDrag({
            pointerId: event.pointerId,
            clientX: dragIntent.startX,
            clientY: dragIntent.startY,
          }, dragIntent.elementId);
        }
        suppressElementClickUntil.value = Date.now() + 250;
      }
    }

    if (!drag.active || drag.pointerId !== event.pointerId || (!drag.elementId && !drag.groupId) || !canvasRef.value) {
        // para drag tipo 'multi', drag.elementId sí está seteado, así que este bloque no la afecta
        if (touchIntent.pointerId === event.pointerId) {
            const moved = Math.hypot(event.clientX - touchIntent.startX, event.clientY - touchIntent.startY);
            if (moved > 8) clearLongPress();
        }
        return;
    }

    const rect = canvasRef.value.getBoundingClientRect();
    const logicalBounds = getCanvasBounds();
    const boundsWidth = logicalBounds.width;
    const boundsHeight = logicalBounds.height;
    const layout = drag.groupId ? groupedElements[drag.groupId]?.layout : state.elementLayout[drag.elementId];
    const isText = drag.groupId ? false : isTextElement(drag.elementId);
    if (!layout) return;

    if (drag.groupId) {
      const group = groupedElements[drag.groupId];
      if (!group) return;

      if (drag.mode === 'move') {
        const deltaX = (event.clientX - drag.startClientX) / zoomScale.value;
        const deltaY = (event.clientY - drag.startClientY) / zoomScale.value;
        const nextX = Math.round(drag.startX + deltaX);
        const nextY = Math.round(drag.startY + deltaY);
        const shiftX = nextX - group.layout.x;
        const shiftY = nextY - group.layout.y;

        group.layout.x = nextX;
        group.layout.y = nextY;
        group.elementIds.forEach((id) => {
          const memberLayout = state.elementLayout[id];
          if (!memberLayout) return;
          memberLayout.x = Math.round((memberLayout.x ?? 0) + shiftX);
          memberLayout.y = Math.round((memberLayout.y ?? 0) + shiftY);
        });
        if (event.cancelable) event.preventDefault();
        return;
      }

      if (drag.mode === 'resize') {
        if (event.cancelable) event.preventDefault();
        const snapshot = drag.groupSnapshot;
        if (!snapshot) return;
        const deltaX = (event.clientX - drag.startClientX) / zoomScale.value;
        const deltaY = (event.clientY - drag.startClientY) / zoomScale.value;
        const handle = drag.handle ?? 'se';
        const minSize = 40;
        let nextX = snapshot.x;
        let nextY = snapshot.y;
        let nextW = snapshot.w;
        let nextH = snapshot.h;

        if (handle === 'n-width' || handle === 's-width') {
          if (handle === 's-width') {
            nextH = clamp(Math.round(snapshot.h + deltaY), minSize, boundsHeight - 8);
          } else {
            nextH = clamp(Math.round(snapshot.h - deltaY), minSize, boundsHeight - 8);
            nextY = snapshot.y + (snapshot.h - nextH);
          }
        } else {
          if (handle.includes('e')) {
            nextW = clamp(Math.round(snapshot.w + deltaX), minSize, boundsWidth - 8);
          }
          if (handle.includes('w')) {
            nextW = clamp(Math.round(snapshot.w - deltaX), minSize, boundsWidth - 8);
            nextX = snapshot.x + (snapshot.w - nextW);
          }
        }

        if (handle === 'e' || handle === 'w') {
          nextH = snapshot.h;
          nextY = snapshot.y;
        } else if (handle !== 'n-width' && handle !== 's-width') {
          if (handle.includes('s')) {
            nextH = clamp(Math.round(snapshot.h + deltaY), minSize, boundsHeight - 8);
          }
          if (handle.includes('n')) {
            nextH = clamp(Math.round(snapshot.h - deltaY), minSize, boundsHeight - 8);
            nextY = snapshot.y + (snapshot.h - nextH);
          }
        }

        nextX = clamp(Math.round(nextX), 0, Math.max(0, boundsWidth - nextW - 8));
        nextY = clamp(Math.round(nextY), 18, Math.max(18, boundsHeight - nextH - 8));

        const sx = nextW / Math.max(1, snapshot.w);
        const sy = nextH / Math.max(1, snapshot.h);

        group.layout.x = Math.round(nextX);
        group.layout.y = Math.round(nextY);
        group.layout.w = Math.round(nextW);
        group.layout.h = Math.round(nextH);

        snapshot.members.forEach((memberSnapshot) => {
          const member = state.elementLayout[memberSnapshot.id];
          if (!member) return;

          const scaledX = nextX + ((memberSnapshot.x - snapshot.x) * sx);
          const scaledY = nextY + ((memberSnapshot.y - snapshot.y) * sy);
          const scaledW = Math.max(40, Math.round(memberSnapshot.w * sx));
          const scaledH = Math.max(40, Math.round(memberSnapshot.h * sy));

          member.x = Math.round(scaledX);
          member.y = Math.round(scaledY);
          member.w = scaledW;

          if (!memberSnapshot.isText) {
            member.h = scaledH;
          }

          if (memberSnapshot.isText) {
            const scale = Math.max(0.2, Math.min(sx, sy));
            member.fontSize = clamp(Math.round(memberSnapshot.fontSize * scale), 8, 200);
            member.paragraphStyles = memberSnapshot.paragraphStyles.map((style) => ({
              ...style,
              fontSize: clamp(Math.round((style.fontSize ?? memberSnapshot.fontSize) * scale), 8, 200),
            }));
          }
        });
        return;
      }

      if (drag.mode === 'rotate') {
        const currentAngle = getPointerAngle(event, drag.centerX, drag.centerY);
        const deltaAngle = currentAngle - drag.startAngle;
        const radians = (deltaAngle * Math.PI) / 180;
        const cos = Math.cos(radians);
        const sin = Math.sin(radians);

        group.layout.rotation = Math.round(((Number(group.layout.rotation ?? 0) + deltaAngle) + 540) % 360 - 180);
        group.elementIds.forEach((id) => {
          const member = state.elementLayout[id];
          if (!member) return;
          const width = Math.max(1, member.w ?? 1);
          const height = Math.max(1, member.h ?? 44);
          const cx = (member.x ?? 0) + width / 2;
          const cy = (member.y ?? 0) + height / 2;
          const dx = cx - drag.centerX;
          const dy = cy - drag.centerY;
          const nextCx = drag.centerX + (dx * cos) - (dy * sin);
          const nextCy = drag.centerY + (dx * sin) + (dy * cos);

          member.x = Math.round(nextCx - width / 2);
          member.y = Math.round(nextCy - height / 2);
          member.rotation = Math.round(((Number(member.rotation ?? 0) + deltaAngle) + 540) % 360 - 180);
        });

        drag.startAngle = currentAngle;
        if (event.cancelable) event.preventDefault();
        return;
      }
    }

    if (drag.mode === 'rotate') {
      const dx = (event.clientX - drag.lastClientX) / zoomScale.value;
      const dy = (event.clientY - drag.lastClientY) / zoomScale.value;
      const currentRotation = Number(layout.rotation ?? 0);
      const theta = (currentRotation * Math.PI) / 180;

      // El asa de rotacion esta debajo del elemento, asi que su tangente local
      // es la inversa de la usada cuando el asa estaba arriba.
      const tangentX = -Math.cos(theta);
      const tangentY = -Math.sin(theta);
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
      const deltaX = (event.clientX - drag.startClientX) / zoomScale.value;
      const deltaY = (event.clientY - drag.startClientY) / zoomScale.value;
        const handle = drag.handle ?? 'se';
        const isSideHandle = handle === 'e' || handle === 'w';
        const isVerticalBarHandle = handle === 'n-width' || handle === 's-width';
        const horizontalDelta = handle.includes('e') ? deltaX : -deltaX;
      const maxTextWidth = Math.max(120, boundsWidth - 8);

      if (!isText) {
            const currentHeight = drag.startH || layout.h || 140;
        const minHeight = 4;
        const minWidth = 4;

        if (isVerticalBarHandle) {
          const verticalDelta = handle === 's-width' ? deltaY : -deltaY;
          const nextHeight = clamp(Math.round(currentHeight + verticalDelta), minHeight, 460);
          layout.h = nextHeight;

          if (handle === 'n-width') {
            layout.y = Math.round(clamp(drag.startY + (currentHeight - nextHeight), 18, Math.max(18, boundsHeight - nextHeight - 8)));
          } else {
            layout.y = Math.round(clamp(drag.startY, 18, Math.max(18, boundsHeight - nextHeight - 8)));
          }
          return;
        }

        if (isSideHandle) {
          const nextWidth = clamp(Math.round(drag.startW + horizontalDelta), minWidth, 460);
          layout.w = nextWidth;

          if (handle === 'w') {
            layout.x = Math.round(clamp(drag.startX + (drag.startW - nextWidth), 0, Math.max(0, boundsWidth - nextWidth - 8)));
          } else {
            layout.x = Math.round(clamp(drag.startX, 0, Math.max(0, boundsWidth - nextWidth - 8)));
          }

          return;
        }

        const verticalDelta = handle.includes('s') ? deltaY : -deltaY;
        let nextWidth = clamp(Math.round(drag.startW + horizontalDelta), minWidth, 460);
        let nextHeight = clamp(Math.round(currentHeight + verticalDelta), minHeight, 460);

        if (isAspectLockedResizeElement(drag.elementId)) {
          const startW = Math.max(1, drag.startW);
          const startH = Math.max(1, currentHeight);
          const widthScale = (drag.startW + horizontalDelta) / startW;
          const heightScale = (currentHeight + verticalDelta) / startH;
          const scale = Math.abs(widthScale - 1) >= Math.abs(heightScale - 1) ? widthScale : heightScale;
          nextWidth = clamp(Math.round(startW * scale), minWidth, 460);
          nextHeight = clamp(Math.round(startH * scale), minHeight, 460);
        }

        layout.w = nextWidth;
        layout.h = nextHeight;

        if (handle.includes('w')) {
          layout.x = Math.round(clamp(drag.startX + (drag.startW - nextWidth), 0, Math.max(0, boundsWidth - nextWidth - 8)));
        } else {
          layout.x = Math.round(clamp(drag.startX, 0, Math.max(0, boundsWidth - nextWidth - 8)));
        }
        if (handle.includes('n')) {
          layout.y = Math.round(clamp(drag.startY + (currentHeight - nextHeight), 18, Math.max(18, boundsHeight - nextHeight - 8)));
        } else {
          layout.y = Math.round(clamp(drag.startY, 18, Math.max(18, boundsHeight - nextHeight - 8)));
        }

        return;
      }

        if (isSideHandle) {
          const nextWidth = clamp(Math.round(drag.startW + horizontalDelta), 120, maxTextWidth);
            layout.w = nextWidth;

            if (handle === 'w') {
                layout.x = Math.round(clamp(drag.startX + (drag.startW - nextWidth), 0, Math.max(0, boundsWidth - nextWidth - 8)));
            } else {
                layout.x = Math.round(clamp(drag.startX, 0, Math.max(0, boundsWidth - nextWidth - 8)));
            }

            return;
        }

        const widthDelta = horizontalDelta + (deltaY * 0.35);
        const nextWidth = clamp(Math.round(drag.startW + widthDelta), 120, maxTextWidth);
        const scale = nextWidth / Math.max(drag.startW, 1);

        layout.w = nextWidth;
        layout.fontSize = clamp(Math.round(drag.startFontSize * scale), 14, 72);
        layout.paragraphStyles = (drag.startParagraphStyles?.length ? drag.startParagraphStyles : ensureParagraphStyles(layout, getElementText(drag.elementId)).map((style) => ({ ...style })))
            .map((style) => ({
                ...style,
                fontSize: clamp(Math.round((style.fontSize ?? drag.startFontSize) * scale), 8, 200),
            }));

        if (handle.includes('w')) layout.x = Math.round(clamp(drag.startX + (drag.startW - nextWidth), 0, Math.max(0, boundsWidth - nextWidth - 8)));
        else layout.x = Math.round(clamp(drag.startX, 0, Math.max(0, boundsWidth - nextWidth - 8)));

        if (handle.includes('n')) layout.y = Math.round(clamp(drag.startY - ((layout.fontSize - drag.startFontSize) * 0.6), 18, Math.max(18, boundsHeight - 44)));
        return;
    }

    if (drag.mode === 'multi') {
      if (!drag.multiSnapshot) return;
      const deltaX = (event.clientX - drag.startClientX) / zoomScale.value;
      const deltaY = (event.clientY - drag.startClientY) / zoomScale.value;
      drag.multiSnapshot.forEach(({ id: elId, startX, startY }) => {
        const l = state.elementLayout[elId];
        if (!l) return;
        l.x = Math.round(startX + deltaX);
        l.y = Math.round(startY + deltaY);
      });
      if (event.cancelable) event.preventDefault();
      return;
    }

    const deltaX = (event.clientX - drag.startClientX) / zoomScale.value;
    const deltaY = (event.clientY - drag.startClientY) / zoomScale.value;
    layout.x = Math.round(drag.startX + deltaX);
    layout.y = Math.round(drag.startY + deltaY);
    if (event.cancelable) event.preventDefault();
};

const endDrag = (event) => {
  if (selectionMarquee.active && selectionMarquee.pointerId === event.pointerId) {
    finalizeSelectionMarquee();
    setDragDocumentState(false);
    return;
  }

    if (toolbarDrag.active && toolbarDrag.pointerId === event.pointerId) {
        toolbarDrag.active = false;
        toolbarDrag.pointerId = null;
        setDragDocumentState(false);
        return;
    }

  if (dragIntent.pointerId !== null && event.pointerId !== undefined && dragIntent.pointerId === event.pointerId) {
    clearDragIntent();
  }

    if (drag.pointerId !== null && event.pointerId !== undefined && drag.pointerId !== event.pointerId) return;
  const wasDragging = drag.active;
    drag.active = false;
    drag.mode = 'move';
    drag.pointerId = null;
    drag.elementId = null;
    drag.groupId = null;
    drag.groupSnapshot = null;
    drag.multiSnapshot = null;
    drag.handle = null;
    drag.startH = 0;
    drag.startRotation = 0;
    drag.startAngle = 0;
    drag.centerX = 0;
    drag.centerY = 0;
    drag.lastClientX = 0;
    drag.lastClientY = 0;
    clearLongPress();
    clearDragIntent();
    if (wasDragging) {
      suppressElementClickUntil.value = Date.now() + 250;
    }
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
    selectedGroupId.value = null;
    multiSelectionIds.value = [];
    marqueePreviewIds.value = [];
    state.selectedElementId = null;
    activePropertyPanel.value = null;
};

const handleCanvasPointerDown = (event) => {
    if (drag.active || selectionMarquee.active) return;
    if (event.button !== undefined && event.button !== 0) return;
    if (event.target.closest('[data-editor-element="true"]') || event.target.closest('[data-editor-control="true"]')) return;

    // Si el fondo ya está seleccionado, permitir deseleccionar con clic
    if (state.selectedElementId === 'background') {
        clearSelection();
        return;
    }

    // Permitir seleccionar el fondo con doble clic
    if (event.detail === 2) {
      selectedGroupId.value = null;
      multiSelectionIds.value = [];
        state.selectedElementId = 'background';
        activePropertyPanel.value = 'color';
        return;
    }

    clearSelection();
    startSelectionMarquee(event);
};

const handleGlobalPointerDown = (event) => {
    if (drag.active || selectionMarquee.active || (!state.selectedElementId && !selectedGroupId.value && !multiSelectionIds.value.length)) return;

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

const handleGlobalKeydown = (event) => {
  if (editingElementId.value) return;
  if (event.target && event.target !== document.body && ['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName)) return;
  if (event.key === 'Delete' || event.key === 'Backspace') {
    deleteCurrentSelection();
  }
};

onMounted(() => {
  document.addEventListener('pointerdown', handleGlobalPointerDown, true);
  document.addEventListener('pointermove', moveDrag, { passive: false });
  document.addEventListener('pointerup', endDrag);
  document.addEventListener('pointercancel', endDrag);
  document.addEventListener('keydown', handleGlobalKeydown);
  refreshElementObservers();
});

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleGlobalPointerDown, true);
  document.removeEventListener('pointermove', moveDrag);
  document.removeEventListener('pointerup', endDrag);
  document.removeEventListener('pointercancel', endDrag);
  document.removeEventListener('keydown', handleGlobalKeydown);
  elementObservers.forEach((observer) => observer.disconnect());
  elementObservers.clear();
  clearLongPress();
  setDragDocumentState(false);
});

watch(editorElements, () => {
    Object.entries(groupedElements).forEach(([groupId, group]) => {
      group.elementIds = group.elementIds.filter((id) => Boolean(state.elementLayout[id]));
      if (group.elementIds.length < 2) {
        delete groupedElements[groupId];
        if (selectedGroupId.value === groupId) {
          selectedGroupId.value = null;
        }
      }
    });

    refreshElementObservers();
}, { deep: true });

watch(() => state.selectedElementId, () => {
    toolbarPosition.x = 0;
    toolbarPosition.y = 3;
  if (state.selectedElementId) {
    selectedGroupId.value = null;
    multiSelectionIds.value = [];
  }
});

watch(selectedGroupId, (groupId) => {
  if (!groupId) return;
  state.selectedElementId = null;
  activePropertyPanel.value = null;
});
</script>

<template>
  <DesignerLayout
    title="Editor simplificado"
    eyebrow="Pantalla 6"
    description="Selecciona un texto para editarlo."
    :current-step="currentStep"
    :steps="steps"
    :show-steps="false"
    :show-header="false"
    :full-height="true"
    :dark-mode="state.darkMode"
    @toggle-dark="state.darkMode = !state.darkMode"
  >
    <div class="flex h-full min-h-0 flex-col overflow-hidden bg-base-100">
    <nav class="flex flex-wrap items-center justify-between gap-3 border-b border-base-300 bg-base-100 px-4 py-3 shadow-sm">
      <div class="flex items-center gap-2">
        <span class="rounded-xl bg-primary/15 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-primary">Editor</span>
        <span class="text-sm text-base-content/65">{{ state.size || 'Tamaño no definido' }}</span>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <div class="flex items-center gap-2 rounded-xl border border-base-300 px-3 py-2">
          <span class="text-xs font-semibold uppercase tracking-[0.16em] text-base-content/60">Zoom</span>
          <input
            :value="zoomLevel"
            type="range"
            min="25"
            max="200"
            step="5"
            class="range range-primary h-2 w-28"
            @input="setZoomLevel($event.target.value)"
          />
          <input
            :value="zoomLevel"
            type="number"
            min="25"
            max="200"
            step="5"
            class="input input-bordered input-sm w-20"
            @input="setZoomLevel($event.target.value)"
          />
          <span class="text-xs text-base-content/60">%</span>
        </div>

        <button
          type="button"
          class="btn btn-sm btn-outline rounded-full"
          @click="state.darkMode = !state.darkMode"
        >
          {{ state.darkMode ? '☀️ Modo claro' : '🌙 Modo oscuro' }}
        </button>

        <a href="/designer/export" class="btn btn-sm btn-primary rounded-full">Exportar</a>
      </div>
    </nav>

    <section class="relative min-h-0 flex-1 overflow-hidden">
      <div class="h-full overflow-hidden border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
        <div
          v-if="hasSelection && !hasMultiSelection && !isGroupSelection && state.selectedElementId !== 'background'"
          data-editor-keep-selection="true"
          class="pointer-events-none absolute z-50 flex justify-center"
          :style="{ left: '70px', right: '0', top: `${toolbarPosition.y}px` }"
        >
          <div :style="{ transform: `translateX(${toolbarPosition.x}px)` }" class="pointer-events-none">
          <div data-editor-keep-selection="true" class="pointer-events-auto card glass soft-shadow border border-base-300/70 bg-base-100/90">
            <div class="card-body p-1.5">
                <div class="flex flex-wrap items-center gap-3">
                    <button type="button" class="order-first btn btn-ghost text-lg cursor-grab active:cursor-grabbing" @pointerdown="startToolbarDrag">⋮⋮</button>
                  <button v-for="tab in selectedPropertyTabs" :key="tab.id" type="button" class="btn border-0 py-1 px-2" :class="[activePropertyPanel === tab.id ? 'btn-primary' : 'btn-outline', tab.class]"
                        @click="activePropertyPanel = tab.id; optionsPanelOpen = true">
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
                  </template>
                  <template v-else>
                    <span class="rounded-full border border-base-300 bg-base-100 px-3 py-1 text-[11px] font-medium text-base-content/70">{{ activeElementLabel }}</span>
                  </template>
                </div>
            </div>
          </div>
          </div>
        </div>

        <div class="relative grid h-full min-h-0 gap-0" :style="editorGridStyle">
          <!-- Panel de Creación (vertical, siempre visible) -->
          <div class="flex flex-col items-center gap-2 border-r border-base-300 bg-base-100 p-3 xl:border-b-0">
            <button
              type="button"
              class="flex h-14 w-14 flex-col items-center justify-center gap-1 rounded-2xl border transition"
              :class="textPanelOpen ? 'border-primary bg-primary/10 text-primary' : 'border-base-300 bg-base-100/80 hover:border-primary/50 hover:bg-primary/10'"
              @click="textPanelOpen = true; imagePanelOpen = false; shapePanelOpen = false; optionsPanelOpen = true"
              title="Agregar Texto"
            >
              <span class="text-2xl font-bold leading-none">T</span>
              <span class="text-[9px] font-medium">Texto</span>
            </button>

            <button
              type="button"
              class="flex h-14 w-14 flex-col items-center justify-center gap-1 rounded-2xl border transition"
              :class="imagePanelOpen ? 'border-primary bg-primary/10 text-primary' : 'border-base-300 bg-base-100/80 hover:border-primary/50 hover:bg-primary/10'"
              @click="imagePanelOpen = true; textPanelOpen = false; shapePanelOpen = false; optionsPanelOpen = true"
              title="Agregar Imagen"
            >
              <Icon icon="mdi:image-outline" class="text-2xl" />
              <span class="text-[9px] font-medium">Imagen</span>
            </button>

            <button
              type="button"
              class="flex h-14 w-14 flex-col items-center justify-center gap-1 rounded-2xl border transition"
              :class="shapePanelOpen ? 'border-primary bg-primary/10 text-primary' : 'border-base-300 bg-base-100/80 hover:border-primary/50 hover:bg-primary/10'"
              @click="shapePanelOpen = true; textPanelOpen = false; imagePanelOpen = false; optionsPanelOpen = true"
              title="Agregar Figura"
            >
              <Icon icon="mdi:shape-outline" class="text-2xl" />
              <span class="text-[9px] font-medium">Figura</span>
            </button>

            <button
              type="button"
              class="flex h-14 w-14 flex-col items-center justify-center gap-1 rounded-2xl border transition"
              :class="state.selectedElementId === 'background' ? 'border-primary bg-primary/10 text-primary' : 'border-base-300 bg-base-100/80 hover:border-primary/50 hover:bg-primary/10'"
              @click="state.selectedElementId = 'background'; activePropertyPanel = 'color'; textPanelOpen = false; imagePanelOpen = false; shapePanelOpen = false; optionsPanelOpen = true"
              title="Ajustar Fondo"
            >
              <span class="flex h-10 w-10 items-center justify-center rounded-xl text-xl"
                :class="state.selectedElementId === 'background' ? 'bg-primary/20' : 'bg-base-200'">
                <Icon icon="mdi:palette-outline" class="text-xl" />
              </span>
              <span class="text-[9px] font-medium">Fondo</span>
            </button>
          </div>

          <!-- Panel de Opciones (condicionalmente visible) -->
          <aside v-if="optionsPanelOpen" data-editor-keep-selection="true" class="relative z-40 h-full w-80 border-r border-base-300 bg-base-100 p-5 overflow-y-auto">
            <div class="space-y-5">
              <div>
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Panel contextual</p>
                    <h3 class="mt-2 text-xl font-semibold text-base-content">{{ hasSelection && activePropertyPanel ? activePropertyTitle : 'Elementos' }}</h3>
                    <p v-if="hasSelection && activePropertyPanel" class="mt-2 text-sm leading-6 text-base-content/75">Elige una propiedad arriba para ver sus opciones.</p>
                  </div>
                  <div class="flex gap-2">
                    <button
                      type="button"
                      class="btn btn-ghost btn-sm btn-circle"
                      aria-label="Cerrar panel de opciones"
                      @click="optionsPanelOpen = false; activePropertyPanel = null; textPanelOpen = false; imagePanelOpen = false; shapePanelOpen = false"
                    >
                      <Icon icon="mdi:close" class="text-lg" />
                    </button>
                  </div>
                </div>
              </div>

              <!-- Panel de inserción (siempre visible cuando no hay selección) -->
              <div v-if="!hasSelection || !activePropertyPanel" class="space-y-3">
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
                        <p class="text-xs text-base-content/60">Puedes usar color sólido o degradado.</p>
                      </div>
                      <span class="rounded-full border border-base-300 bg-base-100 px-2 py-1 text-[11px] font-medium text-base-content/70">
                        {{ state.elementLayout.background?.fillMode === 'gradient' ? 'degradado' : (state.elementLayout.background?.backgroundColor || 'transparent') }}
                      </span>
                    </div>

                    <div class="mt-3 flex flex-wrap gap-2">
                      <button
                        type="button"
                        class="btn btn-sm rounded-full"
                        :class="state.elementLayout.background?.fillMode !== 'gradient' ? 'btn-primary' : 'btn-outline'"
                        @click="state.elementLayout.background.fillMode = 'solid'"
                      >
                        Sólido
                      </button>
                      <button
                        type="button"
                        class="btn btn-sm rounded-full"
                        :class="state.elementLayout.background?.fillMode === 'gradient' ? 'btn-primary' : 'btn-outline'"
                        @click="state.elementLayout.background.fillMode = 'gradient'"
                      >
                        Degradado
                      </button>
                    </div>

                    <div v-if="state.elementLayout.background?.fillMode !== 'gradient'" class="space-y-4">
                      <div class="mt-4 grid grid-cols-6 gap-2">
                        <button
                          v-for="color in backgroundOptions"
                          :key="'bg-color-' + color"
                          type="button"
                          class="h-9 w-9 rounded-full transition hover:scale-105"
                          :class="state.elementLayout.background?.backgroundColor === color ? 'ring-2 ring-primary ring-offset-2 ring-offset-base-100' : 'ring-1 ring-slate-200 dark:ring-slate-700'"
                          :style="{ backgroundColor: color === 'transparent' ? '#ffffff' : color }"
                          :title="color"
                          @click="state.elementLayout.background.fillMode = 'solid'; state.elementLayout.background.backgroundColor = color"
                        ></button>
                      </div>
                      <div class="mt-4 grid gap-3 sm:grid-cols-[auto_1fr] sm:items-center">
                        <label class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Color custom</label>
                        <div class="flex items-center gap-2">
                          <input
                            type="color"
                            class="h-10 w-12 cursor-pointer rounded-xl border border-base-300 bg-base-100 p-1"
                            :value="normalizePickerColor(state.elementLayout.background?.backgroundColor || '#4338ca', '#4338ca')"
                            @input="state.elementLayout.background.fillMode = 'solid'; state.elementLayout.background.backgroundColor = $event.target.value"
                          />
                          <input
                            :value="state.elementLayout.background?.backgroundColor"
                            type="text"
                            placeholder="#4338ca"
                            class="input input-bordered input-sm flex-1"
                            @input="state.elementLayout.background.fillMode = 'solid'; state.elementLayout.background.backgroundColor = $event.target.value"
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
                          :class="state.elementLayout.background?.gradientStart === preset.start && state.elementLayout.background?.gradientEnd === preset.end ? 'ring-2 ring-primary ring-offset-2 ring-offset-base-100' : ''"
                          :style="{ background: `linear-gradient(135deg, ${preset.start}, ${preset.end})` }"
                          @click="applyGradientPreset('background', preset.start, preset.end)"
                        ></button>
                      </div>
                      <div class="grid gap-3 sm:grid-cols-2">
                        <div class="flex items-center gap-2">
                          <span class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Inicio</span>
                          <input
                            type="color"
                            class="h-10 w-12 cursor-pointer rounded-xl border border-base-300 bg-base-100 p-1"
                            :value="normalizePickerColor(state.elementLayout.background?.gradientStart || '#0ea5e9', '#0ea5e9')"
                            @input="state.elementLayout.background.gradientStart = $event.target.value"
                          />
                        </div>
                        <div class="flex items-center gap-2">
                          <span class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Final</span>
                          <input
                            type="color"
                            class="h-10 w-12 cursor-pointer rounded-xl border border-base-300 bg-base-100 p-1"
                            :value="normalizePickerColor(state.elementLayout.background?.gradientEnd || '#8b5cf6', '#8b5cf6')"
                            @input="state.elementLayout.background.gradientEnd = $event.target.value"
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
                            :class="state.elementLayout.background?.gradientAngle === direction.value
                              ? 'border-primary bg-primary/15 text-primary'
                              : 'border-base-300/70 bg-base-100/80 text-base-content/70 hover:border-primary/50 hover:text-primary'"
                            :title="direction.label"
                            :aria-label="direction.label"
                            @click="state.elementLayout.background.gradientAngle = direction.value"
                          >
                            <Icon :icon="direction.icon" class="text-xl" />
                          </button>
                        </div>
                      </div>
                      <div class="flex flex-wrap gap-2">
                        <button type="button" class="btn btn-outline btn-sm rounded-full" @click="swapGradientStops('background')">Alternar inicio/fin</button>
                        <div class="h-8 flex-1 min-w-28 rounded-full border border-base-300/70" :style="{ background: `linear-gradient(${state.elementLayout.background?.gradientAngle || 135}deg, ${state.elementLayout.background?.gradientStart || '#0ea5e9'}, ${state.elementLayout.background?.gradientEnd || '#8b5cf6'})` }"></div>
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
                  <template v-if="hasTextSelection">
                    <template v-for="(effectRow, rowIndex) in textEffectRows" :key="`effect-row-${rowIndex}`">
                      <div class="grid grid-cols-3 gap-2">
                        <button
                          v-for="effect in effectRow"
                          :key="effect.id"
                          type="button"
                          class="text-center transition"
                          :style="{ fontFamily: textEffectCardFontFamily }"
                          @click="setTextEffect(effect.id)"
                        >
                          <span
                            class="inline-flex h-18 w-full items-center justify-center rounded-xl border transition"
                            :class="activeTextEffectId === effect.id
                              ? 'border-primary bg-white ring-1 ring-primary/35'
                              : 'border-base-300 bg-white hover:border-primary/45 hover:bg-white'"
                          >
                            <span :style="textEffectPreviewStyle(effect.id)">Ag</span>
                          </span>
                          <span class="mt-1.5 block text-[11px] font-medium text-base-content/85">{{ effect.label }}</span>
                        </button>
                        <div v-for="emptyIndex in Math.max(0, 3 - effectRow.length)" :key="`effect-row-${rowIndex}-empty-${emptyIndex}`"></div>
                      </div>

                      <div
                        v-if="activeTextEffectId !== 'none' && effectRow.some((effect) => effect.id === activeTextEffectId)"
                        class="flex flex-wrap items-end gap-3 rounded-2xl border border-base-300/70 bg-base-100/60 p-3"
                      >
                      <div v-if="activeTextEffectId === 'shadow'" class="min-w-55 flex-1 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Direccion</label>
                        <div class="flex items-center gap-2">
                          <input v-model.number="selectedElement.shadowAngle" type="range" min="0" max="360" step="1" class="range range-primary flex-1" />
                          <input v-model.number="selectedElement.shadowAngle" type="number" min="0" max="360" step="1" class="input input-bordered input-sm w-20" />
                        </div>
                      </div>
                      <div v-if="activeTextEffectId === 'shadow'" class="min-w-55 flex-1 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Compensacion</label>
                        <div class="flex items-center gap-2">
                          <input v-model.number="selectedElement.shadowOffset" type="range" min="0" max="100" step="1" class="range range-primary flex-1" />
                          <input v-model.number="selectedElement.shadowOffset" type="number" min="0" max="100" step="1" class="input input-bordered input-sm w-20" />
                        </div>
                      </div>
                      <div v-if="activeTextEffectId === 'shadow'" class="min-w-55 flex-1 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Desenfoque</label>
                        <div class="flex items-center gap-2">
                          <input v-model.number="selectedElement.shadowBlur" type="range" min="0" max="100" step="1" class="range range-primary flex-1" />
                          <input v-model.number="selectedElement.shadowBlur" type="number" min="0" max="100" step="1" class="input input-bordered input-sm w-20" />
                        </div>
                      </div>
                      <div v-if="['shadow', 'shadow1', 'shadow2'].includes(activeTextEffectId)" class="min-w-55 flex-1 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Transparencia</label>
                        <div class="flex items-center gap-2">
                          <input v-model.number="selectedElement.shadowOpacity" type="range" min="0" max="100" step="1" class="range range-primary flex-1" />
                          <input v-model.number="selectedElement.shadowOpacity" type="number" min="0" max="100" step="1" class="input input-bordered input-sm w-20" />
                        </div>
                      </div>
                      <div v-if="['shadow', 'shadow1', 'shadow2'].includes(activeTextEffectId)" class="w-23 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Color</label>
                        <div class="flex h-10 items-center justify-center rounded-xl border border-base-300 bg-base-100 p-1">
                          <input
                            type="color"
                            class="h-full w-full cursor-pointer rounded-lg bg-base-100"
                            :value="normalizePickerColor(selectedElement.shadowColor || '#000000', '#000000')"
                            @input="selectedElement.shadow = true; setSelectedColor('shadowColor', $event.target.value)"
                          />
                        </div>
                      </div>

                      <div v-if="activeTextEffectId === 'echo'" class="min-w-55 flex-1 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Direccion</label>
                        <div class="flex items-center gap-2">
                          <input v-model.number="selectedElement.shadowAngle" type="range" min="0" max="360" step="1" class="range range-primary flex-1" />
                          <input v-model.number="selectedElement.shadowAngle" type="number" min="0" max="360" step="1" class="input input-bordered input-sm w-20" />
                        </div>
                      </div>
                      <div v-if="activeTextEffectId === 'echo'" class="min-w-55 flex-1 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Compensacion</label>
                        <div class="flex items-center gap-2">
                          <input v-model.number="selectedElement.shadowOffset" type="range" min="0" max="100" step="1" class="range range-primary flex-1" />
                          <input v-model.number="selectedElement.shadowOffset" type="number" min="0" max="100" step="1" class="input input-bordered input-sm w-20" />
                        </div>
                      </div>
                      <div v-if="activeTextEffectId === 'echo'" class="w-23 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Color</label>
                        <div class="flex h-10 items-center justify-center rounded-xl border border-base-300 bg-base-100 p-1">
                          <input
                            type="color"
                            class="h-full w-full cursor-pointer rounded-lg bg-base-100"
                            :value="normalizePickerColor(selectedElement.shadowColor || '#000000', '#000000')"
                            @input="selectedElement.shadow = true; setSelectedColor('shadowColor', $event.target.value)"
                          />
                        </div>
                      </div>

                      <div v-if="activeTextEffectId === 'glow'" class="min-w-55 flex-1 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Brillo</label>
                        <div class="flex items-center gap-2">
                          <input v-model.number="selectedElement.neonIntensity" type="range" min="0" max="100" step="1" class="range range-primary flex-1" />
                          <input v-model.number="selectedElement.neonIntensity" type="number" min="0" max="100" step="1" class="input input-bordered input-sm w-20" />
                        </div>
                      </div>
                      <div v-if="activeTextEffectId === 'glow'" class="w-23 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Color</label>
                        <div class="flex h-10 items-center justify-center rounded-xl border border-base-300 bg-base-100 p-1">
                          <input
                            type="color"
                            class="h-full w-full cursor-pointer rounded-lg bg-base-100"
                            :value="normalizePickerColor(selectedElement.neonColor || '#8b5cf6', '#8b5cf6')"
                            @input="setSelectedColor('neonColor', $event.target.value)"
                          />
                        </div>
                      </div>

                      <div v-if="activeTextEffectId === 'distort'" class="min-w-55 flex-1 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Direccion</label>
                        <div class="flex items-center gap-2">
                          <input v-model.number="selectedElement.shadowAngle" type="range" min="0" max="360" step="1" class="range range-primary flex-1" />
                          <input v-model.number="selectedElement.shadowAngle" type="number" min="0" max="360" step="1" class="input input-bordered input-sm w-20" />
                        </div>
                      </div>
                      <div v-if="activeTextEffectId === 'distort'" class="min-w-55 flex-1 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Compensacion</label>
                        <div class="flex items-center gap-2">
                          <input v-model.number="selectedElement.shadowOffset" type="range" min="0" max="20" step="1" class="range range-primary flex-1" />
                          <input v-model.number="selectedElement.shadowOffset" type="number" min="0" max="20" step="1" class="input input-bordered input-sm w-20" />
                        </div>
                      </div>
                      <div v-if="activeTextEffectId === 'distort'" class="w-23 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Color 1</label>
                        <div class="flex h-10 items-center justify-center rounded-xl border border-base-300 bg-base-100 p-1">
                          <input
                            type="color"
                            class="h-full w-full cursor-pointer rounded-lg bg-base-100"
                            :value="normalizePickerColor(selectedElement.shadowColor || '#f0f', '#f0f')"
                            @input="selectedElement.shadow = true; setSelectedColor('shadowColor', $event.target.value)"
                          />
                        </div>
                      </div>
                      <div v-if="activeTextEffectId === 'distort'" class="w-23 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Color 2</label>
                        <div class="flex h-10 items-center justify-center rounded-xl border border-base-300 bg-base-100 p-1">
                          <input
                            type="color"
                            class="h-full w-full cursor-pointer rounded-lg bg-base-100"
                            :value="normalizePickerColor(selectedElement.neonColor || '#0ff', '#0ff')"
                            @input="setSelectedColor('neonColor', $event.target.value)"
                          />
                        </div>
                      </div>

                      <div v-if="activeTextEffectId === 'misaligned'" class="min-w-55 flex-1 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Grosor</label>
                        <div class="flex items-center gap-2">
                          <input v-model.number="selectedElement.contourWidth" type="range" min="1" max="100" step="1" class="range range-primary flex-1" />
                          <input v-model.number="selectedElement.contourWidth" type="number" min="1" max="100" step="1" class="input input-bordered input-sm w-20" />
                        </div>
                      </div>
                      <div v-if="activeTextEffectId === 'misaligned'" class="min-w-55 flex-1 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Compensacion</label>
                        <div class="flex items-center gap-2">
                          <input v-model.number="selectedElement.shadowOffset" type="range" min="0" max="100" step="1" class="range range-primary flex-1" />
                          <input v-model.number="selectedElement.shadowOffset" type="number" min="0" max="100" step="1" class="input input-bordered input-sm w-20" />
                        </div>
                      </div>
                      <div v-if="activeTextEffectId === 'misaligned'" class="min-w-55 flex-1 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Direccion</label>
                        <div class="flex items-center gap-2">
                          <input v-model.number="selectedElement.shadowAngle" type="range" min="0" max="360" step="1" class="range range-primary flex-1" />
                          <input v-model.number="selectedElement.shadowAngle" type="number" min="0" max="360" step="1" class="input input-bordered input-sm w-20" />
                        </div>
                      </div>
                      <div v-if="activeTextEffectId === 'misaligned'" class="w-23 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Color</label>
                        <div class="flex h-10 items-center justify-center rounded-xl border border-base-300 bg-base-100 p-1">
                          <input
                            type="color"
                            class="h-full w-full cursor-pointer rounded-lg bg-base-100"
                            :value="normalizePickerColor(selectedElement.shadowColor || '#000000', '#000000')"
                            @input="selectedElement.shadow = true; setSelectedColor('shadowColor', $event.target.value)"
                          />
                        </div>
                      </div>

                      <div v-if="activeTextEffectId === 'neon'" class="min-w-55 flex-1 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Intensidad</label>
                        <div class="flex items-center gap-2">
                          <input v-model.number="selectedElement.neonIntensity" type="range" min="0" max="100" step="1" class="range range-primary flex-1" />
                          <input v-model.number="selectedElement.neonIntensity" type="number" min="0" max="100" step="1" class="input input-bordered input-sm w-20" />
                        </div>
                      </div>

                      <div v-if="activeTextEffectId === 'outline'" class="min-w-55 flex-1 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Grosor</label>
                        <div class="flex items-center gap-2">
                          <input v-model.number="selectedElement.contourWidth" type="range" min="1" max="100" step="1" class="range range-primary flex-1" />
                          <input v-model.number="selectedElement.contourWidth" type="number" min="1" max="100" step="1" class="input input-bordered input-sm w-20" />
                        </div>
                      </div>
                      <div v-if="activeTextEffectId === 'outline'" class="w-23 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Color</label>
                        <div class="flex h-10 items-center justify-center rounded-xl border border-base-300 bg-base-100 p-1">
                          <input
                            type="color"
                            class="h-full w-full cursor-pointer rounded-lg bg-base-100"
                            :value="normalizePickerColor(selectedElement.contourColor || '#7c3aed', '#7c3aed')"
                            @input="selectedElement.border = true; setSelectedColor('contourColor', $event.target.value)"
                          />
                        </div>
                      </div>

                      <div v-if="activeTextEffectId === 'hollow'" class="min-w-55 flex-1 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Grosor</label>
                        <div class="flex items-center gap-2">
                          <input v-model.number="selectedElement.contourWidth" type="range" min="1" max="100" step="1" class="range range-primary flex-1" />
                          <input v-model.number="selectedElement.contourWidth" type="number" min="1" max="100" step="1" class="input input-bordered input-sm w-20" />
                        </div>
                      </div>

                      <div v-if="activeTextEffectId === 'background'" class="min-w-55 flex-1 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Redondez</label>
                        <div class="flex items-center gap-2">
                          <input v-model.number="selectedElement.backgroundRoundness" type="range" min="0" max="100" step="1" class="range range-primary flex-1" />
                          <input v-model.number="selectedElement.backgroundRoundness" type="number" min="0" max="100" step="1" class="input input-bordered input-sm w-20" />
                        </div>
                      </div>
                      <div v-if="activeTextEffectId === 'background'" class="min-w-55 flex-1 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Extender</label>
                        <div class="flex items-center gap-2">
                          <input v-model.number="selectedElement.backgroundPadding" type="range" min="0" max="100" step="1" class="range range-primary flex-1" />
                          <input v-model.number="selectedElement.backgroundPadding" type="number" min="0" max="100" step="1" class="input input-bordered input-sm w-20" />
                        </div>
                      </div>
                      <div v-if="activeTextEffectId === 'background'" class="min-w-55 flex-1 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Transparencia</label>
                        <div class="flex items-center gap-2">
                          <input v-model.number="selectedElement.backgroundOpacity" type="range" min="0" max="100" step="1" class="range range-primary flex-1" />
                          <input v-model.number="selectedElement.backgroundOpacity" type="number" min="0" max="100" step="1" class="input input-bordered input-sm w-20" />
                        </div>
                      </div>
                      <div v-if="activeTextEffectId === 'background'" class="w-23 space-y-2">
                        <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Color</label>
                        <div class="flex h-10 items-center justify-center rounded-xl border border-base-300 bg-base-100 p-1">
                          <input
                            type="color"
                            class="h-full w-full cursor-pointer rounded-lg bg-base-100"
                            :value="normalizePickerColor(selectedElement.backgroundColor, '#ddd6fe')"
                            @input="setSelectedColor('backgroundColor', $event.target.value)"
                          />
                        </div>
                      </div>
                      </div>
                    </template>

                    <button
                      v-if="activeTextEffectId !== 'none'"
                      type="button"
                      class="btn btn-primary btn-block mt-2 rounded-2xl text-sm font-semibold shadow-md"
                      @click="setTextEffect('none')"
                    >
                      Quitar efecto
                    </button>
                  </template>

                  <template v-else>
                    <p class="text-sm text-base-content/70">Los efectos tipo Canva estan disponibles para elementos de texto.</p>
                  </template>
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

          <div class="canvas-grid h-full overflow-auto bg-slate-100 px-6 pt-12 pb-6 dark:bg-slate-950 sm:px-10 sm:pt-16 sm:pb-10" :style="canvasGridStyle">
            <div class="mx-auto bg-white p-4 shadow-2xl dark:bg-slate-900" :style="[canvasFrameStyle, canvasZoomStyle]" :class="state.selectedElementId === 'background' ? 'ring-2 ring-primary' : ''">
              <div ref="canvasRef" class="relative overflow-visible p-7 text-white select-none touch-none" :style="{ ...canvasBackgroundStyle, ...canvasElementStyle }" @pointerdown="handleCanvasPointerDown">

                <div
                  v-for="item in editorElements"
                  :key="item.id"
                  data-editor-element="true"
                  :data-editor-id="item.id"
                  class="absolute p-0 text-left"
                  :style="elementBoxStyle(item.id)"
                  :class="isElementSelected(item.id)
                    ? (editingElementId === item.id
                        ? 'border-2 border-solid border-cyan-300 bg-white/10 shadow-[0_0_0_3px_rgba(103,232,249,.35)] editor-editing-pulse'
                        : (drag.active && drag.elementId === item.id
                            ? 'border-2 border-dashed border-cyan-300 bg-white/10 shadow-[0_0_0_3px_rgba(103,232,249,.18)]'
                            : 'border-2 border-dashed border-cyan-300 bg-white/8 shadow-[0_0_0_3px_rgba(103,232,249,.18)]'))
                    : 'z-10 border border-transparent hover:border-white/20'"
                  @click="handleElementClick($event, item.id)"
                  @dblclick="beginTextEdit(item.id)"
                  @pointerdown="handleElementPointerDown($event, item.id)"
                >
                  <div class="relative" :class="item.type === 'text' ? '' : 'h-full w-full'" :style="elementContentStyle(item.id)">
                    <template v-if="item.type === 'text'">
                      <RichTextEditor
                        :ref="(el) => { if (el) richEditorRefs[item.id] = el; else delete richEditorRefs[item.id]; }"
                        :paragraph-styles="state.elementLayout[item.id].paragraphStyles ?? []"
                        :text="item.text ?? ''"
                        :editable="editingElementId === item.id"
                        :editor-style="richEditorContainerStyle(item.id)"
                        :color-override="neonColorOverride(item.id)"
                        :transparent-fill="!!state.elementLayout[item.id]?.hollowText"
                        @update:text="onRichEditorTextUpdate(item.id, $event)"
                        @update:paragraph-styles="onRichEditorStylesUpdate(item.id, $event)"
                        @selection-change="onRichEditorSelectionChange(item.id, $event)"
                        @blur="onRichEditorBlur(item.id, $event)"
                        @keydown.escape.stop="cancelTextEdit"
                        @keydown.ctrl.enter.stop="commitTextEdit"
                        @keydown.meta.enter.stop="commitTextEdit"
                        @pointerdown.stop="editingElementId === item.id ? null : handleElementPointerDown($event, item.id)"
                        @mousedown.stop
                        @dblclick.stop="beginTextEdit(item.id)"
                        @click.stop="editingElementId === item.id ? null : handleElementClick($event, item.id)"
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
                <div
                  v-if="activeSelectionIds.length && state.selectedElementId !== 'background'"
                  data-editor-control="true"
                  class="pointer-events-none absolute"
                  :style="selectedActionBarStyle"
                >
                  <div class="pointer-events-auto card glass soft-shadow border border-base-300/70 bg-base-100/90 text-base-content" :style="controlZoomStyle">
                    <div class="flex items-center gap-1 p-1.5">
                    <button
                      v-if="multiSelectionIds.length > 1"
                      data-editor-control="true"
                      type="button"
                      class="btn btn-ghost btn-sm font-semibold"
                      title="Agrupar elementos"
                      @pointerdown.stop="markEditorControlInteraction"
                      @click.stop="groupSelectedElements"
                    >
                      agrupar
                    </button>
                    <button
                      v-if="selectedElementType === 'text'"
                      data-editor-control="true"
                      type="button"
                      class="btn btn-ghost btn-sm"
                      title="Editar texto"
                      @pointerdown.stop="markEditorControlInteraction"
                      @click.stop="editSelectedTextElement"
                    >
                      <Icon icon="ph:pencil-simple-bold" class="text-base" />
                    </button>
                    <button
                      data-editor-control="true"
                      type="button"
                      class="btn btn-ghost btn-sm"
                      title="Clonar elemento"
                      @pointerdown.stop="markEditorControlInteraction"
                      @click.stop="cloneCurrentSelection"
                    >
                      <Icon icon="ph:copy-bold" class="text-base" />
                    </button>
                    <button
                      data-editor-control="true"
                      type="button"
                      class="btn btn-ghost btn-sm text-error hover:bg-error/10"
                      title="Eliminar elemento"
                      @pointerdown.stop="markEditorControlInteraction"
                      @click.stop="deleteCurrentSelection"
                    >
                      <Icon icon="ph:trash-bold" class="text-base" />
                    </button>
                    </div>
                  </div>
                </div>

                <div v-if="activeSelectionIds.length && state.selectedElementId !== 'background'" data-editor-control="true" class="pointer-events-none absolute" :style="selectedOverlayStyle">
                  <button
                    v-if="overlayControlTargetId && (isGroupSelection || !hasMultiSelection)"
                    data-editor-control="true"
                    type="button"
                    class="pointer-events-auto absolute -bottom-12 left-1/2 z-40 flex h-8 w-8 -translate-x-1/2 items-center justify-center rounded-full border-2 border-white bg-cyan-300 text-slate-950 shadow-md touch-none"
                    :style="controlZoomStyle"
                    title="Girar elemento"
                    @pointerdown="startRotate($event, overlayControlTargetId)"
                    @dblclick.stop.prevent="resetRotation(overlayControlTargetId)"
                  >
                    <Icon icon="ph:arrow-clockwise-bold" class="text-lg" />
                  </button>
                  <span
                    v-if="overlayControlTargetId && (isGroupSelection || (!hasMultiSelection && selectedElementType !== 'text'))"
                    data-editor-control="true"
                    class="pointer-events-auto absolute left-1/2 z-30 -translate-x-1/2 cursor-ns-resize rounded-full border-2 border-white bg-cyan-300 touch-none"
                    :style="{ top: selectedHandleMetrics.barOffset, width: selectedHandleMetrics.barLength, height: selectedHandleMetrics.barThickness, ...controlZoomStyle }"
                    @pointerdown="startResize($event, overlayControlTargetId, 'n-width')"
                  ></span>
                  <span
                    v-if="overlayControlTargetId && (isGroupSelection || (!hasMultiSelection && selectedElementType !== 'text'))"
                    data-editor-control="true"
                    class="pointer-events-auto absolute left-1/2 z-30 -translate-x-1/2 cursor-ns-resize rounded-full border-2 border-white bg-cyan-300 touch-none"
                    :style="{ bottom: selectedHandleMetrics.barOffset, width: selectedHandleMetrics.barLength, height: selectedHandleMetrics.barThickness, ...controlZoomStyle }"
                    @pointerdown="startResize($event, overlayControlTargetId, 's-width')"
                  ></span>
                  <span v-if="overlayControlTargetId && (isGroupSelection || !hasMultiSelection)" data-editor-control="true" class="pointer-events-auto absolute top-1/2 z-30 -translate-y-1/2 cursor-ew-resize rounded-full border-2 border-white bg-cyan-300 touch-none" :style="{ left: selectedHandleMetrics.sideOffset, width: selectedHandleMetrics.sideThickness, height: selectedHandleMetrics.sideLength, ...controlZoomStyle }" @pointerdown="startResize($event, overlayControlTargetId, 'w')"></span>
                  <span v-if="overlayControlTargetId && (isGroupSelection || !hasMultiSelection)" data-editor-control="true" class="pointer-events-auto absolute top-1/2 z-30 -translate-y-1/2 cursor-ew-resize rounded-full border-2 border-white bg-cyan-300 touch-none" :style="{ right: selectedHandleMetrics.sideOffset, width: selectedHandleMetrics.sideThickness, height: selectedHandleMetrics.sideLength, ...controlZoomStyle }" @pointerdown="startResize($event, overlayControlTargetId, 'e')"></span>
                  <span v-if="overlayControlTargetId && (isGroupSelection || !hasMultiSelection)" data-editor-control="true" class="pointer-events-auto absolute z-30 cursor-nwse-resize rounded-full border-2 border-white bg-cyan-300 touch-none" :style="{ left: selectedHandleMetrics.cornerOffset, top: selectedHandleMetrics.cornerOffset, width: selectedHandleMetrics.cornerSize, height: selectedHandleMetrics.cornerSize, ...controlZoomStyle }" @pointerdown="startResize($event, overlayControlTargetId, 'nw')"></span>
                  <span v-if="overlayControlTargetId && (isGroupSelection || !hasMultiSelection)" data-editor-control="true" class="pointer-events-auto absolute z-30 cursor-nesw-resize rounded-full border-2 border-white bg-cyan-300 touch-none" :style="{ right: selectedHandleMetrics.cornerOffset, top: selectedHandleMetrics.cornerOffset, width: selectedHandleMetrics.cornerSize, height: selectedHandleMetrics.cornerSize, ...controlZoomStyle }" @pointerdown="startResize($event, overlayControlTargetId, 'ne')"></span>
                  <span v-if="overlayControlTargetId && (isGroupSelection || !hasMultiSelection)" data-editor-control="true" class="pointer-events-auto absolute z-30 cursor-nesw-resize rounded-full border-2 border-white bg-cyan-300 touch-none" :style="{ left: selectedHandleMetrics.cornerOffset, bottom: selectedHandleMetrics.cornerOffset, width: selectedHandleMetrics.cornerSize, height: selectedHandleMetrics.cornerSize, ...controlZoomStyle }" @pointerdown="startResize($event, overlayControlTargetId, 'sw')"></span>
                  <span v-if="overlayControlTargetId && (isGroupSelection || !hasMultiSelection)" data-editor-control="true" class="pointer-events-auto absolute z-30 cursor-nwse-resize rounded-full border-2 border-white bg-cyan-300 touch-none" :style="{ right: selectedHandleMetrics.cornerOffset, bottom: selectedHandleMetrics.cornerOffset, width: selectedHandleMetrics.cornerSize, height: selectedHandleMetrics.cornerSize, ...controlZoomStyle }" @pointerdown="startResize($event, overlayControlTargetId, 'se')"></span>
                </div>
                <div v-if="selectionMarquee.active" class="pointer-events-none absolute border border-cyan-200/90 bg-cyan-200/20" :style="marqueeRectStyle"></div>
                <div class="pointer-events-none absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-cyan-200/30"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
    </div>
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
