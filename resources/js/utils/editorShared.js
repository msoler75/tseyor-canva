export const BASE_TEXT_ELEMENT_IDS = new Set(['title', 'subtitle', 'meta', 'contact', 'extra']);

export const SHAPE_CLIP_PATHS = {
  diamond:           'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)',
  parallelogram:     'polygon(20% 0%, 100% 0%, 80% 100%, 0% 100%)',
  trapezoid:         'polygon(15% 0%, 85% 0%, 100% 100%, 0% 100%)',
  'trapezoid-inv':   'polygon(0% 0%, 100% 0%, 85% 100%, 15% 100%)',
  'triangle-up':     'polygon(50% 0%, 100% 100%, 0% 100%)',
  'triangle-right-angle': 'polygon(0% 0%, 100% 100%, 0% 100%)',
  'triangle-down':   'polygon(0% 0%, 100% 0%, 50% 100%)',
  'triangle-right':  'polygon(0% 0%, 100% 50%, 0% 100%)',
  'triangle-left':   'polygon(100% 0%, 0% 50%, 100% 100%)',
  pentagon:          'polygon(50% 0%, 100% 38%, 82% 100%, 18% 100%, 0% 38%)',
  hexagon:           'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)',
  octagon:           'polygon(30% 0%, 70% 0%, 100% 30%, 100% 70%, 70% 100%, 30% 100%, 0% 70%, 0% 30%)',
  'star-5':          'polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)',
  'star-4':          'polygon(50% 0%, 60% 40%, 100% 50%, 60% 60%, 50% 100%, 40% 60%, 0% 50%, 40% 40%)',
  'star-6':          'polygon(50% 0%, 58% 17%, 79% 7%, 71% 26%, 93% 25%, 82% 43%, 100% 50%, 82% 57%, 93% 75%, 71% 74%, 79% 93%, 58% 83%, 50% 100%, 42% 83%, 21% 93%, 29% 74%, 7% 75%, 18% 57%, 0% 50%, 18% 43%, 7% 25%, 29% 26%, 21% 7%, 42% 17%)',
  'star-burst':      'polygon(50% 0%, 60% 22%, 82% 18%, 78% 40%, 100% 50%, 78% 60%, 82% 82%, 60% 78%, 50% 100%, 40% 78%, 18% 82%, 22% 60%, 0% 50%, 22% 40%, 18% 18%, 40% 22%)',
  'arrow-right':     'polygon(0% 25%, 60% 25%, 60% 0%, 100% 50%, 60% 100%, 60% 75%, 0% 75%)',
  'arrow-curved':    'polygon(70% 0%, 100% 22%, 82% 22%, 82% 50%, 62% 72%, 34% 72%, 24% 62%, 24% 46%, 40% 46%, 40% 56%, 56% 56%, 66% 46%, 66% 22%, 48% 22%)',
  'arrow-left':      'polygon(40% 0%, 40% 25%, 100% 25%, 100% 75%, 40% 75%, 40% 100%, 0% 50%)',
  'arrow-up':        'polygon(25% 40%, 0% 40%, 50% 0%, 100% 40%, 75% 40%, 75% 100%, 25% 100%)',
  'arrow-down':      'polygon(25% 0%, 75% 0%, 75% 60%, 100% 60%, 50% 100%, 0% 60%, 25% 60%)',
  'arrow-double-h':  'polygon(0% 50%, 20% 0%, 20% 35%, 80% 35%, 80% 0%, 100% 50%, 80% 100%, 80% 65%, 20% 65%, 20% 100%)',
  'arrow-double-v':  'polygon(50% 0%, 100% 20%, 65% 20%, 65% 80%, 100% 80%, 50% 100%, 0% 80%, 35% 80%, 35% 20%, 0% 20%)',
  'chevron-right':   'polygon(0% 0%, 70% 0%, 100% 50%, 70% 100%, 0% 100%, 30% 50%)',
  'chevron-left':    'polygon(30% 0%, 100% 0%, 70% 50%, 100% 100%, 30% 100%, 0% 50%)',
  cross:             'polygon(33% 0%, 67% 0%, 67% 33%, 100% 33%, 100% 67%, 67% 67%, 67% 100%, 33% 100%, 33% 67%, 0% 67%, 0% 33%, 33% 33%)',
  'x-mark':          'polygon(10% 0%, 50% 40%, 90% 0%, 100% 10%, 60% 50%, 100% 90%, 90% 100%, 50% 60%, 10% 100%, 0% 90%, 40% 50%, 0% 10%)',
  heart:             'polygon(50% 30%, 20% 5%, 0% 25%, 0% 50%, 50% 95%, 100% 50%, 100% 25%, 80% 5%)',
  badge:             'polygon(50% 0%, 63% 12%, 79% 8%, 83% 25%, 98% 33%, 91% 50%, 98% 67%, 83% 75%, 79% 92%, 63% 88%, 50% 100%, 37% 88%, 21% 92%, 17% 75%, 2% 67%, 9% 50%, 2% 33%, 17% 25%, 21% 8%, 37% 12%)',
  ribbon:            'polygon(0% 0%, 100% 0%, 100% 55%, 80% 55%, 100% 100%, 50% 73%, 0% 100%, 20% 55%, 0% 55%)',
  frame:             'polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%, 12% 12%, 12% 88%, 88% 88%, 88% 12%, 12% 12%)',
  'frame-thick':     'polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%, 18% 18%, 18% 82%, 82% 82%, 82% 18%, 18% 18%)',
  'frame-thin':      'polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%, 8% 8%, 8% 92%, 92% 92%, 92% 8%, 8% 8%)',
  'frame-notch':     'polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%, 14% 8%, 86% 8%, 92% 14%, 92% 86%, 86% 92%, 14% 92%, 8% 86%, 8% 14%, 14% 8%)',
  callout:           'polygon(0% 0%, 100% 0%, 100% 75%, 55% 75%, 50% 100%, 45% 75%, 0% 75%)',
  'callout-ellipse': 'polygon(8% 42%, 12% 25%, 24% 12%, 40% 6%, 60% 6%, 76% 12%, 88% 25%, 92% 40%, 88% 55%, 76% 68%, 66% 76%, 70% 94%, 54% 82%, 38% 82%, 24% 76%, 12% 64%, 8% 52%)',
  'callout-cloud':   'polygon(14% 60%, 8% 46%, 14% 33%, 26% 28%, 32% 18%, 46% 14%, 58% 18%, 70% 14%, 82% 22%, 88% 34%, 86% 46%, 92% 58%, 86% 70%, 74% 76%, 62% 76%, 56% 92%, 46% 78%, 32% 78%, 22% 72%)',
  'callout-burst':   'polygon(6% 18%, 26% 10%, 44% 0%, 58% 12%, 80% 8%, 90% 24%, 100% 40%, 92% 56%, 100% 74%, 84% 84%, 68% 96%, 54% 84%, 34% 90%, 20% 82%, 6% 70%, 0% 52%, 8% 38%)',
  'callout-top':     'polygon(0% 25%, 45% 25%, 50% 0%, 55% 25%, 100% 25%, 100% 100%, 0% 100%)',
  'callout-left':    'polygon(20% 0%, 100% 0%, 100% 100%, 20% 100%, 20% 60%, 0% 50%, 20% 40%)',
  'callout-right':   'polygon(0% 0%, 80% 0%, 80% 40%, 100% 50%, 80% 60%, 80% 100%, 0% 100%)',
};


