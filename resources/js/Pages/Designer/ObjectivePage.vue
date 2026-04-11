<script setup>
import ChoiceCard from '../../Components/designer/ChoiceCard.vue';
import StepFooter from '../../Components/designer/StepFooter.vue';
import DesignerLayout from '../../Layouts/DesignerLayout.vue';
import { objectiveOptions } from '../../data/designer';
import { useDesignerState } from '../../composables/useDesignerState';

defineProps({ currentStep: String, steps: Array, navigation: Object });
const state = useDesignerState();
</script>

<template>
    <DesignerLayout
        title="Objetivo de la pieza"
        eyebrow="Pantalla 2"
        description="Elige el objetivo de tu diseño."
        :current-step="currentStep"
        :steps="steps"
        :dark-mode="state.darkMode"
        @toggle-dark="state.darkMode = !state.darkMode"
    >
        <section class="glass soft-shadow rounded-[32px] border border-white/70 p-6 sm:p-8 dark:border-slate-700/70">
            <div class="alert mb-6 border border-base-300 bg-base-100/80 text-base-content">
                <span>Esto nos ayuda a recomendar tamaños, campos y plantillas.</span>
            </div>
            <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <ChoiceCard
                    v-for="item in objectiveOptions"
                    :key="item.id"
                    :title="item.title"
                    :description="item.description"
                    :recommendation="item.recommendation + ' · ' + item.categoryHint"
                    :selected="state.objective === item.id"
                    @click="state.objective = item.id"
                />
            </div>
            <div class="card mt-6 border border-base-300 bg-base-100/80">
                <div class="card-body text-sm leading-6 text-base-content/80">
                    Elige la opción que más se acerque a lo que quieres crear.
                </div>
            </div>
            <StepFooter :previous-url="navigation.previous" :next-url="navigation.next" :next-disabled="!state.objective" />
        </section>
    </DesignerLayout>
</template>
