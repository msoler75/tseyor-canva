<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (Schema::hasTable('design_templates') && Schema::hasColumn('design_templates', 'created_by')) {
            Schema::table('design_templates', function (Blueprint $table) {
                $table->dropConstrainedForeignId('created_by');
            });
        }
    }

    public function down(): void
    {
        if (Schema::hasTable('design_templates') && ! Schema::hasColumn('design_templates', 'created_by')) {
            Schema::table('design_templates', function (Blueprint $table) {
                $table->foreignId('created_by')->nullable()->after('base_design_id')->constrained('users')->nullOnDelete();
            });
        }
    }
};

