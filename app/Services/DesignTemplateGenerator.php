<?php

namespace App\Services;

use App\Models\Design;
use App\Models\DesignTemplate;
use App\Models\User;
use Illuminate\Support\Arr;
use Illuminate\Support\Str;

class DesignTemplateGenerator
{
    private const BASE_TEXT_ELEMENT_IDS = ['title', 'subtitle', 'meta', 'contact', 'extra'];

    private const FIELD_ALIASES = [
        'title' => ['title', 'titulo', 'título', 'main-title', 'headline', 'encabezado', 'nombre'],
        'subtitle' => ['subtitle', 'subtitulo', 'subtítulo', 'claim', 'entradilla', 'descripcion', 'descripción'],
        'date' => ['date', 'fecha'],
        'time' => ['time', 'hora'],
        'location' => ['location', 'ubicacion', 'ubicación', 'lugar', 'venue'],
        'platform' => ['platform', 'plataforma', 'url', 'enlace'],
        'teacher' => ['teacher', 'profesor', 'profesora', 'ponente', 'facilitador'],
        'price' => ['price', 'precio', 'importe'],
        'contact' => ['contact', 'contacto', 'contact-info', 'datos-contacto', 'datos de contacto'],
        'extra' => ['extra', 'notas', 'texto-adicional', 'texto adicional', 'descripcion-larga', 'descripción larga'],
        'datos1' => ['datos1', 'dato1', 'datos-1'],
        'datos2' => ['datos2', 'dato2', 'datos-2'],
        'image' => ['image', 'imagen', 'main-image', 'imagen-principal', 'hero-image'],
        'mainImage' => ['mainimage', 'main-image', 'imagen-principal', 'hero-image', 'image', 'imagen'],
    ];

    /**
     * @param  array<string, mixed>  $data
     * @param  array<string, mixed>|null  $targetSurface
     */
    public function generate(DesignTemplate $template, User $user, array $data = [], ?array $targetSurface = null, ?Design $targetDesign = null): Design
    {
        /** @var Design $baseDesign */
        $baseDesign = $template->baseDesign;
        $state = $baseDesign->state ?? [];
        $targetSurface = $this->normalizeSurface($targetSurface)
            ?? $this->normalizeSurface(Arr::get($data, 'designSurface'))
            ?? $this->surfaceFromDesign($baseDesign);

        if ($targetSurface) {
            $state = $this->adaptStateToSurface($state, $this->surfaceFromState($state, $baseDesign), $targetSurface);
        }

        $state = $this->applyData($state, $data, $template->field_mappings ?? []);

        $uuid = $targetDesign?->uuid ?? (string) Str::uuid();
        $state['currentDesignUuid'] = $uuid;
        $state['selectedTemplateId'] = $template->uuid;
        $state['designSurface'] = $targetSurface ?? ($state['designSurface'] ?? null);
        $state['objective'] = $data['objective'] ?? ($state['objective'] ?? null);
        $state['outputType'] = $data['outputType'] ?? ($state['outputType'] ?? null);
        $state['format'] = $data['format'] ?? ($state['format'] ?? null);
        $state['size'] = $data['size'] ?? ($state['size'] ?? null);

        $name = trim((string) ($data['designTitle'] ?? ''));
        if ($name === '' || Str::lower($name) === 'diseño sin título' || Str::lower($name) === 'diseno sin titulo') {
            $name = sprintf('%s personalizado', $template->title);
        }
        $state['designTitle'] = $name;
        $state['designTitleManual'] = false;

        $attributes = [
            'name' => $name,
            'name_manual' => false,
            'objective' => $state['objective'] ?? null,
            'output_type' => $state['outputType'] ?? null,
            'format' => $state['format'] ?? null,
            'size_label' => $state['size'] ?? null,
            'surface_width' => $targetSurface['width'] ?? null,
            'surface_height' => $targetSurface['height'] ?? null,
            'template_category' => $state['templateCategory'] ?? null,
            'selected_template_id' => $template->uuid,
            'state' => $state,
            'status' => 'draft',
            'last_opened_at' => now(),
            'public' => false,
        ];

        if ($targetDesign) {
            $targetDesign->forceFill($attributes)->save();

            return $targetDesign;
        }

        return $user->designs()->create([
            'uuid' => $uuid,
            ...$attributes,
        ]);
    }

