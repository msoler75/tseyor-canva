<?php

namespace Tests\Unit;

use App\Support\DesignerStateSync;
use PHPUnit\Framework\Attributes\Test;
use PHPUnit\Framework\TestCase;

class DesignerStateSyncTest extends TestCase
{
    #[Test]
    public function it_syncs_title_from_content_to_element_layout(): void
    {
        $content = ['title' => 'Hello World', 'subtitle' => ''];
        $elementLayout = ['background' => []];

        DesignerStateSync::syncContentAndElementLayout($content, $elementLayout);

        $this->assertSame('Hello World', $content['title']);
        $this->assertSame('Hello World', $elementLayout['title']['text']);
    }

    #[Test]
    public function it_removes_layout_text_when_content_is_empty(): void
    {
        $content = ['title' => '', 'subtitle' => ''];
        $elementLayout = ['title' => ['text' => 'Old Title'], 'subtitle' => ['text' => 'Old Subtitle']];

        DesignerStateSync::syncContentAndElementLayout($content, $elementLayout);

        $this->assertArrayNotHasKey('text', $elementLayout['title']);
        $this->assertArrayNotHasKey('text', $elementLayout['subtitle']);
    }

    #[Test]
    public function it_syncs_subtitle(): void
    {
        $content = ['title' => 'T', 'subtitle' => 'Subtitle value'];
        $elementLayout = ['background' => []];

        DesignerStateSync::syncContentAndElementLayout($content, $elementLayout);

        $this->assertSame('Subtitle value', $content['subtitle']);
        $this->assertSame('Subtitle value', $elementLayout['subtitle']['text']);
    }

    #[Test]
    public function it_syncs_contact_and_extra(): void
    {
        $content = ['title' => '', 'subtitle' => '', 'contact' => 'info@test.com', 'extra' => 'Note'];
        $elementLayout = ['background' => []];

        DesignerStateSync::syncContentAndElementLayout($content, $elementLayout);

        $this->assertSame('info@test.com', $elementLayout['contact']['text']);
        $this->assertSame('Note', $elementLayout['extra']['text']);
    }

    #[Test]
    public function it_syncs_meta_from_date_and_time(): void
    {
        $content = ['title' => '', 'subtitle' => '', 'date' => '2024-01-15', 'time' => '14:30'];
        $elementLayout = ['background' => []];

        DesignerStateSync::syncContentAndElementLayout($content, $elementLayout);

        $this->assertStringContainsString('2024-01-15', $elementLayout['meta']['text']);
        $this->assertStringContainsString('14:30', $elementLayout['meta']['text']);
    }

    #[Test]
    public function it_trims_whitespace_from_text_values(): void
    {
        $content = ['title' => '  Spaced Title  ', 'subtitle' => ''];
        $elementLayout = ['background' => []];

        DesignerStateSync::syncContentAndElementLayout($content, $elementLayout);

        $this->assertSame('Spaced Title', $content['title']);
        $this->assertSame('Spaced Title', $elementLayout['title']['text']);
    }

    #[Test]
    public function it_creates_layout_entry_if_missing(): void
    {
        $content = ['title' => 'New', 'subtitle' => ''];
        $elementLayout = ['background' => []];

        DesignerStateSync::syncContentAndElementLayout($content, $elementLayout);

        $this->assertArrayHasKey('title', $elementLayout);
        $this->assertIsArray($elementLayout['title']);
    }

    #[Test]
    public function it_does_not_affect_other_keys(): void
    {
        $content = ['title' => 'Test', 'subtitle' => ''];
        $elementLayout = ['background' => ['backgroundColor' => '#fff'], 'custom-key' => ['x' => 10]];

        DesignerStateSync::syncContentAndElementLayout($content, $elementLayout);

        $this->assertSame('#fff', $elementLayout['background']['backgroundColor']);
        $this->assertSame(10, $elementLayout['custom-key']['x']);
    }

    #[Test]
    public function it_handles_empty_content_gracefully(): void
    {
        $content = [];
        $elementLayout = ['background' => []];

        DesignerStateSync::syncContentAndElementLayout($content, $elementLayout);

        $this->assertArrayHasKey('title', $content);
        $this->assertSame('', $content['title']);
        $this->assertArrayHasKey('subtitle', $content);
    }
}
