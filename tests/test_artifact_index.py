import json
from pathlib import Path

from kie_api.artifacts.index import append_run_index
from kie_api.artifacts.models import RunIndexEntry


def test_append_run_index_writes_jsonl_line(tmp_path: Path) -> None:
    entry = RunIndexEntry(
        run_id="20260326_214512_nano_banana_pro_cinematic_v01",
        created_at="2026-03-26T21:45:12+00:00",
        model_key="nano-banana-pro",
        status="succeeded",
        hero_output="web/output_01.webp",
        hero_thumb="thumb/output_01.webp",
        prompt_summary="Make the portrait more cinematic.",
        tags=["portrait", "test"],
        run_path="2026-03-26/20260326_214512_nano_banana_pro_cinematic_v01",
    )

    index_path = append_run_index(tmp_path / "outputs", entry)

    lines = index_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["run_id"] == entry.run_id
    assert payload["hero_thumb"] == "thumb/output_01.webp"
