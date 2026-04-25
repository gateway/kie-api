import pytest

from kie_api.enums import PromptPolicy, TaskMode
from kie_api.exceptions import RequestNormalizationError
from kie_api.models import RawUserRequest
from kie_api.registry.loader import load_registry
from kie_api.services.normalizer import RequestNormalizer


def test_normalizer_resolves_prompt_only_nano_banana_to_text_to_image() -> None:
    normalizer = RequestNormalizer(load_registry())

    normalized = normalizer.normalize(
        RawUserRequest(model_key="nano-banana-pro", prompt="a studio portrait")
    )

    assert normalized.model_key == "nano-banana-pro"
    assert normalized.task_mode == TaskMode.TEXT_TO_IMAGE
    assert normalized.prompt_policy == PromptPolicy.ASK
    assert normalized.defaulted_fields == []


def test_normalizer_resolves_nano_banana_with_images_to_image_edit() -> None:
    normalizer = RequestNormalizer(load_registry())

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="nano-banana-2",
            prompt="add a sunset",
            images=["https://example.com/ref.png"],
        )
    )

    assert normalized.task_mode == TaskMode.IMAGE_EDIT
    assert len(normalized.images) == 1


def test_normalizer_resolves_gpt_image_2_i2i_defaults() -> None:
    normalizer = RequestNormalizer(load_registry())

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="gpt-image-2-image-to-image",
            prompt="turn this sketch into a polished poster",
            images=["https://example.com/source.png"],
        )
    )

    assert normalized.model_key == "gpt-image-2-image-to-image"
    assert normalized.task_mode == TaskMode.IMAGE_EDIT
    assert normalized.options["aspect_ratio"] == "auto"
    assert [item.field for item in normalized.defaulted_fields] == ["aspect_ratio"]


def test_normalizer_resolves_generic_kling_3_family_to_i2v_when_image_present() -> None:
    normalizer = RequestNormalizer(load_registry())

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0",
            prompt="camera pushes in slowly",
            images=["https://example.com/start.png"],
            options={"duration": "5", "mode": "pro"},
        )
    )

    assert normalized.model_key == "kling-3.0-i2v"
    assert normalized.task_mode == TaskMode.IMAGE_TO_VIDEO
    assert normalized.options["multi_shots"] is False
    assert normalized.options["sound"] is True
    assert [item.field for item in normalized.defaulted_fields] == ["sound", "multi_shots"]


def test_normalizer_keeps_generic_kling_3_family_as_t2v_without_images() -> None:
    normalizer = RequestNormalizer(load_registry())

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0",
            prompt="a wide cinematic street scene",
            options={"duration": "7", "mode": "std"},
        )
    )

    assert normalized.model_key == "kling-3.0-t2v"
    assert normalized.task_mode == TaskMode.TEXT_TO_VIDEO
    assert normalized.options["duration"] == 7
    assert normalized.options["sound"] is True
    assert [item.field for item in normalized.defaulted_fields] == ["sound", "multi_shots"]


def test_normalizer_preserves_kling_multi_prompt_shape() -> None:
    normalizer = RequestNormalizer(load_registry())

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0-t2v",
            multi_prompt=[
                {"prompt": "first shot", "duration": 2},
                {"prompt": "second shot", "duration": 3},
            ],
            options={"duration": "5", "mode": "std", "multi_shots": "true"},
        )
    )

    assert normalized.options["multi_shots"] is True
    assert [shot.duration for shot in normalized.multi_prompt] == [2, 3]


def test_normalizer_rejects_unsafe_family_inference_when_too_many_images() -> None:
    normalizer = RequestNormalizer(load_registry())

    with pytest.raises(RequestNormalizationError):
        normalizer.normalize(
            RawUserRequest(
                model_key="kling-3.0",
                prompt="animate all of these",
                images=[
                    "https://example.com/1.png",
                    "https://example.com/2.png",
                    "https://example.com/3.png",
                ],
            )
        )


def test_normalizer_resolves_seedance_text_only_to_text_to_video() -> None:
    normalizer = RequestNormalizer(load_registry())

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="seedance-2.0",
            prompt="a fox sprinting through a snowy forest",
            options={"duration": 4},
        )
    )

    assert normalized.task_mode == TaskMode.TEXT_TO_VIDEO


def test_normalizer_resolves_seedance_first_frame_to_reference_to_video() -> None:
    normalizer = RequestNormalizer(load_registry())

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="seedance-2.0",
            prompt="animate from this starting pose",
            images=[
                {
                    "url": "https://example.com/start.png",
                    "role": "first_frame",
                }
            ],
            options={"duration": 4},
        )
    )

    assert normalized.task_mode == TaskMode.REFERENCE_TO_VIDEO


def test_normalizer_resolves_seedance_first_last_frames_to_reference_to_video() -> None:
    normalizer = RequestNormalizer(load_registry())

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="seedance-2.0",
            prompt="move from this opening frame to the final pose",
            images=[
                {"url": "https://example.com/start.png", "role": "first_frame"},
                {"url": "https://example.com/end.png", "role": "last_frame"},
            ],
            options={"duration": 6},
        )
    )

    assert normalized.task_mode == TaskMode.REFERENCE_TO_VIDEO


def test_normalizer_resolves_seedance_reference_media_to_reference_to_video() -> None:
    normalizer = RequestNormalizer(load_registry())

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="seedance-2.0",
            prompt="use the reference assets for character identity and pacing",
            images=[{"url": "https://example.com/ref1.png", "role": "reference"}],
            videos=[{"url": "https://example.com/ref1.mp4", "role": "reference"}],
            audios=[{"url": "https://example.com/ref1.mp3", "role": "reference"}],
            options={"duration": 8},
        )
    )

    assert normalized.task_mode == TaskMode.REFERENCE_TO_VIDEO
