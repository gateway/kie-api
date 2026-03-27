# Real API Integration Readiness

This checklist is the explicit gap list before wiring a real KIE API key into this package or a wrapper repo.

## Configuration and environment
- [x] `KIE_API_KEY`, base URLs, and path settings are configurable through `KieSettings`
- [x] Decide the final env contract for a wrapper repo and document which values are wrapper-owned versus package-owned
- [x] Harden `load_registry()` for non-editable installs or publish specs as package data

## Upload handling
- [x] Thin upload abstraction exists
- [x] Verify upload endpoint behavior end-to-end against a real KIE key for image uploads
- [ ] Confirm temp upload URL lifetime, expiry format, and whether KIE returns direct-download URLs consistently
- [x] Package policy now requires upload-first for all media before model submission
- [ ] Add retry and timeout policy for upload failures and transient network errors

## Submission and callbacks
- [x] Thin submit abstraction exists
- [x] Standalone callback signature verifier exists for the currently documented HMAC scheme
- [x] Verify live `createTask` response payloads for Nano Banana 2 with a real key
- [ ] Verify live `createTask` response payloads for the rest of the first-wave models with a real key
- [ ] Confirm callback payload shape and callback retry behavior from live runs
- [ ] Confirm the documented callback HMAC scheme against a real signed callback sample
- [ ] Decide how wrapper repos should deduplicate callback retries
- [ ] Confirm whether `callBackUrl` is honored uniformly across all supported KIE model families

## Polling and status
- [x] Thin status abstraction exists
- [x] Verify live `recordInfo` payload variants for Nano Banana 2 with a real key
- [ ] Verify live `recordInfo` payload variants with real tasks from the rest of the first-wave models
- [ ] Add wrapper-level polling fallback guidance when callbacks do not arrive
- [ ] Add retry policy and backoff recommendations for polling
- [ ] Confirm final result URL lifetime and whether outputs require authenticated download later

## Model-spec verification still missing
- [x] Re-verify Nano Banana Pro provider model string from an explicit docs or live JSON example
- [x] Re-verify Nano Banana 2 provider model string from an explicit docs or live JSON example
- [x] Confirm whether Kling 3.0 prompt is strictly required on text-to-video and image-to-video, or just present in the UI
- [ ] Confirm whether Kling 3.0 `sound` has a provider default when omitted
- [x] Confirm whether Kling 2.6 `sound` must always be sent explicitly or if the provider accepts omission with a default
- [x] Confirm whether Kling 3.0 Motion Control exposes `background_source` in docs even when it does not appear on the current live page API surface

## Pricing and credits
- [x] Pricing registry and credit guard abstraction exist
- [x] Public site pricing-page API discovered and mapped into a non-authoritative snapshot
- [x] Credit balance probe client exists with fallback endpoint support
- [x] Verify the credit endpoint shape against a real key in this environment
- [ ] Verify machine-usable pricing for each first-wave model against billed usage before enforcing hard credit checks
- [ ] Confirm whether pricing varies by duration, mode, audio, or resolution in ways not yet modeled
- [ ] Confirm whether KIE exposes billed credits in submit or status responses

## Validation and transport behavior
- [x] Structured validation result states exist
- [x] Add live submit/validate smoke tests once a real API key is available
- [ ] Confirm whether KIE rejects omitted optional fields exactly as modeled here
- [ ] Confirm whether capitalization-sensitive enum values ever differ from the live page expected fields lists

## Explicitly not production-ready yet
- The package does not implement webhook receivers, retry orchestration, persistence, or job state storage.
- The pricing layer is still intentionally non-authoritative even when it has numeric estimates.
- Some spec fields remain `inferred` or `unknown`; these are visible in the YAML and should not be treated as provider facts.
- The current tests verify normalization, validation, and payload shape locally, not end-to-end provider execution.
- Optional live smoke tests exist, but they are opt-in scaffolding and do not run by default in normal local or CI workflows.
