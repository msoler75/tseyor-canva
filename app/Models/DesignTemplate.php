<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class DesignTemplate extends Model
{
    use HasFactory;

    /**
     * @var list<string>
     */
    protected $fillable = [
        'uuid',
        'base_design_id',
        'title',
        'description',
        'category_ids',
        'objective_ids',
        'adaptation_mode',
        'field_mappings',
        'status',
        'featured',
        'sort_order',
        'published_at',
    ];

    /**
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'category_ids' => 'array',
            'objective_ids' => 'array',
            'field_mappings' => 'array',
            'featured' => 'boolean',
            'sort_order' => 'integer',
            'published_at' => 'datetime',
        ];
    }

    public function baseDesign(): BelongsTo
    {
        return $this->belongsTo(Design::class, 'base_design_id');
    }

    public function getRouteKeyName(): string
    {
        return 'uuid';
    }
}
