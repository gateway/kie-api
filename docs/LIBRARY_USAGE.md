# Library Usage

This package can be used as:
- an editable local repo for spec authoring and test development
- a packaged Python dependency
- a reusable integration layer underneath a separate Control API

## Installation

Editable:
```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

Packaged usage:
```bash
python -m pip install .
```

## How specs are loaded

`load_registry()` prefers the repo-local `specs/` directory when you are working in a checkout.
If that directory is not present, it falls back to bundled package data under `kie_api/resources/specs/`.

That means:
- editable installs use the authoring tree directly
- packaged installs still load model specs and prompt profiles correctly

## Normalize and validate

```python
from kie_api import dry_run_prompt_enhancement, normalize_request, validate_request
from kie_api.models import RawUserRequest

raw_request = RawUserRequest(
    model_key="kling-3.0",
    prompt="A cinematic reveal shot.",
    images=["https://example.com/start.png"],
    options={"duration": 5, "mode": "pro"},
)

normalized = normalize_request(raw_request)
validation = validate_request(normalized)
enhancement = dry_run_prompt_enhancement(normalized)
print(validation.model_dump())
print(enhancement.model_dump())
```

## Prepare, build, submit, and wait

All input media must be uploaded first. The recommended wrapper flow is:
- normalize
- validate
- prepare/upload
- build/submit
- wait/poll

```python
from kie_api import (
    build_submission_payload,
    download_output_file,
    prepare_request_for_submission,
    submit_prepared_request,
    validate_request,
    wait_for_task,
)
from kie_api.config import KieSettings
from kie_api.models import RawUserRequest

validation = validate_request(
    RawUserRequest(
        model_key="nano-banana-2",
        prompt="Generate a square ad image.",
        images=["/absolute/path/to/source.png"],
        options={"aspect_ratio": "1:1", "output_format": "jpg"},
    )
)

settings = KieSettings(api_key="replace-me")
prepared = prepare_request_for_submission(validation, settings=settings)
payload = build_submission_payload(prepared, settings=settings)
submission = submit_prepared_request(prepared, settings=settings)
wait_result = wait_for_task(submission.task_id, settings=settings)

print(payload)
print(wait_result.model_dump())
if wait_result.final_status and wait_result.final_status.output_urls:
    download = download_output_file(
        wait_result.final_status.output_urls[0],
        "/absolute/path/to/output.jpg",
        settings=settings,
    )
    print(download.model_dump())
```

Notes:
- `build_submission_payload(...)` intentionally rejects local paths and arbitrary third-party URLs.
- If a media URL is already hosted on a trusted KIE upload host, `prepare_request_for_submission(...)` will reuse it instead of reuploading it.

## Kling 3.0 frame guidance dry run

For Kling 3.0 on the current live page/API surface:
- `0` images means text-to-video
- `1` image means image-to-video with a start frame
- `2` images means image-to-video with first and last frames
- `aspect_ratio` must be omitted when both first and last frame images are provided

The validator now exposes the dry-run mode in `normalized_request.debug["frame_guidance_mode"]`.

```python
from kie_api import normalize_request, validate_request
from kie_api.models import RawUserRequest

request = RawUserRequest(
    model_key="kling-3.0-i2v",
    prompt="Animate smoothly from the first frame to the last frame.",
    images=["https://example.com/start.png", "https://example.com/end.png"],
    options={"duration": 5, "mode": "pro"},
)

normalized = normalize_request(request)
validation = validate_request(normalized)

print(validation.state)
print(validation.normalized_request.debug["frame_guidance_mode"])
```

Use `examples/dry_run_kling_frame_guidance.py` for a local dry-run check, including a path that can reuse the latest successful Nano Banana 2 artifact as the first frame.

## Kling 3.0 multi-shot shape

Kling 3.0 now supports the docs-aligned `multi_prompt` request shape in the runtime models.

Rules:
- `multi_prompt` is only valid when `options["multi_shots"]` is `True`
- each shot must include:
  - `prompt`
  - `duration`
- each shot duration must be between `1` and `12` seconds
- in image-to-video multi-shot mode, only a single first-frame image is allowed

Example:

```python
from kie_api import normalize_request, validate_request
from kie_api.models import RawUserRequest

request = RawUserRequest(
    model_key="kling-3.0-t2v",
    multi_prompt=[
        {"prompt": "wide establishing shot of the cockpit", "duration": 2},
        {"prompt": "closer reaction shot as the pilot studies the phone", "duration": 3},
    ],
    options={"duration": 5, "mode": "pro", "multi_shots": True},
)

normalized = normalize_request(request)
validation = validate_request(normalized)

print(validation.state)
print(validation.normalized_request.multi_prompt)
```

This is intentionally separate from the single-shot path:
- single-shot: use `prompt`
- multi-shot: use `multi_prompt` with `multi_shots=True`

Current limitation:
- `kling_elements` / element references from the official Kling 3.0 docs are not modeled in the runtime request types yet
- treat that as a documented TODO before relying on advanced element-reference workflows

Kling 2.6 note:
- the current official Kling 2.6 docs in `docs.kie.ai` show the simpler single-prompt text-to-video and image-to-video shapes
- this repo does not currently model Kling 2.6 as a multi-shot workflow

## Prompt presets and wrapper-side system prompts

Use `resolve_prompt_context()` when your wrapper needs the rendered preset text and resolved preset metadata before calling an external LLM skill.

```python
from kie_api import (
    apply_enhanced_prompt,
    build_submission_payload,
    dry_run_prompt_enhancement,
    normalize_request,
    resolve_prompt_context,
)
from kie_api.models import RawUserRequest

