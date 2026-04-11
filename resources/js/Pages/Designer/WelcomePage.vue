<script setup>
import { onMounted } from 'vue';
import ChoiceCard from '../../Components/designer/ChoiceCard.vue';
import StepFooter from '../../Components/designer/StepFooter.vue';
import DesignerLayout from '../../Layouts/DesignerLayout.vue';
import { modeOptions } from '../../data/designer';
import { resetDesignerState, useDesignerState } from '../../composables/useDesignerState';

defineProps({ currentStep: String, steps: Array, navigation: Object });
const state = useDesignerState();

onMounted(() => {
    resetDesignerState();
});
</script>

<template>
    <DesignerLayout
        title="Entrada a la app"
        eyebrow="Pantalla 1"
        description="Elige cómo quieres empezar."
        :current-step="currentStep"
        :steps="steps"
        :dark-mode="state.darkMode"
        @toggle-dark="state.darkMode = !state.darkMode"
    >
        <section>
            <div class="card glass soft-shadow border border-base-300/60 bg-base-100/85">
                <div class="card-body p-7 sm:p-10">
                    <div class="mb-6 max-w-3xl">
                        <p class="text-sm leading-6 text-base-content/75">Selecciona una opción para continuar.</p>
                    </div>
                    <div class="grid gap-4 md:grid-cols-2">
                        <ChoiceCard
                            v-for="item in modeOptions"
                            :key="item.id"
                            :title="item.title"
                            :description="item.description"
                            :tag="item.badge"
                            :selected="state.mode === item.id"
                            @click="state.mode = item.id"
                        />
                    </div>
                    <StepFooter :next-url="navigation.next" />
                </div>
            </div>
        </section>
    </DesignerLayout>
</template>
