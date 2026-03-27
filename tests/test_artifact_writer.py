import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from kie_api import ArtifactDerivativeSettings, create_run_artifact
from kie_api.artifacts.models import ArtifactSource, PromptRecord, ProviderTrace, RunArtifactCreateRequest, RunSourceContext


def test_create_run_artifact_writes_expected_bundle_for_image_run(tmp_path: Path) -> None:
    input_image = tmp_path / "input.png"
    output_image = tmp_path / "output.png"
    Image.new("RGB", (1024, 768), color="green").save(input_image)
    Image.new("RGB", (1200, 900), color="red").save(output_image)

    run = create_run_artifact(
        RunArtifactCreateRequest(
            status="succeeded",
            model_key="nano-banana-pro",
            provider_model="nano-banana-pro",
            slug="cinematic_v01",
            created_at=datetime(2026, 3, 26, 21, 45, 12, tzinfo=timezone.utc).isoformat(),
            prompts=PromptRecord(
                raw="Make this portrait more cinematic.",
                enhanced="Make this portrait more cinematic with soft rim light.",
                final_used="Make this portrait more cinematic with soft rim light.",
                prompt_profile="nano_banana_pro_v1",
            ),
            inputs=[
                ArtifactSource(
                    kind="image",
                    role="reference",
                    source_path=str(input_image),
                )
            ],
            outputs=[
                ArtifactSource(
                    kind="image",
                    role="output",
                    source_path=str(output_image),
                )
            ],
            options={"resolution": "2K", "aspect_ratio": "9:16", "output_format": "jpg"},
            provider_trace=ProviderTrace(task_id="task_123"),
            submit_payload={"model": "nano-banana-pro"},
            submit_response={"code": 200, "data": {"taskId": "task_123"}},
            final_status_response={"code": 200, "data": {"state": "success"}},
            warnings=["Used test asset inputs."],
            tags=["portrait", "artifact-test"],
        ),
        output_root=tmp_path / "outputs",
    )

    run_dir = Path(run.run_dir)
    assert run.run_id == "20260326_214512_nano_banana_pro_cinematic_v01"
    assert (run_dir / "run.json").exists()
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "notes.md").exists()
    assert (run_dir / "prompt.txt").exists()
    assert (run_dir / "prompt_enhanced.txt").exists()
    assert (run_dir / "inputs" / "ref_01.png").exists()
    assert (run_dir / "original" / "output_01.png").exists()
    assert (run_dir / "web" / "output_01.webp").exists()
    assert (run_dir / "thumb" / "output_01.webp").exists()
    assert (run_dir / "logs" / "submit_payload.json").exists()
    assert (run_dir / "logs" / "submit_response.json").exists()
    assert (run_dir / "logs" / "status_response_final.json").exists()

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["hero_output_path"] == "web/output_01.webp"
    assert manifest["thumbnail_path"] == "thumb/output_01.webp"
    assert manifest["output_count"] == 1

    run_payload = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert run_payload["outputs"][0]["relative_path"] == "original/output_01.png"
    assert run_payload["outputs"][0]["original_path"] == "original/output_01.png"
    assert run_payload["outputs"][0]["web_path"] == "web/output_01.webp"
    assert run_payload["outputs"][0]["thumb_path"] == "thumb/output_01.webp"
    assert run_payload["outputs"][0]["bytes_original"] is not None
    assert run_payload["provider_trace"]["task_id"] == "task_123"

    index_path = tmp_path / "outputs" / "index.jsonl"
    assert index_path.exists()
    index_line = json.loads(index_path.read_text(encoding="utf-8").splitlines()[0])
    assert index_line["run_id"] == run.run_id
    assert index_line["hero_output"] == "web/output_01.webp"


def test_create_run_artifact_honors_custom_derivative_settings(tmp_path: Path) -> None:
    input_image = tmp_path / "input.png"
    output_image = tmp_path / "output.png"
    Image.new("RGB", (640, 480), color="green").save(input_image)
    Image.new("RGB", (640, 480), color="red").save(output_image)

    run = create_run_artifact(
        RunArtifactCreateRequest(
            status="succeeded",
            model_key="nano-banana-2",
            created_at=datetime(2026, 3, 26, 22, 1, 0, tzinfo=timezone.utc).isoformat(),
            source_context=RunSourceContext(
                source_type="manual",
                source_user="tester",
                source_channel="cli",
                source_agent="codex",
                project_name="artifact-tests",
                notes="custom derivative test",
            ),
            derivative_settings=ArtifactDerivativeSettings(
                image_web_max_dimension=320,
                image_web_format="jpg",
                image_thumb_max_dimension=128,
                image_thumb_format="png",
                enable_sha256=False,
            ),
            prompts=PromptRecord(raw="Test", final_used="Test"),
            inputs=[ArtifactSource(kind="image", role="reference", source_path=str(input_image))],
            outputs=[ArtifactSource(kind="image", role="output", source_path=str(output_image))],
        ),
        output_root=tmp_path / "outputs",
    )

    output = run.outputs[0]
    assert output.web_path == "web/output_01.jpg"
    assert output.thumb_path == "thumb/output_01.png"
    assert output.sha256 is None
    assert output.derivatives[0].sha256 is None
    assert run.source_context.project_name == "artifact-tests"
