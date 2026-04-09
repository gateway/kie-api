from pathlib import Path
from typing import Optional

import pytest

from kie_api import build_submission_payload, prepare_request_for_submission
from kie_api.config import KieSettings
from kie_api.enums import JobState, MediaRole, MediaType, TaskMode
from kie_api.exceptions import RequestPreparationError
from kie_api.models import MediaReference, NormalizedRequest, RawUserRequest, StatusResult, UploadResult
from kie_api.registry.loader import load_registry


class DummyUploadClient:
    def __init__(self) -> None:
        self.stream_calls = []
        self.url_calls = []

    def upload_file_stream(self, file_path: str, file_name: Optional[str] = None) -> UploadResult:
        self.stream_calls.append((file_path, file_name))
        resolved_name = file_name or Path(file_path).name
        return UploadResult(
            success=True,
            file_name=resolved_name,
            file_path=f"kieai/183531/images/user-uploads/{resolved_name}",
            download_url=f"https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/{resolved_name}",
            mime_type="application/octet-stream",
            raw_response={"success": True},
        )

    def upload_from_url(self, source_url: str, file_name: Optional[str] = None) -> UploadResult:
        self.url_calls.append((source_url, file_name))
        resolved_name = file_name or Path(source_url).name or "uploaded.bin"
        return UploadResult(
            success=True,
            file_name=resolved_name,
            file_path=f"kieai/183531/images/user-uploads/{resolved_name}",
            download_url=f"https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/{resolved_name}",
            mime_type="application/octet-stream",
            raw_response={"success": True},
        )


def test_prepare_request_uploads_local_image_path_via_stream_upload(tmp_path: Path) -> None:
    registry = load_registry()
    upload_client = DummyUploadClient()
    image_path = tmp_path / "portrait.png"
    image_path.write_bytes(b"fake-image")

    prepared = prepare_request_for_submission(
        RawUserRequest(
            model_key="nano-banana-pro",
            prompt="Make this portrait more cinematic.",
            images=[str(image_path)],
            options={"aspect_ratio": "16:9", "resolution": "2K", "output_format": "png"},
        ),
        registry=registry,
        settings=KieSettings(api_key="test-key"),
        upload_client=upload_client,
    )

    assert len(upload_client.stream_calls) == 1
    stream_path, stream_name = upload_client.stream_calls[0]
    assert stream_path == str(image_path)
    assert stream_name.startswith("portrait-")
    assert stream_name.endswith(".png")
    assert prepared.normalized_request.images[0].url.startswith("https://tempfile.redpandaai.co/")
    assert prepared.normalized_request.images[0].path is None
    assert prepared.upload_results[0].file_path.endswith(stream_name)
    assert prepared.debug["original_media"]["images"][0]["path"] == str(image_path)


def test_prepare_request_uploads_remote_image_url_via_url_upload() -> None:
    registry = load_registry()
    upload_client = DummyUploadClient()

    prepared = prepare_request_for_submission(
        RawUserRequest(
            model_key="nano-banana-pro",
            prompt="Make this portrait more cinematic.",
            images=["https://example.com/source/portrait.png"],
            options={"aspect_ratio": "16:9", "resolution": "2K", "output_format": "png"},
        ),
        registry=registry,
        settings=KieSettings(api_key="test-key"),
        upload_client=upload_client,
    )

    assert len(upload_client.url_calls) == 1
    upload_url, upload_name = upload_client.url_calls[0]
    assert upload_url == "https://example.com/source/portrait.png"
    assert upload_name.startswith("portrait-")
    assert upload_name.endswith(".png")
    assert prepared.normalized_request.images[0].url.startswith("https://tempfile.redpandaai.co/")
    assert prepared.upload_results[0].download_url is not None


def test_prepare_request_reuses_trusted_uploaded_media_without_reupload() -> None:
    registry = load_registry()
    upload_client = DummyUploadClient()
    trusted_url = "https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/source.png"

    prepared = prepare_request_for_submission(
        RawUserRequest(
            model_key="nano-banana-pro",
            prompt="Keep it clean.",
            images=[trusted_url],
        ),
        registry=registry,
        settings=KieSettings(api_key="test-key"),
        upload_client=upload_client,
    )

    assert upload_client.stream_calls == []
    assert upload_client.url_calls == []
    assert prepared.upload_results == []
    assert prepared.reused_uploaded_media[0].url == trusted_url


def test_prepare_request_uploads_all_media_types_from_normalized_request() -> None:
    registry = load_registry()
    upload_client = DummyUploadClient()
    normalized = NormalizedRequest(
        model_key="kling-3.0-motion",
        provider_model="kling-3.0/motion-control",
        task_mode=TaskMode.MOTION_CONTROL,
        images=[
            MediaReference(
                media_type=MediaType.IMAGE,
                url="https://example.com/source/subject.png",
                filename="subject.png",
            )
        ],
        videos=[
            MediaReference(
                media_type=MediaType.VIDEO,
                path="/tmp/motion.mov",
                filename="motion.mov",
            )
        ],
        audios=[
            MediaReference(
                media_type=MediaType.AUDIO,
                url="https://example.com/source/audio.wav",
                filename="audio.wav",
            )
        ],
    )

    prepared = prepare_request_for_submission(
        normalized,
        registry=registry,
        settings=KieSettings(api_key="test-key"),
        upload_client=upload_client,
    )

    assert len(prepared.upload_results) == 3
    assert prepared.normalized_request.images[0].url.startswith("https://tempfile.redpandaai.co/")
    assert prepared.normalized_request.videos[0].url.startswith("https://tempfile.redpandaai.co/")
    assert prepared.normalized_request.audios[0].url.startswith("https://tempfile.redpandaai.co/")


