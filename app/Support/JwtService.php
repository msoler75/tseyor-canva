<?php

namespace App\Support;

use App\Models\User;
use Carbon\CarbonImmutable;
use Illuminate\Support\Arr;
use Illuminate\Support\Str;
use RuntimeException;

final class JwtService
{
    /**
     * Decodifica un JWT usando firebase/php-jwt
     * @param string $token
     * @return object|null
     */
    public function decodeWithFirebase(string $token): ?object
    {
        try {
            $key = config('jwt.secret') ?? '';
            if (!$key) {
                throw new \RuntimeException('JWT secret no configurado.');
            }
            return \Firebase\JWT\JWT::decode($token, new \Firebase\JWT\Key($key, 'HS256'));
        } catch (\Firebase\JWT\SignatureInvalidException $e) {
            \Log::warning('Firma JWT inválida', ['exception' => $e->getMessage()]);
            return null;
        } catch (\Exception $e) {
            \Log::warning('Error al decodificar JWT', ['exception' => $e->getMessage()]);
            return null;
        }
    }
}
