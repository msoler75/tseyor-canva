<script setup>
import axios from 'axios';
import { router, usePage } from '@inertiajs/vue3';
import { computed, ref } from 'vue';
import ChoiceCard from './../Components/designer/ChoiceCard.vue';
import SelectionIndicator from './../Components/designer/SelectionIndicator.vue';
import TemplateCard from './../Components/designer/TemplateCard.vue';
import DesignerAssistant from './../Components/designer/DesignerAssistant.vue';
import DesignerLayout from './../Layouts/DesignerLayout.vue';
import {
    filterLabels,
    formatCards,
    objectiveOptions,
    objectiveRecommendations,
    templateCatalog,
    templateFilters,
} from '../data/designer';
import { flushDesignerStatePersistence, resetDesignerState, useDesignerState } from '../composables/useDesignerState';

const props = defineProps({
    currentStep: String,
    steps: Array,
    navigation: Object,
    designs: {
        type: Array,
        default: () => [],
    },
    communityDesigns: {
        type: Array,
        default: () => [],
    }
});

const page = usePage();
const state = useDesignerState();
const assistantOpen = ref(false);
const assistantStep = ref('objective');

const assistantSteps = [
    { id: 'objective', label: 'Objetivo' },
    { id: 'format', label: 'Formato' },
    { id: 'content', label: 'Datos' },
    { id: 'templates', label: 'Plantillas' },
];

const authUser = computed(() => page.props.auth?.user ?? null);
const recentProjects = computed(() => props.designs ?? []);

const communityDesigns = computed(() => props.communityDesigns ?? []);

const assistantIndex = computed(() => assistantSteps.findIndex((step) => step.id === assistantStep.value));
const isFirstStep = computed(() => assistantIndex.value <= 0);
const isLastStep = computed(() => assistantIndex.value === assistantSteps.length - 1);

const objectiveTitle = computed(() => objectiveOptions.find((item) => item.id === state.objective)?.title ?? 'Sin objetivo');

const sizes = computed(() => {
    if (!state.outputType) return [];
    const rules = objectiveRecommendations[state.objective] ?? objectiveRecommendations.generic;
    return rules[state.outputType];
});

const selectedSizeId = computed({
    get: () => sizes.value.find((size) => size.label === state.size)?.id ?? '',
    set: (sizeId) => {
        const selected = sizes.value.find((size) => size.id === sizeId);
        if (selected) {
            selectSizeOption(selected);
        }
    },
});

const fields = computed(() => (objectiveRecommendations[state.objective] ?? objectiveRecommendations.generic).fields);

const fieldPlaceholders = {
    title: 'Ej. Festival de Primavera',
    subtitle: 'Ej. Musica, talleres y actividades para toda la familia',
    date: 'Ej. 25 abril 2026',
    time: 'Ej. 18:00',
    location: 'Ej. Plaza Mayor',
    platform: 'Ej. https://zoom.us/j/123456789',
    teacher: 'Ej. Maria Lopez',
    price: 'Ej. Entrada gratuita',
    contact: 'Ej. 600 123 123 · hola@tudominio.com',
    extra: 'Ej. Aforo limitado · Reserva previa · Traer material',
};

const filteredTemplates = computed(() => (!state.templateCategory || state.templateCategory === 'all')
    ? templateCatalog
    : templateCatalog.filter((item) => item.category === state.templateCategory));

const metaLine = computed(() => [state.content.date, state.content.time].filter(Boolean).join(' · '));
const venueLine = computed(() => {
    if (state.objective === 'event_virtual') {
        return state.content.platform?.trim() || state.content.contact?.trim() || '';
    }

    return state.content.location?.trim() || state.content.contact?.trim() || '';
});

const canGoNext = computed(() => {
    if (assistantStep.value === 'objective') return Boolean(state.objective);
    if (assistantStep.value === 'format') return Boolean(state.outputType && state.format && state.size);
    return true;
});

const openAssistant = () => {
    resetDesignerState();
    state.mode = 'guided';
    state.templateCategory = 'all';
    state.currentDesignUuid = null;
    state.designSurface = null;
    assistantStep.value = 'objective';
    assistantOpen.value = true;
};

const closeAssistant = () => {
    assistantOpen.value = false;
};

const goNext = () => {
    if (!canGoNext.value || isLastStep.value) return;
    assistantStep.value = assistantSteps[assistantIndex.value + 1].id;
};

const goPrevious = () => {
    if (isFirstStep.value) return;
    assistantStep.value = assistantSteps[assistantIndex.value - 1].id;
};

