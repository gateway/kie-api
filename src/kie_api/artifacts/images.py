"""Image derivative helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

from PIL import Image, ImageOps

from ..exceptions import ArtifactProcessingError

from .inspect import animation_frames, animation_loop_count, image_metadata
from .models import DerivedAssetRecord


def generate_image_derivatives(
    source_path: Path,
    web_path: Path,
    thumb_path: Path,
    *,
    web_max_dimension: int = 1600,
    web_format: str = "webp",
    web_quality: int = 82,
    thumb_max_dimension: int = 384,
    thumb_format: str = "webp",
    thumb_quality: int = 76,
    allow_upscale: bool = False,
    enable_sha256: bool = True,
) -> tuple[DerivedAssetRecord, DerivedAssetRecord]:
    source = Path(source_path)
    try:
        with Image.open(source) as image:
            animated_gif = image.format == "GIF" and image.is_animated
            _save_preview(
                image, web_path, max_dimension=web_max_dimension, output_format=web_format,
                quality=web_quality, allow_upscale=allow_upscale, animate=animated_gif,
            )
            image.seek(0)
            _save_preview(
                image, thumb_path, max_dimension=thumb_max_dimension, output_format=thumb_format,
                quality=thumb_quality, allow_upscale=allow_upscale,
            )
        return (
            _derived_record("web", web_path, include_sha256=enable_sha256),
            _derived_record("thumb", thumb_path, include_sha256=enable_sha256),
        )
    except (OSError, ValueError, SyntaxError, KeyError, EOFError, Image.DecompressionBombError) as exc:
        raise ArtifactProcessingError("Image preview could not be generated.") from exc


def _save_preview(
    image: Image.Image,
    destination_path: Path,
    *,
    max_dimension: int,
    output_format: str,
    quality: int,
    allow_upscale: bool,
    animate: bool = False,
) -> None:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    format_name = output_format.upper()
    if format_name == "JPG":
        format_name = "JPEG"

    def resized(frame: Image.Image) -> Image.Image:
        processed = ImageOps.exif_transpose(frame)
        alpha = "A" in processed.getbands() or "transparency" in processed.info
        mode = "RGBA" if alpha and format_name != "JPEG" else "RGB"
        if processed.mode != mode:
            processed = processed.convert(mode)
        size = _target_size(processed.size, max_dimension=max_dimension, allow_upscale=allow_upscale)
        if size != processed.size:
            processed = processed.resize(size, Image.Resampling.LANCZOS)
        return processed

    save_kwargs = {}
    if format_name == "WEBP":
        save_kwargs.update(quality=quality, method=6)
    elif format_name == "JPEG":
        save_kwargs["quality"] = quality
    if not animate:
        resized(image).save(destination_path, format=format_name, **save_kwargs)
        return

    if format_name not in {"WEBP", "GIF", "PNG"}:
        raise ArtifactProcessingError("Animated GIF previews require WebP, GIF or PNG.")
    if format_name == "GIF":
        if "loop" in image.info:
            save_kwargs["loop"] = image.info["loop"]
        save_kwargs["disposal"] = 2
    else:
        save_kwargs["loop"] = animation_loop_count(image)
    if format_name == "WEBP":
        if save_kwargs["loop"] > 65535:
            raise ArtifactProcessingError("The GIF loop count exceeds WebP's supported range.")
        # Use full frames so cropped opaque regions cannot erase alpha in the canvas.
        save_kwargs.update(background=(0, 0, 0, 0), kmax=1)
    frames = []
    durations = []
    for frame in animation_frames(image):
        frames.append(resized(frame.convert("RGBA")))
        durations.append(frame.info.get("duration", 100))
    frames[0].save(
        destination_path, format=format_name, save_all=True, append_images=frames[1:],
        duration=durations, **save_kwargs,
    )


def _target_size(
    size: Tuple[int, int], *, max_dimension: int, allow_upscale: bool
) -> Tuple[int, int]:
    width, height = size
    longest = max(width, height)
    if longest <= max_dimension and not allow_upscale:
        return width, height
    scale = max_dimension / float(longest)
    return max(1, int(round(width * scale))), max(1, int(round(height * scale)))


def _derived_record(kind: str, path: Path, *, include_sha256: bool) -> DerivedAssetRecord:
    metadata = image_metadata(path, include_sha256=include_sha256)
    return DerivedAssetRecord(
        kind=kind,
        relative_path=str(path),
        mime_type=metadata["mime_type"],
        width=metadata["width"],
        height=metadata["height"],
        duration_seconds=metadata["duration_seconds"],
        bytes=metadata["bytes"],
        sha256=metadata["sha256"],
        metadata=metadata["metadata"],
    )
