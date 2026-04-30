import { reactive, computed, watch, ref, shallowRef } from 'vue';
import { buildFontString, measureTextWidth } from '../utils/editorShared';

export const LINKED_TEXT_STYLE_ATTRS = [
  'fontSize', 'color', 'fontFamily', 'fontWeight', 'italic',
  'underline', 'uppercase', 'textAlign', 'letterSpacing', 'lineHeight'
];

export function parseHtmlToStyledSpans(html, defaultStyle = {}) {
  if (!html) return [];
  const temp = document.createElement('div');
  temp.innerHTML = html;
  return parseNodeToSpans(temp, defaultStyle);
}

function parseNodeToSpans(node, parentStyle = {}) {
  const spans = [];

  for (const child of node.childNodes) {
    if (child.nodeType === Node.TEXT_NODE) {
      const text = child.textContent;
      if (text) {
        spans.push({ text, style: { ...parentStyle } });
      }
    } else if (child.nodeType === Node.ELEMENT_NODE) {
      const tagName = child.tagName.toLowerCase();
      const blockTags = new Set(['p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']);
      const inlineTags = new Set(['strong', 'b', 'em', 'i', 'u', 'span', 'a', 'mark']);

      if (blockTags.has(tagName)) {
        if (spans.length > 0 && spans[spans.length - 1].text !== '\n') {
          spans.push({ text: '\n', style: { ...parentStyle } });
        }
        const childSpans = parseNodeToSpans(child, parentStyle);
        spans.push(...childSpans);
        if (spans.length > 0 && spans[spans.length - 1].text !== '\n') {
          spans.push({ text: '\n', style: { ...parentStyle } });
        }
        continue;
      }

      if (!inlineTags.has(tagName)) {
        const childSpans = parseNodeToSpans(child, parentStyle);
        spans.push(...childSpans);
        continue;
      }

      const newStyle = { ...parentStyle };
      if (tagName === 'strong' || tagName === 'b') newStyle.fontWeight = 'bold';
      if (tagName === 'em' || tagName === 'i') newStyle.italic = true;
      if (tagName === 'u') newStyle.underline = true;

      const css = child.style;
      if (css.color) newStyle.color = css.color;
      if (css.fontSize) {
        const match = css.fontSize.match(/(\d+(?:\.\d+)?)/);
        if (match) newStyle.fontSize = parseFloat(match[1]);
      }
      if (css.fontFamily) newStyle.fontFamily = css.fontFamily;
      if (css.fontWeight === 'bold' || css.fontWeight === '700') newStyle.fontWeight = 'bold';
      if (css.fontStyle === 'italic') newStyle.italic = true;
      if (css.textDecoration === 'underline') newStyle.underline = true;
      if (css.textTransform === 'uppercase') newStyle.uppercase = true;
      if (css.letterSpacing) {
        const match = css.letterSpacing.match(/(\d+(?:\.\d+)?)/);
        if (match) newStyle.letterSpacing = parseFloat(match[1]);
      }
      if (css.lineHeight) {
        const match = css.lineHeight.match(/(\d+(?:\.\d+)?)/);
        if (match) newStyle.lineHeight = parseFloat(match[1]);
      }

      const childSpans = parseNodeToSpans(child, newStyle);
      spans.push(...childSpans);
    }
  }
  return spans;
}

export function styledSpansToHtml(spans) {
  if (!spans || spans.length === 0) return '';
  return spans.map(span => {
    if (!span.text) return '';
    let text = span.text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    if (span.style.uppercase) text = text.toUpperCase();

    const styleParts = [];
    if (span.style.color) styleParts.push(`color:${span.style.color}`);
    if (span.style.fontSize) styleParts.push(`font-size:${span.style.fontSize}px`);
    if (span.style.fontFamily) styleParts.push(`font-family:${span.style.fontFamily}`);
    if (span.style.fontWeight === 'bold') styleParts.push('font-weight:700');
    if (span.style.italic) styleParts.push('font-style:italic');
    if (span.style.underline) styleParts.push('text-decoration:underline');
    if (span.style.letterSpacing) styleParts.push(`letter-spacing:${span.style.letterSpacing}px`);
    if (span.style.lineHeight) styleParts.push(`line-height:${span.style.lineHeight}`);

    const styleStr = styleParts.length > 0 ? `style="${styleParts.join(';')}"` : '';

    if (span.style.fontWeight === 'bold') return `<strong ${styleStr}>${text}</strong>`;
    if (span.style.italic) return `<em ${styleStr}>${text}</em>`;
    if (styleStr) return `<span ${styleStr}>${text}</span>`;
    return text;
  }).join('');
}

function buildSpanFontString(style = {}) {
  return buildFontString({
    fontSize: style.fontSize || 18,
    fontFamily: style.fontFamily || 'Inter, sans-serif',
    fontWeight: style.fontWeight || 'regular',
    italic: style.italic || false,
    letterSpacing: style.letterSpacing || 0,
  });
}

