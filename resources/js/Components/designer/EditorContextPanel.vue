<script setup>
import { computed, toRefs } from 'vue';
import { Icon } from '@iconify/vue';
import ColorPaletteSection from './ColorPaletteSection.vue';
import ColorValueField from './ColorValueField.vue';
import FillColorPanel from './FillColorPanel.vue';

const props = defineProps({
  state: Object,
  hasSelection: Boolean,
  hasTextSelection: Boolean,
  activePropertyPanel: String,
  activePropertyTitle: String,
  textPanelOpen: Boolean,
  imagePanelOpen: Boolean,
  shapePanelOpen: Boolean,
  textPresets: Array,
  imagePanelTabs: Array,
  imagePanelTab: String,
  imageUrlInput: String,
  imageLibrary: Array,
  shapeCategoryFilter: String,
  shapeCategories: Array,
  shapeStyleFromKind: Function,
  selectedElement: Object,
  selectedElementType: String,
  backgroundHasImage: Boolean,
  selectedTextStyle: Object,
  activeParagraphLabel: String,
  fontOptions: Array,
  colorOptions: Array,
  backgroundOptions: Array,
  designColorOptions: Array,
  designGradientOptions: Array,
  textEffectRows: Array,
  visualEffectRows: Array,
  activeTextEffectId: String,
  activeVisualEffectId: String,
  textEffectCardFontFamily: String,
  textEffectPreviewStyle: Function,
  visualEffectPreviewStyle: Function,
  shapeGradientOptions: Array,
  shapeGradientDirections: Array,
  normalizePickerColor: Function,
  imageInputRefSetter: Function,
  addTextElement: Function,
  triggerImagePicker: Function,
  onImagePicked: Function,
  addImageFromUrl: Function,
  addLibraryImage: Function,
  addUploadedImage: Function,
  getUploadProgress: Function,
  retryUploadedImage: Function,
  addShapeElement: Function,
  applyGradientPreset: Function,
  applyShapeGradientPreset: Function,
  swapGradientStops: Function,
  swapShapeGradientStops: Function,
  setTextEffect: Function,
  setVisualEffect: Function,
  setSelectedColor: Function,
  changeLayer: Function,
  toggleSelectedImageFlip: Function,
  resetSelectedImageCrop: Function,
});

const emit = defineEmits(['closePanel', 'updateImagePanelTab', 'updateImageUrlInput', 'updateShapeCategoryFilter']);

const {
  state,
  hasSelection,
  hasTextSelection,
  activePropertyPanel,
  activePropertyTitle,
  textPanelOpen,
  imagePanelOpen,
  shapePanelOpen,
  textPresets,
  imagePanelTabs,
  imageLibrary,
  shapeCategories,
  shapeStyleFromKind,
  selectedElement,
  selectedElementType,
  backgroundHasImage,
  selectedTextStyle,
  activeParagraphLabel,
  fontOptions,
  colorOptions,
  backgroundOptions,
  designColorOptions,
  designGradientOptions,
  textEffectRows,
  visualEffectRows,
  activeTextEffectId,
  activeVisualEffectId,
  textEffectCardFontFamily,
  textEffectPreviewStyle,
  visualEffectPreviewStyle,
  shapeGradientOptions,
  shapeGradientDirections,
  normalizePickerColor,
  imageInputRefSetter,
  addTextElement,
  triggerImagePicker,
  onImagePicked,
  addImageFromUrl,
  addLibraryImage,
  addUploadedImage,
  getUploadProgress,
  retryUploadedImage,
  addShapeElement,
  applyGradientPreset,
  applyShapeGradientPreset,
  swapGradientStops,
  swapShapeGradientStops,
  setTextEffect,
  setVisualEffect,
  setSelectedColor,
  changeLayer,
  toggleSelectedImageFlip,
  resetSelectedImageCrop,
} = toRefs(props);

const imagePanelTab = computed({
  get: () => props.imagePanelTab,
  set: (value) => emit('updateImagePanelTab', value),
});
const imageUrlInput = computed({
  get: () => props.imageUrlInput,
  set: (value) => emit('updateImageUrlInput', value),
});
const shapeCategoryFilter = computed({
  get: () => props.shapeCategoryFilter,
  set: (value) => emit('updateShapeCategoryFilter', value),
});

const closePanel = () => emit('closePanel');
</script>

