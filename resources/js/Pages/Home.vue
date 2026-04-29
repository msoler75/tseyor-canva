<script setup>
import axios from 'axios';
import { router, usePage } from '@inertiajs/vue3';
import { computed, ref } from 'vue';
import DesignerAssistant from './../Components/designer/DesignerAssistant.vue';
import DesignerLayout from './../Layouts/DesignerLayout.vue';
import TimeAgo from '../Components/TimeAgo.vue';
import { flushDesignerStatePersistence, resetDesignerState, toggleDesignerDarkMode, useDesignerState } from '../composables/useDesignerState';
import { isHorizontalFormat } from '../data/designer';
import { applyFormatToDimensions, parseSizeDetail } from '../utils/editorShared';

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
    },
    adminTemplates: {
        type: Array,
        default: () => [],
    },
    sessionDesign: {
        type: Object,
        default: null,
    },
});

const continueSessionDesign = () => {
    router.visit('/designer/editor');
};

const page = usePage();
const state = useDesignerState();
const assistantOpen = ref(false);
const assistantStep = ref('objective');
const isCreatingDesign = ref(false);

const authUser = computed(() => page.props.auth?.user ?? null);
const recentProjects = computed(() => props.designs ?? []);

const communityDesigns = computed(() => props.communityDesigns ?? []);
const adminTemplates = computed(() => props.adminTemplates ?? []);

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

const newDesignUuid = () => {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
        return crypto.randomUUID();
    }

    return '10000000-1000-4000-8000-100000000000'.replace(/[018]/g, (char) => (
        Number(char) ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> Number(char) / 4
    ).toString(16));
};

const resolveInitialDesignName = (snapshot) => {
    const candidates = [
        snapshot.designTitle,
        snapshot.content?.title,
        snapshot.content?.subtitle,
    ];

    const name = candidates
        .map((candidate) => String(candidate ?? '').trim())
        .find((candidate) => candidate && candidate.toLowerCase() !== 'diseño sin título');

    return name || 'Diseño sin título';
};

const resolveTargetSurface = (snapshot) => {
    const parsed = parseSizeDetail(snapshot.size || '1080 × 1080 px');
    const adjusted = applyFormatToDimensions(parsed, snapshot.format);

    if (adjusted?.width > 0 && adjusted?.height > 0) {
        return {
            width: adjusted.width,
            height: adjusted.height,
        };
    }

    return isHorizontalFormat(snapshot.format)
        ? { width: 620, height: 368 }
        : (snapshot.format === 'square' ? { width: 500, height: 500 } : { width: 368, height: 620 });
};

const finishAndOpenEditor = async ({ selectedTemplate, designerState } = {}) => {
    // Permitir acceso al editor como invitado. El alert solo se mostrará en descarga/exportación o al crear un segundo diseño temporal.

    if (isCreatingDesign.value) return;

    isCreatingDesign.value = true;
    assistantOpen.value = false;

    const snapshot = JSON.parse(JSON.stringify(designerState ?? state));
    snapshot.currentDesignUuid = snapshot.currentDesignUuid || newDesignUuid();
    snapshot.designTitle = resolveInitialDesignName(snapshot);

    try {
        const response = selectedTemplate?.uuid
            ? await axios.post(`/designer/design-templates/${selectedTemplate.uuid}/generate`, {
                content: snapshot.content ?? {},
                objective: snapshot.objective,
                outputType: snapshot.outputType,
                format: snapshot.format,
                size: snapshot.size,
                designTitle: snapshot.designTitle,
                designSurface: resolveTargetSurface(snapshot),
            })
            : await axios.post('/designer/designs', {
                name: snapshot.designTitle,
                state: snapshot,
            });

        const designUuid = response.data?.design?.uuid;
        if (authUser.value && designUuid) {
            state.currentDesignUuid = designUuid;
            state.designTitle = response.data?.design?.name ?? snapshot.designTitle;
            router.visit(`/designer/designs/${designUuid}/edit`);
        } else {
            // Invitado: ir al editor temporal
            router.visit('/designer/editor');
        }
    } catch (error) {
        isCreatingDesign.value = false;
        assistantOpen.value = true;
        console.error('No se pudo crear el diseño inicial', error);
    }
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

const startRemoteLogin = async () => {
    router.visit('/auth/login');
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
    }
};

