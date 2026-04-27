<script setup>
import axios from 'axios';
import { ref, computed, onMounted, watch } from 'vue';
import { usePage } from '@inertiajs/vue3';
import ChoiceCard from './ChoiceCard.vue';
import SelectionIndicator from './SelectionIndicator.vue';
import TemplateCard from './TemplateCard.vue';
import StepFooter from './StepFooter.vue';
import {
  filterLabels,
  formatCards,
  objectiveOptions,
  objectiveRecommendations,
  outputTypeOptions,
  resolveObjectiveSizeOptions,
  templateFilters,
} from '../../data/designer';
import { useDesignerState, resetDesignerState, flushDesignerStatePersistence } from '../../composables/useDesignerState';

const props = defineProps({
  step: { type: String, default: 'objective' },
  showFooter: { type: Boolean, default: true },
  showClose: { type: Boolean, default: true },
  showStepNavigation: { type: Boolean, default: true },
  hideTemplatesStep: { type: Boolean, default: false },
});

const emit = defineEmits(['close', 'finish']);
const state = useDesignerState();
const page = usePage();
const remoteTemplates = ref([]);
const customWidth = ref('');
const customHeight = ref('');
const allAssistantSteps = [
  { id: 'objective', label: 'Objetivo' },
  { id: 'format', label: 'Formato' },
  { id: 'content', label: 'Datos' },
  { id: 'templates', label: 'Plantillas' },
];
const assistantSteps = computed(() => props.hideTemplatesStep
  ? allAssistantSteps.filter((step) => step.id !== 'templates')
  : allAssistantSteps);
const assistantStep = ref(props.step);
const assistantIndex = computed(() => assistantSteps.value.findIndex((step) => step.id === assistantStep.value));
const isFirstStep = computed(() => assistantIndex.value <= 0);
const isLastStep = computed(() => assistantIndex.value === assistantSteps.value.length - 1);

const objectiveTitle = computed(() => objectiveOptions.find((item) => item.id === state.objective)?.title ?? 'Sin objetivo');
const sizes = computed(() => resolveObjectiveSizeOptions(state.objective, state.outputType, state.format));
const groupedSizes = computed(() => {
  if (!state.outputType) return [];

  return [
    {
      id: 'print',
      label: 'Impresión',
      options: sizes.value.filter((size) => size.outputType === 'print'),
    },
    {
      id: 'digital',
      label: 'Redes sociales/Web',
      options: sizes.value.filter((size) => size.outputType === 'digital'),
    },
  ].filter((group) => group.options.length);
});
const fields = computed(() => (objectiveRecommendations[state.objective] ?? objectiveRecommendations.generic).fields);
const fieldPlaceholders = {
  title: 'Ej. Festival de Primavera',
  subtitle: 'Ej. Música, talleres y actividades para toda la familia',
  date: 'Ej. 25 abril 2026',
  time: 'Ej. 18:00',
  location: 'Ej. Plaza Mayor',
  platform: 'Ej. https://zoom.us/j/123456789',
  teacher: 'Ej. María López',
  price: 'Ej. Entrada gratuita',
  contact: 'Ej. 600 123 123 · hola@tudominio.com',
  extra: 'Ej. Aforo limitado · Reserva previa · Traer material',
};
const availableTemplates = computed(() => remoteTemplates.value);
const availableTemplateFilters = computed(() => {
  const categories = new Set(templateFilters);
  availableTemplates.value.forEach((template) => {
    (template.category_ids ?? (template.category ? [template.category] : [])).forEach((category) => categories.add(category));
  });
  return Array.from(categories);
});
const filteredTemplates = computed(() => {
  if (!availableTemplates.value.length) return [];
  return availableTemplates.value.filter((item) => {
    const categoryIds = item.category_ids ?? (item.category ? [item.category] : []);
    const objectiveIds = item.objective_ids ?? [];
    const matchesCategory = !state.templateCategory
      || state.templateCategory === 'all'
      || categoryIds.includes(state.templateCategory);
    const matchesObjective = !objectiveIds.length
      || objectiveIds.includes('generic')
      || !state.objective
      || objectiveIds.includes(state.objective);

    return matchesCategory && matchesObjective;
  });
});
const metaLine = computed(() => [state.content.date, state.content.time].filter(Boolean).join(' · '));
const venueLine = computed(() => {
  if (state.objective === 'event_virtual') {
    return state.content.platform?.trim() || state.content.contact?.trim() || '';
  }
  return state.content.location?.trim() || state.content.contact?.trim() || '';
});
const canGoNext = computed(() => {
  if (assistantStep.value === 'objective') return Boolean(state.objective);
  if (assistantStep.value === 'format') return Boolean(state.outputType && state.format && state.size);
  return true;
});
const isAssistantComplete = computed(() => Boolean(
  state.objective
  && state.outputType
  && state.format
  && state.size
));
const canApplyCurrentStep = computed(() => {
  if (assistantStep.value === 'objective') return Boolean(state.objective);
  if (assistantStep.value === 'format') return Boolean(state.outputType && state.format && state.size);
  return true;
});
const usingCustomFormat = computed(() => state.format === 'other');

