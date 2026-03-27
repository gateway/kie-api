"""Reusable asset inspection helpers."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image

from ..exceptions import ArtifactProcessingError


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect_mime_type(path: Path) -> Optional[str]:
    mime_type, _ = mimetypes.guess_type(path.name)
    return mime_type


def image_metadata(path: Path, *, include_sha256: bool = True) -> Dict[str, Any]:
    with Image.open(path) as image:
        width, height = image.size
        format_name = image.format
    return {
        "width": width,
        "height": height,
        "mime_type": detect_mime_type(path) or _mime_from_pillow_format(format_name),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path) if include_sha256 else None,
    }


def video_metadata(path: Path, *, include_sha256: bool = True) -> Dict[str, Any]:
    _require_binary("ffprobe")
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover - defensive
        raise ArtifactProcessingError(f"ffprobe failed for {path}: {exc.stderr}") from exc

    payload = json.loads(result.stdout)
    streams = payload.get("streams") or []
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), {})
    format_payload = payload.get("format") or {}
    duration = _coerce_float(video_stream.get("duration") or format_payload.get("duration"))
    width = _coerce_int(video_stream.get("width"))
    height = _coerce_int(video_stream.get("height"))
    return {
        "duration_seconds": duration,
        "width": width,
        "height": height,
        "codec_name": video_stream.get("codec_name"),
        "mime_type": detect_mime_type(path) or "video/mp4",
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path) if include_sha256 else None,
    }


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _require_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise ArtifactProcessingError(f"{name} is required for video derivative generation")


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _mime_from_pillow_format(format_name: Optional[str]) -> Optional[str]:
    if not format_name:
        return None
    normalized = format_name.lower()
    if normalized == "jpeg":
        return "image/jpeg"
    return f"image/{normalized}"
