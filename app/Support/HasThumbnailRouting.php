<?php

namespace App\Support;

use App\Models\DesignTemplate;

trait HasThumbnailRouting
{
    private function versionedThumbnailRoute(string $path, mixed $version = null): string
    {
        return route('designer.thumbnails.show', [
            'path' => $path,
            'v' => $this->resolveAssetVersion($path, $version),
        ]);
    }

    private function versionedUploadRoute(string $path, mixed $version = null): string
    {
        return route('designer.uploads.show', [
            'path' => $path,
            'v' => $this->resolveAssetVersion($path, $version),
        ]);
    }

    private function resolveAssetVersion(string $path, mixed $version = null): string
    {
        $normalizedVersion = is_scalar($version) ? trim((string) $version) : '';

        if ($normalizedVersion !== '') {
            return $normalizedVersion;
        }

        return sha1($path);
    }

    /**
     * @return array<string, mixed>
     */
    private function serializeTemplate(DesignTemplate $template): array
    {
        $template->loadMissing('baseDesign:id,uuid,thumbnail_path,updated_at');

        return [
            'id' => $template->uuid,
            'uuid' => $template->uuid,
            'title' => $template->title,
            'name' => $template->title,
            'description' => $template->description,
            'category_ids' => $template->category_ids ?? [],
            'objective_ids' => $template->objective_ids ?? [],
            'category' => ($template->category_ids ?? ['all'])[0] ?? 'all',
            'adaptation_mode' => $template->adaptation_mode,
            'field_mappings' => $template->field_mappings ?? [],
            'status' => $template->status,
            'featured' => $template->featured,
            'sort_order' => $template->sort_order,
            'base_design_uuid' => $template->baseDesign?->uuid,
            'base_pages_count' => $template->baseDesign?->pages_count ?? 1,
            'thumbnail_url' => $template->baseDesign?->thumbnail_path
                ? $this->versionedThumbnailRoute(
                    $template->baseDesign->thumbnail_path,
                    optional($template->baseDesign->updated_at)->timestamp,
                )
                : null,
        ];
    }
}