function goNext() {
  if (!canGoNext.value || isLastStep.value) return;
  assistantStep.value = assistantSteps.value[assistantIndex.value + 1].id;
  scrollToHeader()
}
function goPrevious() {
  if (isFirstStep.value) return;
  assistantStep.value = assistantSteps.value[assistantIndex.value - 1].id;
  scrollToHeader()
}

function scrollToHeader() {
    setTimeout(() => {
        const el = document.getElementById(`header-${assistantStep.value}`);
        if (el) {
      // nos situamos al comienzo de ese elemento, con un scroll suave
      scrollToElement(el);
        }
    }, 100);
}

function getScrollParent(node) {
  while (node && node !== document.body) {
    const style = getComputedStyle(node);
    if (/(auto|scroll)/.test(style.overflowY || '')) return node;
    node = node.parentElement;
  }
  return document.scrollingElement || document.documentElement;
}

function scrollToElement(el) {
  try {
    const scroller = getScrollParent(el.parentElement);
    if (!scroller) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }

    const elRect = el.getBoundingClientRect();
    const scrollerRect = scroller.getBoundingClientRect();
    const scrollerStyle = getComputedStyle(scroller);
    const paddingTop = parseFloat(scrollerStyle.paddingTop) || 0;

    const top = elRect.top - scrollerRect.top + scroller.scrollTop - paddingTop;
    scroller.scrollTo({ top, behavior: 'smooth' });
  } catch (e) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

function selectSizeOption(option) {
  state.size = option.label;
  if (state.format === 'other' && option.formatHint) {
    state.format = option.formatHint;
  }
}

function syncCustomSizeState() {
  const width = Number(customWidth.value);
  const height = Number(customHeight.value);

  if (Number.isFinite(width) && Number.isFinite(height) && width > 0 && height > 0) {
    const normalizedWidth = Math.round(width);
    const normalizedHeight = Math.round(height);
    state.size = `${normalizedWidth} × ${normalizedHeight} px`;
    state.designSurface = {
      width: normalizedWidth,
      height: normalizedHeight,
    };
    return;
  }

  state.size = null;
  state.designSurface = null;
}
function finishAndOpenEditor() {
  const selectedTemplate = availableTemplates.value.find((template) => template.id === state.selectedTemplateId) ?? null;
  emit('finish', { selectedTemplate});
}

function selectTemplate(template) {
  state.selectedTemplateId = template.id;

  // Emitir finish siempre; la página padre decide si debe generar/aplicar
  const selectedTemplate = availableTemplates.value.find((t) => t.id === template.id) ?? null;
  emit('finish', { selectedTemplate });
}
watch(() => props.step, (val) => {
  if (val && assistantSteps.value.some(s => s.id === val)) assistantStep.value = val;
});
watch(assistantSteps, (steps) => {
  if (!steps.some((step) => step.id === assistantStep.value)) {
    assistantStep.value = steps[0]?.id ?? 'objective';
  }
}, { immediate: true });

