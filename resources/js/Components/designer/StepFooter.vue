<script setup>
import { Link } from '@inertiajs/vue3';

defineProps({
    previousUrl: {
        type: String,
        default: null,
    },
    nextUrl: {
        type: String,
        default: null,
    },
    nextLabel: {
        type: String,
        default: 'Siguiente',
    },
    hint: {
        type: String,
        default: '',
    },
    nextDisabled: {
        type: Boolean,
        default: false,
    },
});
</script>

<template>
    <div class="mt-6 flex flex-wrap items-center justify-between gap-3">
        <slot name="left">
            <Link
                v-if="previousUrl"
                :href="previousUrl"
                class="btn btn-outline btn-sm rounded-full"
            >
                Anterior
            </Link>
            <span v-else></span>
        </slot>

        <div class="flex flex-wrap items-center gap-3">
            <span
                v-if="hint"
                class="badge badge-success badge-outline px-4 py-3 text-sm font-semibold"
            >
                {{ hint }}
            </span>
            <slot name="right">
                <button
                    v-if="nextUrl && nextDisabled"
                    type="button"
                    disabled
                    class="btn btn-primary btn-sm rounded-full"
                >
                    {{ nextLabel }}
                </button>
                <Link
                    v-else-if="nextUrl"
                    :href="nextUrl"
                    class="btn btn-primary btn-sm rounded-full"
                >
                    {{ nextLabel }}
                </Link>
            </slot>
        </div>
    </div>
</template>
