<script setup>
import axios from 'axios';
import { router, usePage } from '@inertiajs/vue3';
import { computed, ref } from 'vue';
import ChoiceCard from '../../Components/designer/ChoiceCard.vue';
import SelectionIndicator from '../../Components/designer/SelectionIndicator.vue';
import TemplateCard from '../../Components/designer/TemplateCard.vue';
import DesignerLayout from '../../Layouts/DesignerLayout.vue';
import {
    filterLabels,
    formatCards,
    objectiveOptions,
    objectiveRecommendations,
    templateCatalog,
    templateFilters,
} from '../../data/designer';
import { flushDesignerStatePersistence, resetDesignerState, useDesignerState } from '../../composables/useDesignerState';

const props = defineProps({
    currentStep: String,
    steps: Array,
    navigation: Object,
    designs: {
        type: Array,
        default: () => [],
    },
    devLoginToken: {
        type: String,
        default: null,
    },
});

const page = usePage();
const state = useDesignerState();
const assistantOpen = ref(false);
const assistantStep = ref('objective');
const loggingInDev = ref(false);

const assistantSteps = [
    { id: 'objective', label: 'Objetivo' },
    { id: 'format', label: 'Formato' },
    { id: 'content', label: 'Datos' },
    { id: 'templates', label: 'Plantillas' },
];

const authUser = computed(() => page.props.auth?.user ?? null);
const recentProjects = computed(() => props.designs ?? []);

