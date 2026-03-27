"""Typed schema for model specs, prompt presets, and pricing resources."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from ..enums import (
    OptionType,
    PromptInputPattern,
    PromptPolicy,
    PromptPresetStatus,
    ProvenanceStatus,
    TaskMode,
)


class InputCountSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_min: int = 0
    required_max: Optional[int] = None


class InputConstraintsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_formats: Optional[List[str]] = None
    image_max_mb: Optional[float] = None
    image_min_dimension_px: Optional[int] = None
    image_aspect_ratio_min: Optional[float] = None
    image_aspect_ratio_max: Optional[float] = None
    video_formats: Optional[List[str]] = None
    video_max_mb: Optional[float] = None
    video_duration_min_seconds: Optional[int] = None
    video_duration_max_seconds: Optional[int] = None
    video_min_dimension_px: Optional[int] = None
    video_aspect_ratio_min: Optional[float] = None
    video_aspect_ratio_max: Optional[float] = None


class OptionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: OptionType
    allowed: Optional[List[Any]] = None
    default: Optional[Any] = None
    min: Optional[int] = None
    max: Optional[int] = None
    required: bool = False
    provider_field: Optional[str] = None
    allow_infer_from_media: bool = False
    value_aliases: Dict[str, str] = Field(default_factory=dict)
    notes: Optional[str] = None


class PromptSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    required: bool = True
    max_chars: Optional[int] = None
    enhancement_supported: bool = False
    enhancement_default_policy: PromptPolicy = PromptPolicy.OFF
    default_profile_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("default_profile_key", "enhancement_profile"),
        serialization_alias="default_profile_key",
    )
    default_profile_keys_by_input_pattern: Dict[PromptInputPattern, str] = Field(default_factory=dict)

    @property
    def enhancement_profile(self) -> Optional[str]:
        return self.default_profile_key


class TransportSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    endpoint_family: str
    create_path: str
    status_path: str
    callback_supported: bool = False


class VerificationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verified_from: List[str] = Field(default_factory=list)
    verified_on: Optional[str] = None
    verification_notes: List[str] = Field(default_factory=list)
    field_provenance: Dict[str, ProvenanceStatus] = Field(default_factory=dict)


class ModelSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    family: str
    provider_model: str
    task_modes: List[TaskMode]
    inputs: Dict[str, InputCountSpec]
    input_constraints: Optional[InputConstraintsSpec] = None
    options: Dict[str, OptionSpec] = Field(default_factory=dict)
    prompt: PromptSpec
    defaults: Dict[str, Any] = Field(default_factory=dict)
    transport: TransportSpec
    verification: VerificationSpec


class PromptProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    key: str
    label: str
    version: str = "v1"
    description: Optional[str] = None
    applies_to_models: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("applies_to_models", "applies_to"),
        serialization_alias="applies_to_models",
    )
    applies_to_task_modes: List[TaskMode] = Field(default_factory=list)
    applies_to_input_patterns: List[PromptInputPattern] = Field(default_factory=list)
    template: str = Field(
        validation_alias=AliasChoices("template", "prompt_markdown"),
        serialization_alias="template",
    )
    variables: List[str] = Field(default_factory=list)
    rules: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    status: PromptPresetStatus = PromptPresetStatus.ACTIVE
    source: Optional[str] = "builtin"
    source_path: Optional[str] = None

    @property
    def system_prompt(self) -> str:
        return self.template

    @property
    def prompt_markdown(self) -> str:
        return self.template

    @property
    def applies_to(self) -> List[str]:
        return self.applies_to_models


class PricingRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_key: str
    pricing_status: str = "unknown"
    billing_unit: str = "request"
    provider: Optional[str] = None
    interface_type: Optional[str] = None
    anchor_url: Optional[str] = None
    raw_credit_text: Optional[str] = None
    raw_usd_text: Optional[str] = None
    base_credits: Optional[float] = None
    base_cost_usd: Optional[float] = None
    multipliers: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    adders_credits: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    adders_cost_usd: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)

    @property
    def option_dependent_fields(self) -> List[str]:
        return sorted(
            set(self.multipliers)
            | set(self.adders_credits)
            | set(self.adders_cost_usd)
        )


class PricingSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    label: str
    released_on: Optional[str] = None
    currency: str = "USD"
    source_kind: str = "unknown"
    source_url: Optional[str] = None
    notes: List[str] = Field(default_factory=list)
    rules: List[PricingRule] = Field(default_factory=list)
