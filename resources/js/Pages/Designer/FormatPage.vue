<script setup>
import SelectionIndicator from '../../Components/designer/SelectionIndicator.vue';
import StepFooter from '../../Components/designer/StepFooter.vue';
import DesignerLayout from '../../Layouts/DesignerLayout.vue';
import { computed } from 'vue';
import { formatCards, inferFormatFromSizeOption, objectiveRecommendations, objectiveOptions } from '../../data/designer';
import { useDesignerState } from '../../composables/useDesignerState';

defineProps({ currentStep: String, steps: Array, navigation: Object });
const state = useDesignerState();

const sizes = computed(() => {
    if (!state.outputType) {
        return [];
    }

    const rules = objectiveRecommendations[state.objective] ?? objectiveRecommendations.generic;
    return rules[state.outputType];
});

const objectiveTitle = computed(() => objectiveOptions.find((item) => item.id === state.objective)?.title ?? 'Sin objetivo');
const activeSubstep = computed(() => {
    if (!state.outputType) return 1;
    if (!state.format) return 2;
    return 3;
});

const selectSizeOption = (option) => {
    state.size = option.label;

    if (state.format === 'other' && option.formatHint) {
        state.format = option.formatHint;
    }
};
</script>

<template>
    <DesignerLayout
        title="Formato y salida"
        eyebrow="Pantalla 3"
        description="Sigue estos pasos: primero elige si es para impresión o digital, después el formato y por último el tamaño."
        :hint="state.objective ? ('Objetivo activo: ' + objectiveTitle) : ''"
        :current-step="currentStep"
        :steps="steps"
        :dark-mode="state.darkMode"
        @toggle-dark="state.darkMode = !state.darkMode"
    >
        <section class="card glass soft-shadow border border-base-300/60 bg-base-100/85">
            <div class="card-body p-6 sm:p-8">
                <div class="mb-4 alert border border-base-300 bg-base-100/80 text-base-content shadow-sm">
                    <span>Para continuar debes completar las 3 elecciones en este orden.</span>
                </div>

                <div v-if="state.objective" class="alert mb-6 border border-base-300 bg-base-100/80 text-base-content shadow-sm">
                    <span>
                        Recomendación para:
                        <strong>{{ objectiveTitle }}</strong>
                    </span>
                </div>

                <div class="space-y-6">
                    <div class="card bg-base-100/80 shadow-sm transition" :class="activeSubstep === 1 ? 'border-4 border-primary shadow-md ring-2 ring-primary/20' : 'border border-base-300'">
                        <div class="card-body p-5">
                            <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
                                <div>
                                    <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Paso 1</p>
                                    <p class="mt-1 text-base font-semibold text-base-content">Elige dónde se va a ver tu diseño</p>
                                </div>
                                <span class="badge" :class="state.outputType ? 'badge-success badge-outline' : 'badge-warning badge-outline'">
                                    {{ state.outputType ? 'Elegido' : 'Pendiente' }}
                                </span>
                            </div>
                            <div class="grid gap-4 md:grid-cols-2">
                                <button
                                    type="button"
                                    class="card rounded-[24px] border-2 text-left transition"
                                    :class="state.outputType === 'print'
                                        ? 'border-primary bg-primary/12 shadow-lg ring-4 ring-primary/20'
                                        : 'border-warning/60 bg-warning/10 hover:border-primary/50 hover:bg-primary/5 hover:shadow-md'"
                                    @click="state.outputType = 'print'; state.size = null"
                                >
                                    <div class="card-body p-5">
                                        <div class="mb-2 flex items-center justify-between gap-3">
                                            <p class="text-base font-semibold text-base-content">Para imprimir</p>
                                            <SelectionIndicator :selected="state.outputType === 'print'" idle-class="badge-warning badge-outline" />
                                        </div>
                                        <p class="text-sm leading-6 text-base-content/75">El resultado final será en papel, por ejemplo un cartel o un flier.</p>
                                        <p class="text-xs uppercase tracking-[0.2em] text-base-content/50">A2, A3, A4, A5, PDF</p>
                                    </div>
                                </button>

                                <button
                                    type="button"
                                    class="card rounded-[24px] border-2 text-left transition"
                                    :class="state.outputType === 'digital'
                                        ? 'border-primary bg-primary/12 shadow-lg ring-4 ring-primary/20'
                                        : 'border-info/60 bg-info/10 hover:border-primary/50 hover:bg-primary/5 hover:shadow-md'"
                                    @click="state.outputType = 'digital'; state.size = null"
                                >
                                    <div class="card-body p-5">
                                        <div class="mb-2 flex items-center justify-between gap-3">
                                            <p class="text-base font-semibold text-base-content">Para pantalla</p>
                                            <SelectionIndicator :selected="state.outputType === 'digital'" idle-class="badge-info badge-outline" />
                                        </div>
                                        <p class="text-sm leading-6 text-base-content/75">El resultado final se verá en móvil, web o redes sociales.</p>
                                        <p class="text-xs uppercase tracking-[0.2em] text-base-content/50">Instagram, Facebook, historias, banners</p>
                                    </div>
                                </button>
                            </div>
                        </div>
                    </div>

                    <div class="card bg-base-100/80 shadow-sm transition" :class="!state.outputType ? 'border border-base-300 opacity-70 blur-[2px] saturate-50 pointer-events-none select-none' : (activeSubstep === 2 ? 'border-4 border-primary shadow-md ring-2 ring-primary/20' : 'border border-base-300')">
                        <div class="card-body p-5">
                            <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
                                <div>
                                    <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Paso 2</p>
                                    <p class="mt-1 text-base font-semibold text-base-content">Elige el formato del diseño</p>
                                </div>
                                <span class="badge" :class="state.format ? 'badge-success badge-outline' : 'badge-warning badge-outline'">
                                    {{ state.format ? 'Elegido' : (state.outputType ? 'Pendiente' : 'Bloqueado') }}
                                </span>
                            </div>
                            <p v-if="!state.outputType" class="mb-4 text-sm text-base-content/70">Primero debes elegir si es impresión o digital.</p>
                            <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                                <button
                                    v-for="item in formatCards"
                                    :key="item.id"
                                    type="button"
                                    class="card rounded-[28px] border text-left transition"
                                    :disabled="!state.outputType"
                                    :class="state.format === item.id ? 'border-2 border-primary bg-primary/10 shadow-md ring-2 ring-primary/20' : 'border-base-300 bg-base-100 hover:border-primary/40 hover:shadow-sm'"
                                    @click="state.format = item.id; state.size = null"
                                >
                                    <div class="card-body p-5">
                                        <div class="flex items-start justify-between gap-3">
                                            <div class="mx-auto rounded-[20px] bg-gradient-to-br" :class="[item.gradient, item.shape]"></div>
                                            <SelectionIndicator :selected="state.format === item.id" />
                                        </div>
                                        <p class="mt-4 text-base font-semibold text-base-content">{{ item.title }}</p>
                                        <p class="mt-2 text-sm leading-6 text-base-content/75">{{ item.description }}</p>
                                        <p v-if="item.id === 'other'" class="mt-2 text-xs uppercase tracking-[0.18em] text-base-content/50">
                                            El sistema propondrá el formato automáticamente según el tamaño digital que elijas después.
                                        </p>
                                    </div>
                                </button>
                            </div>
                        </div>
                    </div>

                    <div class="card bg-base-100/80 shadow-sm transition" :class="!state.outputType || !state.format ? 'border border-base-300 opacity-70 blur-[2px] saturate-50 pointer-events-none select-none' : (activeSubstep === 3 ? 'border-4 border-primary shadow-md ring-2 ring-primary/20' : 'border border-base-300')">
                        <div class="card-body p-5">
                            <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
                                <div>
                                    <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Paso 3</p>
                                    <p class="mt-1 text-base font-semibold text-base-content">Elige el tamaño</p>
                                </div>
                                <span class="badge" :class="state.size ? 'badge-success badge-outline' : 'badge-warning badge-outline'">
                                    {{ state.size ? 'Elegido' : (state.outputType && state.format ? 'Pendiente' : 'Bloqueado') }}
                                </span>
                            </div>
                            <p v-if="!state.outputType || !state.format" class="mb-4 text-sm text-base-content/70">Primero debes elegir el tipo de salida y el formato.</p>
                            <div v-if="state.outputType" class="flex flex-wrap gap-3">
                                <button
                                    v-for="size in sizes"
                                    :key="size.id"
                                    type="button"
                                    class="btn h-auto min-h-0 rounded-2xl px-4 py-3 text-left"
                                    :disabled="!state.format"
                                    :class="state.size === size.label ? 'btn-primary' : 'btn-outline'"
                                    @click="selectSizeOption(size)"
                                >
                                    <div class="flex flex-col items-start">
                                        <span>{{ size.label }}</span>
                                        <span class="text-xs opacity-70">{{ size.detail }}</span>
                                    </div>
                                    <span v-if="state.size === size.label" class="ml-2 font-bold">✓</span>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <StepFooter :previous-url="navigation.previous" :next-url="navigation.next" :next-disabled="!state.outputType || !state.format || !state.size" />
            </div>
        </section>
    </DesignerLayout>
</template>
