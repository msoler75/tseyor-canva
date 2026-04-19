<?php

namespace App\Http\Controllers;

use App\Models\Design;
use App\Models\User;
use App\Support\DesignerStateRules;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Str;

class DesignController extends Controller
{
    public function index(Request $request): JsonResponse
    {
        /** @var User $user */
        $user = $request->user();

        $designs = $user->designs()
            ->whereDoesntHave('baseTemplate')
            ->latest('updated_at')
            ->get([
                'id',
                'uuid',
                'name',
                'name_manual',
                'objective',
                'output_type',
                'format',
                'size_label',
                'surface_width',
                'surface_height',
                'template_category',
                'selected_template_id',
                'thumbnail_path',
                'status',
                'last_opened_at',
                'created_at',
                'updated_at',
            ]);

        return response()->json([
            'designs' => $designs,
        ]);
    }

    public function store(Request $request): JsonResponse
    {
        /** @var User $user */
        $user = $request->user();

        $validated = $request->validate([
            ...DesignerStateRules::rules(),
            'name' => ['nullable', 'string', 'max:255'],
            'thumbnail_path' => ['nullable', 'string', 'max:1024'],
            'status' => ['nullable', 'string', 'max:32'],
            'public' => ['nullable', 'boolean'],
        ]);

        $state = $validated['state'];
        $requestedUuid = (string) ($state['currentDesignUuid'] ?? '');
        $uuid = Str::isUuid($requestedUuid) ? $requestedUuid : (string) Str::uuid();
        $state['currentDesignUuid'] = $uuid;

        $existingDesign = Design::query()->where('uuid', $uuid)->first();
        abort_if($existingDesign && ! $existingDesign->user?->is($user), 409);

        $attributes = [
            ...$this->extractDesignMetadata($state),
            'name' => $validated['name'] ?? $this->resolveDesignName($state),
            'thumbnail_path' => $validated['thumbnail_path'] ?? null,
            'state' => $state,
            'status' => $validated['status'] ?? 'draft',
            'last_opened_at' => now(),
            'public' => $validated['public'] ?? ($state['public'] ?? false),
        ];

        $status = 201;
        if ($existingDesign) {
            $existingDesign->fill($attributes)->save();
            $design = $existingDesign;
            $status = 200;
        } else {
            $design = $user->designs()->create([
                ...$attributes,
                'uuid' => $uuid,
            ]);
        }

        return response()->json([
            'design' => $design->fresh(),
        ], $status);
    }

    public function show(Request $request, Design $design): JsonResponse
    {
        $this->authorizeOwnership($request, $design);

        $design->forceFill([
            'last_opened_at' => now(),
        ])->save();

        return response()->json([
            'design' => $design->fresh(),
        ]);
    }

    public function update(Request $request, Design $design): JsonResponse
    {
        $this->authorizeOwnership($request, $design);

        $validated = $request->validate([
            ...DesignerStateRules::rules(),
            'name' => ['nullable', 'string', 'max:255'],
            'thumbnail_path' => ['nullable', 'string', 'max:1024'],
            'status' => ['nullable', 'string', 'max:32'],
            'public' => ['nullable', 'boolean'],
        ]);

        $state = $validated['state'];

        $design->fill([
            ...$this->extractDesignMetadata($state),
            'name' => $validated['name'] ?? $this->resolveDesignName($state),
            'thumbnail_path' => $validated['thumbnail_path'] ?? $design->thumbnail_path,
            'state' => $state,
            'status' => $validated['status'] ?? $design->status,
            'last_opened_at' => now(),
            'public' => $validated['public'] ?? ($state['public'] ?? $design->public),
        ])->save();

        return response()->json([
            'design' => $design->fresh(),
        ]);
    }

    public function duplicate(Request $request, Design $design): JsonResponse
    {
        $this->authorizeOwnership($request, $design);

        $clone = $design->replicate([
            'uuid',
            'name',
            'last_opened_at',
            'created_at',
            'updated_at',
        ]);

        $clone->uuid = (string) Str::uuid();
        $clone->name = sprintf('Copia de %s', $design->name);
        $clone->last_opened_at = now();
        $clone->save();

        return response()->json([
            'design' => $clone->fresh(),
        ], 201);
    }

    public function rename(Request $request, Design $design): JsonResponse
    {
        $this->authorizeOwnership($request, $design);

        $validated = $request->validate([
            'name' => ['required', 'string', 'max:255'],
        ]);

        $design->forceFill([
            'name' => trim($validated['name']) ?: 'Diseño sin título',
            'name_manual' => true,
        ])->save();

        $state = $design->state ?? [];
        $state['designTitle'] = $design->name;
        $state['designTitleManual'] = true;
        $design->forceFill(['state' => $state])->save();

        return response()->json([
            'design' => $design->fresh(),
        ]);
    }

    public function destroy(Request $request, Design $design): JsonResponse
    {
        $this->authorizeOwnership($request, $design);

        $design->delete();

        return response()->json([
            'deleted' => true,
        ]);
    }

    private function authorizeOwnership(Request $request, Design $design): void
    {
        abort_unless($request->user()?->is($design->user), 404);
    }

    /**
     * @param  array<string, mixed>  $state
     * @return array<string, mixed>
     */
    private function extractDesignMetadata(array $state): array
    {
        return [
            'objective' => $state['objective'] ?? null,
            'output_type' => $state['outputType'] ?? null,
            'format' => $state['format'] ?? null,
            'size_label' => $state['size'] ?? null,
            'surface_width' => $state['designSurface']['width'] ?? null,
            'surface_height' => $state['designSurface']['height'] ?? null,
            'template_category' => $state['templateCategory'] ?? null,
            'selected_template_id' => $state['selectedTemplateId'] ?? null,
            'name_manual' => (bool) ($state['designTitleManual'] ?? false),
        ];
    }

    /**
     * @param  array<string, mixed>  $state
     */
    private function resolveDesignName(array $state): string
    {
        $name = trim((string) ($state['designTitle'] ?? ''));

        return $name !== '' ? $name : 'Diseño sin título';
    }
}
