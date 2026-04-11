export const modeOptions = [
    {
        id: 'guided',
        title: 'Modo guiado',
        description: 'Explica objetivos, recomienda tamaños y te acompaña paso a paso.',
        badge: 'Recomendado',
    },
    {
        id: 'direct',
        title: 'Modo editor',
        description: 'Para usuarios rápidos que quieren llegar antes al editor y ajustar lo esencial.',
    },
];

export const objectiveOptions = [
    {
        id: 'event_presential',
        title: 'Evento presencial',
        description: 'Conciertos, encuentros, jornadas o celebraciones con asistencia física.',
        recommendation: 'A3 o A4 · fecha, hora, lugar y contacto',
        categoryHint: 'Plantillas vivas y promocionales',
    },
    {
        id: 'event_virtual',
        title: 'Evento virtual',
        description: 'Directos, webinars, talleres online o encuentros por videollamada.',
        recommendation: 'A3 o A4 · fecha, hora, URL de conexión y contacto',
        categoryHint: 'Plantillas limpias y digitales',
    },
    {
        id: 'course',
        title: 'Cartel para curso',
        description: 'Clases, talleres, seminarios o formaciones.',
        recommendation: 'A4 o A3 · profesor, fechas y plazas',
        categoryHint: 'Plantillas limpias e informativas',
    },
    {
        id: 'flyer',
        title: 'Flier informativo',
        description: 'Promociones, servicios o reparto en mano.',
        recommendation: 'A5 o DL · mensaje directo',
        categoryHint: 'Plantillas compactas y claras',
    },
    {
        id: 'shop',
        title: 'Anuncio para tienda',
        description: 'Ofertas, horarios o avisos para escaparate.',
        recommendation: 'A4 o A3 · precio y visibilidad',
        categoryHint: 'Plantillas comerciales',
    },
    {
        id: 'generic',
        title: 'Genérico',
        description: 'Para piezas que todavía no encajan en una categoría concreta.',
        recommendation: 'Opciones amplias · campos base',
        categoryHint: 'Plantillas mixtas',
    },
    {
        id: 'other',
        title: 'Otros',
        description: 'Casos más especiales que detallaremos después.',
        recommendation: 'Formato manual · plantillas abiertas',
        categoryHint: 'Colección abierta',
    },
];

export const formatCards = [
    { id: 'vertical', title: 'Cartel vertical', description: 'El más habitual para imprimir y colgar.', shape: 'h-36 w-24', gradient: 'from-violet-600 to-fuchsia-500' },
    { id: 'horizontal', title: 'Cartel horizontal', description: 'Útil para cabeceras y banners.', shape: 'h-24 w-36', gradient: 'from-cyan-500 to-sky-400' },
    { id: 'square', title: 'Cuadrado', description: 'Perfecto para redes o piezas cuadradas.', shape: 'h-28 w-28', gradient: 'from-amber-400 to-orange-500' },
    { id: 'other', title: 'No lo sé', description: 'No tienes claro el formato y quieres decidirlo más adelante.', shape: 'h-28 w-28', gradient: 'from-slate-300 to-slate-400' },
];

export const templateFilters = ['all', 'modern', 'minimal', 'promo', 'elegant', 'corporate', 'youth', 'informative'];

export const filterLabels = {
    all: 'Todas',
    modern: 'Modernas',
    minimal: 'Minimal',
    promo: 'Promocional',
    elegant: 'Elegante',
    corporate: 'Corporativa',
    youth: 'Juvenil',
    informative: 'Informativa',
};

