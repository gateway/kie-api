import subprocess
import sys
from importlib import resources
from pathlib import Path

import pytest

from kie_api.exceptions import ModelNotFoundError, SpecValidationError
from kie_api.registry.loader import load_latest_pricing_snapshot, load_model_spec_file, load_registry


def test_registry_loads_verified_model_specs() -> None:
    registry = load_registry()

    assert len(registry.model_specs) == 7
    assert registry.get_model("nano-banana-pro").inputs["image"].required_max == 8
    assert registry.get_model("nano-banana-2").inputs["image"].required_max == 14
    assert registry.get_model("kling-3.0-i2v").inputs["image"].required_max == 2
    assert registry.get_model("nano-banana-pro").options["resolution"].allowed == ["1K", "2K", "4K"]
    assert registry.get_model("nano-banana-2").options["output_format"].allowed == ["jpg", "png"]


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


def test_registry_loads_new_prompt_preset_metadata() -> None:
    registry = load_registry()
    preset = registry.get_prompt_profile("kling_3_0_i2v_first_last_frame_v1")

    assert preset.applies_to_models == ["kling-3.0-i2v"]
    assert [str(item) for item in preset.applies_to_task_modes] == ["image_to_video"]
    assert [str(item) for item in preset.applies_to_input_patterns] == ["first_last_frames"]
    assert "{{user_prompt}}" in preset.template


def test_registry_exposes_field_level_provenance() -> None:
    registry = load_registry()

    motion_spec = registry.get_model("kling-3.0-motion")

    assert motion_spec.verification.field_provenance["options.mode.allowed"] == "verified_live"
    assert motion_spec.verification.field_provenance["options.mode.value_aliases"] == "inferred"
    assert motion_spec.verification.field_provenance["transport.create_path"] == "verified_docs"


def test_registry_can_load_bundled_package_specs() -> None:
    bundled_root = resources.files("kie_api").joinpath("resources", "specs")
    bundled_profiles_root = resources.files("kie_api").joinpath("resources", "prompt_profiles")
    registry = load_registry(bundled_root, bundled_profiles_root)

    assert registry.get_model("nano-banana-2").provider_model == "nano-banana-2"
    assert registry.get_model("kling-3.0-motion").options["background_source"].type == "string"


def test_latest_pricing_snapshot_loads_from_package_resources() -> None:
    snapshot = load_latest_pricing_snapshot()

    assert snapshot.version == "2026-03-26-site-pricing-page"
    assert snapshot.released_on == "2026-03-26"
    assert any(rule.model_key == "kling-3.0-t2v" for rule in snapshot.rules)


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
