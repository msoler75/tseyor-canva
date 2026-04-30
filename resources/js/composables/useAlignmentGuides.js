import { ref, computed } from 'vue';

const SNAP_THRESHOLD = 10; // píxeles

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

  const findAlignmentGuides = (dragBounds) => {
    const canvas = canvasBounds.value;
    if (!canvas.width || !canvas.height) return [];

    const found = [];
    const dragLeft = dragBounds.x;
    const dragRight = dragBounds.x + dragBounds.w;
    const dragTop = dragBounds.y;
    const dragBottom = dragBounds.y + dragBounds.h;
    const dragHCenter = dragBounds.x + dragBounds.w / 2;
    const dragVCenter = dragBounds.y + dragBounds.h / 2;

    // Centro del canvas
    const canvasHCenter = canvas.width / 2;
    const canvasVCenter = canvas.height / 2;

    // Alineación con centro horizontal del canvas
    if (Math.abs(dragHCenter - canvasHCenter) <= SNAP_THRESHOLD) {
      found.push({
        type: 'vertical',
        x: canvasHCenter,
        start: 0,
        end: canvas.height,
      });
    }

    // Alineación con centro vertical del canvas
    if (Math.abs(dragVCenter - canvasVCenter) <= SNAP_THRESHOLD) {
      found.push({
        type: 'horizontal',
        y: canvasVCenter,
        start: 0,
        end: canvas.width,
      });
    }

    // Alineación con bordes del canvas
    if (Math.abs(dragLeft) <= SNAP_THRESHOLD) {
      found.push({
        type: 'vertical',
        x: 0,
        start: 0,
        end: canvas.height,
      });
    }
    if (Math.abs(dragRight - canvas.width) <= SNAP_THRESHOLD) {
      found.push({
        type: 'vertical',
        x: canvas.width,
        start: 0,
        end: canvas.height,
      });
    }
    if (Math.abs(dragTop) <= SNAP_THRESHOLD) {
      found.push({
        type: 'horizontal',
        y: 0,
        start: 0,
        end: canvas.width,
      });
    }
    if (Math.abs(dragBottom - canvas.height) <= SNAP_THRESHOLD) {
      found.push({
        type: 'horizontal',
        y: canvas.height,
        start: 0,
        end: canvas.width,
      });
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

      // Bordes izquierdos alineados
      if (Math.abs(dragLeft - elemLeft) <= SNAP_THRESHOLD) {
        found.push({
          type: 'vertical',
          x: elemLeft,
          start: Math.min(dragTop, elemTop),
          end: Math.max(dragBottom, elemBottom),
        });
      }

      // Bordes derechos alineados
      if (Math.abs(dragRight - elemRight) <= SNAP_THRESHOLD) {
        found.push({
          type: 'vertical',
          x: elemRight,
          start: Math.min(dragTop, elemTop),
          end: Math.max(dragBottom, elemBottom),
        });
      }

      // Bordes superiores alineados
      if (Math.abs(dragTop - elemTop) <= SNAP_THRESHOLD) {
        found.push({
          type: 'horizontal',
          y: elemTop,
          start: Math.min(dragLeft, elemLeft),
          end: Math.max(dragRight, elemRight),
        });
      }

      // Bordes inferiores alineados
      if (Math.abs(dragBottom - elemBottom) <= SNAP_THRESHOLD) {
        found.push({
          type: 'horizontal',
          y: elemBottom,
          start: Math.min(dragLeft, elemLeft),
          end: Math.max(dragRight, elemRight),
        });
      }

      // Centros horizontales alineados
      if (Math.abs(dragHCenter - elemHCenter) <= SNAP_THRESHOLD) {
        found.push({
          type: 'vertical',
          x: elemHCenter,
          start: Math.min(dragTop, elemTop),
          end: Math.max(dragBottom, elemBottom),
        });
      }

      // Centros verticales alineados
      if (Math.abs(dragVCenter - elemVCenter) <= SNAP_THRESHOLD) {
        found.push({
          type: 'horizontal',
          y: elemVCenter,
          start: Math.min(dragLeft, elemLeft),
          end: Math.max(dragRight, elemRight),
        });
      }
    });

    // Eliminar duplicados
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
    SNAP_THRESHOLD,
  };
};