export const templateCatalog = [
    { id: 'template-1', name: 'Cartel principal', category: 'modern', label: 'Moderna', theme: 'from-indigo-800 via-violet-700 to-fuchsia-600', accent: 'bg-violet-100 text-violet-700', text: 'text-white', light: false },
    { id: 'template-2', name: 'Flier cálido', category: 'promo', label: 'Promocional', theme: 'from-amber-300 via-orange-300 to-rose-400', accent: 'bg-orange-100 text-orange-700', text: 'text-slate-950', light: true },
    { id: 'template-3', name: 'Evento destacado', category: 'minimal', label: 'Minimal', theme: 'from-slate-100 via-white to-slate-50', accent: 'bg-slate-900 text-white', text: 'text-slate-950', light: true },
    { id: 'template-4', name: 'Juvenil fresca', category: 'youth', label: 'Juvenil', theme: 'from-emerald-500 via-teal-500 to-cyan-500', accent: 'bg-emerald-100 text-emerald-700', text: 'text-white', light: false },
    { id: 'template-5', name: 'Bold noche', category: 'promo', label: 'Bold', theme: 'from-slate-950 via-slate-800 to-fuchsia-700', accent: 'bg-fuchsia-100 text-fuchsia-700', text: 'text-white', light: false },
    { id: 'template-6', name: 'Informativa limpia', category: 'informative', label: 'Informativa', theme: 'from-slate-100 via-slate-200 to-slate-100', accent: 'bg-slate-100 text-slate-700', text: 'text-slate-950', light: true },
    { id: 'template-7', name: 'Elegante rosa', category: 'elegant', label: 'Elegante', theme: 'from-rose-500 via-pink-500 to-fuchsia-500', accent: 'bg-pink-100 text-pink-700', text: 'text-white', light: false },
    { id: 'template-8', name: 'Corporativa azul', category: 'corporate', label: 'Corporativa', theme: 'from-sky-700 via-cyan-600 to-blue-500', accent: 'bg-sky-100 text-sky-700', text: 'text-white', light: false },
];

