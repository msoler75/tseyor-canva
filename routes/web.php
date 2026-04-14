<?php

use App\Http\Controllers\DesignerController;
use Illuminate\Support\Facades\Route;

Route::get('/', [DesignerController::class, 'welcome'])->name('designer.welcome');

Route::prefix('designer')->group(function (): void {
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
});
