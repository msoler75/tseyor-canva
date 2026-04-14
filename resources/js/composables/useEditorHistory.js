import { computed, nextTick, onBeforeUnmount, ref } from 'vue';

const HISTORY_LIMIT = 80;

const cloneSnapshotValue = (value) => {
  try {
    return structuredClone(value);
  } catch {
    return JSON.parse(JSON.stringify(value));
  }
};

const isPlainObject = (value) => Object.prototype.toString.call(value) === '[object Object]';

const collectChangedPaths = (previousValue, nextValue, basePath = '', changedPaths = new Set()) => {
  if (previousValue === nextValue) return changedPaths;

  const previousIsArray = Array.isArray(previousValue);
  const nextIsArray = Array.isArray(nextValue);
  const previousIsObject = isPlainObject(previousValue);
  const nextIsObject = isPlainObject(nextValue);

  if ((previousIsArray && nextIsArray) || (previousIsObject && nextIsObject)) {
    const keys = new Set([
      ...Object.keys(previousValue ?? {}),
      ...Object.keys(nextValue ?? {}),
    ]);

    if (!keys.size && basePath) {
      changedPaths.add(basePath);
      return changedPaths;
    }

    keys.forEach((key) => {
      const nextPath = basePath ? `${basePath}.${key}` : String(key);
      collectChangedPaths(previousValue?.[key], nextValue?.[key], nextPath, changedPaths);
    });

    return changedPaths;
  }

  changedPaths.add(basePath || '__root__');
  return changedPaths;
};

