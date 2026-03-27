"""Runtime request and response models."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import (
    GuardDecision,
    JobState,
    MediaType,
    PromptInputPattern,
    PromptPolicy,
    PromptResolutionSource,
    TaskMode,
    ValidationState,
)


class MediaReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media_type: MediaType
    url: Optional[str] = None
    path: Optional[str] = None
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    source: str = "remote"

    @model_validator(mode="after")
    def validate_location(self) -> "MediaReference":
        if not self.url and not self.path:
            raise ValueError("either url or path must be provided")
        return self

    @classmethod
    def from_value(cls, value: Any, media_type: MediaType) -> "MediaReference":
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls(media_type=media_type, **value)
        if isinstance(value, Path):
            return cls(media_type=media_type, path=str(value), filename=value.name, source="local")
        if isinstance(value, str):
            parsed = urlparse(value)
            if parsed.scheme in {"http", "https"}:
                name = Path(parsed.path).name or None
                return cls(media_type=media_type, url=value, filename=name, source="remote")
            path = Path(value)
            return cls(media_type=media_type, path=value, filename=path.name, source="local")
        raise TypeError(f"unsupported media reference value: {type(value)!r}")


def _coerce_media_list(value: Any, media_type: MediaType) -> List[MediaReference]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        value = [value]
    return [MediaReference.from_value(item, media_type) for item in value]


class RawUserRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model_key: Optional[str] = None
    task_mode: Optional[TaskMode] = None
    prompt: Optional[str] = None
    images: List[MediaReference] = Field(default_factory=list)
    videos: List[MediaReference] = Field(default_factory=list)
    audios: List[MediaReference] = Field(default_factory=list)
    options: Dict[str, Any] = Field(default_factory=dict)
    enhance: Optional[bool] = None
    prompt_policy: Optional[PromptPolicy] = None
    prompt_profile_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("prompt_profile_key", "prompt_preset_key"),
        serialization_alias="prompt_profile_key",
    )
    system_prompt_override: Optional[str] = None
    callback_url: Optional[str] = None
    multi_prompt: List["KlingMultiPromptShot"] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    raw_payload: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("images", mode="before")
    @classmethod
    def validate_images(cls, value: Any) -> List[MediaReference]:
        return _coerce_media_list(value, MediaType.IMAGE)

    @field_validator("videos", mode="before")
    @classmethod
    def validate_videos(cls, value: Any) -> List[MediaReference]:
        return _coerce_media_list(value, MediaType.VIDEO)

    @field_validator("audios", mode="before")
    @classmethod
    def validate_audios(cls, value: Any) -> List[MediaReference]:
        return _coerce_media_list(value, MediaType.AUDIO)

    @field_validator("multi_prompt", mode="before")
    @classmethod
    def validate_multi_prompt(cls, value: Any) -> List["KlingMultiPromptShot"]:
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise TypeError("multi_prompt must be a list of shot objects")
        return [item if isinstance(item, KlingMultiPromptShot) else KlingMultiPromptShot(**item) for item in value]


class MissingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    message: str
    media_type: Optional[MediaType] = None
    min_count: Optional[int] = None
    current_count: Optional[int] = None


class AppliedDefault(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    value: Any
    source: str = "spec_default"
    reason: str


class ValidationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class InvalidInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: Optional[str] = None
    message: str
    code: Optional[str] = None
    received: Optional[Any] = None


class NormalizedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_key: str
    provider_model: str
    task_mode: TaskMode
    prompt: Optional[str] = None
    raw_prompt: Optional[str] = None
    enhanced_prompt: Optional[str] = None
    final_prompt_used: Optional[str] = None
    prompt_policy: PromptPolicy = PromptPolicy.ASK
    prompt_profile_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("prompt_profile_key", "prompt_preset_key"),
        serialization_alias="prompt_profile_key",
    )
    system_prompt_override: Optional[str] = None
    images: List[MediaReference] = Field(default_factory=list)
    videos: List[MediaReference] = Field(default_factory=list)
    audios: List[MediaReference] = Field(default_factory=list)
    options: Dict[str, Any] = Field(default_factory=dict)
    defaulted_fields: List[AppliedDefault] = Field(default_factory=list)
    callback_url: Optional[str] = None
    multi_prompt: List["KlingMultiPromptShot"] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    debug: Dict[str, Any] = Field(default_factory=dict)


class KlingMultiPromptShot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str
    duration: int

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("multi_prompt shot prompt cannot be empty")
        return value.strip()


class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: ValidationState
    normalized_request: Optional[NormalizedRequest] = None
    missing_inputs: List[MissingInput] = Field(default_factory=list)
    defaulted_fields: List[AppliedDefault] = Field(default_factory=list)
    warning_details: List[ValidationMessage] = Field(default_factory=list)
    impossible_inputs: List[InvalidInput] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ProviderErrorDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_code: Optional[Any] = None
    message: str
    http_status: Optional[int] = None
    raw_response: Dict[str, Any] = Field(default_factory=dict)


class ObservedResponseFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixture_name: str
    endpoint: str
    method: str = "GET"
    observed_on: Optional[str] = None
    source_kind: str = "live_api"
    sanitized: bool = True
    notes: List[str] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)


class UploadUrlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_url: str
    file_name: Optional[str] = None


class UploadFileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_path: str
    file_name: Optional[str] = None


class StatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str


class PromptEnhancementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_key: str
    raw_prompt: str
    policy: PromptPolicy
    provider_model: Optional[str] = None
    task_mode: Optional[TaskMode] = None
    profile_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("profile_key", "preset_key"),
        serialization_alias="profile_key",
    )
    system_prompt_override: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class ResolvedPromptContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_key: str
    provider_model: str
    task_mode: TaskMode
    raw_prompt: Optional[str] = None
    prompt_policy: PromptPolicy
    enhancement_supported: bool = False
    input_pattern: Optional[PromptInputPattern] = None
    resolution_source: PromptResolutionSource = PromptResolutionSource.NONE
    requested_profile_key: Optional[str] = None
    default_profile_key: Optional[str] = None
    resolved_profile_key: Optional[str] = None
    requested_preset_key: Optional[str] = None
    default_preset_key: Optional[str] = None
    resolved_preset_key: Optional[str] = None
    profile_label: Optional[str] = None
    profile_version: Optional[str] = None
    profile_rules: List[str] = Field(default_factory=list)
    profile_notes: List[str] = Field(default_factory=list)
    preset_label: Optional[str] = None
    preset_version: Optional[str] = None
    preset_rules: List[str] = Field(default_factory=list)
    preset_notes: List[str] = Field(default_factory=list)
    resolved_template: Optional[str] = None
    rendered_system_prompt: Optional[str] = None
    system_prompt: Optional[str] = None
    system_prompt_source: str = "none"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PromptEnhancementResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy: PromptPolicy
    raw_prompt: Optional[str] = None
    enhanced_prompt: Optional[str] = None
    final_prompt_used: Optional[str] = None
    profile_key: Optional[str] = None
    profile_label: Optional[str] = None
    profile_version: Optional[str] = None
    profile_rules: List[str] = Field(default_factory=list)
    system_prompt: Optional[str] = None
    system_prompt_source: str = "none"
    preview_only: bool = False
    requires_confirmation: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UploadResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    provider_code: Optional[Any] = None
    provider_message: Optional[str] = None
    file_id: Optional[str] = None
    storage_id: Optional[str] = None
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    download_url: Optional[str] = None
    mime_type: Optional[str] = None
    content_length: Optional[int] = None
    expires_at: Optional[str] = None
    uploaded_at: Optional[str] = None
    raw_response: Dict[str, Any] = Field(default_factory=dict)


class DownloadResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_url: str
    destination_path: str
    content_type: Optional[str] = None
    content_length: Optional[int] = None
    http_status: Optional[int] = None


class PreparedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    normalized_request: NormalizedRequest
    upload_results: List[UploadResult] = Field(default_factory=list)
    reused_uploaded_media: List[MediaReference] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    debug: Dict[str, Any] = Field(default_factory=dict)


class SubmissionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    task_id: Optional[str] = None
    provider_code: Optional[Any] = None
    provider_message: Optional[str] = None
    provider_payload: Dict[str, Any] = Field(default_factory=dict)
    raw_response: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


class StatusResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    state: JobState
    provider_code: Optional[Any] = None
    provider_message: Optional[str] = None
    provider_status: Optional[str] = None
    progress: Optional[float] = None
    output_urls: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    raw_response: Dict[str, Any] = Field(default_factory=dict)


class TaskWaitResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    terminal: bool
    timed_out: bool = False
    final_status: Optional[StatusResult] = None
    history: List[StatusResult] = Field(default_factory=list)
    elapsed_seconds: float = 0.0


class CreditBalanceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    balance_available: bool = False
    available_credits: Optional[float] = None
    credit_unit: Optional[str] = None
    endpoint_path: Optional[str] = None
    provider_code: Optional[Any] = None
    provider_message: Optional[str] = None
    notes: List[str] = Field(default_factory=list)
    raw_response: Dict[str, Any] = Field(default_factory=dict)


class EstimatedCost(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_key: str
    estimated_credits: Optional[float] = None
    estimated_cost_usd: Optional[float] = None
    currency: str = "USD"
    is_known: bool = False
    has_numeric_estimate: bool = False
    is_authoritative: bool = False
    pricing_version: Optional[str] = None
    pricing_source_kind: Optional[str] = None
    pricing_status: Optional[str] = None
    billing_unit: Optional[str] = None
    applied_multipliers: Dict[str, float] = Field(default_factory=dict)
    applied_adders_credits: Dict[str, float] = Field(default_factory=dict)
    applied_adders_cost_usd: Dict[str, float] = Field(default_factory=dict)
    assumptions: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class PreflightDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: GuardDecision
    estimated_cost: EstimatedCost
    remaining_credits: Optional[float] = None
    remaining_credits_checked: bool = False
    requires_confirmation: bool = False
    can_submit: bool = True
    reason: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class CreditGuardResult(PreflightDecision):
    model_config = ConfigDict(extra="forbid")
