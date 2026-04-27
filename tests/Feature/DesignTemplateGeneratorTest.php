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
}
