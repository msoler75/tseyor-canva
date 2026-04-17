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
    // Hook para recuperar diseño temporal tras login
    // Se puede llamar desde el frontend tras login, o integrarse en el flujo de bienvenida
    public static function recoverSessionDesign(Request $request): JsonResponse
    {
        if (! Auth::check()) {
            return response()->json(['recovered' => false, 'reason' => 'No autenticado'], 401);
        }

        $sessionState = $request->session()->get(self::SESSION_KEY);
        if (! $sessionState) {
            return response()->json(['recovered' => false, 'reason' => 'No hay diseño temporal en sesión']);
        }

        /** @var User $user */
        $user = $request->user();

        // Si el diseño temporal tiene uuid y pertenece al usuario, actualizarlo
        $designUuid = $sessionState['currentDesignUuid'] ?? null;
        $design = null;
        if ($designUuid) {
            $design = $user->designs()->where('uuid', $designUuid)->first();
        }

        if ($design) {
            // Actualizar el diseño existente
            $design->fill([
                'name' => trim((string) ($sessionState['designTitle'] ?? '')) ?: 'Diseño sin título',
                'name_manual' => (bool) ($sessionState['designTitleManual'] ?? false),
                'objective' => $sessionState['objective'] ?? null,
                'output_type' => $sessionState['outputType'] ?? null,
                'format' => $sessionState['format'] ?? null,
                'size_label' => $sessionState['size'] ?? null,
                'surface_width' => $sessionState['designSurface']['width'] ?? null,
                'surface_height' => $sessionState['designSurface']['height'] ?? null,
                'template_category' => $sessionState['templateCategory'] ?? null,
                'selected_template_id' => $sessionState['selectedTemplateId'] ?? null,
                'state' => $sessionState,
                'status' => 'draft',
                'last_opened_at' => now(),
            ])->save();
        } else {
            // Crear copia nueva para el usuario
            $design = $user->designs()->create([
                'uuid' => (string) Str::uuid(),
                'name' => trim((string) ($sessionState['designTitle'] ?? '')) ?: 'Diseño sin título',
                'name_manual' => (bool) ($sessionState['designTitleManual'] ?? false),
                'objective' => $sessionState['objective'] ?? null,
                'output_type' => $sessionState['outputType'] ?? null,
                'format' => $sessionState['format'] ?? null,
                'size_label' => $sessionState['size'] ?? null,
                'surface_width' => $sessionState['designSurface']['width'] ?? null,
                'surface_height' => $sessionState['designSurface']['height'] ?? null,
                'template_category' => $sessionState['templateCategory'] ?? null,
                'selected_template_id' => $sessionState['selectedTemplateId'] ?? null,
                'state' => $sessionState,
                'status' => 'draft',
                'last_opened_at' => now(),
            ]);
        }

        // Limpiar la sesión
        $request->session()->forget(self::SESSION_KEY);

        return response()->json([
            'recovered' => true,
            'designUuid' => $design->uuid,
        ]);
    }

    private const SESSION_KEY = 'designer.state';

    public function __construct(
        private readonly JwtService $jwtService,
    ) {}

    public function welcome(Request $request): Response
    {
        /** @var User|null $user */
        $user = $request->user();

        // Diseños públicos de la comunidad
        $communityDesigns = Design::query()
            ->where('public', true)
            ->latest('updated_at')
            ->limit(12)
            ->get([
                'uuid',
                'name',
                'objective',
                'format',
                'size_label',
                'thumbnail_path',
                'updated_at',
                'created_at',
            ])->map(fn (Design $design): array => [
                'uuid' => $design->uuid,
                'name' => $design->name,
                'objective' => $design->objective,
                'format' => $design->format,
                'size_label' => $design->size_label,
                'thumbnail_url' => $design->thumbnail_path
                    ? route('designer.uploads.show', ['path' => $design->thumbnail_path])
                    : null,
                'updated_at' => $design->updated_at,
                'created_at' => $design->created_at,
            ]);

        return Inertia::render('Home', [
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
                        'thumbnail_path',
                        'updated_at',
                        'created_at',
                    ])->map(fn (Design $design): array => [
                        'uuid' => $design->uuid,
                        'name' => $design->name,
                        'objective' => $design->objective,
                        'format' => $design->format,
                        'size_label' => $design->size_label,
                        'thumbnail_url' => $design->thumbnail_path
                            ? route('designer.uploads.show', ['path' => $design->thumbnail_path])
                            : null,
                        'updated_at' => $design->updated_at,
                        'created_at' => $design->created_at,
                    ])
                : [],
            'communityDesigns' => $communityDesigns,
        ]);
    }

    public function editor(): Response
    {
        $request = request();

        $activeDesign = $this->resolveRequestedDesign($request);
        $fontFamilies = $this->fontFamilies();

        return Inertia::render('Designer/EditorPage', [
            'currentStep' => 'editor',
            'steps' => [],
            'navigation' => [
                'previous' => null,
                'next' => null,
            ],
            'fontFamilies' => $fontFamilies,
            'designer' => [
                'state' => $activeDesign?->state,
                'currentDesign' => $activeDesign
                    ? [
                        'uuid' => $activeDesign->uuid,
                        'name' => $activeDesign->name,
                        'updated_at' => $activeDesign->updated_at,
                    ]
                    : null,
                'endpoints' => [
                    'save' => route('designer.state.save'),
                    'reset' => route('designer.state.reset'),
                    'upload' => route('designer.uploads.store'),
                    'designsIndex' => Auth::check() ? route('designer.designs.index') : null,
                    'designsStore' => Auth::check() ? route('designer.designs.store') : null,
                    'assetsIndex' => Auth::check() ? route('designer.assets.index') : null,
                ],
                'imageUploads' => [
                    'maxWidth' => config('designer.image_uploads.max_width'),
                    'maxHeight' => config('designer.image_uploads.max_height'),
                    'jpegQuality' => config('designer.image_uploads.jpeg_quality'),
                    'webpQuality' => config('designer.image_uploads.webp_quality'),
                ],
            ],
        ]);
    }

    public function saveState(Request $request): JsonResponse
    {
        $validated = $request->validate([
            ...DesignerStateRules::rules(),
            'state.currentDesignUuid' => ['nullable', 'string', 'max:36'],
            'thumbnailDataUrl' => ['nullable', 'string'],
        ]);

        $state = $validated['state'];

        if (! Auth::check()) {
            // Usuario no autenticado: guardar el diseño en sesión
            $request->session()->put(self::SESSION_KEY, $state);

            return response()->json([
                'saved' => true,
                'designUuid' => $state['currentDesignUuid'] ?? null,
                'temporal' => true,
            ]);
        }

        /** @var User $user */
        $user = $request->user();

        $design = null;

        if (! empty($state['currentDesignUuid'])) {
            $design = $user->designs()->where('uuid', $state['currentDesignUuid'])->first();
        }

        if (! $design) {
            return response()->json([
                'saved' => false,
                'message' => 'No se puede autoguardar un diseño autenticado sin currentDesignUuid.',
            ], 409);
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

        if (! empty($validated['thumbnailDataUrl'])) {
            $thumbnailPath = $this->storeThumbnailDataUrl($user, $design, $validated['thumbnailDataUrl']);
            if ($thumbnailPath) {
                $design->forceFill([
                    'thumbnail_path' => $thumbnailPath,
                ])->save();
            }
        }

        $state['currentDesignUuid'] = $design->uuid;

        return response()->json([
            'saved' => true,
            'designUuid' => $state['currentDesignUuid'] ?? null,
        ]);
    }

    public function resetState(Request $request): JsonResponse
    {
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

    /**
     * @return array<int, string>
     */
    private function fontFamilies(): array
    {
        $fontsListPath = base_path('resources/fonts_list.txt');
        if (! file_exists($fontsListPath)) {
            return [];
        }

        $fontFamilies = [];
        $lines = file($fontsListPath, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        foreach ($lines as $line) {
            $line = trim($line);
            if ($line !== '' && $line[0] !== '#') {
                $fontFamilies[] = $line;
            }
        }

        return $fontFamilies;
    }

    public static function sessionKey(): string
    {
        return self::SESSION_KEY;
    }

    private function resolveRequestedDesign(Request $request): ?Design
    {
        $routeDesign = $request->route('design');
        $designUuid = $routeDesign instanceof Design
            ? $routeDesign->uuid
            : (is_string($routeDesign) ? $routeDesign : ($request->query('design') ?: null));

        if (! $designUuid) {
            return null;
        }

        $design = Design::where('uuid', $designUuid)->first();
        if (! $design) {
            return null;
        }

        $user = $request->user();

        // Si hay usuario autenticado y el diseño es suyo, devolverlo tal cual
        if ($user && $design->user_id === $user->id) {
            $state = $design->state ?? [];
            $state['currentDesignUuid'] = $design->uuid;
            $state['designTitle'] = $design->name;
            $state['designTitleManual'] = (bool) $design->name_manual;
            $design->state = $state;

            return $design;
        }

        // Si hay usuario autenticado y el diseño NO es suyo, crear copia para él
        if ($user && $design->user_id !== $user->id) {
            $copy = $user->designs()->create([
                'uuid' => (string) Str::uuid(),
                'name' => $design->name.' (copia)',
                'name_manual' => $design->name_manual,
                'objective' => $design->objective,
                'output_type' => $design->output_type,
                'format' => $design->format,
                'size_label' => $design->size_label,
                'surface_width' => $design->surface_width,
                'surface_height' => $design->surface_height,
                'template_category' => $design->template_category,
                'selected_template_id' => $design->selected_template_id,
                'state' => $design->state,
                'status' => 'draft',
                'last_opened_at' => now(),
            ]);
            $state = $copy->state ?? [];
            $state['currentDesignUuid'] = $copy->uuid;
            $state['designTitle'] = $copy->name;
            $state['designTitleManual'] = (bool) $copy->name_manual;
            $copy->state = $state;

            return $copy;
        }

        // Si NO hay usuario autenticado, guardar el diseño en sesión como temporal
        if (! $user) {
            $state = $design->state ?? [];
            $state['currentDesignUuid'] = null; // No asociar UUID real
            $state['designTitle'] = $design->name;
            $state['designTitleManual'] = (bool) $design->name_manual;
            // Guardar en sesión para edición temporal
            $request->session()->put(self::SESSION_KEY, $state);
            // Devolver un objeto Design simulado solo para el frontend
            $fakeDesign = new Design;
            $fakeDesign->uuid = null;
            $fakeDesign->name = $design->name;
            $fakeDesign->state = $state;
            $fakeDesign->updated_at = $design->updated_at;

            return $fakeDesign;
        }

        return null;
    }

    private function storeThumbnailDataUrl(User $user, Design $design, string $dataUrl): ?string
    {
        if (! preg_match('/^data:image\/(?<type>[a-zA-Z0-9.+-]+);base64,(?<data>.+)$/', $dataUrl, $matches)) {
            return null;
        }

        $binary = base64_decode($matches['data'], true);
        if ($binary === false) {
            return null;
        }

        $extension = strtolower($matches['type']);
        if ($extension === 'jpeg') {
            $extension = 'jpg';
        }

        $path = sprintf('designer/thumbnails/users/%s/%s.%s', $user->id, $design->uuid, $extension);
        Storage::disk('public')->put($path, $binary);

        return $path;
    }
}
