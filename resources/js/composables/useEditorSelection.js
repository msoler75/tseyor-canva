import { computed } from 'vue';

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
const SELECTION_MARQUEE_CLICK_THRESHOLD = 3;

export const useEditorSelection = ({
  state,
  editorElements,
  groupedElements,
  selectedGroupId,
  multiSelectionIds,
  marqueePreviewIds,
  selectionMarquee,
  activePropertyPanel,
  elementMeasurements,
  canvasRef,
  editingElementId,
  commitTextEdit,
  setDragDocumentState,
  getEstimatedTextHeight,
  getElementText,
  ensureParagraphStyles,
  isTextElement,
}) => {
  const selectedElement = computed(() => state.elementLayout[state.selectedElementId]);
  const hasSelection = computed(() => Boolean(state.selectedElementId && selectedElement.value));
  const isGroupSelection = computed(() => Boolean(selectedGroupId.value && groupedElements[selectedGroupId.value]));
  const selectedGroup = computed(() => {
    if (!selectedGroupId.value) return null;
    return groupedElements[selectedGroupId.value] ?? null;
  });
  const activeSelectionIds = computed(() => {
    if (isGroupSelection.value) {
      return [...(selectedGroup.value?.elementIds ?? [])];
    }
    if (multiSelectionIds.value.length > 1) {
      return [...multiSelectionIds.value];
    }
    if (state.selectedElementId) {
      return [state.selectedElementId];
    }
    return [];
  });
  const hasMultiSelection = computed(() => activeSelectionIds.value.length > 1);
  const overlayControlTargetId = computed(() => (isGroupSelection.value ? selectedGroupId.value : state.selectedElementId));
  const activeElementLabel = computed(() => {
    if (isGroupSelection.value) {
      return `Grupo (${selectedGroup.value?.elementIds?.length ?? 0})`;
    }
    if (state.selectedElementId === 'background') return 'Fondo';
    return editorElements.value.find((item) => item.id === state.selectedElementId)?.label ?? 'Elemento';
  });
  const selectedElementType = computed(() => editorElements.value.find((item) => item.id === state.selectedElementId)?.type ?? null);
  const hasTextSelection = computed(() => hasSelection.value && selectedElementType.value === 'text');

  const getGroupIdForElement = (id) => {
    for (const [groupId, group] of Object.entries(groupedElements)) {
      if (group.elementIds.includes(id)) return groupId;
    }
    return null;
  };

  const getSelectionBounds = (ids = []) => {
    const bounds = ids.map((id) => {
      const layout = state.elementLayout[id];
      if (!layout) return null;
      const measured = elementMeasurements[id] ?? null;
      const width = measured?.width ?? layout.w ?? 0;
      const height = measured?.height ?? layout.h ?? 44;
      return {
        left: layout.x,
        top: layout.y,
        right: layout.x + width,
        bottom: layout.y + height,
      };
    }).filter(Boolean);

    if (!bounds.length) return null;
    const left = Math.min(...bounds.map((item) => item.left));
    const top = Math.min(...bounds.map((item) => item.top));
    const right = Math.max(...bounds.map((item) => item.right));
    const bottom = Math.max(...bounds.map((item) => item.bottom));
    return {
      x: left,
      y: top,
      w: Math.max(1, right - left),
      h: Math.max(1, bottom - top),
    };
  };

  const isElementSelected = (id) => {
    if (marqueePreviewIds.value.includes(id)) return true;
    if (isGroupSelection.value) {
      return selectedGroup.value?.elementIds?.includes(id) ?? false;
    }
    if (multiSelectionIds.value.length > 1) {
      return multiSelectionIds.value.includes(id);
    }
    return state.selectedElementId === id;
  };

  const clearSelectionMarquee = () => {
    selectionMarquee.active = false;
    selectionMarquee.pointerId = null;
    selectionMarquee.dragged = false;
    selectionMarquee.startX = 0;
    selectionMarquee.startY = 0;
    selectionMarquee.currentX = 0;
    selectionMarquee.currentY = 0;
    marqueePreviewIds.value = [];
  };

  const clearSelection = () => {
    if (editingElementId.value) {
      commitTextEdit();
    }
    selectedGroupId.value = null;
    multiSelectionIds.value = [];
    marqueePreviewIds.value = [];
    state.selectedElementId = null;
    activePropertyPanel.value = null;
  };

  const startSelectionMarquee = (event) => {
    if (!canvasRef.value) return;
    const rect = canvasRef.value.getBoundingClientRect();
    selectionMarquee.active = true;
    selectionMarquee.pointerId = event.pointerId;
    selectionMarquee.dragged = false;
    selectionMarquee.startX = event.clientX - rect.left;
    selectionMarquee.startY = event.clientY - rect.top;
    selectionMarquee.currentX = selectionMarquee.startX;
    selectionMarquee.currentY = selectionMarquee.startY;
    marqueePreviewIds.value = [];
    event.currentTarget?.setPointerCapture?.(event.pointerId);
    setDragDocumentState(true);
  };

  const updateSelectionMarqueePreview = () => {
    const movedDistance = Math.hypot(
      selectionMarquee.currentX - selectionMarquee.startX,
      selectionMarquee.currentY - selectionMarquee.startY,
    );
    if (movedDistance > SELECTION_MARQUEE_CLICK_THRESHOLD) {
      selectionMarquee.dragged = true;
    }

    const left = Math.min(selectionMarquee.startX, selectionMarquee.currentX);
    const top = Math.min(selectionMarquee.startY, selectionMarquee.currentY);
    const right = Math.max(selectionMarquee.startX, selectionMarquee.currentX);
    const bottom = Math.max(selectionMarquee.startY, selectionMarquee.currentY);

    marqueePreviewIds.value = editorElements.value
      .map((item) => {
        const layout = state.elementLayout[item.id];
        if (!layout) return null;
        const measured = elementMeasurements[item.id] ?? null;
        const width = measured?.width ?? layout.w ?? 0;
        const height = measured?.height ?? layout.h ?? 44;
        const intersects = !(
          layout.x + width < left
          || layout.x > right
          || layout.y + height < top
          || layout.y > bottom
        );
        return intersects ? item.id : null;
      })
      .filter(Boolean);
  };

  const finalizeSelectionMarquee = () => {
    const picked = [...new Set(marqueePreviewIds.value)]
      .filter((id) => id !== 'background');
    clearSelectionMarquee();

    if (!picked.length) {
      clearSelection();
      return;
    }

    if (picked.length === 1) {
      selectedGroupId.value = null;
      multiSelectionIds.value = [];
      state.selectedElementId = picked[0];
      return;
    }

    state.selectedElementId = null;
    selectedGroupId.value = null;
    multiSelectionIds.value = picked;
    activePropertyPanel.value = null;
  };

  const selectGroup = (groupId) => {
    if (!groupedElements[groupId]) return;
    const bounds = getSelectionBounds(groupedElements[groupId].elementIds);
    if (bounds) {
      groupedElements[groupId].layout.x = bounds.x;
      groupedElements[groupId].layout.y = bounds.y;
      groupedElements[groupId].layout.w = bounds.w;
      groupedElements[groupId].layout.h = bounds.h;
    }
    selectedGroupId.value = groupId;
    state.selectedElementId = null;
    multiSelectionIds.value = [];
    activePropertyPanel.value = null;
  };

  const buildGroupResizeSnapshot = (groupId) => {
    const group = groupedElements[groupId];
    if (!group) return null;

    return {
      x: group.layout.x,
      y: group.layout.y,
      w: group.layout.w,
      h: group.layout.h,
      members: group.elementIds.map((id) => {
        const layout = state.elementLayout[id];
        if (!layout) return null;
        const measured = elementMeasurements[id] ?? null;
        const measuredHeight = measured?.height ?? layout.h ?? getEstimatedTextHeight(layout, getElementText(id));
        return {
          id,
          isText: isTextElement(id),
          x: layout.x,
          y: layout.y,
          w: layout.w ?? measured?.width ?? 40,
          h: layout.h ?? measuredHeight,
          fontSize: layout.fontSize ?? 16,
          paragraphStyles: ensureParagraphStyles(layout, getElementText(id)).map((style) => ({ ...style })),
        };
      }).filter(Boolean),
    };
  };

  const selectedOverlayStyle = computed(() => {
    const ids = activeSelectionIds.value;
    if (!ids.length) return {};

    const bounds = getSelectionBounds(ids);
    if (!bounds) return {};
    let rotation = 0;
    if (isGroupSelection.value) {
      rotation = Number(selectedGroup.value?.layout?.rotation ?? 0);
    } else if (ids.length === 1) {
      rotation = Number(state.elementLayout[ids[0]]?.rotation ?? 0);
    }

    return {
      left: `${bounds.x}px`,
      top: `${bounds.y}px`,
      width: `${bounds.w}px`,
      height: `${bounds.h}px`,
      zIndex: '6000',
      transform: `rotate(${rotation}deg)`,
      transformOrigin: 'center center',
    };
  });

  const selectedActionBarStyle = computed(() => {
    const ids = activeSelectionIds.value;
    if (!ids.length || state.selectedElementId === 'background') {
      return {};
    }

    const bounds = getSelectionBounds(ids);
    if (!bounds) return {};
    const top = bounds.y - 74;

    return {
      left: `${bounds.x + (bounds.w / 2)}px`,
      top: `${top}px`,
      zIndex: '6100',
      transform: 'translateX(-50%)',
    };
  });

  const selectedHandleMetrics = computed(() => {
    const ids = activeSelectionIds.value;
    const bounds = ids.length ? getSelectionBounds(ids) : null;
    const width = Math.max(1, bounds?.w ?? 120);
    const height = Math.max(1, bounds?.h ?? 120);
    const minSide = Math.min(width, height);

    const cornerSize = clamp(Math.round(minSide * 0.28), 8, 16);
    const sideThickness = clamp(Math.round(minSide * 0.12), 2, 12);
    const sideLength = clamp(Math.round(height * 0.45), 10, 32);
    const barThickness = clamp(Math.round(minSide * 0.12), 2, 10);
    const barLength = clamp(Math.round(width * 0.45), 14, 64);

    return {
      cornerSize: `${cornerSize}px`,
      cornerOffset: `${-Math.round(cornerSize / 2)}px`,
      sideThickness: `${sideThickness}px`,
      sideOffset: `${-Math.round(sideThickness / 2)}px`,
      sideLength: `${sideLength}px`,
      barThickness: `${barThickness}px`,
      barOffset: `${-Math.round(barThickness / 2)}px`,
      barLength: `${barLength}px`,
    };
  });

  const marqueeRectStyle = computed(() => {
    if (!selectionMarquee.active) return {};
    const left = Math.min(selectionMarquee.startX, selectionMarquee.currentX);
    const top = Math.min(selectionMarquee.startY, selectionMarquee.currentY);
    const width = Math.abs(selectionMarquee.currentX - selectionMarquee.startX);
    const height = Math.abs(selectionMarquee.currentY - selectionMarquee.startY);
    return {
      left: `${left}px`,
      top: `${top}px`,
      width: `${width}px`,
      height: `${height}px`,
    };
  });

  return {
    selectedElement,
    hasSelection,
    isGroupSelection,
    selectedGroup,
    activeSelectionIds,
    hasMultiSelection,
    overlayControlTargetId,
    activeElementLabel,
    selectedElementType,
    hasTextSelection,
    clearSelection,
    clearSelectionMarquee,
    getGroupIdForElement,
    getSelectionBounds,
    isElementSelected,
    startSelectionMarquee,
    updateSelectionMarqueePreview,
    finalizeSelectionMarquee,
    selectGroup,
    buildGroupResizeSnapshot,
    selectedOverlayStyle,
    selectedActionBarStyle,
    selectedHandleMetrics,
    marqueeRectStyle,
  };
};
