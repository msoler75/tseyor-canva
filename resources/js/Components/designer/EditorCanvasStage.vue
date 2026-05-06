<script setup>
import { computed, defineAsyncComponent } from 'vue';
import { foldGuidePositionsForFormat } from '../../data/designer';
import { useLinkedTextBoxSystem } from '../../composables/useLinkedTextBoxSystem';
import { useFrontendLog } from '../../composables/useFrontendLog';

const RichTextEditor = defineAsyncComponent(() => import('./RichTextEditor.vue'));
const linkedTextBoxSystem = useLinkedTextBoxSystem();
const frontendLog = useFrontendLog();

const props = defineProps({
  canvasGridStyle: Object,
  canvasFrameStyle: [Object, Array],
  canvasZoomStyle: [Object, Array],
  isBackgroundSelected: Boolean,
  canvasBackgroundStyle: Object,
  canvasElementStyle: Object,
  editorElements: {
    type: Array,
    default: () => [],
  },
  drag: Object,
  fileDragActive: Boolean,
  backgroundDropPreview: Boolean,
  editingElementId: String,
  state: Object,
  elementBoxStyle: Function,
  isElementSelected: Function,
  elementContentStyle: Function,
  richEditorContainerStyle: Function,
  neonColorOverride: Function,
  imageFrameStyle: Function,
  imageRenderStyle: Function,
  imageTintOverlayStyle: Function,
  shapeStyle: Function,
  shapeRenderModel: Function,
  canvasBackgroundImageSrc: String,
  canvasBackgroundImageStyle: [Object, Array],
  templateMode: Boolean,
  templateWatermark: String,
  showFieldLabels: Boolean,
  hoveredFieldKey: String,
  activePage: Boolean,
  activePageId: String,
  showPermanentLinkLines: Boolean,
  canvasRefSetter: Function,
  richEditorRefSetter: Function,
  linkedTextLink: Object,
  activeLinkedTextBox: String,
});

const emit = defineEmits([
  'canvasPointerDown',
  'canvasClick',
  'elementClick',
  'beginTextEdit',
  'elementPointerDown',
  'richEditorTextUpdate',
  'richEditorStylesUpdate',
  'richEditorHtmlUpdate',
  'richEditorSelectionChange',
  'richEditorBlur',
  'cancelTextEdit',
  'commitTextEdit',
  'canvasFileDragEnter',
  'canvasFileDragOver',
  'canvasFileDragLeave',
  'canvasFileDrop',
  'linkedTextLinkStart',
  'fieldHover',
]);

const assignRichEditorRef = (id, element) => {
  if (!props.activePage) return;
  props.richEditorRefSetter?.(id, element);
};

const foldGuidePositions = computed(() => foldGuidePositionsForFormat(props.state?.format));
const PI = Math.PI;
const DEG_TO_RAD = PI / 180;
const layoutFor = (id) => {
  if (props.state?.elementLayout?.[id]) return props.state.elementLayout[id];
  for (const page of props.state?.pages ?? []) {
    if (page.elementLayout?.[id]) return page.elementLayout[id];
  }
  return null;
};
const elementFor = (id) => {
  if (props.state?.customElements?.[id]) return props.state.customElements[id];
  for (const page of props.state?.pages ?? []) {
    if (page.customElements?.[id]) return page.customElements[id];
  }
  return null;
};

// Función para rotar un punto (x,y) alrededor de un centro (cx,cy) por un ángulo en grados
const rotatePoint = (x, y, cx, cy, angleDeg) => {
  if (!angleDeg) return { x, y };
  const angleRad = angleDeg * DEG_TO_RAD;
  const dx = x - cx;
  const dy = y - cy;
  const cosA = Math.cos(angleRad);
  const sinA = Math.sin(angleRad);
  return {
    x: cx + dx * cosA - dy * sinA,
    y: cy + dx * sinA + dy * cosA,
  };
};

