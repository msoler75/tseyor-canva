<script setup>
import axios from 'axios';
import { Icon } from '@iconify/vue';
import { usePage } from '@inertiajs/vue3';
import DesignerLayout from '../../Layouts/DesignerLayout.vue';
import EditorTopBar from '../../Components/designer/EditorTopBar.vue';
import EditorInsertSidebar from '../../Components/designer/EditorInsertSidebar.vue';
import EditorContextPanel from '../../Components/designer/EditorContextPanel.vue';
import EditorCanvasStage from '../../Components/designer/EditorCanvasStage.vue';
import SelectionOverlay from '../../Components/designer/SelectionOverlay.vue';
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { objectiveRecommendations } from '../../data/designer';
import { useDesignerState } from '../../composables/useDesignerState';
import { flushDesignerStatePersistence } from '../../composables/useDesignerState';
import { useEditorHistory } from '../../composables/useEditorHistory';
import { useEditorStyles } from '../../composables/useEditorStyles';
import { useEditorSelection } from '../../composables/useEditorSelection';
import { useEditorInteractions } from '../../composables/useEditorInteractions';
import { applyFormatToDimensions, buildCoverImageStyle, parseSizeDetail } from '../../utils/editorShared';
import { dataUrlToFile, extractImageFilesFromDataTransfer, fileToDataUrl, hasFilesInTransfer, isDataImageUrl, isEditableTarget, optimizeImageFile } from '../../utils/imageUploads';

