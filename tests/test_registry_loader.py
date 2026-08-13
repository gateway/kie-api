import subprocess
import sys
from importlib import resources
from pathlib import Path

import pytest

from kie_api.exceptions import ModelNotFoundError, SpecValidationError
from kie_api.registry.loader import load_latest_pricing_snapshot, load_model_spec_file, load_registry


def test_registry_loads_verified_model_specs() -> None:
    registry = load_registry()

    assert len(registry.model_specs) == 16
    assert registry.get_model("nano-banana-pro").inputs["image"].required_max == 8
    assert registry.get_model("nano-banana-2").inputs["image"].required_max == 14
    assert registry.get_model("gpt-image-2-image-to-image").inputs["image"].required_max == 16
    assert registry.get_model("gpt-image-2-text-to-image").inputs["image"].required_max == 0
    assert registry.get_model("kling-3.0-i2v").inputs["image"].required_max == 2
    assert registry.get_model("seedance-2.0").provider_model == "bytedance/seedance-2"
    assert registry.get_model("seedance-2.0").task_modes[-1] == "reference_to_video"
    assert registry.get_model("seedance-2.0").options["resolution"].allowed == ["480p", "720p", "1080p", "4k"]
    assert registry.get_model("seedance-2.0").options["aspect_ratio"].allowed[-1] == "adaptive"
    assert registry.get_model("seedance-2.0-fast").provider_model == "bytedance/seedance-2-fast"
    assert registry.get_model("seedance-2.0-fast").options["resolution"].allowed == ["480p", "720p"]
    assert registry.get_model("seedance-2.0-fast").options["aspect_ratio"].allowed[-1] == "adaptive"
    assert registry.get_model("seedance-2.0-mini").provider_model == "bytedance/seedance-2-mini"
    assert registry.get_model("seedance-2.0-mini").options["resolution"].allowed == ["480p", "720p"]
    assert registry.get_model("seedance-2.0-mini").options["aspect_ratio"].allowed[-1] == "adaptive"
    assert "nsfw_checker" not in registry.get_model("seedance-2.0-mini").options
    seedance_25 = registry.get_model("seedance-2.5")
    assert seedance_25.provider_model == "bytedance/seedance-2-5"
    assert seedance_25.inputs["image"].required_max == 30
    assert seedance_25.inputs["video"].required_max == 10
    assert seedance_25.inputs["audio"].required_max == 10
    assert seedance_25.options["resolution"].allowed == ["480p", "720p"]
    assert seedance_25.options["duration"].allowed == [-1]
    assert seedance_25.options["duration"].max == 30
    assert seedance_25.options["output_format"].allowed == ["mp4", "mov"]
    assert seedance_25.options["nsfw_checker"].default is False
    assert registry.get_model("kling-3.0-turbo-i2v").provider_model == "kling/v3-turbo-image-to-video"
    assert registry.get_model("kling-3.0-turbo-i2v").options["resolution"].allowed == ["720p", "1080p"]
    assert registry.get_model("kling-3.0-turbo-i2v").options["duration"].min == 3
    assert registry.get_model("kling-3.0-turbo-i2v").options["duration"].max == 15
    assert "sound" not in registry.get_model("kling-3.0-turbo-i2v").options
    assert "mode" not in registry.get_model("kling-3.0-turbo-i2v").options
    assert registry.get_model("kling-3.0-t2v").options["mode"].allowed == ["std", "pro", "4K"]
    assert registry.get_model("kling-3.0-t2v").options["mode"].hidden_from_studio is False
    assert registry.get_model("kling-3.0-t2v").options["mode"].label is None
    assert registry.get_model("nano-banana-pro").options["resolution"].allowed == ["1K", "2K", "4K"]
    assert registry.get_model("nano-banana-2").options["output_format"].allowed == ["jpg", "png"]
    assert registry.get_model("gpt-image-2-image-to-image").transport.image_input_field == "input_urls"
    assert registry.get_model("suno-generate-music").transport.endpoint_family == "suno"
    assert registry.get_model("suno-generate-music").transport.create_path == "/api/v1/generate"
    assert registry.get_model("suno-generate-music").options["suno_model"].allowed == [
        "V4",
        "V4_5",
        "V4_5PLUS",
        "V4_5ALL",
        "V5",
        "V5_5",
    ]
    assert registry.get_model("suno-generate-music").options["style"].ui_visible_when == {
        "custom_mode": True
    }
    assert registry.get_model("gpt-image-2-image-to-image").options["aspect_ratio"].allowed == [
        "auto",
        "1:1",
        "9:16",
        "16:9",
        "4:3",
        "3:4",
    ]
    assert (
        registry.get_model("gpt-image-2-text-to-image").prompt.default_profile_keys_by_input_pattern[
            "prompt_only"
        ]
        == "gpt_image_2_text_to_image_v1"
    )


