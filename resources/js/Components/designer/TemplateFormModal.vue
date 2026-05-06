<script setup>
defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  saving: {
    type: Boolean,
    default: false,
  },
  title: {
    type: String,
    default: 'Datos de la plantilla',
  },
  eyebrow: {
    type: String,
    default: 'Publicar plantilla',
  },
  description: {
    type: String,
    default: 'Solo el usuario admin puede publicar y modificar plantillas.',
  },
  submitLabel: {
    type: String,
    default: 'Guardar cambios',
  },
  cancelLabel: {
    type: String,
    default: 'Cancelar',
  },
});

const emit = defineEmits(['close', 'submit']);
</script>

<template>
  <dialog v-if="open" class="modal modal-open backdrop-blur-sm" style="z-index:10000;">
    <div class="modal-box flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-[30px] border border-base-300 bg-base-100 p-0 shadow-2xl">
      <form class="flex min-h-0 flex-col" @submit.prevent="emit('submit')">
        <header class="shrink-0 border-b border-base-300 px-6 py-5">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">
                {{ eyebrow }}
              </p>
              <h3 class="mt-1 text-2xl font-semibold">{{ title }}</h3>
              <p class="mt-1 text-sm text-base-content/70">
                {{ description }}
              </p>
            </div>
            <button
              type="button"
              class="btn btn-ghost btn-sm rounded-full"
              :disabled="saving"
              @click="emit('close')"
            >
              Cerrar
            </button>
          </div>
        </header>

        <div class="min-h-0 flex-1 overflow-y-auto px-6 py-5">
          <slot />
        </div>

        <footer class="shrink-0 flex flex-wrap items-center justify-end gap-3 border-t border-base-300 px-6 py-4">
          <button type="button" class="btn btn-outline rounded-full" :disabled="saving" @click="emit('close')">
            {{ cancelLabel }}
          </button>
          <button type="submit" class="btn btn-primary rounded-full" :disabled="saving">
            {{ saving ? 'Guardando...' : submitLabel }}
          </button>
        </footer>
      </form>
    </div>
  </dialog>
</template>
