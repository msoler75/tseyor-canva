<script setup>
import StepFooter from '../../Components/designer/StepFooter.vue';
import DesignerLayout from '../../Layouts/DesignerLayout.vue';
import { computed } from 'vue';
import { formatCards, objectiveRecommendations, objectiveOptions } from '../../data/designer';
import { useDesignerState } from '../../composables/useDesignerState';

defineProps({ currentStep: String, steps: Array, navigation: Object });
const state = useDesignerState();

const sizes = computed(() => {
    const rules = objectiveRecommendations[state.objective] ?? objectiveRecommendations.generic;
    return rules[state.outputType];
});

const objectiveTitle = computed(() => objectiveOptions.find((item) => item.id === state.objective)?.title ?? 'Genérico');
</script>

<template>
    <DesignerLayout
        title="Formato y salida"
        eyebrow="Pantalla 3"
        description="La recomendación mejora porque ya sabemos el objetivo principal de la pieza."
        :hint="'Objetivo activo: ' + objectiveTitle"
        :current-step="currentStep"
        :steps="steps"
        :dark-mode="state.darkMode"
        @toggle-dark="state.darkMode = !state.darkMode"
    >
        <section class="card glass soft-shadow border border-base-300/60 bg-base-100/85">
            <div class="card-body p-6 sm:p-8">
            <div class="mb-6 flex flex-wrap items-center justify-between gap-3">
                <div class="join">
                    <button type="button" class="btn join-item btn-sm" :class="state.outputType === 'print' ? 'btn-primary' : 'btn-outline'" @click="state.outputType = 'print'">Impresión</button>
                    <button type="button" class="btn join-item btn-sm" :class="state.outputType === 'digital' ? 'btn-primary' : 'btn-outline'" @click="state.outputType = 'digital'">Digital</button>
                </div>
                <span class="badge badge-warning badge-outline px-4 py-3 text-sm font-semibold">Sugerencias orientadas por objetivo</span>
            </div>

            <div class="alert mb-6 border border-base-300 bg-base-100/80 text-base-content shadow-sm">
                <span>
                    Se está recomendando formato para:
                    <strong>{{ objectiveTitle }}</strong>
                </span>
            </div>

            <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <button
                    v-for="item in formatCards"
                    :key="item.id"
                    type="button"
                    class="card rounded-[28px] border text-left transition"
                    :class="state.format === item.id ? 'border-2 border-primary bg-primary/10 shadow-md ring-2 ring-primary/20' : 'border-base-300 bg-base-100 hover:border-primary/40 hover:shadow-sm'"
                    @click="state.format = item.id"
                >
                    <div class="card-body p-5">
                        <div class="mx-auto rounded-[20px] bg-gradient-to-br" :class="[item.gradient, item.shape]"></div>
                        <p class="mt-4 text-base font-semibold text-base-content">{{ item.title }}</p>
                        <p class="mt-2 text-sm leading-6 text-base-content/75">{{ item.description }}</p>
                    </div>
                </button>
            </div>

            <div class="card mt-6 border border-base-300 bg-base-100/80 shadow-sm">
                <div class="card-body p-5">
                <p class="text-sm font-semibold text-base-content">Tamaños sugeridos</p>
                <div class="mt-3 flex flex-wrap gap-3">
                    <button
                        v-for="size in sizes"
                        :key="size"
                        type="button"
                        class="btn btn-sm rounded-full"
                        :class="state.size === size ? 'btn-primary' : 'btn-outline'"
                        @click="state.size = size"
                    >
                        {{ size }}
                    </button>
                </div>
                </div>
            </div>
            <StepFooter :previous-url="navigation.previous" :next-url="navigation.next" />
            </div>
        </section>
    </DesignerLayout>
</template>
