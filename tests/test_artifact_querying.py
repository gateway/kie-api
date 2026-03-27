import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from kie_api import (
    ArtifactDerivativeSettings,
    ArtifactSource,
    PromptRecord,
    ProviderTrace,
    RunArtifactCreateRequest,
    append_run_index,
    create_run_artifact,
    get_latest_assets,
    get_latest_successful_run,
    get_run_by_id,
    get_run_summary,
    list_recent_runs,
    list_runs_by_model,
    list_runs_by_status,
    list_runs_by_tag,
    load_run_artifact,
    rebuild_run_index,
    update_run_notes,
)
from kie_api.artifacts.index import load_run_index, scan_run_artifacts
from kie_api.artifacts.models import RunIndexEntry, RunSourceContext


def _make_image(path: Path, color: str) -> None:
    Image.new("RGB", (800, 600), color=color).save(path)


def _create_image_run(
    output_root: Path,
    *,
    created_at: str,
    model_key: str,
    status: str,
    tag: str,
    slug: str,
) -> Path:
    tmp_inputs = output_root.parent
    input_path = tmp_inputs / f"{slug}_input.png"
    output_path = tmp_inputs / f"{slug}_output.png"
    _make_image(input_path, "navy")
    _make_image(output_path, "orange")
    artifact = create_run_artifact(
        RunArtifactCreateRequest(
            status=status,
            model_key=model_key,
            created_at=created_at,
            slug=slug,
            prompts=PromptRecord(raw=f"Prompt for {slug}", final_used=f"Prompt for {slug}"),
            source_context=RunSourceContext(project_name="query-tests", source_agent="codex"),
            inputs=[ArtifactSource(kind="image", role="reference", source_path=str(input_path))],
            outputs=[ArtifactSource(kind="image", role="output", source_path=str(output_path))],
            provider_trace=ProviderTrace(task_id=f"task_{slug}"),
            tags=[tag],
        ),
        output_root=output_root,
    )
    return Path(artifact.run_dir)


def test_query_helpers_filter_and_load_runs(tmp_path: Path) -> None:
    output_root = tmp_path / "outputs"
    run_a = _create_image_run(
        output_root,
        created_at=datetime(2026, 3, 26, 20, 0, tzinfo=timezone.utc).isoformat(),
        model_key="nano-banana-2",
        status="succeeded",
        tag="portrait",
        slug="a",
    )
    run_b = _create_image_run(
        output_root,
        created_at=datetime(2026, 3, 26, 21, 0, tzinfo=timezone.utc).isoformat(),
        model_key="nano-banana-pro",
        status="failed",
        tag="retry",
        slug="b",
    )
    run_c = _create_image_run(
        output_root,
        created_at=datetime(2026, 3, 26, 22, 0, tzinfo=timezone.utc).isoformat(),
        model_key="nano-banana-2",
        status="succeeded",
        tag="portrait",
        slug="c",
    )

    recent = list_recent_runs(output_root=str(output_root), limit=2)
    assert [entry.run_id for entry in recent] == [run_c.name, run_b.name]

    by_model = list_runs_by_model("nano-banana-2", output_root=str(output_root))
    assert [entry.run_id for entry in by_model] == [run_c.name, run_a.name]

    by_status = list_runs_by_status("failed", output_root=str(output_root))
    assert [entry.run_id for entry in by_status] == [run_b.name]

    by_tag = list_runs_by_tag("portrait", output_root=str(output_root))
    assert [entry.run_id for entry in by_tag] == [run_c.name, run_a.name]

    latest_success = get_latest_successful_run(output_root=str(output_root))
    assert latest_success is not None
    assert latest_success.run_id == run_c.name

    latest_assets = get_latest_assets(output_root=str(output_root), model_key="nano-banana-2")
    assert latest_assets["run_id"] == run_c.name
    assert latest_assets["hero_web"] == "web/output_01.webp"

    loaded = get_run_by_id(run_a.name, output_root=str(output_root))
    assert loaded is not None
    assert loaded.provider_trace.task_id == "task_a"

    summary = get_run_summary(str(run_a))
    assert summary.run_id == run_a.name
    assert summary.hero_web == "web/output_01.webp"

    loaded_direct = load_run_artifact(str(run_b))
    assert loaded_direct.run_id == run_b.name


def test_duplicate_safe_append_and_rebuild_index(tmp_path: Path) -> None:
    output_root = tmp_path / "outputs"
    run_dir = _create_image_run(
        output_root,
        created_at=datetime(2026, 3, 26, 20, 0, tzinfo=timezone.utc).isoformat(),
        model_key="nano-banana-2",
        status="succeeded",
        tag="portrait",
        slug="dup",
    )
    existing = load_run_index(output_root)
    assert len(existing) == 1

    append_run_index(
        RunIndexEntry(
            run_id=run_dir.name,
            created_at=existing[0].created_at,
            status=existing[0].status,
            model_key=existing[0].model_key,
            run_path=existing[0].run_path,
        ),
        output_root=str(output_root),
    )
    after = load_run_index(output_root)
    assert len(after) == 1

    index_path = output_root / "index.jsonl"
    index_path.unlink()
    rebuilt = rebuild_run_index(output_root=str(output_root))
    assert rebuilt.exists()
    rebuilt_entries = load_run_index(output_root)
    assert len(rebuilt_entries) == 1
    assert rebuilt_entries[0].run_id == run_dir.name
    assert scan_run_artifacts(output_root) == [run_dir]


def test_update_run_notes_regenerates_notes_from_run_metadata(tmp_path: Path) -> None:
    output_root = tmp_path / "outputs"
    run_dir = _create_image_run(
        output_root,
        created_at=datetime(2026, 3, 26, 23, 0, tzinfo=timezone.utc).isoformat(),
        model_key="nano-banana-2",
        status="succeeded",
        tag="portrait",
        slug="notes",
    )
    run = get_run_by_id(run_dir.name, output_root=str(output_root))
    assert run is not None
    run.notes = "Updated note body"

    notes_path = update_run_notes(run)

    text = Path(notes_path).read_text(encoding="utf-8")
    assert "Updated note body" in text
    assert "query-tests" in text


def test_custom_derivative_settings_change_index_hero_paths(tmp_path: Path) -> None:
    output_root = tmp_path / "outputs"
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "output.png"
    _make_image(input_path, "blue")
    _make_image(output_path, "green")

    run = create_run_artifact(
        RunArtifactCreateRequest(
            status="succeeded",
            model_key="nano-banana-pro",
            created_at=datetime(2026, 3, 26, 23, 30, tzinfo=timezone.utc).isoformat(),
            prompts=PromptRecord(raw="Custom formats", final_used="Custom formats"),
            derivative_settings=ArtifactDerivativeSettings(
                image_web_format="jpg",
                image_thumb_format="png",
            ),
            inputs=[ArtifactSource(kind="image", role="reference", source_path=str(input_path))],
            outputs=[ArtifactSource(kind="image", role="output", source_path=str(output_path))],
        ),
        output_root=output_root,
    )

    entries = load_run_index(output_root)
    assert entries[0].hero_web == "web/output_01.jpg"
    assert entries[0].hero_thumb == "thumb/output_01.png"
    manifest = json.loads((Path(run.run_dir) / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["hero_web"] == "web/output_01.jpg"
