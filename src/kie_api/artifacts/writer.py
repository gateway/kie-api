"""Run artifact bundle creation helpers."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

from .images import generate_image_derivatives
from .index import append_run_index
from .inspect import detect_mime_type, image_metadata, sha256_file, video_metadata
from .models import (
    ArtifactSource,
    AssetRecord,
    ArtifactDerivativeSettings,
    PromptRecord,
    ProviderTrace,
    RunArtifact,
    RunArtifactCreateRequest,
    RunIndexEntry,
    RunManifest,
)
from .paths import coerce_created_at, create_run_artifact_paths


def create_run_artifact(
    request: RunArtifactCreateRequest,
    *,
    output_root: Union[Path, str] = "outputs",
    append_index: bool = True,
) -> RunArtifact:
    created_at_dt = coerce_created_at(request.created_at)
    run_id, resolved_created_at, paths = create_run_artifact_paths(
        Path(output_root),
        request.model_key,
        slug=request.slug,
        created_at=created_at_dt,
    )
    created_at = resolved_created_at.isoformat()
    inputs = _copy_inputs(
        request.inputs,
        paths.run_dir,
        paths.inputs_dir,
        derivative_settings=request.derivative_settings,
    )
    outputs = _copy_outputs(
        request.outputs,
        paths.run_dir,
        paths.original_dir,
        paths.web_dir,
        paths.thumb_dir,
        derivative_settings=request.derivative_settings,
    )
    prompt_record = _write_prompts(paths.run_dir, paths.prompt_txt, paths.prompt_enhanced_txt, request.prompts)
    request_path = _write_optional_json(paths.run_dir, paths.request_json, request.request_payload)
    provider_trace, log_paths = _write_provider_trace(paths.run_dir, paths.logs_dir, request.provider_trace, request)

    run = RunArtifact(
        run_id=run_id,
        created_at=created_at,
        status=request.status,
        model_key=request.model_key,
        provider_model=request.provider_model,
        task_mode=request.task_mode,
        run_dir=str(paths.run_dir),
        source_metadata=request.source_metadata,
        source_context=request.source_context,
        prompts=prompt_record,
        inputs=inputs,
        outputs=outputs,
        options=request.options,
        defaults=request.defaults,
        provider_trace=provider_trace,
        warnings=request.warnings,
        errors=request.errors,
        tags=request.tags,
        notes=request.notes,
        derivative_settings=request.derivative_settings,
        manifest_path=str(paths.manifest_json.relative_to(paths.run_dir)),
        notes_path=str(paths.notes_md.relative_to(paths.run_dir)),
        request_path=request_path,
        logs=log_paths,
    )
    manifest = build_run_manifest(run)
    _write_json(paths.run_json, run.model_dump())
    _write_json(paths.manifest_json, manifest.model_dump())
    write_run_notes(run, manifest=manifest)

    if append_index:
        append_run_index(paths.root_dir, build_run_index_entry(run, manifest))
    return run


def build_run_manifest(run: RunArtifact) -> RunManifest:
    hero_output = run.outputs[0] if run.outputs else None
    prompt_summary = _summarize_prompt(run.prompts.final_used or run.prompts.raw)
    thumbnail_path = None
    hero_output_path = None
    hero_original = None
    hero_web = None
    duration_seconds = None
    if hero_output:
        hero_original = hero_output.relative_path
        hero_web = hero_output.web_path or hero_output.relative_path
        hero_output_path = hero_web
        thumbnail_path = hero_output.thumb_path or hero_output.poster_path or hero_output.web_path
        duration_seconds = hero_output.duration_seconds
    run_dir = Path(run.run_dir)
    root_dir = run_dir.parent.parent
    return RunManifest(
        run_id=run.run_id,
        created_at=run.created_at,
        status=run.status,
        model_key=run.model_key,
        task_mode=run.task_mode,
        hero_original=hero_original,
        hero_output_path=hero_output_path,
        hero_web=hero_web,
        thumbnail_path=thumbnail_path,
        hero_thumb=thumbnail_path,
        prompt_summary=prompt_summary,
        tags=run.tags,
        input_count=len(run.inputs),
        output_count=len(run.outputs),
        has_video=any(asset.kind == "video" for asset in run.outputs),
        has_image=any(asset.kind == "image" for asset in run.outputs),
        duration_seconds=duration_seconds,
        run_folder=str(run_dir.relative_to(root_dir)),
    )


def build_run_index_entry(run: RunArtifact, manifest: Optional[RunManifest] = None) -> RunIndexEntry:
    resolved_manifest = manifest or build_run_manifest(run)
    run_dir = Path(run.run_dir)
    root_dir = run_dir.parent.parent
    return RunIndexEntry(
        run_id=run.run_id,
        created_at=run.created_at,
        status=run.status,
        model_key=run.model_key,
        task_mode=run.task_mode,
        tags=resolved_manifest.tags,
        prompt_summary=resolved_manifest.prompt_summary,
        hero_original=resolved_manifest.hero_original,
        hero_output=resolved_manifest.hero_output_path,
        hero_web=resolved_manifest.hero_web,
        hero_thumb=resolved_manifest.hero_thumb,
        input_count=resolved_manifest.input_count,
        output_count=resolved_manifest.output_count,
        has_video=resolved_manifest.has_video,
        has_image=resolved_manifest.has_image,
        duration_seconds=resolved_manifest.duration_seconds,
        run_path=resolved_manifest.run_folder or str(run_dir.relative_to(root_dir)),
    )


def _copy_inputs(
    sources: Iterable[ArtifactSource],
    run_dir: Path,
    inputs_dir: Path,
    *,
    derivative_settings: ArtifactDerivativeSettings,
) -> List[AssetRecord]:
    records: List[AssetRecord] = []
    counters: Dict[str, int] = {}
    for source in sources:
        prefix = _input_prefix(source.role, source.kind)
        counter = counters.get(prefix, 0) + 1
        counters[prefix] = counter
        source_path = Path(source.source_path)
        destination = inputs_dir / f"{prefix}_{counter:02d}{source_path.suffix.lower()}"
        shutil.copy2(source_path, destination)
        records.append(
            _asset_record(
                kind=source.kind,
                role=source.role,
                run_dir=run_dir,
                path=destination,
                original_filename=source.original_filename or source_path.name,
                source_path=str(source_path),
                source_url=source.source_url,
                metadata=source.metadata,
                enable_sha256=derivative_settings.enable_sha256,
            )
        )
    return records


def _copy_outputs(
    sources: Iterable[ArtifactSource],
    run_dir: Path,
    original_dir: Path,
    web_dir: Path,
    thumb_dir: Path,
    *,
    derivative_settings: ArtifactDerivativeSettings,
) -> List[AssetRecord]:
    records: List[AssetRecord] = []
    for index, source in enumerate(sources, start=1):
        source_path = Path(source.source_path)
        destination = original_dir / f"output_{index:02d}{source_path.suffix.lower()}"
        shutil.copy2(source_path, destination)
        record = _asset_record(
            kind=source.kind,
            role=source.role,
            run_dir=run_dir,
            path=destination,
            original_filename=source.original_filename or source_path.name,
            source_path=str(source_path),
            source_url=source.source_url,
            metadata=source.metadata,
            enable_sha256=derivative_settings.enable_sha256,
        )
        if source.kind == "image":
            web_path = web_dir / f"output_{index:02d}.{derivative_settings.image_web_format.lstrip('.')}"
            thumb_path = thumb_dir / f"output_{index:02d}.{derivative_settings.image_thumb_format.lstrip('.')}"
            web_record, thumb_record = generate_image_derivatives(
                destination,
                web_path,
                thumb_path,
                web_max_dimension=derivative_settings.image_web_max_dimension,
                web_format=derivative_settings.image_web_format,
                web_quality=derivative_settings.image_web_quality,
                thumb_max_dimension=derivative_settings.image_thumb_max_dimension,
                thumb_format=derivative_settings.image_thumb_format,
                thumb_quality=derivative_settings.image_thumb_quality,
                allow_upscale=derivative_settings.allow_upscale,
                enable_sha256=derivative_settings.enable_sha256,
            )
            record.web_path = _relative(run_dir, web_path)
            record.thumb_path = _relative(run_dir, thumb_path)
            record.bytes_web = web_record.bytes
            record.bytes_thumb = thumb_record.bytes
            record.derivatives = [
                _rebase_derived(run_dir, web_record, web_path),
                _rebase_derived(run_dir, thumb_record, thumb_path),
            ]
        elif source.kind == "video":
            from .videos import generate_video_derivatives

            web_path = web_dir / f"output_{index:02d}.mp4"
            poster_path = thumb_dir / f"output_{index:02d}_poster.{derivative_settings.video_poster_format.lstrip('.')}"
            web_record, poster_record = generate_video_derivatives(
                destination,
                web_path,
                poster_path,
                web_max_width=derivative_settings.video_web_max_width,
                poster_max_width=derivative_settings.video_poster_width,
                poster_format=derivative_settings.video_poster_format,
                enable_sha256=derivative_settings.enable_sha256,
            )
            record.web_path = _relative(run_dir, web_path)
            record.poster_path = poster_record.relative_path
            record.bytes_web = web_record.bytes
            record.bytes_poster = poster_record.bytes
            record.derivatives = [
                _rebase_derived(run_dir, web_record, web_path),
                poster_record,
            ]
        records.append(record)
    return records


def _write_prompts(run_dir: Path, raw_path: Path, enhanced_path: Path, prompts: PromptRecord) -> PromptRecord:
    record = prompts.model_copy(deep=True)
    if record.raw:
        raw_path.write_text(record.raw, encoding="utf-8")
        record.raw_path = _relative(run_dir, raw_path)
    if record.enhanced:
        enhanced_path.write_text(record.enhanced, encoding="utf-8")
        record.enhanced_path = _relative(run_dir, enhanced_path)
    return record


def _write_provider_trace(
    run_dir: Path,
    logs_dir: Path,
    trace: ProviderTrace,
    request: RunArtifactCreateRequest,
) -> tuple[ProviderTrace, Dict[str, str]]:
    record = trace.model_copy(deep=True)
    logs: Dict[str, str] = {}

    for filename, payload, attr_name in (
        ("submit_payload.json", request.submit_payload, "submit_payload_path"),
        ("submit_response.json", request.submit_response, "submit_response_path"),
        ("status_response_final.json", request.final_status_response, "final_status_path"),
    ):
        if payload is None:
            continue
        path = logs_dir / filename
        _write_json(path, payload)
        relative = _relative(run_dir, path)
        setattr(record, attr_name, relative)
        logs[filename] = relative

    if request.request_payload is not None and not record.request_path:
        record.request_path = _relative(run_dir, run_dir / "request.json")
    return record, logs


def _asset_record(
    *,
    kind: str,
    role: str,
    run_dir: Path,
    path: Path,
    original_filename: Optional[str],
    source_path: Optional[str],
    source_url: Optional[str],
    metadata: Dict[str, Any],
    enable_sha256: bool,
) -> AssetRecord:
    extracted = (
        image_metadata(path, include_sha256=enable_sha256)
        if kind == "image"
        else video_metadata(path, include_sha256=enable_sha256)
        if kind == "video"
        else {
        "mime_type": detect_mime_type(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path) if enable_sha256 else None,
        "width": None,
        "height": None,
        "duration_seconds": None,
        "codec_name": None,
    })
    return AssetRecord(
        kind=kind,
        role=role,
        relative_path=_relative(run_dir, path),
        original_path=_relative(run_dir, path),
        original_filename=original_filename,
        source_path=source_path,
        source_url=source_url,
        mime_type=extracted.get("mime_type"),
        width=extracted.get("width"),
        height=extracted.get("height"),
        duration_seconds=extracted.get("duration_seconds"),
        bytes=extracted.get("bytes"),
        bytes_original=extracted.get("bytes"),
        sha256=extracted.get("sha256"),
        codec_name=extracted.get("codec_name"),
        metadata=metadata,
    )


def _write_optional_json(run_dir: Path, path: Path, payload: Optional[Dict[str, Any]]) -> Optional[str]:
    if payload is None:
        return None
    _write_json(path, payload)
    return _relative(run_dir, path)


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_run_notes(run: RunArtifact, *, manifest: Optional[RunManifest] = None) -> Path:
    path = Path(run.run_dir) / run.notes_path
    resolved_manifest = manifest or build_run_manifest(run)
    lines = [
        f"# {run.run_id}",
        "",
        f"- Status: `{run.status}`",
        f"- Model: `{run.model_key}`",
        f"- Created: `{run.created_at}`",
        f"- Task mode: `{run.task_mode}`" if run.task_mode else "- Task mode: unknown",
        f"- Task ID: `{run.provider_trace.task_id}`" if run.provider_trace.task_id else "- Task ID: not available",
        f"- Outputs: `{resolved_manifest.output_count}`",
    ]
    if run.source_context.project_name:
        lines.append(f"- Project: `{run.source_context.project_name}`")
    if run.source_context.source_user:
        lines.append(f"- Source user: `{run.source_context.source_user}`")
    if run.source_context.source_channel:
        lines.append(f"- Source channel: `{run.source_context.source_channel}`")
    if run.tags:
        lines.append(f"- Tags: {', '.join(run.tags)}")
    if resolved_manifest.prompt_summary:
        lines.extend(["", "## Prompt", "", resolved_manifest.prompt_summary])
    if run.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in run.warnings)
    if run.errors:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {error}" for error in run.errors)
    extra_notes = run.notes or run.source_context.notes
    if extra_notes:
        lines.extend(["", "## Notes", "", extra_notes.strip()])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def _relative(run_dir: Path, path: Path) -> str:
    return str(path.relative_to(run_dir))


def _rebase_derived(run_dir: Path, record, path: Path):
    return record.model_copy(update={"relative_path": _relative(run_dir, path)})


def _input_prefix(role: str, kind: str) -> str:
    normalized_role = role.lower()
    if "motion" in normalized_role:
        return "motion"
    if "audio" in normalized_role or kind == "audio":
        return "audio"
    if "video" in normalized_role or kind == "video":
        return "video"
    if "ref" in normalized_role or "reference" in normalized_role or kind == "image":
        return "ref"
    return "input"


def _summarize_prompt(prompt: Optional[str], *, max_chars: int = 140) -> Optional[str]:
    if not prompt:
        return None
    clean = " ".join(prompt.split())
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 3].rstrip() + "..."
