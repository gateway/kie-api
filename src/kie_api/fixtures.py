"""Reusable example fixtures for integration and wrapper tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple

from .enums import ValidationState
from .models import RawUserRequest


@dataclass(frozen=True)
class RequestFixture:
    key: str
    description: str
    request: RawUserRequest
    expected_state: ValidationState
    expected_model_key: str
    notes: Tuple[str, ...] = field(default_factory=tuple)


REQUEST_FIXTURES: Dict[str, RequestFixture] = {
    "nano_banana_pro_cinematic_edit": RequestFixture(
        key="nano_banana_pro_cinematic_edit",
        description="Use Nano Banana Pro on this image and make it more cinematic.",
        request=RawUserRequest(
            model_key="nano-banana-pro",
            prompt="Make this portrait more cinematic with deeper contrast and softer falloff.",
            images=["https://example.com/source/portrait.png"],
            options={"aspect_ratio": "16:9", "resolution": "2K", "output_format": "png"},
        ),
        expected_state=ValidationState.READY,
        expected_model_key="nano-banana-pro",
    ),
    "nano_banana_2_square_ad": RequestFixture(
        key="nano_banana_2_square_ad",
        description="Use Nano Banana 2 and generate a square ad image from this prompt.",
        request=RawUserRequest(
            model_key="nano-banana-2",
            prompt="Generate a square ad image for a premium cold brew launch with bold product text.",
            options={"aspect_ratio": "1:1", "resolution": "4K", "output_format": "jpg"},
        ),
        expected_state=ValidationState.READY,
        expected_model_key="nano-banana-2",
    ),
    "kling_3_image_to_video_5s": RequestFixture(
        key="kling_3_image_to_video_5s",
        description="Make a 5 second Kling 3.0 video from this image.",
        request=RawUserRequest(
            model_key="kling-3.0",
            prompt="Animate this still into a subtle 5 second cinematic push-in.",
            images=["https://example.com/source/start-frame.png"],
            options={"duration": 5, "mode": "pro"},
        ),
        expected_state=ValidationState.READY_WITH_WARNING,
        expected_model_key="kling-3.0-i2v",
        notes=("Expected to default multi_shots to false and infer aspect_ratio from media.",),
    ),
    "kling_3_first_last_frames_5s": RequestFixture(
        key="kling_3_first_last_frames_5s",
        description="Make a 5 second Kling 3.0 video from a first and last frame pair.",
        request=RawUserRequest(
            model_key="kling-3.0-i2v",
            prompt="Animate smoothly from the first frame to the last frame in 5 seconds.",
            images=[
                "https://example.com/source/start-frame.png",
                "https://example.com/source/end-frame.png",
            ],
            options={"duration": 5, "mode": "pro"},
        ),
        expected_state=ValidationState.READY_WITH_WARNING,
        expected_model_key="kling-3.0-i2v",
        notes=(
            "Two images are treated as first and last frame guidance.",
            "Kling 3.0 live page says aspect_ratio is invalid when first or last frames are provided.",
        ),
    ),
    "kling_3_motion_complete": RequestFixture(
        key="kling_3_motion_complete",
        description="Use Kling 3.0 motion control with this image and this motion clip.",
        request=RawUserRequest(
            model_key="kling-3.0-motion",
            images=["https://example.com/source/subject.png"],
            videos=["https://example.com/source/motion.mov"],
            options={"character_orientation": "image", "mode": "720p"},
        ),
        expected_state=ValidationState.READY,
        expected_model_key="kling-3.0-motion",
    ),
    "kling_3_motion_missing_video": RequestFixture(
        key="kling_3_motion_missing_video",
        description="Use Kling 3.0 motion control with only this image.",
        request=RawUserRequest(
            model_key="kling-3.0-motion",
            images=["https://example.com/source/subject.png"],
            options={"character_orientation": "image", "mode": "720p"},
        ),
        expected_state=ValidationState.NEEDS_INPUT,
        expected_model_key="kling-3.0-motion",
        notes=("Expected to surface a missing motion video requirement.",),
    ),
    "kling_3_pro_audio_15s": RequestFixture(
        key="kling_3_pro_audio_15s",
        description="Make a 15 second Kling 3.0 Pro video with audio.",
        request=RawUserRequest(
            model_key="kling-3.0-t2v",
            prompt="A premium launch trailer with layered motion graphics and voiceover pacing.",
            options={"duration": 15, "mode": "pro", "sound": True},
        ),
        expected_state=ValidationState.READY_WITH_DEFAULTS,
        expected_model_key="kling-3.0-t2v",
        notes=("Expected to default multi_shots to false and exercise pricing checks.",),
    ),
}


def get_request_fixture(key: str) -> RequestFixture:
    return REQUEST_FIXTURES[key]
