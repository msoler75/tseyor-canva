<script setup>
import { watch, onBeforeUnmount, onMounted, nextTick, ref, computed } from 'vue';
import { useEditor, EditorContent } from '@tiptap/vue-3';
import StarterKit from '@tiptap/starter-kit';
import { TextAlign } from '@tiptap/extension-text-align';
import { Node, Mark } from '@tiptap/core';
import { TextSelection } from '@tiptap/pm/state';
import { useFrontendLog } from '../../composables/useFrontendLog';

const frontendLog = useFrontendLog();

const STYLE_ATTRS = ['fontSize', 'color', 'fontFamily', 'fontWeight', 'italic', 'underline', 'uppercase', 'textAlign', 'letterSpacing', 'lineHeight'];

const StyledTextMark = Mark.create({
    name: 'styledText',
    keepOnSplit: false,
    addAttributes() {
        return {
            color: { default: null },
            fontWeight: { default: null },
            fontStyle: { default: null },
            textDecoration: { default: null },
            fontSize: { default: null },
            fontFamily: { default: null },
        };
    },
    parseHTML() {
        return [{ tag: 'span[style]' }];
    },
    renderHTML({ HTMLAttributes }) {
        const style = [];
        if (HTMLAttributes.color) style.push(`color:${HTMLAttributes.color}`);
        if (HTMLAttributes.fontWeight) style.push(`font-weight:${HTMLAttributes.fontWeight === 'bold' ? 700 : 500}`);
        if (HTMLAttributes.fontStyle) style.push(`font-style:${HTMLAttributes.fontStyle}`);
        if (HTMLAttributes.textDecoration) style.push(`text-decoration:${HTMLAttributes.textDecoration}`);
        if (HTMLAttributes.fontSize) style.push(`font-size:${HTMLAttributes.fontSize}px`);
        if (HTMLAttributes.fontFamily) style.push(`font-family:${HTMLAttributes.fontFamily}`);
        return ['span', { ...HTMLAttributes, style: style.join(';') }, 0];
    },
});

const attrsToStyle = (attrs) => {
    const parts = [];
    if (attrs.fontSize    != null) parts.push(`font-size:${attrs.fontSize}px`);
    if (attrs.color       != null) parts.push(`color:${attrs.color}`);
    if (attrs.fontFamily  != null) parts.push(`font-family:${attrs.fontFamily}`);
    if (attrs.fontWeight  != null) parts.push(`font-weight:${attrs.fontWeight === 'bold' ? 700 : attrs.fontWeight === 'regular' ? 400 : attrs.fontWeight}`);
    if (attrs.italic)              parts.push('font-style:italic');
    if (attrs.underline)           parts.push('text-decoration:underline');
    if (attrs.uppercase)           parts.push('text-transform:uppercase');
    if (attrs.letterSpacing != null) parts.push(`letter-spacing:${attrs.letterSpacing}px`);
    if (attrs.lineHeight    != null) parts.push(`line-height:${attrs.lineHeight}`);
    if (attrs.textAlign     != null) parts.push(`text-align:${attrs.textAlign}`);
    return parts.join(';');
};

const StyledParagraph = Node.create({
    name: 'paragraph',
    priority: 1001,
    group: 'block',
    content: 'inline*',
    parseHTML() {
        return [{ tag: 'p' }];
    },
    renderHTML({ node, HTMLAttributes }) {
        const style = attrsToStyle(node.attrs);
        return ['p', { ...HTMLAttributes, ...(style ? { style } : {}) }, 0];
    },
    addAttributes() {
        return Object.fromEntries(
            STYLE_ATTRS.map((key) => [key, {
                default: null,
                parseHTML: (element) => {
                    const style = element.style;
                    switch (key) {
                        case 'fontSize': {
                            const value = parseFloat(style.fontSize);
                            return Number.isFinite(value) ? value : null;
                        }
                        case 'color':
                            return style.color || null;
                        case 'fontFamily':
                            return style.fontFamily || null;
                        case 'fontWeight':
                            return style.fontWeight === '700' ? 'bold' : style.fontWeight === '400' ? 'regular' : (style.fontWeight || null);
                        case 'italic':
                            return style.fontStyle === 'italic' || null;
                        case 'underline':
                            return style.textDecorationLine.includes('underline') || null;
                        case 'uppercase':
                            return style.textTransform === 'uppercase' || null;
                        case 'textAlign':
                            return style.textAlign || null;
                        case 'letterSpacing': {
                            const value = parseFloat(style.letterSpacing);
                            return Number.isFinite(value) ? value : null;
                        }
                        case 'lineHeight': {
                            const value = parseFloat(style.lineHeight);
                            return Number.isFinite(value) ? value : null;
                        }
                        default:
                            return null;
                    }
                },
                renderHTML: () => ({}),
            }])
        );
    },
});

