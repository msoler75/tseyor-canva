<?php

namespace App\Services;

use App\Models\Design;
use App\Models\DesignTemplate;
use App\Models\User;
use Illuminate\Support\Facades\Storage;

class DemoTemplateFactory
{
    /**
     * @return array{user: User, designs: array<int, Design>, templates: array<int, DesignTemplate>}
     */
    public function create(string $adminEmail = 'admin@example.com', string $adminName = 'admin', string $password = 'password', string $status = 'published'): array
    {
        $status = in_array($status, ['draft', 'published', 'archived'], true) ? $status : 'published';
        $admin = User::query()->firstOrCreate(
            ['email' => $adminEmail],
            [
                'name' => $adminName,
                'password' => $password,
            ],
        );

        if ($admin->name !== $adminName) {
            $admin->forceFill(['name' => $adminName])->save();
        }

        $designs = [];
        $templates = [];

        foreach ($this->templateDefinitions() as $index => $definition) {
            $state = $this->buildDesignerState($definition);
            $design = Design::query()->updateOrCreate(
                ['uuid' => $definition['design_uuid']],
                [
                    'user_id' => $admin->id,
                    'name' => $definition['title'],
                    'name_manual' => true,
                    'objective' => 'generic',
                    'output_type' => 'digital',
                    'format' => 'vertical',
                    'size_label' => 'Historia / vertical 1080x1350',
                    'surface_width' => 1080,
                    'surface_height' => 1350,
                    'template_category' => 'generic',
                    'selected_template_id' => null,
                    'thumbnail_path' => null,
                    'state' => $state,
                    'status' => 'published',
                    'public' => false,
                    'last_opened_at' => now()->subMinutes(3 - $index),
                ],
            );

            $thumbnailPath = $this->storeThumbnailSvg($design->uuid, $definition);
            $design->forceFill(['thumbnail_path' => $thumbnailPath])->save();

            $template = DesignTemplate::query()->updateOrCreate(
                ['uuid' => $definition['template_uuid']],
                [
                    'base_design_id' => $design->id,
                    'title' => $definition['title'],
                    'description' => $definition['description'],
                    'category_ids' => $definition['category_ids'],
                    'objective_ids' => $definition['objective_ids'],
                    'adaptation_mode' => 'proportional',
                    'field_mappings' => $this->fieldMappings($definition),
                    'status' => $status,
                    'featured' => $index === 0,
                    'sort_order' => $index + 1,
                    'published_at' => $status === 'published' ? now() : null,
                ],
            );

            $designs[] = $design->fresh('baseTemplate');
            $templates[] = $template->fresh('baseDesign');
        }

        return [
            'user' => $admin->fresh(),
            'designs' => $designs,
            'templates' => $templates,
        ];
    }

    /**
     * @return array<int, array<string, mixed>>
     */
    public function templateDefinitions(): array
    {
        return [
            [
                'design_uuid' => '41c7d729-9f20-4d3f-9b57-000000000001',
                'template_uuid' => '51c7d729-9f20-4d3f-9b57-000000000001',
                'title' => 'Plantilla genérica clara',
                'description' => 'Base limpia para anuncios, avisos y piezas de prueba.',
                'category_ids' => ['generic', 'minimal'],
                'objective_ids' => ['generic', 'event_presential', 'event_virtual', 'course'],
                'palette' => ['bg' => '#eff6ff', 'panel' => '#ffffff', 'accent' => '#2563eb', 'accent2' => '#38bdf8', 'text' => '#0f172a'],
            ],
            [
                'design_uuid' => '41c7d729-9f20-4d3f-9b57-000000000002',
                'template_uuid' => '51c7d729-9f20-4d3f-9b57-000000000002',
                'title' => 'Plantilla genérica cálida',
                'description' => 'Base promocional con acentos cálidos para probar variaciones.',
                'category_ids' => ['generic', 'promo'],
                'objective_ids' => ['generic', 'event_presential', 'shop'],
                'palette' => ['bg' => '#fff7ed', 'panel' => '#ffedd5', 'accent' => '#ea580c', 'accent2' => '#fbbf24', 'text' => '#431407'],
            ],
            [
                'design_uuid' => '41c7d729-9f20-4d3f-9b57-000000000003',
                'template_uuid' => '51c7d729-9f20-4d3f-9b57-000000000003',
                'title' => 'Plantilla genérica sobria',
                'description' => 'Base institucional neutra para comunicaciones formales.',
                'category_ids' => ['generic', 'corporate'],
                'objective_ids' => ['generic', 'course', 'event_virtual'],
                'palette' => ['bg' => '#f8fafc', 'panel' => '#e2e8f0', 'accent' => '#0f172a', 'accent2' => '#64748b', 'text' => '#0f172a'],
            ],
        ];
    }

