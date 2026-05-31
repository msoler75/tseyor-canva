import { ref } from 'vue';

export function useToastNotification() {
  const toasts = ref([]);

  function showToast({ message, type = 'info', icon = null, duration = 3000 }) {
    const id = Date.now() + Math.random();
    toasts.value.push({ id, message, type, icon });
    setTimeout(() => removeToast(id), duration);
  }

  function removeToast(id) {
    const index = toasts.value.findIndex((t) => t.id === id);
    if (index !== -1) toasts.value.splice(index, 1);
  }

  return { toasts, showToast, removeToast };
}
