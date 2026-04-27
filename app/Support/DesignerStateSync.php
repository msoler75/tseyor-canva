<?php

namespace App\Support;

class DesignerStateSync
{
    /**
     * Normaliza content y elementLayout sin devolver textos viejos por encima del contenido vigente.
     *
     * @param array<string, mixed> $content
     * @param array<string, mixed> $elementLayout
     */
    public static function syncContentAndElementLayout(array &$content, array &$elementLayout): void
    {
        foreach (['title', 'subtitle', 'meta', 'contact', 'extra'] as $key) {
            $contentText = self::resolveTextValue($key, $content);
            $layoutText = isset($elementLayout[$key]['text']) && is_string($elementLayout[$key]['text'])
                ? trim($elementLayout[$key]['text'])
                : '';

            if ($contentText !== '') {
                $content[$key] = $contentText;
                if (! isset($elementLayout[$key]) || ! is_array($elementLayout[$key])) {
                    $elementLayout[$key] = [];
                }
                $elementLayout[$key]['text'] = $contentText;
                continue;
            }

            if ($layoutText !== '') {
                $content[$key] = $layoutText;
                if (! isset($elementLayout[$key]) || ! is_array($elementLayout[$key])) {
                    $elementLayout[$key] = [];
                }
                $elementLayout[$key]['text'] = $layoutText;
                continue;
            }

            $content[$key] = $content[$key] ?? '';
            if (isset($elementLayout[$key]) && is_array($elementLayout[$key])) {
                unset($elementLayout[$key]['text']);
            }
        }
    }

    /**
     * @param array<string, mixed> $content
     */
    private static function resolveTextValue(string $key, array $content): string
    {
        return match ($key) {
            'title', 'subtitle', 'contact', 'extra' => trim((string) ($content[$key] ?? '')),
            'meta' => implode(' · ', array_filter([
                trim((string) ($content['date'] ?? '')),
                trim((string) ($content['time'] ?? '')),
            ])),
            default => trim((string) ($content[$key] ?? '')),
        };
    }
}
