"""Create a local image run artifact bundle with synthetic assets."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from kie_api import ArtifactSource, PromptRecord, ProviderTrace, RunArtifactCreateRequest, create_run_artifact


def main() -> None:
    with TemporaryDirectory() as tmp_dir:
        temp_root = Path(tmp_dir)
        input_image = temp_root / "input.png"
        output_image = temp_root / "output.png"
        Image.new("RGB", (960, 1280), color="navy").save(input_image)
        Image.new("RGB", (960, 1280), color="skyblue").save(output_image)

        artifact = create_run_artifact(
            RunArtifactCreateRequest(
                status="succeeded",
                model_key="nano-banana-2",
                provider_model="nano-banana-2",
                slug="blue_background_test",
                created_at=datetime.now(timezone.utc).isoformat(),
                prompts=PromptRecord(
                    raw="Remove all elements around the man and make the background blue.",
                    final_used="Remove all elements around the man and make the background blue.",
                ),
                inputs=[ArtifactSource(kind="image", role="reference", source_path=str(input_image))],
                outputs=[ArtifactSource(kind="image", role="output", source_path=str(output_image))],
                provider_trace=ProviderTrace(task_id="task_example_001"),
                tags=["example", "image"],
            ),
            output_root=temp_root / "outputs",
        )

        print(artifact.run_dir)


if __name__ == "__main__":
    main()
