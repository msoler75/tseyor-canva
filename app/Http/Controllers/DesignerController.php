<?php

namespace App\Http\Controllers;

use App\Models\Design;
use App\Models\User;
use App\Support\DesignerStateRules;
use App\Support\JwtService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Inertia\Inertia;
use Inertia\Response;
use Symfony\Component\HttpFoundation\BinaryFileResponse;

class DesignerController extends Controller
{
    private const SESSION_KEY = 'designer.state';

    public function __construct(
        private readonly JwtService $jwtService,
    ) {
    }

    /**
     * @var array<string, array{component:string,label:string,url:string}>
     */
    private array $steps = [
        'objective' => ['component' => 'Designer/ObjectivePage', 'label' => 'Objetivo', 'url' => '/designer/objective'],
        'format' => ['component' => 'Designer/FormatPage', 'label' => 'Formato', 'url' => '/designer/format'],
        'content' => ['component' => 'Designer/ContentPage', 'label' => 'Datos', 'url' => '/designer/content'],
        'templates' => ['component' => 'Designer/TemplatesPage', 'label' => 'Plantillas', 'url' => '/designer/templates'],
        'editor' => ['component' => 'Designer/EditorPage', 'label' => 'Editor', 'url' => '/designer/editor'],
        'export' => ['component' => 'Designer/ExportPage', 'label' => 'Exportar', 'url' => '/designer/export'],
    ];

    public function welcome(Request $request): Response
    {
        /** @var User|null $user */
        $user = $request->user();

        return Inertia::render('Designer/WelcomePage', [
            'currentStep' => null,
            'steps' => [],
            'navigation' => [
                'previous' => null,
                'next' => null,
            ],
            'designs' => $user
                ? $user->designs()
                    ->latest('updated_at')
                    ->get([
                        'uuid',
                        'name',
                        'objective',
                        'format',
                        'size_label',
                        'updated_at',
                        'created_at',
                    ])
                : [],
            'devLoginToken' => app()->isLocal()
                ? $this->jwtService->issueBootstrapLoginToken('dev', 'dev@example.com')
                : null,
        ]);
    }

    public function objective(): Response
    {
        return $this->page('objective');
    }

    public function format(): Response
    {
        return $this->page('format');
    }

    public function content(): Response
    {
        return $this->page('content');
    }

    public function templates(): Response
    {
        return $this->page('templates');
    }

    public function editor(): Response
    {
        return $this->page('editor');
    }

    public function export(): Response
    {
        return $this->page('export');
    }

    public function saveState(Request $request): JsonResponse
    {
        $validated = $request->validate([
            ...DesignerStateRules::rules(),
            'state.currentDesignUuid' => ['nullable', 'string', 'max:36'],
        ]);

        $state = $validated['state'];

        if (Auth::check()) {
            /** @var User $user */
            $user = $request->user();

            $design = null;

            if (!empty($state['currentDesignUuid'])) {
                $design = $user->designs()->where('uuid', $state['currentDesignUuid'])->first();
            }

            if (!$design) {
                $design = $user->designs()->create([
                    'uuid' => (string) Str::uuid(),
                    'name' => trim((string) ($state['designTitle'] ?? '')) ?: 'Diseño sin título',
                    'name_manual' => (bool) ($state['designTitleManual'] ?? false),
                    'objective' => $state['objective'] ?? null,
                    'output_type' => $state['outputType'] ?? null,
                    'format' => $state['format'] ?? null,
                    'size_label' => $state['size'] ?? null,
                    'surface_width' => $state['designSurface']['width'] ?? null,
                    'surface_height' => $state['designSurface']['height'] ?? null,
                    'template_category' => $state['templateCategory'] ?? null,
                    'selected_template_id' => $state['selectedTemplateId'] ?? null,
                    'state' => $state,
                    'status' => 'draft',
                    'last_opened_at' => now(),
                ]);
            } else {
                $design->fill([
                    'name' => trim((string) ($state['designTitle'] ?? '')) ?: 'Diseño sin título',
                    'name_manual' => (bool) ($state['designTitleManual'] ?? false),
                    'objective' => $state['objective'] ?? null,
                    'output_type' => $state['outputType'] ?? null,
                    'format' => $state['format'] ?? null,
                    'size_label' => $state['size'] ?? null,
                    'surface_width' => $state['designSurface']['width'] ?? null,
                    'surface_height' => $state['designSurface']['height'] ?? null,
                    'template_category' => $state['templateCategory'] ?? null,
                    'selected_template_id' => $state['selectedTemplateId'] ?? null,
                    'state' => $state,
                    'last_opened_at' => now(),
                ])->save();
            }

            $state['currentDesignUuid'] = $design->uuid;
        }

        $request->session()->put(self::SESSION_KEY, $state);

        return response()->json([
            'saved' => true,
            'designUuid' => $state['currentDesignUuid'] ?? null,
        ]);
    }

