import json
from pathlib import Path

import httpx
import pytest
from PIL import Image, ImageDraw, ImageSequence

from kie_api import load_run_artifact
from kie_api.artifacts import inspect
from kie_api.artifacts.models import ArtifactDerivativeSettings, ArtifactSource, RunArtifactCreateRequest
from kie_api.artifacts.writer import build_run_manifest, create_run_artifact
from kie_api.clients.download import DownloadClient
from kie_api.config import KieSettings

MODEL_KEY = "gpt-image-2-6-sunburst-text-to-image"


def bundle(tmp_path, source, **kwargs):
    return create_run_artifact(
        RunArtifactCreateRequest(
            status="succeeded",
            model_key=MODEL_KEY,
            outputs=[ArtifactSource(kind="image", role="output", source_path=str(source))],
            **kwargs,
        ),
        output_root=tmp_path / "outputs",
    )


def transparent_gif(path, loop=0):
    frames = []
    for x in (10, 30, 50):
        frame = Image.new("RGBA", (96, 72), (0, 0, 0, 0))
        ImageDraw.Draw(frame).rectangle((x, 24, x + 24, 48), fill=(255, 0, 0, 255))
        frames.append(frame)
    loop_option = {"loop": loop} if loop is not None else {}
    frames[0].save(
        path, format="GIF", save_all=True, append_images=frames[1:],
        duration=[60, 100, 200], disposal=2, **loop_option,
    )


def test_downloaded_gif_is_detected_by_content_and_preview_preserves_animation(tmp_path):
    sample = tmp_path / "sample.gif"
    transparent_gif(sample)
    data = sample.read_bytes()
    wrong_name = tmp_path / "response.png"

    def respond(request):
        assert request.url.path == "/response.png"
        return httpx.Response(200, content=data, headers={"Content-Type": "application/octet-stream"})

    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        DownloadClient(KieSettings(), http_client=transport).download_to_path(
            "https://tempfile.redpandaai.co/response.png", str(wrong_name)
        )
    run = bundle(tmp_path, wrong_name)
    root = Path(run.run_dir)
    record = load_run_artifact(run.run_dir).outputs[0]
    assert record.original_filename == "response.png"
    assert record.mime_type == "image/gif"
    assert record.original_path == "original/output_01.gif"
    assert (root / record.original_path).read_bytes() == data
    assert record.metadata == {"is_animated": True, "frame_count": 3, "loop_count": 0}
    assert record.duration_seconds == pytest.approx(0.36)
    web_asset, thumb_asset = record.derivatives
    assert web_asset.metadata == record.metadata
    assert web_asset.duration_seconds == pytest.approx(0.36)
    assert thumb_asset.metadata == {"is_animated": False, "frame_count": 1}
    assert thumb_asset.duration_seconds is None
    manifest = json.loads((root / run.manifest_path).read_text())
    assert manifest["duration_seconds"] == pytest.approx(0.36)
    with Image.open(root / record.web_path) as web:
        assert web.format == "WEBP"
        assert web.n_frames == 3
        assert web.info["loop"] == 0
        durations = []
        for index, frame in enumerate(ImageSequence.Iterator(web)):
            rgba = frame.convert("RGBA")
            durations.append(frame.info["duration"])
            assert rgba.getpixel((0, 0))[3] == 0
            assert rgba.getpixel((16 + index * 20, 36))[3] == 255
        assert durations == [60, 100, 200]
    with Image.open(root / record.thumb_path) as thumb:
        assert thumb.n_frames == 1
        assert thumb.getpixel((0, 0))[3] == 0
    assert not run.warnings


@pytest.mark.parametrize(("gif_loop", "plays", "web_format"), [(None, 1, "webp"), (2, 3, "webp"), (2, 3, "png")])
def test_gif_play_count_is_preserved_across_formats(tmp_path, gif_loop, plays, web_format):
    source = tmp_path / "source.gif"
    transparent_gif(source, loop=gif_loop)
    run = bundle(tmp_path, source, derivative_settings=ArtifactDerivativeSettings(image_web_format=web_format))
    record = run.outputs[0]
    web_asset = record.derivatives[0]
    assert record.metadata["loop_count"] == web_asset.metadata["loop_count"] == plays
    with Image.open(Path(run.run_dir) / web_asset.relative_path) as web:
        assert web.info["loop"] == plays


