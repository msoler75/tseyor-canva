import { reactive, watch } from 'vue';
import { usePage } from '@inertiajs/vue3';
import axios from 'axios';
import { initialDesignerState } from '../data/designer';
import { readThemePreference, setThemePreference } from './useThemePreference';

const BASE_LAYOUT_KEYS = new Set(['background', 'title', 'subtitle', 'meta', 'contact', 'extra']);

let designerState;
let persistenceBootstrapped = false;
let saveTimer;
let saveInFlight = false;
let queuedSave = null;
let currentSaveEndpoint = '/designer/state';
let currentHydratedDesignUuid = null;
let currentRequestIsAuthenticated = false;
let persistenceMeta = {};

function normalizeUploadedAssetUrl(value) {
    if (typeof value !== 'string' || !value) {
        return value;
    }

    try {
        const url = new URL(value, window.location.origin);

        if (url.pathname.startsWith('/storage/designer/uploads/')) {
            url.pathname = `/designer${url.pathname}`;
            return url.toString();
        }

        return typeof window !== 'undefined' && value.startsWith('/')
            ? `${window.location.origin}${url.pathname}${url.search}${url.hash}`
            : value;
    } catch {
        if (value.startsWith('/storage/designer/uploads/')) {
            return `/designer${value}`;
        }

        return value;
    }
}


/**
 * Obtiene el estado reactivo del diseñador.
 * @param {Object} [opts]
 * @param {boolean} [opts.forceRehydrate] - Si es true, fuerza la rehidratación desde los props actuales.
 * @param {Object} [opts.overrideState] - Si se pasa, se usa como estado fuente en vez de los props.
 */
export function useDesignerState(opts = {}) {
    const page = usePage();
    const sessionState = opts.overrideState !== undefined
        ? opts.overrideState
        : (page.props.designer?.state ?? null);
    const saveEndpoint = page.props.designer?.endpoints?.save ?? '/designer/state';
    const incomingDesignUuid = sessionState?.currentDesignUuid ?? page.props.designer?.currentDesign?.uuid ?? null;
    currentSaveEndpoint = saveEndpoint;
    currentRequestIsAuthenticated = Boolean(page.props.auth?.user);

    const shouldForce = opts.forceRehydrate === true;

    if (!designerState || shouldForce) {
        // Si ya existe, limpiar y rehidratar
        if (designerState && shouldForce) {
            Object.keys(designerState).forEach((key) => {
                delete designerState[key];
            });
            Object.assign(designerState, buildInitialState(sessionState));
        } else {
            designerState = reactive(buildInitialState(sessionState));
        }
        currentHydratedDesignUuid = designerState.currentDesignUuid ?? incomingDesignUuid;
    } else if (incomingDesignUuid && incomingDesignUuid !== currentHydratedDesignUuid) {
        const fresh = buildInitialState(sessionState);
        Object.keys(designerState).forEach((key) => {
            delete designerState[key];
        });
        Object.assign(designerState, fresh);
        currentHydratedDesignUuid = designerState.currentDesignUuid ?? incomingDesignUuid;
    }

    if (!persistenceBootstrapped) {
        persistenceBootstrapped = true;
        bootstrapPersistence(saveEndpoint);
    }

    return designerState;
}


/**
 * Hidrata el estado del diseñador desde los props actuales, forzando la rehidratación.
 * Úsalo tras resetDesignerState o cuando quieras garantizar que el estado se sincroniza con backend.
 */
export function hydrateDesignerStateFromPage() {
    const page = usePage();
    // Forzar rehidratación desde los props actuales
    const state = useDesignerState({ forceRehydrate: true });
    const designUuid = page.props.designer?.currentDesign?.uuid ?? null;
    const savedTheme = readThemePreference();

    // LOG: Estado recibido al hidratar
    // eslint-disable-next-line no-console
    console.log('[hydrateDesignerStateFromPage] props.designer.state:', page.props.designer?.state);

    // --- Sincronización de textos entre content y elementLayout tras hidratar (DRY) ---
    if (state && state.content && state.elementLayout) {
        syncContentAndElementLayout(state.content, state.elementLayout);
    }

    if (designUuid) {
        state.currentDesignUuid = designUuid;
        currentHydratedDesignUuid = designUuid;
    }

    if (savedTheme !== null) {
        state.darkMode = savedTheme;
    }

    // LOG: Estado final tras hidratar
    // eslint-disable-next-line no-console
    console.log('[hydrateDesignerStateFromPage] state:', state);

    return state;
}

