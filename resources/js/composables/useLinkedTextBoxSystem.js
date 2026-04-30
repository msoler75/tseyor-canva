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
    * Procesa las cajas en secuencia, cada caja muestra lo que cabe y el overflow
    * pasa a la siguiente caja.
    */
   const redistribute = (groupId, fullHtml, chainLayouts, containerStyle = {}) => {
     const system = systemsMap.get(groupId);
     if (!system) return;

     system.fullHtml = fullHtml;
     system.fragments = {};

      if (!chainLayouts || chainLayouts.length === 0) return;
      if (!fullHtml || fullHtml.trim() === '') {
        // Texto vacío: todas las cajas vacías
        chainLayouts.forEach(layout => {
          system.fragments[layout.id] = { html: '', overflowHtml: '', fullTextHtml: '', fitsInBox: true };
        });
        return;
      }

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

     // Convertir párrafos a lista plana de palabras con referencia a su párrafo original
     const allWords = [];
     for (let pIdx = 0; pIdx < paragraphs.length; pIdx++) {
       const para = paragraphs[pIdx];
       for (let wIdx = 0; wIdx < para.words.length; wIdx++) {
         allWords.push({
           word: para.words[wIdx],
           paragraphIndex: pIdx,
           paragraph: para // referencia al objeto párrafo original
         });
       }
     }
     const totalWords = allWords.length;

     // Crear UN solo div de medición (reutilizar)
     let measureDiv = document.getElementById('measure');
     if(!measureDiv) {
        measureDiv = document.createElement("div")
        measureDiv.id = 'measure'
        measureDiv.style.position = 'absolute';
        measureDiv.style.left = '-9999px';
        measureDiv.style.visibility = 'hidden';
        measureDiv.style.overflow = 'visible';
        measureDiv.style.whiteSpace = 'pre-wrap';
        measureDiv.style.wordBreak = 'break-word';
        measureDiv.style.overflowWrap = 'break-word';
        document.body.appendChild(measureDiv);
     }

     // Función para aplicar estilos del contenedor al div de medición
     const applyContainerStylesToMeasure = () => {
       if (!containerStyle) return;
       const criticalStyles = [
         'fontSize', 'fontFamily', 'lineHeight', 'letterSpacing',
         'wordSpacing', 'padding', 'fontWeight', 'fontStyle'
       ];
       criticalStyles.forEach(prop => {
         if (containerStyle[prop]) {
           measureDiv.style[prop] = containerStyle[prop];
         }
       });
     };
     applyContainerStylesToMeasure();

      /**
       * Construir HTML desde un slice de palabras (manteniendo estructura de párrafos)
       * @param {Array} wordSlice Array de objetos {word, paragraphIndex, paragraph}
       * @returns {string} HTML con párrafos adecuados
       */
      const buildHtmlFromWordSlice = (wordSlice) => {
        if (!wordSlice || wordSlice.length === 0) return '';
        // Agrupar palabras por párrafo original
        const grouped = [];
        let currentGroup = null;
        for (const wObj of wordSlice) {
          if (!currentGroup || currentGroup.paragraphIndex !== wObj.paragraphIndex) {
            // Nuevo párrafo
            currentGroup = {
              paragraphIndex: wObj.paragraphIndex,
              paragraph: wObj.paragraph,
              words: [wObj.word]
            };
            grouped.push(currentGroup);
          } else {
            // Mismo párrafo
            currentGroup.words.push(wObj.word);
          }
        }
        // Construir HTML
        return grouped.map(group => {
          const para = group.paragraph;
          const tag = para.tag || 'p';
          const style = para.style || '';
          const styleAttr = style ? ` style="${style}"` : '';
          // Unir tokens sin añadir espacios extra (ya que los espacios son tokens independientes)
          const text = group.words.join('');
          return `<${tag}${styleAttr}>${text}</${tag}>`;
        }).join('');
      };

      // Procesar cada caja en la cadena secuencialmente
      let wordIdx = 0; // índice de la próxima palabra a colocar
      chainLayouts.forEach((layout, boxIndex) => {
        // Si ya no quedan palabras, la caja actual y las siguientes quedan vacías
        if (wordIdx >= totalWords) {
          system.fragments[layout.id] = {
            html: '',
            overflowHtml: '',
            fullTextHtml: '', // No hay texto de entrada
            fitsInBox: true
          };
          return;
        }

        // Texto de entrada completo para esta caja (antes de recortar por altura)
        const inputSlice = allWords.slice(wordIdx, totalWords);

        // Dimensiones disponibles de la caja (restando padding y botón de enlace)
        const paddingVertical = 0;
        const paddingHorizontal = 0;
        const maxHeight = (layout.h || 50) - paddingVertical;
        const maxWidth = (layout.w || 100) - paddingHorizontal;

        // Aplicar estilos del contenedor (puede variar por caja, pero usamos el mismo containerStyle global)
        applyContainerStylesToMeasure();
        measureDiv.style.width = `${maxWidth}px`;

        // Búsqueda binaria para encontrar cuántas palabras caben en esta caja
        let left = 0;
        let right = totalWords - wordIdx;
        let bestFit = 0;

        while (left <= right) {
          const mid = Math.floor((left + right) / 2);
          const testSlice = allWords.slice(wordIdx, wordIdx + mid);
          const html = buildHtmlFromWordSlice(testSlice);
          measureDiv.innerHTML = html;
          const height = measureDiv.offsetHeight;

          if (height <= maxHeight) {
            // Cabe: intentar con más palabras
            bestFit = mid;
            left = mid + 1;
          } else {
            // No cabe: intentar con menos palabras
            right = mid - 1;
          }
        }

        const fitWords = bestFit;
        const visibleSlice = allWords.slice(wordIdx, wordIdx + fitWords);
        const overflowSlice = allWords.slice(wordIdx + fitWords); // resto para siguientes cajas

        const visibleHtml = buildHtmlFromWordSlice(visibleSlice);
        const overflowHtml = buildHtmlFromWordSlice(overflowSlice); // Texto que no cabe en esta caja (pasará a la siguiente)
        const fullTextHtml = buildHtmlFromWordSlice(inputSlice); // TODO el texto de entrada para esta caja (para la capa inferior sin límite)
        const fitsInBox = (wordIdx + fitWords) >= totalWords; // true si no hay más palabras después

        // Asignar fragmento a esta caja
        system.fragments[layout.id] = {
          html: visibleHtml,
          overflowHtml: overflowHtml,
          fullTextHtml: fullTextHtml, // Nuevo: texto completo para capa inferior (sin límite de altura)
          fitsInBox: fitsInBox
        };

        // Actualizar índice para la siguiente caja
        wordIdx += fitWords;

        // Log para esta caja (opcional)
        frontendLog.info('boxFragment',
          `Caja ${boxIndex + 1}: ${fitWords}/${totalWords - (wordIdx - fitWords)} palabras caben`,
          {
            boxIndex,
            boxId: layout.id,
            wordsFit: fitWords,
            wordsRemaining: totalWords - wordIdx,
            fitsInBox,
            overflowLength: overflowSlice.length,
            fullTextLength: inputSlice.length
          }
        );
      });

  };

  /**
    * Parsear HTML en párrafos con sus estilos
    * Tokenización: conserva signos de puntuación y espacios como tokens independientes
    */
   function parseHtmlIntoParagraphs(html) {
     const temp = document.createElement('div');
     temp.innerHTML = html;

     const paragraphs = [];
     const nodes = Array.from(temp.childNodes);

     for (const node of nodes) {
       if (node.nodeType === Node.TEXT_NODE) {
         const text = node.textContent;
         if (text && text.trim()) {
           paragraphs.push({
             style: '',
             words: tokenizeText(text),
           });
         }
       } else if (node.nodeType === Node.ELEMENT_NODE) {
         const style = node.getAttribute('style') || '';
         const text = node.textContent;
         if (text && text.trim()) {
           paragraphs.push({
             style,
             words: tokenizeText(text),
             tag: node.tagName.toLowerCase(),
           });
         }
       }
     }

     return paragraphs;
   }

   /**
    * Tokenizar texto preservando signos y espacios como tokens independientes
    * Ejemplo: "Hola, mundo!" => ["Hola", ",", " ", "mundo", "!"]
    */
   function tokenizeText(text) {
      // Patrón: separa manteniendo signos de puntuación y espacios
      // \s+ : espacios (se mantienen como tokens)
      // [.,;:!?()\[\]{}"'`…]+ : signos de puntuación (se mantienen como tokens)
      // \w+ : palabras alfanuméricas
      // [^\s\w.,;:!?()\[\]{}"'`´…]+ : otros caracteres (emojis, etc.)
      const regex = /(\s+)|([.,;:!?()[\]{}"'`…]+)|(\w+)|([^\s\w.,;:!?()[\]{}"'`´…]+)/g;
      const tokens = [];
      let match;
      while ((match = regex.exec(text)) !== null) {
        if (match[1]) {
          // Espacios: preservar el texto original (puede ser espacios, tabs, newlines)
          tokens.push(match[1]);
        } else if (match[2] || match[3] || match[4]) {
          tokens.push(match[0]);
        }
      }
      return tokens.filter(t => t !== '');
    }




  /**
    * Construir HTML desde array de párrafos
    * Las palabras ya incluyen signos y espacios como tokens independientes
    */
   function buildHtmlFromParagraphs(paragraphs) {
     if (!paragraphs || paragraphs.length === 0) return '';
     return paragraphs.map(para => {
       const tag = para.tag || 'p';
       const style = para.style || '';
       const styleAttr = style ? ` style="${style}"` : '';
       // Unir sin espacios extra (los espacios ya son tokens)
       const text = para.words ? para.words.join('') : '';
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
     if (!system) return { html: '', overflowHtml: '', fullTextHtml: '', fitsInBox: true };
     return system.fragments[boxId] || { html: '', overflowHtml: '', fullTextHtml: '', fitsInBox: true };
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
