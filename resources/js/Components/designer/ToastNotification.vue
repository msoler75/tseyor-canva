<script setup>
import { Icon } from '@iconify/vue';

defineProps({
  toasts: {
    type: Array,
    required: true,
  },
});

const emit = defineEmits(['remove']);

const typeToIcon = {
  success: 'ph:check-circle-bold',
  error: 'ph:x-circle-bold',
  info: 'ph:info-bold',
  warning: 'ph:warning-bold',
  undo: 'ph:arrow-counter-clockwise-bold',
};

const typeToAlertClass = {
  success: 'alert-success',
  error: 'alert-error',
  info: 'alert-info',
  warning: 'alert-warning',
  undo:
    'border-purple-500 bg-purple-50 dark:bg-purple-950 text-purple-800 dark:text-purple-200',
};
</script>

<template>
  <Teleport to="body">
    <TransitionGroup
      name="toast"
      tag="div"
      class="fixed bottom-4 right-4 z-50 flex flex-col gap-2"
    >
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="alert flex items-center gap-3 shadow-lg max-w-sm"
        :class="typeToAlertClass[toast.type] || 'alert-info'"
      >
        <Icon
          v-if="toast.icon || typeToIcon[toast.type]"
          :icon="toast.icon || typeToIcon[toast.type]"
          class="text-xl shrink-0"
        />
        <span class="flex-1 text-sm">{{ toast.message }}</span>
        <button
          class="btn btn-ghost btn-xs btn-circle shrink-0"
          @click="emit('remove', toast.id)"
        >
          <Icon icon="ph:x-bold" class="text-base" />
        </button>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<style scoped>
.toast-enter-active {
  transition: all 0.3s ease-out;
}
.toast-leave-active {
  transition: all 0.2s ease-in;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
