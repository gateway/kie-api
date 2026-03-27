"""Validate normalized requests against explicit model specs."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, List

from ..enums import OptionType, ValidationState
from ..models import (
    InvalidInput,
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
