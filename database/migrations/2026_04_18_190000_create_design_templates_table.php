<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('design_templates', function (Blueprint $table) {
            $table->id();
            $table->uuid('uuid')->unique();
            $table->foreignId('base_design_id')->unique()->constrained('designs')->cascadeOnDelete();
            $table->string('title', 255);
            $table->text('description')->nullable();
            $table->json('category_ids');
            $table->json('objective_ids');
            $table->string('adaptation_mode', 40)->default('proportional');
            $table->json('field_mappings')->nullable();
            $table->string('status', 32)->default('draft')->index();
            $table->boolean('featured')->default(false)->index();
            $table->unsignedInteger('sort_order')->default(0)->index();
            $table->timestamp('published_at')->nullable();
            $table->timestamps();

            $table->index(['status', 'sort_order']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('design_templates');
    }
};
