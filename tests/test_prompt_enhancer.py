import pytest

from kie_api.exceptions import PromptTemplateRenderError
from kie_api.enums import PromptPolicy
from kie_api.models import NormalizedRequest
from kie_api.registry.loader import load_registry
from kie_api.services.prompt_enhancer import PromptEnhancer


def test_prompt_enhancer_off_policy_uses_raw_prompt() -> None:
    enhancer = PromptEnhancer(load_registry())

    result = enhancer.prepare(
        NormalizedRequest(
            model_key="nano-banana-pro",
            provider_model="nano-banana-pro",
            task_mode="text_to_image",
            prompt="a clean product photo",
            raw_prompt="a clean product photo",
            prompt_policy=PromptPolicy.OFF,
        )
    )

    assert result.final_prompt_used == "a clean product photo"
    assert result.enhanced_prompt is None


def test_prompt_enhancer_preview_policy_returns_preview_only() -> None:
    enhancer = PromptEnhancer(load_registry())

    result = enhancer.prepare(
        NormalizedRequest(
            model_key="kling-3.0-t2v",
            provider_model="kling-3.0/video",
            task_mode="text_to_video",
            prompt="  a   dramatic dolly shot  ",
            raw_prompt="  a   dramatic dolly shot  ",
            prompt_policy=PromptPolicy.PREVIEW,
        )
    )

    assert result.preview_only is True
    assert result.final_prompt_used is None
    assert result.enhanced_prompt == "a dramatic dolly shot"


def test_prompt_enhancer_auto_policy_uses_backend_and_profile() -> None:
    registry = load_registry()

    def backend(request, system_prompt):
        assert "Kling 3.0 image-to-video using one start frame" in system_prompt
        assert "camera drifts forward" in system_prompt
        return f"ENHANCED::{request.raw_prompt}"

    enhancer = PromptEnhancer(registry, backend=backend)
    result = enhancer.prepare(
        NormalizedRequest(
            model_key="kling-3.0-i2v",
            provider_model="kling-3.0/video",
            task_mode="image_to_video",
            prompt="camera drifts forward",
            raw_prompt="camera drifts forward",
            prompt_policy=PromptPolicy.AUTO,
        )
    )

    assert result.profile_key == "kling_3_0_i2v_first_frame_v1"
    assert result.final_prompt_used == "ENHANCED::camera drifts forward"


def test_prompt_enhancer_resolves_explicit_profile_key_and_override() -> None:
    registry = load_registry()
    enhancer = PromptEnhancer(registry)

    request = NormalizedRequest(
        model_key="nano-banana-2",
        provider_model="nano-banana-2",
        task_mode="text_to_image",
        prompt="make this cleaner",
        raw_prompt="make this cleaner",
        prompt_policy=PromptPolicy.PREVIEW,
        prompt_profile_key="nano_banana_2_v1",
        system_prompt_override="Use a strict house style system prompt.",
    )
    context = enhancer.resolve_context(request)
    result = enhancer.prepare(request)

    assert context.resolved_profile_key == "nano_banana_2_v1"
    assert context.system_prompt == "Use a strict house style system prompt."
    assert context.system_prompt_source == "override"
    assert result.profile_key == "nano_banana_2_v1"
    assert result.system_prompt == "Use a strict house style system prompt."
    assert result.system_prompt_source == "override"
    assert result.profile_label == "Nano Banana 2 Prompt Enhancer v1"
    assert result.preview_only is True


def test_prompt_profile_resolution_uses_model_default_key() -> None:
    registry = load_registry()
    profile = registry.resolve_prompt_profile("nano-banana-pro")

    assert profile is not None
    assert profile.key == "nano_banana_pro_v1"
    assert profile.source_path is not None
    assert "Preserve the user's core intent." in profile.prompt_markdown


def test_prompt_enhancer_resolves_input_pattern_specific_preset() -> None:
    registry = load_registry()
    enhancer = PromptEnhancer(registry)

    context = enhancer.resolve_context(
        NormalizedRequest(
            model_key="kling-3.0-i2v",
            provider_model="kling-3.0/video",
            task_mode="image_to_video",
            prompt="bridge the two endpoint frames smoothly",
            raw_prompt="bridge the two endpoint frames smoothly",
            prompt_policy=PromptPolicy.PREVIEW,
            images=[
                {"media_type": "image", "url": "https://example.com/start.png"},
                {"media_type": "image", "url": "https://example.com/end.png"},
            ],
        )
    )

    assert str(context.input_pattern) == "first_last_frames"
    assert str(context.resolution_source) == "model_default"
    assert context.resolved_preset_key == "kling_3_0_i2v_first_last_frame_v1"
    assert "{{user_prompt}}" in (context.resolved_template or "")
    assert "bridge the two endpoint frames smoothly" in (context.rendered_system_prompt or "")


def test_prompt_enhancer_resolves_banana_prompt_only_preset() -> None:
    registry = load_registry()
    enhancer = PromptEnhancer(registry)

    context = enhancer.resolve_context(
        NormalizedRequest(
            model_key="nano-banana-2",
            provider_model="nano-banana-2",
            task_mode="text_to_image",
            prompt="create a clean premium editorial illustration",
            raw_prompt="create a clean premium editorial illustration",
            prompt_policy=PromptPolicy.PREVIEW,
        )
    )

    assert str(context.input_pattern) == "prompt_only"
    assert context.resolved_preset_key == "nano_banana_2_text_to_image_v1"
    assert "create a clean premium editorial illustration" in (context.rendered_system_prompt or "")


def test_prompt_enhancer_raises_for_unresolved_template_variables(tmp_path) -> None:
    prompt_root = tmp_path / "prompt_profiles"
    preset_dir = prompt_root / "broken_preset"
    preset_dir.mkdir(parents=True)
    (preset_dir / "metadata.yaml").write_text(
        "\n".join(
            [
                "key: broken_preset",
                "label: Broken Preset",
                "version: v1",
                "applies_to_models:",
                "  - nano-banana-pro",
            ]
        ),
        encoding="utf-8",
    )
    (preset_dir / "prompt.md").write_text(
        "Use this value: {{missing_value}}",
        encoding="utf-8",
    )

    registry = load_registry(prompt_profiles_root=prompt_root)
    enhancer = PromptEnhancer(registry)

    with pytest.raises(PromptTemplateRenderError):
        enhancer.resolve_context(
            NormalizedRequest(
                model_key="nano-banana-pro",
                provider_model="nano-banana-pro",
                task_mode="text_to_image",
                prompt="make it cinematic",
                raw_prompt="make it cinematic",
                prompt_policy=PromptPolicy.PREVIEW,
                prompt_profile_key="broken_preset",
            )
        )
