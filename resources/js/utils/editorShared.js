export const BASE_TEXT_ELEMENT_IDS = new Set(['title', 'subtitle', 'meta', 'contact', 'extra']);

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

export function buildEditorElements(state) {
  const metaText = [state.content?.date, state.content?.time].filter(Boolean).join(' · ');
  const baseTextElements = [
    { id: 'title', type: 'text', label: 'Titulo', text: state.content?.title ?? '' },
    { id: 'subtitle', type: 'text', label: 'Subtitulo', text: state.content?.subtitle ?? '' },
    { id: 'meta', type: 'text', label: 'Fecha / hora', text: metaText },
    { id: 'contact', type: 'text', label: 'Contacto', text: state.content?.contact ?? '' },
    { id: 'extra', type: 'text', label: 'Texto adicional', text: state.content?.extra ?? '' },
  ];

  const customElements = Object.entries(state.customElements ?? {}).map(([id, element]) => ({
    id,
    type: element.type,
    label: element.label ?? 'Elemento',
    text: element.type === 'text' ? (element.text ?? '') : '',
    src: element.type === 'image' ? element.src : null,
    shapeKind: element.type === 'shape' ? element.shapeKind : null,
  }));

  return [...baseTextElements, ...customElements]
    .filter((item) => state.elementLayout?.[item.id])
    .sort((a, b) => (state.elementLayout[a.id]?.zIndex ?? 0) - (state.elementLayout[b.id]?.zIndex ?? 0));
}

export function buildCanvasBackgroundStyle(backgroundLayout = {}) {
  if (backgroundLayout?.fillMode === 'gradient') {
    return {
      background: `linear-gradient(${backgroundLayout.gradientAngle || 135}deg, ${backgroundLayout.gradientStart || '#0ea5e9'}, ${backgroundLayout.gradientEnd || '#8b5cf6'})`,
    };
  }
  return {
    backgroundColor: backgroundLayout?.backgroundColor || '#4338ca',
  };
}

export function normalizePickerColor(value, fallback = '#ffffff') {
  if (typeof value !== 'string') return fallback;

  const trimmed = value.trim();

  if (/^#[\da-f]{6}$/i.test(trimmed)) return trimmed;
  if (/^#[\da-f]{3}$/i.test(trimmed)) {
    return `#${trimmed[1]}${trimmed[1]}${trimmed[2]}${trimmed[2]}${trimmed[3]}${trimmed[3]}`;
  }

  return fallback;
}

export function getTextEffectStrokeWidth(layout = {}) {
  const mode = layout?.textEffectMode;
  const isTextEffectStrokeMode = mode === 'outline' || mode === 'hollow' || mode === 'misaligned';

  if (!isTextEffectStrokeMode) {
    return clamp(Number(layout?.contourWidth ?? 2), 1, 12);
  }

  return (clamp(Number(layout?.contourWidth ?? 0), 0, 100) / 100) * 12;
}

export function buildTextShadow(layout = {}, textColor = null) {
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
}

export function buildBubbleShadow(layout = {}) {
  if (!layout.bubbleColor || layout.bubbleColor === 'transparent') return 'none';
  return `0 10px 20px ${layout.bubbleColor}55`;
}

export function buildVisualShadow(layout = {}) {
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

  if (layout.neonColor) {
    const blurSoft = Math.round(4 + neonIntensity / 6);
    const blurStrong = Math.round(12 + neonIntensity / 2);
    shadows.push(`0 0 ${blurSoft}px ${layout.neonColor}`, `0 0 ${blurStrong}px ${layout.neonColor}`);
  }

  if (layout.bubbleColor && layout.bubbleColor !== 'transparent') {
    shadows.push(`0 10px 20px ${layout.bubbleColor}55`);
  }

  return shadows.length ? shadows.join(', ') : 'none';
}

export function buildShapeStyleFromKind(shapeKind, base, shapeClipPaths = {}) {
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
}

export function buildShapeStyle(layout = {}, shapeKind, shapeClipPaths = {}) {
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

  return buildShapeStyleFromKind(shapeKind, base, shapeClipPaths);
}

export function buildImageFrameStyle(layout = {}) {
  return {
    width: '100%',
    height: '100%',
    overflow: 'hidden',
    borderRadius: '12px',
    backgroundColor: layout.backgroundColor && layout.backgroundColor !== 'transparent' ? layout.backgroundColor : 'rgba(255,255,255,0.2)',
    border: layout.border
      ? `${layout.contourWidth || 1}px solid ${layout.contourColor || '#ffffff'}`
      : '1px solid rgba(255,255,255,0.4)',
    boxShadow: buildVisualShadow(layout),
  };
}

export function buildImageTintOverlayStyle(layout = {}) {
  const tintStrength = clamp(Number(layout.imageTintStrength ?? 0), 0, 100);

  return {
    position: 'absolute',
    inset: '0',
    backgroundColor: layout.imageTintColor || '#0f172a',
    opacity: `${tintStrength / 100}`,
    mixBlendMode: 'multiply',
    pointerEvents: 'none',
  };
}

export function buildElementContentStyle(layout = {}, { elementType = null } = {}) {
  if (elementType !== 'text') {
    return {
      opacity: `${(layout.opacity ?? 100) / 100}`,
      width: '100%',
      height: '100%',
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
    boxSizing: 'border-box',
    textAlign: 'left',
    textIndent: '0',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    color: layout.hollowText ? 'transparent' : undefined,
    textShadow: 'none',
    WebkitTextStroke: '0',
    boxShadow: buildBubbleShadow(layout),
  };
}

export function buildElementBoxStyle(layout = {}, { isText = false } = {}) {
  const rotation = Number(layout.rotation ?? 0);

  return {
    position: 'absolute',
    left: `${layout.x ?? 0}px`,
    top: `${layout.y ?? 0}px`,
    width: `${layout.w ?? 160}px`,
    height: isText ? 'auto' : `${layout.h ?? 140}px`,
    zIndex: `${layout.zIndex ?? 1}`,
    transform: `rotate(${rotation}deg)`,
    transformOrigin: 'center center',
  };
}

export function buildRichEditorContainerStyle(layout = {}) {
  const firstParagraphColor = layout?.paragraphStyles?.[0]?.color ?? layout?.color ?? '#ffffff';
  const strokeWidth = getTextEffectStrokeWidth(layout);

  return {
    opacity: `${(layout.opacity ?? 100) / 100}`,
    textShadow: buildTextShadow(layout, firstParagraphColor),
    WebkitTextStroke: layout?.border && layout?.hollowText && strokeWidth > 0
      ? `${strokeWidth}px ${firstParagraphColor}`
      : '0',
    WebkitTextFillColor: layout?.hollowText ? 'transparent' : undefined,
    color: layout?.hollowText ? 'transparent' : undefined,
  };
}

export function neonColorOverrideFromLayout(layout = {}) {
  if (!layout || layout.textEffectMode !== 'neon' || layout.hollowText) return null;
  return '#ffffff';
}

export function parseSizeDetail(detail) {
  const source = String(detail || '').replace(',', '.').trim();

  const pxMatch = source.match(/(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*px/i);
  if (pxMatch) {
    return {
      unit: 'px',
      width: Number(pxMatch[1]),
      height: Number(pxMatch[2]),
    };
  }

  const cmMatch = source.match(/(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*cm/i);
  if (cmMatch) {
    return {
      unit: 'cm',
      width: Number(cmMatch[1]),
      height: Number(cmMatch[2]),
    };
  }

  return {
    unit: 'px',
    width: 1080,
    height: 1080,
  };
}