watch([customWidth, customHeight], () => {
  if (usingCustomFormat.value) {
    syncCustomSizeState();
  }
});


function chooseOutput(o) {
    state.outputType = o;
    state.size = null
    if (!usingCustomFormat.value) {
      state.designSurface = null;
    }
    // scroll para que el elemento #step-2 se vea (mover scroll)
    setTimeout(() => {
      const el = document.getElementById('step-2');
      if (el) {
        scrollToElement(el);
      }
    }, 100);
}

function chooseFormat(f) {
    state.format = f;
    state.size = null
    if (f === 'other') {
      customWidth.value = String(Number(state.designSurface?.width ?? 0) || 1080);
      customHeight.value = String(Number(state.designSurface?.height ?? 0) || 1080);
      syncCustomSizeState();
    } else {
      state.designSurface = null;
    }
    // scroll para que el elemento #step-3 se vea (mover scroll)
    setTimeout(() => {
      const el = document.getElementById('step-3');
      if (el) {
        scrollToElement(el);
      }
    }, 100);
}


onMounted(async () => {
  try {
    const response = await axios.get('/designer/design-templates');
    remoteTemplates.value = response.data?.templates ?? [];
  } catch (error) {
    console.error('No se pudieron cargar las plantillas publicadas', error);
  }
});

// Permite exponer el step actual para el padre
defineExpose({ assistantStep });
</script>