const props = defineProps({
    paragraphStyles: { type: Array, required: true },
    text: { type: String, required: true },
    editorClass: { type: String, default: '' },
    editorStyle: { type: Object, default: () => ({}) },
    colorOverride: { type: String, default: null },
    transparentFill: { type: Boolean, default: false },
    isLinkedText: { type: Boolean, default: false },
    linkedTextNext: { type: String, default: null },
    boxDimensions: { type: Object, default: null },
    editable: { type: Boolean, default: false },
    displayMode: { type: Boolean, default: false },
    displayHtml: { type: String, default: '' },
    overflowHtml: { type: String, default: '' },
    fullTextHtml: { type: String, default: '' },
    tailHtml: { type: String, default: '' },
    showOverflow: { type: Boolean, default: false },
    linkedTextActive: { type: Boolean, default: false },
    editorTopOffset: { type: Number, default: 0 },
    editorTextOffset: { type: Number, default: 0 },
    isLastInChain: { type: Boolean, default: false },
});
const emit = defineEmits(['update:text', 'update:paragraphStyles', 'update:html', 'selectionChange', 'blur']);


const buildDoc = (text, styles) => {
    const lines = String(text ?? '').replace(/\r\n/g, '\n').split('\n');
    return {
        type: 'doc',
        content: lines.map((line, i) => {
            const s = styles[i] ?? styles[styles.length - 1] ?? {};
            const node = {
                type: 'paragraph',
                attrs: {
                    fontSize:      s.fontSize      ?? null,
                    color:         s.color         ?? null,
                    fontFamily:    s.fontFamily    ?? null,
                    fontWeight:    s.fontWeight    ?? null,
                    italic:        s.italic        ?? null,
                    underline:     s.underline     ?? null,
                    uppercase:     s.uppercase     ?? null,
                    letterSpacing: s.letterSpacing ?? null,
                    lineHeight:    s.lineHeight    ?? null,
                    textAlign:     s.textAlign     ?? null,
                },
                content: line ? [{ type: 'text', text: line }] : [],
            };
            return node;
        }),
    };
};

const extractFromDoc = (doc) => {
    const lines = [];
    const styles = [];
    doc.forEach((node) => {
        if (node.type.name !== 'paragraph') return;
        let lineText = '';
        node.forEach((child) => { lineText += child.text ?? ''; });
        lines.push(lineText);
        const a = node.attrs;
        styles.push({
            fontSize:      a.fontSize      ?? 16,
            color:         a.color         ?? '#ffffff',
            fontFamily:    a.fontFamily    ?? 'Inter, sans-serif',
            fontWeight:    a.fontWeight    ?? 'regular',
            italic:        a.italic        ?? false,
            underline:     a.underline     ?? false,
            uppercase:     a.uppercase     ?? false,
            textAlign:     a.textAlign     ?? 'left',
            letterSpacing: a.letterSpacing ?? 0,
            lineHeight:    a.lineHeight    ?? 1.3,
        });
    });
    return { text: lines.join('\n'), styles };
};

let suppressWatch = false;

const wrapperRef = ref(null);
const editorViewportRef = ref(null);
const overflowRef = ref(null);

const wrapperStyle = computed(() => {
    const style = props.colorOverride ? { '--neon-override-color': props.colorOverride } : {};

    // Regla 3/4: Overflow invisible cuando la cadena no está activa/seleccionada/edición
    // Cuando está activa, usamos overflow:visible para permitir ver el overflow
    if (props.isLinkedText) {
        style.overflow = props.editable ? 'hidden' : (props.linkedTextActive ? 'visible' : 'hidden');
    }

    return style;
});

