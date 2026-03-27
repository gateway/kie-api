"""Create an image artifact bundle with custom derivative settings."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from kie_api import (
    ArtifactDerivativeSettings,
    ArtifactSource,
    PromptRecord,
    RunArtifactCreateRequest,
    RunSourceContext,
    create_run_artifact,
)


def main() -> None:
    with TemporaryDirectory() as tmp_dir:
        temp_root = Path(tmp_dir)
        input_image = temp_root / "input.png"
        output_image = temp_root / "output.png"
        Image.new("RGB", (1200, 900), color="navy").save(input_image)
        Image.new("RGB", (1200, 900), color="skyblue").save(output_image)

        artifact = create_run_artifact(
            RunArtifactCreateRequest(
                status="succeeded",
                model_key="nano-banana-pro",
                created_at=datetime.now(timezone.utc).isoformat(),
                derivative_settings=ArtifactDerivativeSettings(
                    image_web_max_dimension=960,
                    image_web_format="jpg",
                    image_thumb_max_dimension=240,
                    image_thumb_format="png",
                    enable_sha256=False,
                ),
                source_context=RunSourceContext(
                    source_type="manual",
                    source_user="demo-user",
                    project_name="custom-derivatives-demo",
                ),
                prompts=PromptRecord(raw="Make the portrait cleaner.", final_used="Make the portrait cleaner."),
                inputs=[ArtifactSource(kind="image", role="reference", source_path=str(input_image))],
                outputs=[ArtifactSource(kind="image", role="output", source_path=str(output_image))],
            ),
            output_root=temp_root / "outputs",
        )

        print(artifact.model_dump())


if __name__ == "__main__":
    main()
