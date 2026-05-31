<template>
    <ClientOnly>
        <teleport to="body">
            <transition leave-active-class="duration-200">
                <div
                    v-cloak
                    v-show="show"
                    class="fixed inset-0 overflow-y-auto px-4 py-6 sm:px-0 select-none"
                    scroll-region
                    style="z-index: 10000"
                >
                    <!-- Backdrop -->
                    <transition
                        enter-active-class="ease-out"
                        enter-from-class="opacity-0"
                        enter-to-class="opacity-100"
                        leave-active-class="ease-in"
                        leave-from-class="opacity-100"
                        leave-to-class="opacity-0"
                    >
                        <div
                            v-show="show"
                            class="fixed inset-0 transform transition-all -z-1"
                            @click="close"
                        >
                            <div class="absolute inset-0 bg-gray-500! dark:bg-gray-900! opacity-75" />
                        </div>
                    </transition>

                    <!-- Modal panel -->
                    <transition
                        enter-active-class="ease-out"
                        enter-from-class="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
                        enter-to-class="opacity-100 translate-y-0 sm:scale-100"
                        leave-active-class="ease-in"
                        leave-from-class="opacity-100 translate-y-0 sm:scale-100"
                        leave-to-class="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
                    >
                        <div
                            v-show="show"
                            class="mb-6 bg-base-100 dark:bg-gray-800 dark:border dark:border-gray-500 overflow-hidden shadow-xl transform transition-all sm:w-full sm:mx-auto sm:max-w-2xl rounded-2xl"
                        >
                            <div class="p-6">
                                <!-- Header -->
                                <div class="flex items-center justify-between mb-6">
                                    <div class="flex items-center gap-2">
                                        <Icon icon="ph:keyboard-bold" class="text-xl text-base-content" />
                                        <h2 class="text-lg font-semibold text-base-content">Atajos de teclado</h2>
                                    </div>
                                    <button
                                        type="button"
                                        class="btn btn-ghost btn-circle btn-sm"
                                        title="Cerrar"
                                        aria-label="Cerrar"
                                        @click="close"
                                    >
                                        <Icon icon="ph:x-bold" class="text-lg" />
                                    </button>
                                </div>

                                <!-- Shortcuts grid -->
                                <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1">
                                    <div
                                        v-for="shortcut in shortcuts"
                                        :key="shortcut.label"
                                        class="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-base-200 transition-colors"
                                    >
                                        <span class="text-sm text-base-content">{{ shortcut.label }}</span>
                                        <div class="flex items-center gap-1 ml-4 shrink-0">
                                            <template v-for="(keyPart, i) in shortcut.combo" :key="i">
                                                <kbd class="kbd kbd-sm">{{ keyPart }}</kbd>
                                                <span
                                                    v-if="i < shortcut.combo.length - 1"
                                                    class="text-xs text-base-content/40"
                                                >+</span>
                                            </template>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </transition>
                </div>
            </transition>
        </teleport>
    </ClientOnly>
</template>

<script setup>
import { Icon } from '@iconify/vue';
import { ref, watch, onMounted, onBeforeUnmount } from 'vue';

const props = defineProps({
    show: {
        type: Boolean,
        default: false,
    },
});

const emit = defineEmits(['close']);

const modalId = ref(null);

const shortcuts = [
    { combo: ['Ctrl/Cmd', 'Z'], label: 'Deshacer' },
    { combo: ['Ctrl/Cmd', 'Y'], label: 'Rehacer' },
    { combo: ['Ctrl/Cmd', 'C'], label: 'Copiar elemento' },
    { combo: ['Ctrl/Cmd', 'V'], label: 'Pegar elemento' },
    { combo: ['Ctrl/Cmd', 'D'], label: 'Duplicar elemento' },
    { combo: ['Delete / Backspace'], label: 'Eliminar elemento' },
    { combo: ['Ctrl/Cmd', 'A'], label: 'Seleccionar todo (en editor de texto)' },
    { combo: ['Escape'], label: 'Cerrar modal / Desseleccionar' },
    { combo: ['Ctrl/Cmd', 'S'], label: 'Guardar diseño' },
    { combo: ['+ / -'], label: 'Acercar / Alejar zoom' },
    { combo: ['Flechas'], label: 'Mover elemento seleccionado' },
    { combo: ['Shift', 'Flechas'], label: 'Mover elemento (10px)' },
];

const close = () => {
    emit('close');
};

const closeOnEscape = (e) => {
    if (e.key === 'Escape' && props.show) {
        if (window.modals && window.modals[window.modals.length - 1] === modalId.value) {
            close();
        }
    }
};

watch(() => props.show, (newValue) => {
    if (typeof window === 'undefined') return;
    if (!window.modals) window.modals = [];
    if (!modalId.value) modalId.value = Math.random().toString(36).substr(2, 9);
    if (newValue) {
        window.modals.push(modalId.value);
    } else {
        const idx = window.modals.indexOf(modalId.value);
        if (idx !== -1) window.modals.splice(idx, 1);
    }
});

onMounted(() => document.addEventListener('keydown', closeOnEscape));

onBeforeUnmount(() => {
    document.removeEventListener('keydown', closeOnEscape);
    const idx = window.modals?.indexOf(modalId.value);
    if (idx !== -1) window.modals.splice(idx, 1);
});
</script>
