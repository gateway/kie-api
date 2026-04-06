"""Append-only run index and query helpers."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import IO, Iterable, Iterator, List, Optional

from pydantic import ValidationError
from .models import RunArtifact, RunIndexEntry, RunManifest

try:  # pragma: no cover - Windows fallback
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None


def append_run_index(output_root: Path, entry: RunIndexEntry) -> Path:
    index_path = _index_path(output_root)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("a+", encoding="utf-8") as handle:
        with _locked_file(handle):
            # Re-read while holding the file lock so concurrent writers do not append duplicates.
            handle.seek(0)
            existing = {
                item.run_id
                for item in _parse_index_lines(handle.readlines(), strict=False)
            }
            if entry.run_id in existing:
                return index_path
            handle.seek(0, os.SEEK_END)
            handle.write(json.dumps(entry.model_dump(), ensure_ascii=True))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    return index_path


def load_run_index(output_root: Path) -> List[RunIndexEntry]:
    index_path = _index_path(output_root)
    if not index_path.exists():
        return []
    with index_path.open("r", encoding="utf-8") as handle:
        return _parse_index_lines(handle.readlines(), strict=False)


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
    for entry in load_run_index(output_root):
        if entry.run_id != run_id or not entry.run_path:
            continue
        run_dir = Path(output_root) / entry.run_path
        if run_dir.exists():
            return load_run_artifact(run_dir)
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
    index_path = _index_path(root)
    entries: List[RunIndexEntry] = []
    for run_dir in scan_run_artifacts(root):
        run = load_run_artifact(run_dir)
        manifest = load_run_manifest(run_dir)
        entries.append(build_run_index_entry(run, manifest))
    entries.sort(key=lambda item: item.created_at)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=index_path.parent, delete=False) as handle:
        temp_path = Path(handle.name)
        for entry in entries:
            handle.write(json.dumps(entry.model_dump(), ensure_ascii=True))
            handle.write("\n")
    os.replace(temp_path, index_path)
    return index_path


def _index_path(output_root: Path) -> Path:
    return Path(output_root) / "index.jsonl"


def _parse_index_lines(lines: Iterable[str], *, strict: bool) -> List[RunIndexEntry]:
    entries: List[RunIndexEntry] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(RunIndexEntry.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValidationError):
            if strict:
                raise
    return entries


@contextmanager
def _locked_file(handle: IO[str]) -> Iterator[None]:
    if fcntl is None:  # pragma: no cover - Windows fallback
        yield
        return
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    try:
        yield
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