defineProps({ currentStep: String, steps: Array, navigation: Object });
const page = usePage();
const state = useDesignerState();
if (!state.customElements || Array.isArray(state.customElements)) {
  state.customElements = Object.fromEntries(Object.entries(state.customElements ?? {}));
}
if (!state.userUploadedImages) {
  state.userUploadedImages = [];
}
const uploadEndpoint = computed(() => page.props.designer?.endpoints?.upload ?? '/designer/uploads');
const imageUploadProcessingConfig = computed(() => page.props.designer?.imageUploads ?? {
  maxWidth: 2400,
  maxHeight: 2400,
  jpegQuality: 95,
  webpQuality: 95,
});
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
const fileDragActive = ref(false);
const backgroundDropPreview = ref(false);
const toolbarPosition = reactive({ x: 0, y: 3 });
const toolbarDrag = reactive({ active: false, pointerId: null, startX: 0, startY: 0, originX: 0, originY: 0 });
const uploadProgressByAssetId = reactive({});
const activeUploadAssetIds = new Set();
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
  '#000000', '#545454', '#737373', '#a6a6a6', '#b4b4b4', '#d9d9d9', '#ffffff',
  '#ff3131', '#ff5757', '#ff66c4', '#e2a9f1', '#cb6ce6', '#8c52ff', '#5e17eb',
  '#0097b2', '#0cc0df', '#5ce1e6', '#38b6ff', '#5170ff', '#004aad', '#1800ad',
  '#00bf63', '#7ed957', '#c1ff72', '#ffde59', '#ffbd59', '#ff914d', '#ff751f',
];
const backgroundOptions = [
  'transparent',
  ...colorOptions,
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
  { id: 'g9', start: '#1d4ed8', end: '#06b6d4' },
  { id: 'g10', start: '#7c2d12', end: '#f97316' },
  { id: 'g11', start: '#be123c', end: '#fb7185' },
  { id: 'g12', start: '#166534', end: '#86efac' },
];
const shapeGradientDirections = [
  { value: 0, label: 'Arriba → abajo', icon: 'ph:arrow-down' },
  { value: 90, label: 'Izquierda → derecha', icon: 'ph:arrow-right' },
  { value: 135, label: 'Diagonal ↘', icon: 'ph:arrow-down-right' },
  { value: 45, label: 'Diagonal ↗', icon: 'ph:arrow-up-right' },
  { value: 180, label: 'Abajo → arriba', icon: 'ph:arrow-up' },
  { value: 270, label: 'Derecha → izquierda', icon: 'ph:arrow-left' },
];
const normalizeHexCandidate = (value) => {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  if (trimmed === 'transparent') return null;
  if (/^#[\da-f]{6}$/i.test(trimmed)) return trimmed.toLowerCase();
  if (/^#[\da-f]{3}$/i.test(trimmed)) {
    return `#${trimmed[1]}${trimmed[1]}${trimmed[2]}${trimmed[2]}${trimmed[3]}${trimmed[3]}`.toLowerCase();
  }
  return null;
};
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
const imagePropertyTabs = [
  { id: 'color', icon: 'mdi:palette-outline', label: 'Color', class: 'order-first' },
  { id: 'border', icon: 'radix-icons:border-width', title: 'Borde', class: 'order-first' },
  { id: 'crop', icon: 'ph:crop-bold', title: 'Recortar', class: 'order-last' },
  { id: 'rotate', icon: '', label: 'Girar', class: 'order-last' },
  { id: 'opacity', icon: 'carbon:opacity', class: 'order-last' },
  { id: 'effects', label: 'Efectos', class: 'order-last' },
  { id: 'arrange', label: 'Posición', class: 'order-last' },
  { id: 'set-as-background', icon: 'tabler:background', title: 'Fijar como fondo', class: 'order-last' },
];
const shapePropertyTabs = [
  { id: 'color', icon: 'mdi:palette-outline', label: 'Color', class: 'order-first' },
  { id: 'border', icon: 'radix-icons:border-width', title: 'Borde', class: 'order-first' },
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

const baseElementLabels = {
  background: 'fondo',
  title: 'titulo',
  subtitle: 'subtitulo',
  meta: 'fecha y hora',
  contact: 'contacto',
  extra: 'texto adicional',
};

const contentFieldLabels = {
  title: 'titulo',
  subtitle: 'subtitulo',
  date: 'fecha',
  time: 'hora',
  location: 'ubicacion',
  platform: 'plataforma',
  teacher: 'ponente',
  price: 'precio',
  contact: 'contacto',
  extra: 'texto adicional',
};

const {
  historyApplying,
  canUndo,
  canRedo,
  undoActionLabel,
  redoActionLabel,
  pushHistorySnapshot,
  scheduleHistorySnapshot,
  performUndo,
  performRedo,
  replaceImageAssetSource,
  mutateWithoutHistory,
} = useEditorHistory({
  state,
  editingElementId,
  commitTextEdit: () => commitTextEdit(),
  clearSelection: () => clearSelection(),
  baseElementLabels,
  contentFieldLabels,
});

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
const designColorOptions = computed(() => {
  const seen = new Set();
  const collected = [];
  const pushColor = (value) => {
    const normalized = normalizeHexCandidate(value);
    if (!normalized || seen.has(normalized)) return;
    seen.add(normalized);
    collected.push(normalized);
  };

  Object.values(state.elementLayout ?? {}).forEach((layout) => {
    if (!layout || typeof layout !== 'object') return;
    [
      layout.backgroundColor,
      layout.color,
      layout.gradientStart,
      layout.gradientEnd,
      layout.contourColor,
      layout.shadowColor,
      layout.neonColor,
      layout.imageTintColor,
      layout.bubbleColor,
    ].forEach(pushColor);

    (layout.paragraphStyles ?? []).forEach((style) => pushColor(style?.color));
  });

  return collected;
});
const designGradientOptions = computed(() => {
  const seen = new Set();
  const collected = [];
  const pushGradient = (start, end) => {
    const normalizedStart = normalizeHexCandidate(start);
    const normalizedEnd = normalizeHexCandidate(end);
    if (!normalizedStart || !normalizedEnd) return;
    const key = `${normalizedStart}-${normalizedEnd}`;
    if (seen.has(key)) return;
    seen.add(key);
    collected.push({ id: `design-${seen.size}`, start: normalizedStart, end: normalizedEnd });
  };

  Object.values(state.elementLayout ?? {}).forEach((layout) => {
    if (layout?.fillMode === 'gradient') {
      pushGradient(layout.gradientStart, layout.gradientEnd);
    }
  });

  return collected;
});
const {
  selectedElement,
  hasSelection,
  isGroupSelection,
  selectedGroup,
  activeSelectionIds,
  hasMultiSelection,
  overlayControlTargetId,
  activeElementLabel,
  selectedElementType,
  hasTextSelection,
  clearSelection,
  clearSelectionMarquee,
  getGroupIdForElement,
  getSelectionBounds,
  isElementSelected,
  startSelectionMarquee,
  updateSelectionMarqueePreview,
  finalizeSelectionMarquee,
  selectGroup,
  buildGroupResizeSnapshot,
  selectedOverlayStyle,
  selectedActionBarStyle,
  selectedHandleMetrics,
  marqueeRectStyle,
} = useEditorSelection({
  state,
  editorElements,
  groupedElements,
  selectedGroupId,
  multiSelectionIds,
  marqueePreviewIds,
  selectionMarquee,
  activePropertyPanel,
  elementMeasurements,
  canvasRef,
  editingElementId,
  commitTextEdit: () => commitTextEdit(),
  setDragDocumentState: (...args) => setDragDocumentState(...args),
  getEstimatedTextHeight: (...args) => getEstimatedTextHeight(...args),
  getElementText: (...args) => getElementText(...args),
  ensureParagraphStyles: (...args) => ensureParagraphStyles(...args),
  isTextElement: (...args) => isTextElement(...args),
});
const backgroundHasImage = computed(() => Boolean(state.elementLayout.background?.backgroundImageSrc));
const selectedBackgroundPropertyTabs = computed(() => {
  const tabs = [...backgroundPropertyTabs];

  if (backgroundHasImage.value) {
    tabs.push(
      { id: 'crop', icon: 'ph:crop-bold', title: 'Recortar', class: 'order-last' },
      { id: 'rotate', icon: '', label: 'Girar', class: 'order-last' },
      { id: 'detach', icon: 'tabler:background', title: 'Separar imagen del fondo', class: 'order-last' },
      { id: 'clear-background', icon: 'ph:trash-bold', title: 'Borrar fondo', class: 'order-last' },
    );
  }

  return tabs;
});
const selectedPropertyTabs = computed(() => {
  if (isGroupSelection.value || hasMultiSelection.value) return [];
  if (!hasSelection.value) return textPropertyTabs;
  if (state.selectedElementId === 'background') return selectedBackgroundPropertyTabs.value;
  if (selectedElementType.value === 'text') return textPropertyTabs;
  return selectedElementType.value === 'image' ? imagePropertyTabs : shapePropertyTabs;
});
const hasSidebarPanelContent = computed(() => (
  !!activePropertyPanel.value
  || textPanelOpen.value
  || imagePanelOpen.value
  || shapePanelOpen.value
));
const isOptionsPanelVisible = computed(() => (
  optionsPanelOpen.value && hasSidebarPanelContent.value
));
const activePropertyTitle = computed(() => {
  const activeTab = selectedPropertyTabs.value.find((tab) => tab.id === activePropertyPanel.value);
  return activeTab?.title ?? activeTab?.label ?? 'Propiedades';
});
const {
  activeTextEffectId,
  activeVisualEffectId,
  textEffectRows,
  visualEffectRows,
  canvasBackgroundStyle,
  normalizePickerColor,
  setSelectedColor,
  setTextEffect,
  setVisualEffect,
  textEffectPreviewStyle,
  visualEffectPreviewStyle,
  applyGradientPreset,
  swapGradientStops,
  applyShapeGradientPreset,
  swapShapeGradientStops,
  elementBoxStyle,
  isTextElement,
  isAspectLockedResizeElement,
  shapeStyleFromKind,
  shapeStyle,
  shapeRenderModel,
  imageFrameStyle,
  imageRenderStyle,
  imageTintOverlayStyle,
  elementContentStyle,
  richEditorContainerStyle,
  neonColorOverride,
} = useEditorStyles({
  state,
  selectedElement,
  hasTextSelection,
  textEffectOptions,
  getParagraphStyleFields: () => paragraphStyleFields,
  applyParagraphStyleField: (...args) => applyParagraphStyleField(...args),
  getParagraphStyleForElement: (...args) => getParagraphStyleForElement(...args),
  baseTextElementIds,
  shapeClipPaths: SHAPE_CLIP_PATHS,
});
const orderedLayerIds = computed(() => Object.keys(state.elementLayout).sort((a, b) => {
    const zA = state.elementLayout[a]?.zIndex ?? 0;
    const zB = state.elementLayout[b]?.zIndex ?? 0;

    if (zA === zB) {
        return a.localeCompare(b);
    }

    return zA - zB;
}));
const canvasBackgroundImageStyle = computed(() => buildCoverImageStyle({
  containerWidth: editorCanvasDimensions.value.width,
  containerHeight: editorCanvasDimensions.value.height,
  imageWidth: state.elementLayout.background?.backgroundImageWidth,
  imageHeight: state.elementLayout.background?.backgroundImageHeight,
  cropScale: state.elementLayout.background?.backgroundImageCropScale,
  cropOffsetX: state.elementLayout.background?.backgroundImageCropOffsetX,
  cropOffsetY: state.elementLayout.background?.backgroundImageCropOffsetY,
  flipX: state.elementLayout.background?.backgroundImageFlipX,
  flipY: state.elementLayout.background?.backgroundImageFlipY,
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
watch(hasSidebarPanelContent, (hasContent) => {
  if (!hasContent && optionsPanelOpen.value) {
    optionsPanelOpen.value = false;
  }
});

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

const getMaxZIndex = () => Object.values(state.elementLayout).reduce((max, layout) => Math.max(max, layout?.zIndex ?? 0), 0);
const resolvedSizeOption = computed(() => {
  const objectiveRules = objectiveRecommendations[state.objective] ?? objectiveRecommendations.generic;
  const options = objectiveRules[state.outputType] ?? [];
  return options.find((option) => option.label === state.size) ?? null;
});
const selectedSizeDetail = computed(() => resolvedSizeOption.value?.detail ?? '1080 × 1080 px');
const editorCanvasDimensions = computed(() => {
  const parsed = applyFormatToDimensions(parseSizeDetail(selectedSizeDetail.value), state.format);
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
  gridTemplateColumns: '70px 1fr',
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
const currentCanvasDimensions = () => ({
  width: editorCanvasDimensions.value.width,
  height: editorCanvasDimensions.value.height,
});
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
  borderStyle: 'solid',
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
  contourWidth: 2,
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
  imageCropScale: 1,
  imageCropOffsetX: 0,
  imageCropOffsetY: 0,
  flipX: false,
  flipY: false,
  ...overrides,
});
const placeInsideCanvas = (layout) => {
  const bounds = getCanvasBounds();
  const width = Math.max(40, layout.w ?? 0);
  const height = Math.max(40, layout.h ?? 50);

  layout.x = Math.round(clamp(layout.x ?? 0, 0, Math.max(0, bounds.width - width - 8)));
  layout.y = Math.round(clamp(layout.y ?? 0, 18, Math.max(18, bounds.height - height - 8)));
};

const scaleNumericField = (layout, field, factor, minimum = 0) => {
  if (!Number.isFinite(Number(layout?.[field]))) return;
  layout[field] = Math.max(minimum, Number(layout[field]) * factor);
};

const rescaleDesignSurface = (previousSurface, nextSurface) => {
  if (!previousSurface?.width || !previousSurface?.height || !nextSurface?.width || !nextSurface?.height) {
    state.designSurface = nextSurface;
    return;
  }

  const widthScale = nextSurface.width / previousSurface.width;
  const heightScale = nextSurface.height / previousSurface.height;
  const averageScale = (widthScale + heightScale) / 2;

  Object.entries(state.elementLayout ?? {}).forEach(([id, layout]) => {
    if (!layout || id === 'background') return;

    scaleNumericField(layout, 'x', widthScale);
    scaleNumericField(layout, 'y', heightScale, 18);
    scaleNumericField(layout, 'w', widthScale, 40);
    scaleNumericField(layout, 'h', heightScale, 40);
    scaleNumericField(layout, 'fontSize', averageScale, 8);
    scaleNumericField(layout, 'shadowOffset', averageScale);
    scaleNumericField(layout, 'shadowBlur', averageScale);
    scaleNumericField(layout, 'contourWidth', averageScale);
    scaleNumericField(layout, 'misalignedThickness', averageScale);
    scaleNumericField(layout, 'backgroundPadding', averageScale);
    scaleNumericField(layout, 'letterSpacing', averageScale);

    if (Array.isArray(layout.paragraphStyles)) {
      layout.paragraphStyles = layout.paragraphStyles.map((style) => ({
        ...style,
        fontSize: Number.isFinite(Number(style?.fontSize)) ? Math.max(8, Number(style.fontSize) * averageScale) : style?.fontSize,
        letterSpacing: Number.isFinite(Number(style?.letterSpacing)) ? Number(style.letterSpacing) * averageScale : style?.letterSpacing,
      }));
    }

    placeInsideCanvas(layout);
  });

  state.designSurface = nextSurface;
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

const closeImagePanel = () => {
  imagePanelOpen.value = false;
  imageUrlInput.value = '';
};

const requestImmediateStateFlush = () => {
  flushDesignerStatePersistence().catch((error) => {
    console.error('No se pudo persistir inmediatamente el estado del editor', error);
  });
};

const getUploadedImageIndexByAssetId = (assetId) => state.userUploadedImages.findIndex(
  (image) => image?.assetId === assetId || image?.id === assetId
);

const getUploadedImageByAssetId = (assetId) => {
  const index = getUploadedImageIndexByAssetId(assetId);
  return index >= 0 ? state.userUploadedImages[index] : null;
};

const upsertUploadedImage = (entry) => {
  if (!entry?.assetId) return null;

  const normalizedEntry = {
    id: entry.id ?? entry.assetId,
    assetId: entry.assetId,
    label: entry.label ?? 'Subida',
    src: entry.src ?? '',
    pendingDataUrl: entry.pendingDataUrl ?? null,
    storagePath: entry.storagePath ?? null,
    uploadStatus: entry.uploadStatus ?? 'done',
    needsUpload: Boolean(entry.needsUpload),
    errorMessage: entry.errorMessage ?? null,
    intrinsicWidth: Number(entry.intrinsicWidth ?? 0) || null,
    intrinsicHeight: Number(entry.intrinsicHeight ?? 0) || null,
  };

  const existingIndex = getUploadedImageIndexByAssetId(entry.assetId);
  if (existingIndex >= 0) {
    state.userUploadedImages.splice(existingIndex, 1, {
      ...state.userUploadedImages[existingIndex],
      ...normalizedEntry,
    });
    return state.userUploadedImages[existingIndex];
  }

  state.userUploadedImages.unshift(normalizedEntry);
  return state.userUploadedImages[0];
};

const updateUploadedImage = (assetId, updater) => {
  const existing = getUploadedImageByAssetId(assetId);
  if (!existing) return null;

  const nextValue = typeof updater === 'function' ? updater(existing) : updater;
  if (!nextValue) return existing;

  return upsertUploadedImage({
    ...existing,
    ...nextValue,
    assetId,
  });
};

const getUploadProgress = (assetId) => {
  const progress = uploadProgressByAssetId[assetId];
  if (typeof progress === 'number') {
    return progress;
  }

  const image = getUploadedImageByAssetId(assetId);
  return image?.uploadStatus === 'done' ? 100 : 0;
};

const humanizeUploadError = (error) => {
  const status = error?.response?.status;
  if (status === 413 || status === 422) {
    return 'La imagen es demasiado grande o no tiene un formato válido.';
  }

  return 'No se pudo subir la imagen. Reintenta.';
};

const getImageIntrinsicSize = (src) => new Promise((resolve) => {
  if (!src) {
    resolve(null);
    return;
  }

  const image = new Image();
  image.onload = () => {
    resolve({
      width: image.naturalWidth || image.width,
      height: image.naturalHeight || image.height,
    });
  };
  image.onerror = () => resolve(null);
  image.src = src;
});

const buildInitialImageLayout = async (src) => {
  const bounds = getCanvasBounds();
  const fallbackWidth = 220;
  const fallbackHeight = 160;
  const intrinsicSize = await getImageIntrinsicSize(src);

  if (!intrinsicSize?.width || !intrinsicSize?.height) {
    return {
      intrinsicSize: null,
      layout: buildDefaultLayout({
        w: fallbackWidth,
        h: fallbackHeight,
        x: getInsertX(fallbackWidth),
        y: 120,
        backgroundColor: '#ffffff',
        color: '#ffffff',
      }),
    };
  }

  const maxWidth = Math.max(120, bounds.width - 48);
  const maxHeight = Math.max(120, bounds.height - 72);
  const scale = Math.min(1, maxWidth / intrinsicSize.width, maxHeight / intrinsicSize.height);
  const width = Math.max(40, Math.round(intrinsicSize.width * scale));
  const height = Math.max(40, Math.round(intrinsicSize.height * scale));

  return {
    intrinsicSize,
    layout: buildDefaultLayout({
      w: width,
      h: height,
      x: getInsertX(width),
      y: 120,
      backgroundColor: '#ffffff',
      color: '#ffffff',
      imageCropScale: 1,
      imageCropOffsetX: 0,
      imageCropOffsetY: 0,
      flipX: false,
      flipY: false,
    }),
  };
};

const addImageElementFromSrc = async (src, label = 'Imagen', options = {}) => {
  if (!src) return;
  const {
    assetId = null,
    pendingDataUrl = null,
    storagePath = null,
    needsUpload = false,
    closePanel = true,
    layoutOverrides = {},
    intrinsicWidth = null,
    intrinsicHeight = null,
  } = options;

  const id = createElementId('image');
  const { layout: baseLayout, intrinsicSize } = await buildInitialImageLayout(src);
  const layout = {
    ...baseLayout,
    ...layoutOverrides,
  };

  placeInsideCanvas(layout);
  state.customElements = {
    ...(state.customElements ?? {}),
    [id]: {
      id,
      type: 'image',
      label,
      src,
      assetId,
      pendingDataUrl,
      storagePath,
      needsUpload,
      intrinsicWidth: intrinsicWidth ?? intrinsicSize?.width ?? null,
      intrinsicHeight: intrinsicHeight ?? intrinsicSize?.height ?? null,
    },
  };
  state.elementLayout = {
    ...(state.elementLayout ?? {}),
    [id]: layout,
  };
  state.selectedElementId = id;
  if (closePanel) {
    closeImagePanel();
  }
  return id;
};

const clearBackgroundImage = () => {
  state.elementLayout.background = {
    ...state.elementLayout.background,
    backgroundImageSrc: null,
    backgroundImageAssetId: null,
    backgroundImagePendingDataUrl: null,
    backgroundImageStoragePath: null,
    backgroundImageWidth: null,
    backgroundImageHeight: null,
    backgroundImageCropScale: 1,
    backgroundImageCropOffsetX: 0,
    backgroundImageCropOffsetY: 0,
    backgroundImageFlipX: false,
    backgroundImageFlipY: false,
  };
};

const clearBackgroundFill = () => {
  state.elementLayout.background = {
    ...state.elementLayout.background,
    fillMode: 'solid',
    backgroundColor: '#ffffff',
    gradientStart: '#0ea5e9',
    gradientEnd: '#8b5cf6',
    gradientAngle: 135,
  };
};

const setBackgroundImage = async ({
  src,
  assetId = null,
  label = 'Fondo',
  pendingDataUrl = null,
  storagePath = null,
  needsUpload = false,
  intrinsicWidth = null,
  intrinsicHeight = null,
}) => {
  if (!src) return;

  const intrinsicSize = intrinsicWidth && intrinsicHeight
    ? { width: intrinsicWidth, height: intrinsicHeight }
    : await getImageIntrinsicSize(src);

  state.elementLayout.background = {
    ...state.elementLayout.background,
    backgroundImageSrc: src,
    backgroundImageAssetId: assetId,
    backgroundImagePendingDataUrl: pendingDataUrl,
    backgroundImageStoragePath: storagePath,
    backgroundImageWidth: intrinsicSize?.width ?? null,
    backgroundImageHeight: intrinsicSize?.height ?? null,
    backgroundImageCropScale: 1,
    backgroundImageCropOffsetX: 0,
    backgroundImageCropOffsetY: 0,
    backgroundImageFlipX: false,
    backgroundImageFlipY: false,
  };

  state.selectedElementId = 'background';
  activePropertyPanel.value = 'color';
  optionsPanelOpen.value = true;
  imagePanelOpen.value = false;
  textPanelOpen.value = false;
  shapePanelOpen.value = false;

  if (assetId) {
    upsertUploadedImage({
      assetId,
      label,
      src,
      pendingDataUrl,
      storagePath,
      needsUpload,
      uploadStatus: needsUpload ? 'pending' : 'done',
      intrinsicWidth: intrinsicSize?.width ?? null,
      intrinsicHeight: intrinsicSize?.height ?? null,
    });
  }
};

const replaceUploadedImageSourceEverywhere = async ({ assetId, finalUrl, storagePath = null }) => {
  const uploadedImage = getUploadedImageByAssetId(assetId);
  const previousSrc = uploadedImage?.pendingDataUrl || uploadedImage?.src || null;

  await mutateWithoutHistory(() => {
    updateUploadedImage(assetId, {
      src: finalUrl,
      pendingDataUrl: null,
      storagePath,
      uploadStatus: 'done',
      needsUpload: false,
      errorMessage: null,
    });

    Object.entries(state.customElements ?? {}).forEach(([id, element]) => {
      if (!element || element.type !== 'image') return;
      if (element.assetId !== assetId) return;

      state.customElements[id] = {
        ...element,
        src: finalUrl,
        pendingDataUrl: null,
        storagePath,
        needsUpload: false,
      };
    });

    if (state.elementLayout.background?.backgroundImageAssetId === assetId) {
      state.elementLayout.background = {
        ...state.elementLayout.background,
        backgroundImageSrc: finalUrl,
        backgroundImagePendingDataUrl: null,
        backgroundImageStoragePath: storagePath,
      };
    }

    replaceImageAssetSource({
      assetId,
      previousSrc,
      nextSrc: finalUrl,
      storagePath,
    });
  });

  requestImmediateStateFlush();
};

const uploadImageAsset = async ({ assetId, file, label, dataUrl }) => {
  if (!assetId || !file || activeUploadAssetIds.has(assetId)) {
    return;
  }

  activeUploadAssetIds.add(assetId);
  uploadProgressByAssetId[assetId] = Math.max(1, getUploadProgress(assetId));

  updateUploadedImage(assetId, {
    src: dataUrl,
    pendingDataUrl: dataUrl,
    uploadStatus: 'uploading',
    needsUpload: true,
    errorMessage: null,
  });

  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('assetId', assetId);
    formData.append('label', label ?? file.name ?? 'Imagen');

    const response = await axios.post(uploadEndpoint.value, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (event) => {
        if (!event.total) return;
        uploadProgressByAssetId[assetId] = Math.min(99, Math.round((event.loaded / event.total) * 100));
      },
    });

    const finalUrl = response.data?.url;
    const storagePath = response.data?.path ?? null;

    if (!finalUrl) {
      throw new Error('La respuesta del servidor no incluyó la URL de la imagen.');
    }

    uploadProgressByAssetId[assetId] = 100;
    await replaceUploadedImageSourceEverywhere({ assetId, finalUrl, storagePath });
  } catch (error) {
    console.error('No se pudo subir la imagen del usuario', error);
    uploadProgressByAssetId[assetId] = 0;
    updateUploadedImage(assetId, {
      src: dataUrl,
      pendingDataUrl: dataUrl,
      uploadStatus: 'error',
      needsUpload: true,
      errorMessage: humanizeUploadError(error),
    });
  } finally {
    activeUploadAssetIds.delete(assetId);
  }
};

const queueUploadForAsset = async (assetId, options = {}) => {
  if (!assetId || activeUploadAssetIds.has(assetId)) {
    return;
  }

  const uploadedImage = getUploadedImageByAssetId(assetId);
  const label = options.label ?? uploadedImage?.label ?? 'Imagen';
  const pendingDataUrl = options.dataUrl ?? uploadedImage?.pendingDataUrl ?? uploadedImage?.src ?? '';

  if (!isDataImageUrl(pendingDataUrl)) {
    return;
  }

  try {
    const file = options.file ?? dataUrlToFile(pendingDataUrl, label);
    await uploadImageAsset({
      assetId,
      file,
      label,
      dataUrl: pendingDataUrl,
    });
  } catch (error) {
    console.error('No se pudo preparar la reanudación del upload de imagen', error);
    updateUploadedImage(assetId, {
      uploadStatus: 'error',
      needsUpload: true,
      errorMessage: humanizeUploadError(error),
    });
  }
};

const createPendingUploadedImageFromFile = async (file, options = {}) => {
  if (!(file instanceof File) || !file.type.startsWith('image/')) {
    return null;
  }

  const processedFile = await optimizeImageFile(file, imageUploadProcessingConfig.value);
  const dataUrl = await fileToDataUrl(processedFile);
  const intrinsicSize = await getImageIntrinsicSize(dataUrl);
  const assetId = createElementId('upload');
  const label = processedFile.name || file.name || 'Imagen';

  upsertUploadedImage({
    assetId,
    label,
    src: dataUrl,
    pendingDataUrl: dataUrl,
    uploadStatus: 'pending',
    needsUpload: true,
    errorMessage: null,
    intrinsicWidth: intrinsicSize?.width ?? null,
    intrinsicHeight: intrinsicSize?.height ?? null,
  });

  if (options.useAsBackground) {
    await setBackgroundImage({
      src: dataUrl,
      assetId,
      label,
      pendingDataUrl: dataUrl,
      needsUpload: true,
      intrinsicWidth: intrinsicSize?.width ?? null,
      intrinsicHeight: intrinsicSize?.height ?? null,
    });
  } else if (options.insertIntoCanvas) {
    await addImageElementFromSrc(dataUrl, label, {
      assetId,
      pendingDataUrl: dataUrl,
      needsUpload: true,
      closePanel: Boolean(options.closePanel),
      intrinsicWidth: intrinsicSize?.width ?? null,
      intrinsicHeight: intrinsicSize?.height ?? null,
    });
  }

  if (options.openUploadsPanel) {
    optionsPanelOpen.value = true;
    imagePanelOpen.value = true;
    textPanelOpen.value = false;
    shapePanelOpen.value = false;
    imagePanelTab.value = 'uploads';
  }

  queueUploadForAsset(assetId, { file: processedFile, dataUrl, label });
  requestImmediateStateFlush();

  return assetId;
};

const triggerImagePicker = () => {
  imageInputRef.value?.click();
};

const onImagePicked = async (event) => {
  const input = event.target;
  const files = Array.from(input?.files ?? []).filter((file) => file.type.startsWith('image/'));
  if (!files.length) return;

  imagePanelTab.value = 'uploads';
  for (const file of files) {
    // Desde el picker actúa como subida a la galería del usuario; la inserción en el diseño queda a elección posterior.
    // eslint-disable-next-line no-await-in-loop
    await createPendingUploadedImageFromFile(file, { openUploadsPanel: true });
  }

  input.value = '';
};

const addImageFromUrl = async () => {
  const src = imageUrlInput.value.trim();
  if (!src) return;

  if (state.selectedElementId === 'background') {
    await setBackgroundImage({ src, label: 'Fondo' });
    return;
  }

  await addImageElementFromSrc(src, 'Imagen URL');
};

const addLibraryImage = async (image) => {
  if (state.selectedElementId === 'background') {
    await setBackgroundImage({
      src: image?.src,
      label: image?.label || 'Fondo',
    });
    return;
  }

  return addImageElementFromSrc(image?.src, image?.label || 'Imagen de libreria');
};

const addUploadedImage = async (image) => {
  const src = image?.src || image?.pendingDataUrl || '';
  if (!src) return;

  if (state.selectedElementId === 'background') {
    await setBackgroundImage({
      src,
      assetId: image?.assetId ?? image?.id ?? null,
      label: image?.label || 'Fondo',
      pendingDataUrl: image?.pendingDataUrl ?? (isDataImageUrl(src) ? src : null),
      storagePath: image?.storagePath ?? null,
      needsUpload: Boolean(image?.needsUpload),
      intrinsicWidth: image?.intrinsicWidth ?? null,
      intrinsicHeight: image?.intrinsicHeight ?? null,
    });

    if (image?.needsUpload && (image?.pendingDataUrl || isDataImageUrl(src))) {
      queueUploadForAsset(image.assetId ?? image.id, {
        dataUrl: image.pendingDataUrl ?? src,
        label: image.label,
      });
    }
    return;
  }

  await addImageElementFromSrc(src, image?.label || 'Imagen subida', {
    assetId: image?.assetId ?? image?.id ?? null,
    pendingDataUrl: image?.pendingDataUrl ?? (isDataImageUrl(src) ? src : null),
    storagePath: image?.storagePath ?? null,
    needsUpload: Boolean(image?.needsUpload),
    intrinsicWidth: image?.intrinsicWidth ?? null,
    intrinsicHeight: image?.intrinsicHeight ?? null,
  });

  if (image?.needsUpload && (image?.pendingDataUrl || isDataImageUrl(src))) {
    queueUploadForAsset(image.assetId ?? image.id, {
      dataUrl: image.pendingDataUrl ?? src,
      label: image.label,
    });
  }
};

const retryUploadedImage = (image) => {
  const assetId = image?.assetId ?? image?.id ?? null;
  const pendingDataUrl = image?.pendingDataUrl ?? image?.src ?? '';
  if (!assetId || !isDataImageUrl(pendingDataUrl)) return;

  queueUploadForAsset(assetId, {
    dataUrl: pendingDataUrl,
    label: image?.label ?? 'Imagen',
  });
};

const toggleSelectedImageFlip = (axis) => {
  if (state.selectedElementId === 'background') {
    if (!backgroundHasImage.value) return;
    const key = axis === 'x' ? 'backgroundImageFlipX' : 'backgroundImageFlipY';
    const offsetKey = axis === 'x' ? 'backgroundImageCropOffsetX' : 'backgroundImageCropOffsetY';
    state.elementLayout.background[key] = !state.elementLayout.background[key];
    state.elementLayout.background[offsetKey] = Number(state.elementLayout.background[offsetKey] ?? 0) * -1;
    return;
  }

  if (selectedElementType.value !== 'image' || !selectedElement.value) return;
  const key = axis === 'x' ? 'flipX' : 'flipY';
  const offsetKey = axis === 'x' ? 'imageCropOffsetX' : 'imageCropOffsetY';
  selectedElement.value[key] = !selectedElement.value[key];
  selectedElement.value[offsetKey] = Number(selectedElement.value[offsetKey] ?? 0) * -1;
};

const resetSelectedImageCrop = () => {
  if (state.selectedElementId === 'background') {
    if (!backgroundHasImage.value) return;
    state.elementLayout.background.backgroundImageCropScale = 1;
    state.elementLayout.background.backgroundImageCropOffsetX = 0;
    state.elementLayout.background.backgroundImageCropOffsetY = 0;
    return;
  }

  if (selectedElementType.value !== 'image' || !selectedElement.value) return;
  selectedElement.value.imageCropScale = 1;
  selectedElement.value.imageCropOffsetX = 0;
  selectedElement.value.imageCropOffsetY = 0;
};

const detachBackgroundImage = async () => {
  if (!backgroundHasImage.value) return;

  const backgroundLayout = state.elementLayout.background ?? {};
  const width = Math.round(editorCanvasDimensions.value.width * 0.75);
  const height = Math.round(editorCanvasDimensions.value.height * 0.75);
  const src = backgroundLayout.backgroundImageSrc;

  clearBackgroundImage();

  await addImageElementFromSrc(src, 'Imagen separada del fondo', {
    assetId: backgroundLayout.backgroundImageAssetId ?? null,
    pendingDataUrl: backgroundLayout.backgroundImagePendingDataUrl ?? null,
    storagePath: backgroundLayout.backgroundImageStoragePath ?? null,
    needsUpload: Boolean(backgroundLayout.backgroundImagePendingDataUrl),
    intrinsicWidth: backgroundLayout.backgroundImageWidth ?? null,
    intrinsicHeight: backgroundLayout.backgroundImageHeight ?? null,
    layoutOverrides: {
      w: width,
      h: height,
      x: Math.max(0, Math.round((editorCanvasDimensions.value.width - width) / 2)),
      y: Math.max(18, Math.round((editorCanvasDimensions.value.height - height) / 2)),
      imageCropScale: backgroundLayout.backgroundImageCropScale ?? 1,
      imageCropOffsetX: backgroundLayout.backgroundImageCropOffsetX ?? 0,
      imageCropOffsetY: backgroundLayout.backgroundImageCropOffsetY ?? 0,
      flipX: Boolean(backgroundLayout.backgroundImageFlipX),
      flipY: Boolean(backgroundLayout.backgroundImageFlipY),
    },
  });
};

const clearBackgroundCompletely = () => {
  clearBackgroundImage();
  clearBackgroundFill();
  state.selectedElementId = 'background';
  activePropertyPanel.value = 'color';
  optionsPanelOpen.value = true;
};

const promoteSelectedImageToBackground = async () => {
  if (selectedElementType.value !== 'image' || !state.selectedElementId || !selectedElement.value) {
    return;
  }

  if (backgroundHasImage.value) {
    const confirmed = window.confirm('Ya hay una imagen de fondo. Si continúas, será reemplazada por la imagen seleccionada.');
    if (!confirmed) {
      return;
    }
  }

  const elementId = state.selectedElementId;
  const imageElement = state.customElements?.[elementId];
  const imageLayout = state.elementLayout?.[elementId];

  if (!imageElement || !imageLayout) {
    return;
  }

  await setBackgroundImage({
    src: imageElement.src,
    assetId: imageElement.assetId ?? null,
    label: imageElement.label ?? 'Fondo',
    pendingDataUrl: imageElement.pendingDataUrl ?? null,
    storagePath: imageElement.storagePath ?? null,
    needsUpload: Boolean(imageElement.needsUpload),
    intrinsicWidth: imageElement.intrinsicWidth ?? null,
    intrinsicHeight: imageElement.intrinsicHeight ?? null,
  });

  state.elementLayout.background = {
    ...state.elementLayout.background,
    backgroundImageCropScale: Math.max(1, Number(imageLayout.imageCropScale ?? 1)),
    backgroundImageCropOffsetX: Number(imageLayout.imageCropOffsetX ?? 0),
    backgroundImageCropOffsetY: Number(imageLayout.imageCropOffsetY ?? 0),
    backgroundImageFlipX: Boolean(imageLayout.flipX),
    backgroundImageFlipY: Boolean(imageLayout.flipY),
  };

  if (state.customElements?.[elementId]) {
    delete state.customElements[elementId];
  }
  if (state.elementLayout?.[elementId]) {
    delete state.elementLayout[elementId];
  }
  if (elementMeasurements[elementId]) {
    delete elementMeasurements[elementId];
  }
  if (richEditorRefs.value[elementId]) {
    delete richEditorRefs.value[elementId];
  }
};

const handlePropertyTabClick = async (tab) => {
  if (!tab) return;

  if (tab.id === 'detach') {
    await detachBackgroundImage();
    return;
  }

  if (tab.id === 'set-as-background') {
    await promoteSelectedImageToBackground();
    return;
  }

  if (tab.id === 'clear-background') {
    clearBackgroundCompletely();
    return;
  }

  activePropertyPanel.value = tab.id;
  optionsPanelOpen.value = true;
};

const syncPendingUploadsFromPersistedState = async () => {
  await mutateWithoutHistory(() => {
    const backgroundImageSrc = state.elementLayout.background?.backgroundImageSrc ?? '';
    const backgroundPendingDataUrl = state.elementLayout.background?.backgroundImagePendingDataUrl
      ?? (isDataImageUrl(backgroundImageSrc) ? backgroundImageSrc : null);
    const backgroundAssetId = state.elementLayout.background?.backgroundImageAssetId
      ?? (backgroundPendingDataUrl ? createElementId('background-upload') : null);

    if (backgroundPendingDataUrl && backgroundAssetId) {
      state.elementLayout.background = {
        ...state.elementLayout.background,
        backgroundImageAssetId: backgroundAssetId,
        backgroundImagePendingDataUrl: backgroundPendingDataUrl,
      };

      if (!getUploadedImageByAssetId(backgroundAssetId)) {
        upsertUploadedImage({
          assetId: backgroundAssetId,
          label: 'Fondo',
          src: backgroundPendingDataUrl,
          pendingDataUrl: backgroundPendingDataUrl,
          uploadStatus: 'pending',
          needsUpload: true,
          intrinsicWidth: state.elementLayout.background?.backgroundImageWidth ?? null,
          intrinsicHeight: state.elementLayout.background?.backgroundImageHeight ?? null,
        });
      }
    }

    Object.entries(state.customElements ?? {}).forEach(([id, element]) => {
      if (!element || element.type !== 'image') return;

      const pendingDataUrl = element.pendingDataUrl ?? (isDataImageUrl(element.src) ? element.src : null);
      const assetId = element.assetId ?? (pendingDataUrl ? createElementId(`recovered-${id}`) : null);

      if (!assetId || !pendingDataUrl) return;

      if (!element.assetId || element.assetId !== assetId) {
        state.customElements[id] = {
          ...element,
          assetId,
          pendingDataUrl,
          needsUpload: true,
        };
      }

      if (!getUploadedImageByAssetId(assetId)) {
        upsertUploadedImage({
          assetId,
          label: element.label ?? 'Imagen recuperada',
          src: pendingDataUrl,
          pendingDataUrl,
          uploadStatus: 'pending',
          needsUpload: true,
        });
      }
    });
  });

  state.userUploadedImages.forEach((image) => {
    const assetId = image.assetId ?? image.id;
    const pendingDataUrl = image.pendingDataUrl ?? (isDataImageUrl(image.src) ? image.src : null);

    if (assetId && pendingDataUrl && (image.needsUpload || image.uploadStatus !== 'done')) {
      queueUploadForAsset(assetId, {
        dataUrl: pendingDataUrl,
        label: image.label,
      });
    }
  });
};

const handleCanvasFileDragOver = (event) => {
  if (!hasFilesInTransfer(event.dataTransfer)) return;

  event.preventDefault();
  fileDragActive.value = true;
  const rect = event.currentTarget?.getBoundingClientRect?.();
  if (rect) {
    const edgeThreshold = Math.min(72, Math.max(40, Math.round(Math.min(rect.width, rect.height) * 0.12)));
    backgroundDropPreview.value = (
      event.clientX - rect.left <= edgeThreshold
      || rect.right - event.clientX <= edgeThreshold
      || event.clientY - rect.top <= edgeThreshold
      || rect.bottom - event.clientY <= edgeThreshold
    );
  }
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'copy';
  }
};

const handleCanvasFileDragEnter = (event) => {
  if (!hasFilesInTransfer(event.dataTransfer)) return;

  event.preventDefault();
  fileDragActive.value = true;
};

const handleCanvasFileDragLeave = (event) => {
  if (event?.currentTarget?.contains?.(event.relatedTarget)) {
    return;
  }

  fileDragActive.value = false;
  backgroundDropPreview.value = false;
};

const handleCanvasFileDrop = async (event) => {
  const files = extractImageFilesFromDataTransfer(event.dataTransfer);
  const shouldUseAsBackground = backgroundDropPreview.value && files.length === 1;
  fileDragActive.value = false;
  backgroundDropPreview.value = false;
  if (!files.length) return;

  event.preventDefault();
  for (const file of files) {
    // eslint-disable-next-line no-await-in-loop
    await createPendingUploadedImageFromFile(file, shouldUseAsBackground
      ? { useAsBackground: true }
      : { insertIntoCanvas: true });
  }
};

const handleDocumentPaste = async (event) => {
  if (editingElementId.value || isEditableTarget(event.target)) {
    return;
  }

  const files = extractImageFilesFromDataTransfer(event.clipboardData);
  if (!files.length) return;

  event.preventDefault();
  for (const file of files) {
    // eslint-disable-next-line no-await-in-loop
    await createPendingUploadedImageFromFile(file, { insertIntoCanvas: true });
  }
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

const getEstimatedTextHeight = (layout, text = '') => ensureParagraphStyles(layout, text)
    .reduce((total, style) => total + Math.max((style.fontSize ?? layout.fontSize ?? 16) * (style.lineHeight ?? 1.3), 16), 0);

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
        assetId: sourceElement.assetId ?? null,
        pendingDataUrl: sourceElement.pendingDataUrl ?? null,
        storagePath: sourceElement.storagePath ?? null,
        needsUpload: Boolean(sourceElement.needsUpload),
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
    if (!id) return;
    if (id === 'background') {
      clearBackgroundCompletely();
      return;
    }

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
          assetId: sourceElement.assetId ?? null,
          pendingDataUrl: sourceElement.pendingDataUrl ?? null,
          storagePath: sourceElement.storagePath ?? null,
          needsUpload: Boolean(sourceElement.needsUpload),
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

const {
  clearLongPress,
  handleElementClick,
  markEditorControlInteraction,
  onRichEditorBlur,
  handleElementPointerDown,
  startResize,
  startRotate,
  resetRotation,
  moveDrag,
  endDrag,
  cycleAlignment,
  currentAlignmentIcon,
  changeLayer,
  handleCanvasPointerDown,
  handleGlobalPointerDown,
  handleGlobalKeydown,
} = useEditorInteractions({
  state,
  canvasRef,
  richEditorRefs,
  elementMeasurements,
  drag,
  toolbarPosition,
  toolbarDrag,
  touchIntent,
  dragIntent,
  selectionMarquee,
  groupedElements,
  multiSelectionIds,
  selectedGroupId,
  activePropertyPanel,
  paragraphSelection,
  selectedParagraphIndex,
  preserveEditorSelectionUntil,
  suppressElementClickUntil,
  editingElementId,
  zoomScale,
  orderedLayerIds,
  selectedTextStyle,
  commitTextEdit: () => commitTextEdit(),
  beginTextEdit: (...args) => beginTextEdit(...args),
  deleteCurrentSelection: () => deleteCurrentSelection(),
  performUndo: () => performUndo(),
  performRedo: () => performRedo(),
  setDragDocumentState: (...args) => setDragDocumentState(...args),
  clearSelection: () => clearSelection(),
  startSelectionMarquee: (...args) => startSelectionMarquee(...args),
  updateSelectionMarqueePreview: () => updateSelectionMarqueePreview(),
  finalizeSelectionMarquee: () => finalizeSelectionMarquee(),
  selectGroup: (...args) => selectGroup(...args),
  getGroupIdForElement: (...args) => getGroupIdForElement(...args),
  buildGroupResizeSnapshot: (...args) => buildGroupResizeSnapshot(...args),
  getSelectionBounds: (...args) => getSelectionBounds(...args),
  getCanvasBounds: () => getCanvasBounds(),
  getEstimatedTextHeight: (...args) => getEstimatedTextHeight(...args),
  getElementText: (...args) => getElementText(...args),
  ensureParagraphStyles: (...args) => ensureParagraphStyles(...args),
  isTextElement: (...args) => isTextElement(...args),
  isAspectLockedResizeElement: (...args) => isAspectLockedResizeElement(...args),
  applyParagraphStyleField: (...args) => applyParagraphStyleField(...args),
});

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

const cancelTextEdit = () => {
    editingElementId.value = null;
    editingBoxHeight.value = null;
    paragraphSelection.start = selectedParagraphIndex.value;
    paragraphSelection.end = selectedParagraphIndex.value;
    paragraphSelection.active = false;
};

onMounted(() => {
  const nextSurface = currentCanvasDimensions();
  if (state.designSurface?.width && state.designSurface?.height) {
    rescaleDesignSurface(state.designSurface, nextSurface);
  } else {
    state.designSurface = nextSurface;
  }

  pushHistorySnapshot({ force: true });
  document.addEventListener('pointerdown', handleGlobalPointerDown, true);
  document.addEventListener('pointermove', moveDrag, { passive: false });
  document.addEventListener('pointerup', endDrag);
  document.addEventListener('pointercancel', endDrag);
  document.addEventListener('keydown', handleGlobalKeydown);
  document.addEventListener('paste', handleDocumentPaste);
  document.addEventListener('dragover', handleCanvasFileDragOver);
  document.addEventListener('drop', handleCanvasFileDragLeave);
  syncPendingUploadsFromPersistedState();
  refreshElementObservers();
});

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleGlobalPointerDown, true);
  document.removeEventListener('pointermove', moveDrag);
  document.removeEventListener('pointerup', endDrag);
  document.removeEventListener('pointercancel', endDrag);
  document.removeEventListener('keydown', handleGlobalKeydown);
  document.removeEventListener('paste', handleDocumentPaste);
  document.removeEventListener('dragover', handleCanvasFileDragOver);
  document.removeEventListener('drop', handleCanvasFileDragLeave);
  elementObservers.forEach((observer) => observer.disconnect());
  elementObservers.clear();
  clearLongPress();
  setDragDocumentState(false);
  fileDragActive.value = false;
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

watch(
  () => [state.content, state.elementLayout, state.customElements],
  () => {
    scheduleHistorySnapshot();
  },
  { deep: true }
);

const closeOptionsPanel = () => {
  optionsPanelOpen.value = false;
  activePropertyPanel.value = null;
  textPanelOpen.value = false;
  imagePanelOpen.value = false;
  shapePanelOpen.value = false;
};
const openTextInsertPanel = () => {
  textPanelOpen.value = true;
  imagePanelOpen.value = false;
  shapePanelOpen.value = false;
  optionsPanelOpen.value = true;
};
const openImageInsertPanel = () => {
  imagePanelOpen.value = true;
  textPanelOpen.value = false;
  shapePanelOpen.value = false;
  optionsPanelOpen.value = true;
};
const openShapeInsertPanel = () => {
  shapePanelOpen.value = true;
  textPanelOpen.value = false;
  imagePanelOpen.value = false;
  optionsPanelOpen.value = true;
};
const openBackgroundPanel = () => {
  state.selectedElementId = 'background';
  activePropertyPanel.value = 'color';
  textPanelOpen.value = false;
  imagePanelOpen.value = false;
  shapePanelOpen.value = false;
  optionsPanelOpen.value = true;
};
const setImageInputRef = (element) => {
  imageInputRef.value = element;
};
const setCanvasRef = (element) => {
  canvasRef.value = element;
};
const setRichEditorRef = (id, element) => {
  if (element) {
    richEditorRefs.value[id] = element;
    return;
  }
  delete richEditorRefs.value[id];
};
const handleExportNavigation = async (event) => {
  event?.preventDefault?.();
  try {
    await flushDesignerStatePersistence();
  } catch (error) {
    console.error('Failed to flush designer state before export', error);
  }
  window.location.href = '/designer/export';
};

const handleFormatAssistantNavigation = async () => {
  try {
    await flushDesignerStatePersistence();
  } catch (error) {
    console.error('Failed to flush designer state before format assistant', error);
  }

  window.location.href = '/designer/format?return=%2Fdesigner%2Feditor';
};

const handleCanvasClick = (event) => {
  if (event.target.closest('[data-editor-element="true"]') || event.target.closest('[data-editor-control="true"]')) return;
  state.selectedElementId = 'background';
  activePropertyPanel.value = 'color';
  optionsPanelOpen.value = true;
  textPanelOpen.value = false;
  imagePanelOpen.value = false;
  shapePanelOpen.value = false;
};

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
    <EditorTopBar
      :size="state.size"
      :can-undo="canUndo"
      :can-redo="canRedo"
      :undo-action-label="undoActionLabel"
      :redo-action-label="redoActionLabel"
      :zoom-level="zoomLevel"
      :dark-mode="state.darkMode"
      @open-format-assistant="handleFormatAssistantNavigation"
      @undo="performUndo"
      @redo="performRedo"
      @update-zoom-level="setZoomLevel"
      @toggle-dark-mode="state.darkMode = !state.darkMode"
      @export-navigate="handleExportNavigation"
    />

    <section class="relative min-h-0 flex-1 overflow-hidden">
      <div class="h-full overflow-hidden border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
        <div
          v-if="hasSelection && !hasMultiSelection && !isGroupSelection"
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
                        :title="tab.title || tab.label"
                        @click="handlePropertyTabClick(tab)">
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
          <!-- Panel de CreaciÃ³n (vertical, siempre visible) -->
          <EditorInsertSidebar
            :text-panel-open="textPanelOpen"
            :image-panel-open="imagePanelOpen"
            :shape-panel-open="shapePanelOpen"
            :is-background-selected="state.selectedElementId === 'background'"
            @open-text-panel="openTextInsertPanel"
            @open-image-panel="openImageInsertPanel"
            @open-shape-panel="openShapeInsertPanel"
            @select-background-panel="openBackgroundPanel"
          />

          <!-- Panel de Opciones (condicionalmente visible) -->
          <EditorContextPanel
            v-if="isOptionsPanelVisible"
            class="absolute inset-y-0 left-[70px] z-40 shadow-2xl"
            :state="state"
            :has-selection="hasSelection"
            :has-text-selection="hasTextSelection"
            :active-property-panel="activePropertyPanel"
            :active-property-title="activePropertyTitle"
            :text-panel-open="textPanelOpen"
            :image-panel-open="imagePanelOpen"
            :shape-panel-open="shapePanelOpen"
            :text-presets="textPresets"
            :image-panel-tabs="imagePanelTabs"
            :image-panel-tab="imagePanelTab"
            :image-url-input="imageUrlInput"
            :image-library="imageLibrary"
            :shape-category-filter="shapeCategoryFilter"
            :shape-categories="shapeCategories"
            :shape-style-from-kind="shapeStyleFromKind"
            :selected-element="selectedElement"
            :selected-element-type="selectedElementType"
            :background-has-image="backgroundHasImage"
            :selected-text-style="selectedTextStyle"
            :active-paragraph-label="activeParagraphLabel"
            :font-options="fontOptions"
            :color-options="colorOptions"
            :background-options="backgroundOptions"
            :design-color-options="designColorOptions"
            :design-gradient-options="designGradientOptions"
            :text-effect-rows="textEffectRows"
            :visual-effect-rows="visualEffectRows"
            :active-text-effect-id="activeTextEffectId"
            :active-visual-effect-id="activeVisualEffectId"
            :text-effect-card-font-family="textEffectCardFontFamily"
            :text-effect-preview-style="textEffectPreviewStyle"
            :visual-effect-preview-style="visualEffectPreviewStyle"
            :shape-gradient-options="shapeGradientOptions"
            :shape-gradient-directions="shapeGradientDirections"
            :normalize-picker-color="normalizePickerColor"
            :image-input-ref-setter="setImageInputRef"
            :add-text-element="addTextElement"
            :trigger-image-picker="triggerImagePicker"
            :on-image-picked="onImagePicked"
            :add-image-from-url="addImageFromUrl"
            :add-library-image="addLibraryImage"
            :add-uploaded-image="addUploadedImage"
            :get-upload-progress="getUploadProgress"
            :retry-uploaded-image="retryUploadedImage"
            :add-shape-element="addShapeElement"
            :apply-gradient-preset="applyGradientPreset"
            :apply-shape-gradient-preset="applyShapeGradientPreset"
            :swap-gradient-stops="swapGradientStops"
            :swap-shape-gradient-stops="swapShapeGradientStops"
            :set-text-effect="setTextEffect"
            :set-visual-effect="setVisualEffect"
            :set-selected-color="setSelectedColor"
            :change-layer="changeLayer"
            :toggle-selected-image-flip="toggleSelectedImageFlip"
            :reset-selected-image-crop="resetSelectedImageCrop"
            @close-panel="closeOptionsPanel"
            @update-image-panel-tab="imagePanelTab = $event"
            @update-image-url-input="imageUrlInput = $event"
            @update-shape-category-filter="shapeCategoryFilter = $event"
          />

          <EditorCanvasStage
            :canvas-grid-style="canvasGridStyle"
            :canvas-frame-style="canvasFrameStyle"
            :canvas-zoom-style="canvasZoomStyle"
            :is-background-selected="state.selectedElementId === 'background'"
            :canvas-background-style="canvasBackgroundStyle"
            :canvas-background-image-src="state.elementLayout.background?.backgroundImageSrc"
            :canvas-background-image-style="canvasBackgroundImageStyle"
            :canvas-element-style="canvasElementStyle"
            :editor-elements="editorElements"
            :drag="drag"
            :file-drag-active="fileDragActive"
            :background-drop-preview="backgroundDropPreview"
            :editing-element-id="editingElementId"
            :state="state"
            :element-box-style="elementBoxStyle"
            :is-element-selected="isElementSelected"
            :element-content-style="elementContentStyle"
            :rich-editor-container-style="richEditorContainerStyle"
            :neon-color-override="neonColorOverride"
            :image-frame-style="imageFrameStyle"
            :image-render-style="imageRenderStyle"
            :image-tint-overlay-style="imageTintOverlayStyle"
            :shape-style="shapeStyle"
            :shape-render-model="shapeRenderModel"
            :canvas-ref-setter="setCanvasRef"
            :rich-editor-ref-setter="setRichEditorRef"
            @canvas-pointer-down="handleCanvasPointerDown"
            @canvas-click="handleCanvasClick"
            @canvas-file-drag-enter="handleCanvasFileDragEnter"
            @canvas-file-drag-over="handleCanvasFileDragOver"
            @canvas-file-drag-leave="handleCanvasFileDragLeave"
            @canvas-file-drop="handleCanvasFileDrop"
            @element-click="handleElementClick($event.event, $event.id)"
            @begin-text-edit="beginTextEdit"
            @element-pointer-down="handleElementPointerDown($event.event, $event.id)"
            @rich-editor-text-update="onRichEditorTextUpdate($event.id, $event.value)"
            @rich-editor-styles-update="onRichEditorStylesUpdate($event.id, $event.value)"
            @rich-editor-selection-change="onRichEditorSelectionChange($event.id, $event.value)"
            @rich-editor-blur="onRichEditorBlur($event.id, $event.event)"
            @cancel-text-edit="cancelTextEdit"
            @commit-text-edit="commitTextEdit"
          >
            <template #overlay>
              <SelectionOverlay
                :show-selection-controls="!!(activeSelectionIds.length && state.selectedElementId !== 'background')"
                :show-marquee="selectionMarquee.active"
                :show-group-button="multiSelectionIds.length > 1"
                :show-edit-text-button="selectedElementType === 'text'"
                :overlay-control-target-id="overlayControlTargetId"
                :is-group-selection="isGroupSelection"
                :has-multi-selection="hasMultiSelection"
                :selected-element-type="selectedElementType"
                :selected-action-bar-style="selectedActionBarStyle"
                :selected-overlay-style="selectedOverlayStyle"
                :selected-handle-metrics="selectedHandleMetrics"
                :control-zoom-style="controlZoomStyle"
                :marquee-rect-style="marqueeRectStyle"
                @mark-editor-control-interaction="markEditorControlInteraction"
                @group-selected-elements="groupSelectedElements"
                @edit-selected-text-element="editSelectedTextElement"
                @clone-current-selection="cloneCurrentSelection"
                @delete-current-selection="deleteCurrentSelection"
                @start-rotate="startRotate($event.event, $event.id)"
                @reset-rotation="resetRotation"
                @start-resize="startResize($event.event, $event.id, $event.handle)"
              />
            </template>
          </EditorCanvasStage>
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
