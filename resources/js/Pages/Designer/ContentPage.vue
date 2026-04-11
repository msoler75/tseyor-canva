<script setup>
import StepFooter from '../../Components/designer/StepFooter.vue';
import DesignerLayout from '../../Layouts/DesignerLayout.vue';
import { computed } from 'vue';
import { objectiveRecommendations } from '../../data/designer';
import { useDesignerState } from '../../composables/useDesignerState';

defineProps({ currentStep: String, steps: Array, navigation: Object });
const state = useDesignerState();

const fields = computed(() => (objectiveRecommendations[state.objective] ?? objectiveRecommendations.generic).fields);
const fieldPlaceholders = {
    title: 'Ej. Festival de Primavera',
    subtitle: 'Ej. Música, talleres y actividades para toda la familia',
    date: 'Ej. 25 abril 2026',
    time: 'Ej. 18:00',
    location: 'Ej. Plaza Mayor',
    platform: 'Ej. https://zoom.us/j/123456789',
    teacher: 'Ej. María López',
    price: 'Ej. Entrada gratuita',
    contact: 'Ej. 600 123 123 · hola@tudominio.com',
    extra: 'Ej. Aforo limitado · Reserva previa · Traer material',
};

const previewValue = (key, fallback) => state.content[key]?.trim() || fallback;
</script>

<template>
    <DesignerLayout
        title="Datos del contenido"
        eyebrow="Pantalla 4"
        description="Rellena los datos del diseño."
        :current-step="currentStep"
        :steps="steps"
        :dark-mode="state.darkMode"
        @toggle-dark="state.darkMode = !state.darkMode"
    >
        <section class="glass soft-shadow rounded-[32px] border border-white/70 p-6 sm:p-8 dark:border-slate-700/70">
            <div class="">
                <div>
                    <div class="grid gap-4 sm:grid-cols-2">
                        <label
                            v-for="field in fields"
                            :key="field.key"
                            class="rounded-[22px] border border-base-300 bg-base-100/80 p-4 text-sm font-medium text-base-content"
                            :class="field.type === 'textarea' ? 'sm:col-span-2' : ''"
                        >
                            <span class="block">{{ field.label }}</span>
                            <span v-if="field.helper" class="mt-1 block text-xs font-normal leading-5 text-base-content/65">
                                {{ field.helper }}
                            </span>
                            <textarea v-if="field.type === 'textarea'" v-model="state.content[field.key]" class="textarea textarea-bordered mt-2 min-h-[120px] w-full text-base" :placeholder="fieldPlaceholders[field.key] || 'Escribe aquí...'" @input="state.autosaveMessage = 'Guardado automático · hace un instante'"></textarea>
                            <input v-else v-model="state.content[field.key]" class="input input-bordered mt-2 w-full text-base" :placeholder="fieldPlaceholders[field.key] || 'Escribe aquí...'" @input="state.autosaveMessage = 'Guardado automático · hace un instante'" />
                        </label>
                    </div>
                    <StepFooter :previous-url="navigation.previous" :next-url="navigation.next" />
                </div>

            </div>
        </section>
    </DesignerLayout>
</template>