export function toggleDesignerDarkMode() {
    if (!designerState) {
        useDesignerState();
    }

    designerState.darkMode = !designerState.darkMode;

    return designerState.darkMode;
}


/**
 * Resetea el estado del diseñador a los valores iniciales (sin props).
 * Si quieres rehidratar desde backend tras reset, llama después a hydrateDesignerStateFromPage().
 */
export function resetDesignerState() {
    currentHydratedDesignUuid = null;

    if (!designerState) {
        designerState = reactive(buildInitialState(null));
        return designerState;
    }

    Object.keys(designerState).forEach((key) => {
        delete designerState[key];
    });

    Object.assign(designerState, buildInitialState(null));

    return designerState;
}

function buildInitialState(sessionState) {
    const savedTheme = readThemePreference();
    const base = {
        ...initialDesignerState,
        content: { ...initialDesignerState.content },
        elementLayout: structuredClone(initialDesignerState.elementLayout),
    };

    // LOG: Estado recibido en buildInitialState
    // eslint-disable-next-line no-console
    console.log('[buildInitialState] sessionState:', sessionState);

    if (!sessionState) {
        base.darkMode = savedTheme ?? false;
        return base;
    }

    const mergedElementLayout = mergeElementLayout(base.elementLayout, sessionState.elementLayout ?? {});
    const normalizedContent = {
        ...base.content,
        ...normalizeContentStrings(sessionState.content ?? {}),
    };
    syncContentAndElementLayout(normalizedContent, mergedElementLayout);

    const result = {
        ...base,
        ...sessionState,
        darkMode: savedTheme ?? (typeof sessionState.darkMode === 'boolean' ? sessionState.darkMode : false),
        designTitleManual: Boolean(sessionState.designTitleManual),
        content: normalizedContent,
        elementLayout: mergedElementLayout,
        customElements: normalizeCustomElements(sessionState.customElements, mergedElementLayout),
        userUploadedImages: normalizeUserUploadedImages(sessionState.userUploadedImages),
        designSurface: normalizeDesignSurface(sessionState.designSurface),
    };

    // LOG: Estado devuelto por buildInitialState
    // eslint-disable-next-line no-console
    console.log('[buildInitialState] result:', result);

    return result;
}

function normalizeDesignSurface(designSurface) {
    if (!designSurface || typeof designSurface !== 'object') {
        return null;
    }

    const width = Number(designSurface.width ?? 0);
    const height = Number(designSurface.height ?? 0);

    if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
        return null;
    }

    return { width, height };
}

function normalizeCustomElements(customElements, elementLayout) {
    if (!customElements) return {};

    if (!Array.isArray(customElements)) {
        return Object.fromEntries(
            Object.entries(customElements).map(([id, element]) => [
                id,
                {
                    ...(element ?? {}),
                    id: String((element ?? {}).id ?? id),
                    src: normalizeUploadedAssetUrl((element ?? {}).src),
                    assetId: (element ?? {}).assetId ? String((element ?? {}).assetId) : null,
                    pendingDataUrl: typeof (element ?? {}).pendingDataUrl === 'string' ? (element ?? {}).pendingDataUrl : null,
                    storagePath: typeof (element ?? {}).storagePath === 'string' ? (element ?? {}).storagePath : null,
                    uploadStatus: typeof (element ?? {}).uploadStatus === 'string' ? (element ?? {}).uploadStatus : null,
                    needsUpload: Boolean((element ?? {}).needsUpload),
                    intrinsicWidth: Number((element ?? {}).intrinsicWidth ?? 0) || null,
                    intrinsicHeight: Number((element ?? {}).intrinsicHeight ?? 0) || null,
                },
            ])
        );
    }

    const layoutCustomIds = Object.keys(elementLayout ?? {}).filter((id) => !BASE_LAYOUT_KEYS.has(id));
    const normalized = {};

    customElements.forEach((element, index) => {
        if (!element || typeof element !== 'object') return;
        const candidateId = element.id ?? layoutCustomIds[index] ?? `legacy-${index}`;
        normalized[String(candidateId)] = {
            ...element,
            id: String(candidateId),
            src: normalizeUploadedAssetUrl(element.src),
            assetId: element.assetId ? String(element.assetId) : null,
            pendingDataUrl: typeof element.pendingDataUrl === 'string' ? element.pendingDataUrl : null,
            storagePath: typeof element.storagePath === 'string' ? element.storagePath : null,
            uploadStatus: typeof element.uploadStatus === 'string' ? element.uploadStatus : null,
            needsUpload: Boolean(element.needsUpload),
            intrinsicWidth: Number(element.intrinsicWidth ?? 0) || null,
            intrinsicHeight: Number(element.intrinsicHeight ?? 0) || null,
        };
    });

    return normalized;
}

