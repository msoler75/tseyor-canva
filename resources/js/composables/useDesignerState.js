import { reactive, watch } from 'vue';
import { usePage } from '@inertiajs/vue3';
import axios from 'axios';
import { initialDesignerState } from '../data/designer';

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

export function useDesignerState() {
    const page = usePage();
    const sessionState = page.props.designer?.state ?? null;
    const saveEndpoint = page.props.designer?.endpoints?.save ?? '/designer/state';
    const incomingDesignUuid = sessionState?.currentDesignUuid ?? page.props.designer?.currentDesign?.uuid ?? null;
    currentSaveEndpoint = saveEndpoint;
    currentRequestIsAuthenticated = Boolean(page.props.auth?.user);

    if (!designerState) {
        designerState = reactive(buildInitialState(sessionState));
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

export function resetDesignerState() {
    const fresh = buildInitialState(null);
    currentHydratedDesignUuid = null;

    if (!designerState) {
        designerState = reactive(fresh);
        return designerState;
    }

    Object.keys(designerState).forEach((key) => {
        delete designerState[key];
    });

    Object.assign(designerState, fresh);

    return designerState;
}

function buildInitialState(sessionState) {
    const savedTheme = localStorage.getItem('tseyor-theme');
    const base = {
        ...initialDesignerState,
        content: { ...initialDesignerState.content },
        elementLayout: structuredClone(initialDesignerState.elementLayout),
    };

    if (!sessionState) {
        base.darkMode = savedTheme === 'dark';
        return base;
    }

    const mergedElementLayout = mergeElementLayout(base.elementLayout, sessionState.elementLayout ?? {});

    return {
        ...base,
        ...sessionState,
        darkMode: typeof sessionState.darkMode === 'boolean' ? sessionState.darkMode : savedTheme === 'dark',
        designTitleManual: Boolean(sessionState.designTitleManual),
        content: {
            ...base.content,
            ...normalizeContentStrings(sessionState.content ?? {}),
        },
        elementLayout: mergedElementLayout,
        customElements: normalizeCustomElements(sessionState.customElements, mergedElementLayout),
        userUploadedImages: normalizeUserUploadedImages(sessionState.userUploadedImages),
        designSurface: normalizeDesignSurface(sessionState.designSurface),
    };
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
        }));
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
        designerState,
        () => {
            localStorage.setItem('tseyor-theme', designerState.darkMode ? 'dark' : 'light');

            clearTimeout(saveTimer);
            saveTimer = setTimeout(async () => {
                try {
                    const snapshot = JSON.parse(JSON.stringify(designerState));
                    await persistStateSnapshot(saveEndpoint, snapshot);
                } catch (error) {
                    console.error('Failed to persist designer session state', error);
                }
            }, 250);
        },
        { deep: true }
    );
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

    queuedSave = { saveEndpoint, snapshot, meta: { ...persistenceMeta } };

    if (saveInFlight) {
        return;
    }

    saveInFlight = true;

    try {
        while (queuedSave) {
            const next = queuedSave;
            queuedSave = null;
            const response = await axios.put(next.saveEndpoint, { state: next.snapshot, ...next.meta });

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
    await persistStateSnapshot(currentSaveEndpoint, snapshot);
}

export function setDesignerThumbnailDataUrl(dataUrl) {
    persistenceMeta.thumbnailDataUrl = dataUrl;
}
