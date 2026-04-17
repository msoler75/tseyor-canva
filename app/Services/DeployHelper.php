<?php

declare(strict_types=1);

final class DeployHelper
{
    public const MODE_NODE_MODULES = 'node_modules';
    public const MODE_CLIENT = 'client';

    public static function validateMode(string $mode): void
    {
        if (!in_array($mode, [self::MODE_NODE_MODULES, self::MODE_CLIENT], true)) {
            throw new RuntimeException("Modo no soportado: {$mode}");
        }
    }

    /**
     * @return array<string, mixed>
     */
    public static function getModeConfig(string $mode): array
    {
        self::validateMode($mode);

        $root = __DIR__;
        if ($mode === self::MODE_NODE_MODULES) {
            return [
                'archive_prefix' => 'node_modules',
                'source_type' => 'directory',
                'source' => $root . DIRECTORY_SEPARATOR . 'node_modules',
                'extract_to' => $root,
                'zip_root' => 'node_modules',
            ];
        }

        return [
            'archive_prefix' => 'client_assets',
            'source_type' => 'relative_glob',
            'source' => [
                $root . DIRECTORY_SEPARATOR . 'dist' . DIRECTORY_SEPARATOR . 'index.html',
                $root . DIRECTORY_SEPARATOR . 'dist' . DIRECTORY_SEPARATOR . 'assets' . DIRECTORY_SEPARATOR . 'index*',
            ],
            'source_base' => $root . DIRECTORY_SEPARATOR . 'dist',
            'extract_to' => $root,
            'zip_root' => '',
        ];
    }

    public static function createZipForMode(string $mode, string $zipPath): int
    {
        $config = self::getModeConfig($mode);

        if ($mode === self::MODE_CLIENT) {
            self::assertClientBuildIsFresh();
        }

        if (file_exists($zipPath) && !unlink($zipPath)) {
            throw new RuntimeException("No se pudo sobrescribir ZIP temporal: {$zipPath}");
        }

        $zip = new ZipArchive();
        $result = $zip->open($zipPath, ZipArchive::CREATE | ZipArchive::OVERWRITE);
        if ($result !== true) {
            throw new RuntimeException("No se pudo crear el ZIP: {$zipPath}");
        }

        $filesAdded = 0;
        if ($config['source_type'] === 'directory') {
            $filesAdded = self::addDirectoryToZip(
                $zip,
                (string) $config['source'],
                (string) $config['zip_root']
            );
        } elseif ($config['source_type'] === 'relative_glob') {
            $filesAdded = self::addRelativeGlobToZip(
                $zip,
                (array) $config['source'],
                (string) $config['source_base']
            );
        } else {
            $filesAdded = self::addGlobToZip(
                $zip,
                (array) $config['source']
            );
        }

        $zip->close();

        if ($filesAdded < 1) {
            @unlink($zipPath);
            throw new RuntimeException("No se encontraron archivos para el modo {$mode}");
        }

        return $filesAdded;
    }

