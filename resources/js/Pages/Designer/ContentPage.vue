<script setup>
import StepFooter from '../../Components/designer/StepFooter.vue';
import DesignerLayout from '../../Layouts/DesignerLayout.vue';
import { computed } from 'vue';
import { objectiveRecommendations } from '../../data/designer';
import { useDesignerState } from '../../composables/useDesignerState';

defineProps({ currentStep: String, steps: Array, navigation: Object });
const state = useDesignerState();

const fields = computed(() => (objectiveRecommendations[state.objective] ?? objectiveRecommendations.generic).fields);
const metaLine = computed(() => state.objective === 'course'
    ? [state.content.teacher, state.content.date].filter(Boolean).join(' · ')
    : [state.content.date, state.content.location].filter(Boolean).join(' · '));
</script>

<template>
    <DesignerLayout
        title="Datos del contenido"
        eyebrow="Pantalla 4"
        description="Los campos se adaptan al objetivo elegido para preparar mejor las previews de plantillas."
        :current-step="currentStep"
        :steps="steps"
        :dark-mode="state.darkMode"
        @toggle-dark="state.darkMode = !state.darkMode"
    >
        <section class="glass soft-shadow rounded-[32px] border border-white/70 p-6 sm:p-8 dark:border-slate-700/70">
            <div class="grid gap-6 xl:grid-cols-[1.05fr_.95fr]">
                <div>
                    <div class="grid gap-4 sm:grid-cols-2">
                        <label
                            v-for="field in fields"
                            :key="field.key"
                            class="rounded-[22px] border border-base-300 bg-base-100/80 p-4 text-sm font-medium text-base-content"
                            :class="field.type === 'textarea' ? 'sm:col-span-2' : ''"
                        >
                            {{ field.label }}
                            <textarea v-if="field.type === 'textarea'" v-model="state.content[field.key]" class="textarea textarea-bordered mt-2 min-h-[120px] w-full text-base" @input="state.autosaveMessage = 'Guardado automático · hace un instante'"></textarea>
                            <input v-else v-model="state.content[field.key]" class="input input-bordered mt-2 w-full text-base" @input="state.autosaveMessage = 'Guardado automático · hace un instante'" />
                        </label>
                    </div>
                    <StepFooter :previous-url="navigation.previous" :next-url="navigation.next" />
                </div>

                <div class="space-y-5">
                    <div class="card border border-base-300 bg-base-100 shadow-sm">
                        <div class="card-body">
                            <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Resumen vivo</p>
                            <h3 class="mt-2 text-2xl font-bold text-base-content">{{ state.content.title }}</h3>
                            <p class="mt-1 text-sm leading-6 text-base-content/70">{{ state.content.subtitle }}</p>
                            <div class="mt-4 rounded-[24px] bg-neutral p-5 text-neutral-content">
                                <p class="text-xs uppercase tracking-[0.22em] text-neutral-content/60">Se usará para las previews</p>
                                <p class="mt-3 font-semibold">{{ metaLine }}</p>
                                <p class="mt-1 text-sm text-neutral-content/80">{{ state.content.contact }}</p>
                                <p class="mt-4 text-sm leading-6 text-neutral-content/85">{{ state.content.extra }}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    </DesignerLayout>
</template>
