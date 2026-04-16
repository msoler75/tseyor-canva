// Silenciar errores de cssRules/CORS en desarrollo para evitar ruido en consola
if (import.meta.env && import.meta.env.DEV) {
    const originalError = console.error;
    console.error = (...args) => {
        if (
            args[0]?.toString().includes('cssRules') ||
            args[0]?.toString().includes('SecurityError') ||
            args[0]?.message?.includes('CORS')
        ) {
            console.debug('🔇 Ruido esperado en desarrollo:', args[0]);
            return;
        }
        originalError.apply(console, args);
    };
}



import './bootstrap';
import '../css/app.css';

import { createApp, h } from 'vue';
import { createInertiaApp } from '@inertiajs/vue3';
import { Icon } from '@iconify/vue';

createInertiaApp({
    resolve: (name) => {
        const pages = import.meta.glob('./Pages/**/*.vue');

        return pages[`./Pages/${name}.vue`]();
    },
    setup({ el, App, props, plugin }) {
        createApp({ render: () => h(App, props) })
            .use(plugin)
            .component('IconifyIcon', Icon)
            .mount(el);
    },
    progress: {
        color: '#7c3aed',
    },
});
