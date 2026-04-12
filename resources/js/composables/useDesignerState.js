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

export function useDesignerState() {
    const page = usePage();
    const sessionState = page.props.designer?.state ?? null;
    const saveEndpoint = page.props.designer?.endpoints?.save ?? '/designer/state';

    if (!designerState) {
        designerState = reactive(buildInitialState(sessionState));
    }

    if (!persistenceBootstrapped) {
        persistenceBootstrapped = true;
        bootstrapPersistence(saveEndpoint);
    }

    return designerState;
}

export function resetDesignerState() {
    const fresh = buildInitialState(null);

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
        content: {
            ...base.content,
            ...normalizeContentStrings(sessionState.content ?? {}),
        },
        elementLayout: mergedElementLayout,
        customElements: normalizeCustomElements(sessionState.customElements, mergedElementLayout),
    };
}

function normalizeCustomElements(customElements, elementLayout) {
    if (!customElements) return {};

    if (!Array.isArray(customElements)) {
        return Object.fromEntries(
            Object.entries(customElements).map(([id, element]) => [
                id,
                { ...(element ?? {}), id: String((element ?? {}).id ?? id) },
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
        };
    });

    return normalized;
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
                    delete snapshot.userUploadedImages;
                    await persistStateSnapshot(saveEndpoint, snapshot);
                } catch (error) {
                    console.error('Failed to persist designer session state', error);
                }
            }, 250);
        },
        { deep: true }
    );
}

async function persistStateSnapshot(saveEndpoint, snapshot) {
    queuedSave = { saveEndpoint, snapshot };

    if (saveInFlight) {
        return;
    }

    saveInFlight = true;

    try {
        while (queuedSave) {
            const next = queuedSave;
            queuedSave = null;
            await axios.put(next.saveEndpoint, { state: next.snapshot });
        }
    } finally {
        saveInFlight = false;
    }
}
