<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('designs', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->nullable()->constrained()->nullOnDelete();
            $table->uuid('uuid')->unique();
            $table->string('name', 255);
            $table->boolean('name_manual')->default(false);
            $table->string('objective', 120)->nullable()->index();
            $table->string('output_type', 40)->nullable()->index();
            $table->string('format', 40)->nullable()->index();
            $table->string('size_label', 120)->nullable();
            $table->unsignedInteger('surface_width')->nullable();
            $table->unsignedInteger('surface_height')->nullable();
            $table->string('template_category', 120)->nullable();
            $table->string('selected_template_id', 120)->nullable();
            $table->string('thumbnail_path', 1024)->nullable();
            $table->json('state');
            $table->string('status', 32)->default('draft')->index();
            $table->timestamp('last_opened_at')->nullable()->index();
            $table->timestamps();

            $table->index(['user_id', 'updated_at']);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('designs');
    }
};
