"""Image derivative helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

from PIL import Image, ImageOps

from .inspect import image_metadata
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
    _save_resized_image(
        source,
        web_path,
        max_dimension=web_max_dimension,
        output_format=web_format,
        quality=web_quality,
        allow_upscale=allow_upscale,
    )
    _save_resized_image(
        source,
        thumb_path,
        max_dimension=thumb_max_dimension,
        output_format=thumb_format,
        quality=thumb_quality,
        allow_upscale=allow_upscale,
    )
    return (
        _derived_record("web", web_path, include_sha256=enable_sha256),
        _derived_record("thumb", thumb_path, include_sha256=enable_sha256),
    )


def _save_resized_image(
    source_path: Path,
    destination_path: Path,
    *,
    max_dimension: int,
    output_format: str,
    quality: int,
    allow_upscale: bool,
) -> None:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as image:
        processed = ImageOps.exif_transpose(image)
        if processed.mode not in {"RGB", "RGBA"}:
            processed = processed.convert("RGBA" if "A" in processed.getbands() else "RGB")
        size = _target_size(processed.size, max_dimension=max_dimension, allow_upscale=allow_upscale)
        if size != processed.size:
            processed = processed.resize(size, Image.Resampling.LANCZOS)
        normalized_format = output_format.upper()
        if normalized_format == "JPG":
            normalized_format = "JPEG"
        if normalized_format in {"JPEG", "JPG"} and processed.mode == "RGBA":
            processed = processed.convert("RGB")
        save_kwargs = {}
        if normalized_format == "WEBP":
            save_kwargs["quality"] = quality
            save_kwargs["method"] = 6
        elif normalized_format in {"JPEG", "JPG"}:
            save_kwargs["quality"] = quality
        processed.save(destination_path, format=normalized_format, **save_kwargs)


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
        bytes=metadata["bytes"],
        sha256=metadata["sha256"],
    )