    /**
     * @param  array<string, mixed>  $state
     * @param  array<string, mixed>  $baseSurface
     * @param  array<string, mixed>  $targetSurface
     * @return array<string, mixed>
     */
    public function adaptStateToSurface(array $state, array $baseSurface, array $targetSurface): array
    {
        $baseWidth = (float) ($baseSurface['width'] ?? 0);
        $baseHeight = (float) ($baseSurface['height'] ?? 0);
        $targetWidth = (float) ($targetSurface['width'] ?? 0);
        $targetHeight = (float) ($targetSurface['height'] ?? 0);

        if ($baseWidth <= 0 || $baseHeight <= 0 || $targetWidth <= 0 || $targetHeight <= 0) {
            $state['designSurface'] = $targetSurface;

            return $state;
        }

        $scaleX = $targetWidth / $baseWidth;
        $scaleY = $targetHeight / $baseHeight;
        $uniformScale = min($scaleX, $scaleY);
        $fontScale = $this->clamp($uniformScale, 0.85, 1.15);

        foreach (($state['elementLayout'] ?? []) as $id => $layout) {
            if (! is_array($layout) || $id === 'background') {
                continue;
            }

            $type = $this->elementType($state, (string) $id);
            $oldWidth = (float) ($layout['w'] ?? ($type === 'text' ? 180 : 140));
            $oldHeight = (float) ($layout['h'] ?? ($type === 'text' ? max(40, ((float) ($layout['fontSize'] ?? 18)) * 1.4) : 140));

            if ($this->isBackgroundLike($layout, $baseWidth, $baseHeight)) {
                $layout['x'] = 0;
                $layout['y'] = 0;
                $layout['w'] = $targetWidth;
                $layout['h'] = $targetHeight;
                $state['elementLayout'][$id] = $layout;
                continue;
            }

            if ($type === 'text') {
                $newWidth = max(40, $oldWidth * $scaleX);
                $newHeight = $oldHeight;
            } else {
                $newWidth = max(8, $oldWidth * $uniformScale);
                $newHeight = max(8, $oldHeight * $uniformScale);
            }

            [$newX, $newY] = $this->repositionFromCenter(
                (float) ($layout['x'] ?? 0),
                (float) ($layout['y'] ?? 0),
                $oldWidth,
                $oldHeight,
                $newWidth,
                $newHeight,
                $baseWidth,
                $baseHeight,
                $targetWidth,
                $targetHeight,
                $type === 'text' ? 0.12 : 0.3,
            );

            $layout['x'] = $newX;
            $layout['y'] = $newY;
            $layout['w'] = $newWidth;
            if ($type !== 'text' || array_key_exists('h', $layout)) {
                $layout['h'] = $newHeight;
            }

            $this->scaleNumericField($layout, 'fontSize', $fontScale, 8);
            $this->scaleNumericField($layout, 'shadowOffset', $uniformScale);
            $this->scaleNumericField($layout, 'shadowBlur', $uniformScale);
            $this->scaleNumericField($layout, 'contourWidth', $uniformScale);
            $this->scaleNumericField($layout, 'misalignedThickness', $uniformScale);
            $this->scaleNumericField($layout, 'backgroundPadding', $uniformScale);
            $this->scaleNumericField($layout, 'letterSpacing', $uniformScale);

            if (isset($layout['paragraphStyles']) && is_array($layout['paragraphStyles'])) {
                $layout['paragraphStyles'] = array_map(function ($style) use ($fontScale, $uniformScale) {
                    if (! is_array($style)) {
                        return $style;
                    }
                    $this->scaleNumericField($style, 'fontSize', $fontScale, 8);
                    $this->scaleNumericField($style, 'letterSpacing', $uniformScale);

                    return $style;
                }, $layout['paragraphStyles']);
            }

            $state['elementLayout'][$id] = $layout;
        }

        $state['designSurface'] = $targetSurface;

        return $state;
    }

    /**
     * @param  array<string, mixed>  $state
     * @param  array<string, mixed>  $data
     * @param  array<int, array<string, mixed>>  $fieldMappings
     * @return array<string, mixed>
     */
    public function applyData(array $state, array $data, array $fieldMappings): array
    {
        $content = is_array($state['content'] ?? null) ? $state['content'] : [];
        $incomingContent = is_array($data['content'] ?? null) ? $data['content'] : [];

        foreach ($incomingContent as $field => $value) {
            if (is_scalar($value) || $value === null) {
                $content[$field] = $value === null ? '' : (string) $value;
            }
        }

        $state['content'] = $content;

        foreach ($fieldMappings as $mapping) {
            if (! is_array($mapping)) {
                continue;
            }

            $sourceField = (string) ($mapping['sourceField'] ?? $mapping['fieldName'] ?? '');
            if ($sourceField === '') {
                continue;
            }

            $value = $incomingContent[$sourceField] ?? $data[$sourceField] ?? $state['content'][$sourceField] ?? null;
            if ($value === null && array_key_exists('fallback', $mapping)) {
                $value = $mapping['fallback'];
            }
            if ($value === null) {
                continue;
            }
            $value = is_scalar($value) ? (string) $value : '';

            $targetField = (string) ($mapping['targetField'] ?? '');
            if ($targetField !== '') {
                $state['content'][$targetField] = $value;
            }

            $elementId = (string) ($mapping['elementId'] ?? '');
            if ($elementId !== '') {
                $state = $this->applyValueToElement($state, $elementId, (string) ($mapping['property'] ?? 'text'), $value);
            }
        }

        $state = $this->applyContentToMatchingElements($state, $state['content'] ?? $incomingContent);

        return $state;
    }