const linkedTextEditorOffset = computed(() => (
    0 *
    props.isLinkedText && props.editable
        ? Math.max(0, Number(props.editorTopOffset || 0))
        : 0
));

const linkedTextEditorContentStyle = computed(() => ({
    '--linked-text-editor-offset': `${0*linkedTextEditorOffset.value}px`,
}));

const linkedTextBaseLayerStyle = computed(() => ({
    ...props.editorStyle,
    // ...{transform: props.editable?`translateY(${props.editorTopOffset}px)`:''}
}));

const linkedTextEditorInnerStyle = computed(() => ({
    ...props.editorStyle,
    /*transform: linkedTextEditorOffset.value > 0
        ? `translate3d(0, -${linkedTextEditorOffset.value}px, 0)`
        : undefined,*/
}));

const syncEditorViewportOffset = async () => {
    if (!props.isLinkedText || !props.editable) return;
    await nextTick();
    if (!editorViewportRef.value) return;
    // Keep scroll at zero; the visible slice is aligned by translating the full
    // editor content. This keeps pointer/caret coordinates tied to the same DOM
    // that the user sees and avoids the browser resetting scrollTop on mount.
    editorViewportRef.value.scrollTop = 0;
};

const editor = useEditor({
    extensions: [
        StarterKit.configure({ paragraph: false, bold: false, italic: false, code: false, codeBlock: false, blockquote: false, horizontalRule: false, heading: false }),
        TextAlign.configure({ types: ['paragraph'] }),
        StyledParagraph,
        StyledTextMark,
    ],
    editable: props.editable && !props.displayMode,
    content: (props.isLinkedText && props.tailHtml ? props.tailHtml : props.fullTextHtml) || buildDoc(props.text, props.paragraphStyles),
    editorProps: {
        attributes: {
            class: props.editorClass,
            spellcheck: 'false',
        },
        handlePaste({ editor: ed, event }) {
            if (!props.isLinkedText || !ed) return false;

            const pastedText = event?.clipboardData?.getData('text/plain') || '';
            const htmlBefore = ed.getHTML();
            const textBefore = ed.getText();
            const charsBefore = textBefore.length;

            // El paste ocurre antes del onUpdate, así que usamos nextTick
            nextTick(() => {
                const htmlAfter = ed.getHTML();
                const textAfter = ed.getText();
                const charsAfter = textAfter.length;
                const charsAdded = charsAfter - charsBefore;

                frontendLog.info('paste',
                    `Texto pegado en linkedText`,
                    {
                        boxId: wrapperRef.value?.closest('[data-editor-id]')?.dataset?.editorId,
                        pastedLength: pastedText.length,
                        pastedPreview: pastedText.substring(0, 200),
                        charsBefore,
                        charsAfter,
                        charsAdded,
                        htmlBeforeLength: htmlBefore.length,
                        htmlAfterLength: htmlAfter.length,
                        htmlAfterPreview: htmlAfter.substring(0, 300),
                    }
                );
            });

            return false; // Dejar que TipTap maneje el paste normalmente
        },
    },
    onUpdate({ editor: ed }) {
        const { text, styles } = extractFromDoc(ed.state.doc);

        if (!props.editable || props.displayMode) {
            emit('update:paragraphStyles', styles);
            return;
        }

        suppressWatch = true;
        emit('update:text', text);
        emit('update:paragraphStyles', styles);
        emit('update:html', ed.getHTML());
        suppressWatch = false;
    },
    onSelectionUpdate({ editor: ed }) {
        const { from } = ed.state.selection;
        const paragraphIndex = (() => {
            let idx = 0;
            ed.state.doc.forEach((node, offset) => {
                if (node.type.name !== 'paragraph') return;
                const nodeEnd = offset + node.nodeSize;
                if (offset <= from && nodeEnd > from) return;
                if (nodeEnd <= from) idx++;
            });
            return idx;
        })();

        const selectedIndexes = (() => {
            const { from: f, to: t } = ed.state.selection;
            const indexes = new Set();
            let i = 0;
            ed.state.doc.forEach((node, offset) => {
                if (node.type.name !== 'paragraph') return;
                const nodeEnd = offset + node.nodeSize;
                if (offset < t && nodeEnd > f) indexes.add(i);
                i++;
            });
            return [...indexes];
        })();

        emit('selectionChange', { paragraphIndex, selectedIndexes });
    },
    onBlur({ event }) {
        emit('blur', event);
    },
});

