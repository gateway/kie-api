"""Append-only run index and query helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Optional

from .models import RunArtifact, RunIndexEntry, RunManifest


def append_run_index(output_root: Path, entry: RunIndexEntry) -> Path:
    index_path = Path(output_root) / "index.jsonl"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    existing = {item.run_id for item in load_run_index(output_root)}
    if entry.run_id in existing:
        return index_path
    with index_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry.model_dump(), ensure_ascii=True))
        handle.write("\n")
    return index_path


def load_run_index(output_root: Path) -> List[RunIndexEntry]:
    index_path = Path(output_root) / "index.jsonl"
    if not index_path.exists():
        return []
    entries: List[RunIndexEntry] = []
    with index_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            entries.append(RunIndexEntry.model_validate(json.loads(line)))
    return entries


def list_recent_runs(output_root: Path, *, limit: int = 10) -> List[RunIndexEntry]:
    entries = sorted(load_run_index(output_root), key=lambda item: item.created_at, reverse=True)
    return entries[:limit]


def list_runs_by_model(output_root: Path, model_key: str, *, limit: Optional[int] = None) -> List[RunIndexEntry]:
    entries = [entry for entry in load_run_index(output_root) if entry.model_key == model_key]
    entries.sort(key=lambda item: item.created_at, reverse=True)
    return entries[:limit] if limit is not None else entries


def list_runs_by_status(output_root: Path, status: str, *, limit: Optional[int] = None) -> List[RunIndexEntry]:
    entries = [entry for entry in load_run_index(output_root) if entry.status == status]
    entries.sort(key=lambda item: item.created_at, reverse=True)
    return entries[:limit] if limit is not None else entries


def list_runs_by_tag(output_root: Path, tag: str, *, limit: Optional[int] = None) -> List[RunIndexEntry]:
    entries = [entry for entry in load_run_index(output_root) if tag in entry.tags]
    entries.sort(key=lambda item: item.created_at, reverse=True)
    return entries[:limit] if limit is not None else entries


def get_run_by_id(output_root: Path, run_id: str) -> Optional[RunArtifact]:
    for run_dir in scan_run_artifacts(output_root):
        if run_dir.name == run_id:
            return load_run_artifact(run_dir)
    return None


def get_latest_successful_run(output_root: Path, *, model_key: Optional[str] = None) -> Optional[RunIndexEntry]:
    entries = list_runs_by_status(output_root, "succeeded")
    if model_key is not None:
        entries = [entry for entry in entries if entry.model_key == model_key]
    return entries[0] if entries else None


def get_latest_assets(output_root: Path, *, model_key: Optional[str] = None, status: str = "succeeded") -> dict:
    entries = list_runs_by_status(output_root, status)
    if model_key is not None:
        entries = [entry for entry in entries if entry.model_key == model_key]
    if not entries:
        return {}
    hero = entries[0]
    return {
        "run_id": hero.run_id,
        "hero_original": hero.hero_original,
        "hero_web": hero.hero_web or hero.hero_output,
        "hero_thumb": hero.hero_thumb,
        "run_path": hero.run_path,
    }


def load_run_artifact(run_dir: Path) -> RunArtifact:
    payload = json.loads((Path(run_dir) / "run.json").read_text(encoding="utf-8"))
    return RunArtifact.model_validate(payload)


def load_run_manifest(run_dir: Path) -> RunManifest:
    payload = json.loads((Path(run_dir) / "manifest.json").read_text(encoding="utf-8"))
    return RunManifest.model_validate(payload)


def scan_run_artifacts(output_root: Path) -> List[Path]:
    root = Path(output_root)
    if not root.exists():
        return []
    run_dirs: List[Path] = []
    for day_dir in sorted([path for path in root.iterdir() if path.is_dir()]):
        for run_dir in sorted([path for path in day_dir.iterdir() if path.is_dir()]):
            if (run_dir / "run.json").exists() and (run_dir / "manifest.json").exists():
                run_dirs.append(run_dir)
    return run_dirs


def rebuild_run_index(output_root: Path) -> Path:
    from .writer import build_run_index_entry

    root = Path(output_root)
    index_path = root / "index.jsonl"
    entries: List[RunIndexEntry] = []
    for run_dir in scan_run_artifacts(root):
        run = load_run_artifact(run_dir)
        manifest = load_run_manifest(run_dir)
        entries.append(build_run_index_entry(run, manifest))
    entries.sort(key=lambda item: item.created_at)
    with index_path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry.model_dump(), ensure_ascii=True))
            handle.write("\n")
    return index_path
