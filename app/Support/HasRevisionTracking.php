<?php

namespace App\Support;

trait HasRevisionTracking
{
    private function nextRevision(int ...$values): int
    {
        return (max($values) ?: 0) + 1;
    }
}
