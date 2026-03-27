"""Filesystem path helpers for run artifacts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def slugify(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return normalized or None


def build_run_id(created_at: datetime, model_key: str, slug: Optional[str] = None) -> str:
    base = created_at.strftime("%Y%m%d_%H%M%S")
    safe_model_key = slugify(model_key) or "run"
    safe_slug = slugify(slug)
    parts = [base, safe_model_key]
    if safe_slug:
        parts.append(safe_slug)
    return "_".join(parts)


def coerce_created_at(value: Optional[str] = None) -> datetime:
    if value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class RunArtifactPaths:
    root_dir: Path
    day_dir: Path
    run_dir: Path
    inputs_dir: Path
    original_dir: Path
    web_dir: Path
    thumb_dir: Path
    logs_dir: Path
    run_json: Path
    manifest_json: Path
    notes_md: Path
    request_json: Path
    prompt_txt: Path
    prompt_enhanced_txt: Path


def create_run_artifact_paths(
    output_root: Path,
    model_key: str,
    *,
    slug: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> tuple[str, datetime, RunArtifactPaths]:
    resolved_root = Path(output_root)
    resolved_created_at = created_at or datetime.now(timezone.utc)
    run_id = build_run_id(resolved_created_at, model_key, slug=slug)
    day_dir = resolved_root / resolved_created_at.strftime("%Y-%m-%d")
    run_dir = day_dir / run_id
    paths = RunArtifactPaths(
        root_dir=resolved_root,
        day_dir=day_dir,
        run_dir=run_dir,
        inputs_dir=run_dir / "inputs",
        original_dir=run_dir / "original",
        web_dir=run_dir / "web",
        thumb_dir=run_dir / "thumb",
        logs_dir=run_dir / "logs",
        run_json=run_dir / "run.json",
        manifest_json=run_dir / "manifest.json",
        notes_md=run_dir / "notes.md",
        request_json=run_dir / "request.json",
        prompt_txt=run_dir / "prompt.txt",
        prompt_enhanced_txt=run_dir / "prompt_enhanced.txt",
    )
    paths.day_dir.mkdir(parents=True, exist_ok=True)
    paths.run_dir.mkdir(parents=True, exist_ok=False)
    for directory in (
        paths.inputs_dir,
        paths.original_dir,
        paths.web_dir,
        paths.thumb_dir,
        paths.logs_dir,
    ):
        directory.mkdir(parents=True, exist_ok=False)
    return run_id, resolved_created_at, paths
