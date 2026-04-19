<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasOne;

class Design extends Model
{
    use HasFactory;

    /**
     * @var list<string>
     */
    protected $fillable = [
        'user_id',
        'uuid',
        'name',
        'name_manual',
        'objective',
        'output_type',
        'format',
        'size_label',
        'surface_width',
        'surface_height',
        'template_category',
        'selected_template_id',
        'thumbnail_path',
        'state',
        'status',
        'last_opened_at',
        'public',
    ];

    /**
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'name_manual' => 'boolean',
            'surface_width' => 'integer',
            'surface_height' => 'integer',
            'state' => 'array',
            'last_opened_at' => 'datetime',
            'public' => 'boolean',
        ];
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function selectedTemplate(): BelongsTo
    {
        return $this->belongsTo(DesignTemplate::class, 'selected_template_id', 'uuid');
    }

    public function baseTemplate(): HasOne
    {
        return $this->hasOne(DesignTemplate::class, 'base_design_id');
    }

    public function getRouteKeyName(): string
    {
        return 'uuid';
    }
}
