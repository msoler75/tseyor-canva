<?php

return [
    'endpoint' => env('DEPLOY_ENDPOINT'),
    'token' => env('DEPLOY_TOKEN'),
    'verify_ssl' => env('DEPLOY_VERIFY_SSL', true),
    'timeout' => env('DEPLOY_TIMEOUT', 1800),
    'route_enabled' => env('DEPLOY_ROUTE_ENABLED', false),
];
