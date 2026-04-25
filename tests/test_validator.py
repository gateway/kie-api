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


def test_validator_requires_gpt_image_2_i2i_input_image() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="gpt-image-2-image-to-image",
            prompt="make a polished product poster",
        )
    )
    result = validator.validate(normalized)

    assert result.state == ValidationState.NEEDS_INPUT
    assert result.missing_inputs[0].field == "image"


def test_validator_rejects_gpt_image_2_i2i_invalid_resolution_combinations() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    auto_high_resolution = normalizer.normalize(
        RawUserRequest(
            model_key="gpt-image-2-image-to-image",
            prompt="make a polished product poster",
            images=["https://example.com/product.png"],
            options={"resolution": "2K"},
        )
    )
    auto_result = validator.validate(auto_high_resolution)

    assert auto_result.state == ValidationState.INVALID
    assert any(
        item.code == "gpt_image_2_auto_aspect_high_resolution_not_allowed"
        for item in auto_result.impossible_inputs
    )

    square_4k = normalizer.normalize(
        RawUserRequest(
            model_key="gpt-image-2-image-to-image",
            prompt="make a polished product poster",
            images=["https://example.com/product.png"],
            options={"aspect_ratio": "1:1", "resolution": "4K"},
        )
    )
    square_result = validator.validate(square_4k)

    assert square_result.state == ValidationState.INVALID
    assert any(
        item.code == "gpt_image_2_square_4k_not_allowed"
        for item in square_result.impossible_inputs
    )


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


def test_validator_rejects_kling_multi_prompt_when_multi_shots_disabled() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0-t2v",
            prompt="single-shot prompt",
            multi_prompt=[
                {"prompt": "shot one", "duration": 2},
            ],
            options={"duration": 5, "mode": "std", "multi_shots": False},
        )
    )
    result = validator.validate(normalized)

    assert result.state == ValidationState.INVALID
    assert result.impossible_inputs[0].field == "multi_prompt"
    assert result.impossible_inputs[0].code == "multi_prompt_requires_multi_shots"


def test_validator_requires_multi_prompt_when_kling_multi_shots_enabled() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0-t2v",
            options={"duration": 5, "mode": "std", "multi_shots": True},
        )
    )
    result = validator.validate(normalized)

    assert result.state == ValidationState.NEEDS_INPUT
    assert {item.field for item in result.missing_inputs} == {"multi_prompt"}


def test_validator_accepts_kling_multi_shot_with_multi_prompt() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0-t2v",
            multi_prompt=[
                {"prompt": "wide establishing shot", "duration": 2},
                {"prompt": "close-up reaction shot", "duration": 3},
            ],
            options={"duration": 5, "mode": "std", "multi_shots": True},
        )
    )
    result = validator.validate(normalized)

    assert result.state == ValidationState.READY_WITH_DEFAULTS
    assert result.normalized_request is not None
    assert [shot.prompt for shot in result.normalized_request.multi_prompt] == [
        "wide establishing shot",
        "close-up reaction shot",
    ]


def test_validator_rejects_kling_multi_shot_duration_outside_docs_range() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0-t2v",
            multi_prompt=[
                {"prompt": "too long shot", "duration": 13},
            ],
            options={"duration": 5, "mode": "std", "multi_shots": True},
        )
    )
    result = validator.validate(normalized)

    assert result.state == ValidationState.INVALID
    assert result.impossible_inputs[0].field == "multi_prompt[0].duration"


def test_validator_rejects_kling_multi_shot_with_two_images() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0-i2v",
            images=[
                "https://example.com/start.png",
                "https://example.com/end.png",
            ],
            multi_prompt=[
                {"prompt": "shot one", "duration": 2},
                {"prompt": "shot two", "duration": 2},
            ],
            options={"duration": 5, "mode": "std", "multi_shots": True},
        )
    )
    result = validator.validate(normalized)

    assert result.state == ValidationState.INVALID
    assert any(item.code == "too_many_images_for_kling_multi_shot" for item in result.impossible_inputs)


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


def test_validator_rejects_seedance_last_frame_without_first_frame() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="seedance-2.0",
            prompt="end on this pose",
            images=[{"url": "https://example.com/end.png", "role": "last_frame"}],
            options={"duration": 4},
        )
    )
    result = validator.validate(normalized)

    assert result.state == ValidationState.INVALID
    assert any(item.code == "seedance_last_frame_requires_first_frame" for item in result.impossible_inputs)


def test_validator_rejects_seedance_frames_and_multimodal_references_together() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="seedance-2.0",
            prompt="mix the first frame with other references",
            images=[
                {"url": "https://example.com/start.png", "role": "first_frame"},
                {"url": "https://example.com/ref1.png", "role": "reference"},
            ],
            options={"duration": 4},
        )
    )
    result = validator.validate(normalized)

    assert result.state == ValidationState.INVALID
    assert any(
        item.code == "seedance_frames_and_references_are_mutually_exclusive"
        for item in result.impossible_inputs
    )


def test_validator_rejects_seedance_too_many_reference_images() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="seedance-2.0",
            prompt="use all of these reference stills",
            images=[
                {"url": f"https://example.com/ref{index}.png", "role": "reference"}
                for index in range(10)
            ],
            options={"duration": 4},
        )
    )
    result = validator.validate(normalized)

    assert result.state == ValidationState.INVALID
    assert any(item.code == "too_many_reference_images" for item in result.impossible_inputs)


def test_validator_rejects_seedance_reference_video_duration_sum_over_limit() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="seedance-2.0",
            prompt="use these reference clips for motion language",
            videos=[
                {"url": "https://example.com/ref1.mp4", "role": "reference", "duration_seconds": 10},
                {"url": "https://example.com/ref2.mp4", "role": "reference", "duration_seconds": 8},
            ],
            options={"duration": 6},
        )
    )
    result = validator.validate(normalized)

    assert result.state == ValidationState.INVALID
    assert any(
        item.code == "reference_video_duration_limit_exceeded"
        for item in result.impossible_inputs
    )


def test_validator_accepts_seedance_multimodal_reference_request() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    validator = RequestValidator(registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="seedance-2.0",
            prompt="use these references for the character, scene, and rhythm",
            images=[
                {"url": "https://example.com/ref1.png", "role": "reference"},
                {"url": "https://example.com/ref2.png", "role": "reference"},
            ],
            videos=[{"url": "https://example.com/ref1.mp4", "role": "reference", "duration_seconds": 12}],
            audios=[{"url": "https://example.com/ref1.mp3", "role": "reference"}],
            options={"duration": 8, "resolution": "720p"},
        )
    )
    result = validator.validate(normalized)

    assert result.state == ValidationState.READY_WITH_WARNING
    assert any(item.code == "seedance_reference_audio_duration_unverified" for item in result.warning_details)
