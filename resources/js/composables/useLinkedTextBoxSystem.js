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
          system.fragments[layout.id] = { html: '', overflowHtml: '', fullTextHtml: '', tailHtml: '', prefixHtml: '', editorTopOffset: 0, editorTextOffset: 0, fitsInBox: true };
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
      // - Parrafos vacios → unidad 'paragraph' (ocupan altura)
      // - Texto normal → unidades 'word' (divisibles)
      // - Listas (ul/ol) → unidades 'li' por cada <li> (atómicas, no se dividen)
      const allUnits = [];
      for (let pIdx = 0; pIdx < paragraphs.length; pIdx++) {
        const para = paragraphs[pIdx];
        const isList = (para.tag === 'ul' || para.tag === 'ol') && para.items && para.items.length > 0;

        if (isList) {
          for (let iIdx = 0; iIdx < para.items.length; iIdx++) {
            allUnits.push({
              type: 'li',
              paragraphIndex: pIdx,
              paragraph: para,
              itemIndex: iIdx,
              html: para.items[iIdx].html,
              words: para.items[iIdx].words,
            });
          }
        } else if (!para.words.length) {
          allUnits.push({
            type: 'paragraph',
            paragraphIndex: pIdx,
            paragraph: para,
          });
        } else {
          for (let wIdx = 0; wIdx < para.words.length; wIdx++) {
            allUnits.push({
              type: 'word',
              word: para.words[wIdx],
              paragraphIndex: pIdx,
              paragraph: para,
            });
          }
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
         measureDiv.style.zIndex = '999';
         // measureDiv.style.visibility = 'hidden';
         measureDiv.style.background = 'red';
         measureDiv.style.minHeight = '0';
         measureDiv.style.padding = '0'; // SIN PADDING (para no alterar ancho)
         document.body.appendChild(measureDiv);
      }

      const cssEscape = (value) => {
        if (typeof CSS !== 'undefined' && typeof CSS.escape === 'function') {
          return CSS.escape(String(value));
        }

        return String(value).replace(/["\\]/g, '\\$&');
      };

      const findRenderedEditorElement = (id) => {
        if (!id || typeof document === 'undefined') return null;

        return document.querySelector(`[data-editor-id="${cssEscape(id)}"]`)
          ?? document.getElementById(id)
          ?? null;
      };

      const findRenderedTextNode = (element) => {
        if (!element) return null;

        return element.querySelector('.linked-text-display')
          ?? element.querySelector('.linked-text-editor-viewport .ProseMirror')
          ?? element.querySelector('.ProseMirror')
          ?? element;
      };

      const copyComputedTextStyles = (source, target) => {
        if (!source || !target || typeof window === 'undefined') return;

        const computed = window.getComputedStyle(source);
        [
          'font',
          'font-family',
          'font-size',
          'font-style',
          'font-variant',
          'font-weight',
          'font-stretch',
          'line-height',
          'letter-spacing',
          'text-align',
          'text-transform',
          'text-indent',
          'text-rendering',
          'text-shadow',
          'text-decoration',
          'text-decoration-line',
          'text-decoration-style',
          'text-decoration-color',
          'text-underline-offset',
          'white-space',
          'word-break',
          'overflow-wrap',
          'tab-size',
          'color',
          '-webkit-text-stroke',
          '-webkit-text-stroke-width',
          '-webkit-text-stroke-color',
          '-webkit-text-fill-color',
          'paint-order',
        ].forEach((property) => {
          const value = computed.getPropertyValue(property);
          if (value) {
            target.style.setProperty(property, value, 'important');
          }
        });
      };

      const styleObjectToCss = (style = {}) => {
        const declarations = [];
        const push = (property, value, transform = (v) => v) => {
          if (value === undefined || value === null || value === '') return;
          declarations.push(`${property}: ${transform(value)}`);
        };

        push('font-size', style.fontSize, (value) => `${value}px`);
        push('color', style.color);
        push('font-family', style.fontFamily);
        push('font-weight', style.fontWeight, (value) => value === 'bold' ? '700' : (value === 'regular' ? '400' : value));
        if (style.italic) declarations.push('font-style: italic');
        if (style.underline) declarations.push('text-decoration: underline');
        if (style.uppercase) declarations.push('text-transform: uppercase');
        push('text-align', style.textAlign);
        push('letter-spacing', style.letterSpacing, (value) => `${value}px`);
        push('line-height', style.lineHeight);

        return declarations.join('; ');
      };

      const mergeCssText = (...parts) => parts
        .map((part) => String(part ?? '').trim().replace(/;+$/g, ''))
        .filter(Boolean)
        .join('; ');

      const paragraphCssForIndex = (paragraph, index, layout) => {
        const style = layout?.paragraphStyles?.[index];
        const merged = style
          ? styleObjectToCss(style)
          : styleObjectToCss(layout ?? {});
        return mergeCssText(
          merged,
          paragraph?.style ?? '',
        );
      };

      // Función para configurar el div de medición DINÁMICO
      const setupMeasureDiv = (layout) => {
        if (!layout) return null;

        // Limpiar measureDiv
        measureDiv.innerHTML = '';

        const renderedElement = findRenderedEditorElement(layout.id);
        const renderedTextNode = findRenderedTextNode(renderedElement);

        // Hacer el measureDiv contenedor visible y sin padding
        measureDiv.style.padding = '0';
        measureDiv.style.border = '0px';
        measureDiv.style.margin = '0';
        measureDiv.style.boxSizing = 'border-box';

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
          background: transparent !important;
          margin: 0 !important;
          padding: 0 !important;
        `;

        // ANCHO DIN?MICO: medir con el mismo viewport textual que el render real.
        let width = layout.w || 300;
        if (renderedTextNode) {
          const textRect = renderedTextNode.getBoundingClientRect();
          if (textRect.width > 0) {
            width = textRect.width;
          } else {
            const computedStyle = window.getComputedStyle(renderedTextNode);
            const computedWidth = computedStyle.width;
            if (computedWidth && computedWidth !== 'auto') {
              width = parseFloat(computedWidth);
            }
          }
        } else if (renderedElement) {
          const elementRect = renderedElement.getBoundingClientRect();
          if (elementRect.width > 0) {
            width = elementRect.width;
          } else {
            const computedStyle = window.getComputedStyle(renderedElement);
            const computedWidth = computedStyle.width;
            if (computedWidth && computedWidth !== 'auto') {
              width = parseFloat(computedWidth);
            }
          }
        }
        innerDiv.style.width = `${width}px`;

        // Copiar estilos computados reales antes que los fallbacks.
        // El punto de split solo es fiable si #measure envuelve y pinta igual
        // que .linked-text-display/.ProseMirror en la caja correspondiente.
        copyComputedTextStyles(renderedTextNode, innerDiv);

        // Copiar estilos de fuente desde el layout como fallback si a?n no hay DOM real.
        if (layout.fontSize) innerDiv.style.fontSize = `${layout.fontSize}px`;
        if (layout.fontFamily) innerDiv.style.fontFamily = layout.fontFamily;
        if (layout.lineHeight) innerDiv.style.lineHeight = String(layout.lineHeight);
        if (layout.letterSpacing !== undefined) innerDiv.style.letterSpacing = `${layout.letterSpacing}px`;
        if (layout.fontWeight) innerDiv.style.fontWeight = layout.fontWeight;
        if (layout.fontStyle) innerDiv.style.fontStyle = layout.fontStyle;
        if (layout.italic) innerDiv.style.fontStyle = 'italic';
        if (layout.color) innerDiv.style.color = layout.color;
        if (containerStyle.fontSize) innerDiv.style.fontSize = `${containerStyle.fontSize}px`;
        if (containerStyle.fontFamily) innerDiv.style.fontFamily = containerStyle.fontFamily;
        if (containerStyle.lineHeight) innerDiv.style.lineHeight = String(containerStyle.lineHeight);
        if (containerStyle.letterSpacing !== undefined) innerDiv.style.letterSpacing = `${containerStyle.letterSpacing}px`;

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
        * Construir HTML desde un slice de unidades (word + li).
        * - Unidades word → texto escapado, unido
        * - Unidades li → html original del <li> (preserva estructura)
        * - Unidades paragraph (vacíos) → <tag><br></tag>
        * - Párrafos completos → intenta usar innerHTML original
        */
       const buildHtmlFromUnitSlice = (unitSlice, layout = null) => {
         if (!unitSlice || unitSlice.length === 0) return '';

         const grouped = {};
         for (const unit of unitSlice) {
           const pIdx = unit.paragraphIndex;
           if (!grouped[pIdx]) grouped[pIdx] = [];
           grouped[pIdx].push(unit);
         }

         const sortedKeys = Object.keys(grouped).map(Number).sort((a, b) => a - b);
         const htmlParts = [];

          const isParagraphSplit = (pIdx, units) => {
            const para = paragraphs[pIdx];
            if (!para) return false;
            if ((para.tag === 'ul' || para.tag === 'ol') && para.items) {
              const liUnits = units.filter(u => u.type === 'li');
              return liUnits.length !== para.items.length;
            }
            const textUnits = units.filter(u => u.type === 'word');
            return para.words.length > 0 && textUnits.length < para.words.length;
          };

          const needsJustifyLastLine = (pIdx) => {
            const paraStyle = layout?.paragraphStyles?.[pIdx];
            const align = paraStyle?.textAlign || (!paraStyle ? layout?.textAlign : null);
            return align === 'justify';
          };

          for (const pIdx of sortedKeys) {
            const units = grouped[pIdx];
            const para = paragraphs[pIdx];
            if (!para) continue;

            const tag = para.tag || 'p';
            let baseStyle = paragraphCssForIndex(para, pIdx, layout);
            if (isParagraphSplit(pIdx, units) && needsJustifyLastLine(pIdx)) {
              baseStyle = (baseStyle ? baseStyle + ';' : '') + 'text-align-last:justify';
            }
            const styleAttr = baseStyle ? ` style="${escapeAttribute(baseStyle)}"` : '';

            const isList = (para.tag === 'ul' || para.tag === 'ol') && para.items && para.items.length > 0;

            if (isList) {
              const liUnits = units.filter(u => u.type === 'li');
              const allItemsPresent = liUnits.length === para.items.length;

              if (allItemsPresent && para.innerHTML) {
                htmlParts.push(`<${tag}${styleAttr}>${para.innerHTML}</${tag}>`);
              } else if (liUnits.length > 0) {
                const lis = liUnits.map(u => u.html).join('');
                htmlParts.push(`<${tag}${styleAttr}>${lis}</${tag}>`);
              } else {
                htmlParts.push(`<${tag}${styleAttr}><br></${tag}>`);
              }
            } else {
              const textUnits = units.filter(u => u.type === 'word');
              const isComplete = !para.words.length || textUnits.length === para.words.length;

              let contents;
              if (isComplete && para.innerHTML) {
                contents = para.innerHTML;
              } else if (textUnits.length > 0) {
                contents = textUnits.map(u => escapeHtml(u.word)).join('') || '\u200B';
              } else {
                contents = '<br>';
              }
              htmlParts.push(`<${tag}${styleAttr}>${contents}</${tag}>`);
            }
          }

         return htmlParts.join('');
       };

       /**
        * Construir HTML completo con marcador en un unitIndex (word-level).
        */
       const buildHtmlWithMarkerAtUnitIndex = (markerUnitIndex, layout = null) => {
         const markerHtml = '<span data-linked-text-flow-marker="true" style="display:inline-block;width:0;height:1em;line-height:1;vertical-align:top;overflow:hidden"></span>';
         const htmlParts = [];
         let globalUnitIndex = 0;
         let markerPlaced = false;

         for (let idx = 0; idx < paragraphs.length; idx++) {
           const para = paragraphs[idx];
           const tag = para.tag || 'p';
           const style = paragraphCssForIndex(para, idx, layout);
           const styleAttr = style ? ` style="${escapeAttribute(style)}"` : '';

           const isList = (para.tag === 'ul' || para.tag === 'ol') && para.items && para.items.length > 0;
           let contents = '';

           if (isList) {
             for (let liIdx = 0; liIdx < para.items.length; liIdx++) {
               if (!markerPlaced && markerUnitIndex === globalUnitIndex) {
                 contents += markerHtml;
                 markerPlaced = true;
               }
               contents += para.items[liIdx].html;
               globalUnitIndex++;
             }
             if (!para.items.length) {
               if (!markerPlaced && markerUnitIndex <= globalUnitIndex) {
                 contents += markerHtml;
                 markerPlaced = true;
               }
               globalUnitIndex++;
             }
           } else if (!para.words.length) {
             if (!markerPlaced && markerUnitIndex <= globalUnitIndex) {
               contents += markerHtml;
               markerPlaced = true;
             }
             contents += '<br>';
             globalUnitIndex++;
           } else {
             for (let wIdx = 0; wIdx < para.words.length; wIdx++) {
               if (!markerPlaced && markerUnitIndex === globalUnitIndex) {
                 contents += markerHtml;
                 markerPlaced = true;
               }
               contents += escapeHtml(para.words[wIdx]);
               globalUnitIndex++;
             }
           }

           if (!markerPlaced && markerUnitIndex === globalUnitIndex) {
             contents += markerHtml;
             markerPlaced = true;
           }

           htmlParts.push(`<${tag}${styleAttr}>${contents || '<br>'}</${tag}>`);
         }

         if (!markerPlaced) {
           htmlParts.push(`<p>${markerHtml}</p>`);
         }

         return htmlParts.join('');
       };

       /**
        * Medir el offset del editor (altura del prefijo antes de esta caja).
        * Usa unitIndex (word-level) para colocar el marcador.
        */
       const measureEditorTopOffset = (measureNode, splitUnitIndex, fallbackHtml, layout = null) => {
         if (!measureNode || splitUnitIndex <= 0) return 0;

         measureNode.innerHTML = fallbackHtml;
         const prefixHeight = measureNode.offsetHeight || 0;

         measureNode.innerHTML = buildHtmlWithMarkerAtUnitIndex(splitUnitIndex, layout);
         const marker = measureNode.querySelector('[data-linked-text-flow-marker="true"]');
         if (marker) {
           const markerTop = marker.getBoundingClientRect().top - measureNode.getBoundingClientRect().top;
           return Math.max(0, Math.round(Math.max(prefixHeight, markerTop) * 100) / 100);
         }

         return Math.max(0, Math.round(prefixHeight * 100) / 100);
       };

       // Procesar cada caja en la cadena secuencialmente
      let unitIdx = 0; // indice de la proxima unidad a colocar
      chainLayouts.forEach((layout, boxIndex) => {
        // Si ya no quedan unidades, la caja actual y las siguientes quedan vacías
        if (unitIdx >= totalUnits) {
          system.fragments[layout.id] = {
            html: '',
            overflowHtml: '',
            fullTextHtml: buildHtmlFromUnitSlice(allUnits, layout),
            tailHtml: '',
            prefixHtml: buildHtmlFromUnitSlice(allUnits, layout),
            editorTopOffset: 0,
            editorTextOffset: 0,
            fitsInBox: true
          };
          return;
        }

        // Texto de entrada completo para esta caja (antes de recortar por altura)
        const inputSlice = allUnits.slice(unitIdx, totalUnits);

        // Configurar el div de medición para esta caja (clonar o fallback)
        const measureNode = setupMeasureDiv(layout);
        if (!measureNode) {
          system.fragments[layout.id] = {
            html: '',
            overflowHtml: buildHtmlFromUnitSlice(allUnits.slice(unitIdx), layout),
            fullTextHtml: buildHtmlFromUnitSlice(allUnits, layout),
            tailHtml: buildHtmlFromUnitSlice(inputSlice, layout),
            prefixHtml: buildHtmlFromUnitSlice(allUnits.slice(0, unitIdx), layout),
            editorTopOffset: 0,
            editorTextOffset: 0,
            fitsInBox: false
          };
          return;
        }

        const prefixUnits = allUnits.slice(0, unitIdx);
        const prefixHtml = buildHtmlFromUnitSlice(prefixUnits, layout);
        const editorTopOffset = measureEditorTopOffset(measureNode, unitIdx, prefixHtml, layout);
        const editorTextOffset = prefixUnits
          .filter((unit) => unit.type === 'word')
          .reduce((total, unit) => total + String(unit.word ?? '').length, 0);

        // La altura máxima es la altura de la caja
        const maxHeight = (layout.h || 50);
        let left = 0;
        let right = totalUnits - unitIdx;
        let bestFit = 0;

        while (left <= right) {
          const mid = Math.floor((left + right) / 2);
          const testSlice = allUnits.slice(unitIdx, unitIdx + mid);
          const html = buildHtmlFromUnitSlice(testSlice, layout);
          measureNode.innerHTML = html;
          const height = measureNode.offsetHeight;

          if (height <= maxHeight) {
            bestFit = mid;
            left = mid + 1;
          } else {
            right = mid - 1;
          }
        }

        const fitUnits = bestFit;
        const rawVisibleSlice = allUnits.slice(unitIdx, unitIdx + fitUnits);
        const rawOverflowSlice = allUnits.slice(unitIdx + fitUnits);

        // Eliminar tokens de espacio al final de la porción visible y al inicio del overflow
        const visibleSlice = [...rawVisibleSlice];
        while (visibleSlice.length > 0
          && visibleSlice[visibleSlice.length - 1]?.type === 'word'
          && /^\s+$/.test(visibleSlice[visibleSlice.length - 1]?.word || '')) {
          visibleSlice.pop();
        }
        const overflowSlice = [...rawOverflowSlice];
        let leadingSpaces = 0;
        while (overflowSlice.length > 0
          && overflowSlice[0]?.type === 'word'
          && /^\s+$/.test(overflowSlice[0]?.word || '')) {
          overflowSlice.shift();
          leadingSpaces++;
        }

        const visibleHtml = buildHtmlFromUnitSlice(visibleSlice, layout);

        // REGLA: Si la caja tiene enlace siguiente, NUNCA tiene overflowHtml
        const isLastInChain = !layout.linkedTextNext;
        const overflowHtml = isLastInChain ? buildHtmlFromUnitSlice(overflowSlice, layout) : '';

        const fullTextHtml = buildHtmlFromUnitSlice(allUnits, layout);
        const tailHtml = buildHtmlFromUnitSlice(inputSlice, layout);
        const fitsInBox = isLastInChain && (unitIdx + fitUnits) >= totalUnits;

        system.fragments[layout.id] = {
          html: visibleHtml,
          overflowHtml: overflowHtml,
          fullTextHtml: fullTextHtml,
          tailHtml: tailHtml,
          prefixHtml: prefixHtml,
          editorTopOffset,
          editorTextOffset,
          fitsInBox: fitsInBox
        };

        unitIdx += fitUnits + leadingSpaces;

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
              tag: 'p',
              words: tokenizeText(text),
              innerHTML: text,
            });
          }
        } else if (node.nodeType === Node.ELEMENT_NODE) {
          const style = node.getAttribute('style') || '';
          const tag = node.tagName.toLowerCase();
          const text = node.textContent;
          const innerHtml = node.innerHTML || '';

          if ((tag === 'ul' || tag === 'ol') && node.children.length > 0) {
            const items = [];
            const liNodes = node.querySelectorAll(':scope > li');
            for (const li of liNodes) {
              items.push({
                html: li.outerHTML,
                words: tokenizeText(li.textContent),
              });
            }
            paragraphs.push({
              style,
              tag,
              words: tokenizeText(text),
              innerHTML: innerHtml,
              items,
            });
          } else if (!text || !text.trim()) {
            paragraphs.push({
              style,
              words: [],
              tag,
              innerHTML: innerHtml || '',
            });
          } else {
            paragraphs.push({
              style,
              words: tokenizeText(text),
              tag,
              innerHTML: innerHtml || '',
            });
          }
        }
      }

      return paragraphs;
    }

   /**
    * Tokenizar texto preservando espacios como tokens independientes.
    * Signos de puntuacion y guion se adhieren al token de texto adyacente
    * para que no queden colgando al final de la linea separados de su palabra.
    * Ejemplo: "Hola, mundo!" => ["Hola,", " ", "mundo!"]
    */
    function tokenizeText(text) {
       // Patron: \s+ separado; palabra+signos unido en un solo token
       // [\w\p{L}.,;:!?()\[\]{}"'`´…-]+ : palabra completa con signos pegados
       // [^\s\w\p{L}.,;:!?()\[\]{}"'`´…-]+ : otros (emojis, etc.)
       const regex = /(\s+)|([\w\p{L}.,;:!?()[\]{}"'`´…-]+)|([^\s\w\p{L}.,;:!?()[\]{}"'`´…-]+)/gu;
       const tokens = [];
       let match;
        while ((match = regex.exec(text)) !== null) {
          if (match[1]) {
            // Espacios: preservar el texto original (puede ser espacios, tabs, newlines)
            tokens.push(match[1]);
          } else {
            // Palabras con signos pegados, u otros (emojis, etc.)
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
        // Usar innerHTML original si está disponible (preserva formato inline),
        // de lo contrario unir tokens de texto
        const content = para.innerHTML ? para.innerHTML : (para.words ? para.words.join('') : '');
        return `<${tag}${styleAttr}>${content}</${tag}>`;
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
      if (!system) return { html: '', overflowHtml: '', fullTextHtml: '', tailHtml: '', prefixHtml: '', editorTopOffset: 0, editorTextOffset: 0, fitsInBox: true };
      return system.fragments[boxId] || { html: '', overflowHtml: '', fullTextHtml: '', tailHtml: '', prefixHtml: '', editorTopOffset: 0, editorTextOffset: 0, fitsInBox: true };
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

  /**
   * Reiniciar todos los sistemas (limpiar caché de fragmentos y editor activo).
   * Se usa tras undo/redo para forzar recálculo limpio desde el estado restaurado.
   */
  function resetAllSystems() {
    systemsMap.clear();
    activeEditorId.value = null;
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
    resetAllSystems,
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
