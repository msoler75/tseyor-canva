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
   * Distribuir palabras usando búsqueda binaria jerárquica (2 niveles)
   * REGLAS del experto:
   * - Un solo measureDiv reutilizado
   * - Sin HEIGHT_TOLERANCE
   * - Nivel 1: búsqueda por párrafos completos
   * - Nivel 2: búsqueda por palabras en el párrafo parcial
   */
function distributeWordsToFragments(paragraphs, chainLayouts, containerStyle) {
    const results = [];
    const paddingVertical = 2;
    const paddingHorizontal = 16;
    const linkBtnWidth = 28;

    const maxHeight = (chainLayouts[0]?.h || 120) - paddingVertical;
    const maxWidth = (chainLayouts[0]?.w || 300) - paddingHorizontal - linkBtnWidth;

    // Crear UN solo div de medición (reutilizar)
    const measureDiv = document.createElement('div');
    measureDiv.style.position = 'absolute';
    measureDiv.style.left = '-9999px';
    measureDiv.style.visibility = 'hidden';
    measureDiv.style.width = `${maxWidth}px`;
    measureDiv.style.overflow = 'visible';
    measureDiv.style.whiteSpace = 'pre-wrap';
    measureDiv.style.wordBreak = 'break-word';
    measureDiv.style.overflowWrap = 'break-word';
    applyContainerStyles(measureDiv, containerStyle);
    document.body.appendChild(measureDiv);

    // ==========================================
    // NIVEL 1: BÚSQUEDA BINARIA POR PÁRRAFOS
    // ==========================================
    let leftPara = 0;
    let rightPara = paragraphs.length;
    let fullParagraphsFit = 0;

    while (leftPara <= rightPara) {
      const midPara = Math.floor((leftPara + rightPara) / 2);
      const html = buildHtmlFromParagraphs(paragraphs.slice(0, midPara));

      measureDiv.innerHTML = html;
      const height = measureDiv.offsetHeight;

      if (height <= maxHeight) {
        fullParagraphsFit = midPara;
        leftPara = midPara + 1;
      } else {
        rightPara = midPara - 1;
      }
    }

    // ==========================================
    // NIVEL 2: BÚSQUEDA BINARIA POR PALABRAS
    // Solo en el siguiente párrafo (si existe)
    // ==========================================
    let partialParagraphWords = 0;

    if (fullParagraphsFit < paragraphs.length) {
      const nextParagraph = paragraphs[fullParagraphsFit];
      const words = nextParagraph.words;

      let leftWord = 0;
      let rightWord = words.length;
      let wordsFit = 0;

      while (leftWord <= rightWord) {
        const midWord = Math.floor((leftWord + rightWord) / 2);

        // Construir HTML: párrafos completos + palabras parciales
        const htmlParts = [];
        if (fullParagraphsFit > 0) {
          htmlParts.push(buildHtmlFromParagraphs(paragraphs.slice(0, fullParagraphsFit)));
        }
        if (midWord > 0) {
          const partialPara = { ...nextParagraph, words: words.slice(0, midWord) };
          htmlParts.push(buildHtmlFromParagraphs([partialPara]));
        }

        const html = htmlParts.join('');
        measureDiv.innerHTML = html;
        const height = measureDiv.offsetHeight;

        if (height <= maxHeight) {
          wordsFit = midWord;
          leftWord = midWord + 1;
        } else {
          rightWord = midWord - 1;
        }
      }

      partialParagraphWords = wordsFit;
    }

    // Limpiar
    document.body.removeChild(measureDiv);

    // ==========================================
    // CONSTRUIR RESULTADO FINAL
    // ==========================================
// Nueva estrategia: 
    // - html: texto que cabe (recortado por la caja visible)
    // - overflowHtml: TODO el texto completo (para la caja base sin límite)
    
    // Texto visible (lo que cabe en la caja)
    const visibleParts = [];
    if (fullParagraphsFit > 0) {
      visibleParts.push(buildHtmlFromParagraphs(paragraphs.slice(0, fullParagraphsFit)));
    }
    if (partialParagraphWords > 0 && fullParagraphsFit < paragraphs.length) {
      const partialPara = {
        ...paragraphs[fullParagraphsFit],
        words: paragraphs[fullParagraphsFit].words.slice(0, partialParagraphWords)
      };
      visibleParts.push(buildHtmlFromParagraphs([partialPara]));
    }
    
    // Texto completo (para la caja base sin límite inferior)
    const fullTextParts = [];
    if (fullParagraphsFit > 0) {
      fullTextParts.push(buildHtmlFromParagraphs(paragraphs.slice(0, fullParagraphsFit)));
    }
    if (partialParagraphWords > 0 && fullParagraphsFit < paragraphs.length) {
      const partialPara = {
        ...paragraphs[fullParagraphsFit],
        words: paragraphs[fullParagraphsFit].words.slice(0, partialParagraphWords)
      };
      fullTextParts.push(buildHtmlFromParagraphs([partialPara]));
    }
    // Añadir el resto del texto (lo que no cabe)
    if (fullParagraphsFit < paragraphs.length) {
      const remainingWords = paragraphs[fullParagraphsFit].words.slice(partialParagraphWords);
      if (remainingWords.length > 0) {
        const remainingPara = { ...paragraphs[fullParagraphsFit], words: remainingWords };
        fullTextParts.push(buildHtmlFromParagraphs([remainingPara]));
      }
      if (fullParagraphsFit + 1 < paragraphs.length) {
        fullTextParts.push(buildHtmlFromParagraphs(paragraphs.slice(fullParagraphsFit + 1)));
      }
    }
    
    const visibleHtml = visibleParts.join('');
    const fullTextHtml = fullTextParts.join('');
    const fitsInBox = fullParagraphsFit === paragraphs.length && partialParagraphWords === paragraphs[fullParagraphsFit]?.words?.length;
    
    results.push({
      html: visibleHtml,
      overflowHtml: fullTextHtml, // TODO el texto para la caja base
      fitsInBox: fitsInBox
    });

    // Log
    const totalWords = paragraphs.reduce((sum, p) => sum + p.words.length, 0);
    const wordsBeforeParagraph = paragraphs.slice(0, fullParagraphsFit).reduce((sum, p) => sum + p.words.length, 0);
    const wordsFit = wordsBeforeParagraph + partialParagraphWords;

    const frontendLog = useFrontendLog();
    frontendLog.info('hierarchicalSearch',
      `Búsqueda jerárquica: ${wordsFit}/${totalWords} palabras caben`,
      {
        level1: { paragraphsFit: fullParagraphsFit, totalParagraphs: paragraphs.length },
        level2: { wordsFitInPartialParagraph: partialParagraphWords },
        result: { wordsFit, totalWords, overflowWords: totalWords - wordsFit }
      }
    );

    return results;
  }

  /**
   * Construir HTML desde array de párrafos
   */
  function buildHtmlFromParagraphs(paragraphs) {
    if (!paragraphs || paragraphs.length === 0) return '';
    return paragraphs.map(para => {
      const tag = para.tag || 'p';
      const style = para.style || '';
      const styleAttr = style ? ` style="${style}"` : '';
      const text = para.words ? para.words.join(' ') : '';
      return `<${tag}${styleAttr}>${text}</${tag}>`;
    }).join('');
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
