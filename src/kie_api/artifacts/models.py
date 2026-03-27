"""Typed models for run artifact bundles."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..enums import TaskMode


class ArtifactSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    source_path: str
    role: str
    original_filename: Optional[str] = None
    source_url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ArtifactDerivativeSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_web_max_dimension: int = 1600
    image_web_format: str = "webp"
    image_web_quality: int = 82
    image_thumb_max_dimension: int = 384
    image_thumb_format: str = "webp"
    image_thumb_quality: int = 76
    video_web_max_width: int = 1280
    video_poster_width: int = 640
    video_poster_format: str = "jpg"
    allow_upscale: bool = False
    enable_sha256: bool = True


class RunSourceContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: Optional[str] = None
    source_user: Optional[str] = None
    source_channel: Optional[str] = None
    source_agent: Optional[str] = None
    project_name: Optional[str] = None
    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DerivedAssetRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    relative_path: str
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None
    bytes: Optional[int] = None
    sha256: Optional[str] = None
    codec_name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AssetRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    role: str
    relative_path: str
    original_path: Optional[str] = None
    original_filename: Optional[str] = None
    source_path: Optional[str] = None
    source_url: Optional[str] = None
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None
    bytes: Optional[int] = None
    bytes_original: Optional[int] = None
    sha256: Optional[str] = None
    codec_name: Optional[str] = None
    web_path: Optional[str] = None
    thumb_path: Optional[str] = None
    poster_path: Optional[str] = None
    bytes_web: Optional[int] = None
    bytes_thumb: Optional[int] = None
    bytes_poster: Optional[int] = None
    derivatives: List[DerivedAssetRecord] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PromptRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw: Optional[str] = None
    enhanced: Optional[str] = None
    final_used: Optional[str] = None
    prompt_profile: Optional[str] = None
    raw_path: Optional[str] = None
    enhanced_path: Optional[str] = None


class ProviderTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: Optional[str] = None
    request_path: Optional[str] = None
    submit_payload_path: Optional[str] = None
    submit_response_path: Optional[str] = None
    final_status_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RunArtifactCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    model_key: str
    provider_model: Optional[str] = None
    task_mode: Optional[TaskMode] = None
    slug: Optional[str] = None
    created_at: Optional[str] = None
    source_metadata: Dict[str, Any] = Field(default_factory=dict)
    source_context: RunSourceContext = Field(default_factory=RunSourceContext)
    prompts: PromptRecord = Field(default_factory=PromptRecord)
    inputs: List[ArtifactSource] = Field(default_factory=list)
    outputs: List[ArtifactSource] = Field(default_factory=list)
    options: Dict[str, Any] = Field(default_factory=dict)
    defaults: List[Dict[str, Any]] = Field(default_factory=list)
    provider_trace: ProviderTrace = Field(default_factory=ProviderTrace)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    derivative_settings: ArtifactDerivativeSettings = Field(default_factory=ArtifactDerivativeSettings)
    request_payload: Optional[Dict[str, Any]] = None
    submit_payload: Optional[Dict[str, Any]] = None
    submit_response: Optional[Dict[str, Any]] = None
    final_status_response: Optional[Dict[str, Any]] = None


class RunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    created_at: str
    status: str
    model_key: str
    task_mode: Optional[TaskMode] = None
    hero_original: Optional[str] = None
    hero_output_path: Optional[str] = None
    hero_web: Optional[str] = None
    thumbnail_path: Optional[str] = None
    hero_thumb: Optional[str] = None
    prompt_summary: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    input_count: int = 0
    output_count: int = 0
    has_video: bool = False
    has_image: bool = False
    duration_seconds: Optional[float] = None
    run_folder: Optional[str] = None


class RunIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    created_at: str
    status: str
    model_key: str
    task_mode: Optional[TaskMode] = None
    tags: List[str] = Field(default_factory=list)
    prompt_summary: Optional[str] = None
    hero_original: Optional[str] = None
    hero_output: Optional[str] = None
    hero_web: Optional[str] = None
    hero_thumb: Optional[str] = None
    input_count: int = 0
    output_count: int = 0
    has_video: bool = False
    has_image: bool = False
    duration_seconds: Optional[float] = None
    run_path: Optional[str] = None


class RunArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    created_at: str
    status: str
    model_key: str
    provider_model: Optional[str] = None
    task_mode: Optional[TaskMode] = None
    run_dir: str
    source_metadata: Dict[str, Any] = Field(default_factory=dict)
    source_context: RunSourceContext = Field(default_factory=RunSourceContext)
    prompts: PromptRecord = Field(default_factory=PromptRecord)
    inputs: List[AssetRecord] = Field(default_factory=list)
    outputs: List[AssetRecord] = Field(default_factory=list)
    options: Dict[str, Any] = Field(default_factory=dict)
    defaults: List[Dict[str, Any]] = Field(default_factory=list)
    provider_trace: ProviderTrace = Field(default_factory=ProviderTrace)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    derivative_settings: ArtifactDerivativeSettings = Field(default_factory=ArtifactDerivativeSettings)
    manifest_path: str
    notes_path: str
    request_path: Optional[str] = None
    logs: Dict[str, str] = Field(default_factory=dict)