const applyStyle = (field, value) => {
    if (!editor?.value) return;
    const { from, to } = editor.value.state.selection;
    const patches = [];
    editor.value.state.doc.forEach((node, offset) => {
        if (node.type.name !== 'paragraph') return;
        const nodeEnd = offset + node.nodeSize;
        if (offset < to && nodeEnd > from) patches.push({ pos: offset + 1, attrs: { ...node.attrs } });
    });
    const tr = editor.value.state.tr;
    patches.forEach(({ pos, attrs }) => {
        const resolvedPos = editor.value.state.doc.resolve(pos);
        const node = resolvedPos.parent;
        tr.setNodeMarkup(resolvedPos.before(), undefined, { ...attrs, [field]: value });
    });
    editor.value.view.dispatch(tr);
};

const applyStyleAll = (field, value) => {
    if (!editor?.value) return;
    const patches = [];
    editor.value.state.doc.forEach((node, offset) => {
        if (node.type.name === 'paragraph') patches.push({ pos: offset + 1, attrs: { ...node.attrs } });
    });
    const tr = editor.value.state.tr;
    patches.forEach(({ pos, attrs }) => {
        const resolvedPos = editor.value.state.doc.resolve(pos);
        tr.setNodeMarkup(resolvedPos.before(), undefined, { ...attrs, [field]: value });
    });
    editor.value.view.dispatch(tr);
};

const getActiveAttrs = () => {
    if (!editor?.value) return {};
    const { from } = editor.value.state.selection;
    const resolved = editor.value.state.doc.resolve(from);
    const parent = resolved.parent;
    if (parent?.type?.name === 'paragraph') {
        return parent.attrs ?? {};
    }

    let result = {};
    editor.value.state.doc.forEach((node, offset) => {
        if (node.type.name !== 'paragraph') return;
        if (offset <= from && offset + node.nodeSize > from) result = node.attrs;
    });
    return result;
};

const focusAtEnd = () => {
    if (!editor?.value) return;
    editor.value.commands.focus('end');
};

const docPositionFromTextOffset = (textOffset = 0) => {
    if (!editor?.value) return 1;
    const target = Math.max(0, Number(textOffset || 0));
    let consumed = 0;
    let result = null;

    editor.value.state.doc.descendants((node, pos) => {
        if (result !== null) return false;
        if (!node.isText) return true;

        const length = node.text?.length ?? 0;
        if (consumed + length >= target) {
            result = pos + Math.max(0, target - consumed);
            return false;
        }

        consumed += length;
        return true;
    });

    return Math.min(Math.max(result ?? editor.value.state.doc.content.size, 1), editor.value.state.doc.content.size);
};

const focusAtPosition = (pos = props.editorTextOffset) => {
    if (!editor?.value) return;
    editor.value.commands.focus(docPositionFromTextOffset(pos));
};

const getPlainText = () => {
    if (!editor?.value) return props.text || '';
    return extractFromDoc(editor.value.state.doc).text;
};

const getParagraphStyles = () => {
    if (!editor?.value) return props.paragraphStyles || [];
    return extractFromDoc(editor.value.state.doc).styles;
};

const applyMarkStyle = (markType, attrs = {}) => {
    if (!editor?.value) return;
    const { from, to } = editor.value.state.selection;
    if (from === to) return;
    const mark = editor.value.schema.marks[markType];
    if (!mark) return;
    const tr = editor.value.state.tr.addMark(from, to, mark.create(attrs));
    editor.value.view.dispatch(tr);
};

const removeMarkStyle = (markType) => {
    if (!editor?.value) return;
    const { from, to } = editor.value.state.selection;
    if (from === to) return;
    const mark = editor.value.schema.marks[markType];
    if (!mark) return;
    const tr = editor.value.state.tr.removeMark(from, to, mark);
    editor.value.view.dispatch(tr);
};

