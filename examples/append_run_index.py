"""Append a manual run summary to the global JSONL index."""

from pathlib import Path
from tempfile import TemporaryDirectory

from kie_api import RunIndexEntry, append_run_index


def main() -> None:
    with TemporaryDirectory() as tmp_dir:
        output_root = Path(tmp_dir) / "outputs"
        path = append_run_index(
            RunIndexEntry(
                run_id="20260326_214512_nano_banana_pro_cinematic_v01",
                created_at="2026-03-26T21:45:12+00:00",
                model_key="nano-banana-pro",
                status="succeeded",
                hero_output="web/output_01.webp",
                hero_thumb="thumb/output_01.webp",
                prompt_summary="Make the portrait more cinematic.",
                tags=["example", "index"],
                run_path="2026-03-26/20260326_214512_nano_banana_pro_cinematic_v01",
            ),
            output_root=str(output_root),
        )
        print(path)


if __name__ == "__main__":
    main()
