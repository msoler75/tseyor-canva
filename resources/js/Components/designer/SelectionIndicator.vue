<script setup>
defineProps({
    selected: Boolean,
    idleText: {
        type: String,
        default: 'Elegir',
    },
    selectedText: {
        type: String,
        default: '✓',
    },
    idleClass: {
        type: String,
        default: 'badge-outline',
    },
    selectedClass: {
        type: String,
        default: 'badge-success',
    },
});
</script>

<template>
    <span
        class="badge inline-flex w-16 justify-center px-3 py-3 text-center text-[11px] font-semibold"
        :class="selected ? selectedClass : idleClass"
    >
        {{ selected ? selectedText : idleText }}
    </span>
</template>
