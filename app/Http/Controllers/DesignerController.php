<?php

namespace App\Http\Controllers;

use App\Models\Design;
use App\Models\DesignTemplate;
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

        // --- Mover imágenes temporales a la carpeta del usuario y registrar assets ---
        $userUploadedImages = $sessionState['userUploadedImages'] ?? [];
        $sessionId = trim((string) $request->session()->getId()) ?: 'guest';
        $assetsMap = [];
        foreach ($userUploadedImages as &$image) {
            $storagePath = $image['storagePath'] ?? null;
            if ($storagePath && (str_starts_with($storagePath, $sessionId.'/') || str_starts_with($storagePath, 'guest/'))) {
                $filename = basename($storagePath);
                $oldPath = $storagePath;
                $newPath = $user->id . '/' . $filename;
                // Mover el archivo en el disco 'users'
                if (Storage::disk('users')->exists($oldPath)) {
                    Storage::disk('users')->move($oldPath, $newPath);
                }
                // Registrar el asset si no existe
                $asset = $user->designAssets()->where('path', $newPath)->first();
                if (! $asset) {
                    $asset = $user->designAssets()->create([
                        'uuid' => (string) Str::uuid(),
                        'label' => $image['label'] ?? $filename,
                        'disk' => 'users',
                        'path' => $newPath,
                        'mime_type' => $image['mime_type'] ?? null,
                        'extension' => pathinfo($filename, PATHINFO_EXTENSION),
                        'size_bytes' => $image['size_bytes'] ?? null,
                        'uploaded_at' => now(),
                    ]);
                }
                $assetsMap[$image['assetId'] ?? $image['id'] ?? $filename] = $asset->id;
                // Actualizar storagePath en el estado
                $image['storagePath'] = $newPath;
                $image['assetId'] = $asset->id;
            }
        }
        unset($image);
        // Actualizar el estado en sesión con los paths y assetId corregidos
        $sessionState['userUploadedImages'] = $userUploadedImages;

        // Si el diseño temporal tiene uuid y pertenece al usuario, actualizarlo
        $designUuid = $sessionState['currentDesignUuid'] ?? null;
        $design = null;
        if ($designUuid) {
            $design = $user->designs()->where('uuid', $designUuid)->first();
        }

        if ($design && is_object($design) && method_exists($design, 'fill')) {
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
            ->whereDoesntHave('baseTemplate')
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
                'thumbnail_url' => $this->thumbnailUrl($design),
                'updated_at' => $design->updated_at,
                'created_at' => $design->created_at,
            ]);

        $adminTemplates = $user?->name === 'admin'
            ? $this->publishedTemplates()
            : [];

        return Inertia::render('Home', [
            'currentStep' => null,
            'steps' => [],
            'navigation' => [
                'previous' => null,
                'next' => null,
            ],
            'designs' => $user
                ? $user->designs()
                    ->whereDoesntHave('baseTemplate')
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
                        'thumbnail_url' => $this->thumbnailUrl($design),
                        'updated_at' => $design->updated_at,
                        'created_at' => $design->created_at,
                    ])
                : [],
            'communityDesigns' => $communityDesigns,
            'adminTemplates' => $adminTemplates,
        ]);
    }

    public function editor(): Response
    {
        $request = request();

        $activeDesign = $this->resolveRequestedDesign($request);
        $activeDesign?->loadMissing('baseTemplate');
        $activeBaseTemplate = $activeDesign?->baseTemplate;
        $fontFamilies = $this->fontFamilies();

        // Si no hay diseño activo (invitado), hidratar desde sesión
        $designerState = $activeDesign?->state;
        if (!$activeDesign) {
            $designerState = $request->session()->get(self::SESSION_KEY) ?: null;
        }

        return Inertia::render('Designer/EditorPage', [
            'currentStep' => 'editor',
            'steps' => [],
            'navigation' => [
                'previous' => null,
                'next' => null,
            ],
            'fontFamilies' => $fontFamilies,
            'designer' => [
                'state' => $designerState,
                'currentDesign' => $activeDesign
                    ? [
                        'uuid' => $activeDesign->uuid,
                        'name' => $activeDesign->name,
                        'updated_at' => $activeDesign->updated_at,
                        'baseTemplate' => $activeBaseTemplate
                            ? $this->serializeTemplate($activeBaseTemplate)
                            : null,
                    ]
                    : null,
                'isTemplateBaseEditor' => (bool) $activeBaseTemplate,
                'currentTemplate' => $activeBaseTemplate
                    ? $this->serializeTemplate($activeBaseTemplate)
                    : null,
                'endpoints' => [
                    'save' => route('designer.state.save'),
                    'reset' => route('designer.state.reset'),
                    'upload' => route('designer.uploads.store'),
                    'designsIndex' => Auth::check() ? route('designer.designs.index') : null,
                    'designsStore' => Auth::check() ? route('designer.designs.store') : null,
                    'assetsIndex' => Auth::check() ? route('designer.assets.index') : null,
                    'templatesIndex' => route('designer.templates.index'),
                ],
                'templates' => $this->publishedTemplates(),
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
        if (! $this->isPersistableDesignerState($state)) {
            return response()->json([
                'saved' => false,
                'message' => 'El estado recibido esta incompleto y no se ha guardado.',
            ], 422);
        }

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

            if (! $design && $user->name === 'admin') {
                $candidate = Design::query()
                    ->where('uuid', $state['currentDesignUuid'])
                    ->with('baseTemplate')
                    ->first();

                if ($candidate?->baseTemplate) {
                    $design = $candidate;
                }
            }
        }

        if (! $design) {
            return response()->json([
                'saved' => false,
                'message' => empty($state['currentDesignUuid'])
                    ? 'No se puede autoguardar un dise?o autenticado sin currentDesignUuid.'
                    : 'No tienes permiso para autoguardar este dise?o.',
            ], 409);
        } else {
            $state['currentDesignUuid'] = $design->uuid;

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
        if ($user) {
            $folder = $user->id;
            $disk = 'users';
        } else {
            $folder = trim((string) $request->session()->getId()) ?: 'guest';
            $disk = 'users';
        }
        $extension = $file->guessExtension() ?: $file->extension() ?: 'bin';
        $filename = sprintf('%s.%s', Str::uuid()->toString(), $extension);
        $path = $file->storeAs($folder, $filename, $disk);

        $assetId = $validated['assetId'] ?? null;

        if ($user) {
            $asset = $user->designAssets()->create([
                'uuid' => (string) Str::uuid(),
                'label' => $validated['label'] ?? $file->getClientOriginalName(),
                'disk' => 'users',
                'path' => $path,
                'mime_type' => File::mimeType(Storage::disk('users')->path($path)) ?: $file->getMimeType(),
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
        $design->loadMissing('baseTemplate');

        // Un diseño base de plantilla solo puede abrirse/editarse como tal por admin.
        // Usuarios no admin (incluyendo invitados) reciben 403 y no se genera copia.
        if (($design->baseTemplate !== null) && (($user?->name ?? null) !== 'admin')) {
            abort(403);
        }

        // Los dise?os base de plantilla se editan como la base original.
        // No deben copiarse para admin, porque al copiarlos se pierde la relaci?n
        // design_templates.base_design_id -> designs.id que activa el modo plantilla.
        if ($user?->name === 'admin' && $design->baseTemplate) {
            $state = $design->state ?? [];
            $state['currentDesignUuid'] = $design->uuid;
            $state['designTitle'] = $design->name;
            $state['designTitleManual'] = (bool) $design->name_manual;
            $design->state = $state;

            return $design;
        }

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

        $path = sprintf('%s.%s', $design->uuid, $extension);
        Storage::disk('thumbnails')->put($path, $binary);

        return $path;
    }

    private function thumbnailUrl(Design $design): ?string
    {
        if (! $design->thumbnail_path) {
            return null;
        }

        return route('designer.uploads.show', [
            'path' => $design->thumbnail_path,
            'v' => optional($design->updated_at)->timestamp ?? time(),
        ]);
    }

    /**
     * @return array<int, array<string, mixed>>
     */
    private function publishedTemplates(): array
    {
        return DesignTemplate::query()
            ->with('baseDesign:id,uuid,thumbnail_path,updated_at')
            ->where('status', 'published')
            ->orderByDesc('featured')
            ->orderBy('sort_order')
            ->orderBy('title')
            ->get()
            ->map(fn (DesignTemplate $template): array => $this->serializeTemplate($template))
            ->values()
            ->all();
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
            'thumbnail_url' => $template->baseDesign?->thumbnail_path
                ? route('designer.uploads.show', [
                    'path' => $template->baseDesign->thumbnail_path,
                    'v' => optional($template->baseDesign->updated_at)->timestamp ?? time(),
                ])
                : null,
        ];
    }

    /**
     * @param  array<string, mixed>  $state
     */
    private function isPersistableDesignerState(array $state): bool
    {
        return isset($state['darkMode'], $state['mode'])
            && is_array($state['content'] ?? null)
            && is_array($state['elementLayout'] ?? null)
            && is_array($state['elementLayout']['background'] ?? null)
            && is_array($state['elementLayout']['title'] ?? null)
            && (! isset($state['customElements']) || is_array($state['customElements']))
            && (! isset($state['userUploadedImages']) || is_array($state['userUploadedImages']));
    }
}