const toggleMarkStyle = (markType, attrs = {}) => {
    if (!editor?.value) return;
    const { from, to } = editor.value.state.selection;
    if (from === to) return;
    const mark = editor.value.schema.marks[markType];
    if (!mark) return;
    let hasMark = false;
    editor.value.state.doc.nodesBetween(from, to, (node) => {
        if (node.marks?.some((m) => m.type.name === markType)) hasMark = true;
    });
    if (hasMark) {
        removeMarkStyle(markType);
    } else {
        applyMarkStyle(markType, attrs);
    }
};

const setContentDirect = (html) => {
    if (!editor?.value) return;
    editor.value.commands.setContent(html, false);
};

const htmlTextContent = (html) => {
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    return tempDiv.textContent || '';
};

const syncEditorContentFromProps = ({ force = false } = {}) => {
    if (!editor?.value || (!force && props.displayMode)) return;
    if (!force && props.editable) return;

    const nextContent = (props.isLinkedText && props.tailHtml ? props.tailHtml : props.fullTextHtml) || buildDoc(props.text, props.paragraphStyles);
    const currentText = editor.value.getText() || '';
    const currentHtml = editor.value.getHTML() || '';
    const nextText = typeof nextContent === 'string'
        ? htmlTextContent(nextContent)
        : String(props.text ?? '');
    const htmlChanged = typeof nextContent === 'string' && currentHtml !== nextContent;
    const docChanged = typeof nextContent !== 'string';

    if (currentText !== nextText || htmlChanged || docChanged) {
        suppressWatch = true;
        editor.value.commands.setContent(nextContent, false);
        suppressWatch = false;
    }
};

const getHtml = () => {
    if (!editor?.value) return '';
    return editor.value.getHTML();
};

defineExpose({
    applyStyle,
    applyStyleAll,
    getActiveAttrs,
    focusAtEnd,
    focusAtPosition,
    getPlainText,
    getParagraphStyles,
    getHtml,
    applyMarkStyle,
    removeMarkStyle,
    toggleMarkStyle,
    setContentDirect,
    setCursorAtCoords(clientX, clientY) {
        if (!editor?.value) {
            frontendLog.debug('setCursorAtCoords', 'editor not ready');
            return;
        }
        const view = editor.value.view;
        const dom = view.dom;
        const domRect = dom.getBoundingClientRect();
        frontendLog.debug('setCursorAtCoords', `coords=(${clientX},${clientY}) domRect=${JSON.stringify({x:domRect.x,y:domRect.y,w:domRect.width,h:domRect.height})}`);
        const posResult = view.posAtCoords({ left: clientX, top: clientY });
        frontendLog.debug('setCursorAtCoords', `posAtCoords result: ${JSON.stringify(posResult)}`);
        if (!posResult) return;
        view.focus();
        requestAnimationFrame(() => {
            const $pos = view.state.doc.resolve(posResult.pos);
            const tr = view.state.tr.setSelection(TextSelection.near($pos));
            view.dispatch(tr);
            frontendLog.debug('setCursorAtCoords', `cursor set at pos ${posResult.pos}, selection=${JSON.stringify({from: view.state.selection.from, to: view.state.selection.to})}`);
        });
    },
});

watch(() => props.editable, (val, oldVal) => {
    if (val && !oldVal) {
        // On entering edit mode, hydrate TipTap from the latest canonical
        // linked HTML generated by layout/paragraphStyles. While displayMode is
        // active the editor instance is intentionally not kept in sync, so
        // without this the next edit can reopen stale font sizes/styles.
        syncEditorContentFromProps({ force: true });
    }
    editor?.value?.setEditable(val && !props.displayMode);
    syncEditorViewportOffset();
});

watch(() => props.editorTopOffset, () => {
    syncEditorViewportOffset();
});

watch(() => props.displayMode, (val, oldVal) => {
    if (oldVal && !val) {
        syncEditorContentFromProps({ force: true });
    }
    editor?.value?.setEditable(props.editable && !val);

    // Log de estilos cuando cambia el modo display
    if (props.isLinkedText) {
        nextTick(() => {
            logLinkedTextStyles();
        });
    }
});

