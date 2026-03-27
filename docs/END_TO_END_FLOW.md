# End-to-End Flow

This is the exact library-level execution flow an agent or wrapper should follow.

## Canonical flow
1. Build a `RawUserRequest`
2. Call `normalize_request(...)`
3. Call `validate_request(...)`
4. If state is `needs_input`, stop and surface `missing_inputs`
5. If state is `invalid`, stop and surface `impossible_inputs`
6. Optionally call `dry_run_prompt_enhancement(...)`
7. Optionally call `estimate_request_cost(...)` and `run_preflight(...)`
8. Call `prepare_request_for_submission(...)`
9. Call `submit_prepared_request(...)`
10. Store the returned `task_id`
11. Call `wait_for_task(...)` or poll status manually
12. Read `final_status.output_urls`
13. Optionally call `download_output_file(...)` to save the final asset locally
14. Optionally call `create_run_artifact(...)` to bundle the run, logs, originals, and derivatives

## Important invariant

Do not submit local file paths or arbitrary third-party media URLs directly to a model payload.

Always let `prepare_request_for_submission(...)` upload media first.

## Why validation happens before upload

Validation should reject impossible runs before any network cost or upload work begins.

Examples:
- Nano Banana Pro accepts at most 8 images
- Nano Banana 2 accepts at most 14 images

If a request exceeds those limits, `prepare_request_for_submission(...)` fails before uploading anything.

## Minimal code shape

```python
from kie_api import (
    download_output_file,
    prepare_request_for_submission,
    run_preflight,
    submit_prepared_request,
    validate_request,
    wait_for_task,
)
from kie_api.config import KieSettings
from kie_api.models import RawUserRequest

settings = KieSettings(api_key="replace-me")

request = RawUserRequest(
    model_key="nano-banana-2",
    prompt="Remove all elements around the man and make the background blue.",
    images=["/absolute/path/to/input.jpg"],
    options={"resolution": "2K", "aspect_ratio": "9:16", "output_format": "jpg"},
)

validation = validate_request(request)
if validation.state not in {"ready", "ready_with_defaults", "ready_with_warning"}:
    raise RuntimeError(validation.model_dump_json(indent=2))

preflight = run_preflight(validation, settings=settings)
if not preflight.can_submit:
    raise RuntimeError(preflight.model_dump_json(indent=2))

prepared = prepare_request_for_submission(validation, settings=settings)
submission = submit_prepared_request(prepared, settings=settings)
wait_result = wait_for_task(submission.task_id, settings=settings)

if wait_result.final_status is None or not wait_result.final_status.output_urls:
    raise RuntimeError(wait_result.model_dump_json(indent=2))

download = download_output_file(
    wait_result.final_status.output_urls[0],
    "/absolute/path/to/output.jpg",
    settings=settings,
)
print(download.model_dump())
```

## Data you should persist in a wrapper

This library does not persist jobs. A wrapper system should usually store:
- upstream job id
- `RawUserRequest`
- `ValidationResult`
- `PreparedRequest`
- `SubmissionResult.task_id`
- polling history or callback events
- final output URLs
- local download path if the wrapper saves the asset

## Common failure branches

### `needs_input`
The request is incomplete but recoverable. Ask only for the missing fields.

### `invalid`
The request is impossible as shaped. Do not upload and do not submit.

### timed out polling
The task may still be queued or running. Store the task id and resume polling later.
