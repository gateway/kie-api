"""Public convenience helpers for common package flows."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional, Union

from .clients.credits import CreditsClient
from .clients.download import DownloadClient
from .clients.status import StatusClient
from .clients.submit import SubmitClient
from .clients.upload import UploadClient
from .config import KieSettings
from .enums import JobState, ValidationState
from .artifacts import (
    ArtifactDerivativeSettings,
    RunArtifact,
    RunArtifactCreateRequest,
    RunIndexEntry,
    build_run_manifest,
    append_run_index as append_run_index_file,
    create_run_artifact as write_run_artifact,
    generate_image_derivatives as build_image_derivatives,
    generate_video_derivatives as build_video_derivatives,
    get_latest_assets as query_latest_assets,
    get_latest_successful_run as query_latest_successful_run,
    get_run_by_id as load_run_by_id,
    list_recent_runs as query_recent_runs,
    list_runs_by_model as query_runs_by_model,
    list_runs_by_status as query_runs_by_status,
    list_runs_by_tag as query_runs_by_tag,
    load_run_artifact as load_artifact_from_dir,
    load_run_manifest as load_manifest_from_dir,
    rebuild_run_index as rebuild_index_file,
    write_run_notes as rewrite_notes_for_run,
)
from .models import (
    CreditBalanceResult,
    DownloadResult,
    EstimatedCost,
    NormalizedRequest,
    PreparedRequest,
    PreflightDecision,
    PromptEnhancementResult,
    RawUserRequest,
    ResolvedPromptContext,
    SubmissionResult,
    TaskWaitResult,
    ValidationResult,
)
from .registry.loader import SpecRegistry, load_registry
from .services import (
    PreflightService,
    PricingRegistry,
    PromptEnhancer,
    RequestPreparationService,
)
from .services.normalizer import RequestNormalizer
from .services.validator import RequestValidator


def _resolve_registry(registry: Optional[SpecRegistry] = None) -> SpecRegistry:
    return registry or load_registry()


def normalize_request(
    raw_request: RawUserRequest, registry: Optional[SpecRegistry] = None
) -> NormalizedRequest:
    """Normalize a raw request against the loaded model registry."""

    resolved_registry = _resolve_registry(registry)
    return RequestNormalizer(resolved_registry).normalize(raw_request)


def validate_request(
    request: Union[RawUserRequest, NormalizedRequest],
    registry: Optional[SpecRegistry] = None,
) -> ValidationResult:
    """Validate either a raw or normalized request."""

    resolved_registry = _resolve_registry(registry)
    normalized = (
        normalize_request(request, resolved_registry)
        if isinstance(request, RawUserRequest)
        else request
    )
    return RequestValidator(resolved_registry).validate(normalized)


def build_submission_payload(
    request: Union[RawUserRequest, NormalizedRequest, ValidationResult, PreparedRequest],
    registry: Optional[SpecRegistry] = None,
    settings: Optional[KieSettings] = None,
) -> Dict[str, Any]:
    """Build the outbound KIE payload once a request is submission-ready."""

    resolved_registry = _resolve_registry(registry)
    resolved_settings = settings or KieSettings()
    normalized: Optional[NormalizedRequest]

    if isinstance(request, RawUserRequest):
        validation = validate_request(request, resolved_registry)
        normalized = _require_ready_validation(validation)
    elif isinstance(request, ValidationResult):
        normalized = _require_ready_validation(request)
    elif isinstance(request, PreparedRequest):
        normalized = request.normalized_request
    else:
        normalized = request

    client = SubmitClient(resolved_settings, resolved_registry)
    return client.build_payload(normalized)


def prepare_request_for_submission(
    request: Union[RawUserRequest, NormalizedRequest, ValidationResult],
    registry: Optional[SpecRegistry] = None,
    settings: Optional[KieSettings] = None,
    upload_client: Optional[UploadClient] = None,
) -> PreparedRequest:
    """Normalize, validate, and upload all input media before submission."""

    resolved_registry = _resolve_registry(registry)
    resolved_settings = settings or KieSettings()
    return RequestPreparationService(
        resolved_registry,
        resolved_settings,
        upload_client=upload_client,
    ).prepare(request)


def submit_prepared_request(
    prepared_request: PreparedRequest,
    registry: Optional[SpecRegistry] = None,
    settings: Optional[KieSettings] = None,
) -> SubmissionResult:
    """Submit a request that has already been rewritten to KIE-uploaded media URLs."""

    resolved_registry = _resolve_registry(registry)
    resolved_settings = settings or KieSettings()
    return SubmitClient(resolved_settings, resolved_registry).submit(
        prepared_request.normalized_request
    )


def wait_for_task(
    task_id: str,
    settings: Optional[KieSettings] = None,
    poll_interval_seconds: Optional[float] = None,
    timeout_seconds: Optional[float] = None,
) -> TaskWaitResult:
    """Poll KIE until a task reaches a terminal state or times out."""

    resolved_settings = settings or KieSettings()
    poll_interval = (
        poll_interval_seconds
        if poll_interval_seconds is not None
        else resolved_settings.wait_poll_interval_seconds
    )
    timeout = (
        timeout_seconds
        if timeout_seconds is not None
        else resolved_settings.wait_timeout_seconds
    )
    client = StatusClient(resolved_settings)
    history = []
    start = time.monotonic()

    while True:
        status = client.get_status(task_id)
        history.append(status)
        if status.state in {JobState.SUCCEEDED, JobState.FAILED}:
            return TaskWaitResult(
                task_id=task_id,
                terminal=True,
                timed_out=False,
                final_status=status,
                history=history,
                elapsed_seconds=round(time.monotonic() - start, 3),
            )

        elapsed = time.monotonic() - start
        if elapsed >= timeout:
            return TaskWaitResult(
                task_id=task_id,
                terminal=False,
                timed_out=True,
                final_status=status,
                history=history,
                elapsed_seconds=round(elapsed, 3),
            )
        time.sleep(poll_interval)


def download_output_file(
    source_url: str,
    destination_path: str,
    settings: Optional[KieSettings] = None,
) -> DownloadResult:
    """Download a generated asset from a result URL to a local path."""

    return DownloadClient(settings or KieSettings()).download_to_path(
        source_url,
        destination_path,
    )


def create_run_artifact(
    request: RunArtifactCreateRequest,
    *,
    output_root: str = "outputs",
    append_index: bool = True,
) -> RunArtifact:
    """Create a self-contained run artifact bundle on disk."""

    return write_run_artifact(
        request,
        output_root=output_root,
        append_index=append_index,
    )


def load_run_artifact(run_dir: str) -> RunArtifact:
    """Load a full run artifact from an existing run folder."""

    from pathlib import Path

    return load_artifact_from_dir(Path(run_dir))


def get_run_summary(run_dir: str):
    """Load the per-run manifest summary from an existing run folder."""

    from pathlib import Path

    return load_manifest_from_dir(Path(run_dir))


def generate_image_derivatives(source_path: str, web_path: str, thumb_path: str):
    """Generate web and thumb image derivatives for an existing local image."""

    from pathlib import Path

    return build_image_derivatives(Path(source_path), Path(web_path), Path(thumb_path))


def generate_video_derivatives(source_path: str, web_path: str, poster_path: str):
    """Generate web video and poster derivatives for an existing local video."""

    from pathlib import Path

    return build_video_derivatives(Path(source_path), Path(web_path), Path(poster_path))


def append_run_index(entry: RunIndexEntry, *, output_root: str = "outputs"):
    """Append one run summary to the global artifact index."""

    from pathlib import Path

    return append_run_index_file(Path(output_root), entry)


def rebuild_run_index(*, output_root: str = "outputs"):
    """Rebuild the append-only index from artifact folders on disk."""

    from pathlib import Path

    return rebuild_index_file(Path(output_root))


def list_recent_runs(*, output_root: str = "outputs", limit: int = 10):
    """List recent runs from the global artifact index."""

    from pathlib import Path

    return query_recent_runs(Path(output_root), limit=limit)


def list_runs_by_model(model_key: str, *, output_root: str = "outputs", limit: Optional[int] = None):
    """List indexed runs filtered by model key."""

    from pathlib import Path

    return query_runs_by_model(Path(output_root), model_key, limit=limit)


def list_runs_by_status(status: str, *, output_root: str = "outputs", limit: Optional[int] = None):
    """List indexed runs filtered by status."""

    from pathlib import Path

    return query_runs_by_status(Path(output_root), status, limit=limit)


def list_runs_by_tag(tag: str, *, output_root: str = "outputs", limit: Optional[int] = None):
    """List indexed runs filtered by tag."""

    from pathlib import Path

    return query_runs_by_tag(Path(output_root), tag, limit=limit)


def get_run_by_id(run_id: str, *, output_root: str = "outputs") -> Optional[RunArtifact]:
    """Load a full run artifact by run id."""

    from pathlib import Path

    return load_run_by_id(Path(output_root), run_id)


def get_latest_successful_run(*, output_root: str = "outputs", model_key: Optional[str] = None):
    """Return the most recent successful run summary."""

    from pathlib import Path

    return query_latest_successful_run(Path(output_root), model_key=model_key)


def get_latest_assets(*, output_root: str = "outputs", model_key: Optional[str] = None, status: str = "succeeded"):
    """Return the hero asset paths for the latest matching run."""

    from pathlib import Path

    return query_latest_assets(Path(output_root), model_key=model_key, status=status)


def update_run_notes(run: Optional[RunArtifact] = None, *, run_dir: Optional[str] = None):
    """Regenerate notes.md from an existing run artifact."""

    if run is None and run_dir is None:
        raise ValueError("update_run_notes requires either a RunArtifact or a run_dir path.")
    resolved_run = run or load_run_artifact(run_dir or "")
    return rewrite_notes_for_run(resolved_run, manifest=build_run_manifest(resolved_run))


def dry_run_prompt_enhancement(
    request: Union[RawUserRequest, NormalizedRequest],
    registry: Optional[SpecRegistry] = None,
) -> PromptEnhancementResult:
    """Resolve the default prompt profile and prepare a dry-run enhancement result."""

    resolved_registry = _resolve_registry(registry)
    normalized = (
        normalize_request(request, resolved_registry)
        if isinstance(request, RawUserRequest)
        else request
    )
    return PromptEnhancer(resolved_registry).prepare(normalized)


def resolve_prompt_context(
    request: Union[RawUserRequest, NormalizedRequest],
    registry: Optional[SpecRegistry] = None,
) -> ResolvedPromptContext:
    """Resolve the prompt profile and effective system prompt for wrapper-side enhancement."""

    resolved_registry = _resolve_registry(registry)
    normalized = (
        normalize_request(request, resolved_registry)
        if isinstance(request, RawUserRequest)
        else request
    )
    return PromptEnhancer(resolved_registry).resolve_context(normalized)


def apply_enhanced_prompt(
    request: NormalizedRequest,
    final_prompt: str,
    *,
    enhanced_prompt: Optional[str] = None,
) -> NormalizedRequest:
    """Return a request copy that will submit the provided final prompt."""

    resolved_enhanced = enhanced_prompt if enhanced_prompt is not None else final_prompt
    return request.model_copy(
        update={
            "prompt": final_prompt,
            "enhanced_prompt": resolved_enhanced,
            "final_prompt_used": final_prompt,
        }
    )


def estimate_request_cost(
    request: Union[RawUserRequest, NormalizedRequest],
    registry: Optional[SpecRegistry] = None,
    pricing_registry: Optional[PricingRegistry] = None,
) -> EstimatedCost:
    """Estimate cost from the active pricing snapshot without submitting anything."""

    resolved_registry = _resolve_registry(registry)
    normalized = (
        normalize_request(request, resolved_registry)
        if isinstance(request, RawUserRequest)
        else request
    )
    resolved_pricing = pricing_registry or PricingRegistry()
    return resolved_pricing.estimate_request(normalized)


def get_credit_balance(settings: Optional[KieSettings] = None) -> CreditBalanceResult:
    """Query remaining KIE credits using the configured API key."""

    return CreditsClient(settings or KieSettings()).get_balance()


def run_preflight(
    request: Union[RawUserRequest, NormalizedRequest, ValidationResult],
    registry: Optional[SpecRegistry] = None,
    pricing_registry: Optional[PricingRegistry] = None,
    settings: Optional[KieSettings] = None,
    confirmation_granted: bool = False,
    remaining_credits: Optional[float] = None,
) -> PreflightDecision:
    """Estimate cost and return a preflight decision without calling KIE."""

    resolved_registry = _resolve_registry(registry)
    normalized: Optional[NormalizedRequest]

    if isinstance(request, RawUserRequest):
        validation = validate_request(request, resolved_registry)
        normalized = _require_ready_validation(validation)
    elif isinstance(request, ValidationResult):
        normalized = _require_ready_validation(request)
    else:
        normalized = request

    return PreflightService(
        pricing_registry=pricing_registry or PricingRegistry(),
        settings=settings or KieSettings(),
    ).evaluate(
        normalized,
        remaining_credits=remaining_credits,
        confirmation_granted=confirmation_granted,
    )


def _require_ready_validation(validation: ValidationResult) -> NormalizedRequest:
    ready_states = {
        ValidationState.READY,
        ValidationState.READY_WITH_DEFAULTS,
        ValidationState.READY_WITH_WARNING,
    }
    if validation.state not in ready_states or validation.normalized_request is None:
        raise ValueError(
            "build_submission_payload requires a request in a ready state; "
            f"received {validation.state}."
        )
    return validation.normalized_request
