<?php

namespace Tests\Feature;

use App\Models\Design;
use App\Models\DesignTemplate;
use App\Models\User;
use App\Services\DesignTemplateGenerator;
use Illuminate\Support\Str;
use Tests\TestCase;
use Illuminate\Foundation\Testing\RefreshDatabase;

class DesignTemplateGeneratorTest extends TestCase
{
    use RefreshDatabase;
 
    public function test_apply_template_preserves_existing_texts_on_target_design()
    {
        $user = User::factory()->create();

        // Base design used by the template (visuals)
        $baseDesign = Design::create([
            'user_id' => $user->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Base design',
            'state' => [
                'elementLayout' => [
                    'background' => ['color' => '#ff0000'],
                    'title' => ['x' => 10, 'y' => 20, 'text' => 'Template Title'],
                ],
                'customElements' => [],
                'content' => [],
            ],
        ]);

        $template = DesignTemplate::create([
            'uuid' => (string) Str::uuid(),
            'base_design_id' => $baseDesign->id,
            'title' => 'Sample template',
            'status' => 'published',
            'category_ids' => ['generic'],
            'objective_ids' => ['generic'],
            'field_mappings' => [],
        ]);

        // Target design that already has user-edited texts
        $targetDesign = Design::create([
            'user_id' => $user->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Target design',
            'state' => [
                'elementLayout' => [
                    'title' => ['x' => 5, 'y' => 5, 'text' => 'Old Layout Title'],
                ],
                'customElements' => [],
                'content' => [
                    'title' => 'User Title',
                ],
            ],
        ]);

        $generator = new DesignTemplateGenerator();

        // First application: should preserve existing title
        $design = $generator->generate($template->fresh('baseDesign'), $user, [], null, $targetDesign);
        $fresh = $design->fresh();

        $this->assertEquals($targetDesign->id, $fresh->id);
        $this->assertEquals('User Title', $fresh->state['content']['title'] ?? null);
        $this->assertEquals('User Title', $fresh->state['elementLayout']['title']['text'] ?? null);

        // Simulate a later edit where the persistent layout text is stale again
        $targetDesign->forceFill([
            'state' => [
                'elementLayout' => [
                    'title' => ['x' => 5, 'y' => 5, 'text' => 'Very Old Layout Title'],
                ],
                'customElements' => [],
                'content' => [
                    'title' => 'Assistant Title',
                ],
            ],
        ])->save();

        // If assistant provides a new title in incoming content, it should override any stale layout copy
        $design2 = $generator->generate($template->fresh('baseDesign'), $user, ['content' => ['title' => 'Assistant Title']], null, $targetDesign);
        $fresh2 = $design2->fresh();

        $this->assertEquals('Assistant Title', $fresh2->state['content']['title'] ?? null);
        $this->assertEquals('Assistant Title', $fresh2->state['elementLayout']['title']['text'] ?? null);
    }

    public function test_second_template_application_keeps_current_texts_in_existing_design(): void
    {
        $user = User::factory()->create();

        $baseDesign = Design::create([
            'user_id' => $user->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Base design',
            'state' => [
                'elementLayout' => [
                    'background' => ['color' => '#1d4ed8'],
                    'title' => ['x' => 10, 'y' => 20, 'text' => 'Template Title'],
                ],
                'customElements' => [],
                'content' => [],
            ],
        ]);

        $templateA = DesignTemplate::create([
            'uuid' => (string) Str::uuid(),
            'base_design_id' => $baseDesign->id,
            'title' => 'Template A',
            'status' => 'published',
            'category_ids' => ['generic'],
            'objective_ids' => ['generic'],
            'field_mappings' => [],
        ]);

        $baseDesignB = Design::create([
            'user_id' => $user->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Base design B',
            'state' => [
                'elementLayout' => [
                    'background' => ['color' => '#7c3aed'],
                    'title' => ['x' => 12, 'y' => 24, 'text' => 'Template Title B'],
                ],
                'customElements' => [],
                'content' => [],
            ],
        ]);

        $templateB = DesignTemplate::create([
            'uuid' => (string) Str::uuid(),
            'base_design_id' => $baseDesignB->id,
            'title' => 'Template B',
            'status' => 'published',
            'category_ids' => ['generic'],
            'objective_ids' => ['generic'],
            'field_mappings' => [],
        ]);

        $targetDesign = Design::create([
            'user_id' => $user->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Target design',
            'state' => [
                'stateRevision' => 2,
                'templateRevision' => 1,
                'elementLayout' => [
                    'title' => ['x' => 5, 'y' => 5, 'text' => 'Texto actual'],
                ],
                'customElements' => [],
                'content' => [
                    'title' => 'Texto actual',
                ],
            ],
        ]);

        $generator = new DesignTemplateGenerator();
        $generated = $generator->generate($templateB->fresh('baseDesign'), $user, ['content' => ['title' => 'Texto actual']], null, $targetDesign);
        $fresh = $generated->fresh();

        $this->assertSame('Texto actual', $fresh->state['content']['title'] ?? null);
        $this->assertSame('Texto actual', $fresh->state['elementLayout']['title']['text'] ?? null);
        $this->assertGreaterThan(1, (int) ($fresh->state['templateRevision'] ?? 0));
        $this->assertGreaterThan(1, (int) ($fresh->state['stateRevision'] ?? 0));
    }

