<script setup>
import { defineAsyncComponent } from 'vue';

const RichTextEditor = defineAsyncComponent(() => import('./RichTextEditor.vue'));

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
  canvasRefSetter: Function,
  richEditorRefSetter: Function,
});

const emit = defineEmits([
  'canvasPointerDown',
  'canvasClick',
  'elementClick',
  'beginTextEdit',
  'elementPointerDown',
  'richEditorTextUpdate',
  'richEditorStylesUpdate',
  'richEditorSelectionChange',
  'richEditorBlur',
  'cancelTextEdit',
  'commitTextEdit',
  'canvasFileDragEnter',
  'canvasFileDragOver',
  'canvasFileDragLeave',
  'canvasFileDrop',
]);

const assignRichEditorRef = (id, element) => {
  props.richEditorRefSetter?.(id, element);
};
</script>

<template>
  <div class="canvas-grid relative h-full overflow-auto bg-slate-100 px-4 pt-6 pb-28 dark:bg-slate-950 sm:px-10 sm:pt-16 sm:pb-10 md:px-10 md:pt-16 md:pb-10" :style="canvasGridStyle" @pointerdown="emit('canvasPointerDown', $event)">
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
    <div class="relative z-10 mx-auto shadow-2xl" :style="[canvasFrameStyle, canvasZoomStyle]" :class="isBackgroundSelected ? 'ring-2 ring-primary' : ''">
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
          v-for="item in editorElements"
          :key="item.id"
          data-editor-element="true"
          :data-editor-id="item.id"
          class="group absolute p-0 text-left"
          :style="elementBoxStyle(item.id)"
          :class="isElementSelected(item.id)
            ? (editingElementId === item.id
                ? 'border-2 border-solid border-cyan-300 bg-white/10 shadow-[0_0_0_3px_rgba(103,232,249,.35)] editor-editing-pulse'
                : (drag.active && drag.elementId === item.id
                    ? 'border-2 border-dashed border-cyan-300 bg-white/10 shadow-[0_0_0_3px_rgba(103,232,249,.18)]'
                    : 'border-2 border-dashed border-cyan-300 bg-white/8 shadow-[0_0_0_3px_rgba(103,232,249,.18)]'))
            : (showFieldLabels && item.fieldKey
                ? 'z-10 border-2 border-dashed border-accent bg-accent/10 shadow-[0_0_0_3px_rgba(251,191,36,.20)]'
                : 'z-10 border border-transparent hover:border-white/20')"
          @click="emit('elementClick', { event: $event, id: item.id })"
          @dblclick="emit('beginTextEdit', item.id)"
          @pointerdown="emit('elementPointerDown', { event: $event, id: item.id })"
        >
          <div class="relative" :class="item.type === 'text' ? '' : 'h-full w-full'" :style="elementContentStyle(item.id)">
            <div
              v-if="item.fieldKey"
              class="pointer-events-none absolute -top-6 left-0 z-20 transition group-hover:opacity-100"
              :class="showFieldLabels ? 'opacity-100' : 'opacity-0'"
            >
              <span class="badge badge-xs badge-accent shadow-md">
                {{ item.label }}
              </span>
            </div>
            <template v-if="item.type === 'text'">
              <RichTextEditor
                :ref="(el) => assignRichEditorRef(item.id, el)"
                :paragraph-styles="state.elementLayout[item.id].paragraphStyles ?? []"
                :text="item.text ?? ''"
                :editable="editingElementId === item.id"
                :editor-style="richEditorContainerStyle(item.id)"
                :color-override="neonColorOverride(item.id)"
                :transparent-fill="!!state.elementLayout[item.id]?.hollowText"
                @update:text="emit('richEditorTextUpdate', { id: item.id, value: $event })"
                @update:paragraph-styles="emit('richEditorStylesUpdate', { id: item.id, value: $event })"
                @selection-change="emit('richEditorSelectionChange', { id: item.id, value: $event })"
                @blur="emit('richEditorBlur', { id: item.id, event: $event })"
                @keydown.escape.stop="emit('cancelTextEdit')"
                @keydown.ctrl.enter.stop="emit('commitTextEdit')"
                @keydown.meta.enter.stop="emit('commitTextEdit')"
                @pointerdown.stop="editingElementId === item.id ? null : emit('elementPointerDown', { event: $event, id: item.id })"
                @mousedown.stop
                @dblclick.stop="emit('beginTextEdit', item.id)"
                @click.stop="editingElementId === item.id ? null : emit('elementClick', { event: $event, id: item.id })"
              />
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
              <div class="relative h-full w-full">
                <div class="h-full w-full" :style="shapeRenderModel(item).outerStyle"></div>
                <div
                  v-if="shapeRenderModel(item).innerStyle"
                  class="pointer-events-none absolute inset-0"
                  :style="shapeRenderModel(item).innerStyle"
                ></div>
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
              </div>
            </template>
          </div>
        </div>

        <slot name="overlay" />
      </div>
    </div>
  </div>
</template>
