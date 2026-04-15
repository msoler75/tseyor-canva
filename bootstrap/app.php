<?php

use App\Http\Middleware\HandleInertiaRequests;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Http\Request;
use Inertia\Inertia;
use Symfony\Component\HttpKernel\Exception\HttpExceptionInterface;
use Illuminate\Auth\AuthenticationException;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        commands: __DIR__.'/../routes/console.php',
        health: '/up',
    )
    ->withMiddleware(function (Middleware $middleware): void {
        $middleware->validateCsrfTokens(except: [
            'auth/*',
            'designer/*',
        ]);

        $middleware->web(append: [
            HandleInertiaRequests::class,
        ]);
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        $exceptions->render(function (\Throwable $exception, Request $request) {
            $status = $exception instanceof HttpExceptionInterface
                ? $exception->getStatusCode()
                : 500;

            // Loguear detalles de excepción si es error 500
            if ($status === 500) {
                \Log::error('[Error 500]', [
                    'exception' => $exception,
                    'url' => $request->fullUrl(),
                    'input' => $request->all(),
                ]);
            }


            if($exception instanceof AuthenticationException) {
                 return Inertia::render('Error', [
                    'status' => 401,
                    'message' => "Necesitas iniciar sesión para acceder a esta página.",
                ])->toResponse($request)->setStatusCode($status);
            }

            $message = match ($status) {
                401 => 'No estás autenticado. Por favor, inicia sesión.',
                403 => 'No tienes permisos para acceder a este recurso.',
                404 => 'La página que buscas no existe o ya no está disponible.',
                419 => 'Tu sesión ha expirado. Vuelve a iniciar sesión para continuar.',
                422 => 'La solicitud no pudo procesarse. Revisa los datos e inténtalo de nuevo.',
                500 => 'Algo salió mal en la aplicación. Inténtalo de nuevo en unos minutos.',
                503 => 'La aplicación está temporalmente fuera de servicio por mantenimiento o sobrecarga.',
                default => $exception->getMessage() ?: 'Se ha producido un problema inesperado.',
            };

            return Inertia::render('Error', [
                'status' => $status,
                'message' => $message,
            ])->toResponse($request)->setStatusCode($status);
        });
    })->create();
