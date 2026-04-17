<?php

use App\Services\DeployHelper;
use Illuminate\Foundation\Inspiring;
use Illuminate\Support\Facades\Artisan;

Artisan::command('inspire', function () {
    $this->comment(Inspiring::quote());
})->purpose('Display an inspiring quote');

Artisan::command('deploy:build {--endpoint=} {--token=} {--insecure : No verificar SSL al enviar} {--keep-zip : Mantener el ZIP temporal}', function (): int {
    $endpoint = $this->option('endpoint') ?: config('deploy.endpoint');
    if (! $endpoint) {
        $this->error('Falta endpoint. Configura DEPLOY_ENDPOINT o usa --endpoint=...');
        DeployHelper::printCliUsage('artisan');

        return 1;
    }

    $token = $this->option('token') ?: config('deploy.token');
    $verifySsl = ! $this->option('insecure') && filter_var(config('deploy.verify_ssl', true), FILTER_VALIDATE_BOOLEAN);
    $timeout = (int) config('deploy.timeout', 1800);
    $zipPath = storage_path('app/deploy-public-build-'.date('Ymd-His').'.zip');

    try {
        $this->info('Comprimiendo public/build...');
        $filesAdded = DeployHelper::createZipForMode(DeployHelper::MODE_PUBLIC_BUILD, $zipPath);
        $this->info("ZIP creado: {$zipPath} ({$filesAdded} archivos)");

        $this->info("Enviando ZIP a {$endpoint}...");
        $result = DeployHelper::sendZipFile(
            zipPath: $zipPath,
            endpoint: $endpoint,
            mode: DeployHelper::MODE_PUBLIC_BUILD,
            verifySsl: $verifySsl,
            timeoutSeconds: $timeout,
            token: is_string($token) ? $token : null,
        );

        if (! $result['ok']) {
            $this->error('Error de despliegue. HTTP '.$result['http_code']);
            if ($result['curl_error']) {
                $this->error('cURL: '.$result['curl_error']);
            }
            $this->line((string) $result['response']);

            return 1;
        }

        $this->info('Despliegue completado.');
        $this->line((string) $result['response']);

        return 0;
    } catch (Throwable $exception) {
        $this->error($exception->getMessage());

        return 1;
    } finally {
        if (! $this->option('keep-zip') && is_file($zipPath)) {
            @unlink($zipPath);
        }
    }
})->purpose('Comprime public/build y lo despliega en un endpoint remoto');
