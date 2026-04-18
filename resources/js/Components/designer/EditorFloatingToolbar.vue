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
  if (tab.id === 'color' && tab.label === 'A' && selectedTextStyle?.color) {
    return { color: selectedTextStyle.color };
  }

  if (tab.id === 'typography') {
    return {
      fontFamily: selectedTextStyle.fontFamily || 'inherit',
    };
  }

  return {};
};

const getLabel = (tab, selectedTextStyle) => {
  if (tab.id === 'typography') {
    return selectedTextStyle.fontFamily || 'Tipografía';
  }
  return tab.label || '';
};

const tabTooltipLabels = {
  arrange: 'Posición',
  border: 'Borde',
  color: 'Color',
  crop: 'Recortar',
  detach: 'Separar imagen del fondo',
  effects: 'Efectos',
  opacity: 'Opacidad',
  rotate: 'Girar',
  spacing: 'Interlineado y espaciado',
  'clear-background': 'Borrar fondo',
  'set-as-background': 'Fijar como fondo',
  typography: 'Fuente',
};

const getTabTooltip = (tab) => tab.title || tabTooltipLabels[tab.id] || tab.label || tab.id;

const getTabButtonClasses = (tab, activePropertyPanel) => [
  activePropertyPanel === tab.id ? 'btn-warning' : 'btn-outline',
  tab.id === 'typography' ? '' : 'border-0',
  tab.class,
];
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
          <div class="flex flex-wrap items-center gap-2">
            <button
              type="button"
              class="tooltip tooltip-bottom order-first btn btn-ghost text-lg cursor-grab active:cursor-grabbing"
              data-tip="Mover barra"
              @pointerdown="emit('start-drag', $event)"
            >⋮⋮</button>

            <button
              v-for="tab in selectedPropertyTabs"
              :key="tab.id"
              type="button"
              class="tooltip tooltip-bottom btn py-1 px-2"
              :class="[getTabButtonClasses(tab, activePropertyPanel),
                tab.label?'':'w-10'
              ]"
              :data-tip="getTabTooltip(tab)"
              @click="emit('property-tab-click', tab)"
            >
              <span
                v-if="tab.label"
                class="text-base-100-accent"
                :class="tab.labelClass"
                :style="getTabLabelStyle(tab, selectedTextStyle)"
              >{{ getLabel(tab, selectedTextStyle) }}</span>
              <Icon v-if="tab.icon" :icon="tab.icon" class="text-2xl" :class="tab.iconClass"/>
            </button>

            <template v-if="hasTextSelection">
              <div class="tooltip tooltip-bottom order-first" data-tip="Tamaño de fuente">
                <input
                  v-model.number="selectedTextStyle.fontSize"
                  type="number"
                  min="8"
                  max="200"
                  step="1"
                  class="input input-bordered join-item w-12 border-gray-500 [--input-color:var(--color-gray-500)] text-center"
                />
              </div>

              <button
                type="button"
                class="tooltip tooltip-bottom btn border-0 text-lg flex-col gap-0 px-2"
                data-tip="Color"
                :class="[getTabButtonClasses({ id: 'color'}, activePropertyPanel)]"
                @click="$emit('property-tab-click', { id: 'color' })"
              >
                A
                <div
                  class="rounded-full w-6 h-2 border border-base-content/70"
                  :style="{ backgroundColor: selectedTextStyle.color }"
                ></div>
              </button>

              <button
                type="button"
                class="tooltip tooltip-bottom btn border-0 text-xl font-bold"
                data-tip="Negrita"
                :class="selectedTextStyle.fontWeight === 'bold' ? 'btn-accent' : 'btn-outline'"
                @click="selectedTextStyle.fontWeight = selectedTextStyle.fontWeight === 'bold' ? 'regular' : 'bold'"
              >B</button>

              <button
                type="button"
                class="tooltip tooltip-bottom btn border-0 text-lg font-thin italic font-serif"
                data-tip="Cursiva"
                :class="selectedTextStyle.italic ? 'btn-accent' : 'btn-outline'"
                @click="selectedTextStyle.italic = !selectedTextStyle.italic"
              >I</button>

              <button
                type="button"
                class="tooltip tooltip-bottom btn border-0 text-lg w-10"
                data-tip="Mayúsculas"
                :class="selectedTextStyle.uppercase ? 'btn-accent' : 'btn-outline'"
                @click="selectedTextStyle.uppercase = !selectedTextStyle.uppercase"
              >Aa</button>

              <button
                type="button"
                class="tooltip tooltip-bottom btn border-0 text-lg btn-outline w-10 p-0"
                data-tip="Alineación"
                @click="emit('cycle-alignment')"
              >
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