const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

const getPrefixedLayoutValue = (layout = {}, prefix = '', key, fallback) => {
  const prefixedKey = prefix ? `${prefix}${key[0].toUpperCase()}${key.slice(1)}` : key;
  return layout[prefixedKey] ?? fallback;
};

const easingFns = {
  linear: (t) => t,
  'ease-in': (t) => t * t * t,
  'ease-out': (t) => 1 - ((1 - t) ** 3),
  'ease-in-out': (t) => (t < 0.5 ? 4 * t * t * t : 1 - ((-2 * t + 2) ** 3) / 2),
  quadratic: (t) => t * t,
  'quadratic-out': (t) => 1 - ((1 - t) * (1 - t)),
  smoothstep: (t) => t * t * (3 - 2 * t),
};

const buildCssOpacityStops = (endOpacity, easing = 'linear') => {
  const ease = easingFns[easing] ?? easingFns.linear;
  const stops = [];

  for (let i = 0; i <= 10; i += 1) {
    const t = i / 10;
    const eased = ease(t);
    const opacity = 1 + ((endOpacity - 1) * eased);
    stops.push(`rgba(255, 255, 255, ${opacity.toFixed(4)}) ${Math.round(t * 100)}%`);
  }

  return stops.join(', ');
};

export function buildTransparencyMaskStyle(layout = {}, {
  prefix = '',
  opacityKey = 'opacity',
  defaultOpacity = 100,
  effectBleed = 0,
} = {}) {
  const type = getPrefixedLayoutValue(layout, prefix, 'transparencyType', 'flat');

  if (!type || type === 'flat') {
    return {
      opacity: `${clamp(Number(layout[opacityKey] ?? defaultOpacity), 0, 100) / 100}`,
    };
  }

  const endOpacity = clamp(Number(getPrefixedLayoutValue(layout, prefix, 'transparencyFadeOpacity', 0)), 0, 100) / 100;
  const centerX = clamp(Number(getPrefixedLayoutValue(layout, prefix, 'transparencyCenterX', 50)), 0, 100);
  const centerY = clamp(Number(getPrefixedLayoutValue(layout, prefix, 'transparencyCenterY', 50)), 0, 100);
  const radius = clamp(Number(getPrefixedLayoutValue(layout, prefix, 'transparencyRadius', 70)), 1, 150);
  const radiusX = clamp(Number(getPrefixedLayoutValue(layout, prefix, 'transparencyRadiusX', 70)), 1, 150);
  const radiusY = clamp(Number(getPrefixedLayoutValue(layout, prefix, 'transparencyRadiusY', 45)), 1, 150);
  const rotation = Number(getPrefixedLayoutValue(layout, prefix, 'transparencyRotation', 0));
  const startX = clamp(Number(getPrefixedLayoutValue(layout, prefix, 'transparencyStartX', 0)), 0, 100);
  const startY = clamp(Number(getPrefixedLayoutValue(layout, prefix, 'transparencyStartY', 50)), 0, 100);
  const endX = clamp(Number(getPrefixedLayoutValue(layout, prefix, 'transparencyEndX', 100)), 0, 100);
  const endY = clamp(Number(getPrefixedLayoutValue(layout, prefix, 'transparencyEndY', 50)), 0, 100);
  const easing = getPrefixedLayoutValue(layout, prefix, 'transparencyEasing', 'linear');
  const opacityStops = buildCssOpacityStops(endOpacity, easing);
  const linearAngle = (Math.atan2(endY - startY, endX - startX) * 180 / Math.PI) + 90;
  const radialRadiusX = type === 'ellipse' ? radiusX : radius;
  const radialRadiusY = type === 'ellipse' ? radiusY : radius;
  const maskImage = type === 'linear'
    ? `linear-gradient(${linearAngle}deg, ${opacityStops})`
    : `radial-gradient(ellipse ${radialRadiusX}% ${radialRadiusY}% at ${centerX}% ${centerY}%, ${opacityStops})`;
  const bleed = Math.max(0, Number(effectBleed ?? 0));
  const bleedStyle = bleed > 0 ? {
    margin: `-${bleed}px`,
    padding: `${bleed}px`,
    boxSizing: 'content-box',
    overflow: 'visible',
  } : {};

  return {
    opacity: '1',
    WebkitMaskImage: maskImage,
    maskImage,
    WebkitMaskSize: '100% 100%',
    maskSize: '100% 100%',
    WebkitMaskRepeat: 'no-repeat',
    maskRepeat: 'no-repeat',
    WebkitMaskPosition: 'center',
    maskPosition: 'center',
    maskMode: 'alpha',
    WebkitMaskMode: 'alpha',
    ...bleedStyle,
  };
}