export const useEditorHistory = ({
  state,
  editingElementId,
  commitTextEdit,
  clearSelection,
  baseElementLabels,
  contentFieldLabels,
}) => {
  const historyStack = ref([]);
  const historyMeta = ref([]);
  const historyIndex = ref(-1);
  const historyApplying = ref(false);
  const historyMuted = ref(false);
  let historyTimer = null;

  const buildHistorySnapshot = () => ({
    content: cloneSnapshotValue(state.content ?? {}),
    elementLayout: cloneSnapshotValue(state.elementLayout ?? {}),
    customElements: cloneSnapshotValue(state.customElements ?? {}),
  });

  const getHistoryElementLabel = (snapshot, elementId) => {
    if (baseElementLabels[elementId]) {
      return baseElementLabels[elementId];
    }

    const customLabel = snapshot?.customElements?.[elementId]?.label;
    if (customLabel) {
      return String(customLabel).trim().toLowerCase();
    }

    return 'elemento';
  };

  const buildHistoryGroupKey = (previousSnapshot, nextSnapshot) => {
    const normalizeHistoryPath = (path) => {
      const parts = String(path).split('.');
      if (!parts.length) return path;

      if (parts[0] === 'elementLayout' && parts.length >= 3) {
        const elementId = parts[1];
        const field = parts[2];

        if (field === 'x' || field === 'y') {
          return `elementLayout.${elementId}.position`;
        }

        if (field === 'w' || field === 'h') {
          return `elementLayout.${elementId}.size`;
        }

        if (field === 'paragraphStyles' && parts.length >= 5) {
          const styleField = parts[4];
          return `elementLayout.${elementId}.paragraphStyles.${styleField}`;
        }

        return `elementLayout.${elementId}.${field}`;
      }

      if (parts[0] === 'customElements' && parts.length >= 3) {
        return `customElements.${parts[1]}.${parts[2]}`;
      }

      if (parts[0] === 'content' && parts.length >= 2) {
        return `content.${parts[1]}`;
      }

      return path;
    };

    const changedPaths = [...collectChangedPaths(previousSnapshot ?? {}, nextSnapshot ?? {})]
      .filter((path) => path && path !== '__root__')
      .map((path) => normalizeHistoryPath(path))
      .sort();

    return changedPaths.length ? changedPaths.join('|') : '__noop__';
  };

  const buildHistoryActionLabel = (groupKey, snapshot) => {
    if (!groupKey || groupKey === '__initial__' || groupKey === '__noop__') {
      return 'inicio';
    }

    const paths = groupKey.split('|').filter(Boolean);
    if (!paths.length) return 'edicion';

    const [firstPath] = paths;
    const parts = firstPath.split('.');

    if (parts[0] === 'elementLayout' && parts.length >= 3) {
      const elementLabel = getHistoryElementLabel(snapshot, parts[1]);
      const field = parts[2];

      if (field === 'position') return `mover ${elementLabel}`;
      if (field === 'size') return `tamano ${elementLabel}`;
      if (field === 'rotation') return `rotacion ${elementLabel}`;
      if (field === 'fontSize') return `tamano texto ${elementLabel}`;
      if (field === 'paragraphStyles' && parts[3] === 'fontSize') return `tamano texto ${elementLabel}`;
      if (field === 'color' || (field === 'paragraphStyles' && parts[3] === 'color')) return `color ${elementLabel}`;
      if (field === 'zIndex') return `orden ${elementLabel}`;
      if (parts[1] === 'background') return 'fondo';
      return `editar ${elementLabel}`;
    }

    if (parts[0] === 'content' && parts.length >= 2) {
      const label = contentFieldLabels[parts[1]] ?? 'contenido';
      return `texto ${label}`;
    }

    if (parts[0] === 'customElements' && parts.length >= 3) {
      const elementLabel = getHistoryElementLabel(snapshot, parts[1]);
      if (parts[2] === 'text') return `texto ${elementLabel}`;
      if (parts[2] === 'src') return `imagen ${elementLabel}`;
      return `editar ${elementLabel}`;
    }

    return 'edicion';
  };

  const canUndo = computed(() => historyIndex.value > 0);
  const canRedo = computed(() => historyIndex.value >= 0 && historyIndex.value < historyStack.value.length - 1);
  const undoActionLabel = computed(() => canUndo.value ? (historyMeta.value[historyIndex.value]?.label ?? 'edición') : 'nada');
  const redoActionLabel = computed(() => canRedo.value ? (historyMeta.value[historyIndex.value + 1]?.label ?? 'edición') : 'nada');

  const pushHistorySnapshot = (options = {}) => {
    const { force = false, allowCoalesce = false } = options;
    if (historyApplying.value || historyMuted.value) return;

    const snapshot = buildHistorySnapshot();
    const serializedSnapshot = JSON.stringify(snapshot);
    const currentSnapshot = historyStack.value[historyIndex.value] ?? null;

    if (!force && currentSnapshot && JSON.stringify(currentSnapshot) === serializedSnapshot) {
      return;
    }

    const groupKey = currentSnapshot ? buildHistoryGroupKey(currentSnapshot, snapshot) : '__initial__';
    const actionLabel = buildHistoryActionLabel(groupKey, snapshot);
    const currentMeta = historyMeta.value[historyIndex.value] ?? null;
    const isAtHistoryHead = historyIndex.value === historyStack.value.length - 1;
    const canCoalesce = !force && allowCoalesce && isAtHistoryHead && historyIndex.value > 0 && currentMeta?.groupKey === groupKey;

    if (canCoalesce) {
      historyStack.value[historyIndex.value] = snapshot;
      historyMeta.value[historyIndex.value] = { groupKey, label: actionLabel };
      return;
    }

    if (historyIndex.value < historyStack.value.length - 1) {
      historyStack.value.splice(historyIndex.value + 1);
      historyMeta.value.splice(historyIndex.value + 1);
    }

    historyStack.value.push(snapshot);
    historyMeta.value.push({ groupKey, label: actionLabel });

    if (historyStack.value.length > HISTORY_LIMIT) {
      const extraItems = historyStack.value.length - HISTORY_LIMIT;
      historyStack.value.splice(0, extraItems);
      historyMeta.value.splice(0, extraItems);
    }

    historyIndex.value = historyStack.value.length - 1;
  };

  const scheduleHistorySnapshot = () => {
    if (historyApplying.value || historyMuted.value) return;

    if (historyTimer) {
      clearTimeout(historyTimer);
    }

    historyTimer = setTimeout(() => {
      pushHistorySnapshot({ allowCoalesce: true });
      historyTimer = null;
    }, 180);
  };

  const applyHistorySnapshot = (snapshot) => {
    historyApplying.value = true;

    state.content = cloneSnapshotValue(snapshot.content ?? {});
    state.elementLayout = cloneSnapshotValue(snapshot.elementLayout ?? {});
    state.customElements = Object.fromEntries(Object.entries(cloneSnapshotValue(snapshot.customElements ?? {})));

    const selectedId = state.selectedElementId;
    if (selectedId && selectedId !== 'background' && !state.elementLayout[selectedId]) {
      clearSelection();
    }

    nextTick(() => {
      historyApplying.value = false;
    });
  };

  const replaceImageAssetSource = ({ assetId = null, previousSrc = null, nextSrc, storagePath = null }) => {
    if (!nextSrc) return;

    historyStack.value = historyStack.value.map((snapshot) => {
      const nextSnapshot = cloneSnapshotValue(snapshot);

      Object.entries(nextSnapshot.customElements ?? {}).forEach(([id, element]) => {
        if (!element || element.type !== 'image') return;

        const sameAsset = assetId && element.assetId === assetId;
        const sameSource = previousSrc && (element.src === previousSrc || element.pendingDataUrl === previousSrc);

        if (!sameAsset && !sameSource) {
          return;
        }

        nextSnapshot.customElements[id] = {
          ...element,
          src: nextSrc,
          pendingDataUrl: null,
          storagePath,
          needsUpload: false,
        };
      });

      return nextSnapshot;
    });
  };

  const mutateWithoutHistory = async (callback) => {
    historyMuted.value = true;

    try {
      callback();
      await nextTick();
    } finally {
      historyMuted.value = false;
    }
  };

  const performUndo = () => {
    if (!canUndo.value) return;

    if (editingElementId.value) {
      commitTextEdit();
    }

    historyIndex.value -= 1;
    const snapshot = historyStack.value[historyIndex.value];
    if (snapshot) {
      applyHistorySnapshot(snapshot);
    }
  };

  const performRedo = () => {
    if (!canRedo.value) return;

    if (editingElementId.value) {
      commitTextEdit();
    }

    historyIndex.value += 1;
    const snapshot = historyStack.value[historyIndex.value];
    if (snapshot) {
      applyHistorySnapshot(snapshot);
    }
  };

  onBeforeUnmount(() => {
    if (historyTimer) {
      clearTimeout(historyTimer);
      historyTimer = null;
    }
  });

  return {
    historyApplying,
    canUndo,
    canRedo,
    undoActionLabel,
    redoActionLabel,
    pushHistorySnapshot,
    scheduleHistorySnapshot,
    performUndo,
    performRedo,
    replaceImageAssetSource,
    mutateWithoutHistory,
  };
};
