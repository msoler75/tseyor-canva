<?php

declare(strict_types=1);

namespace App\Services;

use CURLFile;
use FilesystemIterator;
use RecursiveDirectoryIterator;
use RecursiveIteratorIterator;
use RuntimeException;
use ZipArchive;

final class DeployHelper
{
    public const MODE_PUBLIC_BUILD = 'public_build';

    public static function validateMode(string $mode): void
    {
        if ($mode !== self::MODE_PUBLIC_BUILD) {
            throw new RuntimeException("Modo no soportado: {$mode}");
        }
    }

    /**
     * @return array<string, mixed>
     */
    public static function getModeConfig(string $mode): array
    {
        self::validateMode($mode);

        return [
            'archive_prefix' => 'public_build',
            'source' => public_path('build'),
            'extract_to' => public_path('build'),
            'zip_root' => '',
        ];
    }

    public static function createZipForMode(string $mode, string $zipPath): int
    {
        $config = self::getModeConfig($mode);
        $sourceDir = (string) $config['source'];

        if (! is_dir($sourceDir)) {
            throw new RuntimeException('No existe public/build. Ejecuta npm run build antes de desplegar.');
        }

        if (file_exists($zipPath) && ! unlink($zipPath)) {
            throw new RuntimeException("No se pudo sobrescribir ZIP temporal: {$zipPath}");
        }

        $zip = new ZipArchive;
        $result = $zip->open($zipPath, ZipArchive::CREATE | ZipArchive::OVERWRITE);
        if ($result !== true) {
            throw new RuntimeException("No se pudo crear el ZIP: {$zipPath}");
        }

        $filesAdded = self::addDirectoryToZip($zip, $sourceDir, (string) $config['zip_root']);
        $zip->close();

        if ($filesAdded < 1) {
            @unlink($zipPath);
            throw new RuntimeException('No se encontraron archivos dentro de public/build.');
        }

        return $filesAdded;
    }

    /**
     * @return array<string, mixed>
     */
    public static function sendZipFile(
        string $zipPath,
        string $endpoint,
        string $mode,
        bool $verifySsl = true,
        int $timeoutSeconds = 1800,
        ?string $token = null,
    ): array {
        self::validateMode($mode);

        if (! is_file($zipPath)) {
            throw new RuntimeException("ZIP no encontrado: {$zipPath}");
        }

        $ch = curl_init();
        if ($ch === false) {
            throw new RuntimeException('No se pudo inicializar cURL.');
        }

        $headers = ['Accept: application/json'];
        if ($token !== null && $token !== '') {
            $headers[] = 'X-Deploy-Token: '.$token;
        }

        curl_setopt_array($ch, [
            CURLOPT_URL => $endpoint,
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => [
                'mode' => $mode,
                'file' => new CURLFile($zipPath, 'application/zip', basename($zipPath)),
            ],
            CURLOPT_HTTPHEADER => $headers,
            CURLOPT_HEADER => true,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => $timeoutSeconds,
            CURLOPT_SSL_VERIFYPEER => $verifySsl,
            CURLOPT_SSL_VERIFYHOST => $verifySsl ? 2 : 0,
        ]);

        $response = curl_exec($ch);
        $curlError = curl_error($ch);
        $httpCode = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $headerSize = (int) curl_getinfo($ch, CURLINFO_HEADER_SIZE);
        $totalTime = (float) curl_getinfo($ch, CURLINFO_TOTAL_TIME);
        $effectiveUrl = (string) curl_getinfo($ch, CURLINFO_EFFECTIVE_URL);
        $sizeUpload = (float) curl_getinfo($ch, CURLINFO_SIZE_UPLOAD);
        curl_close($ch);

        $responseString = is_string($response) ? $response : '';
        $responseBody = $headerSize > 0 ? substr($responseString, $headerSize) : $responseString;

        return [
            'ok' => $httpCode >= 200 && $httpCode < 300 && $curlError === '',
            'http_code' => $httpCode,
            'response' => $responseBody,
            'curl_error' => $curlError,
            'curl_info' => [
                'total_time' => $totalTime,
                'effective_url' => $effectiveUrl,
                'size_upload' => $sizeUpload,
            ],
        ];
    }

    /**
     * @return array{mode:string,backups:array<int,string>,files_extracted:int}
     */
    public static function installFromZip(string $mode, string $zipPath): array
    {
        $config = self::getModeConfig($mode);
        self::validateZipEntries($zipPath);

        $targetPath = (string) $config['extract_to'];
        $backups = [];

        if (is_dir($targetPath)) {
            $backupPath = self::backupRoot().DIRECTORY_SEPARATOR.'_backup_public_build_'.date('Ymd_His');
            if (! @rename($targetPath, $backupPath)) {
                throw new RuntimeException('No se pudo crear backup de public/build.');
            }
            $backups[] = $backupPath;
            self::cleanupOldBackups(self::backupRoot(), '_backup_public_build_', 5);
        }

        $filesExtracted = self::extractZip($zipPath, $targetPath);

        return [
            'mode' => $mode,
            'backups' => $backups,
            'files_extracted' => $filesExtracted,
        ];
    }

