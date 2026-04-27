<?php

namespace Tests\Feature;

use App\Models\Design;
use App\Models\DesignTemplate;
use App\Models\User;
use App\Services\DemoTemplateFactory;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Inertia\Testing\AssertableInertia as Assert;
use Tests\TestCase;

class DesignTemplateTest extends TestCase
{
    use RefreshDatabase;

    public function test_console_command_creates_three_generic_demo_templates_idempotently(): void
    {
        Storage::fake('thumbnails');

        $this->assertSame(0, Artisan::call('designer:create-demo-templates'));
        $this->assertSame(0, Artisan::call('designer:create-demo-templates'));

        $templates = DesignTemplate::query()
            ->with('baseDesign')
            ->whereIn('uuid', [
                '51c7d729-9f20-4d3f-9b57-000000000001',
                '51c7d729-9f20-4d3f-9b57-000000000002',
                '51c7d729-9f20-4d3f-9b57-000000000003',
            ])
            ->orderBy('sort_order')
            ->get();

        $this->assertCount(3, $templates);
        $this->assertSame(3, Design::query()->whereIn('uuid', [
            '41c7d729-9f20-4d3f-9b57-000000000001',
            '41c7d729-9f20-4d3f-9b57-000000000002',
            '41c7d729-9f20-4d3f-9b57-000000000003',
        ])->count());

        foreach ($templates as $template) {
            $this->assertSame('published', $template->status);
            $this->assertContains('generic', $template->objective_ids);
            $this->assertNotNull($template->baseDesign);
            $this->assertSame($template->baseDesign->uuid, $template->baseDesign->state['currentDesignUuid']);
            $this->assertArrayHasKey('title', $template->baseDesign->state['elementLayout']);
            $this->assertArrayHasKey('subtitle', $template->baseDesign->state['elementLayout']);
            $this->assertNotNull($template->baseDesign->thumbnail_path);
            Storage::disk('thumbnails')->assertExists($template->baseDesign->thumbnail_path);
        }
    }

    public function test_template_base_design_is_hidden_from_design_list(): void
    {
        $admin = User::factory()->create([
            'name' => 'admin',
            'email' => 'admin@example.com',
        ]);

        $baseDesign = $admin->designs()->create([
            'uuid' => (string) Str::uuid(),
            'name' => 'Base publicada',
            'name_manual' => true,
            'objective' => 'event_presential',
            'output_type' => 'digital',
            'format' => 'square',
            'size_label' => 'Post cuadrado',
            'template_category' => 'modern',
            'state' => $this->validDesignerState('Base publicada'),
            'status' => 'draft',
            'last_opened_at' => now(),
        ]);

        $visibleDesign = $admin->designs()->create([
            'uuid' => (string) Str::uuid(),
            'name' => 'Diseño visible',
            'name_manual' => true,
            'objective' => 'event_presential',
            'output_type' => 'digital',
            'format' => 'square',
            'size_label' => 'Post cuadrado',
            'template_category' => 'modern',
            'state' => $this->validDesignerState('Diseño visible'),
            'status' => 'draft',
            'last_opened_at' => now(),
        ]);

        $this->actingAs($admin)
            ->postJson("/designer/designs/{$baseDesign->uuid}/template", [
                'title' => 'Plantilla publicada',
                'description' => 'Base reutilizable',
                'category_ids' => ['modern'],
                'objective_ids' => ['event_presential'],
                'status' => 'published',
            ])
            ->assertCreated();

        $this->actingAs($admin)
            ->getJson('/designer/designs')
            ->assertOk()
            ->assertJsonCount(1, 'designs')
            ->assertJsonPath('designs.0.uuid', $visibleDesign->uuid);
    }

