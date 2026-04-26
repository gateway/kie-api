"""Validate normalized requests against explicit model specs."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, List

from ..enums import MediaRole, OptionType, TaskMode, ValidationState
from ..models import (
    InvalidInput,
    MediaReference,
    MissingInput,
    NormalizedRequest,
    ValidationMessage,
    ValidationResult,
)
from ..registry.loader import SpecRegistry


class RequestValidator:
    """Validate normalized requests and return structured recoverable gaps."""

    def __init__(self, registry: SpecRegistry):
        self.registry = registry

    def validate(self, request: NormalizedRequest) -> ValidationResult:
        spec = self.registry.get_model(request.model_key)
        missing_inputs: List[MissingInput] = []
        normalized = deepcopy(request)
        defaulted_fields = deepcopy(normalized.defaulted_fields)
        warning_details: List[ValidationMessage] = []
        impossible_inputs: List[InvalidInput] = []

        if request.task_mode not in spec.task_modes:
            impossible_inputs.append(
                InvalidInput(
                    field="task_mode",
                    code="unsupported_task_mode",
                    message=f"{request.model_key} does not support task mode {request.task_mode}.",
                    received=str(request.task_mode),
                )
            )

        if spec.prompt.required and not (request.prompt or "").strip():
            if not (
                request.model_key in {"kling-3.0-t2v", "kling-3.0-i2v"}
                and normalized.options.get("multi_shots") is True
            ):
                missing_inputs.append(
                    MissingInput(field="prompt", message="A prompt is required for this model.")
                )

        media_collections = {
            "image": normalized.images,
            "video": normalized.videos,
            "audio": normalized.audios,
        }
        for media_name, count_spec in spec.inputs.items():
            current_count = len(media_collections[media_name])
            if current_count < count_spec.required_min:
                missing_inputs.append(
                    MissingInput(
                        field=media_name,
                        message=(
                            f"{spec.label} requires at least {count_spec.required_min} {media_name} "
                            f"input(s)."
                        ),
                        media_type=media_name,
                        min_count=count_spec.required_min,
                        current_count=current_count,
                    )
                )
            if count_spec.required_max is not None and current_count > count_spec.required_max:
                impossible_inputs.append(
                    InvalidInput(
                        field=media_name,
                        code="too_many_media_inputs",
                        message=(
                            f"{spec.label} accepts at most {count_spec.required_max} {media_name} "
                            f"input(s), received {current_count}."
                        ),
                        received=current_count,
                    )
                )

        if request.model_key == "kling-3.0-i2v":
            image_count = len(normalized.images)
            if image_count == 1:
                normalized.debug["frame_guidance_mode"] = "start_frame"
            elif image_count == 2:
                normalized.debug["frame_guidance_mode"] = "first_last_frames"
                if normalized.options.get("aspect_ratio") is not None:
                    impossible_inputs.append(
                        InvalidInput(
                            field="aspect_ratio",
                            code="aspect_ratio_not_allowed_with_first_last_frames",
                            message=(
                                "Kling 3.0 Image to Video does not allow 'aspect_ratio' when both "
                                "first and last frame images are provided."
                            ),
                            received=normalized.options.get("aspect_ratio"),
                        )
                    )
            if normalized.options.get("multi_shots") is True and image_count > 1:
                impossible_inputs.append(
                    InvalidInput(
                        field="image",
                        code="too_many_images_for_kling_multi_shot",
                        message=(
                            "Kling 3.0 multi-shot mode only supports a single first-frame image."
                        ),
                        received=image_count,
                    )
                )

        if request.model_key == "seedance-2.0":
            first_frame_images = _media_with_role(normalized.images, MediaRole.FIRST_FRAME)
            last_frame_images = _media_with_role(normalized.images, MediaRole.LAST_FRAME)
            reference_images = _media_with_role(normalized.images, MediaRole.REFERENCE)
            reference_videos = _media_with_role(normalized.videos, MediaRole.REFERENCE)
            reference_audios = _media_with_role(normalized.audios, MediaRole.REFERENCE)
            has_reference_media = bool(reference_images or reference_videos or reference_audios)
            has_frame_mode = bool(first_frame_images or last_frame_images)
            unlabeled_media = [
                item
                for collection in (normalized.images, normalized.videos, normalized.audios)
                for item in collection
                if item.role is None
            ]

            if unlabeled_media:
                impossible_inputs.append(
                    InvalidInput(
                        field="media",
                        code="seedance_media_role_required",
                        message=(
                            "Seedance 2.0 media inputs must declare a role of first_frame, last_frame, or reference."
                        ),
                        received=[item.model_dump() for item in unlabeled_media],
                    )
                )

            if normalized.task_mode == TaskMode.TEXT_TO_VIDEO and (
                normalized.images or normalized.videos or normalized.audios
            ):
                impossible_inputs.append(
                    InvalidInput(
                        field="task_mode",
                        code="seedance_text_to_video_cannot_include_media",
                        message=(
                            "Seedance 2.0 text-to-video requests cannot include first/last frame inputs or reference media."
                        ),
                        received=normalized.task_mode.value,
                    )
                )

            if normalized.task_mode == TaskMode.REFERENCE_TO_VIDEO and not (
                normalized.images or normalized.videos or normalized.audios
            ):
                missing_inputs.append(
                    MissingInput(
                        field="media",
                        message=(
                            "Seedance 2.0 reference-to-video requests require a first frame, first+last frames, or reference media."
                        ),
                    )
                )

            if has_frame_mode and has_reference_media:
                impossible_inputs.append(
                    InvalidInput(
                        field="images",
                        code="seedance_frames_and_references_are_mutually_exclusive",
                        message=(
                            "Seedance 2.0 does not allow first/last frame guidance together with multimodal reference assets."
                        ),
                        received={
                            "first_frame_count": len(first_frame_images),
                            "last_frame_count": len(last_frame_images),
                            "reference_image_count": len(reference_images),
                            "reference_video_count": len(reference_videos),
                            "reference_audio_count": len(reference_audios),
                        },
                    )
                )

            if last_frame_images and not first_frame_images:
                impossible_inputs.append(
                    InvalidInput(
                        field="images",
                        code="seedance_last_frame_requires_first_frame",
                        message="Seedance 2.0 requires a first-frame image when a last-frame image is provided.",
                        received={"last_frame_count": len(last_frame_images)},
                    )
                )

            if len(first_frame_images) > 1:
                impossible_inputs.append(
                    InvalidInput(
                        field="images",
                        code="too_many_first_frame_images",
                        message="Seedance 2.0 accepts at most one first-frame image.",
                        received=len(first_frame_images),
                    )
                )

            if len(last_frame_images) > 1:
                impossible_inputs.append(
                    InvalidInput(
                        field="images",
                        code="too_many_last_frame_images",
                        message="Seedance 2.0 accepts at most one last-frame image.",
                        received=len(last_frame_images),
                    )
                )

            if len(reference_images) > 9:
                impossible_inputs.append(
                    InvalidInput(
                        field="images",
                        code="too_many_reference_images",
                        message="Seedance 2.0 accepts at most 9 reference images.",
                        received=len(reference_images),
                    )
                )

            if len(reference_videos) > 3:
                impossible_inputs.append(
                    InvalidInput(
                        field="videos",
                        code="too_many_reference_videos",
                        message="Seedance 2.0 accepts at most 3 reference videos.",
                        received=len(reference_videos),
                    )
                )

            if len(reference_audios) > 3:
                impossible_inputs.append(
                    InvalidInput(
                        field="audios",
                        code="too_many_reference_audios",
                        message="Seedance 2.0 accepts at most 3 reference audios.",
                        received=len(reference_audios),
                    )
                )

            video_total_duration = _sum_known_media_durations(reference_videos)
            if video_total_duration is not None and video_total_duration > 15:
                impossible_inputs.append(
                    InvalidInput(
                        field="videos",
                        code="reference_video_duration_limit_exceeded",
                        message="Seedance 2.0 reference videos must total 15 seconds or less.",
                        received=video_total_duration,
                    )
                )

            if reference_audios:
                warning_details.append(
                    ValidationMessage(
                        field="audios",
                        code="seedance_reference_audio_duration_unverified",
                        message=(
                            "Seedance 2.0 reference audio count is validated, but total reference audio duration still needs live verification."
                        ),
                    )
                )

        if request.model_key in {"kling-3.0-t2v", "kling-3.0-i2v"}:
            multi_shots_enabled = normalized.options.get("multi_shots") is True
            if normalized.multi_prompt and not multi_shots_enabled:
                impossible_inputs.append(
                    InvalidInput(
                        field="multi_prompt",
                        code="multi_prompt_requires_multi_shots",
                        message=(
                            "Kling 3.0 only accepts 'multi_prompt' when 'multi_shots' is enabled."
                        ),
                        received=[item.model_dump() for item in normalized.multi_prompt],
                    )
                )
            if multi_shots_enabled and not normalized.multi_prompt:
                missing_inputs.append(
                    MissingInput(
                        field="multi_prompt",
                        message=(
                            "Kling 3.0 multi-shot mode requires a 'multi_prompt' array of shots."
                        ),
                    )
                )
            for index, shot in enumerate(normalized.multi_prompt):
                if shot.duration < 1 or shot.duration > 12:
                    impossible_inputs.append(
                        InvalidInput(
                            field=f"multi_prompt[{index}].duration",
                            code="invalid_multi_prompt_duration",
                            message=(
                                "Each Kling 3.0 multi-shot entry must use a duration between 1 and 12 seconds."
                            ),
                            received=shot.duration,
                        )
                    )
                if len(shot.prompt) > 500:
                    impossible_inputs.append(
                        InvalidInput(
                            field=f"multi_prompt[{index}].prompt",
                            code="multi_prompt_prompt_too_long",
                            message=(
                                "Each Kling 3.0 multi-shot prompt must be 500 characters or fewer."
                            ),
                            received=len(shot.prompt),
                        )
                    )

        if request.model_key in {
            "gpt-image-2-image-to-image",
            "gpt-image-2-text-to-image",
        }:
            aspect_ratio = normalized.options.get("aspect_ratio")
            resolution = normalized.options.get("resolution")
            if resolution == "4K" and aspect_ratio == "1:1":
                impossible_inputs.append(
                    InvalidInput(
                        field="resolution",
                        code="gpt_image_2_square_4k_not_allowed",
                        message=(
                            "GPT Image 2 does not allow 4K resolution with a 1:1 "
                            "aspect ratio."
                        ),
                        received={"aspect_ratio": aspect_ratio, "resolution": resolution},
                    )
                )
            if resolution in {"2K", "4K"} and aspect_ratio == "auto":
                impossible_inputs.append(
                    InvalidInput(
                        field="resolution",
                        code="gpt_image_2_auto_aspect_high_resolution_not_allowed",
                        message=(
                            "GPT Image 2 only supports 1K output when aspect_ratio "
                            "is auto or omitted."
                        ),
                        received={"aspect_ratio": aspect_ratio, "resolution": resolution},
                    )
                )

        for option_name, option_spec in spec.options.items():
            if option_name not in normalized.options or normalized.options[option_name] is None:
                if option_spec.required and not (
                    option_name == "aspect_ratio"
                    and option_spec.allow_infer_from_media
                    and normalized.images
                ):
                    missing_inputs.append(
                        MissingInput(
                            field=option_name,
                            message=f"Option '{option_name}' is required for {spec.label}.",
                        )
                    )
                elif option_spec.allow_infer_from_media and normalized.images:
                    message = (
                        f"Option '{option_name}' was omitted and will be inferred from image input "
                        f"by {spec.label}."
                    )
                    if (
                        request.model_key == "kling-3.0-i2v"
                        and option_name == "aspect_ratio"
                        and len(normalized.images) == 2
                    ):
                        message = (
                            "Option 'aspect_ratio' was omitted because Kling 3.0 treats it as invalid "
                            "when both first and last frame images are provided."
                        )
                    warning_details.append(
                        ValidationMessage(
                            field=option_name,
                            code="provider_inferred_from_media",
                            message=message,
                        )
                    )
                continue

            value = normalized.options[option_name]
            if option_spec.value_aliases and isinstance(value, str):
                value = option_spec.value_aliases.get(value, value)
                normalized.options[option_name] = value

            if option_spec.type == OptionType.BOOL and not isinstance(value, bool):
                impossible_inputs.append(
                    self._invalid_option(
                        option_name,
                        "invalid_boolean",
                        f"Option '{option_name}' must be a boolean.",
                        value,
                    )
                )
            elif option_spec.type == OptionType.ENUM and option_spec.allowed and value not in option_spec.allowed:
                impossible_inputs.append(
                    self._invalid_option(
                        option_name,
                        "invalid_enum_value",
                        (
                            f"Option '{option_name}' must be one of {option_spec.allowed}, "
                            f"received {value!r}."
                        ),
                        value,
                    )
                )
            elif option_spec.type == OptionType.INT_RANGE:
                if not isinstance(value, int):
                    impossible_inputs.append(
                        self._invalid_option(
                            option_name,
                            "invalid_integer",
                            f"Option '{option_name}' must be an integer.",
                            value,
                        )
                    )
                else:
                    if option_spec.min is not None and value < option_spec.min:
                        impossible_inputs.append(
                            self._invalid_option(
                                option_name,
                                "below_minimum",
                                f"Option '{option_name}' must be >= {option_spec.min}.",
                                value,
                            )
                        )
                    if option_spec.max is not None and value > option_spec.max:
                        impossible_inputs.append(
                            self._invalid_option(
                                option_name,
                                "above_maximum",
                                f"Option '{option_name}' must be <= {option_spec.max}.",
                                value,
                            )
                        )

        for option_name in normalized.options:
            if option_name not in spec.options:
                warning_details.append(
                    ValidationMessage(
                        field=option_name,
                        code="provider_passthrough_option",
                        message=f"Unknown option '{option_name}' preserved for provider passthrough.",
                    )
                )

        errors = [item.message for item in impossible_inputs]
        warnings = [item.message for item in warning_details]

        if impossible_inputs:
            return ValidationResult(
                state=ValidationState.INVALID,
                normalized_request=normalized,
                missing_inputs=missing_inputs,
                defaulted_fields=defaulted_fields,
                warning_details=warning_details,
                impossible_inputs=impossible_inputs,
                errors=errors,
                warnings=warnings,
            )

        if missing_inputs:
            return ValidationResult(
                state=ValidationState.NEEDS_INPUT,
                normalized_request=normalized,
                missing_inputs=missing_inputs,
                defaulted_fields=defaulted_fields,
                warning_details=warning_details,
                warnings=warnings,
            )

        if warning_details:
            return ValidationResult(
                state=ValidationState.READY_WITH_WARNING,
                normalized_request=normalized,
                defaulted_fields=defaulted_fields,
                warning_details=warning_details,
                warnings=warnings,
            )

        if defaulted_fields:
            return ValidationResult(
                state=ValidationState.READY_WITH_DEFAULTS,
                normalized_request=normalized,
                defaulted_fields=defaulted_fields,
            )

        return ValidationResult(
            state=ValidationState.READY,
            normalized_request=normalized,
        )

    def _invalid_option(
        self, field: str, code: str, message: str, received: Any
    ) -> InvalidInput:
        return InvalidInput(field=field, code=code, message=message, received=received)


def _media_with_role(
    media: List[MediaReference],
    role: MediaRole,
) -> List[MediaReference]:
    return [item for item in media if item.role == role]


def _sum_known_media_durations(media: List[MediaReference]) -> int | None:
    durations: List[int] = []
    for item in media:
        duration_hint = item.duration_seconds
        if duration_hint is None:
            return None
        try:
            durations.append(int(duration_hint))
        except (TypeError, ValueError):
            return None
    return sum(durations)