function normalizeUserUploadedImages(userUploadedImages) {
    if (!Array.isArray(userUploadedImages)) {
        return [];
    }

    const seen = new Set();

    return userUploadedImages
        .filter((image) => image && typeof image === 'object')
        .map((image, index) => ({
            id: String(image.id ?? image.assetId ?? `upload-${index}`),
            assetId: String(image.assetId ?? image.id ?? `upload-${index}`),
            label: image.label == null ? 'Subida' : String(image.label),
            src: image.src == null ? '' : normalizeUploadedAssetUrl(String(image.src)),
            pendingDataUrl: typeof image.pendingDataUrl === 'string' ? image.pendingDataUrl : null,
            storagePath: typeof image.storagePath === 'string' ? image.storagePath : null,
            uploadStatus: typeof image.uploadStatus === 'string' ? image.uploadStatus : 'done',
            needsUpload: Boolean(image.needsUpload),
            errorMessage: image.errorMessage == null ? null : String(image.errorMessage),
            intrinsicWidth: Number(image.intrinsicWidth ?? 0) || null,
            intrinsicHeight: Number(image.intrinsicHeight ?? 0) || null,
        }))
        .filter((image) => {
            const key = image.storagePath || image.src || image.assetId || image.id;
            if (!key || seen.has(key)) {
                return false;
            }

            seen.add(key);
            return true;
        });
}

function normalizeContentStrings(content) {
    const normalized = {};

    Object.entries(content).forEach(([key, value]) => {
        normalized[key] = value == null ? '' : String(value);
    });

    return normalized;
}

