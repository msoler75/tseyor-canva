<?php

use App\Http\Controllers\AuthController;
use App\Http\Controllers\DesignAssetController;
use App\Http\Controllers\DesignController;
use App\Http\Controllers\DesignerController;
use Illuminate\Support\Facades\Route;

Route::get('/', [DesignerController::class, 'welcome'])->name('designer.welcome');

Route::prefix('auth')->group(function (): void {
    // si estamos en desarrollo, permitimos login dev
    Route::get('/login-dev', [AuthController::class, 'loginDev'])->name('auth.login.dev');
    Route::get('/login', [AuthController::class, 'login'])->name('auth.login');
    Route::post('/login', [AuthController::class, 'portalCallback'])->name('auth.login.callback');
    Route::middleware('auth')->get('/me', [AuthController::class, 'me'])->name('auth.me');
    Route::middleware('auth')->post('/logout', [AuthController::class, 'logout'])->name('auth.logout');
});

Route::prefix('designer')->middleware('auth')->group(function (): void {
    Route::put('/state', [DesignerController::class, 'saveState'])->name('designer.state.save');
    Route::delete('/state', [DesignerController::class, 'resetState'])->name('designer.state.reset');
    Route::post('/uploads', [DesignerController::class, 'storeUpload'])->name('designer.uploads.store');
    Route::get('/storage/{path}', [DesignerController::class, 'showUpload'])
        ->where('path', '.*')
        ->name('designer.uploads.show');
    Route::get('/objective', [DesignerController::class, 'objective'])->name('designer.objective');
    Route::get('/format', [DesignerController::class, 'format'])->name('designer.format');
    Route::get('/content', [DesignerController::class, 'content'])->name('designer.content');
    Route::get('/templates', [DesignerController::class, 'templates'])->name('designer.templates');
    Route::get('/editor', [DesignerController::class, 'editor'])->name('designer.editor');
    Route::get('/export', [DesignerController::class, 'export'])->name('designer.export');
    Route::get('/designs', [DesignController::class, 'index'])->name('designer.designs.index');
    Route::post('/designs', [DesignController::class, 'store'])->name('designer.designs.store');
    Route::get('/designs/{design:uuid}', [DesignController::class, 'show'])->name('designer.designs.show');
    Route::get('/designs/{design:uuid}/edit', [DesignerController::class, 'editor'])->name('designer.designs.edit');
    Route::put('/designs/{design:uuid}', [DesignController::class, 'update'])->name('designer.designs.update');
    Route::patch('/designs/{design:uuid}/rename', [DesignController::class, 'rename'])->name('designer.designs.rename');
    Route::post('/designs/{design:uuid}/duplicate', [DesignController::class, 'duplicate'])->name('designer.designs.duplicate');
    Route::delete('/designs/{design:uuid}', [DesignController::class, 'destroy'])->name('designer.designs.destroy');

    Route::get('/assets', [DesignAssetController::class, 'index'])->name('designer.assets.index');
    Route::post('/assets', [DesignAssetController::class, 'store'])->name('designer.assets.store');
});
