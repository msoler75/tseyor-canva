<script setup>
import { ref, computed, watch } from 'vue';
import ChoiceCard from './ChoiceCard.vue';
import SelectionIndicator from './SelectionIndicator.vue';
import TemplateCard from './TemplateCard.vue';
import StepFooter from './StepFooter.vue';
import {
  filterLabels,
  formatCards,
  objectiveOptions,
  objectiveRecommendations,
  templateCatalog,
  templateFilters,
} from '../../data/designer';
import { useDesignerState, resetDesignerState, flushDesignerStatePersistence } from '../../composables/useDesignerState';

const props = defineProps({
  step: { type: String, default: 'objective' },
  onFinish: Function, // callback opcional para cuando termina
  showFooter: { type: Boolean, default: true },
  showClose: { type: Boolean, default: true },
});

const emit = defineEmits(['close', 'finish']);
const state = useDesignerState();
const assistantSteps = [
  { id: 'objective', label: 'Objetivo' },
  { id: 'format', label: 'Formato' },
  { id: 'content', label: 'Datos' },
  { id: 'templates', label: 'Plantillas' },
];
const assistantStep = ref(props.step);
const assistantIndex = computed(() => assistantSteps.findIndex((step) => step.id === assistantStep.value));
const isFirstStep = computed(() => assistantIndex.value <= 0);
const isLastStep = computed(() => assistantIndex.value === assistantSteps.length - 1);

const objectiveTitle = computed(() => objectiveOptions.find((item) => item.id === state.objective)?.title ?? 'Sin objetivo');
const sizes = computed(() => {
  if (!state.outputType) return [];
  const rules = objectiveRecommendations[state.objective] ?? objectiveRecommendations.generic;
  return rules[state.outputType];
});
const selectedSizeId = computed({
  get: () => sizes.value.find((size) => size.label === state.size)?.id ?? '',
  set: (sizeId) => {
    const selected = sizes.value.find((size) => size.id === sizeId);
    if (selected) {
      selectSizeOption(selected);
    }
  },
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
const filteredTemplates = computed(() => (!state.templateCategory || state.templateCategory === 'all')
  ? templateCatalog
  : templateCatalog.filter((item) => item.category === state.templateCategory));
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

function goNext() {
  if (!canGoNext.value || isLastStep.value) return;
  assistantStep.value = assistantSteps[assistantIndex.value + 1].id;
}
function goPrevious() {
  if (isFirstStep.value) return;
  assistantStep.value = assistantSteps[assistantIndex.value - 1].id;
}
function selectSizeOption(option) {
  state.size = option.label;
  if (state.format === 'other' && option.formatHint) {
    state.format = option.formatHint;
  }
}
function finishAndOpenEditor() {
  emit('finish');
  if (props.onFinish) props.onFinish();
}
watch(() => props.step, (val) => {
  if (val && assistantSteps.some(s => s.id === val)) assistantStep.value = val;
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
        <div class="alert border border-base-300 bg-base-100/80 text-base-content">
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
        <div v-if="state.objective" class="alert border border-base-300 bg-base-100/80 text-base-content shadow-sm">
          <span>Objetivo activo: <strong>{{ objectiveTitle }}</strong></span>
        </div>
        <div class="grid gap-5 lg:grid-cols-3">
          <article class="card border border-base-300 bg-base-100/80">
            <div class="card-body p-5">
              <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Paso 1</p>
              <p class="mt-1 text-base font-semibold">Salida</p>
              <div class="mt-3 grid gap-3">
                <button
                  type="button"
                  class="card rounded-2xl border-2 p-3 text-left"
                  :class="state.outputType === 'print' ? 'border-primary bg-primary/10' : 'border-base-300 bg-base-100 hover:border-primary/40'"
                  @click="state.outputType = 'print'; state.size = null"
                >
                  <div class="flex items-start justify-start gap-3">
                    <span class="font-medium">Impresión</span>
                    <SelectionIndicator :selected="state.outputType === 'print'" />
                  </div>
                </button>
                <button
                  type="button"
                  class="card rounded-2xl border-2 p-3 text-left"
                  :class="state.outputType === 'digital' ? 'border-primary bg-primary/10' : 'border-base-300 bg-base-100 hover:border-primary/40'"
                  @click="state.outputType = 'digital'; state.size = null"
                >
                  <div class="flex items-start justify-start gap-3">
                    <span class="font-medium">Digital</span>
                    <SelectionIndicator :selected="state.outputType === 'digital'" />
                  </div>
                </button>
              </div>
            </div>
          </article>
          <article class="card border border-base-300 bg-base-100/80">
            <div class="card-body p-5">
              <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Paso 2</p>
              <p class="mt-1 text-base font-semibold">Formato</p>
              <div class="mt-3 grid gap-3">
                <button
                  v-for="item in formatCards"
                  :key="item.id"
                  type="button"
                  class="rounded-2xl border px-3 py-2 text-left"
                  :disabled="!state.outputType"
                  :class="state.format === item.id ? 'border-primary bg-primary/10' : 'border-base-300 bg-base-100 hover:border-primary/40 disabled:opacity-50'"
                  @click="state.format = item.id; state.size = null"
                >
                  <span class="font-medium">{{ item.title }}</span>
                </button>
              </div>
            </div>
          </article>
          <article class="card border border-base-300 bg-base-100/80">
            <div class="card-body p-5">
              <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Paso 3</p>
              <p class="mt-1 text-base font-semibold">Tamaño</p>
              <div class="mt-3 flex flex-col items-start justify-start gap-3">
                <label class="w-full">
                  <span class="mb-2 block text-xs font-medium uppercase tracking-[0.18em] text-base-content/60">Listado de tamaños</span>
                  <select
                    v-model="selectedSizeId"
                    class="select select-bordered w-full rounded-2xl bg-base-100"
                    :disabled="!state.format"
                  >
                    <option disabled value="">Selecciona un tamaño recomendado</option>
                    <option v-for="size in sizes" :key="size.id" :value="size.id">
                      {{ size.label }} · {{ size.detail }}
                    </option>
                  </select>
                </label>
                <div v-if="state.size" class="rounded-2xl border border-primary/30 bg-primary/10 px-3 py-2 text-left">
                  <p class="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Seleccionado</p>
                  <p class="mt-1 text-sm font-medium text-base-content">{{ state.size }}</p>
                </div>
              </div>
            </div>
          </article>
        </div>
      </section>
      <section v-else-if="assistantStep === 'content'" class="space-y-4">
        <div class="alert border border-base-300 bg-base-100/80 text-base-content">
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
        <div class="flex flex-wrap gap-2">
          <button
            v-for="filter in templateFilters"
            :key="filter"
            type="button"
            class="btn btn-sm rounded-full"
            :class="state.templateCategory === filter ? 'btn-primary' : 'btn-outline'"
            @click="state.templateCategory = filter"
          >
            {{ filterLabels[filter] }}
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
            @click="state.selectedTemplateId = template.id"
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
        <button type="button" class="btn btn-outline btn-sm rounded-full" :disabled="isFirstStep" @click="goPrevious">Anterior</button>
      </template>
      <template #right>
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
    </StepFooter>
  </section>
</template>
