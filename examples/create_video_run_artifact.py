"""Create a local video run artifact bundle with a tiny synthetic clip."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess

from kie_api import (
    ArtifactSource,
    PromptRecord,
    ProviderTrace,
    RunArtifactCreateRequest,
    create_run_artifact,
)
from kie_api.artifacts.inspect import ffmpeg_available


def main() -> None:
    if not ffmpeg_available():
        raise SystemExit("ffmpeg and ffprobe are required for this example.")

    with TemporaryDirectory() as tmp_dir:
        temp_root = Path(tmp_dir)
        input_video = temp_root / "motion.mp4"
        output_video = temp_root / "output.mp4"

        for path, color in ((input_video, "orange"), (output_video, "purple")):
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    f"color=c={color}:s=640x360:d=1",
                    "-pix_fmt",
                    "yuv420p",
                    str(path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        artifact = create_run_artifact(
            RunArtifactCreateRequest(
                status="succeeded",
                model_key="kling-3.0-i2v",
                provider_model="kling-3.0/video",
                slug="synthetic_video_test",
                created_at=datetime.now(timezone.utc).isoformat(),
                prompts=PromptRecord(
                    raw="Animate this still into a short push-in.",
                    final_used="Animate this still into a short push-in.",
                ),
                inputs=[ArtifactSource(kind="video", role="motion", source_path=str(input_video))],
                outputs=[ArtifactSource(kind="video", role="output", source_path=str(output_video))],
                provider_trace=ProviderTrace(task_id="task_example_video_001"),
                tags=["example", "video"],
            ),
            output_root=temp_root / "outputs",
        )

        print(artifact.run_dir)


if __name__ == "__main__":
    main()