request = normalize_request(
    RawUserRequest(
        model_key="nano-banana-pro",
        prompt="make it more cinematic",
        enhance=True,
    ),
)

context = resolve_prompt_context(request)
print(context.model_dump())

# wrapper-side LLM call goes here
system_prompt = context.rendered_system_prompt or ""
enhanced_prompt = "cinematic portrait, elevated lighting, clean composition, preserve the subject"
updated_request = apply_enhanced_prompt(request, enhanced_prompt)
updated_validation = validate_request(updated_request)
payload = build_submission_payload(updated_validation)
print(payload["input"]["prompt"])

# deterministic local dry-run still exists
result = dry_run_prompt_enhancement(request)
print(result.model_dump())
```

Notes:
- `resolve_prompt_context(...)` tells the wrapper which preset was chosen, which input pattern was detected, and what rendered system prompt is in effect.
- `system_prompt_override` wins over profile markdown for one request.
- `build_submission_payload(...)` sends `final_prompt_used` first, then falls back to the raw prompt.
- if external enhancement changes the prompt text, re-run `validate_request(...)` before submission.

## Dry-run pricing and preflight

```python
from kie_api import estimate_request_cost, run_preflight
from kie_api.config import KieSettings
from kie_api.models import RawUserRequest

request = RawUserRequest(
    model_key="kling-3.0-t2v",
    prompt="A polished commercial shot of a product reveal.",
    options={"duration": 10, "mode": "pro", "sound": True},
)

estimate = estimate_request_cost(request)
preflight = run_preflight(
    request,
    settings=KieSettings(
        warn_credit_threshold=15,
        confirm_credit_threshold=25,
    ),
)

print(estimate.model_dump())
print(preflight.model_dump())
```

Notes:
- `estimate.has_numeric_estimate` means the library has a numeric planning estimate.
- `estimate.is_authoritative` and `estimate.is_known` should be treated as provider-billing truth flags.
- The default site-pricing snapshot can be numerically useful while still being non-authoritative.

## Optional live credit check

```python
from kie_api import get_credit_balance

balance = get_credit_balance()
print(balance.model_dump())
```

## Artifact bundles for completed runs

Use `create_run_artifact(...)` after outputs are downloaded locally.

```python
from kie_api import ArtifactSource, PromptRecord, ProviderTrace, RunArtifactCreateRequest, create_run_artifact

artifact = create_run_artifact(
    RunArtifactCreateRequest(
        status="succeeded",
        model_key="nano-banana-2",
        provider_model="nano-banana-2",
        prompts=PromptRecord(
            raw="Remove all elements around the man and make the background blue.",
            final_used="Remove all elements around the man and make the background blue.",
        ),
        inputs=[ArtifactSource(kind="image", role="reference", source_path="/absolute/path/to/input.jpg")],
        outputs=[ArtifactSource(kind="image", role="output", source_path="/absolute/path/to/output.jpg")],
        provider_trace=ProviderTrace(task_id="task_123"),
        tags=["portrait", "blue-bg"],
    )
)
print(artifact.run_dir)
```

## Artifact browsing and querying

Use the index-backed helpers for fast browsing:

```python
from kie_api import (
    get_latest_assets,
    get_latest_successful_run,
    get_run_summary,
    list_recent_runs,
    list_runs_by_model,
    rebuild_run_index,
)

print(list_recent_runs(limit=10))
print(list_runs_by_model("nano-banana-2", limit=5))
print(get_latest_successful_run())
print(get_latest_assets(model_key="nano-banana-pro"))

# If index.jsonl is missing or stale:
print(rebuild_run_index())

# For one run folder:
print(get_run_summary("/absolute/path/to/run_dir").model_dump())
```

Notes:
- query helpers prefer `outputs/index.jsonl`
- `get_run_summary(...)` reads `manifest.json`
- `load_run_artifact(...)` reads `run.json` when you need full detail

## Optional live smoke tests

Normal tests:
```bash
. .venv/bin/activate
python -m pytest
```

Optional live smoke tests:
```bash
export KIE_RUN_LIVE_SMOKE=1
export KIE_API_KEY="replace-me"
export KIE_SMOKE_UPLOAD_SOURCE_URL="https://example.com/image.png"
export KIE_SMOKE_ALLOW_SUBMIT=1
export KIE_SMOKE_SUBMIT_MODEL_KEY="nano-banana-2"
. .venv/bin/activate
python -m pytest tests/smoke -m smoke -rs
```

Notes:
- Smoke tests are skipped automatically when env vars are missing.
- Submit/status smoke tests can spend credits, so they require `KIE_SMOKE_ALLOW_SUBMIT=1`.
- These tests are opt-in and should not run in normal CI by default.

## What is not production-ready here
- No persistence
- No webhook receiver
- No retry orchestration
- No company auth or routing
- Some fields are still marked `inferred` or `unknown` in the specs
- The default pricing snapshot is live-observed site pricing, not a live-verified KIE billing contract