    public static function printCliUsage(string $scriptName = 'artisan'): void
    {
        $lines = [
            'Uso:',
            '  php '.$scriptName.' deploy:build [--endpoint=https://tu-servidor/deploy/build] [--insecure] [--keep-zip]',
            '',
            'Variables de entorno soportadas:',
            '  DEPLOY_ENDPOINT, DEPLOY_TOKEN, DEPLOY_VERIFY_SSL, DEPLOY_TIMEOUT',
        ];

        fwrite(STDOUT, implode(PHP_EOL, $lines).PHP_EOL);
    }

    private static function addDirectoryToZip(ZipArchive $zip, string $sourceDir, string $zipRoot): int
    {
        $sourceDir = rtrim((string) realpath($sourceDir), DIRECTORY_SEPARATOR);
        if ($sourceDir === '') {
            throw new RuntimeException('Directorio no encontrado para comprimir.');
        }

        $added = 0;
        $iterator = new RecursiveIteratorIterator(
            new RecursiveDirectoryIterator($sourceDir, FilesystemIterator::SKIP_DOTS),
            RecursiveIteratorIterator::LEAVES_ONLY,
        );

        foreach ($iterator as $fileInfo) {
            if (! $fileInfo->isFile()) {
                continue;
            }

            $absolutePath = $fileInfo->getPathname();
            $relative = substr($absolutePath, strlen($sourceDir) + 1);
            $relative = str_replace('\\', '/', $relative);
            $entryName = $zipRoot !== '' ? $zipRoot.'/'.$relative : $relative;

            if (! $zip->addFile($absolutePath, $entryName)) {
                throw new RuntimeException('No se pudo agregar archivo al ZIP: '.$absolutePath);
            }
            $added++;
        }

        return $added;
    }

    private static function validateZipEntries(string $zipPath): void
    {
        if (! is_file($zipPath)) {
            throw new RuntimeException('ZIP no encontrado para validar: '.$zipPath);
        }

        $zip = new ZipArchive;
        if ($zip->open($zipPath) !== true) {
            throw new RuntimeException('No se pudo abrir el ZIP para validar: '.$zipPath);
        }

        $validFiles = 0;
        for ($i = 0; $i < $zip->numFiles; $i++) {
            $entry = (string) $zip->getNameIndex($i);
            $normalized = str_replace('\\', '/', $entry);

            if ($normalized === '' || str_starts_with($normalized, '/') || str_contains($normalized, '../')) {
                $zip->close();
                throw new RuntimeException('Entrada ZIP insegura: '.$entry);
            }

            if (str_ends_with($normalized, '/')) {
                continue;
            }

            if (str_contains($normalized, '.php') || str_starts_with($normalized, 'storage/') || str_starts_with($normalized, 'vendor/')) {
                $zip->close();
                throw new RuntimeException('El ZIP de public/build contiene un archivo no permitido: '.$entry);
            }

            $validFiles++;
        }

        $zip->close();

        if ($validFiles < 1) {
            throw new RuntimeException('El ZIP no contiene archivos validos para instalar.');
        }
    }

    private static function extractZip(string $zipPath, string $targetPath): int
    {
        if (! is_dir($targetPath) && ! mkdir($targetPath, 0755, true) && ! is_dir($targetPath)) {
            throw new RuntimeException('No se pudo crear destino de extraccion: '.$targetPath);
        }

        $zip = new ZipArchive;
        if ($zip->open($zipPath) !== true) {
            throw new RuntimeException('No se pudo abrir ZIP para extraer: '.$zipPath);
        }

        $filesInArchive = 0;
        for ($i = 0; $i < $zip->numFiles; $i++) {
            $entry = (string) $zip->getNameIndex($i);
            if (! str_ends_with($entry, '/')) {
                $filesInArchive++;
            }
        }

        if (! $zip->extractTo($targetPath)) {
            $zip->close();
            throw new RuntimeException('Error al extraer ZIP en: '.$targetPath);
        }

        $zip->close();

        return $filesInArchive;
    }

    private static function backupRoot(): string
    {
        $backupRoot = storage_path('app/deploy-backups');
        if (! is_dir($backupRoot) && ! mkdir($backupRoot, 0755, true) && ! is_dir($backupRoot)) {
            throw new RuntimeException('No se pudo crear carpeta de backups de despliegue: '.$backupRoot);
        }

        return $backupRoot;
    }

    private static function cleanupOldBackups(string $basePath, string $prefix, int $keep): void
    {
        $dirs = glob($basePath.DIRECTORY_SEPARATOR.$prefix.'*', GLOB_ONLYDIR) ?: [];

        usort($dirs, static fn (string $a, string $b): int => filemtime($b) <=> filemtime($a));

        foreach (array_slice($dirs, $keep) as $dir) {
            self::deleteDirectory($dir);
        }
    }

    private static function deleteDirectory(string $dir): void
    {
        if (! is_dir($dir)) {
            return;
        }

        $items = new RecursiveIteratorIterator(
            new RecursiveDirectoryIterator($dir, FilesystemIterator::SKIP_DOTS),
            RecursiveIteratorIterator::CHILD_FIRST,
        );

        foreach ($items as $item) {
            if ($item->isDir()) {
                @rmdir($item->getPathname());
            } else {
                @unlink($item->getPathname());
            }
        }

        @rmdir($dir);
    }
}
