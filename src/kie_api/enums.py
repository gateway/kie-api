"""Shared enumerations used across the package."""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class MediaType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class TaskMode(StrEnum):
    TEXT_TO_IMAGE = "text_to_image"
    IMAGE_EDIT = "image_edit"
    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"
    MOTION_CONTROL = "motion_control"


class PromptPolicy(StrEnum):
    OFF = "off"
    ASK = "ask"
    AUTO = "auto"
    PREVIEW = "preview"


class PromptInputPattern(StrEnum):
    PROMPT_ONLY = "prompt_only"
    SINGLE_IMAGE = "single_image"
    FIRST_LAST_FRAMES = "first_last_frames"
    IMAGE_EDIT = "image_edit"
    MOTION_CONTROL = "motion_control"


class PromptResolutionSource(StrEnum):
    REQUEST_OVERRIDE = "request_override"
    MODEL_DEFAULT = "model_default"
    BEST_MATCH = "best_match"
    NONE = "none"


class PromptPresetStatus(StrEnum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class ValidationState(StrEnum):
    READY = "ready"
    READY_WITH_DEFAULTS = "ready_with_defaults"
    READY_WITH_WARNING = "ready_with_warning"
    NEEDS_INPUT = "needs_input"
    INVALID = "invalid"


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class GuardDecision(StrEnum):
    ALLOW = "allow"
    WARN = "warn"
    REQUIRE_CONFIRMATION = "require_confirmation"
    REJECT = "reject"


class OptionType(StrEnum):
    ENUM = "enum"
    BOOL = "bool"
    INT_RANGE = "int_range"
    STRING = "string"


class ProvenanceStatus(StrEnum):
    VERIFIED_LIVE = "verified_live"
    VERIFIED_DOCS = "verified_docs"
    INFERRED = "inferred"
    UNKNOWN = "unknown"
