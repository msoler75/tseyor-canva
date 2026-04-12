<script setup>
import { watch, onBeforeUnmount } from 'vue';
import { useEditor, EditorContent } from '@tiptap/vue-3';
import StarterKit from '@tiptap/starter-kit';
import { TextAlign } from '@tiptap/extension-text-align';
import { Node } from '@tiptap/core';

const STYLE_ATTRS = ['fontSize', 'color', 'fontFamily', 'fontWeight', 'italic', 'uppercase', 'textAlign', 'letterSpacing', 'lineHeight'];

const attrsToStyle = (attrs) => {
    const parts = [];
    if (attrs.fontSize    != null) parts.push(`font-size:${attrs.fontSize}px`);
    if (attrs.color       != null) parts.push(`color:${attrs.color}`);
    if (attrs.fontFamily  != null) parts.push(`font-family:${attrs.fontFamily}`);
    if (attrs.fontWeight  != null) parts.push(`font-weight:${attrs.fontWeight === 'bold' ? 700 : 500}`);
    if (attrs.italic)              parts.push('font-style:italic');
    if (attrs.uppercase)           parts.push('text-transform:uppercase');
    if (attrs.letterSpacing != null) parts.push(`letter-spacing:${attrs.letterSpacing}px`);
    if (attrs.lineHeight    != null) parts.push(`line-height:${attrs.lineHeight}`);
    if (attrs.textAlign     != null) parts.push(`text-align:${attrs.textAlign}`);
    return parts.join(';');
};

// Extiende el nodo Paragraph nativo con atributos de estilo propios
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
            STYLE_ATTRS.map((key) => [key, { default: null, parseHTML: () => null, renderHTML: () => ({}) }])
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
    editable: { type: Boolean, default: false },
});
const emit = defineEmits(['update:text', 'update:paragraphStyles', 'selectionChange', 'blur']);

// Construye el documento TipTap desde el texto plano + array de paragraphStyles
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

// Extrae texto plano y paragraphStyles desde el doc TipTap
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
            uppercase:     a.uppercase     ?? false,
            textAlign:     a.textAlign     ?? 'left',
            letterSpacing: a.letterSpacing ?? 0,
            lineHeight:    a.lineHeight    ?? 1.3,
        });
    });
    return { text: lines.join('\n'), styles };
};

let suppressWatch = false;

const editor = useEditor({
    extensions: [
        StarterKit.configure({ paragraph: false, bold: false, italic: false, code: false, codeBlock: false, blockquote: false, horizontalRule: false, heading: false }),
        TextAlign.configure({ types: ['paragraph'] }),
        StyledParagraph,
    ],
    editable: props.editable,
    content: buildDoc(props.text, props.paragraphStyles),
    editorProps: {
        attributes: {
            class: props.editorClass,
            spellcheck: 'false',
        },
    },
    onUpdate({ editor: ed }) {
        suppressWatch = true;
        const { text, styles } = extractFromDoc(ed.state.doc);
        emit('update:text', text);
        emit('update:paragraphStyles', styles);
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

// Aplica un campo de estilo a los párrafos actualmente seleccionados en el editor
const applyStyle = (field, value) => {
    if (!editor.value) return;
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

// Aplica un campo de estilo a TODOS los párrafos (modo sin edición: caja completa)
const applyStyleAll = (field, value) => {
    if (!editor.value) return;
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

// Devuelve los atributos del párrafo donde está el cursor
const getActiveAttrs = () => {
    if (!editor.value) return {};
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
    if (!editor.value) return;
    editor.value.commands.focus('end');
};

// Expone API para que EditorPage pueda llamar
defineExpose({ applyStyle, applyStyleAll, getActiveAttrs, focusAtEnd });

// Cuando cambia el prop editable, actualizar el editor
watch(() => props.editable, (val) => {
    editor.value?.setEditable(val);
});

// Si el texto externo cambia (por sync con state), reconstruimos el doc
watch(() => [props.text, props.paragraphStyles], ([newText, newStyles]) => {
    if (suppressWatch || !editor.value) return;
    const currentText = extractFromDoc(editor.value.state.doc).text;
    if (currentText !== newText) {
        editor.value.commands.setContent(buildDoc(newText, newStyles), false);
    }
}, { deep: true });

onBeforeUnmount(() => {
    editor.value?.destroy();
});
</script>

<template>
    <div
        :class="{ 'neon-active': !!props.colorOverride, 'hollow-active': props.transparentFill }"
        :style="props.colorOverride ? { '--neon-override-color': props.colorOverride } : {}"
    >
        <EditorContent :editor="editor" :style="editorStyle" />
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
    cursor: text;
    color: inherit;
    text-shadow: inherit;
    -webkit-text-stroke: inherit;
}
.ProseMirror p {
    margin: 0;
    padding: 0;
    text-shadow: inherit;
    -webkit-text-stroke: inherit;
}
</style>
