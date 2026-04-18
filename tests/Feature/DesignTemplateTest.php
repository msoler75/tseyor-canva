<?php

namespace Tests\Feature;

use App\Models\Design;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Str;
use Tests\TestCase;

class DesignTemplateTest extends TestCase
{
    use RefreshDatabase;

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
                    'plant' => ['x' => 350, 'y' => 350, 'w' => 100, 'h' => 100, 'zIndex' => 10],
                ],
                'customElements' => [
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
        $this->assertEquals(['width' => 1000, 'height' => 500], $state['designSurface']);
        $this->assertEquals(100.0, $state['elementLayout']['title']['x']);
        $this->assertEquals(750.0, $state['elementLayout']['plant']['x']);
        $this->assertSame(10, $state['elementLayout']['plant']['zIndex']);
        $this->assertNotNull($generated->source_template_id);
    }
}
