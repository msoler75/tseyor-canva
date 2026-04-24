<?php

namespace App\Support;

// DRY: Sincroniza los campos title, subtitle, meta, contact, extra entre content y elementLayout
class DesignerStateSync {
    // DRY: Sincroniza los campos title, subtitle, meta, contact, extra entre content y elementLayout
    public static function syncContentAndElementLayout(array &$content, array &$elementLayout): void {
        foreach (['title','subtitle','meta','contact','extra'] as $key) {
            if (
                isset($elementLayout[$key]['text']) &&
                is_string($elementLayout[$key]['text']) &&
                $elementLayout[$key]['text'] !== '' &&
                (!isset($content[$key]) || $content[$key] === '')
            ) {
                $content[$key] = $elementLayout[$key]['text'];
            }
            if (
                isset($content[$key]) && $content[$key] !== '' &&
                isset($elementLayout[$key]) &&
                (!isset($elementLayout[$key]['text']) || $elementLayout[$key]['text'] === '')
            ) {
                $elementLayout[$key]['text'] = $content[$key];
            }
        }
    }
}