def test_animation_inspection_budget_keeps_original_without_partial_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(inspect, "MAX_ANIMATION_FRAMES", 2)
    source = tmp_path / "source.gif"
    transparent_gif(source)
    run = bundle(tmp_path, source)
    record = load_run_artifact(run.run_dir).outputs[0]
    assert (Path(run.run_dir) / record.original_path).read_bytes() == source.read_bytes()
    assert record.metadata["is_animated"]
    assert record.metadata["animation_metadata_incomplete"]
    assert "frame_count" not in record.metadata
    assert record.duration_seconds is None
    assert record.web_path is None
    assert any("frame or canvas pixel budget" in warning for warning in run.warnings)


def test_palette_png_transparency_survives_previews(tmp_path):
    source = tmp_path / "palette"
    image = Image.new("P", (8, 8), 0)
    image.putpalette([0, 0, 0, 255, 255, 255] + [0] * 762)
    image.putpixel((4, 4), 1)
    image.save(source, format="PNG", transparency=0)
    run = bundle(tmp_path, source)
    record = run.outputs[0]
    assert record.mime_type == "image/png"
    assert record.original_path == "original/output_01.png"
    for path in (record.web_path, record.thumb_path):
        with Image.open(Path(run.run_dir) / path) as image:
            assert image.getpixel((0, 0))[3] == 0
            assert image.getpixel((4, 4))[3] == 255


def test_svg_stays_download_only_even_with_active_content(tmp_path):
    source = tmp_path / "payload.jpg"
    svg = b"""<?xml version="1.0"?>
<!DOCTYPE svg SYSTEM "https://example.invalid/vector.dtd">
<!-- generated vector -->
<svg xmlns="http://www.w3.org/2000/svg" width="96" height="72" onload="alert(1)">
  <script>fetch('https://example.invalid/beacon')</script>
  <image href="https://example.invalid/image.png"/>
  <rect width="50" height="50"/>
</svg>"""
    source.write_bytes(svg)
    run = bundle(tmp_path, source)
    root = Path(run.run_dir)
    persisted = load_run_artifact(str(root))
    record = persisted.outputs[0]
    assert record.mime_type == "image/svg+xml"
    assert record.original_path == "original/output_01.svg"
    assert (root / record.original_path).read_bytes() == svg
    assert not record.web_path and not record.thumb_path and not record.derivatives
    assert not list((root / "web").iterdir()) and not list((root / "thumb").iterdir())
    assert any("safe raster preview is unavailable" in message for message in persisted.warnings)
    manifest = build_run_manifest(persisted)
    assert manifest.hero_original == record.original_path
    assert manifest.hero_output_path is None and manifest.hero_web is None


@pytest.mark.parametrize("kind", ["invalid_image", "failed_thumbnail"])
def test_preview_failure_keeps_original_and_persists_successful_run(tmp_path, kind):
    source = tmp_path / "image.png"
    settings = ArtifactDerivativeSettings()
    if kind == "invalid_image":
        source.write_bytes(b"<html>This is not an image</html>")
    else:
        Image.new("RGB", (24, 24), "green").save(source)
        settings.image_thumb_format = "invalid"
    run = bundle(tmp_path, source, derivative_settings=settings)
    persisted = load_run_artifact(run.run_dir)
    root = Path(persisted.run_dir)
    record = persisted.outputs[0]
    assert (root / record.original_path).read_bytes() == source.read_bytes()
    assert persisted.status == "succeeded"
    assert any("Image derivatives skipped" in message for message in persisted.warnings)
    assert record.web_path is None and record.thumb_path is None
    assert not list((root / "web").iterdir()) and not list((root / "thumb").iterdir())
    if kind == "invalid_image":
        assert record.mime_type is None
        assert record.original_path.endswith(".bin")
