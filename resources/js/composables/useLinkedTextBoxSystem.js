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

     // Convertir parrafos a lista plana de unidades distribuibles.
     // Los parrafos vacios no tienen palabras, asi que necesitan una unidad propia
     // para ocupar altura real y poder empujar el contenido a la siguiente caja.
     const allUnits = [];
     for (let pIdx = 0; pIdx < paragraphs.length; pIdx++) {
       const para = paragraphs[pIdx];
       if (!para.words.length) {
         allUnits.push({
           type: 'paragraph',
           paragraphIndex: pIdx,
           paragraph: para
         });
         continue;
       }

       for (let wIdx = 0; wIdx < para.words.length; wIdx++) {
         allUnits.push({
           type: 'word',
           word: para.words[wIdx],
           paragraphIndex: pIdx,
           paragraph: para
         });
       }
     }
     const totalUnits = allUnits.length;

      // Crear UN solo div de medición (reutilizar)
      let measureDiv = document.getElementById('measure');
      if(!measureDiv) {
         measureDiv = document.createElement("div")
         measureDiv.id = 'measure';
         measureDiv.style.position = 'fixed';
         measureDiv.style.left = '200px';
         measureDiv.style.top = '200px';
         measureDiv.style.zIndex = '999999';
         measureDiv.style.visibility = 'visible';
         measureDiv.style.background = 'orange';
         measureDiv.style.minHeight = '100px';
         measureDiv.style.padding = '0'; // SIN PADDING (para no alterar ancho)
         document.body.appendChild(measureDiv);
      }

      // Función para configurar el div de medición DINÁMICO
      const setupMeasureDiv = (layout) => {
        if (!layout) return null;

        // Limpiar measureDiv
        measureDiv.innerHTML = '';

        // Hacer el measureDiv contenedor visible y sin padding
        measureDiv.style.padding = '0';
        measureDiv.style.border = '0px';

        // Crear div interno para medición
        const innerDiv = document.createElement('div');

        // Hacerlo MUY VISIBLE para depuración
        innerDiv.style.cssText = `
          display: block !important;
          visibility: visible !important;
          opacity: 1 !important;
          height: auto !important;
          overflow: visible !important;
          white-space: pre-wrap !important;
          word-break: break-word !important;
          overflow-wrap: break-word !important;
          box-sizing: border-box !important;
          border: 0 !important;
          background: gray !important;
          margin: 0 !important;
          padding: 0 !important;
        `;

        // ANCHO DINÁMICO: intentar usar el ancho del elemento real
        let width = layout.w || 300;
        const realElement = document.getElementById(layout.id);
        if (realElement) {
          const computedStyle = window.getComputedStyle(realElement);
          const computedWidth = computedStyle.width;
          if (computedWidth && computedWidth !== 'auto') {
            width = parseInt(computedWidth);
          }
        }
        innerDiv.style.width = `${width}px`;

        // Copiar estilos de fuente desde el layout
        if (layout.fontSize) innerDiv.style.fontSize = `${layout.fontSize}px`;
        if (layout.fontFamily) innerDiv.style.fontFamily = layout.fontFamily;
        if (layout.lineHeight) innerDiv.style.lineHeight = String(layout.lineHeight);
        if (layout.letterSpacing !== undefined) innerDiv.style.letterSpacing = `${layout.letterSpacing}px`;
        if (layout.fontWeight) innerDiv.style.fontWeight = layout.fontWeight;
        if (layout.fontStyle) innerDiv.style.fontStyle = layout.fontStyle;
        if (layout.color) innerDiv.style.color = layout.color;

        // Copiar clases CSS (para heredar estilos como .linked-text-display)
        innerDiv.className = 'linked-text-display';

        // Añadir al measureDiv
        measureDiv.appendChild(innerDiv);

        return innerDiv;
      };

       const escapeHtml = (value) => String(value ?? '')
         .replace(/&/g, '&amp;')
         .replace(/</g, '&lt;')
         .replace(/>/g, '&gt;')
         .replace(/"/g, '&quot;')
         .replace(/'/g, '&#39;');

       const escapeAttribute = (value) => escapeHtml(value);

       /**
        * Construir HTML desde un slice de unidades (manteniendo estructura de parrafos).
        * Incluye parrafos vacios como <br> para que ocupen una altura de linea real
        * durante la medicion y en el modo display.
        * @param {Array} unitSlice Array de objetos {type, word, paragraphIndex, paragraph}
        * @returns {string} HTML con parrafos adecuados
        */
       const buildHtmlFromUnitSlice = (unitSlice) => {
         if (!unitSlice || unitSlice.length === 0) return '';

         const paraIndices = new Set();
         for (const unit of unitSlice) {
           paraIndices.add(unit.paragraphIndex);
         }

         if (paraIndices.size === 0) return '';

         const minParaIdx = Math.min(...paraIndices);
         const maxParaIdx = Math.max(...paraIndices);

         if (paragraphs && minParaIdx <= maxParaIdx && maxParaIdx < paragraphs.length) {
           const htmlParts = [];
           let unitIdx = 0;

           for (let idx = minParaIdx; idx <= maxParaIdx; idx++) {
             const para = paragraphs[idx];
             const tag = para.tag || 'p';
             const style = para.style || '';
             const styleAttr = style ? ` style="${escapeAttribute(style)}"` : '';

             const units = [];
             while (unitIdx < unitSlice.length && unitSlice[unitIdx].paragraphIndex === idx) {
               units.push(unitSlice[unitIdx]);
               unitIdx++;
             }

             const text = units
               .filter((unit) => unit.type === 'word')
               .map((unit) => escapeHtml(unit.word))
               .join('');
             const contents = text || '<br>';
             htmlParts.push(`<${tag}${styleAttr}>${contents}</${tag}>`);
           }

           return htmlParts.join('');
         }

         const grouped = [];
         let currentGroup = null;
         for (const unit of unitSlice) {
           if (!currentGroup || currentGroup.paragraphIndex !== unit.paragraphIndex) {
             currentGroup = {
               paragraphIndex: unit.paragraphIndex,
               paragraph: unit.paragraph,
               words: unit.type === 'word' ? [unit.word] : []
             };
             grouped.push(currentGroup);
           } else if (unit.type === 'word') {
             currentGroup.words.push(unit.word);
           }
         }

         return grouped.map(group => {
           const para = group.paragraph;
           const tag = para.tag || 'p';
           const style = para.style || '';
           const styleAttr = style ? ` style="${escapeAttribute(style)}"` : '';
           const text = group.words.map((word) => escapeHtml(word)).join('');
           const contents = text || '<br>';
           return `<${tag}${styleAttr}>${contents}</${tag}>`;
         }).join('');
       };

       // Procesar cada caja en la cadena secuencialmente
      let unitIdx = 0; // indice de la proxima unidad a colocar
      chainLayouts.forEach((layout, boxIndex) => {
        // Si ya no quedan palabras, la caja actual y las siguientes quedan vacías
        if (unitIdx >= totalUnits) {
          system.fragments[layout.id] = {
            html: '',
            overflowHtml: '',
            fullTextHtml: '', // No hay texto de entrada
            fitsInBox: true
          };
          return;
        }

        // Texto de entrada completo para esta caja (antes de recortar por altura)
        const inputSlice = allUnits.slice(unitIdx, totalUnits);

        // Configurar el div de medición para esta caja (clonar o fallback)
        const measureNode = setupMeasureDiv(layout);
        if (!measureNode) {
          // Si no hay nodo, no podemos medir
          system.fragments[layout.id] = {
            html: '',
            overflowHtml: buildHtmlFromUnitSlice(allUnits.slice(unitIdx)),
            fullTextHtml: buildHtmlFromUnitSlice(inputSlice),
            fitsInBox: false
          };
          return;
        }

        // La altura máxima es la altura de la caja
        const maxHeight = (layout.h || 50);
        let left = 0;
        let right = totalUnits - unitIdx;
        let bestFit = 0;

        while (left <= right) {
          const mid = Math.floor((left + right) / 2);
          const testSlice = allUnits.slice(unitIdx, unitIdx + mid);
          const html = buildHtmlFromUnitSlice(testSlice);
          measureNode.innerHTML = html;  // Usar el NODO retornado por setupMeasureDiv
          const height = measureNode.offsetHeight;

          if (height <= maxHeight) {
            // Cabe: intentar con más palabras
            bestFit = mid;
            left = mid + 1;
          } else {
            // No cabe: intentar con menos unidades
            right = mid - 1;
          }
        }

        const fitUnits = bestFit;
        const visibleSlice = allUnits.slice(unitIdx, unitIdx + fitUnits);
        const overflowSlice = allUnits.slice(unitIdx + fitUnits); // resto para siguientes cajas
        
        const visibleHtml = buildHtmlFromUnitSlice(visibleSlice);
        
        // REGLA: Si la caja tiene enlace siguiente, NUNCA tiene overflowHtml
        // (el texto que no cabe pasa a la siguiente caja, no es "overflow" de esta)
        const isLastInChain = !layout.linkedTextNext; // true si NO tiene enlace siguiente (es la última)
        const overflowHtml = isLastInChain ? buildHtmlFromUnitSlice(overflowSlice) : ''; // Solo la última caja puede tener overflow
        
        const fullTextHtml = buildHtmlFromUnitSlice(inputSlice); // Texto completo de entrada (para capa inferior)
        // fitsInBox: true solo si es la última caja Y no hay más palabras después
        const fitsInBox = isLastInChain && (unitIdx + fitUnits) >= totalUnits;

        // Asignar fragmento a esta caja
        system.fragments[layout.id] = {
          html: visibleHtml,
          overflowHtml: overflowHtml,
          fullTextHtml: fullTextHtml, // Nuevo: texto completo para capa inferior (sin límite de altura)
          fitsInBox: fitsInBox
        };

        // Actualizar índice para la siguiente caja
        unitIdx += fitUnits;

        // Log para esta caja (opcional)
        frontendLog.info('boxFragment',
          `Caja ${boxIndex + 1}: ${fitUnits}/${totalUnits - (unitIdx - fitUnits)} unidades caben`,
          {
            boxIndex,
            boxId: layout.id,
            unitsFit: fitUnits,
            unitsRemaining: totalUnits - unitIdx,
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
          const tag = node.tagName.toLowerCase();
          const text = node.textContent;

          // Incluir párrafos vacíos (presionar ENTER crea párrafos vacíos)
          // Los párrafos vacíos empujan el contenido hacia la siguiente caja
          if (!text || !text.trim()) {
            paragraphs.push({
              style,
              words: [],
              tag,
            });
          } else {
            paragraphs.push({
              style,
              words: tokenizeText(text),
              tag,
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
    else el.style.padding = '0px';
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
    const previousEditorId = system.editorId;
    system.editorId = null;
    if (activeEditorId.value === previousEditorId) {
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