    public static function sendZipFile(
        string $zipPath,
        string $endpoint,
        string $mode,
        bool $verifySsl = true,
        int $timeoutSeconds = 1800
    ): array {
        if (!is_file($zipPath)) {
            throw new RuntimeException("ZIP no encontrado: {$zipPath}");
        }

        $ch = curl_init();
        $headers = ['Accept: application/json'];

        $postFields = [
            'mode' => $mode,
            'file' => new CURLFile($zipPath, 'application/zip', basename($zipPath)),
        ];

        curl_setopt_array($ch, [
            CURLOPT_URL => $endpoint,
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => $postFields,
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
        $contentType = (string) curl_getinfo($ch, CURLINFO_CONTENT_TYPE);
        $totalTime = (float) curl_getinfo($ch, CURLINFO_TOTAL_TIME);
        $primaryIp = (string) curl_getinfo($ch, CURLINFO_PRIMARY_IP);
        $effectiveUrl = (string) curl_getinfo($ch, CURLINFO_EFFECTIVE_URL);
        $sizeUpload = (float) curl_getinfo($ch, CURLINFO_SIZE_UPLOAD);
        $sizeDownload = (float) curl_getinfo($ch, CURLINFO_SIZE_DOWNLOAD);
        curl_close($ch);

        $responseString = is_string($response) ? $response : '';
        $responseHeaders = $headerSize > 0 ? substr($responseString, 0, $headerSize) : '';
        $responseBody = $headerSize > 0 ? substr($responseString, $headerSize) : $responseString;

        return [
            'ok' => $httpCode >= 200 && $httpCode < 300 && $curlError === '',
            'http_code' => $httpCode,
            'response' => $responseBody,
            'response_headers' => $responseHeaders,
            'curl_error' => $curlError,
            'curl_info' => [
                'content_type' => $contentType,
                'total_time' => $totalTime,
                'primary_ip' => $primaryIp,
                'effective_url' => $effectiveUrl,
                'size_upload' => $sizeUpload,
                'size_download' => $sizeDownload,
            ],
        ];
    }

    /**
     * @return array{mode:string,tmpZipPath:string,originalName:string,size:int}
     */
    public static function receiveUpload(): array
    {
        if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
            throw new RuntimeException('Metodo no permitido. Usa POST.');
        }

        $mode = (string) ($_POST['mode'] ?? '');
        self::validateMode($mode);

        if (!isset($_FILES['file']) || !is_array($_FILES['file'])) {
            throw new RuntimeException('No se recibio archivo ZIP en el campo file.');
        }

        $file = $_FILES['file'];
        $errorCode = (int) ($file['error'] ?? UPLOAD_ERR_NO_FILE);
        if ($errorCode !== UPLOAD_ERR_OK) {
            throw new RuntimeException('Error de subida: ' . self::uploadErrorMessage($errorCode));
        }

        $tmpName = (string) ($file['tmp_name'] ?? '');
        if ($tmpName === '' || !is_uploaded_file($tmpName)) {
            throw new RuntimeException('Archivo temporal de subida invalido.');
        }

        $targetTmp = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'deploy_' . $mode . '_' . date('Ymd_His') . '_' . bin2hex(random_bytes(4)) . '.zip';
        if (!move_uploaded_file($tmpName, $targetTmp)) {
            throw new RuntimeException('No se pudo mover el ZIP subido a temporal.');
        }

        return [
            'mode' => $mode,
            'tmpZipPath' => $targetTmp,
            'originalName' => (string) ($file['name'] ?? 'upload.zip'),
            'size' => (int) ($file['size'] ?? 0),
        ];
    }

    /**
     * @return array{mode:string,backups:array<int,string>,files_extracted:int}
     */
    public static function installFromZip(string $mode, string $zipPath): array
    {
        $config = self::getModeConfig($mode);
        self::validateZipEntries($zipPath, $mode);

        $backups = [];
        if ($mode === self::MODE_NODE_MODULES) {
            $nodeModulesPath = __DIR__ . DIRECTORY_SEPARATOR . 'node_modules';
            if (is_dir($nodeModulesPath)) {
                $backupPath = __DIR__ . DIRECTORY_SEPARATOR . '_backup_node_modules_' . date('Ymd_His');
                if (!@rename($nodeModulesPath, $backupPath)) {
                    throw new RuntimeException('No se pudo crear backup de node_modules.');
                }
                $backups[] = $backupPath;
                self::cleanupOldBackups(__DIR__, '_backup_node_modules_', 3);
            }
        }

        if ($mode === self::MODE_CLIENT) {
            $publicRoot = (string) $config['extract_to'];
            $assetsPath = $publicRoot . DIRECTORY_SEPARATOR . 'assets';
            if (!is_dir($assetsPath) && !mkdir($assetsPath, 0755, true) && !is_dir($assetsPath)) {
                throw new RuntimeException('No se pudo crear carpeta assets en destino publico.');
            }

            $existingIndexFiles = glob($assetsPath . DIRECTORY_SEPARATOR . 'index*') ?: [];
            $existingIndexHtml = $publicRoot . DIRECTORY_SEPARATOR . 'index.html';
            if (is_file($existingIndexHtml)) {
                $existingIndexFiles[] = $existingIndexHtml;
            }

            if ($existingIndexFiles !== []) {
                $backupDir = __DIR__ . DIRECTORY_SEPARATOR . '_backup_client_assets_' . date('Ymd_His');
                if (!mkdir($backupDir, 0755, true) && !is_dir($backupDir)) {
                    throw new RuntimeException('No se pudo crear backup para assets cliente.');
                }

                foreach ($existingIndexFiles as $filePath) {
                    if (is_file($filePath)) {
                        $relativePath = $filePath === $existingIndexHtml
                            ? 'index.html'
                            : 'assets' . DIRECTORY_SEPARATOR . basename($filePath);
                        $dest = $backupDir . DIRECTORY_SEPARATOR . $relativePath;
                        $destDir = dirname($dest);
                        if (!is_dir($destDir) && !mkdir($destDir, 0755, true) && !is_dir($destDir)) {
                            throw new RuntimeException('No se pudo preparar backup para: ' . basename($filePath));
                        }
                        if (!@rename($filePath, $dest)) {
                            throw new RuntimeException('No se pudo mover asset anterior a backup: ' . basename($filePath));
                        }
                    }
                }

                $backups[] = $backupDir;
                self::cleanupOldBackups(__DIR__, '_backup_client_assets_', 5);
            }
        }

        $filesExtracted = self::extractZip($zipPath, (string) $config['extract_to']);

        return [
            'mode' => $mode,
            'backups' => $backups,
            'files_extracted' => $filesExtracted,
        ];
    }

    public static function printCliUsage(string $scriptName): void
    {
        $lines = [
            'Uso:',
            '  php ' . $scriptName . ' node_modules [--endpoint=https://tu-servidor/deployer.php] [--insecure]',
            '  php ' . $scriptName . ' client [--endpoint=https://tu-servidor/deployer.php] [--insecure]',
            '',
            'Variables de entorno soportadas:',
            '  DEPLOY_ENDPOINT',
        ];

        fwrite(STDOUT, implode(PHP_EOL, $lines) . PHP_EOL);
    }

    private static function addDirectoryToZip(ZipArchive $zip, string $sourceDir, string $zipRoot): int
    {
        if (!is_dir($sourceDir)) {
            throw new RuntimeException('Directorio no encontrado: ' . $sourceDir);
        }

        $added = 0;
        $sourceDir = rtrim($sourceDir, DIRECTORY_SEPARATOR);
        $iterator = new RecursiveIteratorIterator(
            new RecursiveDirectoryIterator($sourceDir, FilesystemIterator::SKIP_DOTS),
            RecursiveIteratorIterator::LEAVES_ONLY
        );

        foreach ($iterator as $fileInfo) {
            if (!$fileInfo->isFile()) {
                continue;
            }

            $absolutePath = $fileInfo->getPathname();
            $relative = substr($absolutePath, strlen($sourceDir) + 1);
            $relative = str_replace('\\', '/', $relative);
            $entryName = $zipRoot !== '' ? $zipRoot . '/' . $relative : $relative;

            if (!$zip->addFile($absolutePath, $entryName)) {
                throw new RuntimeException('No se pudo agregar archivo al ZIP: ' . $absolutePath);
            }
            $added++;
        }

        return $added;
    }

    /**
     * @param array<int,string> $patterns
     */
    private static function addGlobToZip(ZipArchive $zip, array $patterns): int
    {
        $added = 0;
        $seen = [];

        foreach ($patterns as $pattern) {
            $files = glob($pattern) ?: [];
            foreach ($files as $filePath) {
                if (!is_file($filePath)) {
                    continue;
                }

                $realPath = (string) realpath($filePath);
                if ($realPath === '' || isset($seen[$realPath])) {
                    continue;
                }

                $entryName = basename($realPath);
                if (!$zip->addFile($realPath, $entryName)) {
                    throw new RuntimeException('No se pudo agregar archivo al ZIP: ' . $realPath);
                }

                $seen[$realPath] = true;
                $added++;
            }
        }

        return $added;
    }

    /**
     * @param array<int,string> $patterns
     */
    private static function addRelativeGlobToZip(ZipArchive $zip, array $patterns, string $baseDir): int
    {
        if (!is_dir($baseDir)) {
            throw new RuntimeException('Directorio base no encontrado: ' . $baseDir);
        }

        $baseDir = rtrim((string) realpath($baseDir), DIRECTORY_SEPARATOR);
        if ($baseDir === '') {
            throw new RuntimeException('No se pudo resolver el directorio base del ZIP: ' . $baseDir);
        }

        $added = 0;
        $seen = [];

        foreach ($patterns as $pattern) {
            $files = glob($pattern) ?: [];
            foreach ($files as $filePath) {
                if (!is_file($filePath)) {
                    continue;
                }

                $realPath = (string) realpath($filePath);
                if ($realPath === '' || isset($seen[$realPath])) {
                    continue;
                }

                if (!str_starts_with($realPath, $baseDir . DIRECTORY_SEPARATOR) && $realPath !== $baseDir) {
                    throw new RuntimeException('Archivo fuera del directorio base: ' . $realPath);
                }

                $entryName = substr($realPath, strlen($baseDir) + 1);
                $entryName = str_replace('\\', '/', $entryName);
                if ($entryName === '') {
                    continue;
                }

                if (!$zip->addFile($realPath, $entryName)) {
                    throw new RuntimeException('No se pudo agregar archivo al ZIP: ' . $realPath);
                }

                $seen[$realPath] = true;
                $added++;
            }
        }

        return $added;
    }

    private static function assertClientBuildIsFresh(): void
    {
        $sourceIndex = __DIR__ . DIRECTORY_SEPARATOR . 'index.html';
        $builtIndex = __DIR__ . DIRECTORY_SEPARATOR . 'dist' . DIRECTORY_SEPARATOR . 'index.html';

        if (!is_file($builtIndex)) {
            throw new RuntimeException('No existe dist/index.html. Ejecuta la build de produccion antes de desplegar client.');
        }

        if (!is_file($sourceIndex)) {
            return;
        }

        $sourceMTime = filemtime($sourceIndex);
        $builtMTime = filemtime($builtIndex);
        if ($sourceMTime === false || $builtMTime === false) {
            return;
        }

        if ($sourceMTime > $builtMTime) {
            throw new RuntimeException('index.html es mas reciente que dist/index.html. Regenera dist antes de desplegar client para que produccion reciba el index actualizado.');
        }
    }

    private static function validateZipEntries(string $zipPath, string $mode): void
    {
        if (!is_file($zipPath)) {
            throw new RuntimeException('ZIP no encontrado para validar: ' . $zipPath);
        }

        $zip = new ZipArchive();
        if ($zip->open($zipPath) !== true) {
            throw new RuntimeException('No se pudo abrir el ZIP para validar: ' . $zipPath);
        }

        $validFiles = 0;
        for ($i = 0; $i < $zip->numFiles; $i++) {
            $entry = (string) $zip->getNameIndex($i);
            $normalized = str_replace('\\', '/', $entry);

            if ($normalized === '' || str_starts_with($normalized, '/') || str_contains($normalized, '../')) {
                $zip->close();
                throw new RuntimeException('Entrada ZIP insegura: ' . $entry);
            }

            if (str_ends_with($normalized, '/')) {
                continue;
            }

            if ($mode === self::MODE_NODE_MODULES) {
                if (!str_starts_with($normalized, 'node_modules/')) {
                    $zip->close();
                    throw new RuntimeException('El ZIP de node_modules contiene una ruta no permitida: ' . $entry);
                }
            }

            if ($mode === self::MODE_CLIENT) {
                $fileName = basename($normalized);
                $isRootIndexHtml = $normalized === 'index.html';
                $isAssetIndex = str_starts_with($normalized, 'assets/')
                    && $fileName === substr($normalized, strlen('assets/'))
                    && str_starts_with($fileName, 'index');

                if (!$isRootIndexHtml && !$isAssetIndex) {
                    $zip->close();
                    throw new RuntimeException('El ZIP de client contiene un archivo no permitido: ' . $entry);
                }
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
        if (!is_dir($targetPath) && !mkdir($targetPath, 0755, true) && !is_dir($targetPath)) {
            throw new RuntimeException('No se pudo crear destino de extraccion: ' . $targetPath);
        }

        $zip = new ZipArchive();
        if ($zip->open($zipPath) !== true) {
            throw new RuntimeException('No se pudo abrir ZIP para extraer: ' . $zipPath);
        }

        $filesInArchive = 0;
        for ($i = 0; $i < $zip->numFiles; $i++) {
            $entry = (string) $zip->getNameIndex($i);
            if (!str_ends_with($entry, '/')) {
                $filesInArchive++;
            }
        }

        if (!$zip->extractTo($targetPath)) {
            $zip->close();
            throw new RuntimeException('Error al extraer ZIP en: ' . $targetPath);
        }

        $zip->close();
        return $filesInArchive;
    }

    private static function cleanupOldBackups(string $basePath, string $prefix, int $keep): void
    {
        $pattern = $basePath . DIRECTORY_SEPARATOR . $prefix . '*';
        $dirs = glob($pattern, GLOB_ONLYDIR) ?: [];

        usort($dirs, static function (string $a, string $b): int {
            return filemtime($b) <=> filemtime($a);
        });

        $toDelete = array_slice($dirs, $keep);
        foreach ($toDelete as $dir) {
            self::deleteDirectory($dir);
        }
    }

    private static function deleteDirectory(string $dir): void
    {
        if (!is_dir($dir)) {
            return;
        }

        $items = new RecursiveIteratorIterator(
            new RecursiveDirectoryIterator($dir, FilesystemIterator::SKIP_DOTS),
            RecursiveIteratorIterator::CHILD_FIRST
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

    private static function uploadErrorMessage(int $errorCode): string
    {
        return match ($errorCode) {
            UPLOAD_ERR_INI_SIZE => 'El archivo excede upload_max_filesize.',
            UPLOAD_ERR_FORM_SIZE => 'El archivo excede MAX_FILE_SIZE del formulario.',
            UPLOAD_ERR_PARTIAL => 'El archivo se subio parcialmente.',
            UPLOAD_ERR_NO_FILE => 'No se envio archivo.',
            UPLOAD_ERR_NO_TMP_DIR => 'No existe carpeta temporal.',
            UPLOAD_ERR_CANT_WRITE => 'No se pudo escribir en disco.',
            UPLOAD_ERR_EXTENSION => 'Una extension de PHP detuvo la subida.',
            default => 'Error desconocido de subida.',
        };
    }
}
