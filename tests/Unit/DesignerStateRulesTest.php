<?php

namespace Tests\Unit;

use App\Support\DesignerStateRules;
use PHPUnit\Framework\Attributes\Test;
use PHPUnit\Framework\TestCase;

class DesignerStateRulesTest extends TestCase
{
    #[Test]
    public function it_returns_validation_rules_array(): void
    {
        $rules = DesignerStateRules::rules();

        $this->assertIsArray($rules);
        $this->assertNotEmpty($rules);
    }

    #[Test]
    public function it_requires_state_to_be_an_array(): void
    {
        $rules = DesignerStateRules::rules();

        $this->assertArrayHasKey('state', $rules);
        $this->assertContains('required', $rules['state']);
        $this->assertContains('array', $rules['state']);
    }

    #[Test]
    public function it_validates_mode_field(): void
    {
        $rules = DesignerStateRules::rules();

        $this->assertArrayHasKey('state.mode', $rules);
        $this->assertContains('required', $rules['state.mode']);
        $this->assertContains('in:guided,direct', $rules['state.mode']);
    }

    #[Test]
    public function it_validates_outputType(): void
    {
        $rules = DesignerStateRules::rules();

        $this->assertArrayHasKey('state.outputType', $rules);
        $this->assertContains('in:print,digital', $rules['state.outputType']);
    }

    #[Test]
    public function it_validates_content(): void
    {
        $rules = DesignerStateRules::rules();

        $this->assertArrayHasKey('state.content', $rules);
        $this->assertContains('required', $rules['state.content']);
        $this->assertContains('array', $rules['state.content']);
    }

    #[Test]
    public function it_validates_elementLayout(): void
    {
        $rules = DesignerStateRules::rules();

        $this->assertArrayHasKey('state.elementLayout', $rules);
        $this->assertContains('required', $rules['state.elementLayout']);
    }

    #[Test]
    public function it_validates_element_layout_position_fields(): void
    {
        $rules = DesignerStateRules::rules();

        $this->assertArrayHasKey('state.elementLayout.*.x', $rules);
        $this->assertArrayHasKey('state.elementLayout.*.y', $rules);
        $this->assertArrayHasKey('state.elementLayout.*.w', $rules);
        $this->assertArrayHasKey('state.elementLayout.*.h', $rules);
        $this->assertArrayHasKey('state.elementLayout.*.rotation', $rules);
        $this->assertContains('between:-360,360', $rules['state.elementLayout.*.rotation']);
    }

    #[Test]
    public function it_validates_customElements_type(): void
    {
        $rules = DesignerStateRules::rules();

        $this->assertArrayHasKey('state.customElements.*.type', $rules);
        $this->assertContains('in:text,image,shape,linkedText,qr', $rules['state.customElements.*.type']);
    }

    #[Test]
    public function it_validates_upload_status(): void
    {
        $rules = DesignerStateRules::rules();

        $this->assertArrayHasKey('state.customElements.*.uploadStatus', $rules);
        $this->assertContains('in:pending,uploading,done,error', $rules['state.customElements.*.uploadStatus']);
    }

    #[Test]
    public function it_validates_pages_structure(): void
    {
        $rules = DesignerStateRules::rules();

        $this->assertArrayHasKey('state.pages', $rules);
        $this->assertArrayHasKey('state.pages.*.id', $rules);
        $this->assertArrayHasKey('state.pages.*.content', $rules);
        $this->assertArrayHasKey('state.pages.*.elementLayout', $rules);
        $this->assertArrayHasKey('state.pages.*.customElements', $rules);
    }

    #[Test]
    public function it_validates_userUploadedImages(): void
    {
        $rules = DesignerStateRules::rules();

        $this->assertArrayHasKey('state.userUploadedImages', $rules);
        $this->assertArrayHasKey('state.userUploadedImages.*.id', $rules);
        $this->assertArrayHasKey('state.userUploadedImages.*.uploadStatus', $rules);
        $this->assertContains('in:pending,uploading,done,error', $rules['state.userUploadedImages.*.uploadStatus']);
    }

    #[Test]
    public function it_validates_revision_fields(): void
    {
        $rules = DesignerStateRules::rules();

        $this->assertArrayHasKey('state.stateRevision', $rules);
        $this->assertContains('integer', $rules['state.stateRevision']);
        $this->assertContains('min:0', $rules['state.stateRevision']);

        $this->assertArrayHasKey('state.templateRevision', $rules);
        $this->assertContains('integer', $rules['state.templateRevision']);
    }

    #[Test]
    public function it_validates_designSurface_width_and_height(): void
    {
        $rules = DesignerStateRules::rules();

        $this->assertArrayHasKey('state.designSurface.width', $rules);
        $this->assertArrayHasKey('state.designSurface.height', $rules);
    }

    #[Test]
    public function it_validates_background_image_fields(): void
    {
        $rules = DesignerStateRules::rules();

        $this->assertArrayHasKey('state.elementLayout.background.backgroundImageSrc', $rules);
        $this->assertArrayHasKey('state.elementLayout.background.backgroundImageOpacity', $rules);
        $this->assertContains('between:0,100', $rules['state.elementLayout.background.backgroundImageOpacity']);
    }

    #[Test]
    public function it_validates_paragraph_styles(): void
    {
        $rules = DesignerStateRules::rules();

        $this->assertArrayHasKey('state.elementLayout.*.paragraphStyles', $rules);
        $this->assertArrayHasKey('state.elementLayout.*.paragraphStyles.*.fontSize', $rules);
        $this->assertContains('between:8,200', $rules['state.elementLayout.*.paragraphStyles.*.fontSize']);
    }

    #[Test]
    public function it_validates_text_effect_and_shadow_presets(): void
    {
        $rules = DesignerStateRules::rules();

        $this->assertArrayHasKey('state.elementLayout.*.textEffectMode', $rules);
        $this->assertArrayHasKey('state.elementLayout.*.shadowPreset', $rules);
    }

    #[Test]
    public function it_validates_new_qr_fields(): void
    {
        $rules = DesignerStateRules::rules();

        $this->assertArrayHasKey('state.customElements.*.url', $rules);
        $this->assertContains('max:2048', $rules['state.customElements.*.url']);
        $this->assertArrayHasKey('state.customElements.*.qrDataUrl', $rules);
    }

    #[Test]
    public function it_accepts_custom_prefix(): void
    {
        $rules = DesignerStateRules::rules('designer');

        $this->assertArrayHasKey('designer', $rules);
        $this->assertArrayHasKey('designer.mode', $rules);
        $this->assertArrayNotHasKey('state.mode', $rules);
    }

    #[Test]
    public function all_rules_have_expected_structure(): void
    {
        $rules = DesignerStateRules::rules();

        foreach ($rules as $key => $constraints) {
            $this->assertIsArray($constraints, "Rule for '{$key}' must be an array");
            foreach ($constraints as $constraint) {
                $this->assertIsString($constraint, "Constraint for '{$key}' must be a string");
            }
        }
    }
}