    public function resetState(Request $request): JsonResponse
    {
        $request->session()->forget(self::SESSION_KEY);

        return response()->json([
            'reset' => true,
        ]);
    }

    public function storeUpload(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'file' => ['required', 'file', 'image', 'max:20480'],
            'assetId' => ['nullable', 'string', 'max:120'],
            'label' => ['nullable', 'string', 'max:255'],
        ]);

        $file = $validated['file'];
        /** @var User|null $user */
        $user = $request->user();
        $folder = $user
            ? sprintf('designer/uploads/users/%s', $user->id)
            : sprintf('designer/uploads/%s', trim((string) $request->session()->getId()) ?: 'guest');
        $extension = $file->guessExtension() ?: $file->extension() ?: 'bin';
        $filename = sprintf('%s.%s', Str::uuid()->toString(), $extension);
        $path = $file->storeAs($folder, $filename, 'public');

        $assetId = $validated['assetId'] ?? null;

        if ($user) {
            $asset = $user->designAssets()->create([
                'uuid' => (string) Str::uuid(),
                'label' => $validated['label'] ?? $file->getClientOriginalName(),
                'disk' => 'public',
                'path' => $path,
                'mime_type' => File::mimeType(Storage::disk('public')->path($path)) ?: $file->getMimeType(),
                'extension' => $extension,
                'size_bytes' => $file->getSize() ?: 0,
                'uploaded_at' => now(),
            ]);

            $assetId = (string) $asset->id;
        }

        return response()->json([
            'uploaded' => true,
            'assetId' => $assetId,
            'label' => $validated['label'] ?? $file->getClientOriginalName(),
            'path' => $path,
            'url' => route('designer.uploads.show', ['path' => $path]),
        ]);
    }

    public function showUpload(string $path): BinaryFileResponse
    {
        abort_unless(Storage::disk('public')->exists($path), 404);

        $absolutePath = Storage::disk('public')->path($path);
        $mimeType = File::mimeType($absolutePath) ?: 'application/octet-stream';

        return response()->file($absolutePath, [
            'Content-Type' => $mimeType,
            'Cache-Control' => 'public, max-age=31536000',
        ]);
    }

    private function page(string $currentStep): Response
    {
        $this->loadRequestedDesignIntoSession(request());

        $stepKeys = array_keys($this->steps);
        $currentIndex = array_search($currentStep, $stepKeys, true);
        $previous = $currentIndex > 0 ? $this->steps[$stepKeys[$currentIndex - 1]]['url'] : null;
        $next = $currentIndex < count($stepKeys) - 1 ? $this->steps[$stepKeys[$currentIndex + 1]]['url'] : null;

        return Inertia::render($this->steps[$currentStep]['component'], [
            'currentStep' => $currentStep,
            'steps' => array_map(
                fn (string $key): array => [
                    'id' => $key,
                    'label' => $this->steps[$key]['label'],
                    'url' => $this->steps[$key]['url'],
                ],
                $stepKeys
            ),
            'navigation' => [
                'previous' => $previous,
                'next' => $next,
            ],
        ]);
    }

    public static function sessionKey(): string
    {
        return self::SESSION_KEY;
    }

    private function loadRequestedDesignIntoSession(Request $request): void
    {
        $routeDesign = $request->route('design');
        $designUuid = $routeDesign instanceof Design
            ? $routeDesign->uuid
            : ($request->query('design') ?: null);

        if (!$designUuid || !$request->user()) {
            return;
        }

        /** @var User $user */
        $user = $request->user();

        /** @var Design|null $design */
        $design = $user->designs()->where('uuid', $designUuid)->first();

        if (!$design) {
            return;
        }

        $state = $design->state ?? [];
        $state['currentDesignUuid'] = $design->uuid;
        $state['designTitle'] = $design->name;
        $state['designTitleManual'] = (bool) $design->name_manual;

        $request->session()->put(self::SESSION_KEY, $state);
    }
}