    /**
     * @param  array<string, mixed>  $definition
     * @return array<string, mixed>
     */
    private function buildDesignerState(array $definition): array
    {
        $palette = $definition['palette'];

        return [
            'darkMode' => false,
            'mode' => 'guided',
            'objective' => 'generic',
            'outputType' => 'digital',
            'format' => 'vertical',
            'size' => 'Historia / vertical 1080x1350',
            'templateCategory' => 'generic',
            'selectedTemplateId' => null,
            'autosaveMessage' => 'Guardado automático',
            'selectedElementId' => 'title',
            'designTitle' => $definition['title'],
            'designTitleManual' => true,
            'currentDesignUuid' => $definition['design_uuid'],
            'designSurface' => ['width' => 1080, 'height' => 1350],
            'content' => [
                'title' => 'Título de prueba',
                'subtitle' => 'Subtítulo o descripción breve para validar la plantilla.',
                'date' => '01/01/2026',
                'time' => '18:00',
                'location' => 'Lugar o plataforma',
                'platform' => 'https://ejemplo.test',
                'teacher' => 'Facilitador/a',
                'price' => 'Entrada libre',
                'contact' => 'contacto@example.org',
                'extra' => 'Texto adicional editable para pruebas.',
            ],
            'elementLayout' => [
                'background' => $this->backgroundLayout($palette['bg']),
                'title' => $this->textLayout(108, 176, 760, 78, $palette['text'], 'bold', 40, true),
                'subtitle' => $this->textLayout(108, 344, 700, 36, $palette['text'], 'regular', 30),
                'meta' => $this->textLayout(108, 1110, 420, 30, $palette['accent'], 'bold', 20),
                'contact' => $this->textLayout(108, 1180, 520, 28, $palette['text'], 'regular', 10),
                'extra' => $this->textLayout(108, 980, 640, 28, $palette['text'], 'regular', 15),
                'decor-panel' => [
                    'x' => 76,
                    'y' => 104,
                    'w' => 928,
                    'h' => 1040,
                    'zIndex' => 1,
                    'backgroundColor' => $palette['panel'],
                    'opacity' => 82,
                    'borderRadius' => 44,
                    'border' => false,
                    'imageCropScale' => 1,
                    'imageCropOffsetX' => 0,
                    'imageCropOffsetY' => 0,
                    'flipX' => false,
                    'flipY' => false,
                ],
                'decor-accent' => [
                    'x' => 730,
                    'y' => 760,
                    'w' => 210,
                    'h' => 210,
                    'zIndex' => 2,
                    'backgroundColor' => $palette['accent2'],
                    'opacity' => 55,
                    'borderRadius' => 999,
                    'border' => false,
                    'imageCropScale' => 1,
                    'imageCropOffsetX' => 0,
                    'imageCropOffsetY' => 0,
                    'flipX' => false,
                    'flipY' => false,
                ],
                'cta-box' => [
                    'x' => 108,
                    'y' => 820,
                    'w' => 360,
                    'h' => 96,
                    'zIndex' => 8,
                    'backgroundColor' => $palette['accent'],
                    'opacity' => 100,
                    'borderRadius' => 28,
                    'border' => false,
                    'imageCropScale' => 1,
                    'imageCropOffsetX' => 0,
                    'imageCropOffsetY' => 0,
                    'flipX' => false,
                    'flipY' => false,
                ],
            ],
            'customElements' => [
                'decor-panel' => ['id' => 'decor-panel', 'type' => 'shape', 'label' => 'Panel decorativo', 'shapeKind' => 'rectangle'],
                'decor-accent' => ['id' => 'decor-accent', 'type' => 'shape', 'label' => 'Acento circular', 'shapeKind' => 'circle'],
                'cta-box' => ['id' => 'cta-box', 'type' => 'shape', 'label' => 'Botón decorativo', 'shapeKind' => 'rectangle'],
            ],
            'userUploadedImages' => [],
        ];
    }