function mergeElementLayout(defaultLayout, sessionLayout) {
    const merged = structuredClone(defaultLayout);

    Object.entries(sessionLayout).forEach(([key, value]) => {
        merged[key] = {
            ...(merged[key] ?? {}),
            ...value,
        };

        if (key === 'background' && merged[key]) {
            merged[key].backgroundImageSrc = normalizeUploadedAssetUrl(merged[key].backgroundImageSrc);
            merged[key].backgroundImageCropScale = Number(merged[key].backgroundImageCropScale ?? 1);
            merged[key].backgroundImageCropOffsetX = Number(merged[key].backgroundImageCropOffsetX ?? 0);
            merged[key].backgroundImageCropOffsetY = Number(merged[key].backgroundImageCropOffsetY ?? 0);
            merged[key].backgroundImageFlipX = Boolean(merged[key].backgroundImageFlipX);
            merged[key].backgroundImageFlipY = Boolean(merged[key].backgroundImageFlipY);
            merged[key].backgroundImageOpacity = Number(merged[key].backgroundImageOpacity ?? 100);
            merged[key].backgroundImageTransparencyType = merged[key].backgroundImageTransparencyType ?? 'flat';
            merged[key].backgroundImageTransparencyFadeOpacity = Number(merged[key].backgroundImageTransparencyFadeOpacity ?? 0);
            merged[key].backgroundImageTransparencyCenterX = Number(merged[key].backgroundImageTransparencyCenterX ?? 50);
            merged[key].backgroundImageTransparencyCenterY = Number(merged[key].backgroundImageTransparencyCenterY ?? 50);
            merged[key].backgroundImageTransparencyRadius = Number(merged[key].backgroundImageTransparencyRadius ?? 70);
            merged[key].backgroundImageTransparencyRadiusX = Number(merged[key].backgroundImageTransparencyRadiusX ?? 70);
            merged[key].backgroundImageTransparencyRadiusY = Number(merged[key].backgroundImageTransparencyRadiusY ?? 45);
            merged[key].backgroundImageTransparencyRotation = Number(merged[key].backgroundImageTransparencyRotation ?? 0);
            merged[key].backgroundImageTransparencyStartX = Number(merged[key].backgroundImageTransparencyStartX ?? 0);
            merged[key].backgroundImageTransparencyStartY = Number(merged[key].backgroundImageTransparencyStartY ?? 50);
            merged[key].backgroundImageTransparencyEndX = Number(merged[key].backgroundImageTransparencyEndX ?? 100);
            merged[key].backgroundImageTransparencyEndY = Number(merged[key].backgroundImageTransparencyEndY ?? 50);
            merged[key].backgroundImageTransparencyEasing = merged[key].backgroundImageTransparencyEasing ?? 'linear';
        }

        if (merged[key]) {
            merged[key].imageCropScale = Number(merged[key].imageCropScale ?? 1);
            merged[key].imageCropOffsetX = Number(merged[key].imageCropOffsetX ?? 0);
            merged[key].imageCropOffsetY = Number(merged[key].imageCropOffsetY ?? 0);
            merged[key].flipX = Boolean(merged[key].flipX);
            merged[key].flipY = Boolean(merged[key].flipY);
            merged[key].borderRadius = Number(merged[key].borderRadius ?? 12);
            merged[key].borderRadiusTopLeft = merged[key].borderRadiusTopLeft == null ? null : Number(merged[key].borderRadiusTopLeft);
            merged[key].borderRadiusTopRight = merged[key].borderRadiusTopRight == null ? null : Number(merged[key].borderRadiusTopRight);
            merged[key].borderRadiusBottomRight = merged[key].borderRadiusBottomRight == null ? null : Number(merged[key].borderRadiusBottomRight);
            merged[key].borderRadiusBottomLeft = merged[key].borderRadiusBottomLeft == null ? null : Number(merged[key].borderRadiusBottomLeft);
            merged[key].transparencyType = merged[key].transparencyType ?? 'flat';
            merged[key].transparencyFadeOpacity = Number(merged[key].transparencyFadeOpacity ?? 0);
            merged[key].transparencyCenterX = Number(merged[key].transparencyCenterX ?? 50);
            merged[key].transparencyCenterY = Number(merged[key].transparencyCenterY ?? 50);
            merged[key].transparencyRadius = Number(merged[key].transparencyRadius ?? 70);
            merged[key].transparencyRadiusX = Number(merged[key].transparencyRadiusX ?? 70);
            merged[key].transparencyRadiusY = Number(merged[key].transparencyRadiusY ?? 45);
            merged[key].transparencyRotation = Number(merged[key].transparencyRotation ?? 0);
            merged[key].transparencyStartX = Number(merged[key].transparencyStartX ?? 0);
            merged[key].transparencyStartY = Number(merged[key].transparencyStartY ?? 50);
            merged[key].transparencyEndX = Number(merged[key].transparencyEndX ?? 100);
            merged[key].transparencyEndY = Number(merged[key].transparencyEndY ?? 50);
            merged[key].transparencyEasing = merged[key].transparencyEasing ?? 'linear';
        }
    });

    return merged;
}

function bootstrapPersistence(saveEndpoint) {
    watch(
        () => designerState.darkMode,
        (darkMode) => {
            setThemePreference(darkMode);
        },
        { flush: 'sync' }
    );

    // Guardado automático desactivado para evitar múltiples PUT; el guardado lo controla el editor
}