    /**
     * @param  array<string, mixed>  $state
     * @param  array<string, mixed>  $incomingContent
     * @return array<string, mixed>
     */
    private function applyContentToMatchingElements(array $state, array $incomingContent): array
    {
        foreach ($incomingContent as $field => $value) {
            if ($value === null || (! is_scalar($value))) {
                continue;
            }

            $value = (string) $value;
            if ($value === '') {
                continue;
            }

            $normalizedField = $this->normalizeFieldName((string) $field);
            $aliases = $this->aliasesForField((string) $field);

            if (in_array($normalizedField, ['title', 'subtitle', 'contact', 'extra'], true)) {
                $state['content'][$normalizedField] = $value;
            }

            if (in_array($normalizedField, ['date', 'time'], true)) {
                $state['content'][$normalizedField] = $value;
            }

            foreach (($state['customElements'] ?? []) as $elementId => $element) {
                if (! is_array($element)) {
                    continue;
                }

                $elementField = $this->resolveElementField((string) $elementId, $element);
                if (! $this->fieldMatches($elementField, $aliases)) {
                    continue;
                }

                if (($element['type'] ?? null) === 'text') {
                    $state['customElements'][$elementId]['text'] = $value;
                } elseif (($element['type'] ?? null) === 'image' && $this->looksLikeImageField((string) $field)) {
                    $state['customElements'][$elementId]['src'] = $value;
                }
            }
        }

        $state = $this->deriveCommonCompositeFields($state);

        return $state;
    }

    /**
     * @param  array<string, mixed>  $state
     * @return array<string, mixed>
     */
    private function deriveCommonCompositeFields(array $state): array
    {
        $content = $state['content'] ?? [];

        foreach (($state['customElements'] ?? []) as $elementId => $element) {
            if (! is_array($element) || ($element['type'] ?? null) !== 'text') {
                continue;
            }

            $elementField = $this->resolveElementField((string) $elementId, $element);
            if ($this->fieldMatches($elementField, ['meta', 'fecha-hora', 'fecha-y-hora', 'date-time'])) {
                $state['customElements'][$elementId]['text'] = implode(' · ', array_filter([
                    $content['date'] ?? '',
                    $content['time'] ?? '',
                ]));
            }

            if ($this->fieldMatches($elementField, ['venue', 'lugar-contacto', 'ubicacion-contacto'])) {
                $state['customElements'][$elementId]['text'] = trim((string) (($content['location'] ?? '') ?: ($content['platform'] ?? '') ?: ($content['contact'] ?? '')));
            }
        }

        return $state;
    }

    /**
     * @param  array<string, mixed>  $element
     */
    private function resolveElementField(string $elementId, array $element): string
    {
        $candidates = [
            $element['dataField'] ?? null,
            $element['fieldName'] ?? null,
            $element['contentField'] ?? null,
            $element['label'] ?? null,
            $element['name'] ?? null,
            $elementId,
        ];

        return implode(' ', array_map(
            fn ($candidate) => $this->normalizeFieldName((string) $candidate),
            array_filter($candidates, fn ($candidate) => is_scalar($candidate) && (string) $candidate !== ''),
        ));
    }

    /**
     * @return array<int, string>
     */
    private function aliasesForField(string $field): array
    {
        $normalized = $this->normalizeFieldName($field);
        $aliases = self::FIELD_ALIASES[$field] ?? self::FIELD_ALIASES[$normalized] ?? [];

        return array_values(array_unique([
            $normalized,
            ...array_map(fn ($alias) => $this->normalizeFieldName($alias), $aliases),
        ]));
    }

    /**
     * @param  array<int, string>  $aliases
     */
    private function fieldMatches(string $elementField, array $aliases): bool
    {
        $normalizedElementField = $this->normalizeFieldName($elementField);

        foreach ($aliases as $alias) {
            $normalizedAlias = $this->normalizeFieldName($alias);
            if ($normalizedAlias !== '' && (
                $normalizedElementField === $normalizedAlias
                || str_contains($normalizedElementField, $normalizedAlias)
                || str_contains($normalizedAlias, $normalizedElementField)
            )) {
                return true;
            }
        }

        return false;
    }

    private function normalizeFieldName(string $value): string
    {
        $value = Str::of($value)
            ->lower()
            ->ascii()
            ->replaceMatches('/[^a-z0-9]+/', ' ')
            ->squish()
            ->replace(' ', '-')
            ->toString();

        return $value;
    }

