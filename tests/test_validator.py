from kie_api.enums import ValidationState
from kie_api.models import RawUserRequest
from kie_api.registry.loader import load_registry
from kie_api.services.normalizer import RequestNormalizer
from kie_api.services.validator import RequestValidator


def test_validator_returns_needs_input_for_kling_motion_without_video() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0-motion",
            prompt="make the avatar wave",
            images=["https://example.com/subject.png"],
        )
    )
    result = validator.validate(normalized)

    assert result.state == ValidationState.NEEDS_INPUT
    assert result.missing_inputs[0].field == "video"


def test_validator_returns_needs_input_for_kling_motion_without_image() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0-motion",
            videos=["https://example.com/motion.mov"],
        )
    )
    result = validator.validate(normalized)

    assert result.state == ValidationState.NEEDS_INPUT
    assert result.missing_inputs[0].field == "image"


def test_validator_returns_ready_with_warning_for_kling_i2v_aspect_ratio_inference() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0-i2v",
            prompt="a portrait subject turning toward camera",
            images=["https://example.com/start.png"],
            options={"duration": 5, "mode": "pro"},
        )
    )
    result = validator.validate(normalized)

    assert result.state == ValidationState.READY_WITH_WARNING
    assert [item.field for item in result.defaulted_fields] == ["sound", "multi_shots"]
    assert result.warning_details[0].field == "aspect_ratio"


def test_validator_rejects_too_many_images_for_kling_i2v() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0-i2v",
            prompt="animate these",
            images=[
                "https://example.com/1.png",
                "https://example.com/2.png",
                "https://example.com/3.png",
            ],
            options={"duration": 5, "mode": "pro"},
        )
    )
    result = validator.validate(normalized)

    assert result.state == ValidationState.INVALID
    assert "at most 2 image input(s)" in result.errors[0]
    assert result.impossible_inputs[0].field == "image"


def test_validator_marks_single_image_kling_i2v_as_start_frame_mode() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0-i2v",
            prompt="animate this portrait",
            images=["https://example.com/start.png"],
            options={"duration": 5, "mode": "pro"},
        )
    )
    result = validator.validate(normalized)

    assert result.normalized_request is not None
    assert result.normalized_request.debug["frame_guidance_mode"] == "start_frame"


def test_validator_marks_two_image_kling_i2v_as_first_last_frame_mode() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0-i2v",
            prompt="animate between these frames",
            images=[
                "https://example.com/start.png",
                "https://example.com/end.png",
            ],
            options={"duration": 5, "mode": "pro"},
        )
    )
    result = validator.validate(normalized)

    assert result.state == ValidationState.READY_WITH_WARNING
    assert result.normalized_request is not None
    assert result.normalized_request.debug["frame_guidance_mode"] == "first_last_frames"
    assert "aspect_ratio" in result.warnings[0]


def test_validator_rejects_aspect_ratio_when_kling_i2v_uses_first_last_frames() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0-i2v",
            prompt="animate between these frames",
            images=[
                "https://example.com/start.png",
                "https://example.com/end.png",
            ],
            options={"duration": 5, "mode": "pro", "aspect_ratio": "1:1"},
        )
    )
    result = validator.validate(normalized)

    assert result.state == ValidationState.INVALID
    assert result.impossible_inputs[0].field == "aspect_ratio"
    assert result.impossible_inputs[0].code == "aspect_ratio_not_allowed_with_first_last_frames"


def test_validator_defaults_kling_3_sound_when_omitted() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0-i2v",
            prompt="animate this portrait",
            images=["https://example.com/start.png"],
            options={"duration": 5, "mode": "std"},
        )
    )
    result = validator.validate(normalized)

    assert result.normalized_request is not None
    assert result.normalized_request.options["sound"] is True
    assert any(item.field == "sound" for item in result.defaulted_fields)


def test_validator_maps_motion_mode_aliases_from_docs_to_live_values() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0-motion",
            images=["https://example.com/subject.png"],
            videos=["https://example.com/motion.mov"],
            options={"mode": "std", "character_orientation": "image"},
        )
    )
    result = validator.validate(normalized)

    assert result.state == ValidationState.READY
    assert result.normalized_request.options["mode"] == "720p"


def test_validator_returns_ready_with_defaults_for_kling_t2v() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0-t2v",
            prompt="a high-energy title sequence",
            options={"duration": 15, "mode": "pro", "sound": True},
        )
    )
    result = validator.validate(normalized)

    assert result.state == ValidationState.READY_WITH_DEFAULTS
    assert [item.field for item in result.defaulted_fields] == ["multi_shots"]


def test_validator_records_unknown_provider_passthrough_options_as_warnings() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="nano-banana-2",
            prompt="make it punchier",
            options={"aspect_ratio": "1:1", "mystery_flag": "keep"},
        )
    )
    result = validator.validate(normalized)

    assert result.state == ValidationState.READY_WITH_WARNING
    assert result.warning_details[0].field == "mystery_flag"
