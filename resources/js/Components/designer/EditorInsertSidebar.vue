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
  qrPanelOpen: {
    type: Boolean,
    default: false,
  },
  isBackgroundSelected: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['openTextPanel', 'openImagePanel', 'openShapePanel', 'openQrPanel', 'selectBackgroundPanel']);
</script>

<template>
  <div class="flex items-center gap-2 overflow-x-auto border-t border-base-300 bg-base-100/95 p-2 shadow-[0_-10px_30px_rgba(15,23,42,0.12)] md:flex-col md:overflow-visible md:border-r md:border-t-0 md:p-3 md:shadow-none xl:border-b-0">
    <button
      type="button"
      class="flex h-16 min-w-20 flex-col items-center justify-center gap-1 rounded-2xl border transition md:h-14 md:w-14 md:min-w-0"
      :class="textPanelOpen ? 'border-primary bg-primary/10 text-primary' : 'border-base-300 bg-base-100/80 hover:border-primary/50 hover:bg-primary/10'"
      title="Agregar Texto"
      @click="emit('openTextPanel')"
    >
      <span class="text-2xl font-bold leading-none">T</span>
      <span class="text-[9px] font-medium">Texto</span>
    </button>

    <button
      type="button"
      class="flex h-16 min-w-20 flex-col items-center justify-center gap-1 rounded-2xl border transition md:h-14 md:w-14 md:min-w-0"
      :class="imagePanelOpen ? 'border-primary bg-primary/10 text-primary' : 'border-base-300 bg-base-100/80 hover:border-primary/50 hover:bg-primary/10'"
      title="Agregar Imagen"
      @click="emit('openImagePanel')"
    >
      <Icon icon="mdi:image-outline" class="text-2xl" />
      <span class="text-[9px] font-medium">Imagen</span>
    </button>

    <button
      type="button"
      class="flex h-16 min-w-20 flex-col items-center justify-center gap-1 rounded-2xl border transition md:h-14 md:w-14 md:min-w-0"
      :class="shapePanelOpen ? 'border-primary bg-primary/10 text-primary' : 'border-base-300 bg-base-100/80 hover:border-primary/50 hover:bg-primary/10'"
      title="Agregar Figura"
      @click="emit('openShapePanel')"
    >
      <Icon icon="mdi:shape-outline" class="text-2xl" />
      <span class="text-[9px] font-medium">Figura</span>
    </button>

    <button
      type="button"
      class="flex h-16 min-w-20 flex-col items-center justify-center gap-1 rounded-2xl border transition md:h-14 md:w-14 md:min-w-0"
      :class="qrPanelOpen ? 'border-primary bg-primary/10 text-primary' : 'border-base-300 bg-base-100/80 hover:border-primary/50 hover:bg-primary/10'"
      title="Agregar Código QR"
      @click="emit('openQrPanel')"
    >
      <Icon icon="material-symbols:qr-code" class="text-2xl" />
      <span class="text-[9px] font-medium">QR</span>
    </button>

    <button
      type="button"
      class="flex h-16 min-w-20 flex-col items-center justify-center gap-1 rounded-2xl border transition md:h-14 md:w-14 md:min-w-0"
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
