<script setup>
import { Icon } from '@iconify/vue';
import ColorPaletteSection from './ColorPaletteSection.vue';
import ColorValueField from './ColorValueField.vue';
import GradientPaletteSection from './GradientPaletteSection.vue';

const props = defineProps({
  mode: {
    type: String,
    default: 'solid',
  },
  designColors: {
    type: Array,
    default: () => [],
  },
  genericColors: {
    type: Array,
    default: () => [],
  },
  selectedColor: {
    type: String,
    default: '',
  },
  designColorKeyPrefix: {
    type: String,
    default: 'design-color',
  },
  genericColorKeyPrefix: {
    type: String,
    default: 'generic-color',
  },
  transparentPreviewColor: {
    type: String,
    default: '#ffffff',
  },
  customColorValue: {
    type: String,
    default: '',
  },
  customColorNormalizedValue: {
    type: String,
    default: '#000000',
  },
  customColorPlaceholder: {
    type: String,
    default: '#000000',
  },
  designGradients: {
    type: Array,
    default: () => [],
  },
  genericGradients: {
    type: Array,
    default: () => [],
  },
  selectedGradientStart: {
    type: String,
    default: '',
  },
  selectedGradientEnd: {
    type: String,
    default: '',
  },
  designGradientKeyPrefix: {
    type: String,
    default: 'design-gradient',
  },
  genericGradientKeyPrefix: {
    type: String,
    default: 'generic-gradient',
  },
  gradientStartValue: {
    type: String,
    default: '#0ea5e9',
  },
  gradientEndValue: {
    type: String,
    default: '#8b5cf6',
  },
  gradientStartNormalizedValue: {
    type: String,
    default: '#0ea5e9',
  },
  gradientEndNormalizedValue: {
    type: String,
    default: '#8b5cf6',
  },
  gradientDirections: {
    type: Array,
    default: () => [],
  },
  gradientAngle: {
    type: Number,
    default: 135,
  },
  swapLabel: {
    type: String,
    default: 'Alternar inicio/fin',
  },
});

const emit = defineEmits([
  'update:mode',
  'selectSolidColor',
  'updateCustomColor',
  'selectGradientPreset',
  'updateGradientStart',
  'updateGradientEnd',
  'updateGradientAngle',
  'swapGradientStops',
]);

const gradientPreviewStyle = () => ({
  background: `linear-gradient(${props.gradientAngle || 135}deg, ${props.gradientStartValue || '#0ea5e9'}, ${props.gradientEndValue || '#8b5cf6'})`,
});
</script>

<template>
  <div class="space-y-4">
    <div class="mt-3 flex flex-wrap gap-2">
      <button
        type="button"
        class="btn btn-sm rounded-full"
        :class="mode !== 'gradient' ? 'btn-primary' : 'btn-outline'"
        @click="emit('update:mode', 'solid')"
      >
        Sólido
      </button>
      <button
        type="button"
        class="btn btn-sm rounded-full"
        :class="mode === 'gradient' ? 'btn-primary' : 'btn-outline'"
        @click="emit('update:mode', 'gradient')"
      >
        Degradado
      </button>
    </div>

    <div v-if="mode !== 'gradient'" class="space-y-4">
      <ColorPaletteSection
        class="mt-4"
        :design-colors="designColors"
        :generic-colors="genericColors"
        :selected-color="selectedColor"
        :design-key-prefix="designColorKeyPrefix"
        :generic-key-prefix="genericColorKeyPrefix"
        :transparent-preview-color="transparentPreviewColor"
        @select="emit('selectSolidColor', $event)"
      />
      <ColorValueField
        class="mt-4"
        label="Color custom"
        :value="customColorValue"
        :normalized-value="customColorNormalizedValue"
        :placeholder="customColorPlaceholder"
        @update="emit('updateCustomColor', $event)"
      />
    </div>

    <div v-else class="space-y-4">
      <GradientPaletteSection
        :design-presets="designGradients"
        :generic-presets="genericGradients"
        :selected-start="selectedGradientStart"
        :selected-end="selectedGradientEnd"
        :design-key-prefix="designGradientKeyPrefix"
        :generic-key-prefix="genericGradientKeyPrefix"
        @select="emit('selectGradientPreset', $event)"
      />
      <div class="grid gap-3 sm:grid-cols-2">
        <div class="flex items-center gap-2">
          <span class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Inicio</span>
          <input
            type="color"
            class="h-10 w-12 cursor-pointer rounded-xl border border-base-300 bg-base-100 p-1"
            :value="gradientStartNormalizedValue"
            @input="emit('updateGradientStart', $event.target.value)"
          />
        </div>
        <div class="flex items-center gap-2">
          <span class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Final</span>
          <input
            type="color"
            class="h-10 w-12 cursor-pointer rounded-xl border border-base-300 bg-base-100 p-1"
            :value="gradientEndNormalizedValue"
            @input="emit('updateGradientEnd', $event.target.value)"
          />
        </div>
      </div>
      <div class="grid gap-3 sm:grid-cols-[auto_1fr] sm:items-center">
        <label class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">Dirección</label>
        <div class="grid grid-cols-3 gap-2 rounded-xl border border-base-300/70 bg-base-100/70 p-2">
          <button
            v-for="direction in gradientDirections"
            :key="direction.value"
            type="button"
            class="group flex items-center justify-center rounded-lg border p-2 transition"
            :class="gradientAngle === direction.value
              ? 'border-primary bg-primary/15 text-primary'
              : 'border-base-300/70 bg-base-100/80 text-base-content/70 hover:border-primary/50 hover:text-primary'"
            :title="direction.label"
            :aria-label="direction.label"
            @click="emit('updateGradientAngle', direction.value)"
          >
            <Icon :icon="direction.icon" class="text-xl" />
          </button>
        </div>
      </div>
      <div class="flex flex-wrap gap-2">
        <button type="button" class="btn btn-outline btn-sm rounded-full" @click="emit('swapGradientStops')">{{ swapLabel }}</button>
        <div class="h-8 flex-1 min-w-28 rounded-full border border-base-300/70" :style="gradientPreviewStyle()"></div>
      </div>
    </div>
  </div>
</template>