    /**
     * @return array<string, mixed>
     */
    private function backgroundLayout(string $color): array
    {
        return [
            'backgroundColor' => $color,
            'backgroundImageSrc' => null,
            'backgroundImageAssetId' => null,
            'backgroundImagePendingDataUrl' => null,
            'backgroundImageStoragePath' => null,
            'backgroundImageWidth' => null,
            'backgroundImageHeight' => null,
            'backgroundImageCropScale' => 1,
            'backgroundImageCropOffsetX' => 0,
            'backgroundImageCropOffsetY' => 0,
            'backgroundImageFlipX' => false,
            'backgroundImageFlipY' => false,
            'backgroundImageOpacity' => 100,
            'backgroundImageTransparencyType' => 'flat',
            'backgroundImageTransparencyFadeOpacity' => 0,
            'backgroundImageTransparencyCenterX' => 50,
            'backgroundImageTransparencyCenterY' => 50,
            'backgroundImageTransparencyRadius' => 70,
            'backgroundImageTransparencyRadiusX' => 70,
            'backgroundImageTransparencyRadiusY' => 45,
            'backgroundImageTransparencyRotation' => 0,
            'backgroundImageTransparencyStartX' => 0,
            'backgroundImageTransparencyStartY' => 50,
            'backgroundImageTransparencyEndX' => 100,
            'backgroundImageTransparencyEndY' => 50,
            'backgroundImageTransparencyEasing' => 'linear',
        ];
    }

    /**
     * @return array<string, mixed>
     */
    private function textLayout(int $x, int $y, int $width, int $fontSize, string $color, string $weight, int $zIndex, bool $shadow = false): array
    {
        return [
            'x' => $x,
            'y' => $y,
            'w' => $width,
            'zIndex' => $zIndex,
            'fontSize' => $fontSize,
            'color' => $color,
            'shadow' => $shadow,
            'border' => false,
            'fontFamily' => 'Poppins, sans-serif',
            'opacity' => 100,
            'fontWeight' => $weight,
            'italic' => false,
            'uppercase' => false,
            'textAlign' => 'left',
            'letterSpacing' => 0,
            'lineHeight' => 1.1,
            'shadowPreset' => 'soft',
            'shadowColor' => '#0f172a',
            'contourWidth' => 0,
            'contourColor' => '#ffffff',
            'neonColor' => '',
            'bubbleColor' => '',
            'backgroundColor' => 'transparent',
            'imageCropScale' => 1,
            'imageCropOffsetX' => 0,
            'imageCropOffsetY' => 0,
            'flipX' => false,
            'flipY' => false,
            'paragraphStyles' => [[
                'fontSize' => $fontSize,
                'color' => $color,
                'fontFamily' => 'Poppins, sans-serif',
                'fontWeight' => $weight,
                'italic' => false,
                'uppercase' => false,
                'textAlign' => 'left',
                'letterSpacing' => 0,
                'lineHeight' => 1.1,
            ]],
        ];
    }

