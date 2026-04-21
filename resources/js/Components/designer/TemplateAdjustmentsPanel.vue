<script setup>
import { computed } from 'vue';

const props = defineProps({
  templateFields: {
    type: Array,
    default: () => [],
  },
  templateFieldUsage: {
    type: Object,
    default: () => ({}),
  },
});

const emit = defineEmits(['addField', 'hoverChange', 'openSettings']);

const availableFields = computed(() => props.templateFields.filter((field) => !props.templateFieldUsage?.[field.id]));
const addedFields = computed(() => props.templateFields.filter((field) => props.templateFieldUsage?.[field.id]));
</script>

<template>
  <aside
    data-editor-keep-selection="true"
    class="absolute inset-y-0 right-0 z-50 w-80 overflow-y-auto border-l border-base-300 bg-base-100 shadow-2xl"
    @mouseenter="emit('hoverChange', true)"
    @mouseleave="emit('hoverChange', false)"
  >
    <div class="space-y-5">
      <div class="sticky top-0 z-10 border-b border-base-300 bg-base-100 p-5">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Plantilla</p>
          <h3 class="mt-2 text-xl font-semibold text-base-content">Campos y ajustes</h3>
          <p class="mt-2 text-sm text-base-content/65">
            Pulsa un campo disponible para colocarlo en el diseño base.
          </p>
          <button
            type="button"
            class="btn btn-primary btn-sm mt-4 w-full rounded-full"
            @click="emit('openSettings')"
          >
            Ajustes de la plantilla
          </button>
        </div>
      </div>

      <div class="px-5 pb-5 space-y-4">
        <section class="card border border-base-300 bg-base-100/80">
          <div class="card-body p-4">
            <h4 class="text-sm font-semibold uppercase tracking-[0.18em] text-base-content/60">Elementos disponibles</h4>
            <div class="mt-4 space-y-2">
              <button
                v-for="field in availableFields"
                :key="field.id"
                type="button"
                class="w-full rounded-2xl border border-accent/30 bg-base-100 px-4 py-3 text-left transition hover:border-accent hover:bg-accent/10 focus:outline-none focus:ring-2 focus:ring-accent/40"
                @click="emit('addField', field.id)"
              >
                <span class="block font-medium">{{ field.label }}</span>
                <span v-if="field.description" class="block text-xs opacity-70">{{ field.description }}</span>
              </button>
              <p v-if="!availableFields.length" class="rounded-2xl border border-dashed border-base-300 bg-base-200/60 px-4 py-3 text-sm text-base-content/60">
                Todos los campos de esta plantilla ya están en el diseño.
              </p>
            </div>
          </div>
        </section>

        <section class="card border border-base-300 bg-base-100/80">
          <div class="card-body p-4">
            <h4 class="text-sm font-semibold uppercase tracking-[0.18em] text-base-content/60">Campos añadidos</h4>
            <div class="mt-4 space-y-2">
              <button
                v-for="field in addedFields"
                :key="field.id"
                type="button"
                disabled
                class="w-full cursor-not-allowed rounded-2xl border border-base-300 bg-base-200 px-4 py-3 text-left text-base-content/45"
              >
                <span class="block font-medium">{{ field.label }}</span>
                <span v-if="field.description" class="block text-xs opacity-70">{{ field.description }}</span>
              </button>
              <p v-if="!addedFields.length" class="rounded-2xl border border-dashed border-base-300 bg-base-200/60 px-4 py-3 text-sm text-base-content/60">
                Aún no hay campos añadidos al diseño.
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  </aside>
</template>
