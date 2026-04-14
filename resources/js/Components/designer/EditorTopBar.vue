<script setup>
import { Icon } from '@iconify/vue';

defineProps({
  size: {
    type: String,
    default: 'Tamaño no definido',
  },
  canUndo: {
    type: Boolean,
    default: false,
  },
  canRedo: {
    type: Boolean,
    default: false,
  },
  undoActionLabel: {
    type: String,
    default: 'edición',
  },
  redoActionLabel: {
    type: String,
    default: 'edición',
  },
  zoomLevel: {
    type: [Number, String],
    default: 100,
  },
  darkMode: {
    type: Boolean,
    default: false,
  },
  exportHref: {
    type: String,
    default: '/designer/export',
  },
});

const emit = defineEmits(['openFormatAssistant', 'undo', 'redo', 'updateZoomLevel', 'toggleDarkMode', 'exportNavigate']);

const handleZoomInput = (event) => {
  emit('updateZoomLevel', event.target.value);
};
</script>

<template>
  <nav class="flex flex-wrap items-center justify-between gap-3 border-b border-base-300 bg-base-100 px-4 py-3 shadow-sm">
    <div class="flex items-center gap-2">
      <span class="rounded-xl bg-primary/15 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-primary">Editor</span>
      <span class="text-sm text-base-content/65">{{ size || 'Tamaño no definido' }}</span>
    </div>

    <div class="flex flex-wrap items-center gap-3">
      <div class="flex items-center gap-3 rounded-2xl p-1 shadow-sm">
        <button
          type="button"
          class="btn btn-sm btn-ghost rounded-full"
          title="Cambiar formato o tamaño del diseño"
          aria-label="Cambiar formato"
          @click="emit('openFormatAssistant')"
        >
          <Icon icon="ph:frame-corners-bold" class="text-2xl" />
        </button>
        <button
          type="button"
          class="btn btn-sm btn-ghost btn-circle"
          :class="canUndo ? 'text-base-content hover:bg-base-200' : 'text-base-content/35'"
          :disabled="!canUndo"
          :title="`Deshacer: ${undoActionLabel} (Ctrl/Cmd + Z)`"
          aria-label="Deshacer"
          @click="emit('undo')"
        >
          <Icon icon="ci:arrow-undo-up-left" class="text-2xl" />
        </button>
        <button
          type="button"
          class="btn btn-sm btn-ghost btn-circle"
          :class="canRedo ? 'text-base-content hover:bg-base-200' : 'text-base-content/35'"
          :disabled="!canRedo"
          :title="`Rehacer: ${redoActionLabel} (Ctrl/Cmd + Y)`"
          aria-label="Rehacer"
          @click="emit('redo')"
        >
          <Icon icon="ci:arrow-undo-up-right" class="text-2xl" />
        </button>
      </div>
      <div class="flex items-center gap-2 rounded-xl border border-base-300 px-3 py-2">
        <span class="text-xs font-semibold uppercase tracking-[0.16em] text-base-content/60">Zoom</span>
        <input
          :value="zoomLevel"
          type="range"
          min="25"
          max="200"
          step="5"
          class="range range-primary h-2 w-28"
          @input="handleZoomInput"
        />
        <input
          :value="zoomLevel"
          type="number"
          min="25"
          max="200"
          step="5"
          class="input input-bordered input-sm w-20"
          @input="handleZoomInput"
        />
        <span class="text-xs text-base-content/60">%</span>
      </div>

      <button
        type="button"
        class="btn btn-lg rounded-full"
        :title="darkMode ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'"
        @click="emit('toggleDarkMode')"
      >
        {{ darkMode ? '🌙' : '☀️' }}
      </button>

      <a :href="exportHref" class="btn btn-sm btn-primary rounded-full" @click="emit('exportNavigate', $event)">Exportar</a>
    </div>
  </nav>
</template>
