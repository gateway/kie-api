"""Optional live submit/status example guarded by env vars."""

import os

from kie_api import (
    prepare_request_for_submission,
    submit_prepared_request,
    validate_request,
    wait_for_task,
)
from kie_api.config import KieSettings
from kie_api.enums import ValidationState
from kie_api.models import RawUserRequest
from kie_api.registry.loader import load_registry


def main() -> None:
    if os.getenv("KIE_API_KEY") is None:
        raise SystemExit("Set KIE_API_KEY before running this example.")
    if os.getenv("KIE_RUN_LIVE_SMOKE") != "1":
        raise SystemExit("Set KIE_RUN_LIVE_SMOKE=1 to acknowledge this live example.")

    registry = load_registry()
    settings = KieSettings.from_env()
    source_url = os.getenv("KIE_SMOKE_UPLOAD_SOURCE_URL")
    raw_request = RawUserRequest(
        model_key=os.getenv("KIE_SMOKE_SUBMIT_MODEL_KEY", "nano-banana-2"),
        prompt=os.getenv(
            "KIE_SMOKE_PROMPT",
            "Generate a simple square product hero image with soft studio lighting.",
        ),
        images=[source_url] if source_url else [],
        options={"aspect_ratio": "1:1", "output_format": "jpg"},
    )
    validation = validate_request(raw_request, registry)

    if validation.state not in {
        ValidationState.READY,
        ValidationState.READY_WITH_DEFAULTS,
        ValidationState.READY_WITH_WARNING,
    }:
        raise SystemExit(f"Request was not submission-ready: {validation.model_dump()}")

    prepared = prepare_request_for_submission(
        validation,
        registry=registry,
        settings=settings,
    )
    submission = submit_prepared_request(prepared, registry=registry, settings=settings)
    status = wait_for_task(
        submission.task_id,
        settings=settings,
    )

    print("prepared")
    print(prepared.model_dump())
    print("submission")
    print(submission.model_dump())
    print("wait_result")
    print(status.model_dump())


if __name__ == "__main__":
    main()