watch(() => props.fullTextHtml, (html) => {
    // While the user is typing, TipTap must remain the source of truth.
    // The parent re-emits the same linked fullTextHtml after redistribution;
    // calling setContent here replaces the document and moves selection to end.
    if (suppressWatch || !html || !editor?.value || props.displayMode || props.editable) return;
    if (props.isLinkedText && props.tailHtml) return;
    syncEditorContentFromProps();
});

watch(() => props.tailHtml, (html) => {
    if (suppressWatch || !html || !editor?.value || props.displayMode || props.editable) return;
    if (!props.isLinkedText) return;
    syncEditorContentFromProps();
});

watch(() => [props.text, props.paragraphStyles], ([newText, newStyles]) => {
    if (suppressWatch || !editor?.value || props.displayMode || props.editable) return;
    if (props.fullTextHtml || (props.isLinkedText && props.tailHtml)) return;
    const current = extractFromDoc(editor.value.state.doc);
    const textChanged = current.text !== newText;
    const stylesChanged = JSON.stringify(current.styles) !== JSON.stringify(newStyles ?? []);

    if (textChanged || stylesChanged) {
        editor.value.commands.setContent(buildDoc(newText, newStyles), false);
    }
}, { deep: true });

// Log de estilos cuando se monta el componente
onMounted(() => {
    syncEditorViewportOffset();

    if (props.isLinkedText) {
        nextTick(() => {
            logLinkedTextStyles();
        });
    }
});

onBeforeUnmount(() => {
    editor?.value?.destroy();
});

/**
 * Registrar y comparar estilos CSS entre modo display y modo edición.
 */
const logLinkedTextStyles = () => {
    if (!props.isLinkedText) return;

    const boxId = wrapperRef.value?.closest('[data-editor-id]')?.dataset?.editorId;
    if (!boxId) return;

    // Obtener estilos del contenedor padre (elementContentStyle)
    const parentElement = wrapperRef.value?.parentElement;
    const parentStyles = parentElement ? window.getComputedStyle(parentElement) : null;

    // Obtener estilos del contenedor display o editor
    let contentElement = null;
    let mode = 'unknown';

    if (props.displayMode) {
        contentElement = wrapperRef.value?.querySelector('.linked-text-display');
        mode = 'display';
    } else {
        contentElement = wrapperRef.value?.querySelector('.ProseMirror');
        mode = 'edit';
    }

    const contentStyles = contentElement ? window.getComputedStyle(contentElement) : null;

    // Registrar estilos
    const parentStyleData = parentStyles ? frontendLog.logElementStyles(
        boxId,
        `${mode}-parent`,
        parentElement,
        parentStyles
    ) : {};

    const contentStyleData = contentStyles ? frontendLog.logElementStyles(
        boxId,
        mode,
        contentElement,
        contentStyles
    ) : {};

    // Si tenemos ambos modos, comparar
    if (props.displayMode) {
        // Guardar estilos display para comparación posterior
        window.__linkedTextDisplayStyles = window.__linkedTextDisplayStyles || {};
        window.__linkedTextDisplayStyles[boxId] = {
            parent: parentStyleData,
            content: contentStyleData,
        };
    } else {
        // Comparar con estilos display guardados
        const savedStyles = window.__linkedTextDisplayStyles?.[boxId];
        if (savedStyles) {
            frontendLog.logLinkedTextStyleComparison(
                boxId,
                savedStyles.content,
                contentStyleData,
                {
                    displayParentStyles: savedStyles.parent,
                    editParentStyles: parentStyleData,
                    displayMode: props.displayMode,
                    editable: props.editable,
                    editorStyle: props.editorStyle,
                }
            );
        }
    }
};
</script>

