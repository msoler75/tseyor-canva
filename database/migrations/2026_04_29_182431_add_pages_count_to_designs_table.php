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
        Schema::table('designs', function (Blueprint $table) {
            $table->unsignedTinyInteger('pages_count')->default(1)->after('state');
        });

        // Backfill: actualizar diseños existentes contando las páginas en state
        \Illuminate\Support\Facades\DB::table('designs')->orderBy('id')->eachById(function ($design) {
            $state = json_decode($design->state, true);
            $pages = $state['pages'] ?? [];
            $count = is_array($pages) && count($pages) > 0 ? count($pages) : 1;
            \Illuminate\Support\Facades\DB::table('designs')->where('id', $design->id)->update(['pages_count' => $count]);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('designs', function (Blueprint $table) {
            $table->dropColumn('pages_count');
        });
    }
};