function measureSpanWidth(span) {
  let text = span.text || '';
  if (span.style.uppercase) text = text.toUpperCase();
  return measureTextWidth(text, {
    fontSize: span.style.fontSize || 18,
    fontFamily: span.style.fontFamily || 'Inter, sans-serif',
    fontWeight: span.style.fontWeight || 'regular',
    italic: span.style.italic || false,
    letterSpacing: span.style.letterSpacing || 0,
  });
}

function getSpanLineHeight(span) {
  return (span.style.fontSize || 18) * (span.style.lineHeight || 1.4);
}

function breakSpanIntoLines(span, maxWidth) {
  const lines = [];
  const text = span.text || '';
  if (!text) return lines;

  const fontStr = buildSpanFontString(span.style);
  const tempCanvas = document.createElement('canvas');
  const ctx = tempCanvas.getContext('2d');
  ctx.font = fontStr;

  let currentLine = '';
  let currentWidth = 0;
  const letterSpacing = span.style.letterSpacing || 0;

  for (const char of text) {
    const charWidth = ctx.measureText(char).width + letterSpacing;
    const testWidth = currentWidth + charWidth;

    if (testWidth <= maxWidth) {
      currentLine += char;
      currentWidth = testWidth;
    } else {
      if (currentLine) {
        lines.push({ text: currentLine, style: span.style, width: currentWidth });
      }
      currentLine = char;
      currentWidth = ctx.measureText(char).width + letterSpacing;
    }
  }

  if (currentLine) {
    lines.push({ text: currentLine, style: span.style, width: currentWidth });
  }

  return lines;
}

function allocateSpansToBox(spans, boxWidth, boxHeight, boxStyle = {}) {
  const fittingLines = [];
  const fittingSpans = [];
  let currentHeight = 0;
  const lineHeight = getSpanLineHeight({ style: boxStyle });
  let overflowSpans = [];
  let fullyProcessed = true;

  for (let i = 0; i < spans.length; i++) {
    const span = spans[i];
    const spanLines = breakSpanIntoLines(span, boxWidth);

    for (let li = 0; li < spanLines.length; li++) {
      const line = spanLines[li];

      if (currentHeight + getSpanLineHeight({ style: line.style }) > boxHeight) {
        if (li === 0) {
          overflowSpans = spans.slice(i);
        } else {
          overflowSpans = [{ text: span.text.substring(spanLines.slice(0, li).map(l => l.text).join('').length), style: span.style }];
          for (let ri = i + 1; ri < spans.length; ri++) {
            overflowSpans.push(spans[ri]);
          }
        }
        fullyProcessed = false;
        return { fittingSpans, fittingLines, overflowSpans, fullyProcessed };
      }

      fittingLines.push(line);
      fittingSpans.push({ text: line.text, style: line.style });
      currentHeight += getSpanLineHeight({ style: line.style });
    }
  }

  return { fittingSpans, fittingLines, overflowSpans, fullyProcessed };
}

export function distributeTextToLinkedBoxes(fullHtml, chainLayouts, defaultStyle = {}) {
  if (!chainLayouts || chainLayouts.length === 0) return [];
  if (!fullHtml) return chainLayouts.map(() => ({ html: '', overflowHtml: '', fitsInBox: true }));

  const spans = parseHtmlToStyledSpans(fullHtml, defaultStyle);
  if (spans.length === 0) return chainLayouts.map(() => ({ html: '', overflowHtml: '', fitsInBox: true }));

  const results = [];
  let remainingSpans = spans;

  for (let i = 0; i < chainLayouts.length; i++) {
    const layout = chainLayouts[i];
    const boxW = layout.w || 300;
    const boxH = layout.h || 120;
    const isLastBox = i === chainLayouts.length - 1;

    if (remainingSpans.length === 0) {
      results.push({ html: '', overflowHtml: '', fitsInBox: true, spans: [] });
      continue;
    }

    const boxStyle = {
      fontSize: layout.fontSize || defaultStyle.fontSize || 18,
      fontFamily: layout.fontFamily || defaultStyle.fontFamily || 'Inter, sans-serif',
      fontWeight: layout.fontWeight || defaultStyle.fontWeight || 'regular',
      italic: layout.italic || false,
      letterSpacing: layout.letterSpacing || 0,
      lineHeight: layout.lineHeight || defaultStyle.lineHeight || 1.4,
    };

    const { fittingSpans, overflowSpans, fullyProcessed } = allocateSpansToBox(
      remainingSpans, boxW, boxH, boxStyle
    );

    const fittingHtml = styledSpansToHtml(fittingSpans);
    const overflowHtml = styledSpansToHtml(overflowSpans);

    results.push({
      html: fittingHtml,
      overflowHtml: isLastBox ? overflowHtml : '',
      fitsInBox: fullyProcessed && overflowSpans.length === 0,
      spans: fittingSpans
    });

    remainingSpans = overflowSpans;
  }

  return results;
}

