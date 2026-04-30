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
    let currentFrameIndex = 0;
    let currentFrameHtml = '';
    let currentFrameWords = [];
    let currentParagraphIndex = 0;
    let currentWordIndex = 0;
    let totalWordsProcessed = 0;
    const cutPoints = []; // Registrar dónde se corta cada frame

    // Crear contenedor de medición
    const measureDiv = document.createElement('div');
    measureDiv.style.position = 'absolute';
    measureDiv.style.left = '-9999px';
    measureDiv.style.height = 'auto';
    measureDiv.style.overflow = 'visible';
    measureDiv.style.whiteSpace = 'pre-wrap';
    measureDiv.style.wordBreak = 'break-word';
    measureDiv.style.overflowWrap = 'break-word';
    applyContainerStyles(measureDiv, containerStyle);
    document.body.appendChild(measureDiv);

    let frameHeight = chainLayouts[currentFrameIndex]?.h || 120;
    let frameWidth = chainLayouts[currentFrameIndex]?.w || 300;
    measureDiv.style.width = `${frameWidth}px`;

    // Contar total de palabras
    const totalWords = paragraphs.reduce((sum, p) => sum + p.words.length, 0);

    while (currentParagraphIndex < paragraphs.length) {
      const paragraph = paragraphs[currentParagraphIndex];
      
      while (currentWordIndex < paragraph.words.length) {
        const word = paragraph.words[currentWordIndex];
        
        // Construir HTML de prueba con la palabra añadida
        const testWords = [...currentFrameWords, word];
        const testHtml = buildHtmlFromWords(paragraphs, currentParagraphIndex, currentWordIndex, testWords, currentFrameHtml);
        
        // Medir altura
        measureDiv.innerHTML = testHtml;
        const newHeight = measureDiv.offsetHeight;
        
        if (newHeight <= frameHeight || currentFrameWords.length === 0) {
          // Cabe en el frame actual
          currentFrameWords.push(word);
          currentWordIndex++;
          totalWordsProcessed++;
        } else {
          // No cabe - guardar frame actual y empezar nuevo
          cutPoints.push({
            frameIndex: results.length,
            wordsInFrame: currentFrameWords.length,
            measuredHeight: newHeight,
            frameHeight,
            frameWidth,
            lastWordThatFit: currentFrameWords[currentFrameWords.length - 1],
            wordThatOverflowed: word,
          });

          if (currentFrameWords.length > 0) {
            const html = buildHtmlFromWords(paragraphs, currentParagraphIndex, currentWordIndex - 1, currentFrameWords, '');
            results.push({
              html,
              overflowHtml: '',
              fitsInBox: true,
            });
          }
          
          // Empezar nuevo frame
          currentFrameWords = [word];
          currentWordIndex++;
          totalWordsProcessed++;
          currentFrameIndex++;
          
          if (currentFrameIndex >= chainLayouts.length) {
            // No más frames disponibles - el resto es overflow
            break;
          }
          
          // Actualizar contenedor de medición
          frameHeight = chainLayouts[currentFrameIndex]?.h || 120;
          frameWidth = chainLayouts[currentFrameIndex]?.w || 300;
          measureDiv.style.width = `${frameWidth}px`;
        }
      }
      
      if (currentFrameIndex >= chainLayouts.length) {
        break;
      }
      
      // Pasar al siguiente párrafo
      currentParagraphIndex++;
      currentWordIndex = 0;
    }
    
    document.body.removeChild(measureDiv);
    
    // Guardar el último frame si tiene contenido
    const lastValidParagraphIndex = Math.min(currentParagraphIndex, paragraphs.length - 1);
    if (currentFrameWords.length > 0 && currentFrameIndex < chainLayouts.length) {
      const html = buildHtmlFromWords(paragraphs, lastValidParagraphIndex, currentWordIndex - 1, currentFrameWords, '');
      results.push({
        html,
        overflowHtml: '',
        fitsInBox: true,
      });
    }
    
    // Calcular overflow si hay contenido restante
    let overflowWordCount = 0;
    if (currentFrameIndex >= chainLayouts.length && currentParagraphIndex < paragraphs.length) {
      const overflowWords = [];
      
      // Recoger palabras restantes del párrafo actual
      for (let i = currentWordIndex; i < paragraphs[currentParagraphIndex].words.length; i++) {
        overflowWords.push(paragraphs[currentParagraphIndex].words[i]);
      }
      
      // Recoger párrafos restantes
      for (let i = currentParagraphIndex + 1; i < paragraphs.length; i++) {
        overflowWords.push(...paragraphs[i].words);
      }
      
      overflowWordCount = overflowWords.length;
      
      if (overflowWords.length > 0) {
        // Usar el estilo del párrafo actual para el overflow
        const paragraph = paragraphs[currentParagraphIndex];
        const style = paragraph.style || '';
        const tag = paragraph.tag || 'p';
        const styleAttr = style ? ` style="${style}"` : '';
        const overflowHtml = `<${tag}${styleAttr}>${overflowWords.join(' ')}</${tag}>`;
        
        // Agregar overflow al último frame
        if (results.length > 0) {
          results[results.length - 1].overflowHtml = overflowHtml;
          results[results.length - 1].fitsInBox = false;
        }
      }
    }

    // Log detallado de la fragmentación
    const frontendLog = useFrontendLog();
    frontendLog.info('fragmentDetail', 
      `Fragmentación completada: ${results.length} frames, ${overflowWordCount} palabras overflow`, 
      {
        totalWords,
        totalWordsProcessed,
        overflowWordCount,
        framesCount: chainLayouts.length,
        fragmentsGenerated: results.length,
        cutPoints,
        frameDimensions: chainLayouts.map(l => ({
          id: l.id,
          w: l.w,
          h: l.h,
          fontSize: l.fontSize,
          fontFamily: l.fontFamily,
        })),
        containerStyle,
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
    
    // Log detallado para debugging
    const frontendLog = useFrontendLog();
    frontendLog.debug('buildHtmlFromWords', 
      'Construyendo HTML desde palabras', 
      {
        currentParagraphIndex,
        wordsCount: words.length,
        firstWord: words[0],
        tag,
        style: style?.substring(0, 100),
        hasStyle: !!style,
        styleAttr: styleAttr?.substring(0, 100),
        result: result?.substring(0, 200),
      }
    );
    
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
