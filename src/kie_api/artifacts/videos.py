"""Video derivative helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List

from .inspect import ffmpeg_available, video_metadata
from .models import DerivedAssetRecord
from ..exceptions import ArtifactProcessingError


def generate_video_derivatives(
    source_path: Path,
    web_path: Path,
    poster_path: Path,
    *,
    web_max_width: int = 1280,
    poster_max_width: int = 640,
    poster_format: str = "jpg",
    enable_sha256: bool = True,
) -> tuple[DerivedAssetRecord, DerivedAssetRecord]:
    if not ffmpeg_available():
        raise ArtifactProcessingError("ffmpeg and ffprobe are required for video derivatives")
    source = Path(source_path)
    web_path.parent.mkdir(parents=True, exist_ok=True)
    poster_path.parent.mkdir(parents=True, exist_ok=True)

    _run_ffmpeg(build_web_video_command(source, web_path, max_width=web_max_width))
    _run_ffmpeg(
        build_poster_command(
            source,
            poster_path.with_suffix(f".{poster_format.lstrip('.')}"),
            max_width=poster_max_width,
        )
    )
    poster_resolved_path = poster_path.with_suffix(f".{poster_format.lstrip('.')}")

    return (
        _derived_video_record("web", web_path, include_sha256=enable_sha256),
        _derived_video_record("poster", poster_resolved_path, include_sha256=enable_sha256),
    )


def build_web_video_command(source_path: Path, destination_path: Path, *, max_width: int = 1280) -> List[str]:
    scale_filter = f"scale=w='if(gt(iw,{max_width}),{max_width},iw)':h=-2"
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(source_path),
        "-vf",
        scale_filter,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        str(destination_path),
    ]


def build_poster_command(source_path: Path, destination_path: Path, *, max_width: int = 640) -> List[str]:
    scale_filter = f"scale=w='if(gt(iw,{max_width}),{max_width},iw)':h=-2"
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        "00:00:00.000",
        "-i",
        str(source_path),
        "-frames:v",
        "1",
        "-vf",
        scale_filter,
    ]
    if destination_path.suffix.lower() == ".webp":
        command.extend(["-c:v", "libwebp", "-quality", "80"])
    elif destination_path.suffix.lower() in {".jpg", ".jpeg"}:
        command.extend(["-c:v", "mjpeg", "-q:v", "2"])
    command.append(str(destination_path))
    return command


def _run_ffmpeg(command: List[str]) -> None:
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:  # pragma: no cover - defensive
        raise ArtifactProcessingError(f"ffmpeg failed: {exc.stderr}") from exc


def _derived_video_record(kind: str, path: Path, *, include_sha256: bool) -> DerivedAssetRecord:
    metadata = (
        video_metadata(path, include_sha256=include_sha256)
        if path.suffix.lower() == ".mp4"
        else _image_like_poster_metadata(path, include_sha256=include_sha256)
    )
    return DerivedAssetRecord(
        kind=kind,
        relative_path=str(path),
        mime_type=metadata.get("mime_type"),
        width=metadata.get("width"),
        height=metadata.get("height"),
        duration_seconds=metadata.get("duration_seconds"),
        bytes=metadata.get("bytes"),
        sha256=metadata.get("sha256"),
        codec_name=metadata.get("codec_name"),
    )


def _image_like_poster_metadata(path: Path, *, include_sha256: bool) -> dict:
    from .inspect import image_metadata

    return image_metadata(path, include_sha256=include_sha256)
