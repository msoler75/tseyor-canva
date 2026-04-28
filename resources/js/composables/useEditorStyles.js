import { computed } from 'vue';
import {
  buildCanvasBackgroundStyle,
  buildCoverImageStyle,
  buildElementBoxStyle,
  buildElementContentStyle as buildSharedElementContentStyle,
  buildImageFrameStyle,
  buildImageTintOverlayStyle,
  buildRichEditorContainerStyle,
  buildShapeRenderModel,
  buildShapeStyle,
  buildShapeStyleFromKind,
  buildVisualShadow,
  getTextEffectStrokeWidth,
  neonColorOverrideFromLayout,
  normalizePickerColor,
} from '../utils/editorShared';

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

export const useEditorStyles = ({
  state,
  selectedElement,
  selectedElementType,
  hasTextSelection,
  textEffectOptions,
  getParagraphStyleFields,
  applyParagraphStyleField,
  getParagraphStyleForElement,
  baseTextElementIds,
  shapeClipPaths,
}) => {
  const activeTextEffectId = computed(() => {
    if (!hasTextSelection.value || !selectedElement.value) return 'none';

    const mode = selectedElement.value.textEffectMode;
    if (mode) return mode;

    if (selectedElement.value.hollowText) return 'hollow';
    if (selectedElement.value.backgroundColor && selectedElement.value.backgroundColor !== 'transparent') return 'background';
    if (selectedElement.value.border) return 'outline';
    if (selectedElement.value.shadow && selectedElement.value.shadowPreset === 'echo') return 'echo';
    if (selectedElement.value.neonColor) return 'neon';
    if (selectedElement.value.shadow) return 'shadow';

    return 'none';
  });

  const textEffectRows = computed(() => {
    const rows = [];
    for (let index = 0; index < textEffectOptions.length; index += 3) {
      rows.push(textEffectOptions.slice(index, index + 3));
    }
    return rows;
  });
  const visualEffectIds = new Set(['shadow1', 'shadow2', 'shadow', 'glow', 'echo', 'distort']);
  const visualEffectOptions = computed(() => textEffectOptions.filter((effect) => visualEffectIds.has(effect.id)));
  const visualEffectRows = computed(() => {
    const rows = [];
    for (let index = 0; index < visualEffectOptions.value.length; index += 3) {
      rows.push(visualEffectOptions.value.slice(index, index + 3));
    }
    return rows;
  });

  const canvasBackgroundStyle = computed(() => buildCanvasBackgroundStyle(state.elementLayout.background));

  const setSelectedColor = (field, value) => {
    if (getParagraphStyleFields().has(field)) {
      applyParagraphStyleField(field, value);
      return;
    }

    if (!selectedElement.value) return;
    selectedElement.value[field] = value;
  };

  const setTextEffect = (effectId) => {
    if (!selectedElement.value || !hasTextSelection.value) return;

    const layout = selectedElement.value;
    const nextEffectId = activeTextEffectId.value === effectId ? 'none' : effectId;
    layout.textEffectMode = nextEffectId;

    if (nextEffectId === 'none') {
      layout.shadow = false;
      layout.border = false;
      layout.neonColor = '';
      layout.bubbleColor = 'transparent';
      layout.backgroundColor = 'transparent';
      layout.hollowText = false;
      return;
    }

    layout.hollowText = false;

    if (nextEffectId === 'shadow1') {
      layout.shadow = true;
      layout.shadowPreset = 'hard';
      layout.shadowColor = layout.shadowColor || '#000000';
      layout.shadowAngle = 135;
      layout.shadowOffset = 10;
      layout.shadowBlur = 0;
      layout.shadowOpacity = 20;
      layout.border = false;
      layout.neonColor = '';
      layout.backgroundColor = 'transparent';
    } else if (nextEffectId === 'shadow2') {
      layout.shadow = true;
      layout.shadowPreset = 'soft';
      layout.shadowColor = layout.shadowColor || '#000000';
      layout.shadowAngle = 145;
      layout.shadowOffset = 12;
      layout.shadowBlur = 6;
      layout.shadowOpacity = 35;
      layout.border = false;
      layout.neonColor = '';
      layout.backgroundColor = 'transparent';
    } else if (nextEffectId === 'shadow') {
      layout.shadow = true;
      layout.shadowPreset = 'soft';
      layout.shadowColor = layout.shadowColor || '#0f172a';
      layout.shadowAngle = 135;
      layout.shadowOffset = 22;
      layout.shadowBlur = 15;
      layout.shadowOpacity = 55;
      layout.border = false;
      layout.neonColor = '';
      layout.backgroundColor = 'transparent';
    } else if (nextEffectId === 'glow') {
      layout.shadow = false;
      layout.neonColor = layout.neonColor || '#8b5cf6';
      layout.neonIntensity = layout.neonIntensity ?? 65;
      layout.border = false;
      layout.backgroundColor = 'transparent';
    } else if (nextEffectId === 'echo') {
      layout.shadow = true;
      layout.shadowPreset = 'echo';
      layout.shadowColor = layout.shadowColor || '#0f172a';
      layout.shadowAngle = 60;
      layout.shadowOffset = 15;
      layout.shadowBlur = 0;
      layout.shadowOpacity = 40;
      layout.neonColor = '';
      layout.border = false;
      layout.backgroundColor = 'transparent';
    } else if (nextEffectId === 'outline') {
      layout.shadow = false;
      layout.border = true;
      layout.contourColor = layout.contourColor || '#7c3aed';
      layout.contourWidth = 17;
      layout.neonColor = '';
      layout.backgroundColor = 'transparent';
    } else if (nextEffectId === 'background') {
      layout.shadow = false;
      layout.border = false;
      layout.neonColor = '';
      layout.backgroundColor = layout.backgroundColor && layout.backgroundColor !== 'transparent'
        ? layout.backgroundColor
        : '#ddd6fe';
      layout.backgroundRoundness = layout.backgroundRoundness ?? 50;
      layout.backgroundPadding = 5;
      layout.backgroundOpacity = layout.backgroundOpacity ?? 70;
    } else if (nextEffectId === 'misaligned') {
      layout.shadow = true;
      layout.shadowPreset = 'soft';
      layout.shadowColor = layout.shadowColor || '#7c3aed';
      layout.shadowAngle = 45;
      layout.shadowOffset = 33;
      layout.shadowOpacity = 20;
      layout.shadowBlur = 0;
      layout.misalignedThickness = 2;
      layout.contourWidth = 2;
      layout.contourColor = layout.contourColor || '#7c3aed';
      layout.neonColor = '';
      layout.border = true;
      layout.hollowText = true;
      layout.backgroundColor = 'transparent';
    } else if (nextEffectId === 'hollow') {
      layout.shadow = false;
      layout.border = true;
      layout.hollowText = true;
      layout.contourColor = layout.contourColor || '#7c3aed';
      layout.contourWidth = 2;
      layout.neonColor = '';
      layout.backgroundColor = 'transparent';
    } else if (nextEffectId === 'neon') {
      layout.shadow = false;
      layout.border = false;
      layout.neonColor = '';
      layout.neonIntensity = layout.neonIntensity ?? 80;
      layout.backgroundColor = 'transparent';
    } else if (nextEffectId === 'distort') {
      layout.shadow = true;
      layout.shadowPreset = 'hard';
      layout.shadowColor = '#f0f';
      layout.shadowAngle = 0;
      layout.shadowOffset = 15;
      layout.shadowBlur = 0;
      layout.shadowOpacity = 0;
      layout.shadowIntensity = 0;
      layout.neonColor = '#0ff';
      layout.neonIntensity = 0;
      layout.border = false;
      layout.backgroundColor = 'transparent';
    }
  };

  const activeVisualEffectId = computed(() => {
    if (!selectedElement.value || hasTextSelection.value) return 'none';

    const mode = selectedElement.value.textEffectMode;
    if (mode && visualEffectIds.has(mode)) return mode;
    if (selectedElement.value.shadow && selectedElement.value.shadowPreset === 'echo') return 'echo';
    if (selectedElement.value.neonColor) return 'glow';
    if (selectedElement.value.shadow && selectedElement.value.shadowPreset === 'hard') return 'shadow1';
    if (selectedElement.value.shadow) return 'shadow';
    return 'none';
  });

  const applyVisualEffectPreset = (layout, effectId) => {
    if (effectId === 'none') {
      layout.textEffectMode = 'none';
      layout.shadow = false;
      layout.neonColor = '';
      return;
    }

    layout.textEffectMode = effectId;
    layout.shadow = false;
    layout.neonColor = '';

    if (effectId === 'shadow1') {
      layout.shadow = true;
      layout.shadowPreset = 'hard';
      layout.shadowColor = layout.shadowColor || '#000000';
      layout.shadowAngle = 135;
      layout.shadowOffset = 10;
      layout.shadowBlur = 0;
      layout.shadowOpacity = 20;
    } else if (effectId === 'shadow2') {
      layout.shadow = true;
      layout.shadowPreset = 'soft';
      layout.shadowColor = layout.shadowColor || '#000000';
      layout.shadowAngle = 145;
      layout.shadowOffset = 12;
      layout.shadowBlur = 6;
      layout.shadowOpacity = 35;
    } else if (effectId === 'shadow') {
      layout.shadow = true;
      layout.shadowPreset = 'soft';
      layout.shadowColor = layout.shadowColor || '#0f172a';
      layout.shadowAngle = 135;
      layout.shadowOffset = 22;
      layout.shadowBlur = 15;
      layout.shadowOpacity = 55;
    } else if (effectId === 'glow') {
      layout.neonColor = layout.neonColor || '#8b5cf6';
      layout.neonIntensity = layout.neonIntensity ?? 65;
    } else if (effectId === 'echo') {
      layout.shadow = true;
      layout.shadowPreset = 'echo';
      layout.shadowColor = layout.shadowColor || '#0f172a';
      layout.shadowAngle = 60;
      layout.shadowOffset = 15;
      layout.shadowBlur = 0;
      layout.shadowOpacity = 40;
    } else if (effectId === 'distort') {
      layout.shadow = true;
      layout.shadowPreset = 'hard';
      layout.shadowColor = layout.shadowColor || '#f0f';
      layout.shadowAngle = 0;
      layout.shadowOffset = 15;
      layout.shadowBlur = 0;
      layout.shadowOpacity = 0;
      layout.neonColor = layout.neonColor || '#0ff';
      layout.neonIntensity = 0;
    }
  };

  const setVisualEffect = (effectId) => {
    if (!selectedElement.value || hasTextSelection.value) return;
    const nextEffectId = activeVisualEffectId.value === effectId ? 'none' : effectId;
    applyVisualEffectPreset(selectedElement.value, nextEffectId);
  };

  const isVeryDarkColor = (value) => {
    const normalized = normalizePickerColor(value, '');
    if (!normalized) return false;
    const r = Number.parseInt(normalized.slice(1, 3), 16) / 255;
    const g = Number.parseInt(normalized.slice(3, 5), 16) / 255;
    const b = Number.parseInt(normalized.slice(5, 7), 16) / 255;
    const toLinear = (channel) => (channel <= 0.03928
      ? channel / 12.92
      : ((channel + 0.055) / 1.055) ** 2.4);
    const luminance = 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
    return luminance < 0.18;
  };

  const getInitialBorderColor = () => {
    if (!selectedElement.value) return '#ffffff';
    if (selectedElementType?.value === 'image') return '#000000';

    const shapeBaseColor = selectedElement.value.fillMode === 'gradient'
      ? (selectedElement.value.gradientStart || '#0ea5e9')
      : (selectedElement.value.backgroundColor && selectedElement.value.backgroundColor !== 'transparent'
        ? selectedElement.value.backgroundColor
        : '#0ea5e9');

    return isVeryDarkColor(shapeBaseColor) ? '#ffffff' : '#000000';
  };

  const activateBorderStyle = (style = 'solid') => {
    if (!selectedElement.value) return;
    const wasEnabled = !!selectedElement.value.border;

    selectedElement.value.border = true;
    selectedElement.value.borderStyle = style;
    selectedElement.value.contourWidth = Math.max(1, Number(selectedElement.value.contourWidth || 2));

    const shapeBaseColor = selectedElement.value.fillMode === 'gradient'
      ? selectedElement.value.gradientStart
      : selectedElement.value.backgroundColor;
    const currentColor = normalizePickerColor(selectedElement.value.contourColor || '', '');
    const fillColor = normalizePickerColor(shapeBaseColor || '', '');
    const shouldUseInitialColor = !currentColor
      || currentColor === '#ffffff'
      || (currentColor === '#000000' && isVeryDarkColor(shapeBaseColor))
      || (fillColor && currentColor.toLowerCase() === fillColor.toLowerCase());

    if (!wasEnabled && shouldUseInitialColor) {
      selectedElement.value.contourColor = getInitialBorderColor();
    }
  };

  const textEffectPreviewStyle = (effectId) => {
    const base = {
      color: '#7c3aed',
      fontSize: '2.25rem',
      fontWeight: '700',
      lineHeight: '1',
      display: 'inline-block',
      padding: '0.12rem 0.24rem',
      borderRadius: '0.75rem',
      textShadow: 'none',
      WebkitTextStroke: '0',
      backgroundColor: 'transparent',
      transform: 'none',
    };

    if (effectId === 'shadow1') return { ...base, textShadow: '4px 4px 0 #00000099' };
    if (effectId === 'shadow2') return { ...base, textShadow: '3px 4px 5px #000000aa' };
    if (effectId === 'shadow') return { ...base, textShadow: '0 10px 16px #8b5cf680' };
    if (effectId === 'glow') return { ...base, textShadow: '0 0 8px #c4b5fd, 0 0 18px #a855f7' };
    if (effectId === 'echo') return { ...base, textShadow: '2px 2px 0 #a855f7, 5px 5px 0 #c084fc' };
    if (effectId === 'outline') return { ...base, color: '#7c3aed80', WebkitTextStroke: '2px #7c3aed' };
    if (effectId === 'background') return { ...base, backgroundColor: '#ddd6fe' };
    if (effectId === 'misaligned') {
      return {
        ...base,
        fontWeight: '500',
        color: 'transparent',
        WebkitTextStroke: '2px #7c3aed',
        textShadow: '4px 5px 0 #7c3aed33',
      };
    }
    if (effectId === 'hollow') return { ...base, fontWeight: '500', color: 'transparent', WebkitTextStroke: '2px #7c3aed' };
    if (effectId === 'neon') return { ...base, color: '#f5f3ff', textShadow: '0 0 8px #c4b5fd, 0 0 18px #a855f7, 0 0 30px #7c3aed' };
    if (effectId === 'distort') return { ...base, textShadow: '-2px 0 0 #f0f, 2px 0 0 #0ff' };

    return base;
  };

  const visualEffectPreviewStyle = (effectId) => {
    const sample = {
      textEffectMode: 'none',
      shadow: false,
      shadowPreset: 'soft',
      shadowColor: '#0f172a',
      shadowAngle: 135,
      shadowOffset: 22,
      shadowBlur: 15,
      shadowOpacity: 55,
      neonColor: '',
      neonIntensity: 65,
      bubbleColor: 'transparent',
      backgroundColor: '#7c3aed',
      border: false,
      contourWidth: 0,
      contourColor: '#7c3aed',
    };

    applyVisualEffectPreset(sample, effectId);

    return {
      width: '2.75rem',
      height: '2.75rem',
      borderRadius: '0.85rem',
      background: 'linear-gradient(135deg, #8b5cf6, #0ea5e9)',
      boxShadow: buildVisualShadow(sample),
      display: 'inline-block',
    };
  };

  const applyGradientPreset = (target, start, end) => {
    if (target === 'background') {
      state.elementLayout.background.fillMode = 'gradient';
      state.elementLayout.background.gradientStart = start;
      state.elementLayout.background.gradientEnd = end;
    } else if (target === 'shape' && selectedElement.value) {
      selectedElement.value.fillMode = 'gradient';
      selectedElement.value.gradientStart = start;
      selectedElement.value.gradientEnd = end;
    }
  };

  const swapGradientStops = (target) => {
    if (target === 'background') {
      const start = state.elementLayout.background.gradientStart || '#0ea5e9';
      state.elementLayout.background.gradientStart = state.elementLayout.background.gradientEnd || '#8b5cf6';
      state.elementLayout.background.gradientEnd = start;
    } else if (target === 'shape' && selectedElement.value) {
      const start = selectedElement.value.gradientStart || '#0ea5e9';
      selectedElement.value.gradientStart = selectedElement.value.gradientEnd || '#8b5cf6';
      selectedElement.value.gradientEnd = start;
    }
  };

  const applyShapeGradientPreset = (start, end) => {
    applyGradientPreset('shape', start, end);
  };

  const swapShapeGradientStops = () => {
    swapGradientStops('shape');
  };

  const isTextElement = (id) => {
    if (baseTextElementIds.has(id)) return true;
    return state.customElements?.[id]?.type === 'text';
  };

  const isAspectLockedResizeElement = (id) => {
    const type = state.customElements?.[id]?.type;
    return type === 'shape' || type === 'image';
  };

  const shapeStyleFromKind = (shapeKind, base) => buildShapeStyleFromKind(shapeKind, base, shapeClipPaths);

  const shapeStyle = (item) => buildShapeStyle(state.elementLayout[item.id], item.shapeKind, shapeClipPaths);
  const shapeRenderModel = (item) => buildShapeRenderModel(state.elementLayout[item.id], item.shapeKind, shapeClipPaths);

  const elementBoxStyle = (id) => {
    const layout = state.elementLayout[id];
    return buildElementBoxStyle(layout, { isText: isTextElement(id) });
  };

  const imageFrameStyle = (id) => {
    const layout = state.elementLayout[id];
    if (!layout) return {};
    return buildImageFrameStyle(layout);
  };

  const imageRenderStyle = (id) => {
    const layout = state.elementLayout[id];
    const element = state.customElements?.[id];
    if (!layout || !element) return {};

    return buildCoverImageStyle({
      containerWidth: layout.w ?? 160,
      containerHeight: layout.h ?? 140,
      imageWidth: element.intrinsicWidth,
      imageHeight: element.intrinsicHeight,
      cropScale: layout.imageCropScale,
      cropOffsetX: layout.imageCropOffsetX,
      cropOffsetY: layout.imageCropOffsetY,
      flipX: layout.flipX,
      flipY: layout.flipY,
    });
  };

  const imageTintOverlayStyle = (id) => {
    const layout = state.elementLayout[id];
    if (!layout) return {};
    return buildImageTintOverlayStyle(layout);
  };

  const elementContentStyle = (id) => {
    const layout = state.elementLayout[id];
    if (!layout) return {};
    const elementType = state.customElements?.[id]?.type ?? (baseTextElementIds.has(id) ? 'text' : null);
    return buildSharedElementContentStyle(layout, { elementType });
  };

  const richEditorContainerStyle = (id) => buildRichEditorContainerStyle(state.elementLayout[id]);

  const neonColorOverride = (id) => neonColorOverrideFromLayout(state.elementLayout[id]);

  return {
    activeTextEffectId,
    activeVisualEffectId,
    textEffectRows,
    visualEffectRows,
    canvasBackgroundStyle,
    normalizePickerColor,
    setSelectedColor,
    setTextEffect,
    setVisualEffect,
    activateBorderStyle,
    textEffectPreviewStyle,
    visualEffectPreviewStyle,
    applyGradientPreset,
    swapGradientStops,
    applyShapeGradientPreset,
    swapShapeGradientStops,
    elementBoxStyle,
    isTextElement,
    isAspectLockedResizeElement,
    shapeStyleFromKind,
    shapeStyle,
    shapeRenderModel,
    imageFrameStyle,
    imageRenderStyle,
    imageTintOverlayStyle,
    elementContentStyle,
    richEditorContainerStyle,
    neonColorOverride,
  };
};
