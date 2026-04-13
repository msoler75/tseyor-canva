<script setup>
const props = defineProps({
  designPresets: {
    type: Array,
    default: () => [],
  },
  genericPresets: {
    type: Array,
    default: () => [],
  },
  selectedStart: {
    type: String,
    default: '',
  },
  selectedEnd: {
    type: String,
    default: '',
  },
  designKeyPrefix: {
    type: String,
    default: 'design-gradient',
  },
  genericKeyPrefix: {
    type: String,
    default: 'generic-gradient',
  },
  designLabel: {
    type: String,
    default: 'Degradados del diseño',
  },
  genericLabel: {
    type: String,
    default: 'Paleta genérica',
  },
});

const emit = defineEmits(['select']);

const isSelected = (preset) => (
  props.selectedStart === preset.start
  && props.selectedEnd === preset.end
);

const previewStyle = (preset) => ({
  background: `linear-gradient(135deg, ${preset.start}, ${preset.end})`,
});
</script>

<template>
  <div class="space-y-2">
    <div v-if="designPresets.length" class="space-y-2">
      <p class="text-xs font-semibold uppercase tracking-[0.18em] text-primary/80">{{ designLabel }}</p>
      <div class="grid grid-cols-2 gap-2">
        <button
          v-for="preset in designPresets"
          :key="`${designKeyPrefix}-${preset.id}`"
          type="button"
          class="h-10 rounded-xl border border-base-300/70 transition hover:scale-[1.01]"
          :class="isSelected(preset) ? 'ring-2 ring-primary ring-offset-2 ring-offset-base-100' : ''"
          :style="previewStyle(preset)"
          @click="emit('select', preset)"
        ></button>
      </div>
    </div>

    <div class="space-y-2">
      <p class="text-xs font-semibold uppercase tracking-[0.18em] text-base-content/55">{{ genericLabel }}</p>
      <div class="grid grid-cols-2 gap-2">
        <button
          v-for="preset in genericPresets"
          :key="`${genericKeyPrefix}-${preset.id}`"
          type="button"
          class="h-10 rounded-xl border border-base-300/70 transition hover:scale-[1.01]"
          :class="isSelected(preset) ? 'ring-2 ring-primary ring-offset-2 ring-offset-base-100' : ''"
          :style="previewStyle(preset)"
          @click="emit('select', preset)"
        ></button>
      </div>
    </div>
  </div>
</template>
