<script setup>
import { Icon } from '@iconify/vue';
import DesignerLayout from '../../Layouts/DesignerLayout.vue';
import StepFooter from '../../Components/designer/StepFooter.vue';
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useDesignerState } from '../../composables/useDesignerState';

defineProps({ currentStep: String, steps: Array, navigation: Object });
const state = useDesignerState();
const canvasRef = ref(null);
const elementMeasurements = reactive({});
const elementObservers = new Map();
const editInputRef = ref(null);
const editingElementId = ref(null);
const editingDraft = ref('');
const editingBoxHeight = ref(null);
const selectedParagraphIndex = ref(0);
const activePropertyPanel = ref('typography');
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
const propertyTabs = [
    { id: 'typography', label: 'Fuente' , class: 'order-first'},
    { id: 'color', label: 'A', labelClass:'border-b-5 border-blue-500 text-xl',class: '' },
    { id: 'opacity', icon: 'carbon:opacity', class: 'order-last' },
    { id: 'effects', label: 'Efectos', class: 'order-last' },
    { id: 'arrange', label: 'Posición' , class: 'order-last'},
];

const metaLine = computed(() => [state.content.date, state.content.time].filter(Boolean).join(' · '));
const editorElements = computed(() => [
    { id: 'title', label: 'Título', text: state.content.title },
    { id: 'subtitle', label: 'Subtítulo', text: state.content.subtitle },
    { id: 'meta', label: 'Fecha / hora', text: metaLine.value },
    { id: 'contact', label: 'Contacto', text: state.content.contact },
    { id: 'extra', label: 'Texto adicional', text: state.content.extra },
].sort((a, b) => (state.elementLayout[a.id]?.zIndex ?? 0) - (state.elementLayout[b.id]?.zIndex ?? 0)));
const selectedElement = computed(() => state.elementLayout[state.selectedElementId]);
const hasSelection = computed(() => Boolean(state.selectedElementId && selectedElement.value));
const activeElementLabel = computed(() => editorElements.value.find((item) => item.id === state.selectedElementId)?.label ?? 'Elemento');
const orderedLayerIds = computed(() => Object.keys(state.elementLayout).sort((a, b) => {
    const zA = state.elementLayout[a]?.zIndex ?? 0;
    const zB = state.elementLayout[b]?.zIndex ?? 0;

    if (zA === zB) {
        return a.localeCompare(b);
    }

    return zA - zB;
}));

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
    return editingElementId.value === state.selectedElementId ? editingDraft.value : getElementText(state.selectedElementId);
};
const getParagraphStyleForElement = (id, index = 0, text = null) => {
    const layout = state.elementLayout[id];
    if (!layout) return null;

    const sourceText = text ?? (editingElementId.value === id ? editingDraft.value : getElementText(id));
    const styles = ensureParagraphStyles(layout, sourceText);

    return styles[clamp(index, 0, Math.max(0, styles.length - 1))] ?? buildParagraphStyle(layout);
};
const getActiveParagraphStyle = () => {
    if (!selectedElement.value) return null;

    const styles = ensureParagraphStyles(selectedElement.value, getTextSourceForSelectedElement());
    selectedParagraphIndex.value = clamp(selectedParagraphIndex.value, 0, Math.max(0, styles.length - 1));

    return styles[selectedParagraphIndex.value] ?? buildParagraphStyle(selectedElement.value);
};
const selectedTextStyle = computed(() => getActiveParagraphStyle());
const paragraphCount = computed(() => {
    if (!selectedElement.value) return 0;
    return ensureParagraphStyles(selectedElement.value, getTextSourceForSelectedElement()).length;
});
const activeParagraphLabel = computed(() => paragraphCount.value ? `Párrafo ${selectedParagraphIndex.value + 1} de ${paragraphCount.value}` : 'Párrafo 1 de 1');
const getParagraphIndexFromCursor = (text, cursor = 0) => {
    const safeText = String(text ?? '');
    const safeCursor = clamp(cursor, 0, safeText.length);
    return safeText.slice(0, safeCursor).split('\n').length - 1;
};
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
        if (!selectedTextStyle.value) return;
        selectedTextStyle.value[field] = value;
        return;
    }

    if (!selectedElement.value) return;
    selectedElement.value[field] = value;
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

