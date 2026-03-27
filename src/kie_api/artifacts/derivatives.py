"""Convenience wrappers for derivative generation."""

from __future__ import annotations

from pathlib import Path

from .images import generate_image_derivatives
from .videos import generate_video_derivatives

__all__ = [
    "generate_image_derivatives",
    "generate_video_derivatives",
]
