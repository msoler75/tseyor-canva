<?php

namespace App\Http\Controllers;

use App\Models\User;
use App\Support\JwtService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;
use Inertia\Inertia;
use Inertia\Response;
use RuntimeException;

class AuthController extends Controller
{
    private const FROM_EDITOR_KEY = 'auth.redirect_to_editor_after_login';

    public function __construct(
        private readonly JwtService $jwtService,
    ) {
    }

    public function login(Request $request) {
        if ($request->boolean('from_editor')) {
            $request->session()->put(self::FROM_EDITOR_KEY, true);
        }

        if ($request->filled('token')) {
            Log::info('Auth login received token on GET; forwarding to portal callback');

            return $this->portalCallback($request);
        }

        // si hay sesión iniciado, redirigir a /designer/editor
        if (Auth::check()) {
            Log::info('Auth login skipped: user already authenticated', [
                'user_id' => Auth::id(),
                'target' => route('designer.welcome'),
            ]);

            return redirect()->route('designer.welcome');
        }

        // sino, redirigimos al portal principal de login
        $portalLoginUrl = $this->portalLoginUrl();

        if ($portalLoginUrl) {
            Log::info('Auth login redirecting to remote portal', [
                'portal_host' => parse_url($portalLoginUrl, PHP_URL_HOST),
                'callback' => route('auth.login.callback'),
                'callback_parameter' => config('portal.callback_parameter', 'return_to'),
            ]);

            // return redirect()->away($portalLoginUrl);
            return Inertia::location($portalLoginUrl);
        }

        // si no hay URL de portal, mostramos una vista de error
        Log::error('Auth login failed: PORTAL_LOGIN_URL is not configured');

        return Inertia::render('Error', [
            'status' => 500,
            'message' => 'No se ha configurado una URL de login para el portal.',
        ]);
    }

    public function portalCallback(Request $request)
    {
        Log::info('Portal JWT callback received', [
            'method' => $request->method(),
            'has_token' => $request->filled('token'),
            'token_length' => is_string($request->input('token')) ? strlen($request->input('token')) : 0,
            'ip' => $request->ip(),
        ]);

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
            Log::warning('Portal JWT callback rejected: invalid token');

            return Inertia::render('Error', [
                'status' => 422,
                'message' => 'Token de bootstrap inválido.',
            ]);
        }


        // El payload de firebase es un objeto, lo convertimos a array para compatibilidad
        $payloadArr = json_decode(json_encode($payload), true);

        $email = (string) ($payloadArr['email'] ?? $payloadArr['sub'] ?? '');
        $name = (string) ($payloadArr['name'] ?? data_get($payloadArr, 'user.name', 'Usuario'));
        $image = (string) ($payloadArr['image'] ?? data_get($payloadArr, 'user.image', ''));

        Log::info('Portal JWT decoded successfully', [
            'email' => $email,
            'name' => $name,
            'image' => $image,
            'exp' => isset($payloadArr['exp']) ? date(DATE_ATOM, (int) $payloadArr['exp']) : null,
            'payload' => $payloadArr
        ]);

        if ($email === '') {
            Log::warning('Portal JWT callback rejected: token has no email/sub');

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
                'image' => $image !== '' ? $image : null,
                'password' => Str::password(32),
            ]
        );

        $updates = [];
        if ($user->name !== $name) {
            $updates['name'] = $name;
        }
        if ($image !== '' && $user->image !== $image) {
            $updates['image'] = $image;
        }
        if ($updates !== []) {
            $user->forceFill($updates)->save();
        }

        Auth::login($user);
        $request->session()->regenerate();

        Log::info('Portal JWT callback authenticated user', [
            'user_id' => $user->id,
            'email' => $user->email,
            'created_now' => $user->wasRecentlyCreated,
            'updated_fields' => array_keys($updates),
        ]);

        // Recover a temporary design only when login explicitly started from the editor.
        // From home or shared layout login, authenticate and return to the project list.
        // Siempre intentar recuperar diseño temporal tras login, si existe
        $sessionKey = 'designer.state';
        $sessionState = $request->session()->get($sessionKey);
        $recoverDesignAfterLogin = (bool) $request->session()->pull(self::FROM_EDITOR_KEY, false);
        if ($sessionState) {
            $response = \App\Http\Controllers\DesignerController::recoverSessionDesign($request);
            $data = $response->getData(true);
            // Renombrar thumbnail si es necesario
            if (!empty($data['recovered']) && !empty($data['designUuid'])) {
                // Buscar el diseño recién creado
                $designUuid = $data['designUuid'];
                $design = \App\Models\Design::where('uuid', $designUuid)->first();
                if ($design && !empty($sessionState['thumbnail_path'])) {
                    $oldThumbnail = $sessionState['thumbnail_path'];
                    $extension = pathinfo($oldThumbnail, PATHINFO_EXTENSION);
                    $newThumbnail = $designUuid . ($extension ? ('.' . $extension) : '.jpg');
                    if ($oldThumbnail !== $newThumbnail && \Storage::disk('thumbnails')->exists($oldThumbnail)) {
                        \Storage::disk('thumbnails')->move($oldThumbnail, $newThumbnail);
                        $design->thumbnail_path = $newThumbnail;
                        $design->save();
                    }
                }
                if ($recoverDesignAfterLogin) {
                    return redirect()->route('designer.designs.edit', ['design' => $designUuid]);
                }
                // Si no, simplemente redirigir a la home
                return redirect()->route('designer.welcome');
            }
        } else {
            $request->session()->forget($sessionKey);
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
                'image' => $user->image,
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
                'image' => $user->image,
            ],
            'redirect_to' => route('designer.welcome'),
        ]);
    }

    private function resolveUserFromToken(string $token): User
    {
        $payload = $this->jwtService->decodeToken($token);
        $email = (string) data_get($payload, 'user.email', data_get($payload, 'email', data_get($payload, 'sub', '')));
        $name = (string) data_get($payload, 'user.name', data_get($payload, 'name', 'Usuario'));
        $image = (string) data_get($payload, 'user.image', data_get($payload, 'image', ''));

        if ($email === '') {
            throw new RuntimeException('El token no contiene un email válido.');
        }

        Log::debug('Resolviendo usuario desde token JWT', [
            'email' => $email,
            'name' => $name,
            'has_image' => $image !== '',
        ]);

        /** @var User $user */
        $user = User::query()->firstOrCreate(
            ['email' => $email],
            [
                'name' => $name,
                'image' => $image !== '' ? $image : null,
                'password' => Str::password(32),
            ]
        );

        $updates = [];
        if ($user->name !== $name) {
            $updates['name'] = $name;
        }
        if ($image !== '' && $user->image !== $image) {
            $updates['image'] = $image;
        }
        if ($updates !== []) {
            $user->forceFill($updates)->save();
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
        $callbackUrl = route('auth.login.callback');

        return "{$baseUrl}{$separator}{$parameter}=".urlencode($callbackUrl);
    }
}
