<script setup>
import DesignerLayout from '../../Layouts/DesignerLayout.vue';
import StepFooter from '../../Components/designer/StepFooter.vue';
import { computed } from 'vue';
import { objectiveOptions } from '../../data/designer';
import { useDesignerState } from '../../composables/useDesignerState';

defineProps({ currentStep: String, steps: Array, navigation: Object });
const state = useDesignerState();
const objectiveTitle = computed(() => objectiveOptions.find((item) => item.id === state.objective)?.title ?? 'Genérico');
</script>

<template>
    <DesignerLayout
        title="Exportar"
        eyebrow="Pantalla 7"
        description="Elige cómo descargar el diseño."
        :current-step="currentStep"
        :steps="steps"
        :dark-mode="state.darkMode"
        @toggle-dark="state.darkMode = !state.darkMode"
    >
        <section class="grid gap-6 xl:grid-cols-[1fr_340px]">
            <div class="glass soft-shadow rounded-[32px] border border-white/70 p-6 sm:p-8 dark:border-slate-700/70">
                <div class="grid gap-6 lg:grid-cols-2">
                    <div class="rounded-[28px] bg-neutral p-6 text-neutral-content">
                        <p class="text-xs font-semibold uppercase tracking-[0.22em] text-white/60">Exportar</p>
                        <h3 class="mt-3 text-3xl font-semibold">Tu diseño está listo</h3>
                        <p class="mt-4 text-sm leading-6 text-white/78">
                            Elige el formato final respetando el tamaño {{ state.size.toLowerCase() }} y el objetivo {{ objectiveTitle.toLowerCase() }}.
                        </p>
                        <div class="mt-6 flex flex-col gap-4">
                            <div>
                                <button class="btn h-auto w-full rounded-[24px] bg-white px-5 py-4 text-left text-slate-950 hover:bg-white">
                                    <span class="block text-base font-semibold">PDF</span>
                                </button>
                                <p class="mt-2 text-sm text-white/70">Ideal para imprimir en papel y mantener el formato físico.</p>
                            </div>
                            <div>
                                <button class="btn btn-outline h-auto w-full rounded-[24px] px-5 py-4 text-left text-white hover:bg-white/10">
                                    <span class="block text-base font-semibold">Imagen</span>
                                </button>
                                <p class="mt-2 text-sm text-white/70">Útil para compartir rápido o usar en canales digitales.</p>
                            </div>
                        </div>
                    </div>
                    <div class="card border border-base-300 bg-base-100/80">
                        <div class="card-body">
                        <div class="flex h-14 w-14 items-center justify-center rounded-full bg-success/15 text-2xl text-success">✓</div>
                        <h4 class="mt-4 text-2xl font-semibold text-base-content">Listo para descargar</h4>
                        <p class="mt-3 text-sm leading-6 text-base-content/75">
                            Después podrás volver al editor, duplicar esta pieza o crear una nueva manteniendo la misma experiencia dark/light.
                        </p>
                        </div>
                    </div>
                </div>
                <StepFooter :previous-url="navigation.previous" />
            </div>

            <div class="glass soft-shadow rounded-[32px] border border-white/70 p-6 dark:border-slate-700/70">
                <p class="text-sm font-semibold uppercase tracking-[0.22em] text-primary">Estado móvil</p>
                <div class="mx-auto mt-5 max-w-[280px] rounded-[36px] bg-slate-950 p-3 shadow-2xl">
                    <div class="overflow-hidden rounded-[30px] bg-white dark:bg-slate-900">
                        <div class="bg-gradient-to-br from-violet-700 via-fuchsia-600 to-pink-500 p-5 text-white">
                            <p class="text-xs uppercase tracking-[0.22em] text-white/70">Single-app · móvil</p>
                            <h4 class="mt-4 text-2xl font-black">{{ state.content.title }}</h4>
                            <p class="mt-2 text-sm text-white/85">{{ state.content.subtitle }}</p>
                        </div>
                        <div class="space-y-3 p-4 text-sm dark:text-slate-100">
                            <div class="rounded-2xl bg-slate-100 px-4 py-3 font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-100">Paso final · Exportar</div>
                            <div class="rounded-2xl border border-violet-200 bg-violet-50 px-4 py-3 font-semibold text-violet-700 dark:border-violet-400/30 dark:bg-violet-500/10 dark:text-violet-200">PDF para imprimir</div>
                            <div class="rounded-2xl border border-slate-200 px-4 py-3 text-slate-700 dark:border-slate-700 dark:text-slate-100">Imagen JPG / PNG</div>
                            <button class="w-full rounded-full bg-slate-950 px-5 py-3 font-semibold text-white dark:bg-violet-500 dark:text-slate-950">Descargar</button>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    </DesignerLayout>
</template>
