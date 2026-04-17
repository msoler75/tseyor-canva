<?php

namespace Tests\Feature;

use App\Models\Design;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Inertia\Testing\AssertableInertia as Assert;
use Tests\TestCase;

class DesignerSessionStateTest extends TestCase
{
    use RefreshDatabase;

    public function test_designer_editor_includes_shared_session_state_props(): void
    {
        $user = User::factory()->create();

        $response = $this->actingAs($user)->get('/designer/editor');

        $response->assertOk()->assertInertia(fn (Assert $page) => $page
            ->component('Designer/EditorPage')
            ->has('designer.endpoints.save')
            ->has('designer.endpoints.upload')
            ->where('designer.imageUploads.maxWidth', config('designer.image_uploads.max_width'))
            ->where('designer.imageUploads.maxHeight', config('designer.image_uploads.max_height'))
            ->where('designer.imageUploads.jpegQuality', config('designer.image_uploads.jpeg_quality'))
            ->where('designer.imageUploads.webpQuality', config('designer.image_uploads.webp_quality'))
            ->where('designer.state', null)
        );
    }

    public function test_legacy_assistant_and_export_pages_are_not_routed(): void
    {
        foreach (['objective', 'format', 'content', 'templates', 'export'] as $legacyPage) {
            $this->get("/designer/{$legacyPage}")->assertNotFound();
        }
    }

    public function test_authenticated_autosave_without_design_uuid_does_not_create_design(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)
            ->putJson('/designer/state', ['state' => $this->validDesignerState()])
            ->assertStatus(409)
            ->assertJson(['saved' => false]);

