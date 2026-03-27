from datetime import datetime, timezone

from kie_api.artifacts.paths import build_run_id, slugify


def test_slugify_normalizes_human_text() -> None:
    assert slugify("Nano Banana Pro Cinematic V01") == "nano_banana_pro_cinematic_v01"


def test_build_run_id_sorts_by_time_and_model() -> None:
    created_at = datetime(2026, 3, 26, 21, 45, 12, tzinfo=timezone.utc)

    run_id = build_run_id(created_at, "nano-banana-pro", slug="Cinematic V01")

    assert run_id == "20260326_214512_nano_banana_pro_cinematic_v01"
