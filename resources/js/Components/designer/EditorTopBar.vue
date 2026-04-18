<script setup>
import { Icon } from '@iconify/vue';
import Avatar from '@/Components/Avatar.vue';

defineProps({
  authUser: {
    type: Object,
    default: null,
  },
  designTitle: {
    type: String,
    default: 'Diseño sin título',
  },
  size: {
    type: String,
    default: 'Tamaño no definido',
  },
  canUndo: {
    type: Boolean,
    default: false,
  },
  canRedo: {
    type: Boolean,
    default: false,
  },
  undoActionLabel: {
    type: String,
    default: 'edición',
  },
  redoActionLabel: {
    type: String,
    default: 'edición',
  },
  zoomLevel: {
    type: [Number, String],
    default: 100,
  },
  darkMode: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits([
  'goHome',
  'createNewDesign',
  'downloadDesign',
  'duplicateDesign',
  'login',
  'logout',
  'renameDesign',
  'openDesignAssistantStep',
  'undo',
  'redo',
  'updateZoomLevel',
  'toggleDarkMode',
  'exportNavigate',
]);

const handleZoomInput = (event) => {
  emit('updateZoomLevel', event.target.value);
};
</script>

<template>
  <nav class="flex flex-wrap items-center justify-between border-b border-base-300 bg-base-100 px-4 py-1 shadow-sm">
    <div class="flex flex-wrap items-center gap-4">
      <button
        type="button"
        class="btn btn-ghost btn-circle"
        title="Volver al inicio"
        aria-label="Inicio"
        @click="emit('goHome')"
      >
        <Icon icon="ph:house-bold" class="text-xl" />
      </button>

      <div class="dropdown dropdown-start">
        <button
          tabindex="0"
          type="button"
          class="btn rounded-full"
          title="Archivo"
          aria-label="Archivo"
        >
          Archivo
        </button>
        <ul tabindex="0" class="dropdown-content menu z-60 mt-2 w-64 rounded-2xl border border-base-300 bg-base-100 p-2 shadow-xl">
          <li>
            <button type="button" @click="emit('createNewDesign')">
              <Icon icon="ph:file-plus-bold" class="text-lg" />
              Crear un diseño nuevo
            </button>
          </li>
          <li>
            <button type="button" @click="emit('downloadDesign')">
              <Icon icon="ph:download-simple-bold" class="text-lg" />
              Descargar
            </button>
          </li>
          <li>
            <button type="button" @click="emit('duplicateDesign')">
              <Icon icon="ph:copy-bold" class="text-lg" />
              Hacer una copia
            </button>
          </li>
          <li v-if="authUser">
            <button type="button" @click="emit('logout')">
              <Icon icon="ph:sign-out-bold" class="text-lg" />
              Cerrar sesión
            </button>
          </li>
          <li v-else>
            <button type="button" @click="emit('login')">
              <Icon icon="ph:sign-in-bold" class="text-lg" />
              Iniciar sesión
            </button>
          </li>
        </ul>
      </div>

      <div class="dropdown dropdown-start">
        <button
          tabindex="0"
          type="button"
          class="btn rounded-full"
          title="Diseño"
          aria-label="Diseño"
        >
          Diseño
        </button>
        <ul tabindex="0" class="dropdown-content menu z-60 mt-2 w-72 rounded-2xl border border-base-300 bg-base-100 p-2 shadow-xl">
            <li>
            <button type="button" @click="emit('renameDesign')">
              <Icon icon="ph:pencil-simple-bold" class="text-lg" />
              Cambiar nombre del diseño
            </button>
          </li>
          <li>
            <button type="button" @click="emit('openDesignAssistantStep', 'format')">
              <Icon icon="ph:frame-corners-bold" class="text-lg" />
              Cambiar formato/dimensiones
            </button>
          </li>
          <li>
            <button type="button" @click="emit('openDesignAssistantStep', 'content')">
              <Icon icon="ph:list-bullets-bold" class="text-lg" />
              Editar campos/datos
            </button>
          </li>
          <li>
            <button type="button" @click="emit('openDesignAssistantStep', 'templates')">
              <Icon icon="ph:layout-bold" class="text-lg" />
              Cambiar plantilla
            </button>
          </li>
        </ul>
      </div>

      <div class="flex items-center gap-3 rounded-2xl p-1 shadow-sm">
        <button
          type="button"
          class="btn btn-ghost btn-circle"
          :class="canUndo ? 'text-base-content hover:bg-base-200' : 'text-base-content/35'"
          :disabled="!canUndo"
          :title="`Deshacer: ${undoActionLabel} (Ctrl/Cmd + Z)`"
          aria-label="Deshacer"
          @click="emit('undo')"
        >
          <Icon icon="ci:arrow-undo-up-left" class="text-2xl" />
        </button>
        <button
          type="button"
          class="btn btn-ghost btn-circle"
          :class="canRedo ? 'text-base-content hover:bg-base-200' : 'text-base-content/35'"
          :disabled="!canRedo"
          :title="`Rehacer: ${redoActionLabel} (Ctrl/Cmd + Y)`"
          aria-label="Rehacer"
          @click="emit('redo')"
        >
          <Icon icon="ci:arrow-undo-up-right" class="text-2xl" />
        </button>
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-4">

        <span class="max-w-[22ch] truncate text-sm font-semibold text-base-content">{{ designTitle || 'Diseño sin título' }}</span>
      <span class="mr-8 text-sm text-base-content/65">{{ size || 'Tamaño no definido' }}</span>

      <div class="flex items-center gap-2 rounded-xl border border-base-300 px-3 py-2">
        <span class="text-xs font-semibold uppercase tracking-[0.16em] text-base-content/60">Zoom</span>
        <input
          :value="zoomLevel"
          type="range"
          min="25"
          max="200"
          step="5"
          class="range range-primary h-2 w-28"
          @input="handleZoomInput"
        />
        <input
          :value="zoomLevel"
          type="number"
          min="25"
          max="200"
          step="5"
          class="input input-bordered input-sm w-10 text-md"
          @input="handleZoomInput"
        />
        <span class="text-xs text-base-content/60">%</span>
      </div>

      <button
        type="button"
        class="btn text-lg rounded-full px-1.5"
        :title="darkMode ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'"
        @click="emit('toggleDarkMode')"
      >
        {{ darkMode ? '🌙' : '☀️' }}
      </button>

      <div v-if="authUser" class="dropdown dropdown-end">
        <button
          type="button"
          tabindex="0"
          class="btn btn-ghost rounded-full gap-2 border border-base-300/70 px-0"
          title="Cuenta"
        >
          <Avatar
            :user="authUser"
            :link="false"
            image-class="h-9 w-9"
            text-class="text-xs font-bold"
            :lazy="true"
          />
        </button>
        <div tabindex="0" class="dropdown-content z-[70] mt-2 w-64 rounded-2xl border border-base-300 bg-base-100 p-4 shadow-xl">
          <p class="font-bold text-base-content">{{ authUser.name }}</p>
          <p class="mt-1 text-xs text-base-content/60">{{ authUser.email }}</p>
          <button type="button" class="btn btn-ghost mt-4 justify-start rounded-xl" @click="emit('logout')">
            Cerrar sesión
          </button>
        </div>
      </div>

      <button
        v-else
        type="button"
        class="btn btn-primary rounded-full"
        title="Iniciar sesión"
        @click="emit('login')"
      >
        <Icon icon="ph:sign-in-bold" class="text-lg" />
        <span>Iniciar sesión</span>
      </button>

      <button type="button" class="btn btn-primary rounded-full" @click="emit('exportNavigate', $event)">
        <Icon icon="ph:export-bold" class="text-lg" />
        Exportar</button>
    </div>
  </nav>
</template>
