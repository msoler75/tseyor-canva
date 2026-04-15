<script setup>
import { Head, Link } from '@inertiajs/vue3';
import { computed } from 'vue';

const props = defineProps({
  status: {
    type: [Number, String],
    default: 500,
  },
  message: {
    type: String,
    default: '',
  },
});

const normalizedStatus = computed(() => Number(props.status) || 500);

const title = computed(() => ({
  403: 'Acceso restringido',
  404: 'Página no encontrada',
  419: 'Sesión expirada',
  422: 'Solicitud no válida',
  500: 'Se produjo un error',
  503: 'Servicio no disponible',
}[normalizedStatus.value] || 'Error inesperado'));

const description = computed(() => props.message || ({
  403: 'No tienes permisos para acceder a este recurso.',
  404: 'La página que buscas no existe o ya no está disponible.',
  419: 'Tu sesión ha expirado. Vuelve a iniciar sesión para continuar.',
  422: 'La solicitud no pudo procesarse. Revisa los datos e inténtalo de nuevo.',
  500: 'Algo salió mal en la aplicación. Inténtalo de nuevo en unos minutos.',
  503: 'La aplicación está temporalmente fuera de servicio por mantenimiento o sobrecarga.',
}[normalizedStatus.value] || 'Se ha producido un problema inesperado.'));

const accentClass = computed(() => (
  normalizedStatus.value >= 500
    ? 'from-rose-500/20 via-orange-500/10 to-base-100'
    : 'from-sky-500/20 via-violet-500/10 to-base-100'
));
</script>

<template>
  <Head :title="`Error ${normalizedStatus}`" />

  <div class="min-h-screen bg-base-100 text-base-content">
    <div class="mx-auto flex min-h-screen max-w-6xl items-center px-6 py-10">
      <section class="grid w-full gap-8 overflow-hidden rounded-[32px] border border-base-300 bg-base-100 shadow-2xl lg:grid-cols-[1.05fr,0.95fr]">
        <div class="relative overflow-hidden bg-gradient-to-br p-8 sm:p-10" :class="accentClass">
          <div class="absolute inset-0 opacity-60 [background-image:radial-gradient(circle_at_top_right,theme(colors.primary/.18),transparent_32%),radial-gradient(circle_at_bottom_left,theme(colors.secondary/.18),transparent_28%)]"></div>
          <div class="relative">
            <p class="text-xs font-semibold uppercase tracking-[0.28em] text-primary">TSEYOR Canva</p>
            <div class="mt-8 inline-flex items-baseline gap-3 rounded-3xl border border-base-300/70 bg-base-100/75 px-5 py-4 shadow-sm backdrop-blur">
              <span class="text-6xl font-black leading-none text-primary sm:text-7xl">{{ normalizedStatus }}</span>
              <span class="text-sm font-medium uppercase tracking-[0.24em] text-base-content/55">Código</span>
            </div>

            <div class="mt-8 max-w-xl">
              <h1 class="text-3xl font-semibold leading-tight sm:text-4xl">{{ title }}</h1>
              <p class="mt-4 text-sm leading-7 text-base-content/75 sm:text-base">{{ description }}</p>
            </div>
          </div>
        </div>

        <div class="flex items-center p-8 sm:p-10">
          <div class="w-full space-y-6">
            <div class="rounded-3xl border border-base-300 bg-base-100 p-6 shadow-sm">
              <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Qué puedes hacer ahora</p>
              <ul class="mt-4 space-y-3 text-sm leading-6 text-base-content/75">
                <li>• Volver al inicio y abrir otro diseño.</li>
                <li>• Revisar si tu sesión sigue activa.</li>
                <li>• Recargar la página si crees que ha sido un fallo puntual.</li>
              </ul>
            </div>

            <div class="flex flex-wrap gap-3">
              <Link href="/" class="btn btn-primary rounded-full px-6">
                Ir al inicio
              </Link>
              <button type="button" class="btn btn-outline rounded-full px-6" @click="window.location.reload()">
                Reintentar
              </button>
              <button type="button" class="btn btn-ghost rounded-full px-6" @click="window.history.back()">
                Volver atrás
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
