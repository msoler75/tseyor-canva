<?php

use App\Http\Controllers\AuthController;
use App\Http\Controllers\DeployController;
use App\Http\Controllers\DesignAssetController;
use App\Http\Controllers\DesignController;
use App\Http\Controllers\DesignTemplateController;
use App\Http\Controllers\DesignerController;
use App\Http\Controllers\FontController;
use Illuminate\Support\Facades\Route;

Route::get('/', [DesignerController::class, 'welcome'])->name('designer.welcome');

Route::prefix('auth')->group(function (): void {
    Route::get('/login', [AuthController::class, 'login'])->name('auth.login');
    Route::post('/login', [AuthController::class, 'portalCallback'])->name('auth.login.callback');
    Route::middleware('auth')->get('/me', [AuthController::class, 'me'])->name('auth.me');
    Route::middleware('auth')->post('/logout', [AuthController::class, 'logout'])->name('auth.logout');
});

Route::prefix('designer')->group(function (): void {
    Route::put('/state', [DesignerController::class, 'saveState'])->name('designer.state.save');
    Route::delete('/state', [DesignerController::class, 'resetState'])->name('designer.state.reset');
    Route::post('/uploads', [DesignerController::class, 'storeUpload'])->name('designer.uploads.store');
    Route::get('/storage/uploads/{path}', [DesignerController::class, 'showUpload'])
        ->where('path', '.*')
        ->name('designer.uploads.show');
    Route::get('/storage/thumbnails/{path}', [DesignerController::class, 'showThumbnail'])
        ->where('path', '.*')
        ->name('designer.thumbnails.show');
    Route::get('/designs/{design:uuid}', [DesignController::class, 'show'])->name('designer.designs.show');
    // Las rutas de edición y editor quedan accesibles sin autenticación
    Route::get('/editor', [DesignerController::class, 'editor'])->name('designer.editor');

    Route::get('/designs', [DesignController::class, 'index'])->name('designer.designs.index');
    Route::post('/designs', [DesignController::class, 'store'])->name('designer.designs.store');
    Route::get('/designs/{design:uuid}/edit', [DesignerController::class, 'editor'])->name('designer.designs.edit');
    Route::put('/designs/{design:uuid}', [DesignController::class, 'update'])->name('designer.designs.update');
    Route::patch('/designs/{design:uuid}/rename', [DesignController::class, 'rename'])->name('designer.designs.rename');
    Route::post('/designs/{design:uuid}/duplicate', [DesignController::class, 'duplicate'])->name('designer.designs.duplicate');
    Route::delete('/designs/{design:uuid}', [DesignController::class, 'destroy'])->name('designer.designs.destroy');

    Route::get('/template-inventory', [DesignTemplateController::class, 'inventory'])->name('designer.templates.inventory');
    Route::get('/design-templates', [DesignTemplateController::class, 'index'])->name('designer.templates.index');
    Route::post('/designs/{design:uuid}/template', [DesignTemplateController::class, 'store'])->name('designer.templates.store');
    Route::patch('/design-templates/{template:uuid}', [DesignTemplateController::class, 'update'])->name('designer.templates.update');
    Route::post('/design-templates/{template:uuid}/generate', [DesignTemplateController::class, 'generate'])->name('designer.templates.generate');

    Route::get('/assets', [DesignAssetController::class, 'index'])->name('designer.assets.index');
    Route::post('/assets', [DesignAssetController::class, 'store'])->name('designer.assets.store');
});

Route::post('/deploy/build', [DeployController::class, 'build'])->name('deploy.build');

// Ruta para servir fuentes locales solo si está habilitado en config/designer.php
if (config('designer.serve_fonts_route')) {
    Route::get('/fonts/{filename}', [FontController::class, 'serve'])->where('filename', '.*');
}
