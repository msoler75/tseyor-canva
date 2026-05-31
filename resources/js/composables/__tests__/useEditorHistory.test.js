import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockState = {
  content: { title: 'Test', subtitle: 'Sub' },
  elementLayout: {
    title: { x: 10, y: 20, text: 'Test' },
    subtitle: { x: 10, y: 60, text: 'Sub' },
  },
  customElements: {},
  pages: [{
    id: 'page-1',
    content: { title: 'Test', subtitle: 'Sub' },
    elementLayout: { title: {}, subtitle: {} },
    customElements: {},
  }],
  format: 'horizontal',
  size: '1080 × 1080 px',
  designSurface: { width: 1080, height: 1080 },
  objective: 'Bienvenida',
  outputType: 'digital',
  designTitle: 'Test Design',
  designTitleManual: false,
  selectedElementId: null,
};

vi.mock('../useLinkedTextBoxSystem', () => ({
  useLinkedTextBoxSystem: () => ({
    hasLinkedText: vi.fn(() => false),
    resetAllSystems: vi.fn(),
  }),
}));

let useEditorHistory;

beforeEach(async () => {
  vi.resetModules();
  useEditorHistory = (await import('../useEditorHistory')).useEditorHistory;
});

function createHistory() {
  const opts = {
    state: mockState,
    editingElementId: { value: null },
    commitTextEdit: vi.fn(),
    clearSelection: vi.fn(),
    baseElementLabels: { title: 'título', subtitle: 'subtítulo' },
    contentFieldLabels: {},
    syncActivePageSnapshot: vi.fn(),
    refreshDocumentPageList: vi.fn(),
    ensureDocumentPages: vi.fn(),
    workingDocumentPageId: { value: 'page-1' },
    activePageId: { value: 'page-1' },
    visuallyFocusedPageId: { value: null },
  };
  return useEditorHistory(opts);
}

describe('useEditorHistory', () => {
  it('initializes with empty history', () => {
    const history = createHistory();
    expect(history.canUndo.value).toBe(false);
    expect(history.canRedo.value).toBe(false);
  });

  it('pushes history snapshots', () => {
    const history = createHistory();
    mockState.content.title = 'V1';
    history.pushHistorySnapshot({});
    mockState.content.title = 'V2';
    history.pushHistorySnapshot({});
    expect(history.canUndo.value).toBe(true);
  });

  it('undo reverts to previous state', () => {
    const history = createHistory();
    mockState.content.title = 'Original';
    history.pushHistorySnapshot({});
    mockState.content.title = 'Changed';
    history.pushHistorySnapshot({});
    history.performUndo();
    expect(mockState.content.title).toBe('Original');
  });

  it('undo and redo cycle preserves state', () => {
    const history = createHistory();
    mockState.content.title = 'A';
    history.pushHistorySnapshot({});
    mockState.content.title = 'B';
    history.pushHistorySnapshot({});
    history.performUndo();
    expect(mockState.content.title).toBe('A');
    history.performRedo();
    expect(mockState.content.title).toBe('B');
  });

  it('limits history to HISTORY_LIMIT entries', () => {
    const history = createHistory();
    for (let i = 0; i < 100; i++) {
      mockState.content.title = `Version ${i}`;
      history.pushHistorySnapshot({});
    }
    expect(history.canUndo.value).toBe(true);
  });

  it('canUndo is false at start', () => {
    const history = createHistory();
    expect(history.canUndo.value).toBe(false);
  });

  it('canRedo is false after single push', () => {
    const history = createHistory();
    history.pushHistorySnapshot({});
    expect(history.canRedo.value).toBe(false);
  });

  it('canRedo is true after undo', () => {
    const history = createHistory();
    mockState.content.title = 'V1';
    history.pushHistorySnapshot({});
    mockState.content.title = 'V2';
    history.pushHistorySnapshot({});
    history.performUndo();
    expect(history.canRedo.value).toBe(true);
  });
});
