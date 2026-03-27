"""Prompt enhancement framework with pluggable backends."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Callable, Optional

from ..enums import PromptInputPattern, PromptPolicy, PromptResolutionSource, TaskMode
from ..exceptions import PromptTemplateRenderError
from ..models import (
    NormalizedRequest,
    PromptEnhancementRequest,
    PromptEnhancementResult,
    ResolvedPromptContext,
)
from ..registry.loader import SpecRegistry

PromptEnhancerBackend = Callable[[PromptEnhancementRequest, str], str]


class PromptEnhancer:
    """Handle prompt enhancement policy without coupling to transport code."""

    def __init__(
        self,
        registry: SpecRegistry,
        backend: Optional[PromptEnhancerBackend] = None,
    ):
        self.registry = registry
        self.backend = backend

    def resolve_context(self, request: NormalizedRequest) -> ResolvedPromptContext:
        input_pattern = _detect_input_pattern(request)
        profile, resolution_source = self.registry.resolve_prompt_profile_match(
            request.model_key,
            requested_key=request.prompt_profile_key,
            task_mode=request.task_mode,
            input_pattern=input_pattern,
        )
        rendered_system_prompt = None
        resolved_template = profile.system_prompt if profile else None
        system_prompt_source = "none"
        if request.system_prompt_override:
            rendered_system_prompt = _render_template(
                request.system_prompt_override,
                _build_template_context(request, input_pattern),
            )
            system_prompt_source = "override"
        elif profile:
            rendered_system_prompt = _render_template(
                profile.system_prompt,
                _build_template_context(request, input_pattern),
            )
            system_prompt_source = "profile"

        default_profile_key = self.registry.get_model(request.model_key).prompt.default_profile_key
        default_profile_key = (
            self.registry.get_model(request.model_key)
            .prompt.default_profile_keys_by_input_pattern.get(input_pattern, default_profile_key)
        )

        return ResolvedPromptContext(
            model_key=request.model_key,
            provider_model=request.provider_model,
            task_mode=request.task_mode,
            raw_prompt=request.raw_prompt or request.prompt,
            prompt_policy=request.prompt_policy,
            input_pattern=input_pattern,
            resolution_source=resolution_source,
            enhancement_supported=self.registry.get_model(request.model_key).prompt.enhancement_supported,
            requested_profile_key=request.prompt_profile_key,
            default_profile_key=default_profile_key,
            resolved_profile_key=profile.key if profile else None,
            requested_preset_key=request.prompt_profile_key,
            default_preset_key=default_profile_key,
            resolved_preset_key=profile.key if profile else None,
            profile_label=profile.label if profile else None,
            profile_version=profile.version if profile else None,
            profile_rules=deepcopy(profile.rules) if profile else [],
            profile_notes=deepcopy(profile.notes) if profile else [],
            preset_label=profile.label if profile else None,
            preset_version=profile.version if profile else None,
            preset_rules=deepcopy(profile.rules) if profile else [],
            preset_notes=deepcopy(profile.notes) if profile else [],
            resolved_template=resolved_template,
            rendered_system_prompt=rendered_system_prompt,
            system_prompt=rendered_system_prompt,
            system_prompt_source=system_prompt_source,
            metadata={
                "system_prompt_overridden": bool(request.system_prompt_override),
                "preset_status": str(profile.status) if profile else None,
            },
        )

    def prepare(self, request: NormalizedRequest) -> PromptEnhancementResult:
        resolved = self.resolve_context(request)

        enhancement_request = PromptEnhancementRequest(
            model_key=request.model_key,
            raw_prompt=request.raw_prompt or request.prompt or "",
            policy=request.prompt_policy,
            provider_model=request.provider_model,
            task_mode=request.task_mode,
            profile_key=resolved.resolved_profile_key,
            system_prompt_override=request.system_prompt_override,
            context={
                "task_mode": request.task_mode.value,
                "system_prompt_source": resolved.system_prompt_source,
                "input_pattern": resolved.input_pattern.value if resolved.input_pattern else None,
            },
        )

        if request.prompt_policy == PromptPolicy.OFF:
            return PromptEnhancementResult(
                policy=request.prompt_policy,
                raw_prompt=enhancement_request.raw_prompt,
                final_prompt_used=enhancement_request.raw_prompt,
                profile_key=resolved.resolved_profile_key,
                profile_label=resolved.profile_label,
                profile_version=resolved.profile_version,
                profile_rules=resolved.profile_rules,
                system_prompt=resolved.rendered_system_prompt,
                system_prompt_source=resolved.system_prompt_source,
                metadata={
                    "used_backend": False,
                    "default_profile_key": resolved.default_profile_key,
                    "requested_profile_key": resolved.requested_profile_key,
                    "resolved_preset_key": resolved.resolved_preset_key,
                },
            )

        if request.prompt_policy == PromptPolicy.ASK:
            return PromptEnhancementResult(
                policy=request.prompt_policy,
                raw_prompt=enhancement_request.raw_prompt,
                profile_key=resolved.resolved_profile_key,
                profile_label=resolved.profile_label,
                profile_version=resolved.profile_version,
                profile_rules=resolved.profile_rules,
                system_prompt=resolved.rendered_system_prompt,
                system_prompt_source=resolved.system_prompt_source,
                requires_confirmation=True,
                metadata={
                    "used_backend": False,
                    "default_profile_key": resolved.default_profile_key,
                    "requested_profile_key": resolved.requested_profile_key,
                    "resolved_preset_key": resolved.resolved_preset_key,
                },
            )

        enhanced_prompt = self._enhance_prompt(enhancement_request, resolved.rendered_system_prompt or "")

        if request.prompt_policy == PromptPolicy.PREVIEW:
            return PromptEnhancementResult(
                policy=request.prompt_policy,
                raw_prompt=enhancement_request.raw_prompt,
                enhanced_prompt=enhanced_prompt,
                final_prompt_used=None,
                profile_key=resolved.resolved_profile_key,
                profile_label=resolved.profile_label,
                profile_version=resolved.profile_version,
                profile_rules=resolved.profile_rules,
                system_prompt=resolved.rendered_system_prompt,
                system_prompt_source=resolved.system_prompt_source,
                preview_only=True,
                metadata={
                    "used_backend": bool(self.backend),
                    "default_profile_key": resolved.default_profile_key,
                    "requested_profile_key": resolved.requested_profile_key,
                    "resolved_preset_key": resolved.resolved_preset_key,
                },
            )

        return PromptEnhancementResult(
            policy=request.prompt_policy,
            raw_prompt=enhancement_request.raw_prompt,
            enhanced_prompt=enhanced_prompt,
            final_prompt_used=enhanced_prompt,
            profile_key=resolved.resolved_profile_key,
            profile_label=resolved.profile_label,
            profile_version=resolved.profile_version,
            profile_rules=resolved.profile_rules,
            system_prompt=resolved.rendered_system_prompt,
            system_prompt_source=resolved.system_prompt_source,
            metadata={
                "used_backend": bool(self.backend),
                "default_profile_key": resolved.default_profile_key,
                "requested_profile_key": resolved.requested_profile_key,
                "resolved_preset_key": resolved.resolved_preset_key,
            },
        )

    def _enhance_prompt(self, request: PromptEnhancementRequest, system_prompt: str) -> str:
        if self.backend:
            return self.backend(request, system_prompt)
        return " ".join(request.raw_prompt.split())


_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def _detect_input_pattern(request: NormalizedRequest) -> PromptInputPattern:
    if request.task_mode == TaskMode.MOTION_CONTROL:
        return PromptInputPattern.MOTION_CONTROL
    if request.task_mode == TaskMode.IMAGE_EDIT:
        return PromptInputPattern.IMAGE_EDIT
    if request.task_mode == TaskMode.IMAGE_TO_VIDEO:
        if len(request.images) >= 2:
            return PromptInputPattern.FIRST_LAST_FRAMES
        return PromptInputPattern.SINGLE_IMAGE
    return PromptInputPattern.PROMPT_ONLY


def _build_template_context(
    request: NormalizedRequest,
    input_pattern: PromptInputPattern,
):
    return {
        "user_prompt": request.raw_prompt or request.prompt or "",
        "model_key": request.model_key,
        "task_mode": request.task_mode.value,
        "input_pattern": input_pattern.value,
        "image_count": str(len(request.images)),
        "video_count": str(len(request.videos)),
        "audio_count": str(len(request.audios)),
    }


def _render_template(template: str, context: dict) -> str:
    missing = []

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in context:
            missing.append(key)
            return match.group(0)
        return str(context[key])

    rendered = _PLACEHOLDER_RE.sub(replace, template)
    if missing:
        raise PromptTemplateRenderError(
            "prompt preset template referenced unresolved variables: " + ", ".join(sorted(set(missing)))
        )
    return rendered