    public function test_admin_can_publish_template_and_generate_adapted_design(): void
    {
        $admin = User::factory()->create([
            'name' => 'admin',
            'email' => 'admin@example.com',
        ]);

        $baseDesign = $admin->designs()->create([
            'uuid' => (string) Str::uuid(),
            'name' => 'Base maceta',
            'name_manual' => true,
            'objective' => 'event_presential',
            'output_type' => 'digital',
            'format' => 'square',
            'size_label' => 'Post cuadrado',
            'surface_width' => 500,
            'surface_height' => 500,
            'template_category' => 'modern',
            'selected_template_id' => null,
            'state' => [
                'darkMode' => false,
                'mode' => 'guided',
                'objective' => 'event_presential',
                'outputType' => 'digital',
                'format' => 'square',
                'size' => 'Post cuadrado',
                'templateCategory' => 'modern',
                'selectedTemplateId' => null,
                'autosaveMessage' => 'Guardado automático',
                'selectedElementId' => 'title',
                'designTitle' => 'Base maceta',
                'designTitleManual' => true,
                'designSurface' => ['width' => 500, 'height' => 500],
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
                'elementLayout' => [
                    'background' => ['backgroundColor' => '#ffffff'],
                    'title' => ['x' => 50, 'y' => 50, 'w' => 200, 'fontSize' => 40, 'zIndex' => 20],
                    'contact' => ['x' => 50, 'y' => 420, 'w' => 200, 'fontSize' => 16, 'zIndex' => 30],
                    'template-main-title' => ['x' => 70, 'y' => 90, 'w' => 260, 'fontSize' => 34, 'zIndex' => 25],
                    'template-contact-info' => ['x' => 80, 'y' => 380, 'w' => 240, 'fontSize' => 15, 'zIndex' => 26],
                    'plant' => ['x' => 350, 'y' => 350, 'w' => 100, 'h' => 100, 'zIndex' => 10],
                ],
                'customElements' => [
                    'template-main-title' => ['id' => 'template-main-title', 'type' => 'text', 'label' => 'Título principal', 'text' => 'Título de la plantilla'],
                    'template-contact-info' => ['id' => 'template-contact-info', 'type' => 'text', 'label' => 'Datos de contacto', 'text' => 'Contacto base'],
                    'plant' => ['id' => 'plant', 'type' => 'shape', 'label' => 'Maceta', 'shapeKind' => 'circle'],
                ],
                'userUploadedImages' => [],
            ],
            'status' => 'draft',
            'last_opened_at' => now(),
        ]);

        $templateUuid = $this->actingAs($admin)
            ->postJson("/designer/designs/{$baseDesign->uuid}/template", [
                'title' => 'Plantilla maceta',
                'description' => 'Base adaptable',
                'category_ids' => ['modern'],
                'objective_ids' => ['event_presential', 'generic'],
                'field_mappings' => [
                    ['sourceField' => 'datos1', 'targetField' => 'contact'],
                ],
                'status' => 'published',
            ])
            ->assertCreated()
            ->assertJsonPath('template.title', 'Plantilla maceta')
            ->json('template.uuid');

        $response = $this->actingAs($admin)
            ->postJson("/designer/design-templates/{$templateUuid}/generate", [
                'content' => [
                    'title' => 'Encuentro nuevo',
                    'datos1' => 'contacto@example.org',
                ],
                'objective' => 'event_presential',
                'outputType' => 'digital',
                'format' => 'horizontal',
                'size' => 'Banner',
                'designSurface' => ['width' => 1000, 'height' => 500],
            ])
            ->assertCreated()
            ->assertJsonPath('design.name', 'Plantilla maceta personalizado');

        $generated = Design::query()->where('uuid', $response->json('design.uuid'))->firstOrFail();
        $state = $generated->state;

        $this->assertSame('Encuentro nuevo', $state['content']['title']);
        $this->assertSame('contacto@example.org', $state['content']['contact']);
        $this->assertSame('Encuentro nuevo', $state['customElements']['template-main-title']['text']);
        $this->assertSame('contacto@example.org', $state['customElements']['template-contact-info']['text']);
        $this->assertEquals(['width' => 1000, 'height' => 500], $state['designSurface']);
        $this->assertEquals(100.0, $state['elementLayout']['title']['x']);
        $this->assertEquals(750.0, $state['elementLayout']['plant']['x']);
        $this->assertSame(10, $state['elementLayout']['plant']['zIndex']);
        $this->assertSame($templateUuid, $generated->selected_template_id);
    }

    public function test_template_inventory_uses_thumbnail_route_for_demo_templates(): void
    {
        Storage::fake('thumbnails');

        app(DemoTemplateFactory::class)->create();

        $admin = User::query()->where('email', 'admin@example.com')->firstOrFail();

        $this->actingAs($admin)
            ->get('/designer/template-inventory')
            ->assertOk()
            ->assertInertia(fn (Assert $page) => $page
                ->component('Designer/Templates/Index')
                ->where('templates.0.thumbnail_url', fn ($url) => is_string($url)
                    && str_contains($url, '/designer/storage/thumbnails/')
                    && str_contains($url, 'v='))
            );
    }

    /**
     * @return array<string, mixed>
     */
    private function validDesignerState(string $title): array
    {
        return [
            'darkMode' => false,
            'mode' => 'guided',
            'objective' => 'event_presential',
            'outputType' => 'digital',
            'format' => 'square',
            'size' => 'Post cuadrado',
            'templateCategory' => 'modern',
            'selectedTemplateId' => null,
            'autosaveMessage' => 'Guardado automático',
            'selectedElementId' => 'title',
            'designTitle' => $title,
            'designTitleManual' => true,
            'designSurface' => ['width' => 500, 'height' => 500],
            'content' => [
                'title' => $title,
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
                'title' => ['x' => 50, 'y' => 50, 'w' => 200, 'fontSize' => 40, 'zIndex' => 20],
            ],
            'customElements' => [],
            'userUploadedImages' => [],
        ];
    }
}
