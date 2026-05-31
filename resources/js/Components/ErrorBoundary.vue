<template>
  <div v-if="hasError" class="flex flex-col items-center justify-center p-8 text-center">
    <Icon icon="ph:warning-circle-bold" class="text-5xl text-error mb-4" />
    <h2 class="text-lg font-bold text-base-content mb-2">Algo salió mal</h2>
    <p class="text-sm text-base-content/60 mb-4 max-w-md">
      {{ friendlyMessage }}
    </p>
    <button type="button" class="btn btn-primary btn-sm" @click="handleRetry">
      <Icon icon="ph:arrow-clockwise-bold" class="text-lg" />
      Reintentar
    </button>
    <details v-if="showDetail" class="mt-4 max-w-full">
      <summary class="text-xs text-base-content/40 cursor-pointer">Detalle técnico</summary>
      <pre class="mt-2 text-xs text-left text-error bg-base-200 p-3 rounded-xl overflow-auto max-h-48">{{ errorMessage }}</pre>
    </details>
  </div>
  <slot v-else />
</template>

<script setup>
import { Icon } from '@iconify/vue';
import { ref, onErrorCaptured } from 'vue';

defineProps({
  showDetail: {
    type: Boolean,
    default: false,
  },
});

defineEmits(['error']);

const hasError = ref(false);
const errorMessage = ref('');

const friendlyMessage = ref('Ocurrió un error inesperado. Puedes intentar de nuevo.');

onErrorCaptured((err, instance, info) => {
  hasError.value = true;
  errorMessage.value = err?.message ?? String(err ?? '');
  return false;
});

const handleRetry = () => {
  hasError.value = false;
  errorMessage.value = '';
};
</script>
