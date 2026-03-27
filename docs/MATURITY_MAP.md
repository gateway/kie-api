# Maturity Map

This is the blunt status map for the current `kie-api` package.

## Implemented and tested
- YAML-backed model registry loading
- Editable markdown-backed prompt profile loading and resolution
- Wrapper-facing prompt-context resolution and final-prompt application helpers
- Request normalization
- Structured validation with `ready`, `ready_with_defaults`, `ready_with_warning`, `needs_input`, and `invalid`
- Prompt enhancement policy wiring
- Versioned local pricing snapshots and dry-run preflight gating
- KIE credit-balance probe client with fallback endpoint support
- Callback signature verification helper for the currently documented HMAC scheme
- Bundled model-spec drift check script and test coverage
- Upload, submit, and status client abstractions
- Upload-first request preparation and trusted-host enforcement
- Wait/poll helper and output download helper
- Local run artifact bundles with copied originals, derivatives, metadata files, and append-only indexing
- Provider payload construction for the first-wave models
- Public helper surface: `normalize_request`, `validate_request`, `resolve_prompt_context`, `apply_enhanced_prompt`, `prepare_request_for_submission`, `build_submission_payload`, `submit_prepared_request`, `wait_for_task`, `download_output_file`, `dry_run_prompt_enhancement`, `estimate_request_cost`, `run_preflight`
- Reusable request fixtures for wrapper tests
- Bundled package-data fallback for specs and prompt profiles

## Implemented but still partly inferred
- Some model option defaults that are SDK defaults rather than verified provider defaults
- Kling 3.0 `sound` omission behavior
- Some transport assumptions derived from docs examples rather than live response captures
- Callback payload parsing is implemented, but not yet validated against a real signed callback capture
- The default pricing snapshot is live-observed site pricing, not observed billed-credit truth

## Scaffolding only
- Live smoke test scaffolding
- Retry-policy guidance and timeout structure
- Optional pricing refresh script and site-pricing capture scaffolding

## Not yet implemented
- Webhook receiver/server logic
- Persistence or job store
- Company-specific Control API routes
- Background orchestration
- Automatic retries
- Full multi-shot Kling 3.0 abstraction beyond the current core surface
- Cloud storage sync, deduplicated asset storage, or retention policy automation

## Requires a live API key to verify fully
- Upload endpoint behavior end-to-end for video and audio media
- Submit response payload shapes across all first-wave models
- Status response variants across all first-wave models
- Callback payload/signature behavior
- Temp upload URL lifetime and download URL behavior
- Real billed-credit behavior

## Explicit risk areas
- KIE docs and live pages still drift, so specs must keep provenance visible.
- The package is library-ready for local normalization, validation, prompt enhancement, preflight gating, and payload construction, but not production-platform-ready by itself.
- Installed-package spec loading is now supported, and bundled model-spec drift is now guarded by a sync script plus test coverage.
