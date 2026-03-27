from kie_api import build_submission_payload, validate_request
from kie_api.clients.submit import SubmitClient
from kie_api.config import KieSettings
from kie_api.models import RawUserRequest
from kie_api.registry.loader import load_registry
from kie_api.services.normalizer import RequestNormalizer


def test_submit_client_builds_nano_banana_pro_payload() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    client = SubmitClient(KieSettings(api_key="test-key"), registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="nano-banana-pro",
            prompt="make this image more cinematic",
            images=["https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/ref.png"],
            options={"aspect_ratio": "16:9", "resolution": "2K", "output_format": "png"},
        )
    )
    payload = client.build_payload(normalized)

    assert payload["model"] == "nano-banana-pro"
    assert payload["input"]["image_input"] == [
        "https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/ref.png"
    ]
    assert payload["input"]["aspect_ratio"] == "16:9"
    assert payload["input"]["resolution"] == "2K"
    assert payload["input"]["output_format"] == "png"


def test_submit_client_builds_nano_banana_2_prompt_only_payload() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    client = SubmitClient(KieSettings(api_key="test-key"), registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="nano-banana-2",
            prompt="generate a square ad image",
            options={"aspect_ratio": "1:1", "resolution": "4K", "output_format": "jpg"},
        )
    )
    payload = client.build_payload(normalized)

    assert payload["model"] == "nano-banana-2"
    assert "image_input" not in payload["input"]
    assert payload["input"]["aspect_ratio"] == "1:1"
    assert payload["input"]["resolution"] == "4K"
    assert payload["input"]["output_format"] == "jpg"


def test_submit_client_prefers_final_prompt_used_over_raw_prompt() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    client = SubmitClient(KieSettings(api_key="test-key"), registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="nano-banana-2",
            prompt="original user wording",
            options={"aspect_ratio": "1:1", "resolution": "1K", "output_format": "jpg"},
        )
    ).model_copy(
        update={
            "enhanced_prompt": "enhanced wrapper wording",
            "final_prompt_used": "enhanced wrapper wording",
        }
    )
    payload = client.build_payload(normalized)

    assert payload["input"]["prompt"] == "enhanced wrapper wording"


def test_submit_client_builds_kling_2_6_t2v_payload() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    client = SubmitClient(KieSettings(api_key="test-key"), registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-2.6-t2v",
            prompt="a clean product teaser with sound",
            options={"sound": True, "aspect_ratio": "16:9", "duration": 5},
        )
    )
    payload = client.build_payload(normalized)

    assert payload["model"] == "kling-2.6/text-to-video"
    assert payload["input"]["sound"] is True
    assert payload["input"]["aspect_ratio"] == "16:9"
    assert payload["input"]["duration"] == 5


def test_submit_client_builds_kling_2_6_i2v_payload() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    client = SubmitClient(KieSettings(api_key="test-key"), registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-2.6-i2v",
            prompt="animate this still with synced audio",
            images=["https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/start.png"],
            options={"sound": False, "duration": 10},
        )
    )
    payload = client.build_payload(normalized)

    assert payload["model"] == "kling-2.6/image-to-video"
    assert payload["input"]["image_urls"] == [
        "https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/start.png"
    ]
    assert payload["input"]["sound"] is False
    assert payload["input"]["duration"] == 10


def test_submit_client_builds_kling_3_video_payload() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    client = SubmitClient(KieSettings(api_key="test-key"), registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0",
            prompt="a subject turns and smiles",
            images=["https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/start.png"],
            options={"duration": 5, "mode": "pro"},
            callback_url="https://callback.example.com/kie",
        )
    )
    payload = client.build_payload(normalized)

    assert payload["model"] == "kling-3.0/video"
    assert payload["callBackUrl"] == "https://callback.example.com/kie"
    assert payload["input"]["image_urls"] == [
        "https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/start.png"
    ]
    assert payload["input"]["sound"] is True
    assert payload["input"]["duration"] == 5
    assert payload["input"]["mode"] == "pro"


def test_submit_client_preserves_first_last_frame_order_for_kling_3_i2v() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    client = SubmitClient(KieSettings(api_key="test-key"), registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0-i2v",
            prompt="animate from start frame to end frame",
            images=[
                "https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/start.png",
                "https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/end.png",
            ],
            options={"duration": 5, "mode": "pro"},
        )
    )
    payload = client.build_payload(normalized)

    assert payload["input"]["image_urls"] == [
        "https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/start.png",
        "https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/end.png",
    ]
    assert payload["input"]["sound"] is True


def test_submit_client_builds_motion_payload_with_separate_image_and_video_fields() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    client = SubmitClient(KieSettings(api_key="test-key"), registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0-motion",
            images=["https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/subject.png"],
            videos=["https://kieai.redpandaai.co/kieai/183531/videos/user-uploads/motion.mov"],
            options={"mode": "720p", "character_orientation": "image"},
        )
    )
    payload = client.build_payload(normalized)

    assert payload["model"] == "kling-3.0/motion-control"
    assert payload["input"]["input_urls"] == [
        "https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/subject.png"
    ]
    assert payload["input"]["video_urls"] == [
        "https://kieai.redpandaai.co/kieai/183531/videos/user-uploads/motion.mov"
    ]
    assert payload["input"]["mode"] == "720p"


def test_build_submission_payload_validates_motion_aliases_before_payload_build() -> None:
    registry = load_registry()
    result = validate_request(
        RawUserRequest(
            model_key="kling-3.0-motion",
            images=["https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/subject.png"],
            videos=["https://kieai.redpandaai.co/kieai/183531/videos/user-uploads/motion.mov"],
            options={"mode": "std", "character_orientation": "image"},
        ),
        registry,
    )
    payload = build_submission_payload(result, registry)

    assert payload["input"]["mode"] == "720p"


def test_submit_client_passes_through_docs_only_motion_background_source() -> None:
    registry = load_registry()
    normalizer = RequestNormalizer(registry)
    client = SubmitClient(KieSettings(api_key="test-key"), registry)

    normalized = normalizer.normalize(
        RawUserRequest(
            model_key="kling-3.0-motion",
            images=["https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/subject.png"],
            videos=["https://kieai.redpandaai.co/kieai/183531/videos/user-uploads/motion.mov"],
            options={
                "mode": "1080p",
                "character_orientation": "video",
                "background_source": "input_video",
            },
        )
    )
    payload = client.build_payload(normalized)

    assert payload["input"]["background_source"] == "input_video"
