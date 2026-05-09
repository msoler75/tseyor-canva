<?php

namespace App\Http\Controllers;

use App\Models\DesignAsset;
use App\Models\User;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

class DesignAssetController extends Controller
{
    public function index(Request $request): JsonResponse
    {
        /** @var User $user */
        $user = $request->user();

        return response()->json([
            'assets' => $user->designAssets()
                ->latest('created_at')
                ->paginate(20)
                ->through(fn (DesignAsset $asset): array => [
                    'id' => $asset->id,
                    'uuid' => $asset->uuid,
                    'label' => $asset->label,
                    'disk' => $asset->disk,
                    'path' => $asset->path,
                    'mime_type' => $asset->mime_type,
                    'extension' => $asset->extension,
                    'size_bytes' => $asset->size_bytes,
                    'width' => $asset->width,
                    'height' => $asset->height,
                    'uploaded_at' => $asset->uploaded_at,
                    'last_used_at' => $asset->last_used_at,
                    'url' => $this->versionedUploadRoute($asset->path, $asset->updated_at?->timestamp),
                ]),
        ]);
    }

    public function store(Request $request): JsonResponse
    {
        /** @var User $user */
        $user = $request->user();

        $validated = $request->validate([
            'file' => ['required', 'file', 'image', 'max:20480'],
            'label' => ['nullable', 'string', 'max:255'],
        ]);

        $file = $validated['file'];
        $extension = $file->guessExtension() ?: $file->extension() ?: 'bin';
        $uuid = (string) Str::uuid();
        $filename = "{$uuid}.{$extension}";
        $userFolder = $user->id;
        $path = $file->storeAs($userFolder, $filename, 'users');

        $asset = $user->designAssets()->create([
            'uuid' => $uuid,
            'label' => $validated['label'] ?? $file->getClientOriginalName(),
            'disk' => 'users',
            'path' => $path,
            'mime_type' => File::mimeType(Storage::disk('users')->path($path)) ?: $file->getMimeType(),
            'extension' => $extension,
            'size_bytes' => $file->getSize() ?: 0,
            'uploaded_at' => now(),
        ]);

        return response()->json([
            'asset' => $asset,
            'url' => $this->versionedUploadRoute($path, $asset->updated_at?->timestamp),
        ], 201);
    }

    private function versionedUploadRoute(string $path, mixed $version = null): string
    {
        $normalizedVersion = is_scalar($version) ? trim((string) $version) : '';

        return route('designer.uploads.show', [
            'path' => $path,
            'v' => $normalizedVersion !== '' ? $normalizedVersion : sha1($path),
        ]);
    }
}
