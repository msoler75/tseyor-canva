<script setup>
const props = defineProps({
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
  designKeyPrefix: {
    type: String,
    default: 'design-color',
  },
  genericKeyPrefix: {
    type: String,
    default: 'generic-color',
  },
  designLabel: {
    type: String,
    default: 'Colores del diseño',
  },
  genericLabel: {
    type: String,
    default: 'Paleta genérica',
  },
  transparentPreviewColor: {
    type: String,
    default: '#ffffff',
  },
});

const emit = defineEmits(['select']);

const ringClass = (color) => (
  props.selectedColor === color
    ? 'ring-2 ring-primary ring-offset-2 ring-offset-base-100'
    : 'ring-1 ring-slate-200 dark:ring-slate-700'
);

const previewStyle = (color) => ({
  backgroundColor: color === 'transparent' ? props.transparentPreviewColor : color,
});
</script>

<template>
  <div class="space-y-2">
    <div v-if="designColors.length" class="space-y-2">
      <p class="text-xs font-semibold uppercase tracking-[0.18em] text-primary/80">{{ designLabel }}</p>
      <div class="grid grid-cols-6 gap-2">
        <button
          v-for="color in designColors"
          :key="`${designKeyPrefix}-${color}`"
          type="button"
          class="h-9 w-9 rounded-full transition hover:scale-105"
          :class="ringClass(color)"
          :style="previewStyle(color)"
          :title="color"
          @click="emit('select', color)"
        ></button>
      </div>
    </div>

    <div class="space-y-2">
      <p class="text-xs font-semibold uppercase tracking-[0.18em] text-base-content/55">{{ genericLabel }}</p>
      <div class="grid grid-cols-6 gap-2">
        <button
          v-for="color in genericColors"
          :key="`${genericKeyPrefix}-${color}`"
          type="button"
          class="h-9 w-9 rounded-full transition hover:scale-105"
          :class="ringClass(color)"
          :style="previewStyle(color)"
          :title="color"
          @click="emit('select', color)"
        ></button>
      </div>
    </div>
  </div>
</template>