export function buildOutlineCss(layout = {}, { defaultColor = '#ffffff', fallbackWhenDisabled = '0' } = {}) {
  if (!layout.border) {
    return fallbackWhenDisabled;
  }

  const width = Math.max(1, Number(layout.contourWidth || 1));
  const style = layout.borderStyle || 'solid';
  const color = layout.contourColor || defaultColor;

  return `${width}px ${style} ${color}`;
}

export function buildOutlineStyle(layout = {}, options = {}) {
  return {
    border: '0',
    outline: buildOutlineCss(layout, options),
    outlineOffset: '0px',
  };
}

export function buildBorderCss(layout = {}, options = {}) {
  return buildOutlineCss(layout, options);
}

export function buildEditorElements(state) {
  const metaText = [state.content?.date, state.content?.time].filter(Boolean).join(' ? ');
  const contactText = [state.content?.location, state.content?.platform, state.content?.contact].filter(Boolean).join(' ? ');
  const extraText = [state.content?.teacher, state.content?.price, state.content?.extra].filter(Boolean).join(' ? ');
  const baseTextElements = [
    { id: 'title', type: 'text', label: 'Titulo', text: state.content?.title ?? '' },
    { id: 'subtitle', type: 'text', label: 'Subtitulo', text: state.content?.subtitle ?? '' },
    { id: 'meta', type: 'text', label: 'Fecha / hora', text: metaText },
    { id: 'contact', type: 'text', label: 'Contacto', text: contactText },
    { id: 'extra', type: 'text', label: 'Texto adicional', text: extraText },
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

const normalizeIntrinsicSize = (width, height) => {
  const normalizedWidth = Number(width ?? 0);
  const normalizedHeight = Number(height ?? 0);

  if (!Number.isFinite(normalizedWidth) || !Number.isFinite(normalizedHeight) || normalizedWidth <= 0 || normalizedHeight <= 0) {
    return null;
  }

  return {
    width: normalizedWidth,
    height: normalizedHeight,
  };
};

export function buildCoverImageStyle({
  containerWidth,
  containerHeight,
  imageWidth,
  imageHeight,
  cropScale = 1,
  cropOffsetX = 0,
  cropOffsetY = 0,
  flipX = false,
  flipY = false,
  opacity = null,
  transparencyLayout = null,
  transparencyPrefix = '',
  transparencyOpacityKey = 'opacity',
} = {}) {
  const normalizedContainerWidth = Number(containerWidth ?? 0);
  const normalizedContainerHeight = Number(containerHeight ?? 0);
  const intrinsicSize = normalizeIntrinsicSize(imageWidth, imageHeight);
  const opacityStyle = transparencyLayout
    ? buildTransparencyMaskStyle(transparencyLayout, {
        prefix: transparencyPrefix,
        opacityKey: transparencyOpacityKey,
        defaultOpacity: opacity ?? 100,
      })
    : (opacity === null || opacity === undefined
    ? {}
    : { opacity: `${clamp(Number(opacity ?? 100), 0, 100) / 100}` });

  if (!Number.isFinite(normalizedContainerWidth) || !Number.isFinite(normalizedContainerHeight) || normalizedContainerWidth <= 0 || normalizedContainerHeight <= 0 || !intrinsicSize) {
    return {
      width: '100%',
      height: '100%',
      objectFit: 'cover',
      transform: `scale(${flipX ? -1 : 1}, ${flipY ? -1 : 1})`,
      transformOrigin: 'center center',
      ...opacityStyle,
    };
  }

  const safeCropScale = Math.max(1, Number(cropScale ?? 1));
  const baseScale = Math.max(
    normalizedContainerWidth / intrinsicSize.width,
    normalizedContainerHeight / intrinsicSize.height,
  );
  const renderedWidth = intrinsicSize.width * baseScale * safeCropScale;
  const renderedHeight = intrinsicSize.height * baseScale * safeCropScale;
  const maxOffsetX = Math.max(0, (renderedWidth - normalizedContainerWidth) / 2);
  const maxOffsetY = Math.max(0, (renderedHeight - normalizedContainerHeight) / 2);
  const normalizedOffsetX = clamp(Number(cropOffsetX ?? 0), -1, 1);
  const normalizedOffsetY = clamp(Number(cropOffsetY ?? 0), -1, 1);
  const offsetX = normalizedOffsetX * maxOffsetX;
  const offsetY = normalizedOffsetY * maxOffsetY;

  return {
    position: 'absolute',
    left: `${(normalizedContainerWidth - renderedWidth) / 2 + offsetX}px`,
    top: `${(normalizedContainerHeight - renderedHeight) / 2 + offsetY}px`,
    width: `${renderedWidth}px`,
    height: `${renderedHeight}px`,
    maxWidth: 'none',
    maxHeight: 'none',
    transform: `scale(${flipX ? -1 : 1}, ${flipY ? -1 : 1})`,
    transformOrigin: 'center center',
    ...opacityStyle,
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

  if (layout.textEffectMode === 'distort') {
    const primaryColor = layout.shadowColor || '#f0f';
    const secondaryColor = layout.neonColor || '#0ff';
    const distance = clamp(Math.round(clamp(Number(layout.shadowOffset ?? 15), 0, 20) * 0.2), 1, 20);
    const offset = toShadowOffset(distance);
    shadows.push(
      `${offset.x}px ${offset.y}px 0 ${primaryColor}`,
      `${-offset.x}px ${-offset.y}px 0 ${secondaryColor}`,
    );
  }

  if (layout.shadow && layout.textEffectMode !== 'distort') {
    const color = layout.shadowColor || '#0f172a';
    const preset = layout.shadowPreset || 'soft';
    const colorWithAlpha = applyAlphaToHex(color, shadowOpacity);

    if (preset === 'hard') {
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
    } else if (preset === 'lifted') {
      const y = Math.round(8 + shadowIntensity / 4);
      const blur = Math.round(10 + shadowIntensity / 2);
      shadows.push(`0 ${y}px ${blur}px ${colorWithAlpha}`);
    } else {
      const distance = Math.round(shadowOffset * 0.6);
      const blur = Math.round(shadowBlur * 0.8);
      const offset = toShadowOffset(distance);
      shadows.push(`${offset.x}px ${offset.y}px ${blur}px ${colorWithAlpha}`);
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
}

export function buildShapeStyleFromKind(shapeKind, base, shapeClipPaths = {}) {
  if (shapeKind === 'circle' || shapeKind === 'ellipse') {
    return { ...base, borderRadius: '9999px' };
  }
  if (shapeKind === 'frame-rounded') {
    const frameWidth = 8;
    const frameColor = base.frameColor || base.background || 'currentColor';
    const frameShadow = `inset 0 0 0 ${frameWidth}px ${frameColor}`;
    const frameBorderShadow = base.outline && base.outline !== '0'
      ? `inset 0 0 0 ${frameWidth + Math.max(1, Number(base.outlineWidth || 1))}px ${base.outlineColor || '#ffffff'}`
      : null;
    const boxShadow = [
      base.boxShadow && base.boxShadow !== 'none' ? base.boxShadow : null,
      frameShadow,
      frameBorderShadow,
    ].filter(Boolean).join(', ');

    return {
      ...base,
      borderRadius: '22px',
      background: 'transparent',
      boxShadow,
      border: '0',
      outline: base.outline || '0',
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
  const outlineWidth = Math.max(1, Number(layout.contourWidth || 1));
  const outlineColor = layout.contourColor || '#ffffff';
  const fill = shapeKind === 'frame-rounded'
    ? (layout.backgroundColor && layout.backgroundColor !== 'transparent'
      ? layout.backgroundColor
      : (layout.contourColor || '#38bdf8'))
    : (layout.fillMode === 'gradient'
    ? `linear-gradient(${layout.gradientAngle || 135}deg, ${layout.gradientStart || '#0ea5e9'}, ${layout.gradientEnd || '#8b5cf6'})`
    : (layout.backgroundColor && layout.backgroundColor !== 'transparent' ? layout.backgroundColor : '#ffffff'));

  const base = {
    width: '100%',
    height: '100%',
    background: fill,
    frameColor: fill,
    outlineWidth,
    outlineColor,
    boxShadow: buildVisualShadow(layout),
    ...buildOutlineStyle(layout, { defaultColor: '#ffffff', fallbackWhenDisabled: '0' }),
  };

  return buildShapeStyleFromKind(shapeKind, base, shapeClipPaths);
}

export function buildShapeRenderModel(layout = {}, shapeKind, shapeClipPaths = {}) {
  const clipPath = shapeClipPaths[shapeKind] ?? null;
  const usesClipPath = Boolean(clipPath);
  const borderWidth = Math.max(1, Number(layout.contourWidth || 1));
  const fill = layout.fillMode === 'gradient'
    ? `linear-gradient(${layout.gradientAngle || 135}deg, ${layout.gradientStart || '#0ea5e9'}, ${layout.gradientEnd || '#8b5cf6'})`
    : (layout.backgroundColor && layout.backgroundColor !== 'transparent' ? layout.backgroundColor : '#ffffff');

  if (!layout.border || !usesClipPath) {
    return {
      outerStyle: buildShapeStyle(layout, shapeKind, shapeClipPaths),
      innerStyle: null,
      svgStroke: null,
    };
  }

  const polygonMatch = clipPath.match(/^polygon\((.+)\)$/i);
  const points = polygonMatch
    ? polygonMatch[1]
        .split(',')
        .map((point) => point.trim().replace(/\s+/g, ' '))
        .map((point) => point.replace(/%/g, ''))
        .join(' ')
    : null;

  if (points) {
    return {
      outerStyle: buildShapeStyleFromKind(shapeKind, {
        width: '100%',
        height: '100%',
        background: fill,
        boxShadow: buildVisualShadow(layout),
        border: '0',
        outline: '0',
      }, shapeClipPaths),
      innerStyle: null,
      svgStroke: {
        points,
        stroke: layout.contourColor || '#ffffff',
        strokeWidth: borderWidth,
        dasharray: layout.borderStyle === 'dashed'
          ? `${borderWidth * 4} ${borderWidth * 2}`
          : (layout.borderStyle === 'dotted' ? `0 ${borderWidth * 2.2}` : null),
        linecap: layout.borderStyle === 'dotted' ? 'round' : 'butt',
        linejoin: 'round',
      },
    };
  }

  return {
    outerStyle: buildShapeStyle(layout, shapeKind, shapeClipPaths),
    innerStyle: null,
    svgStroke: null,
  };
}

export function buildImageFrameStyle(layout = {}) {
  const hasAdvancedTransparency = layout?.transparencyType && layout.transparencyType !== 'flat';
  const fallbackRadius = Number(layout.borderRadius ?? 12);
  const topLeft = Number(layout.borderRadiusTopLeft ?? fallbackRadius);
  const topRight = Number(layout.borderRadiusTopRight ?? fallbackRadius);
  const bottomRight = Number(layout.borderRadiusBottomRight ?? fallbackRadius);
  const bottomLeft = Number(layout.borderRadiusBottomLeft ?? fallbackRadius);

  return {
    position: 'relative',
    width: '100%',
    height: '100%',
    overflow: 'hidden',
    borderRadius: `${topLeft}px ${topRight}px ${bottomRight}px ${bottomLeft}px`,
    backgroundColor: hasAdvancedTransparency
      ? 'transparent'
      : (layout.backgroundColor && layout.backgroundColor !== 'transparent' ? layout.backgroundColor : 'rgba(255,255,255,0.2)'),
    ...buildOutlineStyle(layout, { defaultColor: '#ffffff', fallbackWhenDisabled: '0' }),
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
  const transparencyType = layout?.transparencyType ?? 'flat';
  const transparencyStyle = buildTransparencyMaskStyle(layout, {
    effectBleed: transparencyType === 'flat' ? 0 : 56,
  });

  if (elementType !== 'text') {
    return {
      width: '100%',
      height: '100%',
      ...transparencyStyle,
    };
  }

  const hasBackground = layout.backgroundColor && layout.backgroundColor !== 'transparent';
  const backgroundOpacity = clamp(Number(layout.backgroundOpacity ?? 70), 0, 100);
  const backgroundExpand = clamp(Number(layout.backgroundPadding ?? 5), 0, 100);
  const backgroundAlphaHex = Math.round((backgroundOpacity / 100) * 255).toString(16).padStart(2, '0');
  const resolvedBackground = hasBackground && /^#[\da-f]{6}$/i.test(layout.backgroundColor)
    ? `${layout.backgroundColor}${backgroundAlphaHex}`
    : (hasBackground ? layout.backgroundColor : 'transparent');
  const flatOpacityStyle = transparencyType === 'flat'
    ? { opacity: `${(layout.opacity ?? 100) / 100}` }
    : { opacity: '1' };

  return {
    ...flatOpacityStyle,
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
  const transparencyType = layout?.transparencyType ?? 'flat';
  const transparencyStyle = buildTransparencyMaskStyle(layout, {
    effectBleed: transparencyType === 'flat' ? 0 : 56,
  });

  return {
    textShadow: buildTextShadow(layout, firstParagraphColor),
    WebkitTextStroke: layout?.border && layout?.hollowText && strokeWidth > 0
      ? `${strokeWidth}px ${firstParagraphColor}`
      : '0',
    WebkitTextFillColor: layout?.hollowText ? 'transparent' : undefined,
    color: layout?.hollowText ? 'transparent' : undefined,
    ...transparencyStyle,
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

export function applyFormatToDimensions(dimensions, format) {
  const width = Number(dimensions?.width ?? 0);
  const height = Number(dimensions?.height ?? 0);
    const horizontalFormats = new Set(['horizontal', 'diptych', 'triptych', 'brochure']);

  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    return dimensions;
  }

  if (horizontalFormats.has(format) && height > width) {
    return { ...dimensions, width: height, height: width };
  }

  if (format === 'vertical' && width > height) {
    return { ...dimensions, width: height, height: width };
  }

  if (format === 'square') {
    const side = Math.max(width, height);
    return { ...dimensions, width: side, height: side };
  }

  return dimensions;
}
