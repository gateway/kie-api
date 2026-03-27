# KIE API Python Toolkit

`kie-api` is a Python toolkit for working with [KIE.AI](https://kie.ai?ref=e7565cf24a7fad4586341a87eaf21e42).

## What is KIE.AI?

KIE.AI is a marketplace-style API platform for creative AI models. Instead of one model or one workflow, it gives you access to multiple image and video models behind one account and one API key.

Examples of model families currently covered by this repo:
- Nano Banana 2
- Nano Banana Pro
- Kling 2.6 text-to-video
- Kling 2.6 image-to-video
- Kling 3.0 text-to-video
- Kling 3.0 image-to-video
- Kling 3.0 motion control

KIE uses a credit-based model, so different models and modes cost different amounts. This repo is built to help you avoid blind API calls by checking credits, validating inputs, and preparing media safely before generation.

Useful links:
- [KIE.AI](https://kie.ai?ref=e7565cf24a7fad4586341a87eaf21e42)
- [KIE Market](https://kie.ai/market?ref=e7565cf24a7fad4586341a87eaf21e42)
- [KIE Pricing](https://kie.ai/pricing?ref=e7565cf24a7fad4586341a87eaf21e42)

## What this repo does

This repo gives you a reusable Python layer for:
- validating model-aware requests before they spend credits
- uploading images, video, and audio before generation
- building KIE payloads with model-specific rules
- resolving prompt presets for different models and request shapes
- polling tasks and downloading final outputs
- storing completed runs as local artifact bundles with web/thumb derivatives

It is meant for developers who want to work with KIE directly, or use a clean Python library inside a larger app.

## Example workflows

### 1. Simple image generation

Use `nano-banana-2` with a prompt only:
- check credits
- submit a prompt-only image request
- wait for completion
- download the image
- store the result under `outputs/`

### 2. Image edit

Use `nano-banana-pro` or `nano-banana-2` with one or more reference images:
- validate image count first
- upload the images
- submit the prompt plus uploaded image URLs
- download the final image

### 3. Image to video

Use `kling-3.0-i2v` with one image:
- create or choose a source image
- upload the image first
- submit a Kling prompt with the uploaded first-frame image
- wait for the video task
- download the final video and poster/artifacts

### 4. Chained run

Use one model’s output as another model’s input:
- generate an image with Nano Banana
- download and store it
- feed that image into Kling 3.0 image-to-video
- store both runs and link them through artifacts

## First live proof path

The easiest way to prove your setup works is:
1. load your key
2. check remaining credits
3. run one simple Nano Banana image generation

Credit check:

```bash
. .venv/bin/activate
set -a
source .env.live
set +a
python examples/check_credit_balance.py
```

Then run the guarded live example:

```bash
python examples/live_run_guarded.py
```

The credit check is the simplest “system is connected” test. After that, the Nano Banana live example is the safest first generation test.

## Supporting development

If you are already planning to use KIE.AI, using the links above is one way to support ongoing maintenance of this repo. There is no obligation, and the library works the same regardless.

## Quick start

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
cp .env.example .env.live
```

Edit `.env.live`, then load it when you want to run live KIE calls:

```bash
set -a
source .env.live
set +a
```

Run the local suite:

```bash
python -m pytest
python scripts/sync_packaged_specs.py --check
```

Start with:
- [Getting started](docs/GETTING_STARTED.md)
- [Configuration](docs/CONFIGURATION.md)
- [Library usage](docs/LIBRARY_USAGE.md)
- [End-to-end flow](docs/END_TO_END_FLOW.md)

## API key and secrets

- Your KIE key belongs in `KIE_API_KEY`.
- Do not hardcode it in Python.
- Do not commit `.env.live`.
- Use the tracked [`.env.example`](/Users/evilone/Documents/Development/Video-Image-APIs/kie-ai/kie_codex_bootstrap/.env.example) as the local template.
- The repo ignores local env files so your personal key stays out of Git.

## What it includes
- explicit YAML model specs
- editable markdown-backed prompt presets
- field-level provenance for current model facts
- example image and video flows that have already been tested live
- typed normalization, validation, upload, submit, status, pricing, and credit models
- local run artifact bundles with derivatives and append-only indexing
- artifact query helpers for recent runs, filters, and latest assets
- thin KIE client abstractions
- public helper surface for wrapper repos
- reusable request fixtures
- versioned pricing snapshots and dry-run preflight gating
- callback signature verification helper and credit balance probe
- packaged model-spec drift guard
- optional live smoke-test scaffolding

## What it does not include
- FastAPI routes
- persistence or a job database
- company auth
- webhook server implementation
- Slack, Discord, or Telegram delivery
- hardcoded secrets

## Source of truth order
1. live `kie.ai` model page
2. the page Playground
3. the page API surface
4. `docs.kie.ai` as a secondary check

When docs and live pages disagree, the live page wins and the mismatch is recorded in the spec `verification_notes`.

## Install
```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Public usage
Upload-first is the default library contract. Any input image, video, or audio must be uploaded through `prepare_request_for_submission(...)` before payload build or submission.

```python
from kie_api import (
    ArtifactDerivativeSettings,
    apply_enhanced_prompt,
    build_submission_payload,
    create_run_artifact,
    download_output_file,
    dry_run_prompt_enhancement,
    estimate_request_cost,
    get_latest_assets,
    normalize_request,
    prepare_request_for_submission,
    resolve_prompt_context,
    run_preflight,
    submit_prepared_request,
    validate_request,
    wait_for_task,
    ArtifactSource,
    PromptRecord,
    ProviderTrace,
    RunArtifactCreateRequest,
)
from kie_api.config import KieSettings
from kie_api.models import RawUserRequest

request = RawUserRequest(
    model_key="kling-3.0",
    prompt="A cinematic reveal shot.",
    images=["/absolute/path/to/start.png"],
    options={"duration": 5, "mode": "pro"},
)

normalized = normalize_request(request)
validation = validate_request(normalized)
prompt_context = resolve_prompt_context(normalized)
enhancement = dry_run_prompt_enhancement(normalized)
estimate = estimate_request_cost(normalized)
preflight = run_preflight(normalized)

if validation.state in {"ready", "ready_with_defaults", "ready_with_warning"}:
    settings = KieSettings(api_key="replace-me")
    final_request = apply_enhanced_prompt(
        normalized,
        enhancement.final_prompt_used or normalized.prompt or "",
        enhanced_prompt=enhancement.enhanced_prompt,
    )
    final_validation = validate_request(final_request)
    prepared = prepare_request_for_submission(final_validation, settings=settings)
    payload = build_submission_payload(prepared, settings=settings)
    submission = submit_prepared_request(prepared, settings=settings)
    wait_result = wait_for_task(submission.task_id, settings=settings)
    print(payload)
    print(wait_result.model_dump())
    if wait_result.final_status and wait_result.final_status.output_urls:
        download = download_output_file(
            wait_result.final_status.output_urls[0],
            "/absolute/path/to/output.bin",
            settings=settings,
        )
        print(download.model_dump())
        artifact = create_run_artifact(
            RunArtifactCreateRequest(
                status="succeeded",
                model_key=request.model_key or normalized.model_key,
                provider_model=normalized.provider_model,
                task_mode=normalized.task_mode,
                prompts=PromptRecord(
                    raw=normalized.raw_prompt,
                    enhanced=normalized.enhanced_prompt,
                    final_used=normalized.final_prompt_used,
                ),
                inputs=[
                    ArtifactSource(
                        kind="image",
                        role="reference",
                        source_path="/absolute/path/to/start.png",
                    )
                ],
                outputs=[
                    ArtifactSource(
                        kind="image",
                        role="output",
                        source_path=download.destination_path,
                    )
                ],
                provider_trace=ProviderTrace(task_id=submission.task_id),
            )
        )
        print(artifact.run_dir)
else:
    print(validation.model_dump())

print(prompt_context.model_dump())
print(enhancement.model_dump())
print(estimate.model_dump())
print(preflight.model_dump())
```

Wrapper-side prompt flow:
- `resolve_prompt_context(...)` loads the model default or requested prompt preset, detects the input pattern, and renders the effective system prompt
- `apply_enhanced_prompt(...)` sets `final_prompt_used` after your own LLM skill enhances the user prompt
- re-run `validate_request(...)` after external enhancement if the prompt text changed
- `build_submission_payload(...)` sends `final_prompt_used` first

## Validation states
- `ready`
- `ready_with_defaults`
- `ready_with_warning`
- `needs_input`
- `invalid`

Structured validation details include:
- `missing_inputs`
- `defaulted_fields`
- `warning_details`
- `impossible_inputs`

## Specs and packaging
`load_registry()` prefers the repo-local `specs/` tree for model specs during development and falls back to bundled package data when installed as a library.

Prompt presets and pricing snapshots are authored directly inside package resources:
- `src/kie_api/resources/prompt_profiles/`
- `src/kie_api/resources/pricing/`

Current default pricing snapshot:
- `src/kie_api/resources/pricing/2026-03-26_site_pricing_page.yaml`

Refresh a candidate snapshot from KIE's public site pricing API:

```bash
. .venv/bin/activate
python scripts/refresh_site_pricing_snapshot.py --output /tmp/kie-site-pricing.yaml
```

Bundled model specs can be checked or synced with:

```bash
python scripts/sync_packaged_specs.py --check
python scripts/sync_packaged_specs.py
```

## Reusable fixtures
The package exports request fixtures for integration tests:
```python
from kie_api import REQUEST_FIXTURES, get_request_fixture

fixture = get_request_fixture("kling_3_motion_missing_video")
print(fixture.request.model_dump())
```

## Examples
- `examples/check_credit_balance.py`
- `examples/normalize_and_validate.py`
- `examples/build_submission_payload.py`
- `examples/dry_run_with_prompt_enhancement.py`
- `examples/dry_run_kling_frame_guidance.py`
- `examples/wrapper_prompt_flow.py`
- `examples/dry_run_cost_estimate.py`
- `examples/dry_run_preflight_gate.py`
- `examples/run_request_fixtures.py`
- `examples/live_run_guarded.py`
- `examples/create_image_run_artifact.py`
- `examples/create_video_run_artifact.py`
- `examples/generate_derivatives_for_originals.py`
- `examples/append_run_index.py`
- `examples/query_artifact_runs.py`
- `examples/rebuild_artifact_index.py`
- `examples/create_artifact_with_custom_settings.py`
- `examples/print_run_summary.py`

## Tests
Normal local test suite:
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

## Docs
- [Getting started](docs/GETTING_STARTED.md)
- [Library usage](docs/LIBRARY_USAGE.md)
- [End-to-end flow](docs/END_TO_END_FLOW.md)
- [Configuration](docs/CONFIGURATION.md)
- [Upload policy](docs/UPLOAD_POLICY.md)
- [Prompt wrapper flow](docs/PROMPT_WRAPPER_FLOW.md)
- [Run artifacts](docs/RUN_ARTIFACTS.md)
- [Derivatives](docs/DERIVATIVES.md)
- [Artifact indexing](docs/ARTIFACT_INDEXING.md)
- [Artifact querying](docs/ARTIFACT_QUERYING.md)
- [Prompt profiles](docs/PROMPT_PROFILES.md)
- [Model onboarding](docs/MODEL_ONBOARDING.md)
- [Pricing and preflight](docs/PRICING_AND_PREFLIGHT.md)
- [Live verification report](docs/LIVE_VERIFICATION_REPORT.md)
- [Control API integration](docs/CONTROL_API_INTEGRATION.md)
- [Real API integration readiness](docs/REAL_API_INTEGRATION_READINESS.md)
- [Maturity map](docs/MATURITY_MAP.md)

## Current readiness
- Library-ready for spec loading, normalization, validation, prompt preset editing, dry-run enhancement, pricing estimation, preflight gating, payload construction, and local testing
- Not production-platform-ready on its own for persistence, retries, webhook serving, or full live operational guarantees

Pricing note:
- `estimate_request_cost(...)` may return a numeric planning estimate with `has_numeric_estimate=true` while `is_known=false` when the source is KIE's public site pricing page rather than verified provider billing.

## License

This repo is licensed under the MIT License. See [LICENSE](/Users/evilone/Documents/Development/Video-Image-APIs/kie-ai/kie_codex_bootstrap/LICENSE).