const openTemplateBase = async (template) => {
    if (!template?.base_design_uuid) {
        console.error('La plantilla no tiene diseño base asociado', template);
        return;
    }

    try {
        await flushDesignerStatePersistence();
    } catch (error) {
        console.error('Failed to flush state before opening template base design', error);
    }

    router.visit(`/designer/designs/${template.base_design_uuid}/edit`);
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
        description="Crea un diseño nuevo, abre tus proyectos guardados o reaprovecha ideas de la comunidad."
        :current-step="currentStep"
        :steps="steps"
        :show-steps="false"
        :dark-mode="state.darkMode"
        @toggle-dark="toggleDesignerDarkMode"
    >
        <section class="grid gap-6 lg:grid-cols-[1.1fr,0.9fr]">
            <!-- Diseño temporal de sesión para invitado -->
            <div v-if="!authUser && props.sessionDesign" class="card border-2 border-primary/70 bg-primary/5 shadow-lg mb-6">
                <div class="card-body p-4 flex flex-col">
                    <div class="flex items-center gap-4">
                        <div class="h-36 w-36 min-w-[9rem] rounded-xl opacity-90 flex items-center justify-center mb-2 bg-base-200/80 border border-base-300">
                            <img
                                v-if="props.sessionDesign.thumbnail_url || props.sessionDesign.thumbnailDataUrl"
                                :src="props.sessionDesign.thumbnail_url || props.sessionDesign.thumbnailDataUrl"
                                alt="Miniatura diseño temporal"
                                class="h-full w-full object-contain rounded-xl bg-transparent"
                            />
                            <span v-else class="text-xs font-medium text-base-content/65">Sin miniatura</span>
                        </div>
                        <div class="flex-1">
                            <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary mb-1">Diseño temporal</p>
                            <h2 class="text-xl font-semibold mb-1">Tienes un diseño sin guardar</h2>
                            <p class="text-base-content/80 text-sm mb-2">Puedes continuar editando tu diseño temporal. Si inicias sesión, podrás guardarlo en tu cuenta.</p>
                            <button type="button" class="btn btn-primary btn-lg rounded-full px-8 mt-2" @click="continueSessionDesign">
                                Continuar editando
                            </button>
                        </div>

                    </div>
                </div>
            </div>
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
                            title="Iniciar sesión"
                            @click="startRemoteLogin"
                        >
                            <IconifyIcon icon="ph:sign-in-bold" class="text-lg" />
                            <span>Iniciar sesión</span>
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

                    <div v-if="recentProjects.length" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6">
                        <div
                            v-for="project in recentProjects"
                            :key="project.uuid"
                            class="rounded-2xl border border-base-300 bg-linear-to-br from-base-100 to-base-200 p-4 text-left hover:border-primary/60 relative"
                        >
                            <button
                                type="button"
                                class="w-full text-left"
                                @click="openExistingDesign(project)"
                            >
                                <div class="h-36 rounded-xl opacity-90 flex items-center justify-center mb-2 bg-base-200/80">
                                    <img v-if="project.thumbnail_url" :src="project.thumbnail_url" :alt="project.name" class="h-full w-full object-contain rounded-xl bg-transparent" />
                                    <span v-else class="text-xs font-medium text-base-content/65">Sin miniatura</span>
                                </div>
                                <p class="font-semibold">{{ project.name }}</p>
                                <TimeAgo :date="project.updated_at" class="text-xs text-base-content/65" />
                            </button>
                            <div class="dropdown dropdown-end absolute top-3 right-3">
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
                        <div class="h-36 rounded-xl opacity-90 flex items-center justify-center bg-base-200/80 mb-2">
                            <img v-if="item.thumbnail_url" :src="item.thumbnail_url" :alt="item.name" class="h-full w-full object-contain rounded-xl bg-transparent" />
                            <span v-else class="text-xs font-medium text-base-content/65">Sin miniatura</span>
                        </div>
                        <p class="mt-3 font-semibold">{{ item.name }}</p>
                        <p class="text-xs text-base-content/65">{{ item.objective || 'Comunidad' }}</p>
                        <TimeAgo :date="item.updated_at" class="text-xs text-base-content/65" />

                        <p class="mt-2 text-xs font-medium text-primary">Clonar y editar</p>
                    </button>
                </div>
            </div>
        </section>

        <section v-if="authUser?.name === 'admin'" class="mt-6 card border border-base-300/70 bg-base-100/90 shadow-sm">
            <div class="card-body p-6">
                <div class="mb-4 flex items-center justify-between gap-3">
                    <div>
                        <h3 class="text-lg font-semibold">Últimas plantillas</h3>
                        <p class="text-sm text-base-content/65">Pulsa una plantilla para editar directamente su diseño base.</p>
                    </div>
                </div>

                <div v-if="adminTemplates.length" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6">
                    <button
                        v-for="template in adminTemplates.slice(0, 6)"
                        :key="template.uuid"
                        type="button"
                        class="rounded-2xl border border-base-300 bg-linear-to-br from-base-100 to-base-200 p-4 text-left hover:border-primary/60"
                        @click="openTemplateBase(template)"
                    >
                        <div class="h-36 rounded-xl opacity-90 flex items-center justify-center bg-base-200/80 mb-2">
                            <img v-if="template.thumbnail_url" :src="template.thumbnail_url" :alt="template.name" class="h-full w-full object-contain rounded-xl bg-transparent" />
                            <span v-else class="text-xs font-medium text-base-content/65">Sin miniatura</span>
                        </div>
                        <p class="font-semibold">{{ template.name }}</p>
                        <p v-if="template.description" class="mt-1 line-clamp-2 text-xs text-base-content/65">{{ template.description }}</p>
                    </button>
                </div>
                <div v-else class="rounded-2xl border border-dashed border-base-300 bg-base-100 px-4 py-5 text-sm text-base-content/65">
                    Todavía no hay plantillas publicadas.
                </div>
            </div>
        </section>

        <dialog v-if="assistantOpen" class="modal modal-open backdrop-blur-sm" style="z-index:90;">
            <div class="modal-box w-full max-w-lg lg:max-w-5xl p-0 overflow-visible bg-base-100 rounded-[30px] shadow-2xl border border-base-300">
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
