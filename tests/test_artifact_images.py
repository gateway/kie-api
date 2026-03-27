from pathlib import Path

from PIL import Image

from kie_api.artifacts.images import generate_image_derivatives


def test_generate_image_derivatives_preserves_aspect_ratio_and_does_not_upscale(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    web = tmp_path / "web.webp"
    thumb = tmp_path / "thumb.webp"
    Image.new("RGB", (800, 400), color="blue").save(source)

    web_record, thumb_record = generate_image_derivatives(source, web, thumb)

    assert web.exists()
    assert thumb.exists()
    assert web_record.width == 800
    assert web_record.height == 400
    assert thumb_record.width == 384
    assert thumb_record.height == 192
    assert web_record.mime_type == "image/webp"
    assert thumb_record.mime_type == "image/webp"
