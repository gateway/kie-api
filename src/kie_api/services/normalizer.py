"""Normalize raw user requests into explicit model-aware requests."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Tuple

from ..enums import PromptPolicy, TaskMode
from ..exceptions import RequestNormalizationError
from ..models import AppliedDefault, NormalizedRequest, RawUserRequest
from ..registry.loader import SpecRegistry
from ..registry.models import ModelSpec


FAMILY_MODEL_ALIASES = {
    "kling-2.6": {"with_image": "kling-2.6-i2v", "without_image": "kling-2.6-t2v"},
    "kling-3.0": {"with_image": "kling-3.0-i2v", "without_image": "kling-3.0-t2v"},
}


class RequestNormalizer:
    """Apply safe request inference and defaults before validation."""

    def __init__(self, registry: SpecRegistry):
        self.registry = registry

    def normalize(self, raw_request: RawUserRequest) -> NormalizedRequest:
        spec = self._resolve_model_spec(raw_request)
        task_mode = self._resolve_task_mode(spec, raw_request)
        options = self._normalize_options(raw_request.options or {})
        options, defaults_applied = self._apply_defaults(spec, options)
        prompt_policy = self._resolve_prompt_policy(raw_request, spec)

        return NormalizedRequest(
            model_key=spec.key,
            provider_model=spec.provider_model,
            task_mode=task_mode,
            prompt=raw_request.prompt,
            raw_prompt=raw_request.prompt,
            enhanced_prompt=None,
            final_prompt_used=raw_request.prompt,
            prompt_policy=prompt_policy,
            prompt_profile_key=raw_request.prompt_profile_key,
            system_prompt_override=raw_request.system_prompt_override,
            images=deepcopy(raw_request.images),
            videos=deepcopy(raw_request.videos),
            audios=deepcopy(raw_request.audios),
            options=options,
            defaulted_fields=defaults_applied,
            callback_url=raw_request.callback_url,
            metadata=deepcopy(raw_request.metadata),
            debug={
                "raw_model_key": raw_request.model_key,
                "resolved_model_key": spec.key,
                "raw_options": deepcopy(raw_request.options),
                "requested_prompt_profile_key": raw_request.prompt_profile_key,
                "has_system_prompt_override": bool(raw_request.system_prompt_override),
            },
        )

    def _resolve_model_spec(self, raw_request: RawUserRequest) -> ModelSpec:
        if not raw_request.model_key:
            raise RequestNormalizationError("model_key is required for normalization")

        explicit = self.registry.model_specs.get(raw_request.model_key)
        if explicit:
            return explicit

        alias = FAMILY_MODEL_ALIASES.get(raw_request.model_key)
        if alias:
            if raw_request.images and len(raw_request.images) <= 2:
                return self.registry.get_model(alias["with_image"])
            if not raw_request.images:
                return self.registry.get_model(alias["without_image"])
            raise RequestNormalizationError(
                f"cannot safely infer a model variant for {raw_request.model_key} with "
                f"{len(raw_request.images)} image inputs"
            )

        raise RequestNormalizationError(f"unknown model key: {raw_request.model_key}")

    def _resolve_task_mode(self, spec: ModelSpec, raw_request: RawUserRequest) -> TaskMode:
        if raw_request.task_mode:
            if raw_request.task_mode not in spec.task_modes:
                raise RequestNormalizationError(
                    f"task mode {raw_request.task_mode} is not supported by {spec.key}"
                )
            return raw_request.task_mode

        if len(spec.task_modes) == 1:
            return spec.task_modes[0]

        if spec.key in {"nano-banana-pro", "nano-banana-2"}:
            return TaskMode.IMAGE_EDIT if raw_request.images else TaskMode.TEXT_TO_IMAGE

        raise RequestNormalizationError(f"unable to infer task mode for {spec.key}")

    def _normalize_options(self, options: Dict[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        for key, value in options.items():
            normalized_key = key.strip().lower().replace("-", "_")
            normalized[normalized_key] = self._normalize_option_value(value)
        return normalized

    def _normalize_option_value(self, value: Any) -> Any:
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "false"}:
                return lowered == "true"
            if lowered.isdigit():
                return int(lowered)
            return value.strip()
        return value

    def _apply_defaults(
        self, spec: ModelSpec, options: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[AppliedDefault]]:
        result = dict(options)
        defaults_applied: List[AppliedDefault] = []
        for name, option_spec in spec.options.items():
            if name not in result and option_spec.default is not None:
                result[name] = option_spec.default
                defaults_applied.append(
                    AppliedDefault(
                        field=name,
                        value=option_spec.default,
                        source="option_default",
                        reason=f"Applied spec option default for '{name}'.",
                    )
                )
        for name, value in spec.defaults.items():
            if name not in result:
                result[name] = value
                defaults_applied.append(
                    AppliedDefault(
                        field=name,
                        value=value,
                        source="spec_defaults",
                        reason=f"Applied model default for '{name}'.",
                    )
                )
        return result, defaults_applied

    def _resolve_prompt_policy(self, raw_request: RawUserRequest, spec: ModelSpec) -> PromptPolicy:
        if raw_request.prompt_policy:
            return raw_request.prompt_policy
        if raw_request.enhance is True:
            return PromptPolicy.AUTO
        if raw_request.enhance is False:
            return PromptPolicy.OFF
        return spec.prompt.enhancement_default_policy