def test_registry_exposes_split_kling_models() -> None:
    registry = load_registry()

    assert registry.get_model("kling-3.0-t2v").provider_model == "kling-3.0/video"
    assert registry.get_model("kling-3.0-i2v").provider_model == "kling-3.0/video"
    assert registry.get_prompt_profile("kling_video_v1").applies_to[-1] == "kling-3.0-i2v"
    assert "Kling video generation" in registry.get_prompt_profile("kling_video_v1").prompt_markdown
    assert (
        registry.get_model("kling-3.0-i2v").prompt.default_profile_keys_by_input_pattern["single_image"]
        == "kling_3_0_i2v_first_frame_v1"
    )
    assert registry.get_model("kling-2.6-t2v").options["duration"].allowed == [5, 10]
    assert registry.get_model("kling-2.6-t2v").options["aspect_ratio"].allowed == ["1:1", "16:9", "9:16"]
    assert registry.get_model("kling-2.6-motion").provider_model == "kling-2.6/motion-control"
    assert registry.get_model("kling-2.6-motion").inputs["image"].required_max == 1
    assert registry.get_model("kling-2.6-motion").inputs["video"].required_max == 1
    assert registry.get_model("kling-2.6-motion").options["mode"].required is True
    assert registry.get_model("kling-2.6-motion").options["character_orientation"].required is True
    assert (
        registry.get_model("kling-2.6-motion").prompt.default_profile_key
        == "kling_2_6_motion_control_v1"
    )


def test_registry_exposes_provider_capability_updates() -> None:
    registry = load_registry()

    kling = registry.get_model("kling-3.0-t2v")
    seedance = registry.get_model("seedance-2.0")
    gpt_image = registry.get_model("gpt-image-2-text-to-image")

    assert "4K" in kling.options["mode"].allowed
    assert kling.options["mode"].value_aliases["4k"] == "4K"
    assert kling.options["duration"].min == 3
    assert kling.options["duration"].max == 15
    assert "1080p" in seedance.options["resolution"].allowed
    assert "4k" in seedance.options["resolution"].allowed
    assert seedance.prompt.min_chars == 3
    assert seedance.prompt.max_chars == 20000
    assert seedance.input_constraints is not None
    assert seedance.input_constraints.image_formats == ["jpg", "jpeg", "png", "webp", "bmp", "tiff", "gif"]
    assert seedance.input_constraints.image_aspect_ratio_min == 0.4
    assert seedance.input_constraints.image_aspect_ratio_max == 2.5
    assert seedance.input_constraints.video_formats == ["mp4", "mov"]
    assert seedance.input_constraints.video_duration_min_seconds == 2
    assert seedance.input_constraints.video_total_duration_max_seconds == 15
    assert seedance.input_constraints.video_fps_min == 24
    assert seedance.input_constraints.video_fps_max == 60
    assert seedance.input_constraints.audio_formats == ["wav", "mp3"]
    assert seedance.input_constraints.audio_total_duration_max_seconds == 15
    assert "16:9" in gpt_image.options["aspect_ratio"].allowed


def test_video_generation_models_expose_duration_controls() -> None:
    registry = load_registry()
    expected_duration_specs = {
        "kling-2.6-t2v": {"allowed": [5, 10]},
        "kling-2.6-i2v": {"allowed": [5, 10]},
        "kling-3.0-t2v": {"min": 3, "max": 15},
        "kling-3.0-i2v": {"min": 3, "max": 15},
        "kling-3.0-turbo-i2v": {"min": 3, "max": 15},
        "seedance-2.0": {"min": 4, "max": 15},
        "seedance-2.0-mini": {"min": 4, "max": 15},
        "seedance-2.5": {"allowed": [-1], "min": 4, "max": 30},
    }

    for model_key, expected in expected_duration_specs.items():
        duration = registry.get_model(model_key).options["duration"]
        assert duration.label == "Duration"
        assert duration.required is True
        assert duration.ui_group == "generation"
        assert duration.ui_order == 10
        for field, value in expected.items():
            assert getattr(duration, field) == value


