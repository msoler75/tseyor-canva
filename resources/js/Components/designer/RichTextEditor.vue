<script setup>
import { watch, onBeforeUnmount, onMounted, nextTick, ref, computed } from 'vue';
import { useEditor, EditorContent } from '@tiptap/vue-3';
import StarterKit from '@tiptap/starter-kit';
import { TextAlign } from '@tiptap/extension-text-align';
import ListItem from '@tiptap/extension-list-item';
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
            textTransform: { default: null },
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
        if (HTMLAttributes.textTransform) style.push(`text-transform:${HTMLAttributes.textTransform}`);
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

const StyledListItem = ListItem.extend({
    addNodeView() {
        return ({ node }) => {
            const dom = document.createElement('li');

            const updateStyle = () => {
                const firstParagraph = node.firstChild;
                const fontSize = firstParagraph?.attrs?.fontSize;
                if (fontSize) {
                    dom.style.fontSize = `${fontSize}px`;
                } else {
                    dom.style.fontSize = '';
                }
            };

            updateStyle();

            return {
                dom,
                contentDOM: dom,
                update: (updatedNode) => {
                    if (updatedNode.type.name !== 'listItem') return false;
                    node = updatedNode;
                    updateStyle();
                    return true;
                },
            };
        };
    },
});

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
    initialHtml: { type: String, default: '' },
    showOverflow: { type: Boolean, default: false },
    linkedTextActive: { type: Boolean, default: false },
    editorTopOffset: { type: Number, default: 0 }, /* este atributo ya no se usa */
    editorTextOffset: { type: Number, default: 0 },
    isLastInChain: { type: Boolean, default: false },
    forceSelectAll: { type: Boolean, default: false },
});
const emit = defineEmits(['update:text', 'update:paragraphStyles', 'update:html', 'selectionChange', 'blur', 'selectAllInChain']);


const buildParagraphAttrs = (s) => ({
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
});

const buildParagraphNode = (line, attrs) => ({
    type: 'paragraph',
    attrs: buildParagraphAttrs(attrs),
    content: line ? [{ type: 'text', text: line }] : [],
});

const buildDoc = (text, styles) => {
    const lines = String(text ?? '').replace(/\r\n/g, '\n').split('\n');
    const content = [];
    let listBuffer = [];
    let listTypeBuffer = null;

    const flushList = () => {
        if (listBuffer.length === 0) return;
        const nodeType = listTypeBuffer === 'bullet' ? 'bulletList' : 'orderedList';
        content.push({
            type: nodeType,
            content: listBuffer.map(({ line, s }) => ({
                type: 'listItem',
                content: [buildParagraphNode(line, s)],
            })),
        });
        listBuffer = [];
        listTypeBuffer = null;
    };

    lines.forEach((line, i) => {
        const s = styles[i] ?? styles[styles.length - 1] ?? {};
        const lt = s.listType ?? null;

        if (lt) {
            if (lt !== listTypeBuffer) {
                flushList();
                listTypeBuffer = lt;
            }
            listBuffer.push({ line, s });
        } else {
            flushList();
            content.push(buildParagraphNode(line, s));
        }
    });

    flushList();
    return { type: 'doc', content };
};

const extractFromDoc = (doc) => {
    const lines = [];
    const styles = [];

    const walk = (nodes, currentListType) => {
        if (!nodes || !nodes.forEach) return;
        nodes.forEach((node) => {
            if (node.type.name === 'bulletList') {
                walk(node.content, 'bullet');
            } else if (node.type.name === 'orderedList') {
                walk(node.content, 'ordered');
            } else if (node.type.name === 'listItem') {
                walk(node.content, currentListType);
            } else if (node.type.name === 'paragraph') {
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
                    listType:      currentListType  ?? null,
                });
            }
        });
    };

    walk(doc.content, null);
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

const displayStyle = computed(() => {
    const style = { ...props.editorStyle };
    if (props.boxDimensions?.fontSize) {
        style.fontSize = `${props.boxDimensions.fontSize}px`;
    }
    if (props.boxDimensions?.lineHeight) {
        style.lineHeight = String(props.boxDimensions.lineHeight);
    }
    return style;
});