export function createLinkedTextFlowManager() {
  const flows = new Map();

  const getOrCreateFlow = (groupId, state) => {
    if (flows.has(groupId)) {
      return flows.get(groupId);
    }

    const flow = createFlowForGroup(groupId, state);
    flows.set(groupId, flow);
    return flow;
  };

  const createFlowForGroup = (groupId, state) => {
    const flowState = reactive({
      groupId,
      chain: [],
      allocations: [],
      activeEditorId: null,
      cursorPositions: {},
      editingState: null
    });

    const recalculateChain = () => {
      if (!state?.customElements || !state?.elementLayout) return [];

      return Object.entries(state.customElements)
        .filter(([id, el]) =>
          el?.type === 'linkedText' &&
          state.elementLayout[id]?.linkedTextGroupId === groupId
        )
        .map(([id]) => id)
        .sort((a, b) => {
          const indexA = state.elementLayout[a]?.linkedTextChainIndex ?? 0;
          const indexB = state.elementLayout[b]?.linkedTextChainIndex ?? 0;
          return indexA - indexB;
        });
    };

    const getChainLayouts = () => {
      return flowState.chain.map(id => {
        const l = state.elementLayout[id] || {};
        return {
          id,
          w: l.w || 300,
          h: l.h || 120,
          fontSize: l.fontSize || 18,
          fontFamily: l.fontFamily || 'Poppins, sans-serif',
          fontWeight: l.fontWeight || 'regular',
          italic: l.italic || false,
          letterSpacing: l.letterSpacing || 0,
          lineHeight: l.lineHeight || 1.4,
        };
      });
    };

    const getHeadText = () => {
      if (flowState.chain.length === 0) return '';
      const headId = flowState.chain[0];
      return state.customElements[headId]?.text || '';
    };

    const recalculate = () => {
      flowState.chain = recalculateChain();
      if (flowState.chain.length === 0) {
        flowState.allocations = [];
        return;
      }

      const headText = getHeadText();
      const chainLayouts = getChainLayouts();

      if (chainLayouts.length === 0) return;

      const firstLayout = chainLayouts[0] || {};
      const defaultStyle = {
        fontSize: firstLayout.fontSize || 18,
        fontFamily: firstLayout.fontFamily || 'Poppins, sans-serif',
        fontWeight: firstLayout.fontWeight || 'regular',
        italic: firstLayout.italic || false,
        letterSpacing: firstLayout.letterSpacing || 0,
        lineHeight: firstLayout.lineHeight || 1.4,
      };

      flowState.allocations = distributeTextToLinkedBoxes(headText, chainLayouts, defaultStyle);
    };

    const setActiveEditor = (editorId) => {
      flowState.activeEditorId = editorId;
    };

    const getAllocationForBox = (boxId) => {
      const idx = flowState.chain.indexOf(boxId);
      if (idx === -1) return null;
      return flowState.allocations[idx] || null;
    };

    const updateTextInChain = (editorId, newText, selectionInfo = null) => {
      if (!flowState.chain.includes(editorId)) return;

      const headId = flowState.chain[0];
      if (state.customElements[headId]) {
        state.customElements[headId].text = newText;
      }

      recalculate();

      if (selectionInfo) {
        flowState.cursorPositions[editorId] = selectionInfo;
      }
    };

    const beginEditing = (editorId) => {
      flowState.editingState = {
        editorId,
        startText: getHeadText(),
        cursorsBefore: { ...flowState.cursorPositions }
      };
      flowState.activeEditorId = editorId;
    };

    const cancelEditing = () => {
      if (!flowState.editingState) return;
      const headId = flowState.chain[0];
      if (state.customElements[headId]) {
        state.customElements[headId].text = flowState.editingState.startText;
      }
      flowState.cursorPositions = { ...flowState.editingState.cursorsBefore };
      flowState.editingState = null;
      recalculate();
    };

    const finishEditing = (editorId, newText, selectionInfo) => {
      if (!flowState.editingState || flowState.editingState.editorId !== editorId) return;

      updateTextInChain(editorId, newText, selectionInfo);
      flowState.editingState = null;
    };

    return {
      flowState,
      recalculate,
      setActiveEditor,
      getAllocationForBox,
      beginEditing,
      cancelEditing,
      finishEditing,
      updateTextInChain,
      getHeadText,
      getChainLayouts
    };
  };

  const removeFlow = (groupId) => {
    flows.delete(groupId);
  };

  const getFlowByBoxId = (boxId, state) => {
    if (!state?.elementLayout?.[boxId]) return null;
    const groupId = state.elementLayout[boxId].linkedTextGroupId;
    if (!groupId) return null;
    return flows.get(groupId) || null;
  };

  return {
    getOrCreateFlow,
    removeFlow,
    getFlowByBoxId,
    flows
  };
}

let globalFlowManager = null;

export function useLinkedTextFlow() {
  if (!globalFlowManager) {
    globalFlowManager = createLinkedTextFlowManager();
  }
  return globalFlowManager;
}