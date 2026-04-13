<script setup>
const props = defineProps({
  label: {
    type: String,
    default: 'Color custom',
  },
  value: {
    type: String,
    default: '',
  },
  normalizedValue: {
    type: String,
    default: '#000000',
  },
  placeholder: {
    type: String,
    default: '#000000',
  },
});

const emit = defineEmits(['update']);
</script>

<template>
  <div class="grid gap-3 sm:grid-cols-[auto_1fr] sm:items-center">
    <label class="text-xs font-semibold uppercase tracking-[0.2em] text-base-content/60">{{ label }}</label>
    <div class="flex items-center gap-2">
      <input
        type="color"
        class="h-10 w-12 cursor-pointer rounded-xl border border-base-300 bg-base-100 p-1"
        :value="normalizedValue"
        @input="emit('update', $event.target.value)"
      />
      <input
        :value="value"
        type="text"
        :placeholder="placeholder"
        class="input input-bordered input-sm flex-1"
        @input="emit('update', $event.target.value)"
      />
    </div>
  </div>
</template>
