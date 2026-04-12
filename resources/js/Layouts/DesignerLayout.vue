<script setup>
import { Head, Link } from '@inertiajs/vue3';
import { onMounted, watch } from 'vue';

const props = defineProps({
    title: String,
    eyebrow: String,
    description: String,
    hint: {
        type: String,
        default: '',
    },
    currentStep: String,
    steps: Array,
    darkMode: Boolean,
    showSteps: {
        type: Boolean,
        default: true,
    },
    showHeader: {
        type: Boolean,
        default: true,
    },
    fullHeight: {
        type: Boolean,
        default: false,
    },
});

const emit = defineEmits(['toggle-dark']);

const syncTheme = () => {
    document.documentElement.classList.toggle('dark', props.darkMode);
    document.documentElement.setAttribute('data-theme', props.darkMode ? 'dark' : 'light');
};

onMounted(syncTheme);
watch(() => props.darkMode, syncTheme);
</script>

<template>
    <Head :title="title" />

    <div :class="props.fullHeight ? 'h-screen overflow-hidden bg-base-100 text-base-content' : 'min-h-screen bg-base-100 text-base-content'">
        <div :class="props.fullHeight ? 'mx-auto h-full w-full' : 'mx-auto w-full px-4 py-6 sm:px-6 lg:px-8'">
            <header v-if="showHeader" class="card glass soft-shadow sticky top-4 z-30 mb-8 border border-base-300/60 bg-base-100/85 text-base-content">
                <div class="card-body gap-4 px-5 py-4">
                <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                        <p class="text-xs font-semibold uppercase tracking-[0.24em] text-primary">TSEYOR Canva</p>
                        <h1 class="mt-2 text-2xl font-semibold text-base-content sm:text-3xl">
                            {{ title }}
                        </h1>
                        <p class="mt-2 max-w-3xl text-sm text-base-content/75 sm:text-base">
                            {{ description }}
                        </p>
                        <p v-if="hint" class="mt-2 text-sm font-medium text-success">
                            {{ hint }}
                        </p>
                    </div>

                    <button
                        type="button"
                        @click="emit('toggle-dark')"
                        class="btn btn-sm btn-outline rounded-full"
                    >
                        {{ darkMode ? '☀️ Modo claro' : '🌙 Modo oscuro' }}
                    </button>
                </div>

                <nav v-if="showSteps && steps?.length" class="mt-5 flex flex-wrap gap-2">
                    <Link
                        v-for="step in steps"
                        :key="step.id"
                        :href="step.url"
                        class="btn btn-sm rounded-full border-none text-sm font-semibold transition"
                        :class="step.id === currentStep
                            ? 'btn-primary text-primary-content'
                            : 'btn-ghost bg-white/80 text-slate-700 shadow-sm dark:bg-slate-900/80 dark:text-slate-100'"
                    >
                        {{ step.label }}
                    </Link>
                </nav>
                </div>
            </header>

            <div :class="props.fullHeight ? (showHeader ? 'h-[calc(100%-9rem)]' : 'h-full') : ''">
                <slot />
            </div>
        </div>
    </div>
</template>
