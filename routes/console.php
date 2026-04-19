<?php

use App\Services\DeployHelper;
use App\Services\DemoTemplateFactory;
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

Artisan::command('designer:create-demo-templates {--admin-email=admin@example.com} {--admin-name=admin} {--password=password} {--status=published}', function (DemoTemplateFactory $factory): int {
    $status = (string) $this->option('status');
    if (! in_array($status, ['draft', 'published', 'archived'], true)) {
        $this->error('Estado no válido. Usa draft, published o archived.');

        return 1;
    }

    $result = $factory->create(
        adminEmail: (string) $this->option('admin-email'),
        adminName: (string) $this->option('admin-name'),
        password: (string) $this->option('password'),
        status: $status,
    );

    $this->info('Plantillas base de prueba creadas/actualizadas.');
    $this->line('Usuario propietario: '.$result['user']->email);

    foreach ($result['templates'] as $template) {
        $this->line(sprintf(
            '- %s (%s) -> diseño base %s',
            $template->title,
            $template->uuid,
            $template->baseDesign?->uuid ?? 'sin diseño',
        ));
    }

    return 0;
})->purpose('Crea o actualiza 3 plantillas base genéricas con sus diseños de prueba');
