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


def test_derivatives_apply_exif_rotation_without_changing_original(tmp_path: Path) -> None:
    source = tmp_path / "rotated.jpg"
    exif = Image.Exif()
    exif[274] = 6
    Image.new("RGB", (80, 40), "blue").save(source, exif=exif)
    original = source.read_bytes()

    web, thumb = generate_image_derivatives(source, tmp_path / "web.webp", tmp_path / "thumb.webp")

    assert (web.width, web.height) == (40, 80)
    assert (thumb.width, thumb.height) == (40, 80)
    assert source.read_bytes() == original


def test_transparent_derivatives_support_webp_and_jpeg(tmp_path: Path) -> None:
    source = tmp_path / "transparent.png"
    Image.new("RGBA", (80, 40), (255, 0, 0, 128)).save(source)
    web_path, thumb_path = tmp_path / "web.webp", tmp_path / "thumb.jpg"

    generate_image_derivatives(source, web_path, thumb_path, thumb_format="jpeg")

    with Image.open(web_path) as web:
        assert web.mode == "RGBA"
        assert web.getpixel((0, 0))[3] == 128
    with Image.open(thumb_path) as thumb:
        assert thumb.mode == "RGB"
        assert thumb.size == (80, 40)
