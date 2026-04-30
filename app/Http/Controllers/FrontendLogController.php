<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Log;

class FrontendLogController extends Controller
{
    /**
     * Recibir logs del frontend (individual o batch) y escribirlos en el log de Laravel.
     */
    public function store(Request $request): JsonResponse
    {
        // Soporte para batch (array de logs) o log individual
        if ($request->has('logs')) {
            $request->validate([
                'logs' => 'required|array|max:100',
                'logs.*.level' => 'required|string|in:debug,info,warning,error',
                'logs.*.category' => 'required|string|max:100',
                'logs.*.message' => 'required|string|max:2000',
                'logs.*.data' => 'nullable|array',
                'logs.*.timestamp' => 'nullable|string|max:50',
            ]);

            foreach ($request->input('logs') as $log) {
                $this->writeLog($log, $request);
            }
        } else {
            $validated = $request->validate([
                'level' => 'required|string|in:debug,info,warning,error',
                'category' => 'required|string|max:100',
                'message' => 'required|string|max:2000',
                'data' => 'nullable|array',
                'data.*' => 'nullable|string|max:5000',
                'timestamp' => 'nullable|string|max:50',
                'url' => 'nullable|string|max:500',
            ]);

            $this->writeLog($validated, $request);
        }

        return response()->json(['success' => true]);
    }

    /**
     * Escribir una entrada de log individual.
     */
    private function writeLog(array $log, Request $request): void
    {
        $level = $log['level'] ?? 'info';
        $category = $log['category'] ?? 'unknown';
        $message = $log['message'] ?? '';
        $data = $log['data'] ?? [];
        $url = $log['url'] ?? $request->header('Referer');
        $timestamp = $log['timestamp'] ?? now()->toISOString();

        Log::{$level}("[FRONTEND] [{$category}] {$message}", [
            'context' => $data,
            'url' => $url,
            'timestamp' => $timestamp,
        ]);
    }
}