    private function looksLikeImageField(string $field): bool
    {
        return in_array($this->normalizeFieldName($field), ['image', 'imagen', 'main-image', 'mainimage', 'hero-image', 'imagen-principal'], true);
    }

    /**
     * @param  array<string, mixed>  $state
     * @return array<string, mixed>
     */
    private function applyValueToElement(array $state, string $elementId, string $property, string $value): array
    {
        if ($property === 'src') {
            if ($elementId === 'background') {
                $state['elementLayout']['background']['backgroundImageSrc'] = $value;
            } elseif (($state['customElements'][$elementId]['type'] ?? null) === 'image') {
                $state['customElements'][$elementId]['src'] = $value;
            }

            return $state;
        }

        if (in_array($elementId, ['title', 'subtitle', 'contact', 'extra'], true)) {
            $state['content'][$elementId] = $value;
        } elseif ($elementId === 'meta') {
            $parts = preg_split('/\s*[·|]\s*/u', $value, 2);
            $state['content']['date'] = trim((string) ($parts[0] ?? $value));
            if (isset($parts[1])) {
                $state['content']['time'] = trim((string) $parts[1]);
            }
        } elseif (($state['customElements'][$elementId]['type'] ?? null) === 'text') {
            $state['customElements'][$elementId]['text'] = $value;
        }

        return $state;
    }

    /**
     * @return array<string, float>
     */
    public function surfaceFromState(array $state, Design $design): array
    {
        return $this->normalizeSurface($state['designSurface'] ?? null)
            ?? $this->surfaceFromDesign($design);
    }

    /**
     * @return array<string, float>
     */
    public function surfaceFromDesign(Design $design): array
    {
        return [
            'width' => (float) ($design->surface_width ?: 500),
            'height' => (float) ($design->surface_height ?: 500),
        ];
    }

    /**
     * @param  mixed  $surface
     * @return array<string, float>|null
     */
    public function normalizeSurface(mixed $surface): ?array
    {
        if (! is_array($surface)) {
            return null;
        }

        $width = (float) ($surface['width'] ?? 0);
        $height = (float) ($surface['height'] ?? 0);

        if ($width <= 0 || $height <= 0) {
            return null;
        }

        return [
            'width' => $width,
            'height' => $height,
        ];
    }

    /**
     * @return array{0: float, 1: float}
     */
    private function repositionFromCenter(
        float $x,
        float $y,
        float $oldWidth,
        float $oldHeight,
        float $newWidth,
        float $newHeight,
        float $baseWidth,
        float $baseHeight,
        float $targetWidth,
        float $targetHeight,
        float $overflowRatio,
    ): array {
        $scaleX = $targetWidth / $baseWidth;
        $scaleY = $targetHeight / $baseHeight;
        $baseCenterX = $baseWidth / 2;
        $baseCenterY = $baseHeight / 2;
        $targetCenterX = $targetWidth / 2;
        $targetCenterY = $targetHeight / 2;
        $elementCenterX = $x + ($oldWidth / 2);
        $elementCenterY = $y + ($oldHeight / 2);
        $newCenterX = $targetCenterX + (($elementCenterX - $baseCenterX) * $scaleX);
        $newCenterY = $targetCenterY + (($elementCenterY - $baseCenterY) * $scaleY);
        $newX = $newCenterX - ($newWidth / 2);
        $newY = $newCenterY - ($newHeight / 2);

        return [
            round($this->clamp($newX, -$newWidth * $overflowRatio, $targetWidth - ($newWidth * (1 - $overflowRatio))), 2),
            round($this->clamp($newY, -$newHeight * $overflowRatio, $targetHeight - ($newHeight * (1 - $overflowRatio))), 2),
        ];
    }

    /**
     * @param  array<string, mixed>  $layout
     */
    private function isBackgroundLike(array $layout, float $baseWidth, float $baseHeight): bool
    {
        $width = (float) ($layout['w'] ?? 0);
        $height = (float) ($layout['h'] ?? 0);

        return $width >= $baseWidth * 0.9 && $height >= $baseHeight * 0.9;
    }

    /**
     * @param  array<string, mixed>  $state
     */
    private function elementType(array $state, string $id): string
    {
        if (in_array($id, self::BASE_TEXT_ELEMENT_IDS, true)) {
            return 'text';
        }

        return (string) ($state['customElements'][$id]['type'] ?? 'shape');
    }

    /**
     * @param  array<string, mixed>  $layout
     */
    private function scaleNumericField(array &$layout, string $field, float $factor, float $minimum = 0): void
    {
        if (! is_numeric($layout[$field] ?? null)) {
            return;
        }

        $layout[$field] = max($minimum, ((float) $layout[$field]) * $factor);
    }

    private function clamp(float $value, float $min, float $max): float
    {
        return min(max($value, $min), $max);
    }
}