    /**
     * @param  array<string, mixed>  $definition
     * @return array<int, array<string, string>>
     */
    private function fieldMappings(array $definition): array
    {
        return [
            ['sourceField' => 'title', 'targetField' => 'title', 'elementId' => 'title', 'property' => 'text', 'label' => 'Título', 'fallback' => $definition['title']],
            ['sourceField' => 'subtitle', 'targetField' => 'subtitle', 'elementId' => 'subtitle', 'property' => 'text', 'label' => 'Subtítulo', 'fallback' => $definition['description']],
            ['sourceField' => 'date', 'targetField' => 'date', 'elementId' => '', 'property' => 'text', 'label' => 'Fecha'],
            ['sourceField' => 'time', 'targetField' => 'time', 'elementId' => '', 'property' => 'text', 'label' => 'Hora'],
            ['sourceField' => 'contact', 'targetField' => 'contact', 'elementId' => 'contact', 'property' => 'text', 'label' => 'Contacto'],
            ['sourceField' => 'extra', 'targetField' => 'extra', 'elementId' => 'extra', 'property' => 'text', 'label' => 'Texto adicional'],
        ];
    }

    /**
     * @param  array<string, mixed>  $definition
     */
    private function storeThumbnailSvg(string $designUuid, array $definition): string
    {
        $palette = $definition['palette'];
        $title = $this->escapeSvgText($definition['title']);
        $description = $this->escapeSvgText($definition['description']);
        $path = sprintf('%s.svg', $designUuid);
        $svg = <<<SVG
<svg width="1200" height="675" viewBox="0 0 1200 675" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">{$title}</title>
  <desc id="desc">{$description}</desc>
  <rect width="1200" height="675" rx="40" fill="{$palette['bg']}"/>
  <circle cx="1025" cy="135" r="120" fill="{$palette['accent2']}" fill-opacity="0.58"/>
  <circle cx="160" cy="560" r="155" fill="{$palette['accent']}" fill-opacity="0.16"/>
  <rect x="82" y="68" width="1036" height="540" rx="38" fill="{$palette['panel']}" fill-opacity="0.92"/>
  <rect x="82" y="68" width="1036" height="18" rx="9" fill="{$palette['accent']}"/>
  <text x="126" y="222" fill="{$palette['text']}" font-size="58" font-family="Arial, Helvetica, sans-serif" font-weight="700">{$title}</text>
  <text x="126" y="294" fill="{$palette['text']}" fill-opacity="0.72" font-size="28" font-family="Arial, Helvetica, sans-serif">{$description}</text>
  <rect x="126" y="368" width="370" height="112" rx="28" fill="{$palette['accent']}" fill-opacity="0.14"/>
  <text x="158" y="418" fill="{$palette['text']}" font-size="24" font-family="Arial, Helvetica, sans-serif" font-weight="700">Plantilla de prueba</text>
  <text x="158" y="456" fill="{$palette['text']}" fill-opacity="0.68" font-size="18" font-family="Arial, Helvetica, sans-serif">Base genérica editable</text>
  <rect x="610" y="150" width="400" height="380" rx="34" fill="{$palette['accent2']}" fill-opacity="0.20"/>
  <rect x="660" y="210" width="300" height="34" rx="17" fill="{$palette['accent']}" fill-opacity="0.38"/>
  <rect x="660" y="282" width="250" height="22" rx="11" fill="{$palette['text']}" fill-opacity="0.18"/>
  <rect x="660" y="326" width="280" height="22" rx="11" fill="{$palette['text']}" fill-opacity="0.18"/>
  <rect x="660" y="404" width="206" height="62" rx="20" fill="{$palette['accent']}"/>
  <text x="700" y="444" fill="white" font-size="22" font-family="Arial, Helvetica, sans-serif" font-weight="700">Usar</text>
</svg>
SVG;

        Storage::disk('thumbnails')->put($path, $svg);

        return $path;
    }

    private function escapeSvgText(mixed $value): string
    {
        return htmlspecialchars((string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    }
}