function isPersistableDesignerStateSnapshot(snapshot) {
    return Boolean(
        snapshot
        && typeof snapshot === 'object'
        && typeof snapshot.darkMode === 'boolean'
        && typeof snapshot.mode === 'string'
        && snapshot.content
        && typeof snapshot.content === 'object'
        && snapshot.elementLayout
        && typeof snapshot.elementLayout === 'object'
        && snapshot.elementLayout.background
        && snapshot.elementLayout.title
        && (snapshot.customElements == null || typeof snapshot.customElements === 'object')
        && (snapshot.userUploadedImages == null || Array.isArray(snapshot.userUploadedImages))
    );
}

async function persistStateSnapshot(saveEndpoint, snapshot) {
    if (!isPersistableDesignerStateSnapshot(snapshot)) {
        return;
    }

    if (!snapshot.currentDesignUuid && currentHydratedDesignUuid) {
        snapshot.currentDesignUuid = currentHydratedDesignUuid;
    }

    if (currentRequestIsAuthenticated && !snapshot.currentDesignUuid) {
        return;
    }

    // Si el usuario es invitado y hay miniatura, incluirla en la petición
    let payload = { state: snapshot, ...persistenceMeta };
    if (!currentRequestIsAuthenticated && snapshot.thumbnailDataUrl) {
        payload.thumbnailDataUrl = snapshot.thumbnailDataUrl;
    }

    queuedSave = { saveEndpoint, snapshot, meta: { ...persistenceMeta } };

    if (saveInFlight) {
        return;
    }

    saveInFlight = true;

    try {
        while (queuedSave) {
            const next = queuedSave;
            queuedSave = null;
            // Usar el payload correcto para invitados
            let reqPayload = { state: next.snapshot, ...next.meta };
            if (!currentRequestIsAuthenticated && next.snapshot.thumbnailDataUrl) {
                reqPayload.thumbnailDataUrl = next.snapshot.thumbnailDataUrl;
            }
            const response = await axios.put(next.saveEndpoint, reqPayload);

            if (designerState && response?.data?.designUuid) {
                designerState.currentDesignUuid = response.data.designUuid;
                currentHydratedDesignUuid = response.data.designUuid;
            }

            if (next.meta?.thumbnailDataUrl && persistenceMeta.thumbnailDataUrl === next.meta.thumbnailDataUrl) {
                persistenceMeta.thumbnailDataUrl = null;
            }
        }
    } finally {
        saveInFlight = false;
    }
}

export async function flushDesignerStatePersistence() {
    if (!designerState) {
        return;
    }

    clearTimeout(saveTimer);
    saveTimer = null;

    const snapshot = JSON.parse(JSON.stringify(designerState));
    // Copiar la miniatura más reciente generada (si existe) al snapshot antes de guardar
    if (persistenceMeta.thumbnailDataUrl) {
        snapshot.thumbnailDataUrl = persistenceMeta.thumbnailDataUrl;
        if (persistenceMeta.thumbnailHash) {
            snapshot.thumbnailHash = persistenceMeta.thumbnailHash;
        }
    }
    // LOG: Estado a guardar
    // eslint-disable-next-line no-console
    console.log('[flushDesignerStatePersistence] snapshot a guardar:', snapshot);
    const resp = await persistStateSnapshot(currentSaveEndpoint, snapshot);
    // LOG: Respuesta del backend tras guardar
    // eslint-disable-next-line no-console
    console.log('[flushDesignerStatePersistence] respuesta backend:', resp);
}

export function setDesignerThumbnailDataUrl(dataUrl, hash) {
    persistenceMeta.thumbnailDataUrl = dataUrl;
    persistenceMeta.thumbnailHash = hash ?? null;
}

// Sincroniza los campos title, subtitle, meta, contact, extra entre content y elementLayout
function syncContentAndElementLayout(content, elementLayout) {
    for (const key of ['title','subtitle','meta','contact','extra']) {
        if (
            elementLayout[key] &&
            typeof elementLayout[key].text === 'string' &&
            elementLayout[key].text !== '' &&
            (!content[key] || content[key] === '')
        ) {
            content[key] = elementLayout[key].text;
        }
        if (
            content[key] && content[key] !== '' &&
            elementLayout[key] &&
            (typeof elementLayout[key].text !== 'string' || elementLayout[key].text === '')
        ) {
            elementLayout[key].text = content[key];
        }
    }
}
