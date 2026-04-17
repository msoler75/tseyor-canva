<?php

namespace App\Http\Controllers;

use App\Services\DeployHelper;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;
use RuntimeException;
use Throwable;

class DeployController extends Controller
{
    public function build(Request $request): JsonResponse
    {
        abort_unless((bool) config('deploy.route_enabled', true), 404);
        $this->authorizeDeployRequest($request);

        $validated = $request->validate([
            'mode' => ['required', 'string', 'in:'.DeployHelper::MODE_PUBLIC_BUILD],
            'file' => ['required', 'file', 'max:512000'],
        ]);

        $file = $request->file('file');
        if (! $file || ! $file->isValid()) {
            throw new RuntimeException('No se recibio un ZIP valido.');
        }

        $tmpPath = storage_path('app/deploy-upload-'.date('Ymd-His').'-'.bin2hex(random_bytes(4)).'.zip');
        File::ensureDirectoryExists(dirname($tmpPath));
        $file->move(dirname($tmpPath), basename($tmpPath));

        try {
            $result = DeployHelper::installFromZip((string) $validated['mode'], $tmpPath);

            return response()->json([
                'ok' => true,
                ...$result,
            ]);
        } catch (Throwable $exception) {
            report($exception);

            return response()->json([
                'ok' => false,
                'message' => $exception->getMessage(),
            ], 500);
        } finally {
            if (is_file($tmpPath)) {
                @unlink($tmpPath);
            }
        }
    }

    private function authorizeDeployRequest(Request $request): void
    {
        $expectedToken = (string) config('deploy.token', '');
        if ($expectedToken === '') {
            return;
        }

        $providedToken = (string) $request->header('X-Deploy-Token', '');
        abort_unless(hash_equals($expectedToken, $providedToken), 403);
    }
}
