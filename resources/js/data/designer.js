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
        id: 'event',
        title: 'Cartel para evento',
        description: 'Conciertos, encuentros, jornadas o celebraciones.',
        recommendation: 'A3 o A4 · fecha, lugar y contacto',
        categoryHint: 'Plantillas vivas y promocionales',
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
    { id: 'other', title: 'Otros formatos', description: 'Formatos personalizados o especiales.', shape: 'h-28 w-28', gradient: 'from-slate-300 to-slate-400' },
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
    event: {
        print: ['A3 · cartel grande', 'A4 · estándar para colgar', 'A2 · máxima visibilidad'],
        digital: ['Post de Facebook', 'Historia de Instagram', 'X / Twitter'],
        fields: [
            { key: 'title', label: 'Título del evento', type: 'text' },
            { key: 'subtitle', label: 'Subtítulo o claim', type: 'text' },
            { key: 'date', label: 'Fecha y hora', type: 'text' },
            { key: 'location', label: 'Lugar', type: 'text' },
            { key: 'contact', label: 'Contacto', type: 'text' },
            { key: 'extra', label: 'Texto adicional', type: 'textarea' },
        ],
    },
    course: {
        print: ['A4 · recomendado', 'A3 · más visible', 'A5 · versión reparto'],
        digital: ['LinkedIn', 'Facebook', 'Historia de Instagram'],
        fields: [
            { key: 'title', label: 'Nombre del curso', type: 'text' },
            { key: 'subtitle', label: 'Descripción breve', type: 'text' },
            { key: 'teacher', label: 'Profesor o ponente', type: 'text' },
            { key: 'date', label: 'Fechas', type: 'text' },
            { key: 'contact', label: 'Contacto / inscripción', type: 'text' },
            { key: 'extra', label: 'Texto adicional', type: 'textarea' },
        ],
    },
    flyer: {
        print: ['A5 · flier clásico', 'DL · mano / mostrador', 'A6 · reparto compacto'],
        digital: ['Story vertical', 'WhatsApp', 'Instagram post'],
        fields: [
            { key: 'title', label: 'Mensaje principal', type: 'text' },
            { key: 'subtitle', label: 'Subtítulo', type: 'text' },
            { key: 'price', label: 'Precio o dato destacado', type: 'text' },
            { key: 'contact', label: 'Contacto', type: 'text' },
            { key: 'extra', label: 'Texto adicional', type: 'textarea' },
        ],
    },
    shop: {
        print: ['A4 · escaparate', 'A3 · impacto', 'A5 · mostrador'],
        digital: ['Facebook post', 'Story promocional', 'X / Twitter'],
        fields: [
            { key: 'title', label: 'Mensaje principal', type: 'text' },
            { key: 'subtitle', label: 'Oferta / subtítulo', type: 'text' },
            { key: 'price', label: 'Precio o promoción', type: 'text' },
            { key: 'contact', label: 'Dirección / contacto', type: 'text' },
            { key: 'extra', label: 'Texto adicional', type: 'textarea' },
        ],
    },
    generic: {
        print: ['A4 · neutro', 'A5 · compacto', 'A3 · más presencia'],
        digital: ['Post cuadrado', 'Story vertical', 'Banner horizontal'],
        fields: [
            { key: 'title', label: 'Título', type: 'text' },
            { key: 'subtitle', label: 'Subtítulo', type: 'text' },
            { key: 'contact', label: 'Contacto', type: 'text' },
            { key: 'extra', label: 'Texto adicional', type: 'textarea' },
        ],
    },
    other: {
        print: ['Manual · a definir', 'A4 · punto de partida', 'A3 · más visible'],
        digital: ['Manual · a definir', 'Post cuadrado', 'Story vertical'],
        fields: [
            { key: 'title', label: 'Título', type: 'text' },
            { key: 'subtitle', label: 'Subtítulo', type: 'text' },
            { key: 'contact', label: 'Contacto', type: 'text' },
            { key: 'extra', label: 'Notas o instrucciones', type: 'textarea' },
        ],
    },
};

export const initialDesignerState = {
    darkMode: false,
    mode: 'guided',
    objective: 'event',
    outputType: 'print',
    format: 'vertical',
    size: 'A3 · cartel grande',
    templateCategory: 'modern',
    selectedTemplateId: 'template-1',
    autosaveMessage: 'Guardado automático',
    selectedElementId: 'title',
    content: {
        title: 'Festival de Primavera',
        subtitle: 'Música, tapas y talleres para toda la familia.',
        date: '25 abril · 18:00',
        location: 'Plaza Mayor',
        teacher: 'María López',
        price: 'Entrada gratuita',
        contact: 'Info: 600 123 123',
        extra: 'Zona gastronómica · Actividades para niños · Aforo libre',
    },
    elementLayout: {
        title: { x: 28, y: 72, w: 300, zIndex: 50, fontSize: 44, color: '#ffffff', shadow: true, border: false, fontFamily: 'Poppins, sans-serif', opacity: 100, fontWeight: 'bold', italic: false, uppercase: false, textAlign: 'left', letterSpacing: 0, lineHeight: 0.95, shadowPreset: 'soft', shadowColor: '#0f172a', contourWidth: 0, contourColor: '#ffffff', neonColor: '', bubbleColor: '', backgroundColor: 'transparent' },
        subtitle: { x: 32, y: 186, w: 280, zIndex: 40, fontSize: 18, color: '#f8fafc', shadow: false, border: false, fontFamily: 'Inter, sans-serif', opacity: 100, fontWeight: 'regular', italic: false, uppercase: false, textAlign: 'left', letterSpacing: 0, lineHeight: 1.45, shadowPreset: 'soft', shadowColor: '#0f172a', contourWidth: 0, contourColor: '#ffffff', neonColor: '', bubbleColor: '', backgroundColor: 'transparent' },
        meta: { x: 36, y: 336, w: 250, zIndex: 30, fontSize: 16, color: '#ffffff', shadow: false, border: false, fontFamily: 'Inter, sans-serif', opacity: 100, fontWeight: 'bold', italic: false, uppercase: false, textAlign: 'left', letterSpacing: 0, lineHeight: 1.3, shadowPreset: 'soft', shadowColor: '#0f172a', contourWidth: 0, contourColor: '#ffffff', neonColor: '', bubbleColor: '', backgroundColor: 'transparent' },
        contact: { x: 36, y: 368, w: 230, zIndex: 20, fontSize: 15, color: '#e9d5ff', shadow: false, border: false, fontFamily: 'Inter, sans-serif', opacity: 100, fontWeight: 'regular', italic: false, uppercase: false, textAlign: 'left', letterSpacing: 0, lineHeight: 1.3, shadowPreset: 'soft', shadowColor: '#0f172a', contourWidth: 0, contourColor: '#ffffff', neonColor: '', bubbleColor: '', backgroundColor: 'transparent' },
        extra: { x: 36, y: 410, w: 270, zIndex: 10, fontSize: 15, color: '#ede9fe', shadow: false, border: false, fontFamily: 'Inter, sans-serif', opacity: 100, fontWeight: 'regular', italic: false, uppercase: false, textAlign: 'left', letterSpacing: 0, lineHeight: 1.4, shadowPreset: 'soft', shadowColor: '#0f172a', contourWidth: 0, contourColor: '#ffffff', neonColor: '', bubbleColor: '', backgroundColor: 'transparent' },
    },
};