const selectSizeOption = (option) => {
    state.size = option.label;

    if (state.format === 'other' && option.formatHint) {
        state.format = option.formatHint;
    }
};

const finishAndOpenEditor = () => {
    if (!authUser.value) {
        window.alert('Debes iniciar sesión para crear y guardar diseños.');
        return;
    }

    assistantOpen.value = false;

    axios.post('/designer/designs', {
        name: state.designTitle,
        state: JSON.parse(JSON.stringify(state)),
    }).then((response) => {
        const designUuid = response.data?.design?.uuid;
        if (designUuid) {
            state.currentDesignUuid = designUuid;
            router.visit(`/designer/designs/${designUuid}/edit`);
        }
    }).catch((error) => {
        console.error('No se pudo crear el diseño inicial', error);
    });
};

const openExistingDesign = async (design) => {
    if (!design?.uuid) return;

    try {
        await flushDesignerStatePersistence();
    } catch (error) {
        console.error('Failed to flush state before opening design', error);
    }

    router.visit(`/designer/designs/${design.uuid}/edit`);
};

const loginAsDev = async () => {
    router.visit('/auth/login-dev');
};

const formatProjectUpdatedAt = (value) => {
    if (!value) return 'Sin fecha';

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Sin fecha';

    return new Intl.DateTimeFormat('es-ES', {
        dateStyle: 'medium',
        timeStyle: 'short',
    }).format(date);
};

const logoutFromApp = async () => {
try {
    await axios.post('/auth/logout');
    router.visit('/');
  } catch (error) {
    console.error('Failed to logout from editor app', error);
};
}


const duplicateDesign = async (design) => {
    if (!design?.uuid) return;

    try {
        const response = await axios.post(`/designer/designs/${design.uuid}/duplicate`);
        const duplicateUuid = response.data?.design?.uuid;
        router.reload();

        if (duplicateUuid) {
            router.visit(`/designer/designs/${duplicateUuid}/edit`);
        }
    } catch (error) {
        console.error('No se pudo duplicar el diseño', error);
    }
};

const renameDesign = async (design) => {
    if (!design?.uuid) return;

    const nextTitle = window.prompt('Nuevo título del diseño', design.name || 'Diseño sin título');
    if (nextTitle === null) return;

    try {
        await axios.patch(`/designer/designs/${design.uuid}/rename`, {
            name: nextTitle,
        });
        router.reload();
    } catch (error) {
        console.error('No se pudo renombrar el diseño', error);
    }
};

const deleteDesign = async (design) => {
    if (!design?.uuid) return;

    const confirmed = window.confirm(`¿Eliminar "${design.name}"?`);
    if (!confirmed) return;

    try {
        await axios.delete(`/designer/designs/${design.uuid}`);
        router.reload();
    } catch (error) {
        console.error('No se pudo borrar el diseño', error);
    }
};
</script>

