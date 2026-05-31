<template>
    <ClientOnly>
        <teleport to="body">
            <transition leave-active-class="duration-200">
                <div v-cloak v-show="show" class="component-modal fixed inset-0 overflow-y-auto px-4 py-6 sm:px-0 select-none" scroll-region
                    :class="[centered ? 'flex items-center' : '']"
                    :style="{ zIndex }">
                    <transition enter-active-class="ease-out" enter-from-class="opacity-0"
                        enter-to-class="opacity-100" leave-active-class="ease-in" leave-from-class="opacity-100"
                        leave-to-class="opacity-0">
                        <div v-show="show" class="fixed inset-0 transform transition-all -z-1" @click="close">
                            <div class="absolute inset-0 bg-gray-500! dark:bg-gray-900! opacity-75" />
                        </div>
                    </transition>

                    <transition enter-active-class="ease-out"
                        enter-from-class="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
                        enter-to-class="opacity-100 translate-y-0 sm:scale-100" leave-active-class="ease-in"
                        leave-from-class="opacity-100 translate-y-0 sm:scale-100"
                        leave-to-class="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95">
                        <div v-show="show"
                            class="mb-6 bg-base-100 dark:bg-gray-800 dark:border dark:border-gray-500 overflow-hidden shadow-xl transform transition-all sm:w-full sm:mx-auto"
                            :class="[maxWidthClass, modalClass]">
                            <slot v-if="show" />
                        </div>
                    </transition>
                </div>
            </transition>
        </teleport>
    </ClientOnly>
</template>


<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
    show: {
        type: [Boolean, Object],
        default: false,
    },
    maxWidth: {
        type: String,
        default: '3xl',
    },
    closeable: {
        type: Boolean,
        default: true,
    },
    centered: {
        type: Boolean,
        default: false
    },
    modalClass: {
        type: String,
        default: null
    },
    zIndex: {
        type: [String, Number],
        default: 10000
    }
});

const emit = defineEmits(['close']);
const modal_id = ref(null)

/**
 * Returns all focusable elements within a given container.
 * Covers links, buttons, inputs, textareas, selects, and elements
 * with an explicit non-negative tabindex.
 */
function getFocusableElements(container) {
    if (!container) return []
    const selectors = [
        'a[href]',
        'button:not([disabled])',
        'input:not([disabled])',
        'textarea:not([disabled])',
        'select:not([disabled])',
        '[tabindex]:not([tabindex="-1"])'
    ]
    return Array.from(container.querySelectorAll(selectors.join(',')))
}

/** Element that had focus before the modal opened â used to restore focus on close. */
const previousActiveElement = ref(null)

const close = () => {
    if (props.closeable) {
        emit('close');
    }
};

const closeOnEscape = (e) => {
    if (e.key === 'Escape' && props.show) {
        // we close only if this modal is in the top, the last in the modals current opened
        if (window.modals[window.modals.length - 1] === modal_id.value)
            close();
    }
};

/**
 * Traps Tab / Shift+Tab focus cycling inside the modal when open.
 */
function handleTabKeydown(e) {
    if (e.key !== 'Tab' || !props.show) return

    const modalEl = document.querySelector('.component-modal')
    if (!modalEl) return

    const focusableElements = getFocusableElements(modalEl)
    if (focusableElements.length === 0) return

    const first = focusableElements[0]
    const last = focusableElements[focusableElements.length - 1]

    if (e.shiftKey) {
        if (document.activeElement === first) {
            e.preventDefault()
            last.focus()
        }
    } else {
        if (document.activeElement === last) {
            e.preventDefault()
            first.focus()
        }
    }
}

// creamos un array de diálogos para saber cuales son los modales abiertos
watch(() => props.show, async (newValue) => {
    if(typeof window === 'undefined') return
    if (!window.modals)
        window.modals = []
    // get a very simple uuid
    if (!modal_id.value)
        modal_id.value = Math.random().toString(36).substr(2, 9);
    if (newValue) {
        window.modals.push(modal_id.value)

        // --- Focus trap: save previous focus and focus first element inside modal ---
        previousActiveElement.value = document.activeElement
        await nextTick()
        const modalEl = document.querySelector('.component-modal')
        if (modalEl) {
            const focusableElements = getFocusableElements(modalEl)
            if (focusableElements.length > 0) {
                focusableElements[0].focus()
            }
        }
    }
    else {
        window.modals.splice(window.modals.indexOf(modal_id.value), 1)

        // --- Focus trap: restore previously focused element ---
        if (previousActiveElement.value && typeof previousActiveElement.value.focus === 'function') {
            previousActiveElement.value.focus()
        }
        previousActiveElement.value = null
    }
});

onMounted(() => {
    document.addEventListener('keydown', closeOnEscape);
    document.addEventListener('keydown', handleTabKeydown);
});

/* watch(() => props.show, () => {
    if (props.show) {
        document.body.style.overflow = 'hidden';
    } else {
        document.body.style.overflow = null;
    }
}); */

onBeforeUnmount(() => {
    document.removeEventListener('keydown', closeOnEscape);
    document.removeEventListener('keydown', handleTabKeydown);
    //document.body.style.overflow = null;
});

const maxWidthClass = computed(() => {
    return {
        'sm': 'sm:max-w-sm',
        'md': 'sm:max-w-md',
        'lg': 'sm:max-w-lg',
        'xl': 'sm:max-w-xl',
        '2xl': 'sm:max-w-2xl',
        '3xl': 'sm:max-w-3xl',
        '4xl': 'sm:max-w-4xl',
    }[props.maxWidth];
});

</script>