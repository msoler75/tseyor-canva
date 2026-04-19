<script setup>
import { computed } from 'vue';
import { Link } from '@inertiajs/vue3';
import { Icon } from '@iconify/vue';
import DesignerLayout from '../../../Layouts/DesignerLayout.vue';

const props = defineProps({
  templates: {
    type: Array,
    default: () => [],
  },
});

const publishedCount = computed(() => props.templates.filter((template) => template.status === 'published').length);
const draftCount = computed(() => props.templates.filter((template) => template.status === 'draft').length);

const openTemplateBase = (template) => {
  if (!template?.base_design_uuid) return;
  window.location.href = `/designer/designs/${template.base_design_uuid}/edit`;
};

</script>

<template>
  <DesignerLayout
    title="Inventario de plantillas"
    eyebrow="Admin"
    description="Listado completo de plantillas creadas en el sistema."
    :show-steps="false"
  >
    <div class="mb-4 flex items-center justify-between">
      <Link href="/" class="btn btn-ghost btn-circle border border-base-300 bg-base-100 shadow-sm" aria-label="Volver al inicio" title="Volver al inicio">
        <Icon icon="ph:house-bold" class="text-xl" />
      </Link>
    </div>

    <section class="space-y-6">
      <div class="grid gap-4 sm:grid-cols-3">
        <div class="card border border-base-300 bg-base-100 shadow-sm">
          <div class="card-body">
            <p class="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Total</p>
            <p class="mt-2 text-3xl font-bold">{{ templates.length }}</p>
          </div>
        </div>
        <div class="card border border-base-300 bg-base-100 shadow-sm">
          <div class="card-body">
            <p class="text-xs font-semibold uppercase tracking-[0.2em] text-success">Publicadas</p>
            <p class="mt-2 text-3xl font-bold">{{ publishedCount }}</p>
          </div>
        </div>
        <div class="card border border-base-300 bg-base-100 shadow-sm">
          <div class="card-body">
            <p class="text-xs font-semibold uppercase tracking-[0.2em] text-warning">Borradores</p>
            <p class="mt-2 text-3xl font-bold">{{ draftCount }}</p>
          </div>
        </div>
      </div>

      <div v-if="templates.length" class="grid gap-4 xl:grid-cols-2">
        <article
          v-for="template in templates"
          :key="template.uuid"
          class="overflow-hidden rounded-[28px] border border-base-300 bg-base-100 shadow-sm"
        >
          <div class="grid gap-0 md:grid-cols-[240px,1fr]">
            <div class="min-h-56 bg-base-200">
              <img
                v-if="template.thumbnail_url"
                :src="template.thumbnail_url"
                :alt="template.title"
                class="h-full w-full object-cover"
              />
              <div v-else class="flex h-full min-h-56 items-center justify-center text-sm text-base-content/60">
                Sin miniatura
              </div>
            </div>
            <div class="p-5">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Plantilla</p>
                  <h3 class="mt-1 text-2xl font-semibold">{{ template.title }}</h3>
                  <p class="mt-2 text-sm text-base-content/70">{{ template.description || 'Sin descripción' }}</p>
                </div>
                <span class="badge badge-outline">{{ template.status }}</span>
              </div>

              <div class="mt-4 flex flex-wrap gap-2">
                <span
                  v-for="category in template.category_ids"
                  :key="`${template.uuid}-category-${category}`"
                  class="badge badge-primary badge-outline"
                >
                  {{ category }}
                </span>
                <span
                  v-for="objective in template.objective_ids"
                  :key="`${template.uuid}-objective-${objective}`"
                  class="badge badge-secondary badge-outline"
                >
                  {{ objective }}
                </span>
              </div>

              <div class="mt-5 flex flex-wrap gap-2">
                <Link
                  v-if="template.base_design_uuid"
                  :href="`/designer/designs/${template.base_design_uuid}/edit`"
                  class="btn btn-primary btn-sm rounded-full"
                >
                  Editar base
                </Link>
                <Link
                  v-if="template.base_design_uuid"
                  :href="`/designer/designs/${template.base_design_uuid}/edit?templateForm=1`"
                  class="btn btn-outline btn-sm rounded-full"
                >
                  Editar plantilla
                </Link>
              </div>
            </div>
          </div>
        </article>
      </div>

      <div v-else class="rounded-[28px] border border-dashed border-base-300 bg-base-100 p-8 text-center text-base-content/65">
        Todavía no hay plantillas creadas.
      </div>
    </section>
  </DesignerLayout>
</template>
