<?php

namespace App\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Inertia\Inertia;
use Inertia\Response;
use Symfony\Component\HttpFoundation\BinaryFileResponse;

class DesignerController extends Controller
{
    private const SESSION_KEY = 'designer.state';

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
        return Inertia::render('Designer/WelcomePage', [
            'currentStep' => null,
            'steps' => [],
            'navigation' => [
                'previous' => null,
                'next' => null,
            ],
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
            'state' => ['required', 'array'],
            'state.darkMode' => ['required', 'boolean'],
            'state.mode' => ['required', 'string', 'in:guided,direct'],
            'state.objective' => ['nullable', 'string'],
            'state.outputType' => ['nullable', 'string', 'in:print,digital'],
            'state.format' => ['nullable', 'string'],
            'state.size' => ['nullable', 'string'],
            'state.templateCategory' => ['nullable', 'string'],
            'state.selectedTemplateId' => ['nullable', 'string'],
            'state.autosaveMessage' => ['nullable', 'string', 'max:255'],
            'state.selectedElementId' => ['nullable', 'string'],
            'state.content' => ['required', 'array'],
            'state.content.*' => ['nullable', 'string', 'max:5000'],
            'state.elementLayout' => ['required', 'array'],
            'state.elementLayout.*.x' => ['nullable', 'numeric'],
            'state.elementLayout.*.y' => ['nullable', 'numeric'],
            'state.elementLayout.*.w' => ['nullable', 'numeric'],
            'state.elementLayout.*.h' => ['nullable', 'numeric'],
            'state.elementLayout.*.rotation' => ['nullable', 'numeric', 'between:-360,360'],
            'state.elementLayout.*.fontSize' => ['nullable', 'numeric'],
            'state.elementLayout.*.zIndex' => ['nullable', 'numeric'],
            'state.elementLayout.*.color' => ['nullable', 'string', 'max:32'],
            'state.elementLayout.*.shadow' => ['nullable', 'boolean'],
            'state.elementLayout.*.border' => ['nullable', 'boolean'],
            'state.elementLayout.*.borderStyle' => ['nullable', 'string', 'in:solid,dashed,dotted'],
            'state.elementLayout.*.fontFamily' => ['nullable', 'string', 'max:120'],
            'state.elementLayout.*.opacity' => ['nullable', 'numeric', 'between:0,100'],
            'state.elementLayout.*.fontWeight' => ['nullable', 'string', 'max:20'],
            'state.elementLayout.*.italic' => ['nullable', 'boolean'],
            'state.elementLayout.*.uppercase' => ['nullable', 'boolean'],
            'state.elementLayout.*.textAlign' => ['nullable', 'string', 'in:left,center,right,justify'],
            'state.elementLayout.*.letterSpacing' => ['nullable', 'numeric', 'between:-5,40'],
            'state.elementLayout.*.lineHeight' => ['nullable', 'numeric', 'between:0.5,4'],
            'state.elementLayout.*.textEffectMode' => ['nullable', 'string', 'max:40'],
            'state.elementLayout.*.shadowPreset' => ['nullable', 'string', 'max:40'],
            'state.elementLayout.*.shadowColor' => ['nullable', 'string', 'max:32'],
            'state.elementLayout.*.shadowAngle' => ['nullable', 'numeric', 'between:0,360'],
            'state.elementLayout.*.shadowOffset' => ['nullable', 'numeric', 'between:0,200'],
            'state.elementLayout.*.shadowBlur' => ['nullable', 'numeric', 'between:0,200'],
            'state.elementLayout.*.shadowOpacity' => ['nullable', 'numeric', 'between:0,100'],
            'state.elementLayout.*.contourWidth' => ['nullable', 'numeric', 'between:0,100'],
            'state.elementLayout.*.contourColor' => ['nullable', 'string', 'max:32'],
            'state.elementLayout.*.neonColor' => ['nullable', 'string', 'max:32'],
            'state.elementLayout.*.neonIntensity' => ['nullable', 'numeric', 'between:0,100'],
            'state.elementLayout.*.misalignedThickness' => ['nullable', 'numeric', 'between:0,100'],
            'state.elementLayout.*.hollowText' => ['nullable', 'boolean'],
            'state.elementLayout.*.bubbleColor' => ['nullable', 'string', 'max:32'],
            'state.elementLayout.*.backgroundColor' => ['nullable', 'string', 'max:32'],
            'state.elementLayout.*.backgroundRoundness' => ['nullable', 'numeric', 'between:0,100'],
            'state.elementLayout.*.backgroundPadding' => ['nullable', 'numeric', 'between:0,100'],
            'state.elementLayout.*.backgroundOpacity' => ['nullable', 'numeric', 'between:0,100'],
            'state.elementLayout.*.fillMode' => ['nullable', 'string', 'in:solid,gradient,image'],
            'state.elementLayout.*.gradientStart' => ['nullable', 'string', 'max:32'],
            'state.elementLayout.*.gradientEnd' => ['nullable', 'string', 'max:32'],
            'state.elementLayout.*.gradientAngle' => ['nullable', 'numeric', 'between:0,360'],
            'state.elementLayout.*.imageTintColor' => ['nullable', 'string', 'max:32'],
            'state.elementLayout.*.imageTintStrength' => ['nullable', 'numeric', 'between:0,100'],
            'state.elementLayout.*.imageCropScale' => ['nullable', 'numeric', 'between:1,10'],
            'state.elementLayout.*.imageCropOffsetX' => ['nullable', 'numeric', 'between:-1,1'],
            'state.elementLayout.*.imageCropOffsetY' => ['nullable', 'numeric', 'between:-1,1'],
            'state.elementLayout.*.flipX' => ['nullable', 'boolean'],
            'state.elementLayout.*.flipY' => ['nullable', 'boolean'],
            'state.elementLayout.background.backgroundImageSrc' => ['nullable', 'string'],
            'state.elementLayout.background.backgroundImageAssetId' => ['nullable', 'string', 'max:120'],
            'state.elementLayout.background.backgroundImagePendingDataUrl' => ['nullable', 'string'],
            'state.elementLayout.background.backgroundImageStoragePath' => ['nullable', 'string', 'max:1024'],
            'state.elementLayout.background.backgroundImageWidth' => ['nullable', 'numeric'],
            'state.elementLayout.background.backgroundImageHeight' => ['nullable', 'numeric'],
            'state.elementLayout.background.backgroundImageCropScale' => ['nullable', 'numeric', 'between:1,10'],
            'state.elementLayout.background.backgroundImageCropOffsetX' => ['nullable', 'numeric', 'between:-1,1'],
            'state.elementLayout.background.backgroundImageCropOffsetY' => ['nullable', 'numeric', 'between:-1,1'],
            'state.elementLayout.background.backgroundImageFlipX' => ['nullable', 'boolean'],
            'state.elementLayout.background.backgroundImageFlipY' => ['nullable', 'boolean'],
            'state.elementLayout.*.paragraphStyles' => ['nullable', 'array'],
            'state.elementLayout.*.paragraphStyles.*.fontSize' => ['nullable', 'numeric', 'between:8,200'],
            'state.elementLayout.*.paragraphStyles.*.color' => ['nullable', 'string', 'max:32'],
            'state.elementLayout.*.paragraphStyles.*.fontFamily' => ['nullable', 'string', 'max:120'],
            'state.elementLayout.*.paragraphStyles.*.fontWeight' => ['nullable', 'string', 'max:20'],
            'state.elementLayout.*.paragraphStyles.*.italic' => ['nullable', 'boolean'],
            'state.elementLayout.*.paragraphStyles.*.uppercase' => ['nullable', 'boolean'],
            'state.elementLayout.*.paragraphStyles.*.textAlign' => ['nullable', 'string', 'in:left,center,right,justify'],
            'state.elementLayout.*.paragraphStyles.*.letterSpacing' => ['nullable', 'numeric', 'between:-5,40'],
            'state.elementLayout.*.paragraphStyles.*.lineHeight' => ['nullable', 'numeric', 'between:0.5,4'],
            'state.customElements' => ['nullable', 'array'],
            'state.customElements.*.id' => ['nullable', 'string', 'max:120'],
            'state.customElements.*.type' => ['nullable', 'string', 'in:text,image,shape'],
            'state.customElements.*.label' => ['nullable', 'string', 'max:120'],
            'state.customElements.*.text' => ['nullable', 'string', 'max:2000'],
            'state.customElements.*.shapeKind' => ['nullable', 'string', 'max:60'],
            'state.customElements.*.src' => ['nullable', 'string'],
            'state.customElements.*.assetId' => ['nullable', 'string', 'max:120'],
            'state.customElements.*.pendingDataUrl' => ['nullable', 'string'],
            'state.customElements.*.storagePath' => ['nullable', 'string', 'max:1024'],
            'state.customElements.*.uploadStatus' => ['nullable', 'string', 'in:pending,uploading,done,error'],
            'state.customElements.*.needsUpload' => ['nullable', 'boolean'],
            'state.customElements.*.intrinsicWidth' => ['nullable', 'numeric'],
            'state.customElements.*.intrinsicHeight' => ['nullable', 'numeric'],
            'state.userUploadedImages' => ['nullable', 'array'],
            'state.userUploadedImages.*.id' => ['nullable', 'string', 'max:120'],
            'state.userUploadedImages.*.label' => ['nullable', 'string', 'max:255'],
            'state.userUploadedImages.*.src' => ['nullable', 'string'],
            'state.userUploadedImages.*.assetId' => ['nullable', 'string', 'max:120'],
            'state.userUploadedImages.*.pendingDataUrl' => ['nullable', 'string'],
            'state.userUploadedImages.*.storagePath' => ['nullable', 'string', 'max:1024'],
            'state.userUploadedImages.*.uploadStatus' => ['nullable', 'string', 'in:pending,uploading,done,error'],
            'state.userUploadedImages.*.needsUpload' => ['nullable', 'boolean'],
            'state.userUploadedImages.*.errorMessage' => ['nullable', 'string', 'max:255'],
            'state.userUploadedImages.*.intrinsicWidth' => ['nullable', 'numeric'],
            'state.userUploadedImages.*.intrinsicHeight' => ['nullable', 'numeric'],
        ]);

        $request->session()->put(self::SESSION_KEY, $validated['state']);

        return response()->json([
            'saved' => true,
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
        $sessionFolder = trim((string) $request->session()->getId());
        $folder = sprintf('designer/uploads/%s', $sessionFolder !== '' ? $sessionFolder : 'guest');
        $extension = $file->guessExtension() ?: $file->extension() ?: 'bin';
        $filename = sprintf('%s.%s', Str::uuid()->toString(), $extension);
        $path = $file->storeAs($folder, $filename, 'public');

        return response()->json([
            'uploaded' => true,
            'assetId' => $validated['assetId'] ?? null,
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
}
