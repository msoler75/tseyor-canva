<script setup>
import { Icon } from '@iconify/vue';

defineProps({
  showSelectionControls: Boolean,
  showMarquee: Boolean,
  showGroupButton: Boolean,
  showEditTextButton: Boolean,
  overlayControlTargetId: String,
  isGroupSelection: Boolean,
  hasMultiSelection: Boolean,
  selectedElementType: String,
  selectedActionBarStyle: [Object, Array],
  selectedOverlayStyle: [Object, Array],
  selectedHandleMetrics: Object,
  controlZoomStyle: [Object, Array],
  marqueeRectStyle: [Object, Array],
});

const emit = defineEmits([
  'markEditorControlInteraction',
  'groupSelectedElements',
  'editSelectedTextElement',
  'cloneCurrentSelection',
  'deleteCurrentSelection',
  'startRotate',
  'resetRotation',
  'startResize',
]);
</script>

<template>
  <template v-if="showSelectionControls">
    <div
      data-editor-control="true"
      class="pointer-events-none absolute"
      :style="selectedActionBarStyle"
    >
      <div class="pointer-events-auto card glass soft-shadow border border-base-300/70 bg-base-100/90 text-base-content" :style="controlZoomStyle">
        <div class="flex items-center gap-1 p-1.5">
          <button
            v-if="showGroupButton"
            data-editor-control="true"
            type="button"
            class="btn btn-ghost btn-sm font-semibold"
            title="Agrupar elementos"
            @pointerdown.stop="emit('markEditorControlInteraction')"
            @click.stop="emit('groupSelectedElements')"
          >
            agrupar
          </button>
          <button
            v-if="showEditTextButton"
            data-editor-control="true"
            type="button"
            class="btn btn-ghost btn-sm"
            title="Editar texto"
            @pointerdown.stop="emit('markEditorControlInteraction')"
            @click.stop="emit('editSelectedTextElement')"
          >
            <Icon icon="ph:pencil-simple-bold" class="text-base" />
          </button>
          <button
            data-editor-control="true"
            type="button"
            class="btn btn-ghost btn-sm"
            title="Clonar elemento"
            @pointerdown.stop="emit('markEditorControlInteraction')"
            @click.stop="emit('cloneCurrentSelection')"
          >
            <Icon icon="ph:copy-bold" class="text-base" />
          </button>
          <button
            data-editor-control="true"
            type="button"
            class="btn btn-ghost btn-sm text-error hover:bg-error/10"
            title="Eliminar elemento"
            @pointerdown.stop="emit('markEditorControlInteraction')"
            @click.stop="emit('deleteCurrentSelection')"
          >
            <Icon icon="ph:trash-bold" class="text-base" />
          </button>
        </div>
      </div>
    </div>

    <div data-editor-control="true" class="pointer-events-none absolute" :style="selectedOverlayStyle">
      <button
        v-if="overlayControlTargetId && (isGroupSelection || !hasMultiSelection)"
        data-editor-control="true"
        type="button"
        class="pointer-events-auto absolute -bottom-12 left-1/2 z-40 flex h-8 w-8 -translate-x-1/2 items-center justify-center rounded-full border-2 border-white bg-cyan-300 text-slate-950 shadow-md touch-none"
        :style="controlZoomStyle"
        title="Girar elemento"
        @pointerdown="emit('startRotate', { event: $event, id: overlayControlTargetId })"
        @dblclick.stop.prevent="emit('resetRotation', overlayControlTargetId)"
      >
        <Icon icon="ph:arrow-clockwise-bold" class="text-lg" />
      </button>
      <span
        v-if="overlayControlTargetId && (isGroupSelection || (!hasMultiSelection && selectedElementType !== 'text'))"
        data-editor-control="true"
        class="pointer-events-auto absolute left-1/2 z-30 -translate-x-1/2 cursor-ns-resize rounded-full border-2 border-white bg-cyan-300 touch-none"
        :style="{ top: selectedHandleMetrics.barOffset, width: selectedHandleMetrics.barLength, height: selectedHandleMetrics.barThickness, ...controlZoomStyle }"
        @pointerdown="emit('startResize', { event: $event, id: overlayControlTargetId, handle: 'n-width' })"
      ></span>
      <span
        v-if="overlayControlTargetId && (isGroupSelection || (!hasMultiSelection && selectedElementType !== 'text'))"
        data-editor-control="true"
        class="pointer-events-auto absolute left-1/2 z-30 -translate-x-1/2 cursor-ns-resize rounded-full border-2 border-white bg-cyan-300 touch-none"
        :style="{ bottom: selectedHandleMetrics.barOffset, width: selectedHandleMetrics.barLength, height: selectedHandleMetrics.barThickness, ...controlZoomStyle }"
        @pointerdown="emit('startResize', { event: $event, id: overlayControlTargetId, handle: 's-width' })"
      ></span>
      <span
        v-if="overlayControlTargetId && (isGroupSelection || !hasMultiSelection)"
        data-editor-control="true"
        class="pointer-events-auto absolute top-1/2 z-30 -translate-y-1/2 cursor-ew-resize rounded-full border-2 border-white bg-cyan-300 touch-none"
        :style="{ left: selectedHandleMetrics.sideOffset, width: selectedHandleMetrics.sideThickness, height: selectedHandleMetrics.sideLength, ...controlZoomStyle }"
        @pointerdown="emit('startResize', { event: $event, id: overlayControlTargetId, handle: 'w' })"
      ></span>
      <span
        v-if="overlayControlTargetId && (isGroupSelection || !hasMultiSelection)"
        data-editor-control="true"
        class="pointer-events-auto absolute top-1/2 z-30 -translate-y-1/2 cursor-ew-resize rounded-full border-2 border-white bg-cyan-300 touch-none"
        :style="{ right: selectedHandleMetrics.sideOffset, width: selectedHandleMetrics.sideThickness, height: selectedHandleMetrics.sideLength, ...controlZoomStyle }"
        @pointerdown="emit('startResize', { event: $event, id: overlayControlTargetId, handle: 'e' })"
      ></span>
      <span
        v-if="overlayControlTargetId && (isGroupSelection || !hasMultiSelection)"
        data-editor-control="true"
        class="pointer-events-auto absolute z-30 cursor-nwse-resize rounded-full border-2 border-white bg-cyan-300 touch-none"
        :style="{ left: selectedHandleMetrics.cornerOffset, top: selectedHandleMetrics.cornerOffset, width: selectedHandleMetrics.cornerSize, height: selectedHandleMetrics.cornerSize, ...controlZoomStyle }"
        @pointerdown="emit('startResize', { event: $event, id: overlayControlTargetId, handle: 'nw' })"
      ></span>
      <span
        v-if="overlayControlTargetId && (isGroupSelection || !hasMultiSelection)"
        data-editor-control="true"
        class="pointer-events-auto absolute z-30 cursor-nesw-resize rounded-full border-2 border-white bg-cyan-300 touch-none"
        :style="{ right: selectedHandleMetrics.cornerOffset, top: selectedHandleMetrics.cornerOffset, width: selectedHandleMetrics.cornerSize, height: selectedHandleMetrics.cornerSize, ...controlZoomStyle }"
        @pointerdown="emit('startResize', { event: $event, id: overlayControlTargetId, handle: 'ne' })"
      ></span>
      <span
        v-if="overlayControlTargetId && (isGroupSelection || !hasMultiSelection)"
        data-editor-control="true"
        class="pointer-events-auto absolute z-30 cursor-nesw-resize rounded-full border-2 border-white bg-cyan-300 touch-none"
        :style="{ left: selectedHandleMetrics.cornerOffset, bottom: selectedHandleMetrics.cornerOffset, width: selectedHandleMetrics.cornerSize, height: selectedHandleMetrics.cornerSize, ...controlZoomStyle }"
        @pointerdown="emit('startResize', { event: $event, id: overlayControlTargetId, handle: 'sw' })"
      ></span>
      <span
        v-if="overlayControlTargetId && (isGroupSelection || !hasMultiSelection)"
        data-editor-control="true"
        class="pointer-events-auto absolute z-30 cursor-nwse-resize rounded-full border-2 border-white bg-cyan-300 touch-none"
        :style="{ right: selectedHandleMetrics.cornerOffset, bottom: selectedHandleMetrics.cornerOffset, width: selectedHandleMetrics.cornerSize, height: selectedHandleMetrics.cornerSize, ...controlZoomStyle }"
        @pointerdown="emit('startResize', { event: $event, id: overlayControlTargetId, handle: 'se' })"
      ></span>
    </div>
  </template>

  <div
    v-if="showMarquee"
    class="pointer-events-none absolute border border-cyan-200/90 bg-cyan-200/20"
    :style="marqueeRectStyle"
  ></div>
</template>
