<script setup>
defineProps({
    title: String,
    description: String,
    recommendation: {
        type: String,
        default: '',
    },
    tag: {
        type: String,
        default: '',
    },
    selected: Boolean,
});
</script>

<template>
    <button
        type="button"
        class="card relative overflow-hidden rounded-[28px] border text-left transition"
        :class="selected
            ? 'border-4 border-accent bg-primary text-primary-content shadow-xl ring-2 ring-accent/40'
            : 'border border-base-300 bg-base-100 hover:border-primary/40 hover:shadow-sm'"
    >
        <div class="card-body gap-4 p-5">
        <div class="flex items-start justify-between gap-4">
            <div class="min-w-0">
                <div class="flex items-center gap-3">
                    <span
                        class="flex h-8 w-8 items-center justify-center rounded-full text-sm font-black"
                        :class="selected ? 'bg-base-100 text-primary' : 'bg-base-200 text-base-content/55'"
                    >
                        {{ selected ? '✓' : '○' }}
                    </span>
                    <p class="text-lg font-semibold" :class="selected ? 'text-primary-content' : 'text-base-content'">{{ title }}</p>
                </div>
                <p class="mt-3 text-sm leading-6" :class="selected ? 'text-primary-content/85' : 'text-base-content/75'">{{ description }}</p>
                <div
                    v-if="recommendation"
                    class="mt-4 rounded-[20px] px-4 py-3 text-sm shadow-sm"
                    :class="selected ? 'bg-primary-content/12 text-primary-content' : 'bg-base-200 text-base-content/80'"
                >
                    {{ recommendation }}
                </div>
            </div>
            <span
                v-if="tag"
                class="badge badge-sm px-3 py-3 text-xs font-semibold"
                :class="selected
                    ? 'badge-accent text-accent-content'
                    : 'badge-ghost'"
            >
                {{ tag }}
            </span>
        </div>
        </div>
    </button>
</template>
