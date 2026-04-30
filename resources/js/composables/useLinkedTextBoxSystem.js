import { reactive, ref, nextTick } from 'vue';
import { useFrontendLog } from './useFrontendLog';

/**
 * useLinkedTextBoxSystem - "Single Source, Multiple Viewports"
 *
 * Arquitectura:
 * - UN solo editor TipTap (fuente única de verdad)
 * - Múltiples frames que muestran fragmentos del contenido
 * - Fragmentación basada en DOM (medición real del navegador)
 * - Overflow visible con opacity 0.5
 */

const systems = new Map();

export function createLinkedTextBoxSystem() {
  const systemsMap = reactive(new Map());
  const activeEditorId = ref(null);

  /**
   * Crear o obtener un sistema para un grupo de cajas enlazadas
   */
  function getOrCreateSystem(groupId, config = {}) {
    if (systemsMap.has(groupId)) {
      return systemsMap.get(groupId);
    }

    const system = reactive({
      groupId,
      chain: [],           // Array de box IDs en orden
      editorId: null,      // ID de la caja que tiene el TipTap activo
      fragments: {},       // { [boxId]: { html, overflowHtml, fitsInBox } }
      fullHtml: '',        // HTML completo del texto
    });

    systemsMap.set(groupId, system);
    return system;
  }

  /**
   * Eliminar un sistema
   */
  function removeSystem(groupId) {
    systemsMap.delete(groupId);
  }

  /**
   * Obtener sistema por ID de caja
   */
  function getSystemByBoxId(boxId, state) {
    const layout = state.elementLayout?.[boxId];
    if (!layout?.linkedTextGroupId) return null;
    return systemsMap.get(layout.linkedTextGroupId) || null;
  }

  /**
   * Reconstruir la cadena de cajas enlazadas desde el estado
   */
  function rebuildChainFromState(headId, state) {
    const chain = [];
    let currentId = headId;

    while (currentId) {
      chain.push(currentId);
      const layout = state.elementLayout?.[currentId];
      currentId = layout?.linkedTextNext || null;
    }

    const groupId = state.elementLayout?.[headId]?.linkedTextGroupId;
    if (groupId) {
      const system = getOrCreateSystem(groupId);
      system.chain = chain;
    }

    return chain;
  }

  /**
   * Redistribuir texto completo entre todas las cajas de una cadena
   * Enfoque: Fragmentar por palabras usando medición del navegador
   */
  const redistribute = (groupId, fullHtml, chainLayouts, containerStyle = {}) => {
    const system = systemsMap.get(groupId);
    if (!system) return;

    system.fullHtml = fullHtml;
    system.fragments = {};

    if (!chainLayouts || chainLayouts.length === 0) return;
    if (!fullHtml || fullHtml.trim() === '') return;

    const frontendLog = useFrontendLog();

    // Parsear el HTML en párrafos con estilos
    const paragraphs = parseHtmlIntoParagraphs(fullHtml);

    // Log de párrafos parseados
    frontendLog.info('parseHtml',
      `HTML parseado en ${paragraphs.length} párrafos`,
      {
        groupId,
        inputHtml: fullHtml.substring(0, 300),
        paragraphs: paragraphs.map(p => ({
          tag: p.tag,
          style: p.style?.substring(0, 150),
          wordsCount: p.words.length,
          firstWords: p.words.slice(0, 3).join(' '),
        })),
      }
    );

    // Distribuir palabras entre frames
    const fragments = distributeWordsToFragments(paragraphs, chainLayouts, containerStyle);

    // Log de fragmentos generados
    frontendLog.info('buildFragments',
      `Generados ${fragments.length} fragmentos`,
      {
        groupId,
        fragments: fragments.map((f, i) => ({
          index: i,
          html: f.html?.substring(0, 200),
          htmlLength: f.html?.length || 0,
          hasOverflow: !!f.overflowHtml,
          fitsInBox: f.fitsInBox,
        })),
      }
    );

    // Asignar HTML a cada caja
    chainLayouts.forEach((layout, index) => {
      if (index < fragments.length) {
        system.fragments[layout.id] = {
          html: fragments[index].html,
          overflowHtml: fragments[index].overflowHtml || '',
          fitsInBox: fragments[index].fitsInBox ?? true,
        };
      } else {
        system.fragments[layout.id] = {
          html: '',
          overflowHtml: '',
          fitsInBox: true,
        };
      }
    });
  };

  /**
   * Parsear HTML en párrafos con sus estilos
   */
  function parseHtmlIntoParagraphs(html) {
    const temp = document.createElement('div');
    temp.innerHTML = html;

    const paragraphs = [];
    const nodes = Array.from(temp.childNodes);

    for (const node of nodes) {
      if (node.nodeType === Node.TEXT_NODE) {
        // Texto sin envolver - tratar como párrafo sin estilo
        const text = node.textContent.trim();
        if (text) {
          paragraphs.push({
            style: '',
            words: text.split(/\s+/).filter(w => w.length > 0),
          });
        }
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        // Elemento HTML - extraer estilo y palabras
        const style = node.getAttribute('style') || '';
        const text = node.textContent.trim();
        if (text) {
          paragraphs.push({
            style,
            words: text.split(/\s+/).filter(w => w.length > 0),
            tag: node.tagName.toLowerCase(),
          });
        }
      }
    }

    return paragraphs;
  }

  /**
   * Distribuir palabras entre fragments usando medición del navegador
   */
function distributeWordsToFragments(paragraphs, chainLayouts, containerStyle) {
    const results = [];
    const cutPoints = [];
    const paddingVertical = 2; // Padding mínimo
    const HEIGHT_TOLERANCE = 22; // Permite ~1 línea extra visualmente

    // Contar total de palabras
    const totalWords = paragraphs.reduce((sum, p) => sum + p.words.length, 0);

    // Crear contenedor de medición
    const measureDiv = document.createElement('div');
    measureDiv.style.position = 'absolute';
    measureDiv.style.left = '-9999px';
    measureDiv.style.top = '0';
    measureDiv.style.width = `${chainLayouts[0]?.w || 300}px`;
    measureDiv.style.overflow = 'visible';
    measureDiv.style.whiteSpace = 'pre-wrap';
    measureDiv.style.wordBreak = 'break-word';
    measureDiv.style.overflowWrap = 'break-word';
    applyContainerStyles(measureDiv, containerStyle);
    document.body.appendChild(measureDiv);

    const availableHeight = (chainLayouts[0]?.h || 120) - paddingVertical;

// Recorrer TODAS las palabras y medir dónde corta
    // También guardar de qué párrafo viene cada palabra para mantener estilos
    let wordsThatFit = [];
    let allOverflowWords = []; // Array de {word, paragraph}
    let splitIndex = 0;

    for (let p = 0; p < paragraphs.length; p++) {
      const paragraph = paragraphs[p];

      for (let w = 0; w < paragraph.words.length; w++) {
        const testWords = [...wordsThatFit.map(ow => ow.word), paragraph.words[w]];
        const testHtml = buildHtmlFromWords(paragraphs, p, w, testWords, '');

        measureDiv.innerHTML = testHtml;
        const newHeight = measureDiv.offsetHeight;

        if (newHeight <= availableHeight + HEIGHT_TOLERANCE) {
          wordsThatFit.push({word: paragraph.words[w], paragraphIndex: p});
          splitIndex++;
        } else {
          // Esta palabra no cabe - empieza el overflow
          allOverflowWords.push({word: paragraph.words[w], paragraphIndex: p});
        }
      }
    }

    document.body.removeChild(measureDiv);

    // Extraer solo las palabras de wordsThatFit para buildHtmlFromWords
    const fitWords = wordsThatFit.map(ow => ow.word);
    const html = buildHtmlFromWords(paragraphs, 0, 0, fitWords, '');

    // Para overflow, reconstruir con los párrafos originales manteniendo estilos
    let overflowHtml = '';
    if (allOverflowWords.length > 0) {
      // Agrupar palabras de overflow por párrafo
      let overflowParagraphs = [];
      let currentParaIndex = -1;
      let currentPara = null;

      for (const ow of allOverflowWords) {
        if (ow.paragraphIndex !== currentParaIndex) {
          if (currentPara) {
            overflowParagraphs.push(currentPara);
          }
          currentParaIndex = ow.paragraphIndex;
          currentPara = {
            ...paragraphs[currentParaIndex],
            words: [ow.word]
          };
        } else {
          currentPara.words.push(ow.word);
        }
      }
      if (currentPara) {
        overflowParagraphs.push(currentPara);
      }

      // Construir HTML del overflow con estilos preservados
      overflowHtml = overflowParagraphs.map(p => {
        const styleAttr = p.style ? ` style="${p.style}"` : '';
        const wordsHtml = p.words.join(' ');
        return `<${p.tag || 'p'}${styleAttr}>${wordsHtml}</${p.tag || 'p'}>`;
      }).join('');
    }

    const fitsInBox = allOverflowWords.length === 0;

    results.push({
      html,
      overflowHtml,
      fitsInBox,
    });

    const overflowWordCount = allOverflowWords.length;

    // Log detallado de la fragmentación
    const frontendLog = useFrontendLog();

    const wordsFitCount = wordsThatFit.length;

    frontendLog.info('fragmentDetail',
      `Fragmentación: ${wordsFitCount}/${totalWords} palabras caben, splitIndex=${splitIndex}, overflow=${overflowWordCount}`,
      {
        totalWords,
        wordsFitCount,
        splitIndex,
        overflowWordCount,
        hasOverflow: overflowWordCount > 0,
        framesCount: chainLayouts.length,
        results: results.map(r => ({
          html: r.html?.substring(0, 100),
          overflowHtml: r.overflowHtml?.substring(0, 100),
          fitsInBox: r.fitsInBox,
        })),
        frameDimensions: chainLayouts.map(l => ({
          id: l.id,
          h: l.h,
          availableHeight: l.h - 16,
        })),
        relationship: {
          explanation: 'Si box.h aumenta → wordsFitCount aumenta. Si box.h reduce → wordsFitCount reduce',
          boxHeightVsWordsFit: chainLayouts.map((l, i) => ({
            boxHeight: l.h,
            wordsFit: results[i]?.html?.split(/\s+/).filter(w => w).length || 0,
          })),
        },
        containerStyle: containerStyle,
        measureSettings: {
          padding: containerStyle.padding || '8px',
          fontSize: containerStyle.fontSize || 18,
          lineHeight: containerStyle.lineHeight || 1.4,
        },
      }
    );

    return results;
  }

  /**
   * Construir HTML a partir de palabras y estilos de párrafos
   */
  function buildHtmlFromWords(paragraphs, currentParagraphIndex, currentWordIndex, words, existingHtml) {
    if (words.length === 0) return existingHtml;

    // Verificar que el índice sea válido
    if (currentParagraphIndex < 0 || currentParagraphIndex >= paragraphs.length) {
      return existingHtml || `<p>${words.join(' ')}</p>`;
    }

    const paragraph = paragraphs[currentParagraphIndex];
    const style = paragraph.style || '';
    const tag = paragraph.tag || 'p';

    // Construir HTML con las palabras y el estilo del párrafo actual
    const styleAttr = style ? ` style="${style}"` : '';
    const result = `<${tag}${styleAttr}>${words.join(' ')}</${tag}>`;

    return result;
  }

  function applyContainerStyles(el, containerStyle) {
    if (containerStyle.padding) el.style.padding = containerStyle.padding;
    else el.style.padding = '8px';
    if (containerStyle.fontSize) el.style.fontSize = `${containerStyle.fontSize}px`;
    if (containerStyle.fontFamily) el.style.fontFamily = containerStyle.fontFamily;
    if (containerStyle.lineHeight) el.style.lineHeight = containerStyle.lineHeight;
    if (containerStyle.letterSpacing) el.style.letterSpacing = `${containerStyle.letterSpacing}px`;
  }

  /**
   * Obtener fragmento para una caja específica
   */
  function getFragmentForBox(groupId, boxId) {
    const system = systemsMap.get(groupId);
    if (!system) return { html: '', overflowHtml: '', fitsInBox: true };
    return system.fragments[boxId] || { html: '', overflowHtml: '', fitsInBox: true };
  }

  /**
   * Activar edición en una caja específica
   */
  function startEditing(groupId, boxId) {
    const system = systemsMap.get(groupId);
    if (!system) return;
    system.editorId = boxId;
    activeEditorId.value = boxId;
  }

  /**
   * Finalizar edición
   */
  function stopEditing(groupId) {
    const system = systemsMap.get(groupId);
    if (!system) return;
    system.editorId = null;
    if (activeEditorId.value === system.editorId) {
      activeEditorId.value = null;
    }
  }

  /**
   * Verificar si una caja está siendo editada
   */
  function isBoxBeingEdited(boxId) {
    return activeEditorId.value === boxId;
  }

  /**
   * Obtener el ID de la caja que está siendo editada en un grupo
   */
  function getEditingBoxId(groupId) {
    const system = systemsMap.get(groupId);
    return system?.editorId || null;
  }

  return {
    systems: systemsMap,
    activeEditorId,
    getOrCreateSystem,
    removeSystem,
    getSystemByBoxId,
    rebuildChainFromState,
    redistribute,
    getFragmentForBox,
    startEditing,
    stopEditing,
    isBoxBeingEdited,
    getEditingBoxId,
  };
}

// Singleton
let singleton = null;

export function useLinkedTextBoxSystem() {
  if (!singleton) {
    singleton = createLinkedTextBoxSystem();
  }
  return singleton;
}