export const objectiveRecommendations = {
    event_presential: {
        print: [
            { id: 'a2', label: 'A2', detail: '42 × 59,4 cm', formatHint: 'vertical' },
            { id: 'a3', label: 'A3', detail: '29,7 × 42 cm', formatHint: 'vertical' },
            { id: 'a4', label: 'A4', detail: '21 × 29,7 cm', formatHint: 'vertical' },
        ],
        digital: [
            { id: 'facebook-post', label: 'Post de Facebook', detail: '1200 × 630 px', formatHint: 'horizontal' },
            { id: 'facebook-story', label: 'Historia de Facebook', detail: '1080 × 1920 px', formatHint: 'vertical' },
            { id: 'instagram-post-square', label: 'Post cuadrado de Instagram', detail: '1080 × 1080 px', formatHint: 'square' },
            { id: 'instagram-post-vertical', label: 'Post vertical de Instagram', detail: '1080 × 1350 px', formatHint: 'vertical' },
            { id: 'instagram-story', label: 'Historia de Instagram', detail: '1080 × 1920 px', formatHint: 'vertical' },
            { id: 'x-post', label: 'Publicación de X', detail: '1600 × 900 px', formatHint: 'horizontal' },
            { id: 'linkedin-post', label: 'Post de LinkedIn', detail: '1200 × 627 px', formatHint: 'horizontal' },
            { id: 'youtube-thumbnail', label: 'Miniatura de YouTube', detail: '1280 × 720 px', formatHint: 'horizontal' },
            { id: 'youtube-short', label: 'YouTube Short', detail: '1080 × 1920 px', formatHint: 'vertical' },
            { id: 'whatsapp-status', label: 'Estado de WhatsApp', detail: '1080 × 1920 px', formatHint: 'vertical' },
        ],
        fields: [
            { key: 'title', label: 'Título del evento', type: 'text', helper: 'Debe ser llamativo y explicar de qué trata el evento, porque será lo primero que leerá la gente.' },
            { key: 'subtitle', label: 'Subtítulo o claim', type: 'text' },
            { key: 'date', label: 'Fecha', type: 'text' },
            { key: 'time', label: 'Hora', type: 'text' },
            { key: 'location', label: 'Lugar', type: 'text' },
            { key: 'contact', label: 'Contacto', type: 'text' },
            { key: 'extra', label: 'Texto adicional', type: 'textarea' },
        ],
    },
    event_virtual: {
        print: [
            { id: 'a2', label: 'A2', detail: '42 × 59,4 cm', formatHint: 'vertical' },
            { id: 'a3', label: 'A3', detail: '29,7 × 42 cm', formatHint: 'vertical' },
            { id: 'a4', label: 'A4', detail: '21 × 29,7 cm', formatHint: 'vertical' },
        ],
        digital: [
            { id: 'facebook-post', label: 'Post de Facebook', detail: '1200 × 630 px', formatHint: 'horizontal' },
            { id: 'facebook-story', label: 'Historia de Facebook', detail: '1080 × 1920 px', formatHint: 'vertical' },
            { id: 'instagram-post-square', label: 'Post cuadrado de Instagram', detail: '1080 × 1080 px', formatHint: 'square' },
            { id: 'instagram-post-vertical', label: 'Post vertical de Instagram', detail: '1080 × 1350 px', formatHint: 'vertical' },
            { id: 'instagram-story', label: 'Historia de Instagram', detail: '1080 × 1920 px', formatHint: 'vertical' },
            { id: 'x-post', label: 'Publicación de X', detail: '1600 × 900 px', formatHint: 'horizontal' },
            { id: 'linkedin-post', label: 'Post de LinkedIn', detail: '1200 × 627 px', formatHint: 'horizontal' },
            { id: 'youtube-thumbnail', label: 'Miniatura de YouTube', detail: '1280 × 720 px', formatHint: 'horizontal' },
            { id: 'youtube-live', label: 'Portada de YouTube Live', detail: '1280 × 720 px', formatHint: 'horizontal' },
            { id: 'youtube-short', label: 'YouTube Short', detail: '1080 × 1920 px', formatHint: 'vertical' },
            { id: 'zoom-banner', label: 'Banner para Zoom', detail: '1920 × 1080 px', formatHint: 'horizontal' },
        ],
        fields: [
            { key: 'title', label: 'Título del evento', type: 'text', helper: 'Debe ser claro y llamativo para explicar de qué trata el evento online.' },
            { key: 'subtitle', label: 'Subtítulo o claim', type: 'text' },
            { key: 'date', label: 'Fecha', type: 'text' },
            { key: 'time', label: 'Hora', type: 'text' },
            { key: 'platform', label: 'URL de conexión', type: 'text', helper: 'Pega la URL de acceso. Más adelante podrá convertirse en un código QR dentro del diseño.' },
            { key: 'contact', label: 'Contacto o enlace', type: 'text' },
            { key: 'extra', label: 'Texto adicional', type: 'textarea' },
        ],
    },
    course: {
        print: [
            { id: 'a3', label: 'A3', detail: '29,7 × 42 cm', formatHint: 'vertical' },
            { id: 'a4', label: 'A4', detail: '21 × 29,7 cm', formatHint: 'vertical' },
            { id: 'a5', label: 'A5', detail: '14,8 × 21 cm', formatHint: 'vertical' },
        ],
        digital: [
            { id: 'linkedin-post', label: 'Post de LinkedIn', detail: '1200 × 627 px', formatHint: 'horizontal' },
            { id: 'facebook-post', label: 'Post de Facebook', detail: '1200 × 630 px', formatHint: 'horizontal' },
            { id: 'instagram-story', label: 'Historia de Instagram', detail: '1080 × 1920 px', formatHint: 'vertical' },
        ],
        fields: [
            { key: 'title', label: 'Nombre del curso', type: 'text' },
            { key: 'subtitle', label: 'Descripción breve', type: 'text' },
            { key: 'teacher', label: 'Profesor o ponente', type: 'text' },
            { key: 'date', label: 'Fecha', type: 'text' },
            { key: 'time', label: 'Hora', type: 'text' },
            { key: 'contact', label: 'Contacto / inscripción', type: 'text' },
            { key: 'extra', label: 'Texto adicional', type: 'textarea' },
        ],
    },
    flyer: {
        print: [
            { id: 'a5', label: 'A5', detail: '14,8 × 21 cm', formatHint: 'vertical' },
            { id: 'a4', label: 'A4', detail: '21 × 29,7 cm', formatHint: 'vertical' },
            { id: 'a3', label: 'A3', detail: '29,7 × 42 cm', formatHint: 'vertical' },
        ],
        digital: [
            { id: 'instagram-story', label: 'Historia vertical', detail: '1080 × 1920 px', formatHint: 'vertical' },
            { id: 'whatsapp-status', label: 'Estado de WhatsApp', detail: '1080 × 1920 px', formatHint: 'vertical' },
            { id: 'instagram-post-square', label: 'Post de Instagram', detail: '1080 × 1080 px', formatHint: 'square' },
        ],
        fields: [
            { key: 'title', label: 'Mensaje principal', type: 'text' },
            { key: 'subtitle', label: 'Subtítulo', type: 'text' },
            { key: 'price', label: 'Precio o dato destacado', type: 'text' },
            { key: 'contact', label: 'Contacto', type: 'text' },
            { key: 'extra', label: 'Texto adicional', type: 'textarea' },
        ],
    },
    shop: {
        print: [
            { id: 'a3', label: 'A3', detail: '29,7 × 42 cm', formatHint: 'vertical' },
            { id: 'a4', label: 'A4', detail: '21 × 29,7 cm', formatHint: 'vertical' },
            { id: 'a5', label: 'A5', detail: '14,8 × 21 cm', formatHint: 'vertical' },
        ],
        digital: [
            { id: 'facebook-post', label: 'Post de Facebook', detail: '1200 × 630 px', formatHint: 'horizontal' },
            { id: 'story-promo', label: 'Historia promocional', detail: '1080 × 1920 px', formatHint: 'vertical' },
            { id: 'x-post', label: 'Publicación de X', detail: '1600 × 900 px', formatHint: 'horizontal' },
        ],
        fields: [
            { key: 'title', label: 'Mensaje principal', type: 'text' },
            { key: 'subtitle', label: 'Oferta / subtítulo', type: 'text' },
            { key: 'price', label: 'Precio o promoción', type: 'text' },
            { key: 'contact', label: 'Dirección / contacto', type: 'text' },
            { key: 'extra', label: 'Texto adicional', type: 'textarea' },
        ],
    },
    generic: {
        print: [
            { id: 'a2', label: 'A2', detail: '42 × 59,4 cm', formatHint: 'vertical' },
            { id: 'a3', label: 'A3', detail: '29,7 × 42 cm', formatHint: 'vertical' },
            { id: 'a4', label: 'A4', detail: '21 × 29,7 cm', formatHint: 'vertical' },
            { id: 'a5', label: 'A5', detail: '14,8 × 21 cm', formatHint: 'vertical' },
        ],
        digital: [
            { id: 'post-square', label: 'Post cuadrado', detail: '1080 × 1080 px', formatHint: 'square' },
            { id: 'story-vertical', label: 'Historia vertical', detail: '1080 × 1920 px', formatHint: 'vertical' },
            { id: 'banner-horizontal', label: 'Banner horizontal', detail: '1600 × 900 px', formatHint: 'horizontal' },
            { id: 'facebook-post', label: 'Post de Facebook', detail: '1200 × 630 px', formatHint: 'horizontal' },
            { id: 'instagram-post-vertical', label: 'Post vertical de Instagram', detail: '1080 × 1350 px', formatHint: 'vertical' },
            { id: 'linkedin-post', label: 'Post de LinkedIn', detail: '1200 × 627 px', formatHint: 'horizontal' },
            { id: 'youtube-thumbnail', label: 'Miniatura de YouTube', detail: '1280 × 720 px', formatHint: 'horizontal' },
        ],
        fields: [
            { key: 'title', label: 'Título', type: 'text' },
            { key: 'subtitle', label: 'Subtítulo', type: 'text' },
            { key: 'contact', label: 'Contacto', type: 'text' },
            { key: 'extra', label: 'Texto adicional', type: 'textarea' },
        ],
    },
    other: {
        print: [
            { id: 'a2', label: 'A2', detail: '42 × 59,4 cm', formatHint: 'vertical' },
            { id: 'a3', label: 'A3', detail: '29,7 × 42 cm', formatHint: 'vertical' },
            { id: 'a4', label: 'A4', detail: '21 × 29,7 cm', formatHint: 'vertical' },
            { id: 'a5', label: 'A5', detail: '14,8 × 21 cm', formatHint: 'vertical' },
        ],
        digital: [
            { id: 'facebook-post', label: 'Post de Facebook', detail: '1200 × 630 px', formatHint: 'horizontal' },
            { id: 'facebook-story', label: 'Historia de Facebook', detail: '1080 × 1920 px', formatHint: 'vertical' },
            { id: 'instagram-post-square', label: 'Post cuadrado de Instagram', detail: '1080 × 1080 px', formatHint: 'square' },
            { id: 'instagram-post-vertical', label: 'Post vertical de Instagram', detail: '1080 × 1350 px', formatHint: 'vertical' },
            { id: 'instagram-story', label: 'Historia de Instagram', detail: '1080 × 1920 px', formatHint: 'vertical' },
            { id: 'x-post', label: 'Publicación de X', detail: '1600 × 900 px', formatHint: 'horizontal' },
            { id: 'linkedin-post', label: 'Post de LinkedIn', detail: '1200 × 627 px', formatHint: 'horizontal' },
            { id: 'youtube-thumbnail', label: 'Miniatura de YouTube', detail: '1280 × 720 px', formatHint: 'horizontal' },
            { id: 'youtube-short', label: 'YouTube Short', detail: '1080 × 1920 px', formatHint: 'vertical' },
            { id: 'whatsapp-status', label: 'Estado de WhatsApp', detail: '1080 × 1920 px', formatHint: 'vertical' },
        ],
        fields: [
            { key: 'title', label: 'Título', type: 'text' },
            { key: 'subtitle', label: 'Subtítulo', type: 'text' },
            { key: 'contact', label: 'Contacto', type: 'text' },
            { key: 'extra', label: 'Notas o instrucciones', type: 'textarea' },
        ],
    },
};

