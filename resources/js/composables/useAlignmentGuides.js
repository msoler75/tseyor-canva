import { ref, computed } from 'vue';
import { foldGuidePositionsForFormat, horizontalPrintFoldFormats } from '../data/designer';

const SNAP_THRESHOLD = 10; // píxeles
const SUB_PAGE_MARGIN_RATIO = 0.08; // ~2cm por subpágina

export const useAlignmentGuides = ({
  state,
  canvasRef,
  getCanvasBounds,
  getSelectionBounds,
  activeSelectionIds,
}) => {
  const guides = ref([]); // [{ type: 'vertical'|'horizontal', x?, y?, start, end }]

  const canvasBounds = computed(() => getCanvasBounds() ?? { width:0, height:0 });

  const getAllElementBounds = () => {
    const bounds = [];
    Object.entries(state.elementLayout).forEach(([id, layout]) => {
      if (!layout || id === 'background') return;
      if (activeSelectionIds?.value?.includes?.(id)) return;
      bounds.push({
        id,
        x: layout.x ?? 0,
        y: layout.y ?? 0,
        w: layout.w ?? 0,
        h: layout.h ?? 0,
      });
    });
    return bounds;
  };

  const getSubPageMarginGuides = (canvas, dragBounds, handle) => {
    if (!horizontalPrintFoldFormats.includes(state?.format)) return [];

    const foldPositions = foldGuidePositionsForFormat(state.format);
    if (!foldPositions.length) return [];

    const panels = [];
    let prev = 0;
    for (const pos of foldPositions) {
      panels.push({ left: prev, right: pos });
      prev = pos;
    }
    panels.push({ left: prev, right: 100 });

    const candidates = [];

    for (const panel of panels) {
      const panelLeftPx = (panel.left / 100) * canvas.width;
      const panelRightPx = (panel.right / 100) * canvas.width;
      const panelWidthPx = panelRightPx - panelLeftPx;
      const marginPx = Math.round(panelWidthPx * SUB_PAGE_MARGIN_RATIO);

      candidates.push({
        type: 'vertical',
        x: panelLeftPx + marginPx,
        start: 0,
        end: canvas.height,
      });
      candidates.push({
        type: 'vertical',
        x: panelRightPx - marginPx,
        start: 0,
        end: canvas.height,
      });
    }

    const vMarginPx = Math.round(canvas.height * SUB_PAGE_MARGIN_RATIO);
    candidates.push({
      type: 'horizontal',
      y: vMarginPx,
      start: 0,
      end: canvas.width,
    });
    candidates.push({
      type: 'horizontal',
      y: canvas.height - vMarginPx,
      start: 0,
      end: canvas.width,
    });

    const dragLeft = dragBounds.x;
    const dragRight = dragBounds.x + dragBounds.w;
    const dragTop = dragBounds.y;
    const dragBottom = dragBounds.y + dragBounds.h;
    const dragHCenter = dragBounds.x + dragBounds.w / 2;
    const dragVCenter = dragBounds.y + dragBounds.h / 2;

    const canSnapLeft = !handle || handle === 'move' || handle === 'w' || handle.includes('w');
    const canSnapRight = !handle || handle === 'move' || handle === 'e' || handle.includes('e');
    const canSnapTop = !handle || handle === 'move' || handle === 'n' || handle.includes('n') || handle === 'n-width';
    const canSnapBottom = !handle || handle === 'move' || handle === 's' || handle.includes('s') || handle === 's-width';
    const canSnapCenter = !handle || handle === 'move';

    return candidates.filter((g) => {
      if (g.type === 'vertical') {
        return (canSnapLeft && Math.abs(dragLeft - g.x) <= SNAP_THRESHOLD)
          || (canSnapRight && Math.abs(dragRight - g.x) <= SNAP_THRESHOLD)
          || (canSnapCenter && Math.abs(dragHCenter - g.x) <= SNAP_THRESHOLD);
      }
      return (canSnapTop && Math.abs(dragTop - g.y) <= SNAP_THRESHOLD)
        || (canSnapBottom && Math.abs(dragBottom - g.y) <= SNAP_THRESHOLD)
        || (canSnapCenter && Math.abs(dragVCenter - g.y) <= SNAP_THRESHOLD);
    });
  };

  const findAlignmentGuides = (dragBounds, handle) => {
    const canvas = canvasBounds.value;
    if (!canvas.width || !canvas.height) return [];

    const found = [];

    found.push(...getSubPageMarginGuides(canvas, dragBounds, handle));
    const dragLeft = dragBounds.x;
    const dragRight = dragBounds.x + dragBounds.w;
    const dragTop = dragBounds.y;
    const dragBottom = dragBounds.y + dragBounds.h;
    const dragHCenter = dragBounds.x + dragBounds.w / 2;
    const dragVCenter = dragBounds.y + dragBounds.h / 2;

    // Centro del canvas
    const canvasHCenter = canvas.width / 2;
    const canvasVCenter = canvas.height / 2;

    if (!handle || handle === 'move') {
      if (Math.abs(dragHCenter - canvasHCenter) <= SNAP_THRESHOLD) {
        found.push({
          type: 'vertical',
          x: canvasHCenter,
          start: 0,
          end: canvas.height,
        });
      }
      if (Math.abs(dragVCenter - canvasVCenter) <= SNAP_THRESHOLD) {
        found.push({
          type: 'horizontal',
          y: canvasVCenter,
          start: 0,
          end: canvas.width,
        });
      }
    }

    const canSnapLeft = !handle || handle === 'move' || handle === 'w' || handle.includes('w');
    const canSnapRight = !handle || handle === 'move' || handle === 'e' || handle.includes('e');
    const canSnapTop = !handle || handle === 'move' || handle === 'n' || handle.includes('n') || handle === 'n-width';
    const canSnapBottom = !handle || handle === 'move' || handle === 's' || handle.includes('s') || handle === 's-width';

    if (canSnapLeft && Math.abs(dragLeft) <= SNAP_THRESHOLD) {
      found.push({ type: 'vertical', x: 0, start: 0, end: canvas.height });
    }
    if (canSnapRight && Math.abs(dragRight - canvas.width) <= SNAP_THRESHOLD) {
      found.push({ type: 'vertical', x: canvas.width, start: 0, end: canvas.height });
    }
    if (canSnapTop && Math.abs(dragTop) <= SNAP_THRESHOLD) {
      found.push({ type: 'horizontal', y: 0, start: 0, end: canvas.width });
    }
    if (canSnapBottom && Math.abs(dragBottom - canvas.height) <= SNAP_THRESHOLD) {
      found.push({ type: 'horizontal', y: canvas.height, start: 0, end: canvas.width });
    }

    // Alineación con otros elementos
    const otherElements = getAllElementBounds();
    otherElements.forEach((elem) => {
      const elemLeft = elem.x;
      const elemRight = elem.x + elem.w;
      const elemTop = elem.y;
      const elemBottom = elem.y + elem.h;
      const elemHCenter = elem.x + elem.w / 2;
      const elemVCenter = elem.y + elem.h / 2;

      if (canSnapLeft && Math.abs(dragLeft - elemLeft) <= SNAP_THRESHOLD) {
        found.push({
          type: 'vertical',
          x: elemLeft,
          start: Math.min(dragTop, elemTop),
          end: Math.max(dragBottom, elemBottom),
        });
      }

      if (canSnapRight && Math.abs(dragRight - elemRight) <= SNAP_THRESHOLD) {
        found.push({
          type: 'vertical',
          x: elemRight,
          start: Math.min(dragTop, elemTop),
          end: Math.max(dragBottom, elemBottom),
        });
      }

      if (canSnapTop && Math.abs(dragTop - elemTop) <= SNAP_THRESHOLD) {
        found.push({
          type: 'horizontal',
          y: elemTop,
          start: Math.min(dragLeft, elemLeft),
          end: Math.max(dragRight, elemRight),
        });
      }

      if (canSnapBottom && Math.abs(dragBottom - elemBottom) <= SNAP_THRESHOLD) {
        found.push({
          type: 'horizontal',
          y: elemBottom,
          start: Math.min(dragLeft, elemLeft),
          end: Math.max(dragRight, elemRight),
        });
      }

      if ((!handle || handle === 'move') && Math.abs(dragHCenter - elemHCenter) <= SNAP_THRESHOLD) {
        found.push({
          type: 'vertical',
          x: elemHCenter,
          start: Math.min(dragTop, elemTop),
          end: Math.max(dragBottom, elemBottom),
        });
      }

      if ((!handle || handle === 'move') && Math.abs(dragVCenter - elemVCenter) <= SNAP_THRESHOLD) {
        found.push({
          type: 'horizontal',
          y: elemVCenter,
          start: Math.min(dragLeft, elemLeft),
          end: Math.max(dragRight, elemRight),
        });
      }
    });

    const unique = [];
    const seen = new Set();
    found.forEach((g) => {
      const key = `${g.type}-${g.x ?? g.y}`;
      if (!seen.has(key)) {
        seen.add(key);
        unique.push(g);
      }
    });

    return unique;
  };

  const snapToGuides = (dragBounds) => {
    const guideLines = findAlignmentGuides(dragBounds, 'move');
    let bestDx = 0, bestDy = 0;
    let bestVScore = 0, bestHScore = 0;
    let bestVDist = Infinity, bestHDist = Infinity;

    for (const guide of guideLines) {
      if (guide.type === 'vertical') {
        const gX = guide.x;
        const candidates = [
          { edge: 'left', dist: gX - dragBounds.x },
          { edge: 'right', dist: gX - (dragBounds.x + dragBounds.w) },
          { edge: 'center', dist: gX - (dragBounds.x + dragBounds.w / 2) },
        ];
        const within = candidates.filter(c => Math.abs(c.dist) <= SNAP_THRESHOLD);
        const score = within.length;
        if (!score) continue;
        const closest = within.reduce((a, b) => Math.abs(a.dist) < Math.abs(b.dist) ? a : b);
        const absDist = Math.abs(closest.dist);
        if (score > bestVScore || (score === bestVScore && absDist < bestVDist)) {
          bestVScore = score;
          bestVDist = absDist;
          bestDx = closest.dist;
        }
      } else {
        const gY = guide.y;
        const candidates = [
          { edge: 'top', dist: gY - dragBounds.y },
          { edge: 'bottom', dist: gY - (dragBounds.y + dragBounds.h) },
          { edge: 'center', dist: gY - (dragBounds.y + dragBounds.h / 2) },
        ];
        const within = candidates.filter(c => Math.abs(c.dist) <= SNAP_THRESHOLD);
        const score = within.length;
        if (!score) continue;
        const closest = within.reduce((a, b) => Math.abs(a.dist) < Math.abs(b.dist) ? a : b);
        const absDist = Math.abs(closest.dist);
        if (score > bestHScore || (score === bestHScore && absDist < bestHDist)) {
          bestHScore = score;
          bestHDist = absDist;
          bestDy = closest.dist;
        }
      }
    }

    return { dx: bestDx, dy: bestDy };
  };

  const snapBoundsForResize = (dragBounds, handle) => {
    const guideLines = findAlignmentGuides(dragBounds, handle);
    let left = dragBounds.x;
    let right = dragBounds.x + dragBounds.w;
    let top = dragBounds.y;
    let bottom = dragBounds.y + dragBounds.h;

    const canSnapLeft = handle === 'w' || handle.includes('w');
    const canSnapRight = handle === 'e' || handle.includes('e');
    const canSnapTop = handle === 'n' || handle.includes('n') || handle === 'n-width';
    const canSnapBottom = handle === 's' || handle.includes('s') || handle === 's-width';

    for (const guide of guideLines) {
      if (guide.type === 'vertical') {
        const dLeft = guide.x - left;
        const dRight = guide.x - right;
        const aLeft = Math.abs(dLeft);
        const aRight = Math.abs(dRight);

        if (canSnapLeft && aLeft <= SNAP_THRESHOLD) {
          left = guide.x;
        } else if (canSnapRight && aRight <= SNAP_THRESHOLD) {
          right = guide.x;
        }
      } else {
        const dTop = guide.y - top;
        const dBottom = guide.y - bottom;
        const aTop = Math.abs(dTop);
        const aBottom = Math.abs(dBottom);

        if (canSnapTop && aTop <= SNAP_THRESHOLD) {
          top = guide.y;
        } else if (canSnapBottom && aBottom <= SNAP_THRESHOLD) {
          bottom = guide.y;
        }
      }
    }

    return { x: left, y: top, w: Math.max(1, right - left), h: Math.max(1, bottom - top) };
  };

  const updateGuides = (dragBounds) => {
    guides.value = findAlignmentGuides(dragBounds);
  };

  const clearGuides = () => {
    guides.value = [];
  };

  return {
    guides,
    updateGuides,
    clearGuides,
    snapToGuides,
    snapBoundsForResize,
    SNAP_THRESHOLD,
  };
};