<template>
  <section class="flex flex-col max-h-[90vh]">
    <header class="border-b border-base-300 px-6 py-5">
      <div class="flex items-start justify-between gap-4">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Asistente de creación</p>
          <h3 class="mt-1 text-2xl font-semibold">Configura tu diseño</h3>
          <p class="mt-1 text-sm text-base-content/70">Objetivo, formato, datos y plantilla antes de entrar al editor.</p>
        </div>
        <button v-if="showClose" type="button" class="btn btn-ghost btn-sm rounded-full" @click="$emit('close')">Cerrar</button>
      </div>
      <nav class="mt-4 flex flex-wrap gap-2">
        <button
          v-for="(step, index) in assistantSteps"
          :key="step.id"
          type="button"
          class="btn btn-sm rounded-full"
          :class="assistantStep === step.id ? 'btn-primary' : (index <= assistantIndex ? 'btn-outline' : 'btn-ghost')"
          @click="assistantStep = step.id"
        >
          {{ index + 1 }}. {{ step.label }}
        </button>
      </nav>
    </header>
    <div class="flex-1 min-h-0 overflow-y-auto px-6 py-5">
      <section v-if="assistantStep === 'objective'" class="space-y-4">
        <div class="alert border border-base-300 bg-base-100/80 text-base-content" id="header-objective">
          <span>Elige para que quieres crear esta pieza.</span>
        </div>
        <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <ChoiceCard
            v-for="item in objectiveOptions"
            :key="item.id"
            :title="item.title"
            :description="item.description"
            :recommendation="item.recommendation + ' · ' + item.categoryHint"
            :selected="state.objective === item.id"
            @click="state.objective = item.id"
          />
        </div>
      </section>
      <section v-else-if="assistantStep === 'format'" class="space-y-6">
        <div class="grid gap-5 lg:grid-cols-3" id="header-format">
          <article class="card border border-base-300 bg-base-100/80" id="step-1"
          :class="[!state.outputType?'outline-4 outline-red-500':'']"
          >
            <div class="card-body p-5">
              <div class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Paso 1: Salida</div>
              <div class="mt-3 grid gap-3">
                <button
                  v-for="item in outputTypeOptions"
                  :key="item.id"
                  type="button"
                  class="card rounded-2xl border-2 p-3 text-left"
                  :class="state.outputType === item.id ? 'border-primary bg-primary/10' : 'border-base-300 bg-base-100 hover:border-primary/40'"
                  @click="chooseOutput(item.id)"
                >
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <span class="font-medium">{{ item.title }}</span>
                      <p class="hidden mt-1 text-xs text-base-content/70">{{ item.description }}</p>
                      <p class="hidden mt-2 text-xs font-medium text-primary">{{ item.helper }}</p>
                    </div>
                    <SelectionIndicator :selected="state.outputType === item.id" />
                  </div>
                </button>
              </div>
            </div>
          </article>
          <article class="card border border-base-300 bg-base-100/80" id="step-2"
          :class="[state.outputType?'':'blur-xs',
            state.outputType&&!state.format?'outline-4 outline-red-500':''
          ]">
            <div class="card-body p-5">
              <div class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Paso 2: Formato</div>
              <div class="mt-3 grid grid-cols-2 gap-3">
                <button
                  v-for="item in formatCards"
                  :key="item.id"
                  type="button"
                  class="rounded-2xl border px-3 py-2 text-left flex lg:flex-col gap-2 items-center"
                  :disabled="!state.outputType"
                  :class="state.format === item.id ? 'border-primary bg-primary/10' : 'border-base-300 bg-base-100 hover:border-primary/40 disabled:opacity-50'"
                  @click="chooseFormat(item.id)"
                >
                    <IconifyIcon :icon="item.icon" :class="item.iconClass" class="text-6xl text-base-content"/>
                  <span class="font-medium">{{ item.title }}</span>
                </button>
              </div>
            </div>
          </article>
          <article class="card border border-base-300 bg-base-100/80" id="step-3"
          :class="[state.format?'':'blur-xs',
            state.format&&!state.size?'outline-4 outline-red-500':'']">
            <div class="card-body p-5">
              <div class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Paso 3: Tamano</div>
              <div class="mt-3 flex flex-col items-start justify-start gap-3">
                <div v-if="usingCustomFormat" class="grid w-full gap-3 sm:grid-cols-2">
                  <label class="rounded-2xl border border-base-300 bg-base-100 px-4 py-3 text-left">
                    <span class="text-sm font-semibold text-base-content">Ancho (px)</span>
                    <input
                      v-model="customWidth"
                      type="number"
                      min="1"
                      step="1"
                      inputmode="numeric"
                      class="input input-bordered mt-2 w-full"
                      placeholder="Ej. 1080"
                    />
                  </label>
                  <label class="rounded-2xl border border-base-300 bg-base-100 px-4 py-3 text-left">
                    <span class="text-sm font-semibold text-base-content">Alto (px)</span>
                    <input
                      v-model="customHeight"
                      type="number"
                      min="1"
                      step="1"
                      inputmode="numeric"
                      class="input input-bordered mt-2 w-full"
                      placeholder="Ej. 1350"
                    />
                  </label>
                </div>
                <template v-else>
                  <div
                    v-for="group in groupedSizes"
                    :key="group.id"
                    class="w-full space-y-2"
                  >
                    <div class="grid w-full gap-2">
                      <button
                        v-for="size in group.options"
                        :key="size.id"
                        type="button"
                        class="rounded-2xl border px-4 py-3 text-left transition"
                        :disabled="!state.format"
                        :class="state.size === size.label
                          ? 'border-primary bg-primary/10'
                          : 'border-base-300 bg-base-100 hover:border-primary/40 disabled:opacity-50'"
                        @click="selectSizeOption(size)"
                      >
                        <div class="flex items-start justify-between gap-3">
                          <div>
                            <p class="font-medium text-base-content">{{ size.label }}</p>
                            <p class="text-sm text-base-content/70">{{ size.detail }}</p>
                          </div>
                          <SelectionIndicator :selected="state.size === size.label" />
                        </div>
                      </button>
                    </div>
                  </div>
                </template>
                <div v-if="0 && state.size" class="rounded-2xl border border-primary/30 bg-primary/10 px-3 py-2 text-left">
                  <p class="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Seleccionado</p>
                  <p class="mt-1 text-sm font-medium text-base-content">{{ state.size }}</p>
                </div>
              </div>
            </div>
          </article>
        </div>
      </section>
      <section v-else-if="assistantStep === 'content'" class="space-y-4">
        <div class="alert border border-base-300 bg-base-100/80 text-base-content" id="header-content">
          <span>Rellena los datos clave para completar las plantillas.</span>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <label
            v-for="field in fields"
            :key="field.key"
            class="rounded-[22px] border border-base-300 bg-base-100/80 p-4 text-sm font-medium text-base-content"
            :class="field.type === 'textarea' ? 'sm:col-span-2' : ''"
          >
            <span class="block">{{ field.label }}</span>
            <span v-if="field.helper" class="mt-1 block text-xs font-normal leading-5 text-base-content/65">
              {{ field.helper }}
            </span>
            <textarea v-if="field.type === 'textarea'" v-model="state.content[field.key]" class="textarea textarea-bordered mt-2 min-h-30 w-full text-base" :placeholder="fieldPlaceholders[field.key] || 'Escribe aquí...'" @input="state.autosaveMessage = 'Guardado automático · hace un instante'"></textarea>
            <input v-else v-model="state.content[field.key]" class="input input-bordered mt-2 w-full text-base" :placeholder="fieldPlaceholders[field.key] || 'Escribe aquí...'" @input="state.autosaveMessage = 'Guardado automático · hace un instante'" />
          </label>
        </div>
      </section>
      <section v-else class="space-y-5">
        <div class="flex flex-wrap gap-2" id="header-templates">
          <button
            v-for="filter in availableTemplateFilters"
            :key="filter"
            type="button"
            class="btn btn-sm rounded-full"
            :class="state.templateCategory === filter ? 'btn-primary' : 'btn-outline'"
            @click="state.templateCategory = filter"
          >
            {{ filterLabels[filter] || filter }}
          </button>
        </div>
        <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <TemplateCard
            v-for="template in filteredTemplates"
            :key="template.id"
            :template="template"
            :content="state.content"
            :meta-line="metaLine"
            :contact-line="venueLine"
            :selected="state.selectedTemplateId === template.id"
            @click="selectTemplate(template)"
          />
          <article
            class="flex min-h-85 cursor-pointer flex-col items-center justify-center rounded-[28px] border border-dashed border-base-300 bg-base-100/80 p-6 text-center transition hover:border-primary/60"
            :class="!state.selectedTemplateId ? 'ring-2 ring-primary/30' : ''"
            @click="state.selectedTemplateId = null"
          >
            <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-base-100 text-3xl text-base-content/40 shadow-sm">+</div>
            <h4 class="mt-5 text-lg font-semibold text-base-content">Plantilla vacía</h4>
            <p class="mt-2 max-w-xs text-sm leading-6 text-base-content/70">
              Empieza desde cero, manteniendo objetivo, formato y datos.
            </p>
          </article>
        </div>
      </section>
    </div>
    <StepFooter
      v-if="showFooter"
      :previous-url="null"
      :next-url="null"
      :next-disabled="!canGoNext && !isLastStep"
      class="sticky bottom-0 left-0 right-0 z-10 border-t border-base-300 bg-base-100 px-6 py-4"
    >
      <template #left>
        <button
          v-if="showStepNavigation"
          type="button"
          class="btn btn-outline btn-sm rounded-full"
          :disabled="isFirstStep"
          @click="goPrevious"
        >
          Anterior
        </button>
      </template>
      <template #right>
        <button
          v-if="!showStepNavigation"
          type="button"
          class="btn btn-primary btn-sm rounded-full"
          :disabled="!canApplyCurrentStep"
          @click="finishAndOpenEditor"
        >
          Aplicar
        </button>
        <template v-else>
          <button
            v-if="isAssistantComplete"
            type="button"
            class="btn btn-outline btn-sm rounded-full"
            @click="finishAndOpenEditor"
          >
            Aplicar
          </button>
          <button
            v-if="!isLastStep"
            type="button"
            class="btn btn-primary btn-sm rounded-full"
            :disabled="!canGoNext"
            @click="goNext"
          >
            Siguiente
          </button>
          <button
            v-else
            type="button"
            class="btn btn-primary btn-sm rounded-full"
            @click="finishAndOpenEditor"
          >
            Abrir editor
          </button>
        </template>
      </template>
    </StepFooter>
  </section>
</template>
