<?php

namespace App\Http\Controllers;

use App\Models\Design;
use App\Models\DesignTemplate;
use App\Models\User;
use App\Services\DesignTemplateGenerator;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;
use Inertia\Inertia;
use Inertia\Response;

class DesignTemplateController extends Controller
{
    public function inventory(Request $request): Response
    {
        $user = $request->user();
        abort_unless($this->isAdmin($user), 403);

        $templates = DesignTemplate::query()
            ->with('baseDesign:id,uuid,thumbnail_path,updated_at,name')
            ->orderByDesc('featured')
            ->orderBy('sort_order')
            ->orderBy('title')
            ->get()
            ->map(fn (DesignTemplate $template): array => $this->serializeTemplate($template));

        return Inertia::render('Designer/Templates/Index', [
            'templates' => $templates,
        ]);
    }

    public function index(Request $request): JsonResponse
    {
        $includeDrafts = $this->isAdmin($request->user()) && $request->boolean('includeDrafts');

        $templates = DesignTemplate::query()
            ->with('baseDesign:id,uuid,thumbnail_path,updated_at')
            ->when(! $includeDrafts, fn ($query) => $query->where('status', 'published'))
            ->orderByDesc('featured')
            ->orderBy('sort_order')
            ->orderBy('title')
            ->get()
            ->map(fn (DesignTemplate $template): array => $this->serializeTemplate($template));

        return response()->json([
            'templates' => $templates,
        ]);
    }

    public function store(Request $request, Design $design): JsonResponse
    {
        /** @var User|null $user */
        $user = $request->user();
        abort_unless($this->isAdmin($user), 403);
        abort_unless($design->user?->is($user), 404);

        $validated = $this->validateTemplatePayload($request);

        $template = DesignTemplate::query()->updateOrCreate(
            ['base_design_id' => $design->id],
            [
                'uuid' => DesignTemplate::query()->where('base_design_id', $design->id)->value('uuid') ?: (string) Str::uuid(),
                ...$validated,
                'adaptation_mode' => 'proportional',
                'published_at' => ($validated['status'] ?? 'draft') === 'published' ? now() : null,
            ],
        );

        return response()->json([
            'template' => $this->serializeTemplate($template->fresh('baseDesign')),
        ], 201);
    }

    public function update(Request $request, DesignTemplate $template): JsonResponse
    {
        abort_unless($this->isAdmin($request->user()), 403);

        $validated = $this->validateTemplatePayload($request, partial: true);
        $nextStatus = $validated['status'] ?? $template->status;

        $template->fill([
            ...$validated,
            'adaptation_mode' => 'proportional',
            'published_at' => $nextStatus === 'published'
                ? ($template->published_at ?? now())
                : ($nextStatus === 'draft' ? null : $template->published_at),
        ])->save();

        return response()->json([
            'template' => $this->serializeTemplate($template->fresh('baseDesign')),
        ]);
    }