const communityDesigns = [
    { id: 'community-1', title: 'Festival neon', author: 'Comunidad TSEYOR' },
    { id: 'community-2', title: 'Curso minimal', author: 'Studio Vega' },
    { id: 'community-3', title: 'Promo urbana', author: 'Plantillas Pro' },
    { id: 'community-4', title: 'Evento corporativo', author: 'Blue Team' },
];

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
    assistantOpen.value = false;
    router.visit('/designer/editor');
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
    if (!props.devLoginToken || loggingInDev.value) return;

    loggingInDev.value = true;

    try {
        const response = await axios.post('/auth/login', {
            token: props.devLoginToken,
        });

        const accessToken = response.data?.access_token;
        if (accessToken) {
            window.localStorage.setItem('tseyor_jwt', accessToken);
            window.axios.defaults.headers.common.Authorization = `Bearer ${accessToken}`;
        }

        router.reload();
    } catch (error) {
        console.error('No se pudo iniciar sesión en modo dev', error);
    } finally {
        loggingInDev.value = false;
    }
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
        description="Crea un diseno nuevo, abre tus proyectos guardados o reaprovecha ideas de la comunidad."
        :current-step="currentStep"
        :steps="steps"
        :show-steps="false"
        :dark-mode="state.darkMode"
        @toggle-dark="state.darkMode = !state.darkMode"
    >
        <section class="grid gap-6 lg:grid-cols-[1.1fr,0.9fr]">
            <div class="card border border-base-300/70 bg-base-100/90 shadow-sm">
                <div class="card-body p-7">
                    <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Nuevo diseno</p>
                    <h2 class="mt-2 text-3xl font-semibold">Empieza desde cero en segundos</h2>
                    <p class="mt-3 max-w-2xl text-sm leading-6 text-base-content/75">
                        Pulsa el boton de crear para abrir el asistente flotante. Te guiara por objetivo, formato, datos y plantilla.
                    </p>

                    <div class="mt-7">
                        <button
                            type="button"
                            class="btn btn-primary btn-lg rounded-full px-8"
                            @click="openAssistant"
                        >
                            <span class="mr-2 inline-flex h-9 w-9 items-center justify-center rounded-full bg-primary-content/15 text-2xl leading-none">+</span>
                            CREAR
                        </button>
                        <button
                            v-if="!authUser && devLoginToken"
                            type="button"
                            class="btn btn-outline btn-lg rounded-full px-8 ml-3"
                            :disabled="loggingInDev"
                            @click="loginAsDev"
                        >
                            <IconifyIcon icon="ph:rocket-launch-bold" class="text-lg" />
                            {{ loggingInDev ? 'Entrando...' : 'Login dev' }}
                        </button>
                    </div>
                </div>
            </div>

            <div class="card border border-base-300/70 bg-base-100/90 shadow-sm">
                <div class="card-body p-6">
                    <div class="mb-4 flex items-center justify-between gap-3">
                        <h3 class="text-lg font-semibold">Tus proyectos recientes</h3>
                        <span v-if="authUser" class="badge badge-outline">{{ authUser.name }}</span>
                    </div>

                    <div v-if="recentProjects.length" class="space-y-3">
                        <div
                            v-for="project in recentProjects"
                            :key="project.uuid"
                            class="flex items-center justify-between rounded-2xl border border-base-300 bg-base-100 px-4 py-3 text-left hover:border-primary/50"
                        >
                            <button
                                type="button"
                                class="min-w-0 flex-1 text-left"
                                @click="openExistingDesign(project)"
                            >
                                <p class="font-medium text-base-content truncate">{{ project.name }}</p>
                                <p class="text-xs text-base-content/65">{{ formatProjectUpdatedAt(project.updated_at) }}</p>
                            </button>
                            <div class="dropdown dropdown-end">
                                <button type="button" tabindex="0" class="btn btn-ghost btn-sm btn-circle">
                                    <IconifyIcon icon="ph:dots-three-outline-vertical-fill" class="text-lg" />
                                </button>
                                <ul tabindex="0" class="dropdown-content menu z-[70] mt-2 w-52 rounded-2xl border border-base-300 bg-base-100 p-2 shadow-xl">
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
                    <h3 class="text-lg font-semibold">Ultimos disenos de la comunidad</h3>
                    <span class="badge badge-primary badge-outline">Inspiracion</span>
                </div>

                <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    <button
                        v-for="item in communityDesigns"
                        :key="item.id"
                        type="button"
                        class="rounded-2xl border border-base-300 bg-gradient-to-br from-base-100 to-base-200 p-4 text-left hover:border-primary/60"
                        @click="openAssistant"
                    >
                        <div class="h-28 rounded-xl bg-gradient-to-br from-indigo-500 via-cyan-500 to-emerald-400 opacity-90"></div>
                        <p class="mt-3 font-semibold">{{ item.title }}</p>
                        <p class="text-xs text-base-content/65">{{ item.author }}</p>
                        <p class="mt-2 text-xs font-medium text-primary">Clonar y editar</p>
                    </button>
                </div>
            </div>
        </section>

        <div v-if="assistantOpen" class="fixed inset-0 z-[90]">
            <div class="absolute inset-0 bg-slate-950/55" @click="closeAssistant"></div>

            <div class="absolute left-1/2 top-1/2 z-[91] w-[min(1120px,92vw)] -translate-x-1/2 -translate-y-1/2">
                <section class="max-h-[90vh] overflow-hidden rounded-[30px] border border-base-300 bg-base-100 shadow-2xl">
                    <header class="border-b border-base-300 px-6 py-5">
                        <div class="flex items-start justify-between gap-4">
                            <div>
                                <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Asistente de creacion</p>
                                <h3 class="mt-1 text-2xl font-semibold">Configura tu diseno</h3>
                                <p class="mt-1 text-sm text-base-content/70">Objetivo, formato, datos y plantilla antes de entrar al editor.</p>
                            </div>
                            <button type="button" class="btn btn-ghost btn-sm rounded-full" @click="closeAssistant">Cerrar</button>
                        </div>

                        <nav class="mt-4 flex flex-wrap gap-2">
                            <button
                                v-for="(step, index) in assistantSteps"
                                :key="step.id"
                                type="button"
                                class="btn btn-sm rounded-full"
                                :class="assistantStep === step.id ? 'btn-primary' : (index <= assistantIndex ? 'btn-outline' : 'btn-ghost')"
                                @click="assistantStep = step.id"
                            >
                                {{ index + 1 }}. {{ step.label }}
                            </button>
                        </nav>
                    </header>

                    <div class="max-h-[62vh] overflow-y-auto px-6 py-5">
                        <section v-if="assistantStep === 'objective'" class="space-y-4">
                            <div class="alert border border-base-300 bg-base-100/80 text-base-content">
                                <span>Elige para que quieres crear esta pieza.</span>
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
                        </section>

                        <section v-else-if="assistantStep === 'format'" class="space-y-6">
                            <div v-if="state.objective" class="alert border border-base-300 bg-base-100/80 text-base-content shadow-sm">
                                <span>Objetivo activo: <strong>{{ objectiveTitle }}</strong></span>
                            </div>

                            <div class="grid gap-5 lg:grid-cols-3">
                                <article class="card border border-base-300 bg-base-100/80">
                                    <div class="card-body p-5">
                                        <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Paso 1</p>
                                        <p class="mt-1 text-base font-semibold">Salida</p>
                                        <div class="mt-3 grid gap-3">
                                            <button
                                                type="button"
                                                class="card rounded-2xl border-2 p-3 text-left"
                                                :class="state.outputType === 'print' ? 'border-primary bg-primary/10' : 'border-base-300 bg-base-100 hover:border-primary/40'"
                                                @click="state.outputType = 'print'; state.size = null"
                                            >
                                                <div class="flex items-start justify-start gap-3">
                                                    <span class="font-medium">Impresion</span>
                                                    <SelectionIndicator :selected="state.outputType === 'print'" />
                                                </div>
                                            </button>
                                            <button
                                                type="button"
                                                class="card rounded-2xl border-2 p-3 text-left"
                                                :class="state.outputType === 'digital' ? 'border-primary bg-primary/10' : 'border-base-300 bg-base-100 hover:border-primary/40'"
                                                @click="state.outputType = 'digital'; state.size = null"
                                            >
                                                <div class="flex items-start justify-start gap-3">
                                                    <span class="font-medium">Digital</span>
                                                    <SelectionIndicator :selected="state.outputType === 'digital'" />
                                                </div>
                                            </button>
                                        </div>
                                    </div>
                                </article>

                                <article class="card border border-base-300 bg-base-100/80">
                                    <div class="card-body p-5">
                                        <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Paso 2</p>
                                        <p class="mt-1 text-base font-semibold">Formato</p>
                                        <div class="mt-3 grid gap-3">
                                            <button
                                                v-for="item in formatCards"
                                                :key="item.id"
                                                type="button"
                                                class="rounded-2xl border px-3 py-2 text-left"
                                                :disabled="!state.outputType"
                                                :class="state.format === item.id ? 'border-primary bg-primary/10' : 'border-base-300 bg-base-100 hover:border-primary/40 disabled:opacity-50'"
                                                @click="state.format = item.id; state.size = null"
                                            >
                                                <span class="font-medium">{{ item.title }}</span>
                                            </button>
                                        </div>
                                    </div>
                                </article>

                                <article class="card border border-base-300 bg-base-100/80">
                                    <div class="card-body p-5">
                                        <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Paso 3</p>
                                        <p class="mt-1 text-base font-semibold">Tamano</p>
                                        <div class="mt-3 flex flex-col items-start justify-start gap-3">
                                            <label class="w-full">
                                                <span class="mb-2 block text-xs font-medium uppercase tracking-[0.18em] text-base-content/60">Listado de tamanos</span>
                                                <select
                                                    v-model="selectedSizeId"
                                                    class="select select-bordered w-full rounded-2xl bg-base-100"
                                                    :disabled="!state.format"
                                                >
                                                    <option disabled value="">Selecciona un tamano recomendado</option>
                                                    <option v-for="size in sizes" :key="size.id" :value="size.id">
                                                        {{ size.label }} · {{ size.detail }}
                                                    </option>
                                                </select>
                                            </label>

                                            <div v-if="state.size" class="rounded-2xl border border-primary/30 bg-primary/10 px-3 py-2 text-left">
                                                <p class="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Seleccionado</p>
                                                <p class="mt-1 text-sm font-medium text-base-content">{{ state.size }}</p>
                                            </div>
                                        </div>
                                    </div>
                                </article>
                            </div>
                        </section>

                        <section v-else-if="assistantStep === 'content'" class="space-y-4">
                            <div class="alert border border-base-300 bg-base-100/80 text-base-content">
                                <span>Rellena los datos clave para completar las plantillas.</span>
                            </div>

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
                                    <textarea v-if="field.type === 'textarea'" v-model="state.content[field.key]" class="textarea textarea-bordered mt-2 min-h-[120px] w-full text-base" :placeholder="fieldPlaceholders[field.key] || 'Escribe aqui...'" @input="state.autosaveMessage = 'Guardado automatico · hace un instante'"></textarea>
                                    <input v-else v-model="state.content[field.key]" class="input input-bordered mt-2 w-full text-base" :placeholder="fieldPlaceholders[field.key] || 'Escribe aqui...'" @input="state.autosaveMessage = 'Guardado automatico · hace un instante'" />
                                </label>
                            </div>
                        </section>

                        <section v-else class="space-y-5">
                            <div class="flex flex-wrap gap-2">
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

                            <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                                <TemplateCard
                                    v-for="template in filteredTemplates"
                                    :key="template.id"
                                    :template="template"
                                    :content="state.content"
                                    :meta-line="metaLine"
                                    :contact-line="venueLine"
                                    :selected="state.selectedTemplateId === template.id"
                                    @click="state.selectedTemplateId = template.id"
                                />

                                <article
                                    class="flex min-h-[340px] cursor-pointer flex-col items-center justify-center rounded-[28px] border border-dashed border-base-300 bg-base-100/80 p-6 text-center transition hover:border-primary/60"
                                    :class="!state.selectedTemplateId ? 'ring-2 ring-primary/30' : ''"
                                    @click="state.selectedTemplateId = null"
                                >
                                    <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-base-100 text-3xl text-base-content/40 shadow-sm">+</div>
                                    <h4 class="mt-5 text-lg font-semibold text-base-content">Plantilla vacia</h4>
                                    <p class="mt-2 max-w-xs text-sm leading-6 text-base-content/70">
                                        Empieza desde cero, manteniendo objetivo, formato y datos.
                                    </p>
                                </article>
                            </div>
                        </section>
                    </div>

                    <footer class="flex items-center justify-between gap-3 border-t border-base-300 px-6 py-4">
                        <button type="button" class="btn btn-outline btn-sm rounded-full" :disabled="isFirstStep" @click="goPrevious">Anterior</button>

                        <div class="flex items-center gap-3">
                            <button
                                v-if="!isLastStep"
                                type="button"
                                class="btn btn-primary btn-sm rounded-full"
                                :disabled="!canGoNext"
                                @click="goNext"
                            >
                                Siguiente
                            </button>

                            <button
                                v-else
                                type="button"
                                class="btn btn-primary btn-sm rounded-full"
                                @click="finishAndOpenEditor"
                            >
                                Abrir editor
                            </button>
                        </div>
                    </footer>
                </section>
            </div>
        </div>
    </DesignerLayout>
</template>
