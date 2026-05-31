<?php

namespace Tests\Unit;

use PHPUnit\Framework\Attributes\Test;
use PHPUnit\Framework\TestCase;

class NormalizeFunctionsTest extends TestCase
{
    private function callPrivateMethod(object $object, string $method, array $args = []): mixed
    {
        $reflection = new \ReflectionMethod($object, $method);
        $reflection->setAccessible(true);
        return $reflection->invokeArgs(null, $args);
    }

    #[Test]
    public function it_resolves_simple_text_values(): void
    {
        $content = ['title' => 'Hello', 'subtitle' => 'World'];
        $class = new \App\Support\DesignerStateSync();

        $reflection = new \ReflectionMethod(\App\Support\DesignerStateSync::class, 'resolveTextValue');
        $reflection->setAccessible(true);

        $title = $reflection->invoke(null, 'title', $content);
        $subtitle = $reflection->invoke(null, 'subtitle', $content);

        $this->assertSame('Hello', $title);
        $this->assertSame('World', $subtitle);
    }

    #[Test]
    public function it_resolves_meta_from_date_and_time(): void
    {
        $content = ['date' => '2024-06-15', 'time' => '10:30'];
        $class = new \App\Support\DesignerStateSync();

        $reflection = new \ReflectionMethod(\App\Support\DesignerStateSync::class, 'resolveTextValue');
        $reflection->setAccessible(true);

        $meta = $reflection->invoke(null, 'meta', $content);

        $this->assertStringContainsString('2024-06-15', $meta);
        $this->assertStringContainsString('10:30', $meta);
    }

    #[Test]
    public function it_handles_missing_meta_parts(): void
    {
        $content = ['date' => '2024-06-15'];
        $class = new \App\Support\DesignerStateSync();

        $reflection = new \ReflectionMethod(\App\Support\DesignerStateSync::class, 'resolveTextValue');
        $reflection->setAccessible(true);

        $meta = $reflection->invoke(null, 'meta', $content);

        $this->assertStringContainsString('2024-06-15', $meta);
    }

    #[Test]
    public function it_returns_default_for_unknown_keys(): void
    {
        $content = ['unknown_key' => 'value'];
        $class = new \App\Support\DesignerStateSync();

        $reflection = new \ReflectionMethod(\App\Support\DesignerStateSync::class, 'resolveTextValue');
        $reflection->setAccessible(true);

        $result = $reflection->invoke(null, 'unknown_key', $content);

        $this->assertSame('value', $result);
    }
}