def test_registry_loads_new_prompt_preset_metadata() -> None:
    registry = load_registry()
    preset = registry.get_prompt_profile("kling_3_0_i2v_first_last_frame_v1")

    assert preset.applies_to_models == ["kling-3.0-i2v"]
    assert [str(item) for item in preset.applies_to_task_modes] == ["image_to_video"]
    assert [str(item) for item in preset.applies_to_input_patterns] == ["first_last_frames"]
    assert "{{user_prompt}}" in preset.template

    gpt_preset = registry.get_prompt_profile("gpt_image_2_image_to_image_v1")

    assert gpt_preset.applies_to_models == ["gpt-image-2-image-to-image"]
    assert [str(item) for item in gpt_preset.applies_to_task_modes] == ["image_edit"]
    assert [str(item) for item in gpt_preset.applies_to_input_patterns] == ["image_edit"]
    assert "{{user_prompt}}" in gpt_preset.template

    gpt_t2i_preset = registry.get_prompt_profile("gpt_image_2_text_to_image_v1")

    assert gpt_t2i_preset.applies_to_models == ["gpt-image-2-text-to-image"]
    assert [str(item) for item in gpt_t2i_preset.applies_to_task_modes] == ["text_to_image"]
    assert [str(item) for item in gpt_t2i_preset.applies_to_input_patterns] == ["prompt_only"]
    assert "{{user_prompt}}" in gpt_t2i_preset.template

    suno_preset = registry.get_prompt_profile("suno_generate_music_v1")

    assert suno_preset.applies_to_models == ["suno-generate-music"]
    assert [str(item) for item in suno_preset.applies_to_task_modes] == ["text_to_music"]
    assert [str(item) for item in suno_preset.applies_to_input_patterns] == ["music_prompt"]
    assert "{{user_prompt}}" in suno_preset.template

    kling_26_motion_preset = registry.get_prompt_profile("kling_2_6_motion_control_v1")

    assert kling_26_motion_preset.applies_to_models == ["kling-2.6-motion"]
    assert [str(item) for item in kling_26_motion_preset.applies_to_task_modes] == ["motion_control"]
    assert [str(item) for item in kling_26_motion_preset.applies_to_input_patterns] == ["motion_control"]
    assert "{{user_prompt}}" in kling_26_motion_preset.template


def test_registry_exposes_field_level_provenance() -> None:
    registry = load_registry()

    motion_spec = registry.get_model("kling-3.0-motion")
    kling_26_motion = registry.get_model("kling-2.6-motion")

    assert motion_spec.verification.field_provenance["options.mode.allowed"] == "verified_live"
    assert motion_spec.verification.field_provenance["options.mode.value_aliases"] == "inferred"
    assert motion_spec.verification.field_provenance["transport.create_path"] == "verified_docs"
    assert kling_26_motion.verification.field_provenance["provider_model"] == "verified_docs"
    assert kling_26_motion.verification.field_provenance["options.mode.required"] == "verified_live"


def test_registry_can_load_bundled_package_specs() -> None:
    bundled_root = resources.files("kie_api").joinpath("resources", "specs")
    bundled_profiles_root = resources.files("kie_api").joinpath("resources", "prompt_profiles")
    registry = load_registry(bundled_root, bundled_profiles_root)

    assert registry.get_model("nano-banana-2").provider_model == "nano-banana-2"
    assert registry.get_model("gpt-image-2-image-to-image").provider_model == "gpt-image-2-image-to-image"
    assert registry.get_model("gpt-image-2-text-to-image").provider_model == "gpt-image-2-text-to-image"
    assert registry.get_model("seedance-2.0-fast").provider_model == "bytedance/seedance-2-fast"
    assert registry.get_model("seedance-2.5").provider_model == "bytedance/seedance-2-5"
    assert registry.get_model("kling-2.6-motion").provider_model == "kling-2.6/motion-control"
    assert registry.get_model("kling-3.0-motion").options["background_source"].type == "string"


