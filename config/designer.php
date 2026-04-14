<?php

return [
    'image_uploads' => [
        'max_width' => (int) env('DESIGNER_IMAGE_MAX_WIDTH', 2400),
        'max_height' => (int) env('DESIGNER_IMAGE_MAX_HEIGHT', 2400),
        'jpeg_quality' => (int) env('DESIGNER_IMAGE_JPEG_QUALITY', 95),
        'webp_quality' => (int) env('DESIGNER_IMAGE_WEBP_QUALITY', 95),
    ],
];