export function inferFormatFromSizeOption(option) {
    return option?.formatHint ?? null;
}

export const initialDesignerState = {
    darkMode: false,
    mode: 'guided',
    objective: null,
    outputType: null,
    format: null,
    size: null,
    templateCategory: 'all',
    selectedTemplateId: null,
    autosaveMessage: 'Guardado automático',
    selectedElementId: 'title',
    content: {
        title: '',
        subtitle: '',
        date: '',
        time: '',
        location: '',
        platform: '',
        teacher: '',
        price: '',
        contact: '',
        extra: '',
    },
    elementLayout: {
        title: { x: 28, y: 72, w: 300, zIndex: 50, fontSize: 44, color: '#ffffff', shadow: true, border: false, fontFamily: 'Poppins, sans-serif', opacity: 100, fontWeight: 'bold', italic: false, uppercase: false, textAlign: 'left', letterSpacing: 0, lineHeight: 0.95, shadowPreset: 'soft', shadowColor: '#0f172a', contourWidth: 0, contourColor: '#ffffff', neonColor: '', bubbleColor: '', backgroundColor: 'transparent' },
        subtitle: { x: 32, y: 186, w: 280, zIndex: 40, fontSize: 18, color: '#f8fafc', shadow: false, border: false, fontFamily: 'Inter, sans-serif', opacity: 100, fontWeight: 'regular', italic: false, uppercase: false, textAlign: 'left', letterSpacing: 0, lineHeight: 1.45, shadowPreset: 'soft', shadowColor: '#0f172a', contourWidth: 0, contourColor: '#ffffff', neonColor: '', bubbleColor: '', backgroundColor: 'transparent' },
        meta: { x: 36, y: 336, w: 250, zIndex: 30, fontSize: 16, color: '#ffffff', shadow: false, border: false, fontFamily: 'Inter, sans-serif', opacity: 100, fontWeight: 'bold', italic: false, uppercase: false, textAlign: 'left', letterSpacing: 0, lineHeight: 1.3, shadowPreset: 'soft', shadowColor: '#0f172a', contourWidth: 0, contourColor: '#ffffff', neonColor: '', bubbleColor: '', backgroundColor: 'transparent' },
        contact: { x: 36, y: 368, w: 230, zIndex: 20, fontSize: 15, color: '#e9d5ff', shadow: false, border: false, fontFamily: 'Inter, sans-serif', opacity: 100, fontWeight: 'regular', italic: false, uppercase: false, textAlign: 'left', letterSpacing: 0, lineHeight: 1.3, shadowPreset: 'soft', shadowColor: '#0f172a', contourWidth: 0, contourColor: '#ffffff', neonColor: '', bubbleColor: '', backgroundColor: 'transparent' },
        extra: { x: 36, y: 410, w: 270, zIndex: 10, fontSize: 15, color: '#ede9fe', shadow: false, border: false, fontFamily: 'Inter, sans-serif', opacity: 100, fontWeight: 'regular', italic: false, uppercase: false, textAlign: 'left', letterSpacing: 0, lineHeight: 1.4, shadowPreset: 'soft', shadowColor: '#0f172a', contourWidth: 0, contourColor: '#ffffff', neonColor: '', bubbleColor: '', backgroundColor: 'transparent' },
    },
};