def test_prepare_request_preserves_seedance_media_roles_and_payload_shape() -> None:
    registry = load_registry()
    upload_client = DummyUploadClient()
    normalized = NormalizedRequest(
        model_key="seedance-2.0",
        provider_model="bytedance/seedance-2",
        task_mode=TaskMode.REFERENCE_TO_VIDEO,
        prompt="Use the first frame as the subject anchor.",
        images=[
            MediaReference(
                media_type=MediaType.IMAGE,
                role=MediaRole.FIRST_FRAME,
                path="/tmp/first.png",
                filename="first.png",
            )
        ],
        videos=[
            MediaReference(
                media_type=MediaType.VIDEO,
                role=MediaRole.REFERENCE,
                url="https://example.com/source/ref.mp4",
                filename="ref.mp4",
                duration_seconds=4.5,
            )
        ],
        options={"resolution": "480p", "aspect_ratio": "9:16", "duration": 5},
    )

    prepared = prepare_request_for_submission(
        normalized,
        registry=registry,
        settings=KieSettings(api_key="test-key"),
        upload_client=upload_client,
    )

    assert prepared.normalized_request.images[0].role == MediaRole.FIRST_FRAME
    assert prepared.normalized_request.videos[0].role == MediaRole.REFERENCE
    assert prepared.normalized_request.videos[0].duration_seconds == 4.5

    payload = build_submission_payload(
        prepared.normalized_request,
        registry=registry,
        settings=KieSettings(api_key="test-key"),
    )

    assert payload["input"]["first_frame_url"].startswith("https://tempfile.redpandaai.co/")
    assert "/first-" in payload["input"]["first_frame_url"]
    assert payload["input"]["first_frame_url"].endswith(".png")
    assert payload["input"]["reference_video_urls"][0].startswith("https://tempfile.redpandaai.co/")
    assert "/ref-" in payload["input"]["reference_video_urls"][0]
    assert payload["input"]["reference_video_urls"][0].endswith(".mp4")


def test_build_submission_payload_rejects_non_uploaded_media_urls() -> None:
    registry = load_registry()

    with pytest.raises(RequestPreparationError, match="must only contain KIE-uploaded media URLs"):
        build_submission_payload(
            RawUserRequest(
                model_key="nano-banana-pro",
                prompt="Make this portrait more cinematic.",
                images=["https://example.com/source/portrait.png"],
            ),
            registry=registry,
            settings=KieSettings(api_key="test-key"),
        )


def test_prepare_request_blocks_nano_banana_pro_when_image_limit_is_exceeded() -> None:
    registry = load_registry()
    upload_client = DummyUploadClient()

    with pytest.raises(RequestPreparationError, match="ready state; received invalid"):
        prepare_request_for_submission(
            RawUserRequest(
                model_key="nano-banana-pro",
                prompt="Keep the subject and simplify the background.",
                images=[f"/tmp/image_{index}.png" for index in range(9)],
            ),
            registry=registry,
            settings=KieSettings(api_key="test-key"),
            upload_client=upload_client,
        )

    assert upload_client.stream_calls == []
    assert upload_client.url_calls == []


def test_prepare_request_blocks_nano_banana_2_when_image_limit_is_exceeded() -> None:
    registry = load_registry()
    upload_client = DummyUploadClient()

    with pytest.raises(RequestPreparationError, match="ready state; received invalid"):
        prepare_request_for_submission(
            RawUserRequest(
                model_key="nano-banana-2",
                prompt="Turn these references into a clean collage.",
                images=[f"/tmp/image_{index}.png" for index in range(15)],
            ),
            registry=registry,
            settings=KieSettings(api_key="test-key"),
            upload_client=upload_client,
        )

    assert upload_client.stream_calls == []
    assert upload_client.url_calls == []


def test_prepare_request_uses_unique_upload_names_for_same_basename(tmp_path: Path) -> None:
    registry = load_registry()
    upload_client = DummyUploadClient()
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first_image = first_dir / "output_01.png"
    second_image = second_dir / "output_01.png"
    first_image.write_bytes(b"first-image")
    second_image.write_bytes(b"second-image")

    first_prepared = prepare_request_for_submission(
        RawUserRequest(
            model_key="nano-banana-2",
            prompt="Use the first generated asset.",
            images=[str(first_image)],
        ),
        registry=registry,
        settings=KieSettings(api_key="test-key"),
        upload_client=upload_client,
    )
    second_prepared = prepare_request_for_submission(
        RawUserRequest(
            model_key="nano-banana-2",
            prompt="Use the second generated asset.",
            images=[str(second_image)],
        ),
        registry=registry,
        settings=KieSettings(api_key="test-key"),
        upload_client=upload_client,
    )

    assert len(upload_client.stream_calls) == 2
    _, first_name = upload_client.stream_calls[0]
    _, second_name = upload_client.stream_calls[1]
    assert first_name != second_name
    assert first_prepared.normalized_request.images[0].url != second_prepared.normalized_request.images[0].url
