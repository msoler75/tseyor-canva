import { reactive, watch } from 'vue';
import { usePage } from '@inertiajs/vue3';
import axios from 'axios';
import { initialDesignerState } from '../data/designer';

let designerState;
let persistenceBootstrapped = false;
let saveTimer;

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

    return {
        ...base,
        ...sessionState,
        darkMode: typeof sessionState.darkMode === 'boolean' ? sessionState.darkMode : savedTheme === 'dark',
        content: {
            ...base.content,
            ...(sessionState.content ?? {}),
        },
        elementLayout: mergeElementLayout(base.elementLayout, sessionState.elementLayout ?? {}),
    };
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
                    await axios.put(saveEndpoint, {
                        state: JSON.parse(JSON.stringify(designerState)),
                    });
                } catch (error) {
                    console.error('Failed to persist designer session state', error);
                }
            }, 250);
        },
        { deep: true }
    );
}
