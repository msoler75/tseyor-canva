<?php

namespace App\Http\Controllers;

use App\Models\User;
use App\Support\JwtService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;
use Inertia\Inertia;
use Inertia\Response;
use RuntimeException;

class AuthController extends Controller
{
    public function __construct(
        private readonly JwtService $jwtService,
    ) {
    }

    public function login() {
        // si hay sesión iniciado, redirigir a /designer/editor
        if (Auth::check()) {
            return redirect()->route('designer.welcome');
        }

        // sino, redirigimos al portal principal de login
        $portalLoginUrl = $this->portalLoginUrl();
        // dd($portalLoginUrl);
        if ($portalLoginUrl) {
            // return redirect()->away($portalLoginUrl);
            return Inertia::location($portalLoginUrl);
        }

        // si no hay URL de portal, mostramos una vista de error
        return Inertia::render('Error', [
            'status' => 500,
            'message' => 'No se ha configurado una URL de login para el portal.',
        ]);
    }

    public function portalCallback(Request $request)
    {
        $validated = $request->validate([
            'token' => ['required', 'string'],
        ]);

        // Decodificar usando firebase/php-jwt
        $payload = $this->jwtService->decodeWithFirebase($validated['token']);
        // Depuración: mostrar expiración y hora actual
        $now = time();
        $exp = null;
        if ($payload) {
            $payloadArr = json_decode(json_encode($payload), true);
            $exp = $payloadArr['exp'] ?? null;
        }
        if(0)
            dd([
            'now' => $now,
            'now_datetime' => date('Y-m-d H:i:s', $now),
            'now_timezone' => date_default_timezone_get(),
            'exp' => $exp,
            'exp_datetime' => $exp ? date('Y-m-d H:i:s', $exp) : null,
            'exp_timezone' => $exp ? (new \DateTimeImmutable('@'.$exp))->setTimezone(new \DateTimeZone(date_default_timezone_get()))->getTimezone()->getName() : null,
            'payload' => $payload,
            'token' => $validated['token'],
        ]);
        if (!$payload) {
            return Inertia::render('Error', [
                'status' => 422,
                'message' => 'Token de bootstrap inválido.',
            ]);
        }


        // El payload de firebase es un objeto, lo convertimos a array para compatibilidad
        $payloadArr = json_decode(json_encode($payload), true);

        $email = (string) ($payloadArr['email'] ?? $payloadArr['sub'] ?? '');
        $name = (string) ($payloadArr['name'] ?? 'Dev');

        if ($email === '') {
            return Inertia::render('Error', [
                'status' => 422,
                'message' => 'El token no contiene un email válido.',
            ]);
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

        // Si hay diseño temporal en sesión, recuperarlo y redirigir a su edición
        $sessionState = $request->session()->get(\App\Http\Controllers\DesignerController::sessionKey());
        if ($sessionState) {
            $response = \App\Http\Controllers\DesignerController::recoverSessionDesign($request);
            $data = $response->getData(true);
            if (!empty($data['recovered']) && !empty($data['designUuid'])) {
                return redirect()->route('designer.designs.edit', ['design' => $data['designUuid']]);
            }
        }

        return redirect()->route('designer.welcome');
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

    public function logout(Request $request): JsonResponse
    {
        Auth::logout();

        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return response()->json([
            'logged_out' => true,
        ]);
    }

    private function authenticateFromToken(Request $request, string $token): RedirectResponse
    {
        try {
            $user = $this->resolveUserFromToken($token);
        } catch (RuntimeException $exception) {
            return redirect()->route('designer.welcome')->with('error', $exception->getMessage());
        }

        Auth::login($user);
        $request->session()->regenerate();

        return redirect()->route('designer.welcome');
    }

    private function loginWithCredentials(Request $request): JsonResponse
    {
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

        return response()->json([
            'token_type' => 'Bearer',
            'access_token' => $this->jwtService->issueTokenForUser($user),
            'expires_in' => (int) config('jwt.ttl', 60) * 60,
            'user' => [
                'id' => $user->id,
                'name' => $user->name,
                'email' => $user->email,
            ],
            'redirect_to' => route('designer.welcome'),
        ]);
    }

    private function resolveUserFromToken(string $token): User
    {
        $payload = $this->jwtService->decodeToken($token);
        $email = (string) data_get($payload, 'user.email', data_get($payload, 'email', data_get($payload, 'sub', '')));
        $name = (string) data_get($payload, 'user.name', data_get($payload, 'name', 'Usuario'));

        if ($email === '') {
            throw new RuntimeException('El token no contiene un email válido.');
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

        return $user;
    }

    private function portalLoginUrl(): ?string
    {
        $baseUrl = config('portal.login_url');
        if (!$baseUrl) {
            return null;
        }

        $separator = str_contains($baseUrl, '?') ? '&' : '?';
        $parameter = config('portal.callback_parameter', 'return_to');
        $callbackUrl = route('auth.login');

        return "{$baseUrl}{$separator}{$parameter}=".urlencode($callbackUrl);
    }
}
