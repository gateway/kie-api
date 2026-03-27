"""Generate derivatives for local originals that already exist on disk."""

from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from kie_api import generate_image_derivatives


def main() -> None:
    with TemporaryDirectory() as tmp_dir:
        temp_root = Path(tmp_dir)
        source = temp_root / "original.png"
        web = temp_root / "web.webp"
        thumb = temp_root / "thumb.webp"
        Image.new("RGB", (1400, 900), color="teal").save(source)

        web_record, thumb_record = generate_image_derivatives(
            str(source),
            str(web),
            str(thumb),
        )

        print(web_record.model_dump())
        print(thumb_record.model_dump())


if __name__ == "__main__":
    main()
