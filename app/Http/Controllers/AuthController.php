<?php

namespace App\Http\Controllers;

use App\Models\User;
use App\Support\JwtService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;
use Throwable;

class AuthController extends Controller
{
    public function __construct(
        private readonly JwtService $jwtService,
    ) {
    }

    public function login(Request $request): JsonResponse
    {
        if ($request->filled('token')) {
            return $this->loginWithBootstrapToken($request);
        }

        $validated = $request->validate([
            'email' => ['required', 'email'],
            'password' => ['required', 'string'],
        ]);

        /** @var User|null $user */
        $user = User::query()->where('email', $validated['email'])->first();

        if (!$user || !Hash::check($validated['password'], $user->password)) {
            return response()->json([
                'message' => 'Credenciales inválidas.',
            ], 422);
        }

        Auth::login($user);
        $request->session()->regenerate();

        $token = $this->jwtService->issueTokenForUser($user);

        return response()->json([
            'token_type' => 'Bearer',
            'access_token' => $token,
            'expires_in' => (int) config('jwt.ttl', 60) * 60,
            'user' => [
                'id' => $user->id,
                'name' => $user->name,
                'email' => $user->email,
            ],
        ]);
    }

    public function me(Request $request): JsonResponse
    {
        /** @var User $user */
        $user = $request->user();

        return response()->json([
            'user' => [
                'id' => $user->id,
                'name' => $user->name,
                'email' => $user->email,
            ],
        ]);
    }

    private function loginWithBootstrapToken(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'token' => ['required', 'string'],
        ]);

        try {
            $payload = $this->jwtService->decodeToken($validated['token']);
        } catch (Throwable $exception) {
            return response()->json([
                'message' => $exception->getMessage(),
            ], 422);
        }

        if (($payload['type'] ?? null) !== 'bootstrap_login') {
            return response()->json([
                'message' => 'Token de bootstrap inválido.',
            ], 422);
        }

        $email = (string) ($payload['user']['email'] ?? $payload['sub'] ?? '');
        $name = (string) ($payload['user']['name'] ?? 'Dev');

        if ($email === '') {
            return response()->json([
                'message' => 'El token no contiene un email válido.',
            ], 422);
        }

        /** @var User $user */
        $user = User::query()->firstOrCreate(
            ['email' => $email],
            [
                'name' => $name,
                'password' => Str::password(32),
            ]
        );

        if ($user->name !== $name) {
            $user->forceFill(['name' => $name])->save();
        }

        Auth::login($user);
        $request->session()->regenerate();

        return response()->json([
            'token_type' => 'Bearer',
            'access_token' => $this->jwtService->issueTokenForUser($user),
            'expires_in' => (int) config('jwt.ttl', 60) * 60,
            'user' => [
                'id' => $user->id,
                'name' => $user->name,
                'email' => $user->email,
            ],
        ]);
    }
}
