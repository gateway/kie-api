# Integration Playbook

This document explains how to integrate `kie-api` into another system such as a Control API, worker, agent runtime, or internal orchestration service.

## Purpose

Use this file when you want to wire `kie-api` into another codebase without reimplementing its internals.

`kie-api` should remain the heavy-lifting library for:
- model specs
- validation
- prompt preset resolution
- upload-first handling
- Kie.ai submission and polling
- output download
- artifact/media bundling

Your integrating system should stay thin and focus on:
- credentials
- request routing
- persistence
- background orchestration
- dashboard-facing API responses

## System Boundary

### `kie-api` owns

- model capability definitions
- prompt preset resources
- request normalization and validation
- pricing estimation and preflight
- upload-first preparation
- provider payload construction
- submit and status polling helpers
- output download
- artifact bundle creation
- artifact query/index helpers

### Your Control API or wrapper owns

- reading secrets from env/config
- deciding which model to use
- deciding whether to run prompt enhancement
- persisting run/task state
- exposing API endpoints for UI/dashboard use
- retries, orchestration, and scheduling

## Recommended Read Order

Start with:
1. [LLM Start Here](./LLM_START_HERE.md)
2. [Getting Started](./GETTING_STARTED.md)
3. [Configuration](./CONFIGURATION.md)
4. [Library Usage](./LIBRARY_USAGE.md)
5. [End-to-End Flow](./END_TO_END_FLOW.md)
6. [Prompt Wrapper Flow](./PROMPT_WRAPPER_FLOW.md)
7. [Prompt Profiles and Presets](./PROMPT_PROFILES.md)
8. [Upload Policy](./UPLOAD_POLICY.md)
9. [Pricing and Preflight](./PRICING_AND_PREFLIGHT.md)
10. [Run Artifacts](./RUN_ARTIFACTS.md)
11. [Artifact Querying](./ARTIFACT_QUERYING.md)
12. [Control API Integration](./CONTROL_API_INTEGRATION.md)

## Installation Into Another Repo

Recommended options:
- local editable dependency
- git submodule
- vendored library folder only if your repo already uses that pattern

Prefer whichever matches the target repo’s current workflow. Do not invent a separate architecture if the host repo already has a clear dependency strategy.

## Minimum Working Integration

Your integration should support this lifecycle:

1. Read `KIE_API_KEY`
2. Check credit balance
3. Normalize request
4. Resolve prompt preset/context
5. Optionally enhance prompt with your wrapper LLM
6. Validate request
7. Upload any local or third-party input media
8. Submit generation request
9. Persist task id
10. Poll by task id until success or failure
11. Download final outputs
12. Create run artifact bundle
13. Expose run metadata for dashboard/media browsing

## Prompt Preset Integration

Prompt presets are one of the key pieces to preserve.

What `kie-api` already provides:
- built-in preset resources
- request-shape-aware preset resolution
- rendered system prompt text
- a place to store the final enhanced prompt

What your wrapper should do:
1. call `resolve_prompt_context(...)`
2. read:
   - raw prompt
   - resolved preset key
   - rendered system prompt
   - input pattern
3. send the rendered system prompt and raw prompt to your LLM
4. receive the enhanced prompt
5. call `apply_enhanced_prompt(...)`
6. continue with validation and submission

Store this prompt lineage if possible:
- raw prompt
- preset key
- rendered system prompt
- enhanced prompt
- final prompt used

## Upload-First Rule

Your integration should not send local file paths or arbitrary external media URLs directly into Kie.ai model submit payloads.

Always:
- validate first
- upload first
- submit using uploaded media URLs

This is one of the core invariants of the toolkit.

## Task Completion Model

Kie.ai generation is asynchronous.

Normal pattern:
- submit -> get task id
- poll -> waiting / queued / success / fail
- when success:
  - read output URLs
  - download output locally
  - build artifact bundle

Your integrating system should treat the task id as resumable state, not just transient runtime data.

## Media And Dashboard Strategy

The first-pass local media library is already built:
- `outputs/index.jsonl`
- run `manifest.json`
- run `run.json`

This data is enough for a dashboard or Control API to show:
- recent runs
- hero images
- thumbs
- posters
- prompt summary
- status
- model used
- artifact folder location

Recommended Control API behavior:
- expose recent runs from the artifact index/query layer
- expose single-run detail from manifest or run metadata
- only load full `run.json` when detailed inspection is needed

## Useful Functions

Use these first:
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

## Good First Integration Tests

1. Credit check returns a valid number
2. Nano Banana prompt-only dry run validates
3. Nano Banana image-edit dry run validates
4. Prompt preset resolution returns a rendered system prompt
5. Upload-first path rewrites media to uploaded URLs
6. Submit returns task id
7. Polling by task id reaches terminal state
8. Download saves the output locally
9. Artifact bundle is created
10. Artifact query helper returns the new run for gallery use

## What Not To Duplicate

Do not duplicate:
- model option lists
- input count rules
- upload-first logic
- prompt preset rendering
- artifact manifest logic
- pricing parsing

If `kie-api` already owns it, your integration should call it rather than reimplement it.

## Suggested Outcome

A good integration should make it possible for another team or LLM to answer:
- is the key working?
- do we have enough credits?
- is this request valid?
- what preset should be used?
- what inputs must be uploaded?
- what task id was created?
- is the run complete?
- where is the final media?
- what artifact bundle should the dashboard read?
