<script setup>
import { Icon } from '@iconify/vue';

defineProps({
  textPanelOpen: {
    type: Boolean,
    default: false,
  },
  imagePanelOpen: {
    type: Boolean,
    default: false,
  },
  shapePanelOpen: {
    type: Boolean,
    default: false,
  },
  isBackgroundSelected: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['openTextPanel', 'openImagePanel', 'openShapePanel', 'selectBackgroundPanel']);
</script>

<template>
  <div class="flex flex-col items-center gap-2 border-r border-base-300 bg-base-100 p-3 xl:border-b-0">
    <button
      type="button"
      class="flex h-14 w-14 flex-col items-center justify-center gap-1 rounded-2xl border transition"
      :class="textPanelOpen ? 'border-primary bg-primary/10 text-primary' : 'border-base-300 bg-base-100/80 hover:border-primary/50 hover:bg-primary/10'"
      title="Agregar Texto"
      @click="emit('openTextPanel')"
    >
      <span class="text-2xl font-bold leading-none">T</span>
      <span class="text-[9px] font-medium">Texto</span>
    </button>

    <button
      type="button"
      class="flex h-14 w-14 flex-col items-center justify-center gap-1 rounded-2xl border transition"
      :class="imagePanelOpen ? 'border-primary bg-primary/10 text-primary' : 'border-base-300 bg-base-100/80 hover:border-primary/50 hover:bg-primary/10'"
      title="Agregar Imagen"
      @click="emit('openImagePanel')"
    >
      <Icon icon="mdi:image-outline" class="text-2xl" />
      <span class="text-[9px] font-medium">Imagen</span>
    </button>

    <button
      type="button"
      class="flex h-14 w-14 flex-col items-center justify-center gap-1 rounded-2xl border transition"
      :class="shapePanelOpen ? 'border-primary bg-primary/10 text-primary' : 'border-base-300 bg-base-100/80 hover:border-primary/50 hover:bg-primary/10'"
      title="Agregar Figura"
      @click="emit('openShapePanel')"
    >
      <Icon icon="mdi:shape-outline" class="text-2xl" />
      <span class="text-[9px] font-medium">Figura</span>
    </button>

    <button
      type="button"
      class="flex h-14 w-14 flex-col items-center justify-center gap-1 rounded-2xl border transition"
      :class="isBackgroundSelected ? 'border-primary bg-primary/10 text-primary' : 'border-base-300 bg-base-100/80 hover:border-primary/50 hover:bg-primary/10'"
      title="Ajustar Fondo"
      @click="emit('selectBackgroundPanel')"
    >
      <span class="flex h-10 w-10 items-center justify-center rounded-xl text-xl" :class="isBackgroundSelected ? 'bg-primary/20' : 'bg-base-200'">
        <Icon icon="mdi:palette-outline" class="text-xl" />
      </span>
      <span class="text-[9px] font-medium">Fondo</span>
    </button>
  </div>
</template>
