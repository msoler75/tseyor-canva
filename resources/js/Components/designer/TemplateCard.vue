<script setup>
defineProps({
    template: Object,
    content: Object,
    metaLine: String,
    contactLine: String,
    selected: Boolean,
});
</script>

<template>
    <article
        class="cursor-pointer overflow-hidden rounded-[28px] outline transition shadow-lg"
        :class="selected
            ? 'outline-4 outline-primary ring-4'
            : 'outline-base-300 bg-base-100 hover:outline-primary/40'"
    >
        <div v-if="template.thumbnail_url" class="relative min-h-64 bg-base-200">
            <img :src="template.thumbnail_url" :alt="template.name" class="h-64 w-full object-cover" />
        </div>
        <div v-else class="bg-gradient-to-br p-5" :class="[template.theme || 'from-slate-100 via-white to-slate-200', template.text || 'text-slate-950']">
            <h4 class="mt-4 text-3xl font-black leading-none">{{ content.title }}</h4>
            <p class="mt-3 text-sm leading-6 opacity-90">{{ content.subtitle }}</p>
            <div class="mt-8 rounded-[20px]" :class="template.light ? 'bg-white/70 p-3 text-slate-900' : 'bg-white/10 p-3 backdrop-blur-sm'">
                <p class="text-sm font-semibold">{{ metaLine }}</p>
                <p class="mt-1 text-sm opacity-80">{{ contactLine }}</p>
            </div>
        </div>
        <div class="space-y-3 bg-base-100 px-4 py-4 text-sm text-base-content">
            <div class="flex flex-wrap items-center justify-between gap-3">
                <div class="flex items-center gap-3">
                    <span
                        class="flex h-9 w-9 items-center justify-center rounded-full border-2 text-lg font-black"
                        :class="selected ? 'border-accent bg-accent text-accent-content' : 'border-base-300 bg-base-200 text-base-content/45'"
                    >
                        {{ selected ? '✓' : '○' }}
                    </span>
                    <div>
                        <p class="font-semibold text-base-content">{{ template.name }}</p>
                        <p class="mt-1 text-xs uppercase tracking-[0.2em] text-base-content/55">
                            {{ template.objective_ids?.length ? 'Plantilla publicada' : 'Tipo y categoría fuera del diseño' }}
                        </p>
                    </div>
                </div>
                <div class="flex flex-wrap items-center gap-2">
                    <span class="rounded-full px-3 py-1 text-[11px] font-semibold" :class="template.accent || 'bg-primary/10 text-primary'">
                        {{ template.label || template.category_ids?.[0] || 'Plantilla' }}
                    </span>
                </div>
            </div>
        </div>
    </article>
</template>