<template>
<aside data-editor-keep-selection="true" class="absolute z-40 h-full w-80 border-r border-base-300 bg-base-100 overflow-y-auto">
            <div class="space-y-5">
                <div class="w-76 fixed z-10 bg-base-100 flex items-start justify-between gap-3 p-5">
                  <div>
                    <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Panel contextual</p>
                    <h3 class="mt-2 text-xl font-semibold text-base-content">{{ hasSelection && activePropertyPanel ? activePropertyTitle : 'Elementos' }}</h3>
                  </div>
                  <div class="flex gap-2">
                    <button
                      type="button"
                      class="btn btn-ghost btn-sm btn-circle"
                      aria-label="Cerrar panel de opciones"
                      @click="closePanel"
                    >
                      <Icon icon="mdi:close" class="text-lg" />
                    </button>
                  </div>
                </div>

                <div class="h-20"></div>

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
                          Seleccionar imágenes
                        </button>
                        <p class="mt-2 text-[11px] text-base-content/60">Puedes elegir varias imágenes; se subirán al servidor en segundo plano.</p>
                        <input :ref="imageInputRefSetter" type="file" accept="image/*" multiple class="hidden" @change="onImagePicked" />
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
                          class="group relative overflow-hidden rounded-xl border border-base-300/70 bg-base-100/70 text-left"
                          @click="addUploadedImage(image)"
                        >
                          <img :src="image.src" :alt="image.label" class="h-20 w-full object-cover transition group-hover:scale-105" />
                          <div class="px-2 py-1.5">
                            <div class="flex items-start justify-between gap-2">
                              <span class="block truncate text-[11px] text-base-content/70">{{ image.label }}</span>
                              <span
                                class="shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.16em]"
                                :class="image.uploadStatus === 'done'
                                  ? 'bg-emerald-500/15 text-emerald-700'
                                  : image.uploadStatus === 'error'
                                    ? 'bg-red-500/15 text-red-600'
                                    : 'bg-amber-500/15 text-amber-700'"
                              >
                                {{ image.uploadStatus === 'done' ? 'OK' : image.uploadStatus === 'error' ? 'Error' : 'Subiendo' }}
                              </span>
                            </div>
                            <div v-if="image.uploadStatus !== 'done'" class="mt-2">
                              <div class="h-1.5 overflow-hidden rounded-full bg-base-300/70">
                                <div
                                  class="h-full rounded-full bg-primary transition-all"
                                  :style="{ width: `${getUploadProgress?.(image.assetId ?? image.id) ?? 0}%` }"
                                ></div>
                              </div>
                              <div class="mt-1 flex items-center justify-between gap-2">
                                <span class="text-[10px] text-base-content/60">
                                  {{ getUploadProgress?.(image.assetId ?? image.id) ?? 0 }}%
                                </span>
                                <button
                                  v-if="image.uploadStatus === 'error'"
                                  type="button"
                                  class="btn btn-ghost btn-xs min-h-0 h-auto px-1.5 py-0.5 text-[10px]"
                                  @click.stop="retryUploadedImage(image)"
                                >
                                  Reintentar
                                </button>
                              </div>
                              <p v-if="image.errorMessage" class="mt-1 text-[10px] text-red-600">{{ image.errorMessage }}</p>
                            </div>
                          </div>
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

                    <FillColorPanel
                      :mode="state.elementLayout.background?.fillMode || 'solid'"
                      :design-colors="designColorOptions"
                      :generic-colors="backgroundOptions"
                      :selected-color="state.elementLayout.background?.backgroundColor"
                      design-color-key-prefix="bg-design-color"
                      generic-color-key-prefix="bg-color"
                      transparent-preview-color="#ffffff"
                      :custom-color-value="state.elementLayout.background?.backgroundColor"
                      :custom-color-normalized-value="normalizePickerColor(state.elementLayout.background?.backgroundColor || '#4338ca', '#4338ca')"
                      custom-color-placeholder="#4338ca"
                      :design-gradients="designGradientOptions"
                      :generic-gradients="shapeGradientOptions"
                      :selected-gradient-start="state.elementLayout.background?.gradientStart"
                      :selected-gradient-end="state.elementLayout.background?.gradientEnd"
                      design-gradient-key-prefix="bg-design-gradient"
                      generic-gradient-key-prefix="bg-gradient"
                      :gradient-start-value="state.elementLayout.background?.gradientStart || '#0ea5e9'"
                      :gradient-end-value="state.elementLayout.background?.gradientEnd || '#8b5cf6'"
                      :gradient-start-normalized-value="normalizePickerColor(state.elementLayout.background?.gradientStart || '#0ea5e9', '#0ea5e9')"
                      :gradient-end-normalized-value="normalizePickerColor(state.elementLayout.background?.gradientEnd || '#8b5cf6', '#8b5cf6')"
                      :gradient-directions="shapeGradientDirections"
                      :gradient-angle="state.elementLayout.background?.gradientAngle || 135"
                      @update:mode="state.elementLayout.background.fillMode = $event"
                      @select-solid-color="(color) => { state.elementLayout.background.fillMode = 'solid'; state.elementLayout.background.backgroundColor = color; }"
                      @update-custom-color="(color) => { state.elementLayout.background.fillMode = 'solid'; state.elementLayout.background.backgroundColor = color; }"
                      @select-gradient-preset="(preset) => applyGradientPreset('background', preset.start, preset.end)"
                      @update-gradient-start="state.elementLayout.background.gradientStart = $event"
                      @update-gradient-end="state.elementLayout.background.gradientEnd = $event"
                      @update-gradient-angle="state.elementLayout.background.gradientAngle = $event"
                      @swap-gradient-stops="swapGradientStops('background')"
                    />
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
                    <ColorPaletteSection
                      class="mt-4"
                      :design-colors="designColorOptions"
                      :generic-colors="colorOptions"
                      :selected-color="selectedTextStyle.color"
                      design-key-prefix="text-design-color"
                      generic-key-prefix="text-color"
                      @select="(color) => { selectedTextStyle.color = color; }"
                    />
                    <ColorValueField
                      class="mt-4"
                      label="Color custom"
                      :value="selectedTextStyle.color"
                      :normalized-value="normalizePickerColor(selectedTextStyle.color, '#ffffff')"
                      placeholder="#7c3aed"
                      @update="setSelectedColor('color', $event)"
                    />
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

                    <FillColorPanel
                      :mode="selectedElement.fillMode || 'solid'"
                      :design-colors="designColorOptions"
                      :generic-colors="backgroundOptions"
                      :selected-color="selectedElement.backgroundColor"
                      design-color-key-prefix="shape-design-color"
                      generic-color-key-prefix="element-color"
                      transparent-preview-color="#ffffff"
                      :custom-color-value="selectedElement.backgroundColor"
                      :custom-color-normalized-value="normalizePickerColor(selectedElement.backgroundColor, '#ffffff')"
                      custom-color-placeholder="transparent o #0ea5e9"
                      :design-gradients="designGradientOptions"
                      :generic-gradients="shapeGradientOptions"
                      :selected-gradient-start="selectedElement.gradientStart"
                      :selected-gradient-end="selectedElement.gradientEnd"
                      design-gradient-key-prefix="shape-design-gradient"
                      generic-gradient-key-prefix="shape-gradient"
                      :gradient-start-value="selectedElement.gradientStart || '#0ea5e9'"
                      :gradient-end-value="selectedElement.gradientEnd || '#8b5cf6'"
                      :gradient-start-normalized-value="normalizePickerColor(selectedElement.gradientStart || '#0ea5e9', '#0ea5e9')"
                      :gradient-end-normalized-value="normalizePickerColor(selectedElement.gradientEnd || '#8b5cf6', '#8b5cf6')"
                      :gradient-directions="shapeGradientDirections"
                      :gradient-angle="selectedElement.gradientAngle || 135"
                      @update:mode="selectedElement.fillMode = $event"
                      @select-solid-color="(color) => { selectedElement.fillMode = 'solid'; selectedElement.backgroundColor = color; }"
                      @update-custom-color="(color) => { selectedElement.fillMode = 'solid'; setSelectedColor('backgroundColor', color); }"
                      @select-gradient-preset="(preset) => applyShapeGradientPreset(preset.start, preset.end)"
                      @update-gradient-start="selectedElement.gradientStart = $event"
                      @update-gradient-end="selectedElement.gradientEnd = $event"
                      @update-gradient-angle="selectedElement.gradientAngle = $event"
                      @swap-gradient-stops="swapShapeGradientStops"
                    />


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
                      <ColorPaletteSection
                        class="mt-4"
                        :design-colors="designColorOptions"
                        :generic-colors="backgroundOptions"
                        :selected-color="selectedElement.backgroundColor"
                        design-key-prefix="image-bg-design-color"
                        generic-key-prefix="image-frame"
                        transparent-preview-color="#ffffff"
                        @select="(color) => { selectedElement.backgroundColor = color; }"
                      />
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
                      <ColorPaletteSection
                        class="mt-3"
                        :design-colors="designColorOptions"
                        :generic-colors="colorOptions"
                        :selected-color="selectedElement.imageTintColor"
                        design-key-prefix="image-tint-design-color"
                        generic-key-prefix="image-tint"
                        @select="(color) => { selectedElement.imageTintColor = color; }"
                      />
                      <ColorValueField
                        class="mt-4"
                        label="Color custom"
                        :value="selectedElement.imageTintColor || '#0f172a'"
                        :normalized-value="normalizePickerColor(selectedElement.imageTintColor || '#0f172a', '#0f172a')"
                        placeholder="#0f172a"
                        @update="setSelectedColor('imageTintColor', $event)"
                      />
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

                  <template v-else-if="selectedElementType === 'shape' || selectedElementType === 'image'">
                    <template v-for="(effectRow, rowIndex) in visualEffectRows" :key="`visual-effect-row-${rowIndex}`">
                      <div class="grid grid-cols-3 gap-2">
                        <button
                          v-for="effect in effectRow"
                          :key="effect.id"
                          type="button"
                          class="text-center transition"
                          @click="setVisualEffect(effect.id)"
                        >
                          <span
                            class="inline-flex h-18 w-full items-center justify-center rounded-xl border transition"
                            :class="activeVisualEffectId === effect.id
                              ? 'border-primary bg-white ring-1 ring-primary/35'
                              : 'border-base-300 bg-white hover:border-primary/45 hover:bg-white'"
                          >
                            <span :style="visualEffectPreviewStyle(effect.id)"></span>
                          </span>
                          <span class="mt-1.5 block text-[11px] font-medium text-base-content/85">{{ effect.label }}</span>
                        </button>
                        <div v-for="emptyIndex in Math.max(0, 3 - effectRow.length)" :key="`visual-effect-row-${rowIndex}-empty-${emptyIndex}`"></div>
                      </div>

                      <div
                        v-if="activeVisualEffectId !== 'none' && effectRow.some((effect) => effect.id === activeVisualEffectId)"
                        class="flex flex-wrap items-end gap-3 rounded-2xl border border-base-300/70 bg-base-100/60 p-3"
                      >
                        <div v-if="['shadow', 'shadow1', 'shadow2', 'echo', 'distort'].includes(activeVisualEffectId)" class="min-w-55 flex-1 space-y-2">
                          <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Direccion</label>
                          <div class="flex items-center gap-2">
                            <input v-model.number="selectedElement.shadowAngle" type="range" min="0" max="360" step="1" class="range range-primary flex-1" />
                            <input v-model.number="selectedElement.shadowAngle" type="number" min="0" max="360" step="1" class="input input-bordered input-sm w-20" />
                          </div>
                        </div>
                        <div v-if="['shadow', 'shadow1', 'shadow2', 'echo'].includes(activeVisualEffectId)" class="min-w-55 flex-1 space-y-2">
                          <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Compensacion</label>
                          <div class="flex items-center gap-2">
                            <input v-model.number="selectedElement.shadowOffset" type="range" min="0" max="100" step="1" class="range range-primary flex-1" />
                            <input v-model.number="selectedElement.shadowOffset" type="number" min="0" max="100" step="1" class="input input-bordered input-sm w-20" />
                          </div>
                        </div>
                        <div v-if="activeVisualEffectId === 'shadow'" class="min-w-55 flex-1 space-y-2">
                          <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Desenfoque</label>
                          <div class="flex items-center gap-2">
                            <input v-model.number="selectedElement.shadowBlur" type="range" min="0" max="100" step="1" class="range range-primary flex-1" />
                            <input v-model.number="selectedElement.shadowBlur" type="number" min="0" max="100" step="1" class="input input-bordered input-sm w-20" />
                          </div>
                        </div>
                        <div v-if="['shadow', 'shadow1', 'shadow2'].includes(activeVisualEffectId)" class="min-w-55 flex-1 space-y-2">
                          <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Transparencia</label>
                          <div class="flex items-center gap-2">
                            <input v-model.number="selectedElement.shadowOpacity" type="range" min="0" max="100" step="1" class="range range-primary flex-1" />
                            <input v-model.number="selectedElement.shadowOpacity" type="number" min="0" max="100" step="1" class="input input-bordered input-sm w-20" />
                          </div>
                        </div>
                        <div v-if="['shadow', 'shadow1', 'shadow2', 'echo'].includes(activeVisualEffectId)" class="w-23 space-y-2">
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
                        <div v-if="activeVisualEffectId === 'glow'" class="min-w-55 flex-1 space-y-2">
                          <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Brillo</label>
                          <div class="flex items-center gap-2">
                            <input v-model.number="selectedElement.neonIntensity" type="range" min="0" max="100" step="1" class="range range-primary flex-1" />
                            <input v-model.number="selectedElement.neonIntensity" type="number" min="0" max="100" step="1" class="input input-bordered input-sm w-20" />
                          </div>
                        </div>
                        <div v-if="activeVisualEffectId === 'glow'" class="w-23 space-y-2">
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
                        <div v-if="activeVisualEffectId === 'distort'" class="min-w-55 flex-1 space-y-2">
                          <label class="block text-[11px] font-semibold uppercase tracking-[0.2em] text-base-content/60">Compensacion</label>
                          <div class="flex items-center gap-2">
                            <input v-model.number="selectedElement.shadowOffset" type="range" min="0" max="20" step="1" class="range range-primary flex-1" />
                            <input v-model.number="selectedElement.shadowOffset" type="number" min="0" max="20" step="1" class="input input-bordered input-sm w-20" />
                          </div>
                        </div>
                        <div v-if="activeVisualEffectId === 'distort'" class="w-23 space-y-2">
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
                        <div v-if="activeVisualEffectId === 'distort'" class="w-23 space-y-2">
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
                      </div>
                    </template>

                    <button
                      v-if="activeVisualEffectId !== 'none'"
                      type="button"
                      class="btn btn-primary btn-block mt-2 rounded-2xl text-sm font-semibold shadow-md"
                      @click="setVisualEffect('none')"
                    >
                      Quitar efecto
                    </button>
                  </template>

                  <template v-else>
                    <p class="text-sm text-base-content/70">Los efectos disponibles aqui aplican a texto, imagenes y figuras segun el tipo seleccionado.</p>
                  </template>
                </div>
              </div>

              <div v-else-if="activePropertyPanel === 'border' && (selectedElementType === 'shape' || selectedElementType === 'image')" class="card border border-base-300 bg-base-100/80">
                <div class="card-body p-4 space-y-4">
                  <div class="flex items-center justify-between gap-3">
                    <div>
                      <p class="text-sm font-semibold text-base-content">Borde</p>
                      <p class="text-xs text-base-content/60">Activa o quita el trazo y ajusta su estilo.</p>
                    </div>
                    <span class="rounded-full border border-base-300 bg-base-100 px-2 py-1 text-[11px] font-medium text-base-content/70">
                      {{ selectedElement.border ? (selectedElement.borderStyle || 'solid') : 'sin borde' }}
                    </span>
                  </div>

                  <div class="flex flex-wrap gap-2">
                    <button type="button" class="btn btn-sm rounded-full" :class="!selectedElement.border ? 'btn-primary' : 'btn-outline'" @click="selectedElement.border = false">Sin borde</button>
                    <button type="button" class="btn btn-sm rounded-full" :class="selectedElement.border && (selectedElement.borderStyle || 'solid') === 'solid' ? 'btn-primary' : 'btn-outline'" @click="selectedElement.border = true; selectedElement.borderStyle = 'solid'">Sólido</button>
                    <button type="button" class="btn btn-sm rounded-full" :class="selectedElement.border && selectedElement.borderStyle === 'dashed' ? 'btn-primary' : 'btn-outline'" @click="selectedElement.border = true; selectedElement.borderStyle = 'dashed'">Dashed</button>
                    <button type="button" class="btn btn-sm rounded-full" :class="selectedElement.border && selectedElement.borderStyle === 'dotted' ? 'btn-primary' : 'btn-outline'" @click="selectedElement.border = true; selectedElement.borderStyle = 'dotted'">Dotted</button>
                  </div>

                  <template v-if="selectedElement.border">
                    <div class="space-y-2">
                      <label class="block text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Grosor</label>
                      <div class="flex items-center gap-3">
                        <input v-model.number="selectedElement.contourWidth" type="range" min="1" max="30" step="1" class="range range-primary flex-1" />
                        <input v-model.number="selectedElement.contourWidth" type="number" min="1" max="30" step="1" class="input input-bordered input-sm w-20" />
                      </div>
                    </div>
                    <div class="grid gap-3 sm:grid-cols-[auto_1fr] sm:items-center">
                      <label class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Color</label>
                      <div class="flex items-center gap-2">
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
                  </template>
                </div>
              </div>

              <div v-else-if="activePropertyPanel === 'rotate' && (selectedElementType === 'image' || (state.selectedElementId === 'background' && backgroundHasImage))" class="card border border-base-300 bg-base-100/80">
                <div class="card-body p-4 space-y-4">
                  <div>
                    <p class="text-sm font-semibold text-base-content">Girar imagen</p>
                    <p class="text-xs text-base-content/60">Invierte la imagen horizontal o verticalmente.</p>
                  </div>
                  <div class="flex flex-col gap-3">
                    <button type="button" class="btn btn-outline rounded-2xl" @click="toggleSelectedImageFlip('x')">
                      <Icon icon="mdi:arrow-u-left-top" class="text-lg" />
                      <span class="w-48 pl-4 text-left">Girar horizontalmente</span>
                    </button>
                    <button type="button" class="btn btn-outline rounded-2xl" @click="toggleSelectedImageFlip('y')">
                      <Icon icon="mdi:arrow-u-down-right" class="text-lg" />
                      <span class="w-48 pl-4 text-left">Girar verticalmente</span>
                    </button>
                  </div>
                </div>
              </div>

              <div v-else-if="activePropertyPanel === 'crop' && (selectedElementType === 'image' || (state.selectedElementId === 'background' && backgroundHasImage))" class="card border border-base-300 bg-base-100/80">
                <div class="card-body p-4 space-y-5">
                  <div>
                    <p class="text-sm font-semibold text-base-content">Recortar imagen</p>
                    <p class="text-xs text-base-content/60">Desplaza o amplía la imagen manteniendo siempre el encuadre cubierto.</p>
                  </div>

                  <div class="space-y-2">
                    <label class="block text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Zoom</label>
                    <div class="flex items-center gap-3">
                      <input
                        v-if="state.selectedElementId === 'background'"
                        v-model.number="state.elementLayout.background.backgroundImageCropScale"
                        type="range"
                        min="1"
                        max="4"
                        step="0.01"
                        class="range range-primary flex-1"
                      />
                      <input
                        v-else
                        v-model.number="selectedElement.imageCropScale"
                        type="range"
                        min="1"
                        max="4"
                        step="0.01"
                        class="range range-primary flex-1"
                      />
                      <input
                        v-if="state.selectedElementId === 'background'"
                        v-model.number="state.elementLayout.background.backgroundImageCropScale"
                        type="number"
                        min="1"
                        max="4"
                        step="0.01"
                        class="input input-bordered input-sm w-24"
                      />
                      <input
                        v-else
                        v-model.number="selectedElement.imageCropScale"
                        type="number"
                        min="1"
                        max="4"
                        step="0.01"
                        class="input input-bordered input-sm w-24"
                      />
                    </div>
                  </div>

                  <div class="space-y-2">
                    <label class="block text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Desplazamiento horizontal</label>
                    <div class="flex items-center gap-3">
                      <input
                        v-if="state.selectedElementId === 'background'"
                        v-model.number="state.elementLayout.background.backgroundImageCropOffsetX"
                        type="range"
                        min="-1"
                        max="1"
                        step="0.01"
                        class="range range-primary flex-1"
                      />
                      <input
                        v-else
                        v-model.number="selectedElement.imageCropOffsetX"
                        type="range"
                        min="-1"
                        max="1"
                        step="0.01"
                        class="range range-primary flex-1"
                      />
                    </div>
                  </div>

                  <div class="space-y-2">
                    <label class="block text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Desplazamiento vertical</label>
                    <div class="flex items-center gap-3">
                      <input
                        v-if="state.selectedElementId === 'background'"
                        v-model.number="state.elementLayout.background.backgroundImageCropOffsetY"
                        type="range"
                        min="-1"
                        max="1"
                        step="0.01"
                        class="range range-primary flex-1"
                      />
                      <input
                        v-else
                        v-model.number="selectedElement.imageCropOffsetY"
                        type="range"
                        min="-1"
                        max="1"
                        step="0.01"
                        class="range range-primary flex-1"
                      />
                    </div>
                  </div>

                  <div class="flex justify-end">
                    <button type="button" class="btn btn-outline btn-sm rounded-full" @click="resetSelectedImageCrop">
                      Resetear recorte
                    </button>
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
            </div>
          </aside>
</template>