    public function generate(Request $request, DesignTemplate $template, DesignTemplateGenerator $generator): JsonResponse
    {
        /** @var User|null $user */
        $user = $request->user();
        if ($template->status !== 'published' && ! ($user && $this->isAdmin($user))) {
            abort(404);
        }

        $validated = $request->validate([
            'content' => ['nullable', 'array'],
            'content.*' => ['nullable', 'string', 'max:5000'],
            'objective' => ['nullable', 'string', 'max:120'],
            'outputType' => ['nullable', 'string', 'max:40'],
            'format' => ['nullable', 'string', 'max:40'],
            'size' => ['nullable', 'string', 'max:120'],
            'designTitle' => ['nullable', 'string', 'max:255'],
            'designSurface' => ['nullable', 'array'],
            'designSurface.width' => ['nullable', 'numeric', 'min:1'],
            'designSurface.height' => ['nullable', 'numeric', 'min:1'],
            'targetDesignUuid' => ['nullable', 'string', 'max:36'],
        ]);

        // Invitado: generar estado y guardar en sesión
        if (!$user) {
            $baseDesign = $template->baseDesign;
            $generatorClass = get_class($generator);
            // Generar el estado igual que el generador, pero sin guardar en BD
            $state = $baseDesign->state ?? [];
            $targetSurface = $generator->normalizeSurface($validated['designSurface'] ?? null)
                ?? $generator->normalizeSurface($state['designSurface'] ?? null)
                ?? $generator->surfaceFromDesign($baseDesign);
            if ($targetSurface) {
                $state = $generator->adaptStateToSurface($state, $generator->surfaceFromState($state, $baseDesign), $targetSurface);
            }
            $state = $generator->applyData($state, $validated, $template->field_mappings ?? []);
            $uuid = (string) Str::uuid();
            $state['currentDesignUuid'] = $uuid;
            $state['selectedTemplateId'] = $template->uuid;
            $state['designSurface'] = $targetSurface ?? ($state['designSurface'] ?? null);
            $state['objective'] = $validated['objective'] ?? ($state['objective'] ?? null);
            $state['outputType'] = $validated['outputType'] ?? ($state['outputType'] ?? null);
            $state['format'] = $validated['format'] ?? ($state['format'] ?? null);
            $state['size'] = $validated['size'] ?? ($state['size'] ?? null);
            $name = trim((string) ($validated['designTitle'] ?? ''));
            if ($name === '' || Str::lower($name) === 'diseño sin título' || Str::lower($name) === 'diseno sin titulo') {
                $name = sprintf('%s personalizado', $template->title);
            }
            $state['designTitle'] = $name;
            $state['designTitleManual'] = false;
            // Guardar en sesión
            $request->session()->put('designer.state', $state);
            return response()->json([
                'design' => [
                    'uuid' => $uuid,
                    'name' => $name,
                    'state' => $state,
                ],
                'temporal' => true,
            ], 201);
        }

        $targetDesign = null;
        if (! empty($validated['targetDesignUuid'])) {
            $targetDesign = $user->designs()
                ->where('uuid', $validated['targetDesignUuid'])
                ->whereDoesntHave('baseTemplate')
                ->firstOrFail();
        }

        $design = $generator->generate(
            $template->loadMissing('baseDesign'),
            $user,
            $validated,
            $validated['designSurface'] ?? null,
            $targetDesign,
        );

        return response()->json([
            'design' => $design->fresh(),
        ], 201);
    }

    /**
     * @return array<string, mixed>
     */
    private function validateTemplatePayload(Request $request, bool $partial = false): array
    {
        $required = $partial ? 'sometimes' : 'required';

        $validated = $request->validate([
            'title' => [$required, 'string', 'max:255'],
            'description' => ['nullable', 'string', 'max:2000'],
            'category_ids' => [$required, 'array', 'min:1'],
            'category_ids.*' => ['string', 'max:120'],
            'objective_ids' => [$required, 'array', 'min:1'],
            'objective_ids.*' => ['string', 'max:120'],
            'field_mappings' => ['nullable', 'array'],
            'field_mappings.*.sourceField' => ['required_with:field_mappings', 'string', 'max:120'],
            'field_mappings.*.targetField' => ['nullable', 'string', 'max:120'],
            'field_mappings.*.elementId' => ['nullable', 'string', 'max:120'],
            'field_mappings.*.property' => ['nullable', 'string', Rule::in(['text', 'src'])],
            'field_mappings.*.label' => ['nullable', 'string', 'max:255'],
            'field_mappings.*.fallback' => ['nullable', 'string', 'max:5000'],
            'status' => ['nullable', 'string', Rule::in(['draft', 'published', 'archived'])],
            'featured' => ['nullable', 'boolean'],
            'sort_order' => ['nullable', 'integer', 'min:0'],
        ]);

        if (array_key_exists('category_ids', $validated)) {
            $validated['category_ids'] = array_values(array_unique($validated['category_ids'] ?? []));
        }
        if (array_key_exists('objective_ids', $validated)) {
            $validated['objective_ids'] = array_values(array_unique($validated['objective_ids'] ?? []));
        }
        if (! $partial || array_key_exists('field_mappings', $validated)) {
            $validated['field_mappings'] = $validated['field_mappings'] ?? null;
        }
        if (! $partial) {
            $validated['status'] = $validated['status'] ?? 'published';
            $validated['featured'] = (bool) ($validated['featured'] ?? false);
            $validated['sort_order'] = (int) ($validated['sort_order'] ?? 0);
        } else {
            if (array_key_exists('featured', $validated)) {
                $validated['featured'] = (bool) $validated['featured'];
            }
            if (array_key_exists('sort_order', $validated)) {
                $validated['sort_order'] = (int) $validated['sort_order'];
            }
        }

        return $validated;
    }

    private function isAdmin(?User $user): bool
    {
        return $user?->name === 'admin';
    }

    /**
     * @return array<string, mixed>
     */
    private function serializeTemplate(DesignTemplate $template): array
    {
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
            'thumbnail_url' => $template->baseDesign?->thumbnail_path
                ? route('designer.uploads.show', [
                    'path' => $template->baseDesign->thumbnail_path,
                    'v' => optional($template->baseDesign->updated_at)->timestamp ?? time(),
                ])
                : null,
        ];
    }
}