        $this->assertDatabaseCount('designs', 0);
    }

    public function test_create_then_autosave_updates_same_design(): void
    {
        $user = User::factory()->create();
        $clientUuid = (string) Str::uuid();
        $state = $this->validDesignerState([
            'currentDesignUuid' => $clientUuid,
            'designTitle' => 'Diseño único',
            'designTitleManual' => true,
        ]);

        $createResponse = $this->actingAs($user)
            ->postJson('/designer/designs', [
                'name' => 'Diseño único',
                'state' => $state,
            ])
            ->assertCreated();

        $designUuid = $createResponse->json('design.uuid');

        $this->assertSame($clientUuid, $designUuid);
        $this->assertSame($designUuid, $createResponse->json('design.state.currentDesignUuid'));
        $this->assertDatabaseCount('designs', 1);

        $state['currentDesignUuid'] = $designUuid;
        $state['elementLayout']['background']['backgroundColor'] = 'red';

        $this->actingAs($user)
            ->putJson('/designer/state', ['state' => $state])
            ->assertOk()
            ->assertJson([
                'saved' => true,
                'designUuid' => $designUuid,
            ]);

        $this->assertDatabaseCount('designs', 1);
        $this->assertDatabaseHas('designs', [
            'uuid' => $designUuid,
            'name' => 'Diseño único',
        ]);
    }

    public function test_repeated_create_with_same_client_uuid_is_idempotent(): void
    {
        $user = User::factory()->create();
        $clientUuid = (string) Str::uuid();
        $state = $this->validDesignerState([
            'currentDesignUuid' => $clientUuid,
            'designTitle' => 'Primer nombre',
            'designTitleManual' => true,
        ]);

        $this->actingAs($user)
            ->postJson('/designer/designs', [
                'name' => 'Primer nombre',
                'state' => $state,
            ])
            ->assertCreated()
            ->assertJsonPath('design.uuid', $clientUuid);

        $state['designTitle'] = 'Nombre reenviado';

        $this->actingAs($user)
            ->postJson('/designer/designs', [
                'name' => 'Nombre reenviado',
                'state' => $state,
            ])
            ->assertOk()
            ->assertJsonPath('design.uuid', $clientUuid)
            ->assertJsonPath('design.name', 'Nombre reenviado');

        $this->assertDatabaseCount('designs', 1);
    }

    public function test_designer_state_is_loaded_from_persisted_design(): void
    {
        $user = User::factory()->create();
        $pendingDataUrl = 'data:image/png;base64,'.str_repeat('a', 5000);

        $state = [
            'darkMode' => true,
            'mode' => 'guided',
            'objective' => 'event',
            'outputType' => 'print',
            'format' => 'vertical',
            'size' => 'A3 Â· cartel grande',
            'templateCategory' => 'modern',
            'selectedTemplateId' => 'template-1',
            'autosaveMessage' => 'Guardado automÃ¡tico',
            'selectedElementId' => 'title',
            'designTitle' => 'Festival persistido',
            'designTitleManual' => false,
            'currentDesignUuid' => null,
            'content' => [
                'title' => 'Festival persistido',
                'subtitle' => 'SubtÃ­tulo persistido',
                'date' => '25 abril Â· 18:00',
                'location' => 'Plaza Mayor',
                'teacher' => 'MarÃ­a LÃ³pez',
                'price' => 'Entrada gratuita',
                'contact' => 'Info: 600 123 123',
                'extra' => 'Texto persistido',
            ],
            'elementLayout' => [
                'background' => ['backgroundColor' => '#ffffff'],
                'title' => ['x' => 20, 'y' => 60, 'w' => 280, 'fontSize' => 42, 'color' => '#ffffff', 'shadow' => true, 'border' => false],
                'subtitle' => ['x' => 30, 'y' => 180, 'w' => 260, 'fontSize' => 18, 'color' => '#f8fafc', 'shadow' => false, 'border' => false],
                'meta' => ['x' => 36, 'y' => 336, 'w' => 250, 'fontSize' => 16, 'color' => '#ffffff', 'shadow' => false, 'border' => false],
                'contact' => ['x' => 36, 'y' => 368, 'w' => 230, 'fontSize' => 15, 'color' => '#e9d5ff', 'shadow' => false, 'border' => false],
                'extra' => ['x' => 36, 'y' => 410, 'w' => 270, 'fontSize' => 15, 'color' => '#ede9fe', 'shadow' => false, 'border' => false],
                'image-1' => ['x' => 40, 'y' => 96, 'w' => 220, 'h' => 160, 'zIndex' => 60, 'backgroundColor' => '#ffffff'],
            ],
            'customElements' => [
                'image-1' => [
                    'id' => 'image-1',
                    'type' => 'image',
                    'label' => 'Foto principal',
                    'src' => $pendingDataUrl,
                    'assetId' => 'upload-1',
                    'pendingDataUrl' => $pendingDataUrl,
                    'uploadStatus' => 'pending',
                    'needsUpload' => true,
                ],
            ],
            'userUploadedImages' => [
                [
                    'id' => 'upload-1',
                    'assetId' => 'upload-1',
                    'label' => 'foto.png',
                    'src' => $pendingDataUrl,
                    'pendingDataUrl' => $pendingDataUrl,
                    'uploadStatus' => 'pending',
                    'needsUpload' => true,
                ],
            ],
        ];

        $design = Design::query()->create([
            'user_id' => $user->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Festival persistido',
            'name_manual' => false,
            'objective' => 'event',
            'output_type' => 'print',
            'format' => 'vertical',
            'size_label' => 'A3 Â· cartel grande',
            'state' => $state,
            'status' => 'draft',
            'last_opened_at' => now(),
        ]);

        $this->actingAs($user)
            ->get("/designer/designs/{$design->uuid}/edit")
            ->assertOk()
            ->assertInertia(fn (Assert $page) => $page
                ->component('Designer/EditorPage')
                ->where('designer.state.darkMode', true)
                ->where('designer.state.content.title', 'Festival persistido')
                ->where('designer.state.selectedElementId', 'title')
                ->where('designer.state.customElements.image-1.assetId', 'upload-1')
                ->where('designer.state.userUploadedImages.0.pendingDataUrl', $pendingDataUrl)
            );
    }

    public function test_designer_state_allows_replacing_text_with_empty_string(): void
    {
        $user = User::factory()->create();

        $state = [
            'darkMode' => true,
            'mode' => 'guided',
            'objective' => 'event',
            'outputType' => 'print',
            'format' => 'vertical',
            'size' => 'A3 Â· cartel grande',
            'templateCategory' => 'modern',
            'selectedTemplateId' => 'template-1',
            'autosaveMessage' => 'Guardado automÃ¡tico',
            'selectedElementId' => 'title',
            'designTitle' => 'Texto inicial',
            'designTitleManual' => false,
            'currentDesignUuid' => null,
            'content' => [
                'title' => 'Texto inicial',
                'subtitle' => 'Subtitulo',
                'date' => '25 abril',
                'location' => 'Plaza Mayor',
                'teacher' => 'MarÃ­a LÃ³pez',
                'price' => 'Gratis',
                'contact' => 'Info',
                'extra' => 'Extra',
            ],
            'elementLayout' => [
                'background' => ['backgroundColor' => '#ffffff'],
                'title' => [
                    'x' => 20,
                    'y' => 60,
                    'w' => 280,
                    'fontSize' => 42,
                    'color' => '#ffffff',
                    'shadow' => true,
                    'border' => true,
                    'textEffectMode' => 'outline',
                    'contourWidth' => 17,
                    'contourColor' => '#7c3aed',
                ],
                'subtitle' => ['x' => 30, 'y' => 180, 'w' => 260, 'fontSize' => 18, 'color' => '#f8fafc', 'shadow' => false, 'border' => false],
                'meta' => ['x' => 36, 'y' => 336, 'w' => 250, 'fontSize' => 16, 'color' => '#ffffff', 'shadow' => false, 'border' => false],
                'contact' => ['x' => 36, 'y' => 368, 'w' => 230, 'fontSize' => 15, 'color' => '#e9d5ff', 'shadow' => false, 'border' => false],
                'extra' => ['x' => 36, 'y' => 410, 'w' => 270, 'fontSize' => 15, 'color' => '#ede9fe', 'shadow' => false, 'border' => false],
            ],
            'customElements' => [],
            'userUploadedImages' => [],
        ];

        $design = Design::query()->create([
            'user_id' => $user->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Texto inicial',
            'name_manual' => false,
            'objective' => 'event',
            'output_type' => 'print',
            'format' => 'vertical',
            'size_label' => 'A3 Â· cartel grande',
            'state' => $state,
            'status' => 'draft',
            'last_opened_at' => now(),
        ]);

        $state['content']['title'] = '';
        $state['currentDesignUuid'] = $design->uuid;

        $this->actingAs($user)
            ->putJson('/designer/state', ['state' => $state])
            ->assertOk()
            ->assertJson(['saved' => true]);

        $this->actingAs($user)
            ->get("/designer/designs/{$design->uuid}/edit")
            ->assertOk()
            ->assertInertia(fn (Assert $page) => $page
                ->component('Designer/EditorPage')
                ->where('designer.state.content.title', null)
            );
    }

    public function test_designer_upload_endpoint_stores_images_in_session_scoped_public_storage(): void
    {
        Storage::fake('public');
        $user = User::factory()->create();

        $response = $this->actingAs($user)->postJson('/designer/uploads', [
            'assetId' => 'upload-abc',
            'label' => 'cartel.png',
            'file' => UploadedFile::fake()->image('cartel.png', 640, 480),
        ]);

        $response
            ->assertOk()
            ->assertJson([
                'uploaded' => true,
                'label' => 'cartel.png',
            ]);

        $path = $response->json('path');
        $assetId = $response->json('assetId');

        $this->assertNotNull($path);
        $this->assertNotNull($assetId);
        $this->assertStringStartsWith("designer/uploads/users/{$user->id}/", $path);
        Storage::disk('public')->assertExists($path);
        $this->assertStringStartsWith(url('/designer/storage/'), $response->json('url'));

        $this->get($response->json('url'))
            ->assertOk()
            ->assertHeader('content-type', 'image/png');
    }

    /**
     * @param  array<string, mixed>  $overrides
     * @return array<string, mixed>
     */
    private function validDesignerState(array $overrides = []): array
    {
        return [
            'darkMode' => true,
            'mode' => 'guided',
            'objective' => 'event_presential',
            'outputType' => 'print',
            'format' => 'vertical',
            'size' => 'A4',
            'templateCategory' => 'modern',
            'selectedTemplateId' => 'template-1',
            'autosaveMessage' => 'Guardado automático',
            'selectedElementId' => 'title',
            'designTitle' => 'Diseño sin título',
            'designTitleManual' => false,
            'currentDesignUuid' => null,
            'content' => [
                'title' => 'Título',
                'subtitle' => '',
                'date' => '',
                'time' => '',
                'location' => '',
                'platform' => '',
                'teacher' => '',
                'price' => '',
                'contact' => '',
                'extra' => '',
            ],
            'elementLayout' => [
                'background' => ['backgroundColor' => '#ffffff'],
                'title' => ['x' => 20, 'y' => 60, 'w' => 280, 'fontSize' => 42, 'zIndex' => 10],
            ],
            'customElements' => [],
            'userUploadedImages' => [],
            ...$overrides,
        ];
    }
}
