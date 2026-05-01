<?php

namespace Tests\Feature;

use App\Models\Design;
use App\Models\DesignTemplate;
use App\Models\User;
use App\Http\Controllers\DesignerController;
use Firebase\JWT\JWT;
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

    public function test_incomplete_autosave_does_not_overwrite_existing_design(): void
    {
        $user = User::factory()->create();
        $state = $this->validDesignerState([
            'designTitle' => 'Estado completo',
            'designTitleManual' => true,
        ]);

        $design = Design::query()->create([
            'user_id' => $user->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Estado completo',
            'name_manual' => true,
            'objective' => 'event_presential',
            'output_type' => 'print',
            'format' => 'vertical',
            'size_label' => 'A4',
            'state' => [
                ...$state,
                'currentDesignUuid' => null,
            ],
            'status' => 'draft',
            'last_opened_at' => now(),
        ]);

        $partialState = $this->validDesignerState([
            'currentDesignUuid' => $design->uuid,
            'elementLayout' => [
                'background' => ['backgroundColor' => '#ffffff'],
            ],
        ]);

        $this->actingAs($user)
            ->putJson('/designer/state', ['state' => $partialState])
            ->assertStatus(422)
            ->assertJson(['saved' => false]);

        $design->refresh();
        $this->assertSame('Estado completo', $design->name);
        $this->assertSame('Título', $design->state['content']['title']);
        $this->assertArrayHasKey('title', $design->state['elementLayout']);
    }

    public function test_autosave_persists_deleted_title_element_when_title_content_is_empty(): void
    {
        $user = User::factory()->create();
        $state = $this->validDesignerState([
            'designTitle' => 'Estado con título borrado',
            'designTitleManual' => true,
        ]);

        $design = Design::query()->create([
            'user_id' => $user->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Estado con título borrado',
            'name_manual' => true,
            'objective' => 'event_presential',
            'output_type' => 'print',
            'format' => 'vertical',
            'size_label' => 'A4',
            'state' => [
                ...$state,
                'currentDesignUuid' => null,
            ],
            'status' => 'draft',
            'last_opened_at' => now(),
        ]);

        $state['currentDesignUuid'] = $design->uuid;
        $state['content']['title'] = '';
        unset($state['elementLayout']['title']);

        $this->actingAs($user)
            ->putJson('/designer/state', ['state' => $state])
            ->assertOk()
            ->assertJson([
                'saved' => true,
                'designUuid' => $design->uuid,
            ]);

        $design->refresh();
        $this->assertSame('', $design->state['content']['title']);
        $this->assertArrayNotHasKey('title', $design->state['elementLayout']);
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

    public function test_guest_create_design_replaces_editor_session_state(): void
    {
        $staleState = $this->validDesignerState([
            'currentDesignUuid' => (string) Str::uuid(),
            'designTitle' => 'Diseño anterior',
            'content' => [
                'title' => 'Diseño anterior',
                'subtitle' => 'Memoria vieja',
                'date' => '',
                'time' => '',
                'location' => '',
                'platform' => '',
                'teacher' => '',
                'price' => '',
                'contact' => '',
                'extra' => '',
            ],
        ]);

        $freshUuid = (string) Str::uuid();
        $freshState = $this->validDesignerState([
            'currentDesignUuid' => $freshUuid,
            'selectedTemplateId' => null,
            'designTitle' => 'Cartel nuevo',
            'designTitleManual' => true,
            'content' => [
                'title' => 'Cartel nuevo',
                'subtitle' => 'Con datos del asistente',
                'date' => '27 abril',
                'time' => '19:00',
                'location' => 'Plaza Mayor',
                'platform' => '',
                'teacher' => '',
                'price' => 'Gratis',
                'contact' => 'hola@example.com',
                'extra' => 'Trae a tus amigos',
            ],
        ]);

        $response = $this->withSession([DesignerController::sessionKey() => $staleState])
            ->postJson('/designer/designs', [
                'name' => 'Cartel nuevo',
                'state' => $freshState,
            ])
            ->assertCreated()
            ->assertJsonPath('design.uuid', $freshUuid)
            ->assertJsonPath('design.state.content.title', 'Cartel nuevo')
            ->assertJsonPath('design.state.content.subtitle', 'Con datos del asistente')
            ->assertJsonPath('design.state.selectedTemplateId', null)
            ->assertJsonPath('design.state.elementLayout.title.text', 'Cartel nuevo');

        $persistedState = $response->json('design.state');

        $this->assertSame('Cartel nuevo', session(DesignerController::sessionKey().'.content.title'));
        $this->assertSame('Con datos del asistente', session(DesignerController::sessionKey().'.content.subtitle'));
        $this->assertSame('Cartel nuevo', session(DesignerController::sessionKey().'.elementLayout.title.text'));

        $this->withSession([DesignerController::sessionKey() => $persistedState])
            ->get('/designer/editor')
            ->assertOk()
            ->assertInertia(fn (Assert $page) => $page
                ->component('Designer/EditorPage')
                ->where('designer.state.currentDesignUuid', $freshUuid)
                ->where('designer.state.designTitle', 'Cartel nuevo')
                ->where('designer.state.content.title', 'Cartel nuevo')
                ->where('designer.state.content.subtitle', 'Con datos del asistente')
                ->where('designer.state.content.location', 'Plaza Mayor')
                ->where('designer.state.selectedTemplateId', null)
            );
    }

    public function test_designer_state_is_loaded_from_persisted_design(): void
    {
        $user = User::factory()->create();
        $pendingDataUrl = 'data:image/png;base64,'.str_repeat('a', 5000);

        $state = [
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
                ->where('designer.state.content.title', '')
            );
    }


    public function test_stale_save_requests_do_not_overwrite_newer_state(): void
    {
        $user = User::factory()->create();

        $design = Design::query()->create([
            'user_id' => $user->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Revision test',
            'name_manual' => true,
            'objective' => 'event',
            'output_type' => 'digital',
            'format' => 'square',
            'size_label' => 'Post cuadrado',
            'state' => [
                'mode' => 'guided',
                'stateRevision' => 2,
                'objective' => 'event',
                'outputType' => 'digital',
                'format' => 'square',
                'size' => 'Post cuadrado',
                'templateCategory' => 'all',
                'selectedTemplateId' => null,
                'autosaveMessage' => 'Guardado autom?tico',
                'selectedElementId' => 'title',
                'designTitle' => 'Revision test',
                'designTitleManual' => true,
                'currentDesignUuid' => null,
                'designSurface' => ['width' => 500, 'height' => 500],
                'content' => [
                    'title' => 'Texto nuevo',
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
                    'title' => ['x' => 50, 'y' => 50, 'w' => 200, 'fontSize' => 40, 'zIndex' => 20, 'text' => 'Texto nuevo'],
                ],
                'customElements' => [],
                'userUploadedImages' => [],
            ],
            'status' => 'draft',
            'last_opened_at' => now(),
        ]);

        $staleState = $design->state;
        $staleState['stateRevision'] = 1;
        $staleState['content']['title'] = 'Texto viejo';
        $staleState['elementLayout']['title']['text'] = 'Texto viejo';
        $staleState['currentDesignUuid'] = $design->uuid;

        $this->actingAs($user)
            ->putJson('/designer/state', ['state' => $staleState])
            ->assertOk()
            ->assertJsonPath('ignored', true);

        $fresh = $design->fresh();
        $this->assertSame('Texto nuevo', $fresh->state['content']['title']);
        $this->assertSame('Texto nuevo', $fresh->state['elementLayout']['title']['text']);
        $this->assertSame(2, $fresh->state['stateRevision']);
    }
    public function test_designer_upload_endpoint_stores_images_in_user_scoped_storage(): void
    {
        Storage::fake('users');
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
        $this->assertStringStartsWith("{$user->id}/", $path);
        Storage::disk('users')->assertExists($path);
        $this->assertStringStartsWith(url('/designer/storage/uploads/'), $response->json('url'));
        $this->assertStringContainsString('v=', $response->json('url'));

        $this->get($response->json('url'))
            ->assertOk()
            ->assertHeader('content-type', 'image/png');
    }

    public function test_assets_index_returns_versioned_upload_urls(): void
    {
        Storage::fake('users');
        $user = User::factory()->create();

        Storage::disk('users')->put("{$user->id}/asset-demo.png", 'fake-image');

        $asset = $user->designAssets()->create([
            'uuid' => (string) Str::uuid(),
            'label' => 'Asset demo',
            'disk' => 'users',
            'path' => "{$user->id}/asset-demo.png",
            'mime_type' => 'image/png',
            'extension' => 'png',
            'size_bytes' => 10,
            'uploaded_at' => now(),
        ]);

        $this->actingAs($user)
            ->getJson('/designer/assets')
            ->assertOk()
            ->assertJsonPath('assets.0.id', $asset->id)
            ->assertJsonPath('assets.0.path', "{$user->id}/asset-demo.png")
            ->assertJsonPath('assets.0.url', fn ($url) => is_string($url)
                && str_contains($url, '/designer/storage/uploads/')
                && str_contains($url, 'v='));
    }

    public function test_home_hides_designs_used_as_template_bases(): void
    {
        $user = User::factory()->create();

        Design::query()->create([
            'user_id' => $user->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Diseño normal',
            'state' => $this->validDesignerState([
                'currentDesignUuid' => (string) Str::uuid(),
            ]),
            'status' => 'draft',
            'last_opened_at' => now(),
        ]);

        $base = Design::query()->create([
            'user_id' => $user->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Base plantilla',
            'state' => $this->validDesignerState([
                'currentDesignUuid' => (string) Str::uuid(),
            ]),
            'status' => 'draft',
            'last_opened_at' => now(),
        ]);

        DesignTemplate::query()->create([
            'uuid' => (string) Str::uuid(),
            'base_design_id' => $base->id,
            'title' => 'Plantilla desde base',
            'description' => null,
            'category_ids' => ['general'],
            'objective_ids' => ['generic'],
            'adaptation_mode' => 'proportional',
            'field_mappings' => null,
            'status' => 'published',
            'featured' => false,
            'sort_order' => 0,
            'published_at' => now(),
        ]);

        $this->actingAs($user)
            ->get('/')
            ->assertOk()
            ->assertInertia(fn (Assert $page) => $page
                ->component('Home')
                ->has('designs', 1)
                ->where('designs.0.name', 'Diseño normal')
            );
    }

    public function test_home_exposes_versioned_session_thumbnail_url(): void
    {
        $state = $this->validDesignerState([
            'currentDesignUuid' => (string) Str::uuid(),
            'thumbnail_path' => 'demo-thumb.svg',
            'thumbnail_version' => 'thumb-version-123',
        ]);

        $this->withSession([DesignerController::sessionKey() => $state])
            ->get('/')
            ->assertOk()
            ->assertInertia(fn (Assert $page) => $page
                ->component('Home')
                ->where('sessionDesign.thumbnail_url', fn ($url) => is_string($url)
                    && str_contains($url, '/designer/storage/thumbnails/demo-thumb.svg')
                    && str_contains($url, 'v=thumb-version-123'))
            );
    }

    public function test_home_shows_latest_templates_only_for_admin(): void
    {
        $admin = User::factory()->create(['name' => 'admin']);
        $base = Design::query()->create([
            'user_id' => $admin->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Base admin',
            'state' => $this->validDesignerState([
                'currentDesignUuid' => (string) Str::uuid(),
            ]),
            'status' => 'draft',
            'last_opened_at' => now(),
        ]);

        DesignTemplate::query()->create([
            'uuid' => (string) Str::uuid(),
            'base_design_id' => $base->id,
            'title' => 'Plantilla admin',
            'description' => null,
            'category_ids' => ['general'],
            'objective_ids' => ['generic'],
            'adaptation_mode' => 'proportional',
            'field_mappings' => null,
            'status' => 'published',
            'featured' => false,
            'sort_order' => 0,
            'published_at' => now(),
        ]);

        $this->actingAs($admin)
            ->get('/')
            ->assertOk()
            ->assertInertia(fn (Assert $page) => $page
                ->component('Home')
                ->has('adminTemplates', 1)
                ->where('adminTemplates.0.name', 'Plantilla admin')
            );

        $user = User::factory()->create();

        $this->actingAs($user)
            ->get('/')
            ->assertOk()
            ->assertInertia(fn (Assert $page) => $page
                ->component('Home')
                ->where('adminTemplates', [])
            );
    }

    public function test_editor_marks_opened_template_base_design(): void
    {
        $admin = User::factory()->create(['name' => 'admin']);
        $base = Design::query()->create([
            'user_id' => $admin->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Base editable',
            'state' => $this->validDesignerState([
                'currentDesignUuid' => null,
            ]),
            'status' => 'draft',
            'last_opened_at' => now(),
        ]);

        $template = DesignTemplate::query()->create([
            'uuid' => (string) Str::uuid(),
            'base_design_id' => $base->id,
            'title' => 'Plantilla editable',
            'description' => null,
            'category_ids' => ['general'],
            'objective_ids' => ['generic'],
            'adaptation_mode' => 'proportional',
            'field_mappings' => null,
            'status' => 'published',
            'featured' => false,
            'sort_order' => 0,
            'published_at' => now(),
        ]);

        $this->actingAs($admin)
            ->get("/designer/designs/{$base->uuid}/edit")
            ->assertOk()
            ->assertInertia(fn (Assert $page) => $page
                ->component('Designer/EditorPage')
                ->where('designer.currentDesign.uuid', $base->uuid)
                ->where('designer.state.currentDesignUuid', $base->uuid)
                ->where('designer.isTemplateBaseEditor', true)
                ->where('designer.currentTemplate.uuid', $template->uuid)
                ->where('designer.currentDesign.baseTemplate.uuid', $template->uuid)
                ->where('designer.currentDesign.baseTemplate.base_design_uuid', $base->uuid)
            );
    }

    public function test_admin_opens_foreign_template_base_without_creating_copy(): void
    {
        $owner = User::factory()->create(['name' => 'template-owner']);
        $admin = User::factory()->create(['name' => 'admin']);
        $base = Design::query()->create([
            'user_id' => $owner->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Base de otro propietario',
            'state' => $this->validDesignerState([
                'currentDesignUuid' => null,
            ]),
            'status' => 'draft',
            'last_opened_at' => now(),
        ]);

        $template = DesignTemplate::query()->create([
            'uuid' => (string) Str::uuid(),
            'base_design_id' => $base->id,
            'title' => 'Plantilla de otro propietario',
            'description' => null,
            'category_ids' => ['general'],
            'objective_ids' => ['generic'],
            'adaptation_mode' => 'proportional',
            'field_mappings' => null,
            'status' => 'published',
            'featured' => false,
            'sort_order' => 0,
            'published_at' => now(),
        ]);

        $this->actingAs($admin)
            ->get("/designer/designs/{$base->uuid}/edit")
            ->assertOk()
            ->assertInertia(fn (Assert $page) => $page
                ->component('Designer/EditorPage')
                ->where('designer.currentDesign.uuid', $base->uuid)
                ->where('designer.isTemplateBaseEditor', true)
                ->where('designer.currentTemplate.uuid', $template->uuid)
            );

        $this->assertDatabaseCount('designs', 1);
    }

    public function test_non_admin_owner_cannot_open_template_base_design(): void
    {
        $owner = User::factory()->create(['name' => 'editor']);
        $base = Design::query()->create([
            'user_id' => $owner->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Base restringida',
            'state' => $this->validDesignerState([
                'currentDesignUuid' => null,
            ]),
            'status' => 'draft',
            'last_opened_at' => now(),
        ]);

        DesignTemplate::query()->create([
            'uuid' => (string) Str::uuid(),
            'base_design_id' => $base->id,
            'title' => 'Plantilla restringida',
            'description' => null,
            'category_ids' => ['general'],
            'objective_ids' => ['generic'],
            'adaptation_mode' => 'proportional',
            'field_mappings' => null,
            'status' => 'published',
            'featured' => false,
            'sort_order' => 0,
            'published_at' => now(),
        ]);

        $this->actingAs($owner)
            ->get("/designer/designs/{$base->uuid}/edit")
            ->assertForbidden();
    }

    public function test_non_admin_foreign_user_cannot_open_or_copy_template_base_design(): void
    {
        $owner = User::factory()->create(['name' => 'template-owner']);
        $viewer = User::factory()->create(['name' => 'viewer']);
        $base = Design::query()->create([
            'user_id' => $owner->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Base bloqueada',
            'state' => $this->validDesignerState([
                'currentDesignUuid' => null,
            ]),
            'status' => 'draft',
            'last_opened_at' => now(),
        ]);

        DesignTemplate::query()->create([
            'uuid' => (string) Str::uuid(),
            'base_design_id' => $base->id,
            'title' => 'Plantilla bloqueada',
            'description' => null,
            'category_ids' => ['general'],
            'objective_ids' => ['generic'],
            'adaptation_mode' => 'proportional',
            'field_mappings' => null,
            'status' => 'published',
            'featured' => false,
            'sort_order' => 0,
            'published_at' => now(),
        ]);

        $this->actingAs($viewer)
            ->get("/designer/designs/{$base->uuid}/edit")
            ->assertForbidden();

        $this->assertDatabaseCount('designs', 1);
    }

    public function test_guest_template_generation_is_loaded_in_editor(): void
    {
        $admin = User::factory()->create(['name' => 'admin']);
        $base = Design::query()->create([
            'user_id' => $admin->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Base pública',
            'name_manual' => true,
            'objective' => 'event_presential',
            'output_type' => 'digital',
            'format' => 'square',
            'size_label' => 'Post cuadrado',
            'surface_width' => 500,
            'surface_height' => 500,
            'template_category' => 'modern',
            'state' => $this->validDesignerState([
                'designTitle' => 'Base pública',
                'designTitleManual' => true,
                'selectedTemplateId' => null,
                'currentDesignUuid' => null,
                'content' => [
                    'title' => 'Título base',
                    'subtitle' => 'Subtítulo base',
                    'date' => '',
                    'time' => '',
                    'location' => '',
                    'platform' => '',
                    'teacher' => '',
                    'price' => '',
                    'contact' => '',
                    'extra' => '',
                ],
            ]),
            'status' => 'draft',
            'last_opened_at' => now(),
        ]);

        $template = DesignTemplate::query()->create([
            'uuid' => (string) Str::uuid(),
            'base_design_id' => $base->id,
            'title' => 'Plantilla pública',
            'description' => 'Plantilla para invitado',
            'category_ids' => ['modern'],
            'objective_ids' => ['generic', 'event_presential'],
            'adaptation_mode' => 'proportional',
            'field_mappings' => [
                ['sourceField' => 'title', 'targetField' => 'title', 'elementId' => 'title', 'property' => 'text'],
                ['sourceField' => 'subtitle', 'targetField' => 'subtitle', 'elementId' => 'subtitle', 'property' => 'text'],
            ],
            'status' => 'published',
            'featured' => false,
            'sort_order' => 0,
            'published_at' => now(),
        ]);

        $response = $this->postJson("/designer/design-templates/{$template->uuid}/generate", [
            'content' => [
                'title' => 'Cartel invitado',
                'subtitle' => 'Generado con plantilla',
                'location' => 'Biblioteca',
            ],
            'objective' => 'event_presential',
            'outputType' => 'digital',
            'format' => 'square',
            'size' => 'Post cuadrado',
            'designSurface' => ['width' => 500, 'height' => 500],
        ])->assertCreated();

        $state = $response->json('design.state');

        $this->withSession([DesignerController::sessionKey() => $state])
            ->get('/designer/editor')
            ->assertOk()
            ->assertInertia(fn (Assert $page) => $page
                ->component('Designer/EditorPage')
                ->where('designer.state.selectedTemplateId', $template->uuid)
                ->where('designer.state.content.title', 'Cartel invitado')
                ->where('designer.state.content.subtitle', 'Generado con plantilla')
                ->where('designer.state.designTitle', 'Plantilla pública personalizado')
            );
    }

    public function test_guest_second_template_generation_keeps_current_texts_in_session_state(): void
    {
        $admin = User::factory()->create(['name' => 'admin']);

        $baseA = Design::query()->create([
            'user_id' => $admin->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Base A',
            'name_manual' => true,
            'objective' => 'event_presential',
            'output_type' => 'digital',
            'format' => 'square',
            'size_label' => 'Post cuadrado',
            'surface_width' => 500,
            'surface_height' => 500,
            'template_category' => 'modern',
            'state' => $this->validDesignerState([
                'designTitle' => 'Base A',
                'designTitleManual' => true,
                'content' => [
                    'title' => 'Texto base A',
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
                    'title' => ['x' => 20, 'y' => 60, 'w' => 280, 'fontSize' => 42, 'zIndex' => 10, 'text' => 'Texto base A'],
                ],
            ]),
            'status' => 'draft',
            'last_opened_at' => now(),
        ]);

        $templateA = DesignTemplate::query()->create([
            'uuid' => (string) Str::uuid(),
            'base_design_id' => $baseA->id,
            'title' => 'Plantilla A',
            'description' => 'Primera plantilla',
            'category_ids' => ['modern'],
            'objective_ids' => ['generic'],
            'adaptation_mode' => 'proportional',
            'field_mappings' => [
                ['sourceField' => 'title', 'targetField' => 'title', 'elementId' => 'title', 'property' => 'text'],
            ],
            'status' => 'published',
            'featured' => false,
            'sort_order' => 0,
            'published_at' => now(),
        ]);

        $baseB = Design::query()->create([
            'user_id' => $admin->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Base B',
            'name_manual' => true,
            'objective' => 'event_presential',
            'output_type' => 'digital',
            'format' => 'square',
            'size_label' => 'Post cuadrado',
            'surface_width' => 500,
            'surface_height' => 500,
            'template_category' => 'modern',
            'state' => $this->validDesignerState([
                'designTitle' => 'Base B',
                'designTitleManual' => true,
                'content' => [
                    'title' => 'Texto base B',
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
                    'background' => ['backgroundColor' => '#7c3aed'],
                    'title' => ['x' => 120, 'y' => 90, 'w' => 220, 'fontSize' => 30, 'zIndex' => 10, 'text' => 'Texto base B'],
                ],
            ]),
            'status' => 'draft',
            'last_opened_at' => now(),
        ]);

        $templateB = DesignTemplate::query()->create([
            'uuid' => (string) Str::uuid(),
            'base_design_id' => $baseB->id,
            'title' => 'Plantilla B',
            'description' => 'Segunda plantilla',
            'category_ids' => ['modern'],
            'objective_ids' => ['generic'],
            'adaptation_mode' => 'proportional',
            'field_mappings' => [
                ['sourceField' => 'title', 'targetField' => 'title', 'elementId' => 'title', 'property' => 'text'],
            ],
            'status' => 'published',
            'featured' => false,
            'sort_order' => 0,
            'published_at' => now(),
        ]);

        $firstResponse = $this->postJson("/designer/design-templates/{$templateA->uuid}/generate", [
            'content' => [
                'title' => 'Título actual',
            ],
            'objective' => 'event_presential',
            'outputType' => 'digital',
            'format' => 'square',
            'size' => 'Post cuadrado',
            'designSurface' => ['width' => 500, 'height' => 500],
        ])->assertCreated();

        $sessionState = $firstResponse->json('design.state');
        $sessionState['content']['title'] = 'Título actual';
        $sessionState['elementLayout']['title']['text'] = 'Título actual';
        $sessionState['stateRevision'] = 2;
        $sessionState['templateRevision'] = 1;

        $secondResponse = $this->withSession([
            DesignerController::sessionKey() => $sessionState,
        ])->postJson("/designer/design-templates/{$templateB->uuid}/generate", [
            'content' => [
                'title' => 'Título actual',
            ],
            'objective' => 'event_presential',
            'outputType' => 'digital',
            'format' => 'square',
            'size' => 'Post cuadrado',
            'designSurface' => ['width' => 500, 'height' => 500],
        ])->assertCreated();

        $secondState = $secondResponse->json('design.state');

        $this->assertSame('Título actual', $secondState['content']['title'] ?? null);
        $this->assertSame('Título actual', $secondState['elementLayout']['title']['text'] ?? null);
        $this->assertSame('#7c3aed', $secondState['elementLayout']['background']['backgroundColor'] ?? null);
        $this->assertSame(120, $secondState['elementLayout']['title']['x'] ?? null);
        $this->assertGreaterThan(1, (int) ($secondState['templateRevision'] ?? 0));
    }

    public function test_guest_template_generation_prefers_client_snapshot_over_stale_session_state(): void
    {
        $admin = User::factory()->create(['name' => 'admin']);

        $base = Design::query()->create([
            'user_id' => $admin->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Base snapshot',
            'name_manual' => true,
            'objective' => 'event_presential',
            'output_type' => 'digital',
            'format' => 'square',
            'size_label' => 'Post cuadrado',
            'surface_width' => 500,
            'surface_height' => 500,
            'template_category' => 'modern',
            'state' => $this->validDesignerState([
                'designTitle' => 'Base snapshot',
                'designTitleManual' => true,
                'content' => [
                    'title' => 'Título base',
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
            ]),
            'status' => 'draft',
            'last_opened_at' => now(),
        ]);

        $template = DesignTemplate::query()->create([
            'uuid' => (string) Str::uuid(),
            'base_design_id' => $base->id,
            'title' => 'Plantilla snapshot',
            'description' => 'Prueba snapshot',
            'category_ids' => ['modern'],
            'objective_ids' => ['generic'],
            'adaptation_mode' => 'proportional',
            'field_mappings' => [
                ['sourceField' => 'title', 'targetField' => 'title', 'elementId' => 'title', 'property' => 'text'],
            ],
            'status' => 'published',
            'featured' => false,
            'sort_order' => 0,
            'published_at' => now(),
        ]);

        $staleSession = $this->validDesignerState([
            'currentDesignUuid' => (string) Str::uuid(),
            'selectedTemplateId' => null,
            'designTitle' => 'Estado viejo',
            'content' => [
                'title' => 'Título original',
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
                'title' => ['x' => 50, 'y' => 50, 'w' => 200, 'fontSize' => 40, 'zIndex' => 20, 'text' => 'Título original'],
            ],
        ]);

        $clientSnapshot = $staleSession;
        $clientSnapshot['content']['title'] = 'Título actual';
        $clientSnapshot['elementLayout']['title']['text'] = 'Título actual';
        $clientSnapshot['stateRevision'] = 4;
        $clientSnapshot['templateRevision'] = 2;

        $response = $this->withSession([
            DesignerController::sessionKey() => $staleSession,
        ])->postJson("/designer/design-templates/{$template->uuid}/generate", [
            'designerState' => $clientSnapshot,
            'content' => [
                'title' => 'Título actual',
            ],
            'objective' => 'event_presential',
            'outputType' => 'digital',
            'format' => 'square',
            'size' => 'Post cuadrado',
            'designSurface' => ['width' => 500, 'height' => 500],
        ])->assertCreated();

        $state = $response->json('design.state');

        $this->assertSame('Título actual', $state['content']['title'] ?? null);
        $this->assertSame('Título actual', $state['elementLayout']['title']['text'] ?? null);
    }

    public function test_guest_design_is_recovered_after_login_from_editor(): void
    {
        $sessionState = $this->validDesignerState([
            'currentDesignUuid' => (string) Str::uuid(),
            'selectedTemplateId' => (string) Str::uuid(),
            'designTitle' => 'Diseño invitado',
            'content' => [
                'title' => 'Diseño invitado',
                'subtitle' => 'Pendiente de recuperar',
                'date' => '',
                'time' => '',
                'location' => 'Centro cultural',
                'platform' => '',
                'teacher' => '',
                'price' => '',
                'contact' => '',
                'extra' => '',
            ],
        ]);

        $token = JWT::encode([
            'email' => 'guest-recovered@example.com',
            'name' => 'Recovered Guest',
            'image' => '',
            'exp' => now()->addHour()->timestamp,
        ], (string) config('jwt.secret'), 'HS256');

        $response = $this->withSession([DesignerController::sessionKey() => $sessionState])
            ->get('/auth/login?from_editor=1&token='.$token);

        $user = User::query()->where('email', 'guest-recovered@example.com')->firstOrFail();
        $design = Design::query()->where('user_id', $user->id)->firstOrFail();

        $response->assertRedirect("/designer/designs/{$design->uuid}/edit");
        $this->assertSame('Diseño invitado', $design->name);
        $this->assertSame('Diseño invitado', $design->state['content']['title'] ?? null);
        $this->assertSame('Centro cultural', $design->state['content']['location'] ?? null);
    }

    /**
     * @param  array<string, mixed>  $overrides
     * @return array<string, mixed>
     */
    private function validDesignerState(array $overrides = []): array
    {
        return [
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