const getLinkSourcePosition = computed(() => {
  if (!props.linkedTextLink?.active || !props.linkedTextLink.sourceId) return null;
  const layout = layoutFor(props.linkedTextLink.sourceId);
  if (!layout) return null;
  // Botón en bottom-1 right-1 (24x24px). Tailwind bottom-1 = 4px, right-1 = 4px
  // Centro del botón: (x + w - 4px - 12px, y + h - 4px - 12px)
  const bw = 24, bh = 24;
  const offset = 4; // Tailwind bottom-1 right-1 = 4px
  const btnCenterX = layout.x + (layout.w ?? 300) - offset - bw/2;
  const btnCenterY = layout.y + (layout.h ?? 120) - offset - bh/2;
  // Aplicar rotación alrededor del centro de la caja
  const cx = layout.x + (layout.w ?? 300) / 2;
  const cy = layout.y + (layout.h ?? 120) / 2;
  return rotatePoint(btnCenterX, btnCenterY, cx, cy, layout.rotation ?? 0);
});

// Posición de destino: esquina superior izquierda de la caja destino (con rotación)
const getLinkTargetPosition = computed(() => {
  if (!props.linkedTextLink?.active) return null;
  const targetId = props.linkedTextLink.hoverTargetId || props.linkedTextLink.canvasTargetId;
  if (!targetId) {
    // Fallback: usar la posición del mouse
    if (props.linkedTextLink.canvasX !== undefined) {
      return { x: props.linkedTextLink.canvasX, y: props.linkedTextLink.canvasY };
    }
    return null;
  }
  const targetLayout = layoutFor(targetId);
  if (!targetLayout) return null;
  // Esquina superior izquierda (sin rotación)
  const x = targetLayout.x ?? 0;
  const y = targetLayout.y ?? 0;
  // Aplicar rotación alrededor del centro de la caja destino
  const cx = x + (targetLayout.w ?? 300) / 2;
  const cy = y + (targetLayout.h ?? 120) / 2;
  return rotatePoint(x, y, cx, cy, targetLayout.rotation ?? 0);
});

const permanentLinkLines = computed(() => {
  if (!props.showPermanentLinkLines) return [];
  const selectedId = props.state?.selectedElementId;
  if (!selectedId) return [];
  const allPages = props.state?.pages ?? [];
  const el = elementFor(selectedId);
  if (!el || el.type !== 'linkedText') return [];
  const layout = layoutFor(selectedId);
  const groupId = layout?.linkedTextGroupId;
  if (!groupId) return [];

  const lookupLayout = (id) => {
    return layoutFor(id);
  };

  const activePageIndex = allPages.findIndex(p => p.id === props.activePageId);
  const findElementPageIndex = (id) => {
    if (props.state?.elementLayout?.[id] || props.state?.customElements?.[id]) return activePageIndex;
    for (let i = 0; i < allPages.length; i++) {
      if (allPages[i].elementLayout?.[id] || allPages[i].customElements?.[id]) return i;
    }
    return activePageIndex;
  };
  const pageHeight = parseFloat(props.canvasElementStyle?.height) || 0;
  const pageGap = 32;

  const getElementYOffset = (id) => {
    const pageIdx = findElementPageIndex(id);
    return (pageIdx - activePageIndex) * (pageHeight + pageGap);
  };

  const chainIds = [];
  const visited = new Set();
  let current = selectedId;
  while (current && !visited.has(current)) {
    visited.add(current);
    const l = lookupLayout(current);
    if (!l) break;
    if (l.linkedTextPrev) {
      current = l.linkedTextPrev;
    } else {
      break;
    }
  }
  const head = current;
  current = head;
  visited.clear();
  while (current && !visited.has(current)) {
    visited.add(current);
    chainIds.push(current);
    const l = lookupLayout(current);
    if (!l) break;
    current = l.linkedTextNext;
  }
  const lines = [];
  const bw = 24, bh = 24;
  for (let i = 0; i < chainIds.length - 1; i++) {
    const a = lookupLayout(chainIds[i]);
    const b = lookupLayout(chainIds[i + 1]);
    if (!a || !b) continue;

    const allOnActivePage = findElementPageIndex(chainIds[i]) === activePageIndex
      && findElementPageIndex(chainIds[i + 1]) === activePageIndex;
    const offsetYA = allOnActivePage ? 0 : getElementYOffset(chainIds[i]);
    const offsetYB = allOnActivePage ? 0 : getElementYOffset(chainIds[i + 1]);

    const fin = (v, fallback) => Number.isFinite(v) ? v : fallback;

    const btnCenterX = fin(a.x, 0) + fin(a.w, 300) - bw/2;
    const btnCenterY = fin(a.y, 0) + fin(a.h, 120) - bh/2 + offsetYA;
    const cxA = fin(a.x, 0) + fin(a.w, 300) / 2;
    const cyA = fin(a.y, 0) + fin(a.h, 120) / 2 + offsetYA;
    const src = rotatePoint(btnCenterX, btnCenterY, cxA, cyA, fin(a.rotation, 0));

    const tx = fin(b.x, 0);
    const ty = fin(b.y, 0) + offsetYB;
    const cxB = tx + fin(b.w, 300) / 2;
    const cyB = ty + fin(b.h, 120) / 2;
    const tgt = rotatePoint(tx, ty, cxB, cyB, fin(b.rotation, 0));

    lines.push({ x1: src.x, y1: src.y, x2: tgt.x, y2: tgt.y });
  }
  return lines;
});

