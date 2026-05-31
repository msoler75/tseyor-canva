import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

vi.mock('@inertiajs/vue3', () => ({
  usePage: vi.fn(() => ({
    props: {
      designer: {
        endpoints: { save: '/designer/state' },
      },
      auth: { user: null },
    },
  })),
}));

vi.mock('axios');
vi.mock('../useThemePreference', () => ({
  setThemePreference: vi.fn(),
  readThemePreference: vi.fn(() => false),
}));

import { usePage } from '@inertiajs/vue3';

let useDesignerState, resetDesignerState, hydrateDesignerStateFromPage, toggleDesignerDarkMode;
let initialDesignerState;

beforeEach(async () => {
  vi.resetModules();
  vi.stubGlobal('readThemePreference', vi.fn(() => false));
  const mod = await import('../useDesignerState');
  useDesignerState = mod.useDesignerState;
  resetDesignerState = mod.resetDesignerState;
  hydrateDesignerStateFromPage = mod.hydrateDesignerStateFromPage;
  toggleDesignerDarkMode = mod.toggleDesignerDarkMode;
  const data = await import('../../data/designer');
  initialDesignerState = data.initialDesignerState;
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('useDesignerState', () => {
  it('returns a reactive state object', () => {
    const state = useDesignerState();
    expect(state).toBeDefined();
    expect(state.mode).toBe('guided');
    expect(typeof state.content).toBe('object');
    expect(typeof state.elementLayout).toBe('object');
  });

  it('returns the same singleton on repeated calls', () => {
    const a = useDesignerState();
    const b = useDesignerState();
    expect(a).toBe(b);
  });

  it('hydrates from page props when forceRehydrate is set', () => {
    const state = useDesignerState({ forceRehydrate: true });
    expect(state).toBeDefined();
  });

  it('hydrates from overrideState when provided', () => {
    const override = {
      mode: 'direct',
      content: { title: 'Override Title' },
      elementLayout: {},
      customElements: {},
    };
    const state = useDesignerState({ forceRehydrate: true, overrideState: override });
    expect(state.mode).toBe('direct');
    expect(state.content.title).toBe('Override Title');
  });

  it('sets currentDesignUuid when design UUID is in page props state', () => {
    usePage.mockReturnValue({
      props: {
        designer: {
          endpoints: { save: '/designer/state' },
          currentDesign: { uuid: 'abc-123' },
          state: { currentDesignUuid: 'abc-123' },
        },
        auth: { user: { id: 1 } },
      },
    });
    const state = useDesignerState({ forceRehydrate: true });
    expect(state.currentDesignUuid).toBe('abc-123');
  });
});

describe('resetDesignerState', () => {
  it('resets state to initial values', () => {
    const state = useDesignerState();
    state.mode = 'direct';
    state.content.title = 'Modified';
    resetDesignerState();
    expect(state.mode).toBe('guided');
    expect(state.content.title).toBe('');
  });

  it('returns the reset state', () => {
    const result = resetDesignerState();
    expect(result.mode).toBe('guided');
  });
});

describe('toggleDesignerDarkMode', () => {
  it('toggles dark mode', () => {
    const result = toggleDesignerDarkMode();
    expect(typeof result).toBe('boolean');
  });
});
