<?php

namespace App\Support;

use App\Models\User;
use Carbon\CarbonImmutable;
use Illuminate\Support\Arr;
use Illuminate\Support\Str;
use RuntimeException;

final class JwtService
{
    public function issueTokenForUser(User $user): string
    {
        $issuedAt = CarbonImmutable::now();
        $expiresAt = $issuedAt->addMinutes((int) config('jwt.ttl', 60));

        $payload = [
            'iss' => config('app.url'),
            'sub' => (string) $user->getKey(),
            'iat' => $issuedAt->timestamp,
            'nbf' => $issuedAt->timestamp,
            'exp' => $expiresAt->timestamp,
            'jti' => (string) Str::uuid(),
            'user' => [
                'id' => $user->getKey(),
                'name' => $user->name,
                'email' => $user->email,
            ],
        ];

        return $this->encode($payload);
    }

    public function issueBootstrapLoginToken(string $name, string $email): string
    {
        $issuedAt = CarbonImmutable::now();
        $expiresAt = $issuedAt->addMinutes(15);

        return $this->encode([
            'iss' => config('app.url'),
            'sub' => $email,
            'iat' => $issuedAt->timestamp,
            'nbf' => $issuedAt->timestamp,
            'exp' => $expiresAt->timestamp,
            'jti' => (string) Str::uuid(),
            'type' => 'bootstrap_login',
            'user' => [
                'name' => $name,
                'email' => $email,
            ],
        ]);
    }

    /**
     * @return array<string, mixed>
     */
    public function decodeToken(string $token): array
    {
        $parts = explode('.', $token);
        if (count($parts) !== 3) {
            throw new RuntimeException('Token JWT malformado.');
        }

        [$encodedHeader, $encodedPayload, $encodedSignature] = $parts;

        $header = json_decode($this->base64UrlDecode($encodedHeader), true);
        $payload = json_decode($this->base64UrlDecode($encodedPayload), true);

        if (!is_array($header) || !is_array($payload)) {
            throw new RuntimeException('Token JWT inválido.');
        }

        if (Arr::get($header, 'alg') !== 'HS256') {
            throw new RuntimeException('Algoritmo JWT no soportado.');
        }

        $expectedSignature = $this->sign("{$encodedHeader}.{$encodedPayload}");
        if (!hash_equals($expectedSignature, $this->base64UrlDecode($encodedSignature))) {
            throw new RuntimeException('Firma JWT inválida.');
        }

        $now = CarbonImmutable::now()->timestamp;
        if (($payload['nbf'] ?? 0) > $now) {
            throw new RuntimeException('Token JWT todavía no válido.');
        }

        if (($payload['exp'] ?? 0) <= $now) {
            throw new RuntimeException('Token JWT expirado.');
        }

        return $payload;
    }

    /**
     * @param array<string, mixed> $payload
     */
    private function encode(array $payload): string
    {
        $header = [
            'alg' => 'HS256',
            'typ' => 'JWT',
        ];

        $encodedHeader = $this->base64UrlEncode(json_encode($header, JSON_THROW_ON_ERROR));
        $encodedPayload = $this->base64UrlEncode(json_encode($payload, JSON_THROW_ON_ERROR));
        $signature = $this->base64UrlEncode($this->sign("{$encodedHeader}.{$encodedPayload}"));

        return "{$encodedHeader}.{$encodedPayload}.{$signature}";
    }

    private function sign(string $message): string
    {
        return hash_hmac('sha256', $message, $this->secret(), true);
    }

    private function secret(): string
    {
        $secret = (string) config('jwt.secret');
        if ($secret === '') {
            throw new RuntimeException('JWT secret no configurado.');
        }

        if (str_starts_with($secret, 'base64:')) {
            $decoded = base64_decode(substr($secret, 7), true);
            if ($decoded !== false) {
                return $decoded;
            }
        }

        return $secret;
    }

    private function base64UrlEncode(string $value): string
    {
        return rtrim(strtr(base64_encode($value), '+/', '-_'), '=');
    }

    private function base64UrlDecode(string $value): string
    {
        $padding = strlen($value) % 4;
        if ($padding > 0) {
            $value .= str_repeat('=', 4 - $padding);
        }

        $decoded = base64_decode(strtr($value, '-_', '+/'), true);

        if ($decoded === false) {
            throw new RuntimeException('Base64URL inválido.');
        }

        return $decoded;
    }
}