const getLinkedTextChainHead = (boxId) => {
  let currentId = boxId;
  const visited = new Set();
  while (currentId && !visited.has(currentId)) {
    visited.add(currentId);
    const l = layoutFor(currentId);
    if (!l) break;
    if (l.linkedTextPrev) {
      currentId = l.linkedTextPrev;
    } else {
      return currentId;
    }
  }
  return boxId;
};

const getLinkedTextStyleSourceId = (item) => {
  if (item?.type !== 'linkedText') return item?.id;
  const sourceId = item.linkedTextStyleSourceId || getLinkedTextChainHead(item.id);
  return layoutFor(sourceId) ? sourceId : item.id;
};

const getLinkedTextChain = (headId) => {
  const chain = [];
  let currentId = headId;
  const visited = new Set();
  while (currentId && !visited.has(currentId)) {
    visited.add(currentId);
    const l = layoutFor(currentId);
    if (!l) break;
    chain.push(currentId);
    currentId = l.linkedTextNext;
  }
  return chain;
};

const isLinkedTextInChainBeingEdited = (boxId) => {
  // Si no hay ninguna caja activa editándose, mostrar modo display para todas
  if (!props.activeLinkedTextBox) return true;

  // Si esta caja ES la que está siendo editada, NO está en modo display
  if (boxId === props.activeLinkedTextBox) return false;

  // Verificar que ambas cajas pertenecen al mismo grupo
  const boxLayout = layoutFor(boxId);
  const activeLayout = layoutFor(props.activeLinkedTextBox);

  if (!boxLayout?.linkedTextGroupId || !activeLayout?.linkedTextGroupId) return true;
  if (boxLayout.linkedTextGroupId !== activeLayout.linkedTextGroupId) return true;

  // Otra caja del mismo grupo está siendo editada, esta debe estar en modo display
  return true;
};

// Regla 3/4/6: Overflow visible solo cuando algún elemento de la cadena está seleccionado O en edición
const isLinkedTextChainActive = (boxId) => {
  const boxLayout = layoutFor(boxId);
  if (!boxLayout?.linkedTextGroupId) return false;

  // Si hay edición activa en cualquier caja de la cadena
  if (props.editingElementId) {
    const editingLayout = layoutFor(props.editingElementId);
    if (editingLayout?.linkedTextGroupId === boxLayout.linkedTextGroupId) {
      return true;
    }
  }

  // Si hay selección activa en cualquier caja de la cadena
  const selectedId = props.state?.selectedElementId;
  if (selectedId) {
    const selectedLayout = layoutFor(selectedId);
    if (selectedLayout?.linkedTextGroupId === boxLayout.linkedTextGroupId) {
      return true;
    }
  }

  return false;
};
</script>

