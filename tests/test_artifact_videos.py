import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from kie_api.artifacts.inspect import ffmpeg_available, ffmpeg_path, ffprobe_path
from kie_api.artifacts.videos import (
    build_poster_command,
    build_web_video_command,
    generate_video_derivatives,
)
from kie_api.exceptions import ArtifactProcessingError


def test_build_video_commands_are_browser_friendly() -> None:
    web_command = build_web_video_command(Path("in.mov"), Path("out.mp4"))
    poster_command = build_poster_command(Path("in.mov"), Path("poster.jpg"))

    assert web_command[0] == "ffmpeg"
    assert "libx264" in web_command
    assert "+faststart" in web_command
    assert poster_command[-1] == "poster.jpg"

    custom_command = build_web_video_command(Path("in.mov"), Path("out.mp4"), ffmpeg_binary=r"C:\venv\ffmpeg.exe")
    assert custom_command[0] == r"C:\venv\ffmpeg.exe"


def test_ffmpeg_path_uses_imageio_binary_when_system_ffmpeg_is_missing(monkeypatch) -> None:
    monkeypatch.setattr("kie_api.artifacts.inspect.shutil.which", lambda _name: None)
    monkeypatch.setitem(sys.modules, "imageio_ffmpeg", SimpleNamespace(get_ffmpeg_exe=lambda: r"C:\venv\ffmpeg.exe"))

    assert ffmpeg_path() == r"C:\venv\ffmpeg.exe"
    assert ffmpeg_available() is True


def test_generate_video_derivatives_raises_clear_error_without_ffmpeg(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("kie_api.artifacts.videos.ffmpeg_path", lambda: None)

    with pytest.raises(ArtifactProcessingError, match="ffmpeg is required"):
        generate_video_derivatives(
            tmp_path / "source.mp4",
            tmp_path / "web.mp4",
            tmp_path / "poster.jpg",
        )


@pytest.mark.skipif(not ffmpeg_available(), reason="ffmpeg is required for video derivative test")
def test_generate_video_derivatives_for_tiny_clip(tmp_path: Path) -> None:
    ffmpeg = ffmpeg_path()
    assert ffmpeg is not None
    source = tmp_path / "source.mp4"
    web = tmp_path / "web.mp4"
    poster = tmp_path / "poster.jpg"

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=320x240:d=1",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    web_record, poster_record = generate_video_derivatives(source, web, poster)

    assert web.exists()
    assert poster.exists()
    assert web_record.mime_type == "video/mp4"
    if ffprobe_path():
        assert web_record.duration_seconds is not None
    assert poster_record.mime_type == "image/jpeg"
