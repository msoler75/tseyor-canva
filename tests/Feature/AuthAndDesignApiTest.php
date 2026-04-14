<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class AuthAndDesignApiTest extends TestCase
{
    use RefreshDatabase;

    public function test_user_can_login_and_receive_jwt_token(): void
    {
        $user = User::factory()->create([
            'email' => 'designer@example.com',
            'password' => 'secret123',
        ]);

        $response = $this->postJson('/auth/login', [
            'email' => $user->email,
            'password' => 'secret123',
        ]);

        $response
            ->assertOk()
            ->assertJsonStructure([
                'token_type',
                'access_token',
                'expires_in',
                'user' => ['id', 'name', 'email'],
            ]);
    }

    public function test_authenticated_user_can_create_and_list_designs(): void
    {
        $user = User::factory()->create([
            'email' => 'designer@example.com',
            'password' => 'secret123',
        ]);

        $loginResponse = $this->postJson('/auth/login', [
            'email' => $user->email,
            'password' => 'secret123',
        ])->assertOk();

        $token = $loginResponse->json('access_token');

        $payload = [
            'name' => 'Cartel guardado',
            'state' => [
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
                'designTitle' => 'Cartel guardado',
                'designTitleManual' => true,
                'designSurface' => [
                    'width' => 368,
                    'height' => 620,
                ],
                'content' => [
                    'title' => 'Festival de prueba',
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
            ],
        ];

        $createResponse = $this->withHeader('Authorization', 'Bearer '.$token)
            ->postJson('/designer/designs', $payload)
            ->assertCreated()
            ->assertJsonPath('design.name', 'Cartel guardado');

        $designUuid = $createResponse->json('design.uuid');

        $this->withHeader('Authorization', 'Bearer '.$token)
            ->getJson('/designer/designs')
            ->assertOk()
            ->assertJsonCount(1, 'designs')
            ->assertJsonPath('designs.0.uuid', $designUuid);
    }

    public function test_authenticated_user_can_rename_duplicate_and_delete_designs(): void
    {
        $user = User::factory()->create([
            'email' => 'designer@example.com',
            'password' => 'secret123',
        ]);

        $token = $this->postJson('/auth/login', [
            'email' => $user->email,
            'password' => 'secret123',
        ])->json('access_token');

        $designResponse = $this->withHeader('Authorization', 'Bearer '.$token)
            ->postJson('/designer/designs', [
                'name' => 'Diseño original',
                'state' => [
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
                    'designTitle' => 'Diseño original',
                    'designTitleManual' => true,
                    'designSurface' => ['width' => 368, 'height' => 620],
                    'content' => ['title' => 'Título', 'subtitle' => '', 'date' => '', 'time' => '', 'location' => '', 'platform' => '', 'teacher' => '', 'price' => '', 'contact' => '', 'extra' => ''],
                    'elementLayout' => [
                        'background' => ['backgroundColor' => '#ffffff'],
                        'title' => ['x' => 20, 'y' => 60, 'w' => 280, 'fontSize' => 42, 'zIndex' => 10],
                    ],
                    'customElements' => [],
                    'userUploadedImages' => [],
                ],
            ])
            ->assertCreated();

        $designUuid = $designResponse->json('design.uuid');

        $this->withHeader('Authorization', 'Bearer '.$token)
            ->patchJson("/designer/designs/{$designUuid}/rename", [
                'name' => 'Diseño renombrado',
            ])
            ->assertOk()
            ->assertJsonPath('design.name', 'Diseño renombrado');

        $duplicateResponse = $this->withHeader('Authorization', 'Bearer '.$token)
            ->postJson("/designer/designs/{$designUuid}/duplicate")
            ->assertCreated();

        $duplicateUuid = $duplicateResponse->json('design.uuid');

        $this->withHeader('Authorization', 'Bearer '.$token)
            ->deleteJson("/designer/designs/{$designUuid}")
            ->assertOk()
            ->assertJson(['deleted' => true]);

        $this->withHeader('Authorization', 'Bearer '.$token)
            ->getJson('/designer/designs')
            ->assertOk()
            ->assertJsonCount(1, 'designs')
            ->assertJsonPath('designs.0.uuid', $duplicateUuid);
    }
}
