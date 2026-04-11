<script setup>
import DesignerLayout from '../../Layouts/DesignerLayout.vue';
import StepFooter from '../../Components/designer/StepFooter.vue';
import TemplateCard from '../../Components/designer/TemplateCard.vue';
import { computed } from 'vue';
import { filterLabels, templateCatalog, templateFilters } from '../../data/designer';
import { useDesignerState } from '../../composables/useDesignerState';

defineProps({ currentStep: String, steps: Array, navigation: Object });
const state = useDesignerState();

const filteredTemplates = computed(() => state.templateCategory === 'all'
    ? templateCatalog
    : templateCatalog.filter((item) => item.category === state.templateCategory));
const metaLine = computed(() => [state.content.date, state.content.location].filter(Boolean).join(' · '));
</script>

<template>
    <DesignerLayout
        title="Plantillas con preview real"
        eyebrow="Pantalla 5"
        description="La plantilla se elige cuando ya existe contenido real. La galería es generosa y filtrable por categorías."
        :current-step="currentStep"
        :steps="steps"
        :dark-mode="state.darkMode"
        @toggle-dark="state.darkMode = !state.darkMode"
    >
        <section class="glass soft-shadow rounded-[32px] border border-white/70 p-6 sm:p-8 dark:border-slate-700/70">
            <div class="mb-5 flex flex-wrap gap-2">
                <button
                    v-for="filter in templateFilters"
                    :key="filter"
                    type="button"
                    class="btn btn-sm rounded-full"
                    :class="state.templateCategory === filter ? 'btn-primary' : 'btn-outline'"
                    @click="state.templateCategory = filter"
                >
                    {{ filterLabels[filter] }}
                </button>
            </div>

            <div class="max-h-[720px] overflow-y-auto pr-2">
                <div class="alert mb-4 border border-base-300 bg-base-100/80 text-sm text-base-content/80">
                    Desplaza para ver más plantillas. Más adelante se añadirán fondos fotográficos y diseños más ricos.
                </div>

                <div class="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
                    <TemplateCard
                        v-for="template in filteredTemplates"
                        :key="template.id"
                        :template="template"
                        :content="state.content"
                        :meta-line="metaLine"
                        :contact-line="state.content.contact"
                        :selected="state.selectedTemplateId === template.id"
                        @click="state.selectedTemplateId = template.id"
                    />

                    <article class="flex min-h-[360px] flex-col items-center justify-center rounded-[28px] border border-dashed border-base-300 bg-base-100/80 p-6 text-center">
                        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-base-100 text-3xl text-base-content/40 shadow-sm">+</div>
                        <h4 class="mt-5 text-lg font-semibold text-base-content">Sin plantilla</h4>
                        <p class="mt-2 max-w-xs text-sm leading-6 text-base-content/70">
                            Empieza desde cero, conservando el formato, el objetivo y los datos que ya has introducido.
                        </p>
                    </article>
                </div>
            </div>

            <StepFooter :previous-url="navigation.previous" :next-url="navigation.next" />
        </section>
    </DesignerLayout>
</template>
