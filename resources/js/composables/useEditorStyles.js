import { computed } from 'vue';

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

export const useEditorStyles = ({
  state,
  selectedElement,
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

  const canvasBackgroundStyle = computed(() => {
    const bg = state.elementLayout.background;
    if (bg?.fillMode === 'gradient') {
      return {
        background: `linear-gradient(${bg.gradientAngle || 135}deg, ${bg.gradientStart || '#0ea5e9'}, ${bg.gradientEnd || '#8b5cf6'})`,
      };
    }
    return {
      backgroundColor: bg?.backgroundColor || '#4338ca',
    };
  });

  const normalizePickerColor = (value, fallback = '#ffffff') => {
    if (typeof value !== 'string') return fallback;

    const trimmed = value.trim();

    if (/^#[\da-f]{6}$/i.test(trimmed)) return trimmed;
    if (/^#[\da-f]{3}$/i.test(trimmed)) {
      return `#${trimmed[1]}${trimmed[1]}${trimmed[2]}${trimmed[2]}${trimmed[3]}${trimmed[3]}`;
    }

    return fallback;
  };

  const setSelectedColor = (field, value) => {
    if (getParagraphStyleFields().has(field)) {
      applyParagraphStyleField(field, value);
      return;
    }

    if (!selectedElement.value) return;
    selectedElement.value[field] = value;
  };

  const getTextEffectStrokeWidth = (layout) => {
    const mode = layout?.textEffectMode;
    const isTextEffectStrokeMode = mode === 'outline' || mode === 'hollow' || mode === 'misaligned';

    if (!isTextEffectStrokeMode) {
      return clamp(Number(layout?.contourWidth ?? 2), 1, 12);
    }

    return (clamp(Number(layout?.contourWidth ?? 0), 0, 100) / 100) * 12;
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

  const buildTextShadow = (layout, textColor = null) => {
    const shadows = [];
    const shadowOffset = clamp(Number(layout.shadowOffset ?? 20), 0, 100);
    const shadowBlur = clamp(Number(layout.shadowBlur ?? 25), 0, 100);
    const shadowOpacity = clamp(Number(layout.shadowOpacity ?? 65), 0, 100);
    const shadowAngle = ((Number(layout.shadowAngle ?? 135) % 360) + 360) % 360;
    const neonIntensity = clamp(Number(layout.neonIntensity ?? 55), 0, 100);

    const toShadowOffset = (distance) => {
      const rad = (shadowAngle * Math.PI) / 180;
      return {
        x: Math.round(Math.cos(rad) * distance),
        y: Math.round(Math.sin(rad) * distance),
      };
    };

    const applyAlphaToHex = (color, alphaPercent) => {
      if (typeof color !== 'string') return color;
      const value = color.trim();
      const alpha = clamp(100 - alphaPercent, 0, 100);

      if (/^#[\da-f]{3}$/i.test(value)) {
        const r = value[1];
        const g = value[2];
        const b = value[3];
        const a = Math.round((alpha / 100) * 255).toString(16).padStart(2, '0');
        return `#${r}${r}${g}${g}${b}${b}${a}`;
      }

      if (/^#[\da-f]{6}$/i.test(value)) {
        const a = Math.round((alpha / 100) * 255).toString(16).padStart(2, '0');
        return `${value}${a}`;
      }

      return value;
    };

    if (layout.border && !layout.hollowText) {
      const borderColor = layout.contourColor || '#7c3aed';
      const width = getTextEffectStrokeWidth(layout);
      if (width <= 0) {
        return shadows.length ? shadows.join(', ') : 'none';
      }
      const ring = Math.max(1, Math.round(width));
      for (let x = -ring; x <= ring; x++) {
        for (let y = -ring; y <= ring; y++) {
          if (x === 0 && y === 0) continue;
          if (x * x + y * y <= ring * ring) {
            shadows.push(`${x}px ${y}px 0 ${borderColor}`);
          }
        }
      }
    }

    if (layout.textEffectMode === 'distort') {
      const primaryColor = layout.shadowColor || '#f0f';
      const secondaryColor = layout.neonColor || '#0ff';
      const distance = clamp(Math.round(clamp(Number(layout.shadowOffset ?? 15), 0, 20) * 0.2), 1, 20);
      const offset = toShadowOffset(distance);
      shadows.push(
        `${offset.x}px ${offset.y}px 0 ${primaryColor}`,
        `${-offset.x}px ${-offset.y}px 0 ${secondaryColor}`,
      );
    } else if (layout.shadow) {
      const color = layout.shadowColor || '#0f172a';
      const preset = layout.shadowPreset || 'soft';
      const colorWithAlpha = applyAlphaToHex(color, shadowOpacity);
      const isMisaligned = layout.textEffectMode === 'misaligned';

      if (isMisaligned) {
        const distance = Math.max(0, Math.round(shadowOffset * 0.25));
        const offset = toShadowOffset(distance);
        shadows.push(`${offset.x}px ${offset.y}px 0 ${colorWithAlpha}`);
      } else if (preset === 'hard') {
        const distance = Math.round(shadowOffset * 0.6);
        const offset = toShadowOffset(distance);
        shadows.push(`${offset.x}px ${offset.y}px 0 ${colorWithAlpha}`);
      } else if (preset === 'echo') {
        const distance = Math.max(1, Math.round(shadowOffset * 0.25));
        const offset = toShadowOffset(distance);
        shadows.push(
          `${offset.x}px ${offset.y}px 0 ${colorWithAlpha}`,
          `${offset.x * 2}px ${offset.y * 2}px 0 ${colorWithAlpha}`,
          `${offset.x * 3}px ${offset.y * 3}px 0 ${colorWithAlpha}`,
        );
      } else {
        const distance = Math.round(shadowOffset * 0.6);
        const blur = Math.round(shadowBlur * 0.8);
        const offset = toShadowOffset(distance);
        shadows.push(`${offset.x}px ${offset.y}px ${blur}px ${colorWithAlpha}`);
      }
    }

    if (layout.textEffectMode === 'neon' && !layout.hollowText) {
      const sourceColor = textColor || '#7c3aed';
      const blurSoft = Math.round(4 + neonIntensity / 5);
      const blurStrong = Math.round(10 + neonIntensity / 2.5);
      const glowColor = normalizePickerColor(sourceColor, '#7c3aed');
      shadows.push(`0 0 ${blurSoft}px ${glowColor}`, `0 0 ${blurStrong}px ${glowColor}`);
    } else if (layout.neonColor && layout.textEffectMode !== 'distort') {
      const blurSoft = Math.round(4 + neonIntensity / 6);
      const blurStrong = Math.round(12 + neonIntensity / 2);
      shadows.push(`0 0 ${blurSoft}px ${layout.neonColor}`, `0 0 ${blurStrong}px ${layout.neonColor}`);
    }

    return shadows.length ? shadows.join(', ') : 'none';
  };

  const buildBubbleShadow = (layout) => {
    if (!layout.bubbleColor || layout.bubbleColor === 'transparent') return 'none';
    return `0 10px 20px ${layout.bubbleColor}55`;
  };

  const buildVisualShadow = (layout) => {
    const shadows = [];
    const shadowIntensity = clamp(Number(layout.shadowIntensity ?? 45), 0, 100);
    const neonIntensity = clamp(Number(layout.neonIntensity ?? 55), 0, 100);

    if (layout.shadow) {
      const color = layout.shadowColor || '#0f172a';
      const preset = layout.shadowPreset || 'soft';

      if (preset === 'hard') {
        const distance = Math.round(1 + shadowIntensity / 12);
        shadows.push(`${distance}px ${distance}px 0 ${color}`);
      } else if (preset === 'lifted') {
        const y = Math.round(8 + shadowIntensity / 4);
        const blur = Math.round(10 + shadowIntensity / 2);
        shadows.push(`0 ${y}px ${blur}px ${color}66`);
      } else {
        const y = Math.round(4 + shadowIntensity / 6);
        const blur = Math.round(8 + shadowIntensity / 2);
        shadows.push(`0 ${y}px ${blur}px ${color}66`);
      }
    }

    if (layout.neonColor && layout.textEffectMode !== 'distort') {
      const blurSoft = Math.round(4 + neonIntensity / 6);
      const blurStrong = Math.round(12 + neonIntensity / 2);
      shadows.push(`0 0 ${blurSoft}px ${layout.neonColor}`, `0 0 ${blurStrong}px ${layout.neonColor}`);
    }

    if (layout.bubbleColor && layout.bubbleColor !== 'transparent') {
      shadows.push(`0 10px 20px ${layout.bubbleColor}55`);
    }

    return shadows.length ? shadows.join(', ') : 'none';
  };

  const isTextElement = (id) => {
    if (baseTextElementIds.has(id)) return true;
    return state.customElements?.[id]?.type === 'text';
  };

  const isAspectLockedResizeElement = (id) => {
    const type = state.customElements?.[id]?.type;
    return type === 'shape' || type === 'image';
  };

  const shapeStyleFromKind = (shapeKind, base) => {
    if (shapeKind === 'circle' || shapeKind === 'ellipse') {
      return { ...base, borderRadius: '9999px' };
    }
    if (shapeKind === 'frame-rounded') {
      return {
        ...base,
        borderRadius: '22px',
        background: 'transparent',
        border: base.border === '0' ? '8px solid currentColor' : base.border,
      };
    }
    if (shapeKind === 'rectangle-outline') {
      return { ...base, borderRadius: '0' };
    }
    if (shapeKind === 'rectangle') {
      return { ...base, borderRadius: '10px' };
    }
    if (shapeKind === 'square') {
      return { ...base, borderRadius: '8px' };
    }
    const clipPath = shapeClipPaths[shapeKind];
    if (clipPath) {
      return { ...base, clipPath, border: '0' };
    }
    return { ...base, borderRadius: '8px' };
  };

  const shapeStyle = (item) => {
    const layout = state.elementLayout[item.id];
    const fill = layout.fillMode === 'gradient'
      ? `linear-gradient(${layout.gradientAngle || 135}deg, ${layout.gradientStart || '#0ea5e9'}, ${layout.gradientEnd || '#8b5cf6'})`
      : (layout.backgroundColor && layout.backgroundColor !== 'transparent' ? layout.backgroundColor : '#ffffff');
    const base = {
      width: '100%',
      height: '100%',
      background: fill,
      boxShadow: buildVisualShadow(layout),
      border: layout.border
        ? `${layout.contourWidth || 1}px solid ${layout.contourColor || '#ffffff'}`
        : '0',
    };
    return shapeStyleFromKind(item.shapeKind, base);
  };

  const imageFrameStyle = (id) => {
    const layout = state.elementLayout[id];
    if (!layout) return {};

    return {
      backgroundColor: layout.backgroundColor && layout.backgroundColor !== 'transparent' ? layout.backgroundColor : 'rgba(255,255,255,0.2)',
      border: layout.border
        ? `${layout.contourWidth || 1}px solid ${layout.contourColor || '#ffffff'}`
        : '1px solid rgba(255,255,255,0.4)',
      boxShadow: buildVisualShadow(layout),
    };
  };

  const imageTintOverlayStyle = (id) => {
    const layout = state.elementLayout[id];
    if (!layout) return {};

    const tintStrength = clamp(Number(layout.imageTintStrength ?? 0), 0, 100);

    return {
      backgroundColor: layout.imageTintColor || '#0f172a',
      opacity: `${tintStrength / 100}`,
      mixBlendMode: 'multiply',
    };
  };

  const elementContentStyle = (id) => {
    const layout = state.elementLayout[id];
    if (!layout) return {};

    const elementType = state.customElements?.[id]?.type ?? (baseTextElementIds.has(id) ? 'text' : null);

    if (elementType !== 'text') {
      return {
        opacity: `${(layout.opacity ?? 100) / 100}`,
      };
    }

    const hasBackground = layout.backgroundColor && layout.backgroundColor !== 'transparent';
    const backgroundOpacity = clamp(Number(layout.backgroundOpacity ?? 70), 0, 100);
    const backgroundExpand = clamp(Number(layout.backgroundPadding ?? 5), 0, 100);
    const backgroundAlphaHex = Math.round((backgroundOpacity / 100) * 255).toString(16).padStart(2, '0');
    const resolvedBackground = hasBackground && /^#[\da-f]{6}$/i.test(layout.backgroundColor)
      ? `${layout.backgroundColor}${backgroundAlphaHex}`
      : (hasBackground ? layout.backgroundColor : 'transparent');

    return {
      opacity: `${(layout.opacity ?? 100) / 100}`,
      backgroundColor: resolvedBackground,
      borderRadius: hasBackground ? `${Math.round(clamp(Number(layout.backgroundRoundness ?? 50), 0, 100) * 0.48)}px` : '0',
      padding: hasBackground ? `${backgroundExpand}px` : '0',
      margin: hasBackground ? `-${backgroundExpand}px` : '0',
      color: layout.hollowText ? 'transparent' : undefined,
      textShadow: 'none',
      WebkitTextStroke: '0',
      boxShadow: buildBubbleShadow(layout),
    };
  };

  const richEditorContainerStyle = (id) => {
    const layout = state.elementLayout[id];
    const firstParagraphColor = layout?.paragraphStyles?.[0]?.color ?? layout?.color ?? '#ffffff';
    const strokeWidth = getTextEffectStrokeWidth(layout);
    return {
      opacity: `${(layout?.opacity ?? 100) / 100}`,
      textShadow: buildTextShadow(layout, firstParagraphColor),
      WebkitTextStroke: layout?.border && layout?.hollowText && strokeWidth > 0
        ? `${strokeWidth}px ${firstParagraphColor}`
        : '0',
      WebkitTextFillColor: layout?.hollowText ? 'transparent' : undefined,
      color: layout?.hollowText ? 'transparent' : undefined,
    };
  };

  const neonColorOverride = (id) => {
    const layout = state.elementLayout[id];
    if (!layout || layout.textEffectMode !== 'neon' || layout.hollowText) return null;
    return '#ffffff';
  };

  return {
    activeTextEffectId,
    textEffectRows,
    canvasBackgroundStyle,
    normalizePickerColor,
    setSelectedColor,
    setTextEffect,
    textEffectPreviewStyle,
    applyGradientPreset,
    swapGradientStops,
    applyShapeGradientPreset,
    swapShapeGradientStops,
    isTextElement,
    isAspectLockedResizeElement,
    shapeStyleFromKind,
    shapeStyle,
    imageFrameStyle,
    imageTintOverlayStyle,
    elementContentStyle,
    richEditorContainerStyle,
    neonColorOverride,
  };
};
