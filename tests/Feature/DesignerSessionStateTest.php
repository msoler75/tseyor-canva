<?php

namespace Tests\Feature;

use Inertia\Testing\AssertableInertia as Assert;
use Tests\TestCase;

class DesignerSessionStateTest extends TestCase
{
    public function test_designer_pages_include_shared_session_state_props(): void
    {
        $response = $this->get('/designer/content');

        $response->assertOk()->assertInertia(fn (Assert $page) => $page
            ->component('Designer/ContentPage')
            ->has('designer.endpoints.save')
            ->where('designer.state', null)
        );
    }

    public function test_designer_state_is_persisted_in_session_and_rehydrated(): void
    {
        $payload = [
            'state' => [
                'darkMode' => true,
                'mode' => 'guided',
                'objective' => 'event',
                'outputType' => 'print',
                'format' => 'vertical',
                'size' => 'A3 · cartel grande',
                'templateCategory' => 'modern',
                'selectedTemplateId' => 'template-1',
                'autosaveMessage' => 'Guardado automático',
                'selectedElementId' => 'title',
                'content' => [
                    'title' => 'Festival persistido',
                    'subtitle' => 'Subtítulo persistido',
                    'date' => '25 abril · 18:00',
                    'location' => 'Plaza Mayor',
                    'teacher' => 'María López',
                    'price' => 'Entrada gratuita',
                    'contact' => 'Info: 600 123 123',
                    'extra' => 'Texto persistido',
                ],
                'elementLayout' => [
                    'title' => ['x' => 20, 'y' => 60, 'w' => 280, 'fontSize' => 42, 'color' => '#ffffff', 'shadow' => true, 'border' => false],
                    'subtitle' => ['x' => 30, 'y' => 180, 'w' => 260, 'fontSize' => 18, 'color' => '#f8fafc', 'shadow' => false, 'border' => false],
                    'meta' => ['x' => 36, 'y' => 336, 'w' => 250, 'fontSize' => 16, 'color' => '#ffffff', 'shadow' => false, 'border' => false],
                    'contact' => ['x' => 36, 'y' => 368, 'w' => 230, 'fontSize' => 15, 'color' => '#e9d5ff', 'shadow' => false, 'border' => false],
                    'extra' => ['x' => 36, 'y' => 410, 'w' => 270, 'fontSize' => 15, 'color' => '#ede9fe', 'shadow' => false, 'border' => false],
                ],
            ],
        ];

        $this->putJson('/designer/state', $payload)
            ->assertOk()
            ->assertJson(['saved' => true]);

        $this->assertEquals(
            'Festival persistido',
            session('designer.state.content.title')
        );

        $this->get('/designer/editor')
            ->assertOk()
            ->assertInertia(fn (Assert $page) => $page
                ->component('Designer/EditorPage')
                ->where('designer.state.darkMode', true)
                ->where('designer.state.content.title', 'Festival persistido')
                ->where('designer.state.selectedElementId', 'title')
            );
    }

    public function test_designer_state_allows_replacing_text_with_empty_string(): void
    {
        $state = [
            'darkMode' => true,
            'mode' => 'guided',
            'objective' => 'event',
            'outputType' => 'print',
            'format' => 'vertical',
            'size' => 'A3 · cartel grande',
            'templateCategory' => 'modern',
            'selectedTemplateId' => 'template-1',
            'autosaveMessage' => 'Guardado automático',
            'selectedElementId' => 'title',
            'content' => [
                'title' => 'Texto inicial',
                'subtitle' => 'Subtitulo',
                'date' => '25 abril',
                'location' => 'Plaza Mayor',
                'teacher' => 'María López',
                'price' => 'Gratis',
                'contact' => 'Info',
                'extra' => 'Extra',
            ],
            'elementLayout' => [
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
        ];

        $this->putJson('/designer/state', ['state' => $state])->assertOk();

        $state['content']['title'] = '';

        $this->putJson('/designer/state', ['state' => $state])
            ->assertOk()
            ->assertJson(['saved' => true]);

        $this->get('/designer/editor')
            ->assertOk()
            ->assertInertia(fn (Assert $page) => $page
                ->component('Designer/EditorPage')
                ->where('designer.state.content.title', null)
            );
    }
}