const linkedTextEditorOffset = computed(() => (
    props.isLinkedText && props.editable
        ? Math.max(0, Number(props.editorTopOffset || 0))
        : 0
));

const linkedTextEditorContentStyle = computed(() => ({
    '--linked-text-editor-offset': `${linkedTextEditorOffset.value}px`,
}));

const linkedTextEditorInnerStyle = computed(() => ({
    ...props.editorStyle,
}));

const syncEditorViewportOffset = async () => {
    if (!props.isLinkedText || !props.editable) return;
    await nextTick();
    if (!editorViewportRef.value) return;
    // Scroll al inicio del contenido que corresponde a esta caja
    editorViewportRef.value.scrollTop = linkedTextEditorOffset.value;
};

const editor = useEditor({
    extensions: [
        StarterKit.configure({ paragraph: false, bold: false, italic: false, code: false, codeBlock: false, blockquote: false, horizontalRule: false, heading: false, listItem: false }),
        TextAlign.configure({ types: ['paragraph'] }),
        StyledListItem,
        StyledParagraph,
        StyledTextMark,
    ],
    editable: props.editable && !props.displayMode,
    content: props.fullTextHtml || buildDoc(props.text, props.paragraphStyles),
    editorProps: {
        attributes: {
            class: props.editorClass,
            spellcheck: 'false',
        },
        handleKeyDown(view, event) {
            if ((event.ctrlKey || event.metaKey) && !event.altKey && event.key.toLowerCase() === 'a') {
                if (!props.isLinkedText) return false;
                nextTick(() => emit('selectAllInChain'));
                return false;
            }
            return false;
        },
        handlePaste(view, event) {
            const ed = editor.value;
            if (!props.isLinkedText || !ed) return false;

            const pastedText = event?.clipboardData?.getData('text/plain') || '';
            const pastedHtml = event?.clipboardData?.getData('text/html') || '';
            const hasRichFormatting = htmlContainsRichFormatting(pastedHtml);

            if (hasRichFormatting && typeof window !== 'undefined') {
                const keepFormatting = window.confirm(
                    'Este texto tiene formato (negritas, listas, encabezados, etc.).\n\n' +
                    '¿Quieres conservar el formato al pegarlo?'
                );
                if (!keepFormatting) {
                    event?.preventDefault?.();
                    ed.commands.insertContent(String(pastedText ?? '').replace(/\r\n/g, '\n'));
                    return true;
                }
            }

            const htmlBefore = ed.getHTML();
            const textBefore = ed.getText();
            const charsBefore = textBefore.length;

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

                syncEditorViewportOffset();
            });

            return false;
        },
    },
    onUpdate({ editor: ed }) {
        const { text, styles } = extractFromDoc(ed.state.doc);

        if (!props.editable || props.displayMode) {
            if (props.isLinkedText) return;
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
        console.log('[SEL-UPDATE] id=', props.id, 'editable=', props.editable, 'displayMode=', props.displayMode);
        if (!props.editable || props.displayMode) {
            console.log('[SEL-UPDATE] BLOCKED for id=', props.id);
            return;
        }
        const { from, to: selectionTo } = ed.state.selection;

        const paragraphs = [];
        ed.state.doc.nodesBetween(0, ed.state.doc.content.size, (node, pos) => {
            if (node.type.name === 'paragraph') {
                paragraphs.push({ pos, end: pos + node.nodeSize });
            }
        });

        const paragraphIndex = (() => {
            for (let i = 0; i < paragraphs.length; i++) {
                const { pos, end } = paragraphs[i];
                if (pos <= from && end > from) return i;
            }
            return 0;
        })();

        const selectedIndexes = paragraphs
            .map(({ pos, end }, i) => (pos < selectionTo && end > from) ? i : -1)
            .filter(i => i !== -1);

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
    editor.value.state.doc.nodesBetween(0, editor.value.state.doc.content.size, (node, pos) => {
        if (node.type.name !== 'paragraph') return;
        const nodeEnd = pos + node.nodeSize;
        if (pos < to && nodeEnd > from) patches.push({ pos, attrs: { ...node.attrs } });
    });
    const tr = editor.value.state.tr;
    patches.forEach(({ pos, attrs }) => {
        tr.setNodeMarkup(pos, undefined, { ...attrs, [field]: value });
    });
    editor.value.view.dispatch(tr);
};

const applyStyleAll = (field, value) => {
    if (!editor?.value) return;
    const patches = [];
    editor.value.state.doc.nodesBetween(0, editor.value.state.doc.content.size, (node, pos) => {
        if (node.type.name === 'paragraph') patches.push({ pos, attrs: { ...node.attrs } });
    });
    const tr = editor.value.state.tr;
    patches.forEach(({ pos, attrs }) => {
        tr.setNodeMarkup(pos, undefined, { ...attrs, [field]: value });
    });
    editor.value.view.dispatch(tr);
};

const MIXED_FIELDS = ['fontFamily', 'fontSize', 'color', 'fontWeight', 'italic', 'underline', 'uppercase', 'textAlign', 'letterSpacing', 'lineHeight'];

const getMixedState = () => {
    if (!editor?.value) return {};
    const { styles } = extractFromDoc(editor.value.state.doc);
    if (!styles.length) return {};
    const result = {};
    for (const field of MIXED_FIELDS) {
        const values = [...new Set(styles.map(s => {
            const v = s[field];
            return v === undefined || v === null ? '__NULL__' : v;
        }))];
        result[field] = values.length > 1 ? 'mixed' : styles[0][field] ?? null;
    }
    return result;
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
    editor.value.state.doc.nodesBetween(0, editor.value.state.doc.content.size, (node, offset) => {
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

const toggleListType = () => {
    if (!editor?.value) return;
    const isBullet = editor.value.isActive('bulletList');
    const isOrdered = editor.value.isActive('orderedList');

    if (!isBullet && !isOrdered) {
        editor.value.chain().focus().toggleBulletList().run();
    } else if (isBullet) {
        editor.value.chain().focus().toggleBulletList().toggleOrderedList().run();
    } else {
        editor.value.chain().focus().toggleOrderedList().run();
    }
};

const getListType = () => {
    if (!editor?.value) return 'none';
    if (editor.value.isActive('bulletList')) return 'bullet';
    if (editor.value.isActive('orderedList')) return 'ordered';
    return 'none';
};

const getSelection = () => {
    if (!editor?.value) return { from: 0, to: 0 };
    const { from, to } = editor.value.state.selection;
    return { from, to };
};

const CHAR_STYLE_TO_MARK = {
  color: 'color',
  fontWeight: 'fontWeight',
  italic: { mark: 'styledText', attr: 'fontStyle', value: 'italic' },
  underline: { mark: 'styledText', attr: 'textDecoration', value: 'underline' },
  uppercase: { mark: 'styledText', attr: 'textTransform', value: 'uppercase' },
  fontSize: 'fontSize',
  fontFamily: 'fontFamily',
};

const applyCharacterStyle = (field, value) => {
    if (!editor?.value) return;
    const { from, to } = editor.value.state.selection;
    if (from === to) return;
    const mapping = CHAR_STYLE_TO_MARK[field];
    if (!mapping) return;
    const mark = editor.value.schema.marks.styledText;
    if (!mark) return;

    const tr = editor.value.state.tr;

    // Merge existing styledText marks on the selection range
    const existingAttrs = {};
    editor.value.state.doc.nodesBetween(from, to, (node) => {
        if (node.marks) {
            node.marks.forEach((m) => {
                if (m.type.name === 'styledText') {
                    Object.keys(m.attrs).forEach((k) => {
                        if (m.attrs[k] !== null && m.attrs[k] !== undefined) {
                            existingAttrs[k] = m.attrs[k];
                        }
                    });
                }
            });
        }
    });

    // Remove all existing styledText marks in range first
    tr.removeMark(from, to, mark);

    // Build new attrs: merge existing + new, handling toggle fields
    const newAttrKey = typeof mapping === 'object' ? mapping.attr : mapping;
    const isToggleField = field === 'fontWeight' || field === 'italic' || field === 'underline' || field === 'uppercase';
    const toggleValue = typeof mapping === 'object' ? mapping.value : value;

    let finalAttrs;
    if (isToggleField) {
        if (value) {
            // Set the attribute ON
            finalAttrs = { ...existingAttrs, [newAttrKey]: toggleValue };
        } else {
            // Remove the attribute OFF
            const { [newAttrKey]: _, ...rest } = existingAttrs;
            finalAttrs = rest;
        }
    } else {
        finalAttrs = { ...existingAttrs, [newAttrKey]: value };
    }

    // Only add mark if there are attrs
    const hasAttrs = Object.values(finalAttrs).some(v => v !== null && v !== undefined);
    if (hasAttrs) {
        tr.addMark(from, to, mark.create(finalAttrs));
    }

    tr.scrollIntoView();
    editor.value.view.dispatch(tr);
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

const htmlContainsRichFormatting = (html = '') => {
    if (!html || !html.trim()) return false;
    if (/\sstyle=|\sclass=|<a\b/i.test(html)) return true;
    if (/<(strong|b|em|i|u|span|font|mark|h[1-6]|ul|ol|li|table|blockquote|code)\b/i.test(html)) return true;
    return false;
};

const syncEditorContentFromProps = ({ force = false } = {}) => {
    if (!editor?.value || (!force && props.displayMode)) return;
    if (!force && props.editable) return;

    const nextContent = props.initialHtml || props.fullTextHtml || buildDoc(props.text, props.paragraphStyles);
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

const selectAll = () => {
    if (!editor?.value) return;
    editor.value.commands.selectAll();
};

const getHtml = () => {
    if (!editor?.value) return '';
    return editor.value.getHTML();
};

const getMarkAttributes = (markName) => {
    if (!editor?.value) return {};
    return editor.value.getAttributes(markName);
};

defineExpose({
    selectAll,
    applyStyle,
    applyStyleAll,
    applyCharacterStyle,
    getActiveAttrs,
    getMixedState,
    focusAtEnd,
    focusAtPosition,
    getPlainText,
    getParagraphStyles,
    getHtml,
    getMarkAttributes,
    applyMarkStyle,
    removeMarkStyle,
    toggleMarkStyle,
    setContentDirect,
    toggleListType,
    getListType,
    getSelection,
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
    if (suppressWatch || !html || !editor?.value || props.displayMode || props.editable) return;
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
                'linked-text-active': props.isLinkedText && props.linkedTextActive,
                'force-select-all': props.forceSelectAll
            }"
            :style="wrapperStyle"
        >
        <!-- Nueva estrategia: dos capas -->
        <!-- Capa visible: texto recortado a la altura de la caja -->
        <div
            v-if="props.displayMode"
            class="linked-text-display"
            :class="{ 'linked-text-clipped': props.isLinkedText && !props.linkedTextActive }"
            :style="displayStyle"
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
    caret-color: #ff8c00;
}
.ProseMirror p {
    margin: 0;
    padding: 0;
    text-shadow: inherit;
    -webkit-text-stroke: inherit;
}
.linked-text-display p:empty {
    min-height: 1em;
}
.ProseMirror-gapcursor:after {
    border-top-color: #ff8c00 !important;
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
    overflow-y: auto;
    overflow-x: hidden;
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
    white-space: pre-wrap;
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
.ProseMirror ul,
.ProseMirror ol,
.linked-text-display ul,
.linked-text-display ol {
    list-style-position: outside;
    padding-left: 1.5em;
    margin: 0;
}
.ProseMirror ul,
.linked-text-display ul {
    list-style: disc;
}
.ProseMirror ol,
.linked-text-display ol {
    list-style: decimal;
}
.ProseMirror li,
.linked-text-display li {
    margin: 0;
    padding: 0;
}
.ProseMirror li p,
.linked-text-display li p {
    margin: 0;
    padding: 0;
}
.force-select-all .ProseMirror p,
.force-select-all .linked-text-display p {
    background: rgba(45, 170, 219, 0.15);
    border-radius: 2px;
}
.force-select-all .ProseMirror p:empty,
.force-select-all .linked-text-display p:empty {
    background: none;
}
</style>
