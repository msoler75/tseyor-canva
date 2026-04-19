<?php

namespace Database\Seeders;

use App\Services\DemoTemplateFactory;
use Illuminate\Database\Seeder;

class DesignTemplateSeeder extends Seeder
{
    /**
     * Seed three published generic templates for the app.
     */
    public function run(): void
    {
        app(DemoTemplateFactory::class)->create();
    }
}
