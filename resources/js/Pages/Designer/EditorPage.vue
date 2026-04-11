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
});
const touchIntent = reactive({
    pointerId: null,
    startX: 0,
    startY: 0,
});

const colorOptions = ['#ffffff', '#c4b5fd', '#f9a8d4', '#67e8f9', '#fde68a', '#1f2937', '#7c3aed', '#0ea5e9', '#10b981', '#f97316'];
const backgroundOptions = ['transparent', '#ffffff', '#111827', '#7c3aed', '#0ea5e9', '#10b981', '#fef3c7', '#fecdd3'];
const fontOptions = ['Poppins, sans-serif', 'Montserrat, sans-serif', 'Inter, sans-serif', 'Georgia, serif'];
const propertyTabs = [
    { id: 'typography', label: 'Fuente' , class: 'order-first'},
    { id: 'color', label: 'A', labelClass:'border-b-5 border-blue-500 text-xl',class: 'order-first' },
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

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
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

const selectedOverlayStyle = computed(() => {
    if (!state.selectedElementId) {
        return {};
    }

    const layout = state.elementLayout[state.selectedElementId];
    const measured = elementMeasurements[state.selectedElementId] ?? null;
    const measuredWidth = measured?.width ?? layout.w;
    const measuredHeight = measured?.height ?? layout.fontSize * (layout.lineHeight ?? 1.3);

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
        fontSize: `${layout.fontSize}px`,
        color: layout.color,
        fontFamily: layout.fontFamily ?? 'Inter, sans-serif',
        fontStyle: layout.italic ? 'italic' : 'normal',
        fontWeight: layout.fontWeight === 'bold' ? '700' : '500',
        textAlign: layout.textAlign ?? 'left',
        textTransform: layout.uppercase ? 'uppercase' : 'none',
        letterSpacing: `${layout.letterSpacing ?? 0}px`,
        lineHeight: `${layout.lineHeight ?? 1.3}`,
        opacity: `${(layout.opacity ?? 100) / 100}`,
        backgroundColor: layout.backgroundColor && layout.backgroundColor !== 'transparent' ? layout.backgroundColor : 'transparent',
        borderRadius: layout.backgroundColor && layout.backgroundColor !== 'transparent' ? '16px' : '0',
        padding: '0',
        textShadow: buildTextShadow(layout),
        WebkitTextStroke: layout.border ? `${layout.contourWidth || 1}px ${layout.contourColor || '#ffffff'}` : '0',
        boxShadow: buildBubbleShadow(layout),
    };
};

const setDragDocumentState = (active) => {
    document.documentElement.style.userSelect = active ? 'none' : '';
    document.documentElement.style.touchAction = active ? 'none' : '';
    document.body.style.overflow = active ? 'hidden' : '';
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

const beginTextEdit = async (id) => {
    state.selectedElementId = id;
    editingElementId.value = id;
    editingDraft.value = getElementText(id);
    clearLongPress();
    await nextTick();
    editInputRef.value?.focus();
    editInputRef.value?.select?.();
};

const commitTextEdit = () => {
    if (!editingElementId.value) return;
    const value = editingDraft.value.trim();

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
};

const cancelTextEdit = () => { editingElementId.value = null; };
const onEditorKeydown = (event) => {
    if (event.key === 'Escape') return cancelTextEdit();
    if (event.key === 'Enter' && !event.shiftKey) {
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
        const horizontalDelta = handle.includes('e') ? deltaX : -deltaX;
        const widthDelta = horizontalDelta + (deltaY * 0.35);
        const nextWidth = clamp(Math.round(drag.startW + widthDelta), 120, 340);

        layout.w = nextWidth;
        layout.fontSize = clamp(Math.round(drag.startFontSize * (nextWidth / drag.startW)), 14, 72);

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
    if (!selectedElement.value) return;
    const index = order.indexOf(selectedElement.value.textAlign ?? 'left');
    selectedElement.value.textAlign = order[(index + 1) % order.length];
};

const currentAlignmentIcon = computed(() => {
    const icons = {
        left: 'ph:text-align-left',
        center: 'ph:text-align-center',
        right: 'ph:text-align-right',
        justify: 'ph:text-align-justify',
    };

    return icons[selectedElement.value?.textAlign ?? 'left'];
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
    state.selectedElementId = null;
    cancelTextEdit();
};

const handleCanvasPointerDown = (event) => {
    if (drag.active) return;
    if (event.target.closest('[data-editor-element="true"]') || event.target.closest('[data-editor-control="true"]')) return;
    clearSelection();
};

const handleGlobalPointerDown = (event) => {
    if (drag.active || !state.selectedElementId) return;

    const interactiveTarget = event.target.closest(
        '[data-editor-element="true"],[data-editor-control="true"],button,input,textarea,select,label,a,[role="button"]'
    );

    if (interactiveTarget) {
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
          class="pointer-events-none absolute z-[7000]"
          :style="{ left: toolbarPosition.x + 'px', top: toolbarPosition.y + 'px' }"
        >
          <div class="pointer-events-auto card glass soft-shadow border border-base-300/70 bg-base-100/90">
            <div class="card-body p-3">
          <div class="flex flex-wrap items-center gap-4">
              <button type="button" class="order-first btn btn-ghost btn-sm cursor-grab active:cursor-grabbing rounded-full" @pointerdown="startToolbarDrag">⋮⋮</button>
              <button v-for="tab in propertyTabs" :key="tab.id" type="button" class="btn border-0 py-1 px-2" :class="[activePropertyPanel === tab.id ? 'btn-primary' : 'btn-outline',
              tab.class
              ]" @click="activePropertyPanel = tab.id">
                <span v-if="tab.label" class="text-sm text-base-100-accent" :class="tab.labelClass">{{ tab.label }}</span>
                <Icon v-if="tab.icon" :icon="tab.icon" class="text-2xl"/>
              </button>
                <input v-model="selectedElement.fontSize" type="number" min="8" max="200" step="1" class="input input-bordered join-item w-12 text-center" />
                <button type="button" class="btn btn-lg" :class="selectedElement.fontWeight === 'bold' ? 'btn-primary' : 'btn-outline'" @click="selectedElement.fontWeight = selectedElement.fontWeight === 'bold' ? 'regular' : 'bold'">B</button>
                <button type="button" class="btn btn-lg italic" :class="selectedElement.italic ? 'btn-primary' : 'btn-outline'" @click="selectedElement.italic = !selectedElement.italic">I</button>
                <button type="button" class="btn btn-lg" :class="selectedElement.uppercase ? 'btn-primary' : 'btn-outline'" @click="selectedElement.uppercase = !selectedElement.uppercase">Aa</button>
                <button type="button" class="btn btn-lg btn-outline" @click="cycleAlignment">
                    <Icon :icon="currentAlignmentIcon" class="scale-150"/></button>
          </div>
            </div>
          </div>
        </div>

        <div class="grid gap-0 xl:grid-cols-[320px_1fr]">
          <aside class="border-b border-base-300 bg-base-100 p-5 xl:border-b-0 xl:border-r">
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
                  <p class="text-sm font-semibold text-base-content">Tipo de fuente</p>
                  <div class="mt-3 flex flex-wrap gap-2">
                    <button v-for="font in fontOptions" :key="font" type="button" class="btn btn-outline btn-sm rounded-full" :class="selectedElement.fontFamily === font ? 'btn-primary' : ''" @click="selectedElement.fontFamily = font">{{ font.split(',')[0] }}</button>
                  </div>
                  <div class="mt-4 space-y-3">
                    <label class="block text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Interletrado</label>
                    <div class="flex items-center gap-3">
                      <input v-model="selectedElement.letterSpacing" type="range" min="-5" max="40" step="1" class="range range-primary flex-1" />
                      <input v-model="selectedElement.letterSpacing" type="number" min="-5" max="40" step="1" class="input input-bordered input-sm w-20" />
                    </div>
                  </div>
                  <div class="mt-4 space-y-3">
                    <label class="block text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Interlineado</label>
                    <div class="flex items-center gap-3">
                      <input v-model="selectedElement.lineHeight" type="range" min="0.6" max="3" step="0.1" class="range range-primary flex-1" />
                      <input v-model="selectedElement.lineHeight" type="number" min="0.6" max="3" step="0.1" class="input input-bordered input-sm w-20" />
                    </div>
                  </div>
                </div>
              </div>

              <div v-else-if="activePropertyPanel === 'color'" class="card border border-base-300 bg-base-100/80">
                <div class="card-body p-4">
                  <p class="text-sm font-semibold text-base-content">Color del texto</p>
                  <div class="mt-4 grid grid-cols-5 gap-3">
                    <button v-for="color in colorOptions" :key="color" type="button" class="h-10 w-10 rounded-full ring-2 ring-slate-200 dark:ring-slate-700" :style="{ backgroundColor: color }" @click="selectedElement.color = color"></button>
                  </div>
                </div>
              </div>

              <div v-else-if="activePropertyPanel === 'effects'" class="card border border-base-300 bg-base-100/80">
                <div class="card-body p-4 space-y-4">
                  <div>
                    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Sombra</p>
                    <div class="mt-2 flex flex-wrap gap-2">
                      <button type="button" class="btn btn-outline btn-sm rounded-full" :class="selectedElement.shadow && selectedElement.shadowPreset === 'soft' ? 'btn-primary' : ''" @click="selectedElement.shadow = true; selectedElement.shadowPreset = 'soft'">Suave</button>
                      <button type="button" class="btn btn-outline btn-sm rounded-full" :class="selectedElement.shadow && selectedElement.shadowPreset === 'hard' ? 'btn-primary' : ''" @click="selectedElement.shadow = true; selectedElement.shadowPreset = 'hard'">Dura</button>
                      <button type="button" class="btn btn-outline btn-sm rounded-full" :class="selectedElement.shadow && selectedElement.shadowPreset === 'lifted' ? 'btn-primary' : ''" @click="selectedElement.shadow = true; selectedElement.shadowPreset = 'lifted'">Elevada</button>
                      <button type="button" class="btn btn-outline btn-sm rounded-full" @click="selectedElement.shadow = false">Sin sombra</button>
                    </div>
                    <div class="mt-3 flex flex-wrap gap-2">
                      <button v-for="color in colorOptions" :key="'shadow-' + color" type="button" class="h-8 w-8 rounded-full ring-2 ring-slate-200 dark:ring-slate-700" :style="{ backgroundColor: color }" @click="selectedElement.shadowColor = color"></button>
                    </div>
                  </div>

                  <div>
                    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Contorno</p>
                    <div class="mt-2 flex flex-wrap gap-2">
                      <button type="button" class="btn btn-outline btn-sm rounded-full" @click="selectedElement.border = !selectedElement.border">{{ selectedElement.border ? 'Quitar' : 'Activar' }}</button>
                      <button type="button" class="btn btn-outline btn-sm rounded-full" @click="selectedElement.contourWidth = clamp((selectedElement.contourWidth || 0) - 1, 0, 12)">Grosor -</button>
                      <button type="button" class="btn btn-outline btn-sm rounded-full" @click="selectedElement.contourWidth = clamp((selectedElement.contourWidth || 0) + 1, 0, 12)">Grosor +</button>
                    </div>
                    <div class="mt-3 flex flex-wrap gap-2">
                      <button v-for="color in colorOptions" :key="'contour-' + color" type="button" class="h-8 w-8 rounded-full ring-2 ring-slate-200 dark:ring-slate-700" :style="{ backgroundColor: color }" @click="selectedElement.contourColor = color"></button>
                    </div>
                  </div>

                  <div>
                    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Neón</p>
                    <div class="mt-2 flex flex-wrap gap-2">
                      <button v-for="color in colorOptions" :key="'neon-' + color" type="button" class="h-8 w-8 rounded-full ring-2 ring-slate-200 dark:ring-slate-700" :style="{ backgroundColor: color }" @click="selectedElement.neonColor = color"></button>
                    </div>
                  </div>

                  <div>
                    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Burbuja</p>
                    <div class="mt-2 flex flex-wrap gap-2">
                      <button v-for="color in backgroundOptions" :key="'bubble-' + color" type="button" class="h-8 w-8 rounded-full ring-2 ring-slate-200 dark:ring-slate-700" :style="{ backgroundColor: color === 'transparent' ? '#ffffff' : color }" @click="selectedElement.bubbleColor = color"></button>
                    </div>
                  </div>

                  <div>
                    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Fondo</p>
                    <div class="mt-2 flex flex-wrap gap-2">
                      <button v-for="color in backgroundOptions" :key="'bg-' + color" type="button" class="h-8 w-8 rounded-full ring-2 ring-slate-200 dark:ring-slate-700" :style="{ backgroundColor: color === 'transparent' ? '#ffffff' : color }" @click="selectedElement.backgroundColor = color"></button>
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
                Doble click para editar texto. En touch, mantén pulsado para editar. Usa el icono inferior para mover y las esquinas para redimensionar.
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
                  @click="state.selectedElementId = item.id"
                  @dblclick="beginTextEdit(item.id)"
                  @pointerdown="startTouchEditIntent($event, item.id)"
                >
                  <div class="relative" :style="elementContentStyle(item.id)">
                  <textarea v-if="editingElementId === item.id" ref="editInputRef" v-model="editingDraft" class="textarea textarea-ghost block min-h-[3.5rem] w-full resize-none border-none bg-transparent p-0 font-inherit text-inherit placeholder:text-white/55 focus:bg-transparent focus:outline-none" :style="{ textAlign: selectedElement.textAlign ?? 'left' }" @blur="commitTextEdit" @keydown="onEditorKeydown"></textarea>
                  <span v-else class="block">{{ item.text }}</span>
                  </div>
                </button>

                <div v-if="state.selectedElementId" data-editor-control="true" class="pointer-events-none absolute" :style="selectedOverlayStyle">
                  <span class="pointer-events-none absolute -top-10 left-0 rounded-full bg-cyan-300 px-3 py-1 text-xs font-semibold text-slate-950">{{ activeElementLabel }} seleccionado</span>
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