<template>
  <div class="canvas-grid relative h-full overflow-auto bg-slate-100 px-4 pt-6 pb-28 [touch-action:pan-x_pan-y] dark:bg-slate-950 sm:px-10 sm:pt-16 sm:pb-10 md:px-10 md:pt-16 md:pb-10" :style="canvasGridStyle" @pointerdown="emit('canvasPointerDown', $event)">
    <div v-if="templateMode" class="pointer-events-none absolute inset-0 z-0 overflow-hidden">
      <div class="absolute inset-0 bg-[repeating-linear-gradient(-28deg,transparent_0,transparent_118px,rgba(15,23,42,0.055)_118px,rgba(15,23,42,0.055)_121px)] dark:bg-[repeating-linear-gradient(-28deg,transparent_0,transparent_118px,rgba(255,255,255,0.06)_118px,rgba(255,255,255,0.06)_121px)]"></div>
      <div class="grid min-h-full min-w-full content-start gap-x-24 gap-y-32 px-12 py-16 [grid-template-columns:repeat(auto-fill,minmax(300px,1fr))]">
        <span
          v-for="index in 28"
          :key="`template-grid-watermark-${index}`"
          class="block select-none whitespace-nowrap text-center text-[clamp(1.1rem,2.7vw,2.9rem)] font-black uppercase tracking-[0.32em] leading-none text-slate-900/10 dark:text-white/10 [transform:rotate(-28deg)] [transform-origin:center]"
        >
          {{ templateWatermark || 'PLANTILLA' }}
        </span>
      </div>
    </div>
    <div
      class="relative z-10 mx-auto shadow-2xl"
      :style="[canvasFrameStyle, canvasZoomStyle]"
      :class="[
        isBackgroundSelected ? 'ring-2 ring-primary' : '',
        activePage ? 'outline outline-4 outline-primary/70 outline-offset-4' : '',
      ]"
    >
      <div
        :ref="canvasRefSetter"
        data-editor-canvas="true"
        class="relative overflow-visible p-7 text-white select-none touch-none"
        :style="{ ...canvasBackgroundStyle, ...canvasElementStyle }"
        @pointerdown="emit('canvasPointerDown', $event)"
        @click="emit('canvasClick', $event)"
        @dragenter="emit('canvasFileDragEnter', $event)"
        @dragover="emit('canvasFileDragOver', $event)"
        @dragleave="emit('canvasFileDragLeave', $event)"
        @drop="emit('canvasFileDrop', $event)"
      >
        <div
          v-if="fileDragActive"
          class="pointer-events-none absolute inset-3 z-30 rounded-[28px] border-2 border-dashed shadow-[0_0_0_4px_rgba(34,211,238,0.15)]"
          :class="backgroundDropPreview ? 'border-fuchsia-300 bg-fuchsia-400/10' : 'border-cyan-300 bg-cyan-400/10'"
        >
          <div class="flex h-full w-full items-center justify-center">
            <div class="rounded-full bg-slate-950/70 px-4 py-2 text-sm font-semibold shadow-lg" :class="backgroundDropPreview ? 'text-fuchsia-100' : 'text-cyan-100'">
              {{ backgroundDropPreview ? 'Suelta para usarla como fondo' : 'Suelta aquí tus imágenes' }}
            </div>
          </div>
        </div>
        <div v-if="canvasBackgroundImageSrc" class="pointer-events-none absolute inset-0 overflow-hidden rounded-[inherit]">
          <img
            :src="canvasBackgroundImageSrc"
            alt="Fondo del diseño"
            class="pointer-events-none"
            :style="canvasBackgroundImageStyle"
            draggable="false"
          />
        </div>
        <div
          v-for="position in foldGuidePositions"
          :key="`fold-guide-${position}`"
          class="pointer-events-none absolute top-0 bottom-0 z-[60] w-0 -translate-x-1/2 border-l border-dashed border-white/75 mix-blend-difference"
          :style="{ left: `${position}%` }"
          aria-hidden="true"
        ></div>
        <div
          v-for="item in editorElements"
          :key="item.id"
          data-editor-element="true"
          :data-editor-id="item.id"
          class="group absolute p-0 text-left"
          :class="[(isElementSelected(item.id)
            ? (editingElementId === item.id
                ? 'ring-2 ring-cyan-300/70 bg-white/10 editor-editing-pulse'
                : (drag.active && drag.elementId === item.id
                    ? 'ring-2 ring-cyan-300/50 bg-white/10'
                    : 'ring-2 ring-cyan-300/50 bg-white/8'))
            : (showFieldLabels && item.fieldKey
                ? (item.fieldKey === props.hoveredFieldKey ? 'z-[70] ring-2 ring-accent/50 bg-accent/10' : 'z-50 ring-2 ring-accent/50 bg-accent/10')
                : (linkedTextLink?.active && linkedTextLink.hoverTargetId === item.id
                    ? 'z-40 ring-2 ring-emerald-400/70 bg-emerald-400/15'
                    : 'z-10'))),
            item.type === 'linkedText' && !item.text && editingElementId !== item.id ? 'linked-text-empty-box' : '']"
            :style="[elementBoxStyle(item.id), item.type === 'linkedText' && !item.text && editingElementId !== item.id ? { outline: '1px dashed rgba(255,255,255,0.3)', outlineOffset: '-1px' } : {}]"
          @click="emit('elementClick', { event: $event, id: item.id })"
          @pointerdown="emit('elementPointerDown', { event: $event, id: item.id })"
          @mouseenter="item.fieldKey && emit('fieldHover', item.fieldKey)"
          @mouseleave="item.fieldKey && emit('fieldHover', null)"
        >
          <div class="relative" :class="(item.type === 'text' || item.type === 'linkedText') ? '' : 'h-full w-full'" :style="elementContentStyle(item.id)">
            <div
              v-if="item.fieldKey"
              class="pointer-events-none absolute -top-6 left-0 z-[100] transition group-hover:z-[120] group-hover:opacity-100 isolate"
              :class="showFieldLabels ? 'opacity-100' : 'opacity-0'"
            >
              <span class="badge badge-xs badge-accent shadow-md">
                {{ item.label }}
              </span>
            </div>
            <template v-if="item.type === 'text' || item.type === 'linkedText'">
              <RichTextEditor
                :key="`${item.id}-${state.templateRevision ?? 0}`"
                :ref="activePage ? (el) => assignRichEditorRef(item.id, el) : null"
                :paragraph-styles="item.type === 'linkedText' ? (item.linkedTextParagraphStyles ?? []) : (layoutFor(item.id)?.paragraphStyles ?? [])"
                :text="item.text ?? ''"
                :editable="editingElementId === item.id"
                :editor-style="richEditorContainerStyle(getLinkedTextStyleSourceId(item))"
                :color-override="neonColorOverride(getLinkedTextStyleSourceId(item))"
                :transparent-fill="!!layoutFor(getLinkedTextStyleSourceId(item))?.hollowText"
                :is-linked-text="item.type === 'linkedText'"
                :linked-text-active="item.type === 'linkedText' && isLinkedTextChainActive(item.id)"
                :linked-text-next="item.type === 'linkedText' ? (layoutFor(item.id)?.linkedTextNext ?? null) : null"
                :box-dimensions="item.type === 'linkedText' ? { w: layoutFor(item.id)?.w, h: layoutFor(item.id)?.h, fontSize: layoutFor(item.id)?.fontSize, lineHeight: layoutFor(item.id)?.lineHeight } : null"
                :display-mode="item.type === 'linkedText' && editingElementId !== item.id && isLinkedTextInChainBeingEdited(item.id)"
                :initial-html="item.type === 'linkedText' ? (item.linkedTextInitialHtml ?? '') : ''"
                :display-html="item.type === 'linkedText' ? (item.linkedTextDisplayHtml ?? '') : ''"
                :overflow-html="item.type === 'linkedText' ? (item.linkedTextOverflowHtml ?? '') : ''"
                :full-text-html="item.type === 'linkedText' ? (item.linkedTextFullTextHtml ?? '') : ''"
                :tail-html="item.type === 'linkedText' ? (item.linkedTextTailHtml ?? '') : ''"
                :editor-top-offset="item.type === 'linkedText' ? (item.linkedTextEditorTopOffset ?? 0) : 0"
                :editor-text-offset="item.type === 'linkedText' ? (item.linkedTextEditorTextOffset ?? 0) : 0"
                :show-overflow="item.type === 'linkedText' && isLinkedTextChainActive(item.id) && item.linkedTextIsLastInChain"
                :is-last-in-chain="item.type === 'linkedText' ? (item.linkedTextIsLastInChain ?? false) : false"
                @update:text="emit('richEditorTextUpdate', { id: item.id, value: $event })"
                @update:paragraph-styles="emit('richEditorStylesUpdate', { id: item.id, value: $event })"
                @update:html="emit('richEditorHtmlUpdate', { id: item.id, value: $event })"
                @selection-change="emit('richEditorSelectionChange', { id: item.id, value: $event })"
                @blur="emit('richEditorBlur', { id: item.id, event: $event })"
                @keydown.escape.stop="emit('cancelTextEdit')"
                @keydown.ctrl.enter.stop="emit('commitTextEdit')"
                @keydown.meta.enter.stop="emit('commitTextEdit')"
                @pointerdown.stop="editingElementId === item.id ? null : emit('elementPointerDown', { event: $event, id: item.id })"
                @mousedown.stop
                @click.stop="editingElementId === item.id ? null : emit('elementClick', { event: $event, id: item.id })"
              />
              <button
                v-if="item.type === 'linkedText' && isElementSelected(item.id) && editingElementId !== item.id"
                type="button"
                class="linked-text-link-btn absolute -bottom-4 right-1 z-20 flex h-6 w-6 cursor-grab items-center justify-center rounded-full bg-primary/80 text-white shadow-md transition hover:bg-primary active:cursor-grabbing"
                title="Arrastra para conectar con otro texto enlazado"
                @pointerdown.stop="emit('linkedTextLinkStart', { event: $event, id: item.id })"
              >
                <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                </svg>
              </button>
            </template>
            <template v-else-if="item.type === 'image'">
              <div class="relative h-full w-full overflow-hidden rounded-xl" :style="imageFrameStyle(item.id)">
                <img
                  v-if="item.src"
                  :src="item.src"
                  :alt="item.label"
                  class="h-full w-full object-cover"
                  :style="imageRenderStyle ? imageRenderStyle(item.id) : null"
                  draggable="false"
                />
                <div
                  v-if="item.src && (layoutFor(item.id)?.imageTintStrength ?? 0) > 0"
                  class="pointer-events-none absolute inset-0"
                  :style="imageTintOverlayStyle(item.id)"
                ></div>
                <div v-else class="flex h-full w-full items-center justify-center text-xs font-semibold text-white/80">
                  Imagen
                </div>
              </div>
            </template>
            <template v-else>
              <div class="relative h-full w-full">
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
                <div class="relative h-full w-full" :style="shapeRenderModel(item).outerStyle"></div>
                <div
                  v-if="shapeRenderModel(item).innerStyle"
                  class="pointer-events-none absolute inset-0"
                  :style="shapeRenderModel(item).innerStyle"
                ></div>
              </div>
            </template>
          </div>
        </div>

        <svg
          v-if="linkedTextLink?.active && linkedTextLink.sourceId"
          class="pointer-events-none absolute inset-0 z-50 overflow-visible"
          style="width: 100%; height: 100%;"
        >
          <line
            v-if="getLinkSourcePosition && getLinkTargetPosition"
            :x1="getLinkSourcePosition.x"
            :y1="getLinkSourcePosition.y"
            :x2="getLinkTargetPosition.x"
            :y2="getLinkTargetPosition.y"
            stroke="currentColor"
            stroke-width="2"
            stroke-dasharray="5,5"
          />
        </svg>

        <svg
          v-if="permanentLinkLines.length"
          class="pointer-events-none absolute inset-0 z-40 overflow-visible"
          style="width: 100%; height: 100%;"
        >
          <line
            v-for="(line, idx) in permanentLinkLines"
            :key="idx"
            :x1="line.x1"
            :y1="line.y1"
            :x2="line.x2"
            :y2="line.y2"
            stroke="currentColor"
            stroke-width="2"
            stroke-dasharray="5,5"
            class="text-emerald-400"
          />
        </svg>

        <slot name="overlay" />
      </div>
    </div>
  </div>
</template>
