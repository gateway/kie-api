# LLM Start Here

This file is the fastest way for another LLM, agent, or integration wrapper to understand how `kie-api` works end to end.

## What This Repo Is

`kie-api` is a Python workflow toolkit for working with [Kie.ai](https://kie.ai?ref=e7565cf24a7fad4586341a87eaf21e42).

It is not:
- a web app
- your Control API
- a dashboard
- a persistence layer

It is the reusable runtime layer that handles:
- Kie.ai model specs and validation
- prompt preset resolution
- upload-first media preparation
- task submission and polling
- output download
- local artifact/media bundle creation

## What Kie.ai Is

Kie.ai is a credit-based model marketplace for image and video models. Different models and options cost different amounts, so callers should validate requests and estimate cost before submitting paid runs.

Useful links:
- [Kie.ai](https://kie.ai?ref=e7565cf24a7fad4586341a87eaf21e42)
- [Kie.ai Market](https://kie.ai/market?ref=e7565cf24a7fad4586341a87eaf21e42)
- [Kie.ai Pricing](https://kie.ai/pricing?ref=e7565cf24a7fad4586341a87eaf21e42)

## First Setup

1. Create and activate the virtual environment.
2. Install the package in editable mode.
3. Put your Kie.ai key in `KIE_API_KEY`.
4. Check credits first.
5. Run a small Nano Banana test before trying more expensive video models.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env.live
set -a
source .env.live
set +a
python examples/check_credit_balance.py
```

## Core Request Lifecycle

This is the normal flow:

1. `normalize_request(...)`
2. `resolve_prompt_context(...)`
3. optional wrapper LLM prompt enhancement
4. `apply_enhanced_prompt(...)`
5. `validate_request(...)`
6. `prepare_request_for_submission(...)`
7. `submit_prepared_request(...)`
8. `wait_for_task(...)`
9. `download_output_file(...)`
10. `create_run_artifact(...)`

Important rules:
- always validate before submit
- always upload local or third-party media before final submit
- always poll by task id until terminal state
- always return the final media URL and local artifact paths

## Prompt Presets

Prompt presets are built into `kie-api`.

They are:
- model-aware
- mode-aware
- input-pattern-aware

Examples:
- Nano Banana prompt-only
- Nano Banana image-edit
- Kling text-to-video
- Kling first-frame image-to-video
- Kling first+last-frame image-to-video

The wrapper flow is:
1. call `resolve_prompt_context(...)`
2. read `rendered_system_prompt`
3. send that plus the raw user prompt to the wrapper LLM
4. get back the enhanced prompt
5. call `apply_enhanced_prompt(...)`

## First Safe Tests

### Test 1: Credits

Use:
- `examples/check_credit_balance.py`

This proves your API key is loaded and the system can talk to Kie.ai.

### Test 2: Nano Banana Prompt-Only

Use:
- `examples/live_run_guarded.py`

This is the safest first real generation path.

### Test 3: Nano Banana With Image Input

Read:
- `docs/UPLOAD_POLICY.md`
- `docs/LIBRARY_USAGE.md`

The important behavior is:
- validate input count and options first
- upload the image first
- submit using the uploaded media URL

### Test 4: Image To Video

Read:
- `docs/LIBRARY_USAGE.md`
- `docs/PRICING_AND_PREFLIGHT.md`

Use Kling carefully because video costs more and has more option-sensitive pricing.

## Media And Artifacts

Completed runs are stored as local artifact bundles.

Key files:
- `outputs/index.jsonl`
- per-run `manifest.json`
- per-run `run.json`

These are used for:
- browsing recent runs
- finding hero images and thumbs
- finding posters and web videos
- powering future dashboard/API retrieval

If you need gallery-style lookup, start with:
- `list_recent_runs(...)`
- `get_run_by_id(...)`
- `get_latest_successful_run(...)`
- `get_latest_assets(...)`

## Good First Docs To Read Next

1. [Getting Started](./GETTING_STARTED.md)
2. [Library Usage](./LIBRARY_USAGE.md)
3. [End-to-End Flow](./END_TO_END_FLOW.md)
4. [Prompt Wrapper Flow](./PROMPT_WRAPPER_FLOW.md)
5. [Prompt Profiles and Presets](./PROMPT_PROFILES.md)
6. [Upload Policy](./UPLOAD_POLICY.md)
7. [Pricing and Preflight](./PRICING_AND_PREFLIGHT.md)
8. [Run Artifacts](./RUN_ARTIFACTS.md)
9. [Artifact Querying](./ARTIFACT_QUERYING.md)
10. [Control API Integration](./CONTROL_API_INTEGRATION.md)
11. [Model Onboarding](./MODEL_ONBOARDING.md)

## Relevant Public APIs

Read and use these first:
- `normalize_request(...)`
- `resolve_prompt_context(...)`
- `apply_enhanced_prompt(...)`
- `validate_request(...)`
- `prepare_request_for_submission(...)`
- `build_submission_payload(...)`
- `submit_prepared_request(...)`
- `wait_for_task(...)`
- `download_output_file(...)`
- `create_run_artifact(...)`
- `list_recent_runs(...)`
- `get_run_by_id(...)`
- `get_latest_successful_run(...)`
- `get_latest_assets(...)`

## Recommended Mental Model

- `kie-api` owns the Kie.ai workflow rules
- your wrapper or Control API owns orchestration and persistence
- the dashboard should usually read from the Control API, not parse raw toolkit internals directly

## If You Are An LLM

Do this in order:
1. confirm `KIE_API_KEY` is configured
2. check credits
3. pick the model
4. resolve prompt context
5. validate before spending credits
6. upload media first if any are present
7. submit and store the task id
8. poll until complete
9. download the output
10. create a run artifact
11. return the remote URL, local file path, and artifact folder