<template>
    <div
            ref="wrapperRef"
            :class="{
                'neon-active': !!props.colorOverride,
                'hollow-active': props.transparentFill,
                'linked-text-display-mode': props.displayMode,
                'linked-text-active': props.isLinkedText && props.linkedTextActive
            }"
            :style="wrapperStyle"
        >
        <!-- Nueva estrategia: dos capas -->
        <!-- Capa inferior: texto completo (sin límite inferior), opacidad 50% -->
        <div
            v-if="props.isLinkedText && props.showOverflow && props.tailHtml && props.isLastInChain"
            class="linked-text-base-layer"
            :style="linkedTextBaseLayerStyle"
            v-html="props.tailHtml"
        ></div>

        <!-- Capa superior: texto visible (recortado) -->
        <div
            v-if="props.displayMode"
            class="linked-text-display"
            :class="{ 'linked-text-clipped': props.isLinkedText && !props.linkedTextActive }"
            :style="props.editorStyle"
            v-html="props.displayHtml"
        ></div>
        <div
            v-else-if="props.isLinkedText && props.editable"
            ref="editorViewportRef"
            class="linked-text-editor-viewport"
        >
            <div class="linked-text-editor-content" :style="linkedTextEditorContentStyle">
                <EditorContent
                    :editor="editor"
                    :style="linkedTextEditorInnerStyle"
                />
            </div>
        </div>
        <EditorContent
            v-else
            :editor="editor"
            :style="props.editorStyle"
        />
    </div>
</template>

<style>
.neon-active .ProseMirror p {
    color: var(--neon-override-color) !important;
}
.hollow-active .ProseMirror,
.hollow-active .ProseMirror p {
    color: transparent !important;
    -webkit-text-fill-color: transparent !important;
}
.ProseMirror {
    outline: none;
    white-space: pre-wrap;
    word-break: break-word;
    overflow-wrap: break-word;
    cursor: text;
    color: inherit;
    text-shadow: inherit;
    -webkit-text-stroke: inherit;
    position: relative;
    z-index: 20;
}
.ProseMirror p {
    margin: 0;
    padding: 0;
    text-shadow: inherit;
    -webkit-text-stroke: inherit;
}
.linked-text-display {
    outline: none;
    white-space: pre-wrap;
    word-break: break-word;
    overflow-wrap: break-word;
    cursor: text;
    color: inherit;
    text-shadow: inherit;
    -webkit-text-stroke: inherit;
    overflow: visible;
    position: relative;
    z-index: 20;
}
.linked-text-display p {
    margin: 0;
    padding: 0;
    text-shadow: inherit;
    -webkit-text-stroke: inherit;
}
.linked-text-display-mode {
    position: relative;
    height: 100%;
    overflow: visible;
}
.linked-text-display-mode .linked-text-display {
    overflow: visible;
    height: 100%;
    box-sizing: border-box;
    position: relative;
}
.linked-text-display-mode .linked-text-display.linked-text-clipped {
    overflow: hidden;
    height: 100%;
}
.linked-text-active .linked-text-display {
    overflow: hidden;
}
/* Nueva estrategia: capa base con texto completo */
.linked-text-base-layer {
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
    pointer-events: auto;
    z-index: 5;
    color: gray !important;
    opacity: 0.45 !important;
    white-space: pre-wrap;
    word-break: break-word;
    overflow-wrap: break-word;
}
/* Cuando está activa, la capa visible recorta */
.linked-text-active .linked-text-display {
    overflow: hidden;
    height: 100%;
}
.linked-text-overflow {
    position: absolute;
    left: 0;
    top: 100%;
    width: 100%;
    pointer-events: none;
    z-index: 10;
    opacity: 0.5;
}
.linked-text-display-mode .linked-text-display.linked-text-clipped {
    overflow: hidden;
    height: 100%;
}
.linked-text-overflow {
    position: absolute;
    left: 0;
    top: 100%;
    width: 100%;
    pointer-events: none;
    z-index: 10;
    opacity: 0.5;
}
.linked-text-active .linked-text-display {
    overflow: hidden !important;
}
.linked-text-editor-viewport {
    width: 100%;
    height: 100%;
    overflow: hidden;
    position: relative;
    z-index: 20;
    box-sizing: border-box;
}
.linked-text-editor-content {
    width: 100%;
    min-height: 100%;
    transform-origin: left top;
    box-sizing: border-box;
}
.linked-text-editor-viewport .ProseMirror {
    width: 100%;
    min-height: 100%;
    box-sizing: border-box;
}
.linked-text-overflow {
    position: absolute;
    left: 0;
    top: 100%;
    width: 100%;
    pointer-events: none;
    z-index: 10;
    opacity: 0.5;
}
</style>
