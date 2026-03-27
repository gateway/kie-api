import os

import pytest

from kie_api import prepare_request_for_submission, submit_prepared_request, validate_request, wait_for_task
from kie_api.clients import CreditsClient, UploadClient
from kie_api.config import KieSettings
from kie_api.enums import ValidationState
from kie_api.models import RawUserRequest
from kie_api.registry.loader import load_registry


pytestmark = pytest.mark.smoke


def _require_live_smoke() -> None:
    if os.getenv("KIE_RUN_LIVE_SMOKE") != "1":
        pytest.skip("Set KIE_RUN_LIVE_SMOKE=1 to enable live smoke tests.")
    if not os.getenv("KIE_API_KEY"):
        pytest.skip("KIE_API_KEY is required for live smoke tests.")


def _require_live_submit_smoke() -> None:
    _require_live_smoke()
    if os.getenv("KIE_SMOKE_ALLOW_SUBMIT") != "1":
        pytest.skip("Set KIE_SMOKE_ALLOW_SUBMIT=1 to run live submit/status smoke tests.")
    model_key = os.getenv("KIE_SMOKE_SUBMIT_MODEL_KEY", "nano-banana-2")
    if not model_key.startswith("nano-banana"):
        pytest.skip("This pass is intentionally limited to low-cost image models.")


def test_live_credit_balance_smoke() -> None:
    _require_live_smoke()
    client = CreditsClient(KieSettings.from_env())

    result = client.get_balance()

    assert result.success is True
    assert result.raw_response is not None


def test_live_upload_from_url_smoke() -> None:
    _require_live_smoke()
    source_url = os.getenv("KIE_SMOKE_UPLOAD_SOURCE_URL")
    if not source_url:
        pytest.skip("Set KIE_SMOKE_UPLOAD_SOURCE_URL to run the upload smoke test.")

    client = UploadClient(KieSettings.from_env())
    result = client.upload_from_url(source_url)

    assert result.success is True
    assert result.file_url or result.download_url


@pytest.fixture(scope="module")
def live_submitted_task_id() -> str:
    _require_live_submit_smoke()

    registry = load_registry()
    settings = KieSettings.from_env()
    model_key = os.getenv("KIE_SMOKE_SUBMIT_MODEL_KEY", "nano-banana-2")
    prompt = os.getenv(
        "KIE_SMOKE_PROMPT",
        "Generate a simple square product hero image with soft studio lighting.",
    )
    source_url = os.getenv("KIE_SMOKE_UPLOAD_SOURCE_URL")

    raw_request = RawUserRequest(
        model_key=model_key,
        prompt=prompt,
        images=[source_url] if source_url else [],
        options={"aspect_ratio": "1:1", "output_format": "jpg"},
    )
    validation = validate_request(raw_request, registry)
    if validation.normalized_request is None or validation.state not in {
        ValidationState.READY,
        ValidationState.READY_WITH_DEFAULTS,
        ValidationState.READY_WITH_WARNING,
    }:
        pytest.skip(f"Smoke request did not validate cleanly: {validation.state}")

    prepared = prepare_request_for_submission(
        validation,
        registry=registry,
        settings=settings,
    )
    result = submit_prepared_request(prepared, registry=registry, settings=settings)
    return result.task_id


def test_live_submit_smoke(live_submitted_task_id: str) -> None:
    assert live_submitted_task_id


def test_live_status_smoke(live_submitted_task_id: str) -> None:
    _require_live_smoke()
    settings = KieSettings.from_env()
    result = wait_for_task(
        live_submitted_task_id,
        settings=settings,
        poll_interval_seconds=settings.wait_poll_interval_seconds,
        timeout_seconds=min(settings.wait_timeout_seconds, 300.0),
    ).final_status

    assert result is not None
    assert result.task_id == live_submitted_task_id
    assert result.provider_status is not None
