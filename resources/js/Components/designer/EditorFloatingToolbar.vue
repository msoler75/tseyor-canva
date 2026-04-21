<script setup>
import { computed } from 'vue';
import { Icon } from '@iconify/vue';

const props = defineProps({
  activeElementLabel: String,
  activePropertyPanel: String,
  currentAlignmentIcon: String,
  hasTextSelection: Boolean,
  mobileMode: {
    type: Boolean,
    default: false,
  },
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
  'close-bar'
]);

const toolbarShellStyle = computed(() => (
  props.mobileMode
    ? {}
    : { left: '70px', right: '0', top: `${props.toolbarPosition.y}px` }
));

const toolbarOffsetStyle = computed(() => (
  props.mobileMode
    ? {}
    : { transform: `translateX(${props.toolbarPosition.x}px)` }
));

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

const getLabel = (tab) => {
  if (tab.id === 'typography') {
    return 'Fuente';
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
  roundness: 'Redondez',
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
    class="pointer-events-none fixed inset-x-2 bottom-2 z-[70] flex justify-center md:absolute md:inset-x-auto md:bottom-auto md:z-50"
    :style="toolbarShellStyle"
  >
    <div :style="toolbarOffsetStyle" class="pointer-events-none max-w-full">
      <div data-editor-keep-selection="true" class="pointer-events-auto card glass soft-shadow border border-base-300/70 bg-base-100/95">
        <div class="card-body p-1.5">
          <div class="flex max-w-[calc(100vw-1rem)] flex-nowrap items-center gap-2 overflow-hidden overflow-x-auto md:flex-wrap md:overflow-visible min-w-[calc(100vw-1rem)] md:min-w-auto pr-20 md:pr-1">
            <button
              type="button"
              class="tooltip tooltip-bottom order-first hidden btn btn-ghost cursor-grab text-lg active:cursor-grabbing md:inline-flex"
              data-tip="Mover barra"
              @pointerdown="emit('start-drag', $event)"
            >⋮⋮</button>

            <button class="md:hidden absolute right-2 z-10 btn btn-neutral rounded-full w-14 h-14 border border-gray-500 shadow-sm"
            @click="emit('close-bar', $event)">
                <Icon icon="ph:check-bold" class="text-2xl" />
            </button>

            <button
              v-for="tab in selectedPropertyTabs"
              :key="tab.id"
              type="button"
              class="md:tooltip tooltip-bottom btn h-16 min-w-20 flex-col gap-1 px-2 py-1 md:h-auto md:min-w-0 md:flex-row"
              :class="[getTabButtonClasses(tab, activePropertyPanel),
                tab.label?'':'w-20 md:w-10'
              ]"
              :data-tip="getTabTooltip(tab)"
              @click="emit('property-tab-click', tab)"
            >
              <span
                v-if="tab.label"
                class="text-base-100-accent text-[11px] leading-none md:text-sm"
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
                  class="input input-bordered join-item w-16 border-gray-500 text-center [--input-color:var(--color-gray-500)]"
                />
              </div>

              <button
                type="button"
                class="tooltip tooltip-bottom btn h-16 min-w-20 flex-col gap-0 border-0 px-2 text-lg md:h-auto md:min-w-0"
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
                class="tooltip tooltip-bottom hidden btn border-0 text-xl font-bold md:inline-flex"
                data-tip="Negrita"
                :class="selectedTextStyle.fontWeight === 'bold' ? 'btn-accent' : 'btn-outline'"
                @click="selectedTextStyle.fontWeight = selectedTextStyle.fontWeight === 'bold' ? 'regular' : 'bold'"
              >B</button>

              <button
                type="button"
                class="tooltip tooltip-bottom hidden btn border-0 text-lg font-thin italic font-serif md:inline-flex"
                data-tip="Cursiva"
                :class="selectedTextStyle.italic ? 'btn-accent' : 'btn-outline'"
                @click="selectedTextStyle.italic = !selectedTextStyle.italic"
              >I</button>

              <button
                type="button"
                class="tooltip tooltip-bottom hidden btn w-10 border-0 text-lg md:inline-flex"
                data-tip="Mayúsculas"
                :class="selectedTextStyle.uppercase ? 'btn-accent' : 'btn-outline'"
                @click="selectedTextStyle.uppercase = !selectedTextStyle.uppercase"
              >Aa</button>

              <button
                type="button"
                class="tooltip tooltip-bottom hidden btn w-10 border-0 p-0 text-lg md:inline-flex"
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