<template>
    <DesignerLayout
        title="TSEYOR Canva"
        eyebrow="Modo casa"
        description="Crea un diseño nuevo, abre tus proyectos guardados o reaprovecha ideas de la comunidad."
        :current-step="currentStep"
        :steps="steps"
        :show-steps="false"
        :dark-mode="state.darkMode"
        @toggle-dark="state.darkMode = !state.darkMode"
    >
        <section class="grid gap-6 lg:grid-cols-[1.1fr,0.9fr]">
            <div class="card border border-base-300/70 bg-base-100/90 shadow-sm">
                <div class="card-body p-7">
                    <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Nuevo diseño</p>
                    <h2 class="mt-2 text-3xl font-semibold">Empieza desde cero en segundos</h2>
                    <p class="mt-3 max-w-2xl text-sm leading-6 text-base-content/75">
                        Pulsa el boton de crear para abrir el asistente flotante. Te guiara por objetivo, formato, datos y plantilla.
                    </p>

                    <div class="mt-7">
                        <button
                            type="button"
                            class="btn btn-primary btn-lg rounded-full pl-2 pr-8"
                            @click="openAssistant"
                        >
                            <span class="mr-2 inline-flex h-9 w-9 items-center justify-center rounded-full bg-primary-content/15 text-2xl leading-none">+</span>
                            CREAR
                        </button>
                        <button
                            v-if="!authUser"
                            type="button"
                            class="btn btn-outline btn-lg rounded-full px-8 ml-3"
                            @click="loginAsDev"
                        >
                            <IconifyIcon icon="ph:rocket-launch-bold" class="text-lg" />
                        </button>
                    </div>
                </div>
            </div>

            <div class="card border border-base-300/70 bg-base-100/90 shadow-sm">
                <div class="card-body p-6">
                    <div class="mb-4 flex items-center justify-between gap-3">
                        <h3 class="text-lg font-semibold">Tus proyectos recientes</h3>
                        <div v-if="authUser" class="flex items-center gap-2">
                            <span class="badge badge-outline">{{ authUser.name }}</span>
                            <button type="button" class="btn btn-ghost btn-sm rounded-full" @click="logoutFromApp">Logout</button>
                        </div>
                    </div>

                    <div v-if="recentProjects.length" class="space-y-3">
                        <div
                            v-for="project in recentProjects"
                            :key="project.uuid"
                            class="flex items-center justify-between rounded-2xl border border-base-300 bg-base-100 px-4 py-3 text-left hover:border-primary/50"
                        >
                            <button
                                type="button"
                                class="min-w-0 flex flex-1 items-center gap-3 text-left"
                                @click="openExistingDesign(project)"
                            >
                                <div class="h-14 w-14 overflow-hidden rounded-xl border border-base-300 bg-base-200 shrink-0">
                                    <img v-if="project.thumbnail_url" :src="project.thumbnail_url" :alt="project.name" class="h-full w-full object-cover" />
                                    <div v-else class="flex h-full w-full items-center justify-center text-[10px] text-base-content/45">Sin miniatura</div>
                                </div>
                                <div class="min-w-0">
                                    <p class="font-medium text-base-content truncate">{{ project.name }}</p>
                                    <p class="text-xs text-base-content/65">{{ formatProjectUpdatedAt(project.updated_at) }}</p>
                                </div>
                            </button>
                            <div class="dropdown dropdown-end">
                                <button type="button" tabindex="0" class="btn btn-ghost btn-sm btn-circle">
                                    <IconifyIcon icon="ph:dots-three-outline-vertical-fill" class="text-lg" />
                                </button>
                                <ul tabindex="0" class="dropdown-content menu z-70 mt-2 w-52 rounded-2xl border border-base-300 bg-base-100 p-2 shadow-xl">
                                    <li><button type="button" @click="openExistingDesign(project)">Abrir</button></li>
                                    <li><button type="button" @click="duplicateDesign(project)">Hacer una copia</button></li>
                                    <li><button type="button" @click="renameDesign(project)">Cambiar título</button></li>
                                    <li><button type="button" class="text-error" @click="deleteDesign(project)">Eliminar</button></li>
                                </ul>
                            </div>
                        </div>
                    </div>
                    <div v-else class="rounded-2xl border border-dashed border-base-300 bg-base-100 px-4 py-5 text-sm text-base-content/65">
                        {{ authUser ? 'Aún no tienes diseños guardados.' : 'Inicia sesión para ver tus diseños guardados.' }}
                    </div>
                </div>
            </div>
        </section>

        <section class="mt-6 card border border-base-300/70 bg-base-100/90 shadow-sm">
            <div class="card-body p-6">
                <div class="mb-4 flex items-center justify-between gap-3">
                    <h3 class="text-lg font-semibold">Últimos diseños de la comunidad</h3>
                    <span class="badge badge-primary badge-outline">Inspiración</span>
                </div>

                <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6">
                    <button
                        v-for="item in communityDesigns"
                        :key="item.uuid"
                        type="button"
                        class="rounded-2xl border border-base-300 bg-linear-to-br from-base-100 to-base-200 p-4 text-left hover:border-primary/60"
                        @click="openExistingDesign(item)"
                    >
                        <div class="h-28 rounded-xl bg-linear-to-br from-indigo-500 via-cyan-500 to-emerald-400 opacity-90 flex items-center justify-center">
                            <img v-if="item.thumbnail_url" :src="item.thumbnail_url" :alt="item.name" class="h-full w-full object-contain rounded-xl bg-white" />
                            <span v-else class="text-xs text-white/70">Sin miniatura</span>
                        </div>
                        <p class="mt-3 font-semibold">{{ item.name }}</p>
                        <p class="text-xs text-base-content/65">{{ item.objective || 'Comunidad' }}</p>
                        <p class="mt-2 text-xs font-medium text-primary">Clonar y editar</p>
                    </button>
                </div>
            </div>
        </section>

        <dialog v-if="assistantOpen" class="modal modal-open backdrop-blur-sm" style="z-index:90;">
            <div class="modal-box w-full max-w-3xl p-0 overflow-visible bg-base-100 rounded-[30px] shadow-2xl border border-base-300">
                <DesignerAssistant
                    :step="assistantStep"
                    :show-footer="true"
                    :show-close="true"
                    @close="closeAssistant"
                    @finish="finishAndOpenEditor"
                />
            </div>
        </dialog>
    </DesignerLayout>
</template>