    public function test_template_switch_replaces_old_visual_layer_but_keeps_text_elements(): void
    {
        $user = User::factory()->create();

        $baseDesign = Design::create([
            'user_id' => $user->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Visual template',
            'state' => [
                'elementLayout' => [
                    'background' => [
                        'backgroundColor' => '#111827',
                        'backgroundImageSrc' => null,
                    ],
                    'title' => ['x' => 20, 'y' => 30, 'text' => 'Template title', 'color' => '#f8fafc'],
                    'template-shape' => ['x' => 80, 'y' => 90, 'w' => 60, 'h' => 60, 'backgroundColor' => '#38bdf8'],
                    'template-image' => ['x' => 150, 'y' => 160, 'w' => 120, 'h' => 80],
                ],
                'customElements' => [
                    'template-shape' => ['id' => 'template-shape', 'type' => 'shape', 'shapeKind' => 'circle'],
                    'template-image' => ['id' => 'template-image', 'type' => 'image', 'src' => '/template.png'],
                ],
                'content' => [],
                'userUploadedImages' => [],
            ],
        ]);

        $template = DesignTemplate::create([
            'uuid' => (string) Str::uuid(),
            'base_design_id' => $baseDesign->id,
            'title' => 'Visual template',
            'status' => 'published',
            'category_ids' => ['generic'],
            'objective_ids' => ['generic'],
            'field_mappings' => [],
        ]);

        $targetDesign = Design::create([
            'user_id' => $user->id,
            'uuid' => (string) Str::uuid(),
            'name' => 'Target design',
            'state' => [
                'elementLayout' => [
                    'background' => [
                        'backgroundColor' => '#ffffff',
                        'backgroundImageSrc' => '/old-background.png',
                    ],
                    'title' => ['x' => 5, 'y' => 5, 'text' => 'Old title', 'color' => '#0f172a'],
                    'old-shape' => ['x' => 10, 'y' => 10, 'w' => 40, 'h' => 40],
                    'old-image' => ['x' => 50, 'y' => 50, 'w' => 80, 'h' => 80],
                    'user-text' => ['x' => 70, 'y' => 70, 'w' => 180, 'text' => 'Texto libre'],
                ],
                'customElements' => [
                    'old-shape' => ['id' => 'old-shape', 'type' => 'shape', 'shapeKind' => 'rectangle'],
                    'old-image' => ['id' => 'old-image', 'type' => 'image', 'src' => '/old.png'],
                    'user-text' => ['id' => 'user-text', 'type' => 'text', 'text' => 'Texto libre'],
                ],
                'content' => [
                    'title' => 'User title',
                ],
                'userUploadedImages' => [
                    ['id' => 'old-upload', 'src' => '/old-upload.png'],
                ],
            ],
        ]);

        $generator = new DesignTemplateGenerator();
        $design = $generator->generate($template->fresh('baseDesign'), $user, ['content' => ['title' => 'User title']], null, $targetDesign);
        $state = $design->fresh()->state;

        $this->assertSame('#111827', $state['elementLayout']['background']['backgroundColor'] ?? null);
        $this->assertNull($state['elementLayout']['background']['backgroundImageSrc'] ?? null);
        $this->assertArrayNotHasKey('old-shape', $state['elementLayout']);
        $this->assertArrayNotHasKey('old-image', $state['elementLayout']);
        $this->assertArrayNotHasKey('old-shape', $state['customElements']);
        $this->assertArrayNotHasKey('old-image', $state['customElements']);
        $this->assertSame([], $state['userUploadedImages'] ?? null);
        $this->assertArrayHasKey('template-shape', $state['customElements']);
        $this->assertArrayHasKey('template-image', $state['customElements']);
        $this->assertSame('User title', $state['elementLayout']['title']['text'] ?? null);
        $this->assertSame(20, $state['elementLayout']['title']['x'] ?? null);
        $this->assertArrayHasKey('user-text', $state['customElements']);
        $this->assertSame('Texto libre', $state['customElements']['user-text']['text'] ?? null);
    }
}