def test_latest_pricing_snapshot_loads_from_package_resources() -> None:
    snapshot = load_latest_pricing_snapshot()

    assert snapshot.version == "2026-08-12-site-pricing-page"
    assert snapshot.released_on == "2026-08-12"
    assert any(rule.model_key == "kling-3.0-t2v" for rule in snapshot.rules)
    assert any(rule.model_key == "gpt-image-2-image-to-image" for rule in snapshot.rules)
    assert any(rule.model_key == "gpt-image-2-text-to-image" for rule in snapshot.rules)
    gpt_rule = next(rule for rule in snapshot.rules if rule.model_key == "gpt-image-2-image-to-image")
    assert gpt_rule.pricing_status == "observed_site_pricing"
    assert gpt_rule.base_credits == 6
    assert gpt_rule.source_anchor_urls == [
        "https://kie.ai/gpt-image-2?model=gpt-image-2-image-to-image"
    ]
    gpt_t2i_rule = next(rule for rule in snapshot.rules if rule.model_key == "gpt-image-2-text-to-image")
    assert gpt_t2i_rule.pricing_status == "observed_site_pricing"
    assert gpt_t2i_rule.base_credits == 6
    kling_26_motion_rule = next(rule for rule in snapshot.rules if rule.model_key == "kling-2.6-motion")
    assert kling_26_motion_rule.billing_unit == "second"
    assert kling_26_motion_rule.base_credits == 11
    assert kling_26_motion_rule.multipliers["mode"]["1080p"] == pytest.approx(18.0 / 11.0)
    kling_rule = next(rule for rule in snapshot.rules if rule.model_key == "kling-3.0-t2v")
    assert kling_rule.multipliers["pricing_variant"]["4k_true"] == pytest.approx(67.0 / 14.0)
    seedance_rule = next(rule for rule in snapshot.rules if rule.model_key == "seedance-2.0")
    assert seedance_rule.multipliers["pricing_variant"]["1080p_no_video_input"] == pytest.approx(102.0 / 19.0)
    assert seedance_rule.multipliers["pricing_variant"]["4k_no_video_input"] == pytest.approx(208.0 / 19.0)
    assert seedance_rule.multipliers["pricing_variant"]["4k_with_video_input"] == pytest.approx(128.0 / 19.0)
    seedance_fast_rule = next(rule for rule in snapshot.rules if rule.model_key == "seedance-2.0-fast")
    assert seedance_fast_rule.base_credits == 11.7
    assert seedance_fast_rule.multipliers["pricing_variant"]["720p_with_video_input"] == pytest.approx(15.0 / 11.7)
    seedance_mini_rule = next(rule for rule in snapshot.rules if rule.model_key == "seedance-2.0-mini")
    assert seedance_mini_rule.base_credits == 3.8
    assert seedance_mini_rule.multipliers["pricing_variant"]["720p_with_video_input"] == pytest.approx(5.0 / 3.8)
    seedance_25_rule = next(rule for rule in snapshot.rules if rule.model_key == "seedance-2.5")
    assert seedance_25_rule.base_credits == 28.0
    assert seedance_25_rule.multipliers["duration"]["-1"] == 30.0
    assert seedance_25_rule.multipliers["pricing_variant"]["720p_with_video_input"] == pytest.approx(38.0 / 28.0)
    kling_turbo_rule = next(rule for rule in snapshot.rules if rule.model_key == "kling-3.0-turbo-i2v")
    assert kling_turbo_rule.base_credits == 18
    assert kling_turbo_rule.multipliers["resolution"]["1080p"] == pytest.approx(22.5 / 18)
    assert snapshot.missing_model_keys == []
    assert "gpt-image-2-text-to-image" in snapshot.priced_model_keys


def test_latest_pricing_snapshot_prefers_metadata_date_over_filename_order(tmp_path: Path) -> None:
    older = tmp_path / "zzz.yaml"
    newer = tmp_path / "aaa.yaml"
    older.write_text(
        "\n".join(
            [
                "version: '2026-03-20-policy'",
                "label: older",
                "released_on: '2026-03-20'",
                "rules: []",
            ]
        ),
        encoding="utf-8",
    )
    newer.write_text(
        "\n".join(
            [
                "version: '2026-03-26-policy'",
                "label: newer",
                "released_on: '2026-03-26'",
                "rules: []",
            ]
        ),
        encoding="utf-8",
    )

    snapshot = load_latest_pricing_snapshot(tmp_path)

    assert snapshot.label == "newer"


def test_load_model_spec_rejects_malformed_yaml(tmp_path: Path) -> None:
    broken = tmp_path / "broken.yaml"
    broken.write_text("key: only-key\n", encoding="utf-8")

    with pytest.raises(SpecValidationError):
        load_model_spec_file(broken)


def test_registry_raises_for_unknown_model() -> None:
    registry = load_registry()

    with pytest.raises(ModelNotFoundError):
        registry.get_model("does-not-exist")


def test_bundled_model_spec_sync_check_passes() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "sync_packaged_specs.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
