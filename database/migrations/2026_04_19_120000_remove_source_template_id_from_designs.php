<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (Schema::hasTable('designs') && Schema::hasColumn('designs', 'source_template_id')) {
            Schema::table('designs', function (Blueprint $table) {
                $table->dropConstrainedForeignId('source_template_id');
            });
        }

        if (
            Schema::hasTable('design_templates')
            && ! Schema::hasIndex('design_templates', 'design_templates_base_design_id_unique')
        ) {
            Schema::table('design_templates', function (Blueprint $table) {
                $table->unique('base_design_id', 'design_templates_base_design_id_unique');
            });
        }
    }

    public function down(): void
    {
        if (
            Schema::hasTable('design_templates')
            && Schema::hasIndex('design_templates', 'design_templates_base_design_id_unique')
        ) {
            Schema::table('design_templates', function (Blueprint $table) {
                $table->dropUnique('design_templates_base_design_id_unique');
            });
        }

        if (Schema::hasTable('designs') && ! Schema::hasColumn('designs', 'source_template_id')) {
            Schema::table('designs', function (Blueprint $table) {
                $table->foreignId('source_template_id')
                    ->nullable()
                    ->after('selected_template_id')
                    ->constrained('design_templates')
                    ->nullOnDelete();
            });
        }
    }
};
