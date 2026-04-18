<script setup>
import { Icon } from '@iconify/vue';

defineProps({
  activeElementLabel: String,
  activePropertyPanel: String,
  currentAlignmentIcon: String,
  hasTextSelection: Boolean,
  selectedPropertyTabs: {
    type: Array,
    default: () => [],
  },
  selectedTextStyle: {
    type: Object,
    default: () => ({}),
  },
  toolbarPosition: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits([
  'cycle-alignment',
  'property-tab-click',
  'start-drag',
]);

const getTabLabelStyle = (tab, selectedTextStyle) => {
   if (tab.id === 'typography') {
    return {
      fontFamily: selectedTextStyle.fontFamily || 'inherit',
    };
  }
  return {}
};

const getLabel = (tab, selectedTextStyle) => {
  if (tab.id === 'typography') {
    return selectedTextStyle.fontFamily || 'Tipografía';
  }
  return tab.label || '';
};
</script>

<template>
  <div
    data-editor-keep-selection="true"
    class="pointer-events-none absolute z-50 flex justify-center"
    :style="{ left: '70px', right: '0', top: `${toolbarPosition.y}px` }"
  >
    <div :style="{ transform: `translateX(${toolbarPosition.x}px)` }" class="pointer-events-none">
      <div data-editor-keep-selection="true" class="pointer-events-auto card glass soft-shadow border border-base-300/70 bg-base-100/90">
        <div class="card-body p-1.5">
          <div class="flex flex-wrap items-center gap-3">
            <button type="button" class="order-first btn btn-ghost text-lg cursor-grab active:cursor-grabbing" @pointerdown="emit('start-drag', $event)">⋮⋮</button>
            <button
              v-for="tab in selectedPropertyTabs"
              :key="tab.id"
              type="button"
              class="btn border-0 py-1 px-2"
              :class="[activePropertyPanel === tab.id ? 'btn-primary' : 'btn-outline', tab.class]"
              :title="tab.title || tab.label"
              @click="emit('property-tab-click', tab)"
            >
              <span
                v-if="tab.label"
                class="text-base-100-accent"
                :class="tab.labelClass"
                :style="getTabLabelStyle(tab, selectedTextStyle)"
              >{{ getLabel(tab, selectedTextStyle) }}</span>
              <Icon v-if="tab.icon" :icon="tab.icon" class="text-2xl" />
            </button>
            <template v-if="hasTextSelection">
              <input v-model.number="selectedTextStyle.fontSize" type="number" min="8" max="200" step="1" class="input input-bordered join-item w-12 text-center order-first" />
              <button type="button" class="btn text-lg flex-col gap-0 px-2" :class="selectedTextStyle.color ? 'btn-primary' : 'btn-outline'" @click="$emit('property-tab-click', { id: 'color' })">
                A
                <div class="rounded-full w-6 h-2 border border-base-content/70"
                :style="{ backgroundColor: selectedTextStyle.color }"></div>
            </button>
              <button type="button" class="btn text-xl font-bold" :class="selectedTextStyle.fontWeight === 'bold' ? 'btn-primary' : 'btn-outline'" @click="selectedTextStyle.fontWeight = selectedTextStyle.fontWeight === 'bold' ? 'regular' : 'bold'">B</button>
              <button type="button" class="btn text-lg font-thin italic font-serif" :class="selectedTextStyle.italic ? 'btn-primary' : 'btn-outline'" @click="selectedTextStyle.italic = !selectedTextStyle.italic">I</button>
              <button type="button" class="btn text-lg w-12" :class="selectedTextStyle.uppercase ? 'btn-primary' : 'btn-outline'" @click="selectedTextStyle.uppercase = !selectedTextStyle.uppercase">Aa</button>
              <button type="button" class="btn text-lg btn-outline" @click="emit('cycle-alignment')">
                <Icon :icon="currentAlignmentIcon" class="scale-150" />
              </button>
            </template>
            <template v-else>
              <span class="rounded-full border border-base-300 bg-base-100 px-3 py-1 text-[11px] font-medium text-base-content/70">{{ activeElementLabel }}</span>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
