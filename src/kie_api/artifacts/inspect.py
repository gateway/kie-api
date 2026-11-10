"""Reusable asset inspection helpers."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterator, Optional
from xml.parsers import expat

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


MAX_ANIMATION_FRAMES = 256
MAX_ANIMATION_PIXELS = 64_000_000


def image_metadata(
    path: Path, *, include_sha256: bool = True, include_animation: bool = True,
) -> Dict[str, Any]:
    width = height = None
    mime_type = None
    duration = None
    metadata = {}
    try:
        with Image.open(path) as image:
            width, height = image.size
            mime_type = Image.MIME.get(image.format) or _mime_from_pillow_format(image.format)
            if include_animation:
                metadata, duration = _read_animation_metadata(image)
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        if _has_svg_root(path):
            mime_type = "image/svg+xml"
    return {
        "width": width,
        "height": height,
        "mime_type": mime_type,
        "duration_seconds": duration,
        "metadata": metadata,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path) if include_sha256 else None,
    }


def animation_frames(image: Image.Image) -> Iterator[Image.Image]:
    """Read at most the supported frame and canvas pixel budgets."""
    index = 1 if image.format == "PNG" and image.info.get("default_image") else 0
    pixels = 0
    for count in range(1, MAX_ANIMATION_FRAMES + 2):
        try:
            image.seek(index)
        except EOFError:
            return
        pixels += image.width * image.height
        if count > MAX_ANIMATION_FRAMES or pixels > MAX_ANIMATION_PIXELS:
            raise ArtifactProcessingError("Animation exceeds the frame or canvas pixel budget.")
        yield image
        index += 1


def animation_loop_count(image: Image.Image) -> int | None:
    """Return total plays, with zero representing an infinite loop."""
    loop = image.info.get("loop")
    if image.format == "GIF":
        # GIF stores additional repeats. WebP and APNG store total plays.
        return 1 if loop is None else loop + 1 if loop else 0
    return loop


def _read_animation_metadata(image: Image.Image) -> tuple[dict[str, Any], float | None]:
    if image.format not in {"GIF", "WEBP", "PNG", "JPEG"}:
        return {}, None
    metadata: dict[str, Any] = {}
    try:
        if not getattr(image, "is_animated", False):
            return {"is_animated": False, "frame_count": 1}, None
        metadata["is_animated"] = True
        loop_count = animation_loop_count(image)
        if loop_count is not None:
            metadata["loop_count"] = loop_count
        delays = []
        for frame in animation_frames(image):
            frame.load()
            delays.append(frame.info.get("duration"))
    except (ArtifactProcessingError, OSError, ValueError, SyntaxError, EOFError, Image.DecompressionBombError):
        metadata["animation_metadata_incomplete"] = True
        return metadata, None
    metadata["frame_count"] = len(delays)
    duration = sum(delays) / 1000 if all(delay is not None for delay in delays) else None
    return metadata, duration


class _RootFound(Exception):
    pass


def _has_svg_root(path: Path) -> bool:
    """Identify an SVG root without rendering, loading DTDs, or parsing its contents."""
    is_svg = False
    parser = expat.ParserCreate(namespace_separator=" ")
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    parser.ExternalEntityRefHandler = lambda *_: 0

    def identify_root(name: str, _attrs: dict) -> None:
        nonlocal is_svg
        is_svg = name in {"http://www.w3.org/2000/svg svg", "svg"}
        raise _RootFound

    parser.StartElementHandler = identify_root
    # Classify from a bounded header without resolving entities or external resources.
    def reject_entity(*_args) -> None:
        raise _RootFound

    parser.EntityDeclHandler = reject_entity
    try:
        with path.open("rb") as handle:
            parser.Parse(handle.read(64 * 1024), False)
    except (_RootFound, expat.ExpatError):
        pass
    return is_svg


def video_metadata(path: Path, *, include_sha256: bool = True) -> Dict[str, Any]:
    ffprobe = ffprobe_path()
    if ffprobe is None:
        return {
            "duration_seconds": None,
            "width": None,
            "height": None,
            "codec_name": None,
            "mime_type": detect_mime_type(path) or "video/mp4",
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path) if include_sha256 else None,
        }
    command = [
        ffprobe,
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
    return ffmpeg_path() is not None


def ffmpeg_path() -> Optional[str]:
    system_binary = shutil.which("ffmpeg")
    if system_binary:
        return system_binary
    try:
        import imageio_ffmpeg
    except Exception:  # pragma: no cover - optional dependency import guard
        return None
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # pragma: no cover - defensive for broken installs
        return None


def ffprobe_path() -> Optional[str]:
    return shutil.which("ffprobe")


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
