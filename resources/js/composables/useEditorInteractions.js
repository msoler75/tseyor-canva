import { computed, nextTick } from 'vue';
import { useAlignmentGuides } from './useAlignmentGuides';

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

export const useEditorInteractions = ({
  state,
  canvasRef,
  richEditorRefs,
  elementMeasurements,
  drag,
  toolbarPosition,
  toolbarDrag,
  touchIntent,
  dragIntent,
  selectionMarquee,
  groupedElements,
  multiSelectionIds,
  selectedGroupId,
  activePropertyPanel,
  paragraphSelection,
  selectedParagraphIndex,
  preserveEditorSelectionUntil,
  suppressElementClickUntil,
  suppressCanvasClickUntil,
  editingElementId,
  zoomScale,
  orderedLayerIds,
  selectedTextStyle,
  commitTextEdit,
  beginTextEdit,
  deleteCurrentSelection,
  performUndo,
  performRedo,
  setDragDocumentState,
  clearSelection,
  startSelectionMarquee,
  updateSelectionMarqueePreview,
  finalizeSelectionMarquee,
  selectGroup,
  getGroupIdForElement,
  buildGroupResizeSnapshot,
  getSelectionBounds,
  getCanvasBounds,
  getEstimatedTextHeight,
  getElementText,
  ensureParagraphStyles,
  isTextElement,
  isLinkedTextElement,
  isAspectLockedResizeElement,
  applyParagraphStyleField,
  recalculateTextHeight,
  activeSelectionIds,
}) => {
  const alignmentGuides = useAlignmentGuides({
    state,
    canvasRef,
    getCanvasBounds,
    getSelectionBounds,
    activeSelectionIds,
  });
  let longPressTimer = null;
  let elementClickWasPreselected = false;

  const clearLongPress = () => {
    if (longPressTimer) {
      clearTimeout(longPressTimer);
      longPressTimer = null;
    }
    touchIntent.pointerId = null;
  };

  const handleElementClick = (event, id) => {
    if (Date.now() < suppressElementClickUntil.value) {
      elementClickWasPreselected = false;
      return;
    }

    if (elementClickWasPreselected && isTextElement(id) && !editingElementId.value) {
      elementClickWasPreselected = false;
      beginTextEdit(id, false, event);
      return;
    }
    elementClickWasPreselected = false;

    if (event?.shiftKey) return;

    const groupId = getGroupIdForElement(id);
    if (groupId) {
      selectGroup(groupId);
      return;
    }

    if (editingElementId.value && editingElementId.value !== id) {
      commitTextEdit();
    }

    selectedGroupId.value = null;
    multiSelectionIds.value = [];

    if (!isTextElement(id)) {
      state.selectedElementId = id;
      return;
    }

    state.selectedElementId = id;
    selectedParagraphIndex.value = 0;
    paragraphSelection.start = 0;
    paragraphSelection.end = 0;
    paragraphSelection.active = false;
  };

  const markEditorControlInteraction = () => {
    preserveEditorSelectionUntil.value = Date.now() + 300;
  };

  const onRichEditorBlur = (id, event) => {
    if (Date.now() < preserveEditorSelectionUntil.value) {
      commitTextEdit();
      return;
    }

    const nextTarget = event?.relatedTarget ?? null;
    if (nextTarget instanceof Element) {
      if (nextTarget.closest('[data-editor-keep-selection="true"]')) {
        const isFocusableInput = nextTarget.closest('input,select,textarea');
        if (!isFocusableInput) {
          nextTick(() => {
            if (editingElementId.value === id) {
              richEditorRefs.value[id]?.$el?.querySelector('[contenteditable]')?.focus();
            }
          });
        }
        return;
      }
      if (nextTarget.closest('[data-editor-control="true"]')) {
        commitTextEdit();
        return;
      }
      if (nextTarget.closest('[data-document-page-switcher="true"]')) {
        commitTextEdit({ recalculateHeight: false, reason: 'switch-page-blur' });
        return;
      }
      if (nextTarget.closest('[data-editor-element="true"]')) {
        commitTextEdit();
        return;
      }
    }
    clearSelection();
  };

  const onRichEditorKeydown = (event) => {
    if (event.key === 'Escape') {
      editingElementId.value = null;
      return;
    }
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      commitTextEdit();
    }
  };

  const clearDragIntent = () => {
    dragIntent.active = false;
    dragIntent.pointerId = null;
    dragIntent.elementId = null;
    dragIntent.groupId = null;
    dragIntent.targetType = 'element';
    dragIntent.startX = 0;
    dragIntent.startY = 0;
  };

  const beginElementDrag = ({ pointerId, clientX, clientY }, id, captureTarget = null) => {
    const canvas = canvasRef.value;
    const layout = state.elementLayout[id];
    if (!canvas || !layout) return;

    state.selectedElementId = id;
    selectedGroupId.value = null;
    multiSelectionIds.value = [];
    drag.active = true;
    drag.mode = 'move';
    drag.pointerId = pointerId;
    drag.elementId = id;
    drag.groupId = null;
    drag.groupSnapshot = null;
    drag.handle = null;
    drag.startClientX = clientX;
    drag.startClientY = clientY;
    drag.startX = layout.x;
    drag.startY = layout.y;
    drag.startW = layout.w;
    drag.startH = layout.h ?? 140;
    drag.startFontSize = layout.fontSize;
    clearLongPress();
    clearDragIntent();
    setDragDocumentState(true);

    captureTarget?.setPointerCapture?.(pointerId);
  };

  const handleElementPointerDown = (event, id) => {
    if (event.button !== undefined && event.button !== 0) return;
    if (editingElementId.value === id) return;

    elementClickWasPreselected = (state.selectedElementId === id) && isTextElement(id) && !editingElementId.value;

    const groupId = getGroupIdForElement(id);
    if (groupId) {
      selectGroup(groupId);
      dragIntent.active = true;
      dragIntent.pointerId = event.pointerId;
      dragIntent.elementId = null;
      dragIntent.groupId = groupId;
      dragIntent.targetType = 'group';
      dragIntent.startX = event.clientX;
      dragIntent.startY = event.clientY;
      clearLongPress();
      return;
    }

    if (event.shiftKey) {
      const current = multiSelectionIds.value.length > 1
        ? [...multiSelectionIds.value]
        : state.selectedElementId
          ? [state.selectedElementId]
          : [];

      if (current.includes(id)) {
        const next = current.filter((elId) => elId !== id);
        if (next.length === 1) {
          state.selectedElementId = next[0];
          selectedGroupId.value = null;
          multiSelectionIds.value = [];
        } else if (next.length === 0) {
          state.selectedElementId = null;
          selectedGroupId.value = null;
          multiSelectionIds.value = [];
        } else {
          state.selectedElementId = null;
          selectedGroupId.value = null;
          multiSelectionIds.value = next;
        }
      } else {
        const next = [...current, id];
        state.selectedElementId = null;
        selectedGroupId.value = null;
        multiSelectionIds.value = next;
        dragIntent.active = true;
        dragIntent.pointerId = event.pointerId;
        dragIntent.elementId = id;
        dragIntent.groupId = null;
        dragIntent.targetType = 'multi';
        dragIntent.startX = event.clientX;
        dragIntent.startY = event.clientY;
        clearLongPress();
      }
      return;
    }

    if (multiSelectionIds.value.length > 1 && multiSelectionIds.value.includes(id)) {
      dragIntent.active = true;
      dragIntent.pointerId = event.pointerId;
      dragIntent.elementId = id;
      dragIntent.groupId = null;
      dragIntent.targetType = 'multi';
      dragIntent.startX = event.clientX;
      dragIntent.startY = event.clientY;
      clearLongPress();
      return;
    }

    state.selectedElementId = id;
    selectedGroupId.value = null;
    multiSelectionIds.value = [];
    dragIntent.active = true;
    dragIntent.pointerId = event.pointerId;
    dragIntent.elementId = id;
    dragIntent.groupId = null;
    dragIntent.targetType = 'element';
    dragIntent.startX = event.clientX;
    dragIntent.startY = event.clientY;

    clearLongPress();
  };

  const startResize = (event, id, handle) => {
    const group = groupedElements[id] ?? null;
    const layout = group ? group.layout : state.elementLayout[id];
    if (!layout) return;

    markEditorControlInteraction();

    if (editingElementId.value) commitTextEdit();

    if (group) {
      selectGroup(id);
      state.selectedElementId = null;
      multiSelectionIds.value = [];
    } else {
      state.selectedElementId = id;
      selectedGroupId.value = null;
      multiSelectionIds.value = [];
    }
    drag.active = true;
    drag.mode = 'resize';
    drag.pointerId = event.pointerId;
    drag.elementId = group ? null : id;
    drag.groupId = group ? id : null;
    drag.groupSnapshot = null;
    drag.handle = handle;
    drag.startClientX = event.clientX;
    drag.startClientY = event.clientY;
    drag.startX = layout.x;
    drag.startY = layout.y;
    drag.startW = layout.w;
    drag.startH = layout.h ?? 140;
    drag.startFontSize = layout.fontSize;
    drag.startParagraphStyles = group
      ? []
      : ensureParagraphStyles(layout, getElementText(id)).map((style) => ({ ...style }));
    drag.groupSnapshot = group ? buildGroupResizeSnapshot(id) : null;
    clearLongPress();
    setDragDocumentState(true);

    event.currentTarget?.setPointerCapture?.(event.pointerId);
    event.stopPropagation();
    event.preventDefault();
  };

  const getPointerAngle = (event, centerX, centerY) => Math.atan2(event.clientY - centerY, event.clientX - centerX) * (180 / Math.PI);

  const startRotate = (event, id) => {
    const group = groupedElements[id] ?? null;
    const layout = group ? group.layout : state.elementLayout[id];
    const measured = group ? { width: layout.w, height: layout.h } : elementMeasurements[id];
    if (!layout) return;

    markEditorControlInteraction();

    if (editingElementId.value) commitTextEdit();

    const width = measured?.width ?? layout.w ?? 0;
    const height = measured?.height ?? layout.h ?? 44;
    const centerX = layout.x + (width / 2);
    const centerY = layout.y + (height / 2);

    if (group) {
      selectGroup(id);
      state.selectedElementId = null;
    } else {
      state.selectedElementId = id;
      selectedGroupId.value = null;
      multiSelectionIds.value = [];
    }
    drag.active = true;
    drag.mode = 'rotate';
    drag.pointerId = event.pointerId;
    drag.elementId = group ? null : id;
    drag.groupId = group ? id : null;
    drag.groupSnapshot = null;
    drag.handle = null;
    drag.startRotation = Number(layout.rotation ?? 0);
    drag.centerX = centerX;
    drag.centerY = centerY;
    drag.startAngle = getPointerAngle(event, centerX, centerY);
    drag.lastClientX = event.clientX;
    drag.lastClientY = event.clientY;
    clearLongPress();
    setDragDocumentState(true);

    event.currentTarget?.setPointerCapture?.(event.pointerId);
    event.stopPropagation();
    event.preventDefault();
  };

  const resetRotation = (id) => {
    if (groupedElements[id]) {
      groupedElements[id].layout.rotation = 0;
      groupedElements[id].elementIds.forEach((memberId) => {
        const memberLayout = state.elementLayout[memberId];
        if (memberLayout) memberLayout.rotation = 0;
      });
      return;
    }

    const layout = state.elementLayout[id];
    if (!layout) return;
    layout.rotation = 0;
  };

  const clampToolbar = () => {};

  const moveDrag = (event) => {
    if (selectionMarquee.active && selectionMarquee.pointerId === event.pointerId && canvasRef.value) {
      const rect = canvasRef.value.getBoundingClientRect();
      selectionMarquee.currentX = event.clientX - rect.left;
      selectionMarquee.currentY = event.clientY - rect.top;
      selectionMarquee.dragged = true;
      updateSelectionMarqueePreview();
      if (event.cancelable) event.preventDefault();
      return;
    }

    if (toolbarDrag.active && toolbarDrag.pointerId === event.pointerId) {
      toolbarPosition.x = toolbarDrag.originX + (event.clientX - toolbarDrag.startX);
      toolbarPosition.y = toolbarDrag.originY + (event.clientY - toolbarDrag.startY);
      clampToolbar();
      if (event.cancelable) event.preventDefault();
      return;
    }

    if (!drag.active && dragIntent.active && dragIntent.pointerId === event.pointerId && (dragIntent.elementId || dragIntent.groupId)) {
      const moved = Math.hypot(event.clientX - dragIntent.startX, event.clientY - dragIntent.startY);

      if (moved > 6) {
        if (dragIntent.targetType === 'group' && dragIntent.groupId) {
          const group = groupedElements[dragIntent.groupId];
          if (group) {
            drag.active = true;
            drag.mode = 'move';
            drag.pointerId = event.pointerId;
            drag.elementId = null;
            drag.groupId = dragIntent.groupId;
            drag.handle = null;
            drag.startClientX = event.clientX;
            drag.startClientY = event.clientY;
            drag.startX = group.layout.x;
            drag.startY = group.layout.y;
            drag.startW = group.layout.w;
            drag.startH = group.layout.h;
            setDragDocumentState(true);
            clearDragIntent();
          }
        } else if (dragIntent.targetType === 'multi' && dragIntent.elementId) {
          const snapshot = multiSelectionIds.value
            .map((elId) => {
              const l = state.elementLayout[elId];
              return l ? { id: elId, startX: l.x, startY: l.y } : null;
            })
            .filter(Boolean);
          drag.active = true;
          drag.mode = 'multi';
          drag.pointerId = event.pointerId;
          drag.elementId = dragIntent.elementId;
          drag.groupId = null;
          drag.multiSnapshot = snapshot;
          drag.handle = null;
          drag.startClientX = event.clientX;
          drag.startClientY = event.clientY;
          setDragDocumentState(true);
          clearDragIntent();
        } else if (dragIntent.elementId) {
          beginElementDrag({
            pointerId: event.pointerId,
            clientX: dragIntent.startX,
            clientY: dragIntent.startY,
          }, dragIntent.elementId);
        }
        suppressElementClickUntil.value = Date.now() + 250;
      }
    }

    if (!drag.active || drag.pointerId !== event.pointerId || (!drag.elementId && !drag.groupId) || !canvasRef.value) {
      if (touchIntent.pointerId === event.pointerId) {
        const moved = Math.hypot(event.clientX - touchIntent.startX, event.clientY - touchIntent.startY);
        if (moved > 8) clearLongPress();
      }
      return;
    }

    const rect = canvasRef.value.getBoundingClientRect();
    const logicalBounds = getCanvasBounds();
    const boundsWidth = logicalBounds.width;
    const boundsHeight = logicalBounds.height;
    const layout = drag.groupId ? groupedElements[drag.groupId]?.layout : state.elementLayout[drag.elementId];
    const isText = drag.groupId ? false : isTextElement(drag.elementId);
    const isLinkedText = drag.groupId ? false : isLinkedTextElement?.(drag.elementId) ?? false;
    if (!layout) return;

    if (drag.groupId) {
      const group = groupedElements[drag.groupId];
      if (!group) return;

      if (drag.mode === 'move') {
        const deltaX = (event.clientX - drag.startClientX) / zoomScale.value;
        const deltaY = (event.clientY - drag.startClientY) / zoomScale.value;
        const nextX = Math.round(drag.startX + deltaX);
        const nextY = Math.round(drag.startY + deltaY);
        const shiftX = nextX - group.layout.x;
        const shiftY = nextY - group.layout.y;

      group.layout.x = nextX;
      group.layout.y = nextY;
      group.elementIds.forEach((id) => {
        const memberLayout = state.elementLayout[id];
        if (!memberLayout) return;
        memberLayout.x = Math.round((memberLayout.x ?? 0) + shiftX);
        memberLayout.y = Math.round((memberLayout.y ?? 0) + shiftY);
      });
      if (event.cancelable) event.preventDefault();
      const dragBounds = getSelectionBounds(activeSelectionIds?.value ?? []);
      if (dragBounds) {
        alignmentGuides.updateGuides(dragBounds);
      }
      return;
    }

      if (drag.mode === 'resize') {
        if (event.cancelable) event.preventDefault();
        const snapshot = drag.groupSnapshot;
        if (!snapshot) return;
        const deltaX = (event.clientX - drag.startClientX) / zoomScale.value;
        const deltaY = (event.clientY - drag.startClientY) / zoomScale.value;
        const handle = drag.handle ?? 'se';
        const minSize = 40;
        let nextX = snapshot.x;
        let nextY = snapshot.y;
        let nextW = snapshot.w;
        let nextH = snapshot.h;

        if (handle === 'n-width' || handle === 's-width') {
          if (handle === 's-width') {
            nextH = Math.max(minSize, Math.round(snapshot.h + deltaY));
          } else {
            nextH = Math.max(minSize, Math.round(snapshot.h - deltaY));
            nextY = snapshot.y + (snapshot.h - nextH);
          }
        } else {
          if (handle.includes('e')) {
            nextW = Math.max(minSize, Math.round(snapshot.w + deltaX));
          }
          if (handle.includes('w')) {
            nextW = Math.max(minSize, Math.round(snapshot.w - deltaX));
            nextX = snapshot.x + (snapshot.w - nextW);
          }
        }

        if (handle === 'e' || handle === 'w') {
          nextH = snapshot.h;
          nextY = snapshot.y;
        } else if (handle !== 'n-width' && handle !== 's-width') {
          if (handle.includes('s')) {
            nextH = Math.max(minSize, Math.round(snapshot.h + deltaY));
          }
          if (handle.includes('n')) {
            nextH = Math.max(minSize, Math.round(snapshot.h - deltaY));
            nextY = snapshot.y + (snapshot.h - nextH);
          }
        }

        nextX = Math.round(nextX);
        nextY = Math.round(nextY);

        const sx = nextW / Math.max(1, snapshot.w);
        const sy = nextH / Math.max(1, snapshot.h);

        group.layout.x = Math.round(nextX);
        group.layout.y = Math.round(nextY);
        group.layout.w = Math.round(nextW);
        group.layout.h = Math.round(nextH);

        snapshot.members.forEach((memberSnapshot) => {
          const member = state.elementLayout[memberSnapshot.id];
          if (!member) return;

          const scaledX = nextX + ((memberSnapshot.x - snapshot.x) * sx);
          const scaledY = nextY + ((memberSnapshot.y - snapshot.y) * sy);
          const scaledW = Math.max(40, Math.round(memberSnapshot.w * sx));
          const scaledH = Math.max(40, Math.round(memberSnapshot.h * sy));

          member.x = Math.round(scaledX);
          member.y = Math.round(scaledY);
          member.w = scaledW;

          if (!memberSnapshot.isText) {
            member.h = scaledH;
          }

          if (memberSnapshot.isText) {
            const scale = Math.max(0.2, Math.min(sx, sy));
            member.fontSize = clamp(Math.round(memberSnapshot.fontSize * scale), 8, 200);
            member.paragraphStyles = memberSnapshot.paragraphStyles.map((style) => ({
              ...style,
              fontSize: clamp(Math.round((style.fontSize ?? memberSnapshot.fontSize) * scale), 8, 200),
            }));
          }
        });
        return;
      }

      if (drag.mode === 'rotate') {
        const currentAngle = getPointerAngle(event, drag.centerX, drag.centerY);
        const deltaAngle = currentAngle - drag.startAngle;
        const radians = (deltaAngle * Math.PI) / 180;
        const cos = Math.cos(radians);
        const sin = Math.sin(radians);

        group.layout.rotation = Math.round(((Number(group.layout.rotation ?? 0) + deltaAngle) + 540) % 360 - 180);
        group.elementIds.forEach((id) => {
          const member = state.elementLayout[id];
          if (!member) return;
          const width = Math.max(1, member.w ?? 1);
          const height = Math.max(1, member.h ?? 44);
          const cx = (member.x ?? 0) + width / 2;
          const cy = (member.y ?? 0) + height / 2;
          const dx = cx - drag.centerX;
          const dy = cy - drag.centerY;
          const nextCx = drag.centerX + (dx * cos) - (dy * sin);
          const nextCy = drag.centerY + (dx * sin) + (dy * cos);

          member.x = Math.round(nextCx - width / 2);
          member.y = Math.round(nextCy - height / 2);
          member.rotation = Math.round(((Number(member.rotation ?? 0) + deltaAngle) + 540) % 360 - 180);
        });

        drag.startAngle = currentAngle;
        if (event.cancelable) event.preventDefault();
        return;
      }
    }

    if (drag.mode === 'rotate') {
      const dx = (event.clientX - drag.lastClientX) / zoomScale.value;
      const dy = (event.clientY - drag.lastClientY) / zoomScale.value;
      const currentRotation = Number(layout.rotation ?? 0);
      const theta = (currentRotation * Math.PI) / 180;
      const tangentX = -Math.cos(theta);
      const tangentY = -Math.sin(theta);
      const projectedDelta = (dx * tangentX) + (dy * tangentY);
      const sensitivity = 0.8;
      const nextRotation = currentRotation + (projectedDelta * sensitivity);

      layout.rotation = Math.round((nextRotation + 540) % 360 - 180);
      drag.lastClientX = event.clientX;
      drag.lastClientY = event.clientY;
      if (event.cancelable) event.preventDefault();
      return;
    }

    if (drag.mode === 'resize') {
      if (event.cancelable) event.preventDefault();
      const deltaX = (event.clientX - drag.startClientX) / zoomScale.value;
      const deltaY = (event.clientY - drag.startClientY) / zoomScale.value;
      const handle = drag.handle ?? 'se';
      const isSideHandle = handle === 'e' || handle === 'w';
      const isVerticalBarHandle = handle === 'n-width' || handle === 's-width';
      const horizontalDelta = handle.includes('e') ? deltaX : -deltaX;
      const maxTextWidth = Math.max(120, boundsWidth - 8);

      if (!isText || isLinkedText) {
        const currentHeight = drag.startH || layout.h || 140;
        const minHeight = 4;
        const minWidth = 4;

        if (isVerticalBarHandle) {
          const verticalDelta = handle === 's-width' ? deltaY : -deltaY;
          const nextHeight = Math.max(minHeight, Math.round(currentHeight + verticalDelta));
          layout.h = nextHeight;

          if (handle === 'n-width') {
            layout.y = Math.round(drag.startY + (currentHeight - nextHeight));
          } else {
            layout.y = Math.round(drag.startY);
          }
          return;
        }

        if (isSideHandle) {
          const nextWidth = Math.max(minWidth, Math.round(drag.startW + horizontalDelta));
          layout.w = nextWidth;

          if (handle === 'w') {
            layout.x = Math.round(drag.startX + (drag.startW - nextWidth));
          } else {
            layout.x = Math.round(drag.startX);
          }

          return;
        }

        const verticalDelta = handle.includes('s') ? deltaY : -deltaY;
        let nextWidth = Math.max(minWidth, Math.round(drag.startW + horizontalDelta));
        let nextHeight = Math.max(minHeight, Math.round(currentHeight + verticalDelta));

        if (isAspectLockedResizeElement(drag.elementId)) {
          const startW = Math.max(1, drag.startW);
          const startH = Math.max(1, currentHeight);
          const widthScale = (drag.startW + horizontalDelta) / startW;
          const heightScale = (currentHeight + verticalDelta) / startH;
          const scale = Math.abs(widthScale - 1) >= Math.abs(heightScale - 1) ? widthScale : heightScale;
          nextWidth = Math.max(minWidth, Math.round(startW * scale));
          nextHeight = Math.max(minHeight, Math.round(startH * scale));
        }

        layout.w = nextWidth;
        layout.h = nextHeight;

        if (handle.includes('w')) {
          layout.x = Math.round(drag.startX + (drag.startW - nextWidth));
        } else {
          layout.x = Math.round(drag.startX);
        }
        if (handle.includes('n')) {
          layout.y = Math.round(drag.startY + (currentHeight - nextHeight));
        } else {
          layout.y = Math.round(drag.startY);
        }

        return;
      }

      if (isSideHandle) {
        const nextWidth = Math.max(120, Math.round(drag.startW + horizontalDelta));
        layout.w = nextWidth;

        if (handle === 'w') {
          layout.x = Math.round(drag.startX + (drag.startW - nextWidth));
        } else {
          layout.x = Math.round(drag.startX);
        }

        return;
      }

      const widthDelta = horizontalDelta + (deltaY * 0.35);
      const nextWidth = Math.max(120, Math.round(drag.startW + widthDelta));
      const scale = nextWidth / Math.max(drag.startW, 1);

      layout.w = nextWidth;
      layout.fontSize = Math.max(14, Math.round(drag.startFontSize * scale));
      layout.paragraphStyles = (drag.startParagraphStyles?.length ? drag.startParagraphStyles : ensureParagraphStyles(layout, getElementText(drag.elementId)).map((style) => ({ ...style })))
        .map((style) => ({
          ...style,
          fontSize: Math.max(8, Math.round((style.fontSize ?? drag.startFontSize) * scale)),
        }));

      recalculateTextHeight(drag.elementId);

      if (handle.includes('w')) layout.x = Math.round(drag.startX + (drag.startW - nextWidth));
      else layout.x = Math.round(drag.startX);

      if (handle.includes('n')) layout.y = Math.round(drag.startY - ((layout.fontSize - drag.startFontSize) * 0.6));
      return;
    }

    if (drag.mode === 'multi') {
      if (!drag.multiSnapshot) return;
      const deltaX = (event.clientX - drag.startClientX) / zoomScale.value;
      const deltaY = (event.clientY - drag.startClientY) / zoomScale.value;
      drag.multiSnapshot.forEach(({ id: elId, startX, startY }) => {
        const l = state.elementLayout[elId];
        if (!l) return;
        l.x = Math.round(startX + deltaX);
        l.y = Math.round(startY + deltaY);
      });
      if (event.cancelable) event.preventDefault();
      const dragBounds = getSelectionBounds(activeSelectionIds?.value ?? []);
      if (dragBounds) {
        alignmentGuides.updateGuides(dragBounds);
      }
      return;
    }

    const deltaX = (event.clientX - drag.startClientX) / zoomScale.value;
    const deltaY = (event.clientY - drag.startClientY) / zoomScale.value;
    layout.x = Math.round(drag.startX + deltaX);
    layout.y = Math.round(drag.startY + deltaY);
    if (event.cancelable) event.preventDefault();
    const ids = activeSelectionIds?.value?.length ? activeSelectionIds.value : [drag.elementId];
    const dragBounds = getSelectionBounds(ids);
    if (dragBounds) {
      alignmentGuides.updateGuides(dragBounds);
    }
  };

  const endDrag = (event) => {
    if (selectionMarquee.active && selectionMarquee.pointerId === event.pointerId) {
      if (canvasRef.value) {
        const rect = canvasRef.value.getBoundingClientRect();
        selectionMarquee.currentX = event.clientX - rect.left;
        selectionMarquee.currentY = event.clientY - rect.top;
        updateSelectionMarqueePreview();
      }
      if (selectionMarquee.dragged && suppressCanvasClickUntil) {
        suppressCanvasClickUntil.value = Date.now() + 300;
      }
      finalizeSelectionMarquee();
      setDragDocumentState(false);
      return;
    }

    if (toolbarDrag.active && toolbarDrag.pointerId === event.pointerId) {
      toolbarDrag.active = false;
      toolbarDrag.pointerId = null;
      setDragDocumentState(false);
      return;
    }

    if (dragIntent.pointerId !== null && event.pointerId !== undefined && dragIntent.pointerId === event.pointerId) {
      clearDragIntent();
    }

    if (drag.pointerId !== null && event.pointerId !== undefined && drag.pointerId !== event.pointerId) return;
    const wasDragging = drag.active;
    drag.active = false;
    drag.mode = 'move';
    drag.pointerId = null;
    drag.elementId = null;
    drag.groupId = null;
    drag.groupSnapshot = null;
    drag.multiSnapshot = null;
    drag.handle = null;
    drag.startH = 0;
    drag.startRotation = 0;
    drag.startAngle = 0;
    drag.centerX = 0;
    drag.centerY = 0;
    drag.lastClientX = 0;
    drag.lastClientY = 0;
    clearLongPress();
    clearDragIntent();
    if (wasDragging) {
      suppressElementClickUntil.value = Date.now() + 250;
    }
    alignmentGuides.clearGuides();
    setDragDocumentState(false);
  };

  const cycleAlignment = () => {
    const order = ['left', 'center', 'right', 'justify'];
    const current = selectedTextStyle.value?.textAlign ?? 'left';
    const index = order.indexOf(current);
    applyParagraphStyleField('textAlign', order[(index + 1) % order.length]);
  };

  const currentAlignmentIcon = computed(() => {
    const icons = {
      left: 'ph:text-align-left',
      center: 'ph:text-align-center',
      right: 'ph:text-align-right',
      justify: 'ph:text-align-justify',
    };
    const editorRef = state.selectedElementId ? richEditorRefs.value[state.selectedElementId] : null;
    const align = editorRef?.getActiveAttrs()?.textAlign ?? 'left';
    return icons[align];
  });

  const changeLayer = (mode) => {
    const currentId = state.selectedElementId;
    const ordered = [...orderedLayerIds.value];
    const currentIndex = ordered.indexOf(currentId);

    if (currentIndex === -1) return;

    const reordered = [...ordered];
    reordered.splice(currentIndex, 1);

    if (mode === 'front') reordered.push(currentId);
    else if (mode === 'back') reordered.unshift(currentId);
    else if (mode === 'forward') reordered.splice(Math.min(currentIndex + 1, reordered.length), 0, currentId);
    else if (mode === 'backward') reordered.splice(Math.max(currentIndex - 1, 0), 0, currentId);

    reordered.forEach((id, index) => {
      state.elementLayout[id].zIndex = (index + 1) * 10;
    });
  };

  const handleCanvasPointerDown = (event) => {
    if (drag.active || selectionMarquee.active) return;
    if (event.button !== undefined && event.button !== 0) return;

    const target = event.target instanceof Element ? event.target : null;
    if (target?.closest('[data-editor-element="true"]') || target?.closest('[data-editor-control="true"]')) return;

    clearSelection();
    startSelectionMarquee(event);
  };

  const handleGlobalPointerDown = (event) => {
    if (drag.active || selectionMarquee.active || (!state.selectedElementId && !selectedGroupId.value && !multiSelectionIds.value.length)) return;

    const target = event.target;
    if (!(target instanceof Element)) return;

    const preserveSelectionTarget = target.closest(
      '[data-editor-element="true"],[data-editor-control="true"],[data-editor-keep-selection="true"],[data-editor-canvas="true"],nav,header,[role="navigation"]',
    );

    if (preserveSelectionTarget) return;

    clearSelection();
  };

  const handleGlobalKeydown = (event) => {
    const targetElement = event.target instanceof Element ? event.target : null;
    const isTypingTarget = Boolean(targetElement?.closest('input, textarea, select, [contenteditable="true"]'));
    if (isTypingTarget) return;

    const hasCommandModifier = event.ctrlKey || event.metaKey;
    const normalizedKey = event.key.toLowerCase();

    if (hasCommandModifier && !event.altKey && normalizedKey === 'z') {
      event.preventDefault();
      if (event.shiftKey) {
        performRedo();
        return;
      }
      performUndo();
      return;
    }

    if (hasCommandModifier && !event.altKey && normalizedKey === 'y') {
      event.preventDefault();
      performRedo();
      return;
    }

    if (editingElementId.value) return;
    if (event.key === 'Delete' || event.key === 'Backspace') {
      deleteCurrentSelection();
    }
  };

  return {
    clearLongPress,
    handleElementClick,
    markEditorControlInteraction,
    onRichEditorBlur,
    onRichEditorKeydown,
    handleElementPointerDown,
    startResize,
    startRotate,
    resetRotation,
    moveDrag,
    endDrag,
    cycleAlignment,
    currentAlignmentIcon,
    changeLayer,
    handleCanvasPointerDown,
    handleGlobalPointerDown,
    handleGlobalKeydown,
    guides: alignmentGuides.guides,
  };
};