const elementBoxStyle = (id) => {
    const layout = state.elementLayout[id];

    return {
        left: `${layout.x}px`,
        top: `${layout.y}px`,
        width: `${layout.w}px`,
        zIndex: `${layout.zIndex ?? 1}`,
    };
};

const getEstimatedTextHeight = (layout, text = '') => ensureParagraphStyles(layout, text)
    .reduce((total, style) => total + Math.max((style.fontSize ?? layout.fontSize ?? 16) * (style.lineHeight ?? 1.3), 16), 0);

const selectedOverlayStyle = computed(() => {
    if (!state.selectedElementId) {
        return {};
    }

    const layout = state.elementLayout[state.selectedElementId];
    const text = editingElementId.value === state.selectedElementId ? editingDraft.value : getElementText(state.selectedElementId);
    const measured = elementMeasurements[state.selectedElementId] ?? null;
    const measuredWidth = measured?.width ?? layout.w;
    const measuredHeight = measured?.height ?? getEstimatedTextHeight(layout, text);

    return {
        left: `${layout.x}px`,
        top: `${layout.y}px`,
        width: `${measuredWidth}px`,
        height: `${measuredHeight}px`,
        zIndex: '6000',
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

const elementEditInputStyle = (id) => {
    const layout = state.elementLayout[id];
    const paragraphStyle = id === state.selectedElementId ? selectedTextStyle.value : getParagraphStyleForElement(id, 0);

    return {
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
        opacity: `${(layout.opacity ?? 100) / 100}`,
        minHeight: editingElementId.value === id && editingBoxHeight.value
            ? `${Math.max(editingBoxHeight.value, (paragraphStyle?.fontSize ?? layout.fontSize) * (paragraphStyle?.lineHeight ?? layout.lineHeight ?? 1.3))}px`
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
            return '';
    }
};

const selectParagraph = (id, index = 0) => {
    state.selectedElementId = id;
    selectedParagraphIndex.value = index;
};

const syncEditingParagraphState = () => {
    if (!editingElementId.value || !selectedElement.value) return;

    ensureParagraphStyles(selectedElement.value, editingDraft.value);

    const input = editInputRef.value;
    if (input && typeof input.selectionStart === 'number') {
        selectedParagraphIndex.value = clamp(
            getParagraphIndexFromCursor(editingDraft.value, input.selectionStart),
            0,
            Math.max(0, paragraphCount.value - 1)
        );
    }
};

const beginTextEdit = async (id) => {
    state.selectedElementId = id;
    editingBoxHeight.value = elementMeasurements[id]?.height ?? null;
    editingDraft.value = getElementText(id);
    ensureParagraphStyles(state.elementLayout[id], editingDraft.value);
    selectedParagraphIndex.value = 0;
    editingElementId.value = id;
    clearLongPress();
    await nextTick();
    syncEditingParagraphState();
    editInputRef.value?.focus();
    editInputRef.value?.select?.();
};

const commitTextEdit = () => {
    if (!editingElementId.value) return;
    const value = String(editingDraft.value ?? '').replace(/\r\n/g, '\n');

    switch (editingElementId.value) {
        case 'title':
        case 'subtitle':
        case 'contact':
        case 'extra':
            state.content[editingElementId.value] = value;
            break;
        case 'meta': {
            const [datePart, ...rest] = value.split('·');
            state.content.date = (datePart ?? '').trim();
            state.content.time = rest.join('·').trim();
            break;
        }
    }

    editingElementId.value = null;
    editingBoxHeight.value = null;
};

const cancelTextEdit = () => {
    editingElementId.value = null;
    editingBoxHeight.value = null;
};
const onEditorKeydown = (event) => {
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
    if (event.pointerType !== 'touch' || drag.active) return;
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
    drag.startFontSize = layout.fontSize;
    drag.startParagraphStyles = ensureParagraphStyles(layout, getElementText(id)).map((style) => ({ ...style }));
    clearLongPress();
    setDragDocumentState(true);

    event.currentTarget?.setPointerCapture?.(event.pointerId);
    event.stopPropagation();
    event.preventDefault();
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

    if (drag.mode === 'resize') {
        if (event.cancelable) event.preventDefault();
        const deltaX = event.clientX - drag.startClientX;
        const deltaY = event.clientY - drag.startClientY;
        const handle = drag.handle ?? 'se';
        const isSideHandle = handle === 'e' || handle === 'w';
        const horizontalDelta = handle.includes('e') ? deltaX : -deltaX;

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
    layout.y = Math.round(clamp(drag.startY + deltaY, 18, Math.max(18, rect.height - 44)));
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
    clearLongPress();
    setDragDocumentState(false);
};

const cycleAlignment = () => {
    const order = ['left', 'center', 'right', 'justify'];
    if (!selectedTextStyle.value) return;
    const index = order.indexOf(selectedTextStyle.value.textAlign ?? 'left');
    selectedTextStyle.value.textAlign = order[(index + 1) % order.length];
};

const currentAlignmentIcon = computed(() => {
    const icons = {
        left: 'ph:text-align-left',
        center: 'ph:text-align-center',
        right: 'ph:text-align-right',
        justify: 'ph:text-align-justify',
    };

    return icons[selectedTextStyle.value?.textAlign ?? 'left'];
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
};

const handleCanvasPointerDown = (event) => {
    if (drag.active) return;
    if (event.target.closest('[data-editor-element="true"]') || event.target.closest('[data-editor-control="true"]')) return;
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

watch(editingDraft, () => {
    if (editingElementId.value) {
        syncEditingParagraphState();
    }
});
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
                    <button v-for="tab in propertyTabs" :key="tab.id" type="button" class="btn border-0 py-1 px-2" :class="[activePropertyPanel === tab.id ? 'btn-primary' : 'btn-outline', tab.class]"
                        @click="activePropertyPanel = tab.id">
                        <span v-if="tab.label" class="text-sm text-base-100-accent" :class="tab.labelClass">{{ tab.label }}</span>
                        <Icon v-if="tab.icon" :icon="tab.icon" class="text-2xl"/>
                    </button>
                    <input v-model="selectedTextStyle.fontSize" type="number" min="8" max="200" step="1" class="input input-bordered join-item w-12 text-center order-first" />
                    <button type="button" class="btn text-lg" :class="selectedTextStyle.fontWeight === 'bold' ? 'btn-primary' : 'btn-outline'" @click="selectedTextStyle.fontWeight = selectedTextStyle.fontWeight === 'bold' ? 'regular' : 'bold'">B</button>
                    <button type="button" class="btn text-lg italic" :class="selectedTextStyle.italic ? 'btn-primary' : 'btn-outline'" @click="selectedTextStyle.italic = !selectedTextStyle.italic">I</button>
                    <button type="button" class="btn text-lg w-12" :class="selectedTextStyle.uppercase ? 'btn-primary' : 'btn-outline'" @click="selectedTextStyle.uppercase = !selectedTextStyle.uppercase">Aa</button>
                    <button type="button" class="btn text-lg btn-outline" @click="cycleAlignment">
                        <Icon :icon="currentAlignmentIcon" class="scale-150"/>
                    </button>
                    <span class="rounded-full border border-base-300 bg-base-100 px-2 py-1 text-[11px] font-medium text-base-content/70">{{ activeParagraphLabel }}</span>
                </div>
            </div>
          </div>
        </div>

        <div class="grid gap-0 xl:grid-cols-[320px_1fr]">
          <aside data-editor-keep-selection="true" class="border-b border-base-300 bg-base-100 p-5 xl:border-b-0 xl:border-r">
            <div class="space-y-5">
              <div>
                <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Panel contextual</p>
                <h3 class="mt-2 text-xl font-semibold text-base-content">{{ propertyTabs.find((tab) => tab.id === activePropertyPanel)?.label }}</h3>
                <p class="mt-2 text-sm leading-6 text-base-content/75">Elige una propiedad arriba para ver sus opciones.</p>
              </div>

              <div v-if="!hasSelection" class="alert border border-base-300 bg-base-100/80 text-sm leading-6 text-base-content/80">
                Selecciona una caja de texto para ver y editar sus propiedades.
              </div>

              <div v-else-if="activePropertyPanel === 'typography'" class="card border border-base-300 bg-base-100/80">
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
                      <input v-model="selectedTextStyle.letterSpacing" type="range" min="-5" max="40" step="1" class="range range-primary flex-1" />
                      <input v-model="selectedTextStyle.letterSpacing" type="number" min="-5" max="40" step="1" class="input input-bordered input-sm w-20" />
                    </div>
                  </div>
                  <div class="mt-4 space-y-3">
                    <label class="block text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Interlineado</label>
                    <div class="flex items-center gap-3">
                      <input v-model="selectedTextStyle.lineHeight" type="range" min="0.6" max="3" step="0.1" class="range range-primary flex-1" />
                      <input v-model="selectedTextStyle.lineHeight" type="number" min="0.6" max="3" step="0.1" class="input input-bordered input-sm w-20" />
                    </div>
                  </div>
                </div>
              </div>

              <div v-else-if="activePropertyPanel === 'color'" class="card border border-base-300 bg-base-100/80">
                <div class="card-body p-4 space-y-4">
                  <div>
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
                </div>
              </div>

              <div v-else-if="activePropertyPanel === 'effects'" class="card border border-base-300 bg-base-100/80">
                <div class="card-body p-4 space-y-4">
                  <p class="text-xs font-medium text-primary/80">Estos efectos se aplican a todo el objeto de texto.</p>
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
                Doble click para editar texto. Enter crea un nuevo parrafo; al hacer clic fuera, el texto se guarda automaticamente. Ctrl+Enter tambien confirma y Esc cancela. En touch, mantén pulsado para editar. Usa el icono inferior para mover y las esquinas para redimensionar.
              </div>
            </div>
          </aside>

          <div class="canvas-grid min-h-[680px] bg-slate-100 p-6 dark:bg-slate-950 sm:p-10">
            <div class="mx-auto max-w-[400px] bg-white p-4 shadow-2xl dark:bg-slate-900">
              <div ref="canvasRef" class="relative h-[620px] overflow-hidden bg-gradient-to-br from-indigo-800 via-violet-700 to-fuchsia-600 p-7 text-white select-none touch-none" @pointerdown="handleCanvasPointerDown">
                <button
                  type="button"
                  class="absolute inset-0 z-0 cursor-default bg-transparent"
                  aria-label="Deseleccionar elemento"
                  @pointerdown.stop="clearSelection"
                ></button>

                <button
                  v-for="item in editorElements"
                  :key="item.id"
                  type="button"
                  data-editor-element="true"
                  :data-editor-id="item.id"
                  class="absolute rounded-[18px] p-0 text-left transition"
                  :style="elementBoxStyle(item.id)"
                  :class="state.selectedElementId === item.id
                    ? (drag.active && drag.elementId === item.id
                        ? 'border-2 border-dashed border-cyan-300 bg-white/10 shadow-[0_0_0_3px_rgba(103,232,249,.18)]'
                        : 'border-2 border-dashed border-cyan-300 bg-white/8 shadow-[0_0_0_3px_rgba(103,232,249,.18)]')
                    : 'z-10 border border-transparent hover:border-white/20'"
                  @click="selectParagraph(item.id, 0)"
                  @dblclick="beginTextEdit(item.id)"
                  @pointerdown="startTouchEditIntent($event, item.id)"
                >
                  <div class="relative" :style="elementContentStyle(item.id)">
                  <textarea
                    v-if="editingElementId === item.id"
                    ref="editInputRef"
                    v-model="editingDraft"
                    class="block min-h-[3.5rem] w-full resize-none border-none bg-transparent p-0 placeholder:text-white/55 focus:bg-transparent focus:outline-none"
                    :style="elementEditInputStyle(item.id)"
                    @input="syncEditingParagraphState"
                    @click="syncEditingParagraphState"
                    @keyup="syncEditingParagraphState"
                    @select="syncEditingParagraphState"
                    @blur="commitTextEdit"
                    @keydown="onEditorKeydown"
                  ></textarea>
                  <template v-else>
                    <span
                      v-for="(paragraph, index) in getParagraphs(item.text)"
                      :key="`${item.id}-${index}`"
                      class="block cursor-text whitespace-pre-wrap"
                      :style="paragraphContentStyle(item.id, index, item.text)"
                      @pointerdown.stop="selectParagraph(item.id, index)"
                      @click.stop="selectParagraph(item.id, index)"
                    >{{ paragraph || '\u00A0' }}</span>
                  </template>
                  </div>
                </button>

                <div v-if="state.selectedElementId" data-editor-control="true" class="pointer-events-none absolute" :style="selectedOverlayStyle">
                  <span class="pointer-events-none absolute -top-10 left-0 rounded-full bg-cyan-300 px-3 py-1 text-xs font-semibold text-slate-950">{{ activeElementLabel }} seleccionado</span>
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
