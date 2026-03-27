# KIE API Build Changelog

This log is append-only. Each entry records one completed slice with:
- date
- slice name
- summary
- files added or updated
- tests run
- live sources checked
- mismatches or open uncertainties

## 2026-03-25 — Slice 1: Tracking docs and package skeleton
- Summary: Added the planning tracker, package build config, `.gitignore`, editable install metadata, and the base `src/kie_api` package layout.
- Files: `pyproject.toml`, `.gitignore`, `docs/planning/IMPLEMENTATION_PLAN.md`, `docs/planning/TASKS.md`, `docs/planning/CHANGELOG.md`, `src/kie_api/__init__.py`, `src/kie_api/config.py`.
- Tests run: none before the first code slice was in place.
- Live sources checked: `https://kie.ai/nano-banana-pro`, `https://kie.ai/nano-banana-2`, `https://kie.ai/kling-2-6`, `https://kie.ai/kling-3-0`, `https://kie.ai/kling-3-motion-control`.
- Notes: Built around Python 3.9 compatibility after confirming the current local interpreter is Python 3.9.6.

## 2026-03-25 — Slice 2: Typed domain models
- Summary: Added shared enums, exceptions, and runtime models for raw requests, normalized requests, validation results, prompt enhancement results, upload results, submission results, status results, and cost guards.
- Files: `src/kie_api/enums.py`, `src/kie_api/exceptions.py`, `src/kie_api/models.py`, `src/kie_api/__init__.py`.
- Tests run: covered indirectly by the first registry import and loader tests.
- Live sources checked: same live model pages as the initial harvest pass.
- Notes: Media references accept either local paths or remote URLs and preserve source provenance for later upload handling.

## 2026-03-25 — Slice 3: Registry loader
- Summary: Added typed schema models for model specs and prompt profiles plus a YAML-backed registry loader with explicit malformed-spec handling.
- Files: `src/kie_api/registry/models.py`, `src/kie_api/registry/loader.py`, `src/kie_api/registry/__init__.py`, `tests/test_registry_loader.py`.
- Tests run: `. .venv/bin/activate && python -m pytest tests/test_registry_loader.py` — passed (4 tests).
- Live sources checked: live KIE model pages plus `docs.kie.ai` as a secondary source for provider model strings where the live page did not expose a full JSON request example.
- Notes: The first test run exposed Python 3.9 union-typing incompatibility and was corrected by replacing `|` unions with `Optional[...]` in runtime settings.

## 2026-03-25 — Slice 4: Live spec harvest and correction
- Summary: Corrected the first-wave YAML model specs from live `kie.ai` model pages and split Kling 3.0 into explicit text-to-video and image-to-video specs.
- Files: `specs/models/nano_banana_pro.yaml`, `specs/models/nano_banana_2.yaml`, `specs/models/kling_2_6_t2v.yaml`, `specs/models/kling_2_6_i2v.yaml`, `specs/models/kling_3_0_t2v.yaml`, `specs/models/kling_3_0_i2v.yaml`, `specs/models/kling_3_0_motion.yaml`, `specs/prompt_profiles/kling_video_v1.yaml`.
- Tests run: `. .venv/bin/activate && python -m pytest tests/test_registry_loader.py` — passed (4 tests).
- Live sources checked: `https://kie.ai/nano-banana-pro`, `https://kie.ai/nano-banana-2`, `https://kie.ai/kling-2-6`, `https://kie.ai/kling-3-0`, `https://kie.ai/kling-3-motion-control`.
- Mismatches and uncertainties:
  - Nano Banana Pro was seeded as image-edit only, but the live page shows prompt-first generation with optional `image_input`.
  - Kling 3.0 Motion Control live page shows `720p` and `1080p` values for `mode`, while docs still mention `std` and `pro`.
  - Kling 3.0 Motion Control live page shows minimum size greater than 300px, while docs mention greater than 340px.
  - `background_source` appears in docs for Kling 3.0 Motion Control but was not visible on the live page API surface, so it remains intentionally unmapped.

## 2026-03-25 — Slice 5: Normalizer
- Summary: Added request normalization that resolves explicit model variants, infers safe task modes, normalizes option keys and primitive values, and applies only verified defaults from the model specs.
- Files: `src/kie_api/services/normalizer.py`, `tests/test_normalizer.py`.
- Tests run: `. .venv/bin/activate && python -m pytest tests/test_registry_loader.py tests/test_normalizer.py tests/test_validator.py` — passed (14 tests).
- Live sources checked: the same first-wave live model pages harvested earlier.
- Notes: Generic `kling-2.6` and `kling-3.0` family keys now normalize to explicit text-to-video or image-to-video specs when the input shape makes that inference safe.

## 2026-03-25 — Slice 6: Validator
- Summary: Added request validation with structured `needs_input` results for recoverable gaps and explicit invalid errors for impossible combinations.
- Files: `src/kie_api/services/validator.py`, `tests/test_validator.py`.
- Tests run: `. .venv/bin/activate && python -m pytest tests/test_registry_loader.py tests/test_normalizer.py tests/test_validator.py` — passed (14 tests).
- Live sources checked: the same first-wave live model pages harvested earlier, especially the Kling 3.0 motion-control API surface.
- Notes:
  - Kling 3.0 motion correctly returns `needs_input` when either the image or motion video is missing.
  - Kling 3.0 motion accepts docs-style `std` and `pro` aliases and maps them to the live `720p` and `1080p` values.
  - Kling image-to-video treats aspect ratio as inferable from image inputs when the spec marks it safe.

## 2026-03-25 — Slice 7: Upload client
- Summary: Added a thin upload abstraction with URL and file-stream methods plus normalized `UploadResult` parsing.
- Files: `src/kie_api/clients/upload.py`, `src/kie_api/clients/__init__.py`, `tests/test_upload_client.py`.
- Tests run: `. .venv/bin/activate && python -m pytest tests/test_registry_loader.py tests/test_normalizer.py tests/test_validator.py tests/test_upload_client.py tests/test_submit_client.py tests/test_status_client.py` — passed (23 tests).
- Live sources checked: model live pages for upload-required models, plus `docs.kie.ai/file-upload-api/quickstart` as a secondary upload reference.
- Notes: Upload endpoint paths remain configurable because the upload quickstart is a docs-only source and not mirrored on the main model pages.

## 2026-03-25 — Slice 8: Submit client
- Summary: Added provider payload construction and a thin task submitter that isolates KIE field mapping from the rest of the package.
- Files: `src/kie_api/clients/submit.py`, `tests/test_submit_client.py`.
- Tests run: `. .venv/bin/activate && python -m pytest tests/test_registry_loader.py tests/test_normalizer.py tests/test_validator.py tests/test_upload_client.py tests/test_submit_client.py tests/test_status_client.py` — passed (23 tests).
- Live sources checked: the first-wave live model pages, especially the live form fields for Nano Banana, Kling 3.0, and Kling 3.0 Motion Control.
- Notes: The submit client intentionally maps internal normalized media collections to provider field names such as `image_input`, `image_urls`, `input_urls`, and `video_urls`.

## 2026-03-25 — Slice 9: Status client
- Summary: Added a status checker that normalizes provider status values into stable internal job states while preserving raw response payloads.
- Files: `src/kie_api/clients/status.py`, `tests/test_status_client.py`.
- Tests run: `. .venv/bin/activate && python -m pytest tests/test_registry_loader.py tests/test_normalizer.py tests/test_validator.py tests/test_upload_client.py tests/test_submit_client.py tests/test_status_client.py` — passed (23 tests).
- Live sources checked: live KIE model pages for callback/status workflow references, plus `docs.kie.ai/market/common/get-task-detail` as a secondary status reference.
- Notes: The status normalizer accepts waiting, queueing, generating, success, and fail variants because KIE status labels differ across docs and models.

## 2026-03-25 — Slice 10: Prompt enhancement
- Summary: Added a prompt enhancement framework with `OFF`, `ASK`, `AUTO`, and `PREVIEW` policies plus prompt-profile resolution per model.
- Files: `src/kie_api/services/prompt_enhancer.py`, `src/kie_api/services/__init__.py`, `tests/test_prompt_enhancer.py`.
- Tests run: `. .venv/bin/activate && python -m pytest` — passed (29 tests).
- Live sources checked: prompt-profile mappings were kept aligned to the corrected live-harvested model keys.
- Notes: Prompt enhancement is intentionally decoupled from upload and transport code; the default fallback is deterministic whitespace cleanup unless an upstream enhancement backend is injected.

## 2026-03-25 — Slice 11: Pricing and credit guard
- Summary: Added an explicit pricing registry abstraction plus a credit-guard decision helper that can allow, warn, require confirmation, or reject.
- Files: `src/kie_api/services/pricing.py`, `src/kie_api/services/credit_guard.py`, `tests/test_pricing_and_credit_guard.py`.
- Tests run: `. .venv/bin/activate && python -m pytest` — passed (29 tests).
- Live sources checked: live model pages were reviewed for pricing hints, but no machine-verifiable pricing contract was harvested from the page API surfaces.
- Notes: Unknown pricing remains unknown by design; the SDK warns instead of inventing costs.

## 2026-03-25 — Slice 12: Examples and integration docs
- Summary: Added local examples, rewrote the repo README around the actual package, and documented the intended Control API wrapper contract.
- Files: `examples/normalize_and_validate.py`, `examples/build_submission_payload.py`, `docs/CONTROL_API_INTEGRATION.md`, `README.md`.
- Tests run: `. .venv/bin/activate && python -m pytest` — passed (29 tests).
- Live sources checked: no additional live harvest beyond the model verification pass.
- Notes: The examples avoid real API keys and demonstrate local normalization, validation, and payload-building only.

## 2026-03-25 — Slice 13: Final test sweep and polish
- Summary: Ran the full suite in the repo-local virtualenv and closed out the tracker so the plan, task status, and implemented surface match.
- Files: `docs/planning/TASKS.md`, `docs/planning/CHANGELOG.md`.
- Tests run: `. .venv/bin/activate && python -m pytest` — passed (29 tests).
- Live sources checked: no new live harvest; this was a validation and bookkeeping pass.
- Notes: The repo is now ready for the next pass of live-field verification or upstream Control API integration work.

## 2026-03-25 — Slice 14: Second-pass hardening and live-verification audit
- Summary: Added field-level provenance to the current first-wave model specs, tightened validation states and result detail structures, added reusable request fixtures, widened payload verification coverage, improved the public package surface, and expanded wrapper/readiness docs.
- Files: `specs/models/*.yaml`, `src/kie_api/enums.py`, `src/kie_api/models.py`, `src/kie_api/api.py`, `src/kie_api/fixtures.py`, `src/kie_api/registry/models.py`, `src/kie_api/services/normalizer.py`, `src/kie_api/services/validator.py`, `src/kie_api/__init__.py`, `tests/test_registry_loader.py`, `tests/test_normalizer.py`, `tests/test_validator.py`, `tests/test_submit_client.py`, `tests/test_request_fixtures.py`, `tests/test_public_api.py`, `examples/normalize_and_validate.py`, `examples/build_submission_payload.py`, `examples/run_request_fixtures.py`, `README.md`, `docs/CONTROL_API_INTEGRATION.md`, `docs/REAL_API_INTEGRATION_READINESS.md`, `docs/planning/IMPLEMENTATION_PLAN.md`, `docs/planning/TASKS.md`.
- Tests run: `. .venv/bin/activate && python -m pytest` — passed (41 tests).
- Live sources checked: `https://kie.ai/nano-banana-pro`, `https://kie.ai/nano-banana-2`, `https://kie.ai/kling-2-6`, `https://kie.ai/kling-3-0`, `https://kie.ai/kling-3-motion-control`.
- Mismatches and uncertainties:
  - Nano Banana provider model strings still match the live slugs, but explicit docs-side request examples were not re-verified in this pass, so those remain `inferred`.
  - Kling 3.0 Motion Control live expected fields use `720p` and `1080p`, while docs-side examples still describe `std` and `pro`; the SDK accepts `std` and `pro` as aliases but emits the live values.
  - Kling 3.0 prompt-required behavior remains partially inferred because the live page clearly exposes the prompt field and max length, but the hard-required constraint was not visible as consistently as it was on some other models.
  - `load_registry()` still assumes the repo-local `specs/` tree, which is acceptable for editable installs but should be hardened before publishing a wheel.

## 2026-03-25 — Slice 15: Third-pass packaging and real-API readiness
- Summary: Hardened the package for installed-library use, separated provider adapters from transport code, improved environment handling, reduced remaining model unknowns with another live/docs verification pass, added callback and smoke-test scaffolding, and expanded external-use documentation.
- Files: `pyproject.toml`, `src/kie_api/config.py`, `src/kie_api/registry/loader.py`, `src/kie_api/exceptions.py`, `src/kie_api/models.py`, `src/kie_api/__init__.py`, `src/kie_api/adapters/__init__.py`, `src/kie_api/adapters/market.py`, `src/kie_api/clients/upload.py`, `src/kie_api/clients/submit.py`, `src/kie_api/clients/status.py`, `src/kie_api/clients/callbacks.py`, `src/kie_api/clients/__init__.py`, `src/kie_api/py.typed`, `src/kie_api/resources/specs/models/*.yaml`, `src/kie_api/resources/specs/prompt_profiles/*.yaml`, `specs/models/*.yaml`, `tests/test_config.py`, `tests/test_callbacks.py`, `tests/test_registry_loader.py`, `tests/test_submit_client.py`, `tests/test_upload_client.py`, `tests/smoke/test_live_api_smoke.py`, `README.md`, `docs/CONFIGURATION.md`, `docs/LIBRARY_USAGE.md`, `docs/MATURITY_MAP.md`, `docs/CONTROL_API_INTEGRATION.md`, `docs/REAL_API_INTEGRATION_READINESS.md`, `docs/planning/IMPLEMENTATION_PLAN.md`, `docs/planning/TASKS.md`.
- Tests run: `. .venv/bin/activate && python -m pytest` — passed (47 tests), skipped (3 smoke tests without env).
- Live sources checked: `https://kie.ai/nano-banana-pro`, `https://kie.ai/nano-banana-2`, `https://kie.ai/kling-2-6`, `https://kie.ai/kling-3-0`, `https://kie.ai/kling-3-motion-control`.
- Docs sources checked: `https://docs.kie.ai/market/google/nano-banana-2`, `https://docs.kie.ai/market/google/nano-banana-pro`, `https://docs.kie.ai/market/kling/kling-3.0`, `https://docs.kie.ai/market/kling/image-to-video`, `https://docs.kie.ai/market/kling/text-to-video`, `https://docs.kie.ai/market/kling/motion-control-v3`.
- Duplication check:
  - Provider payload and response normalization now exists in a single adapter path under `src/kie_api/adapters/market.py`.
  - The only intentional duplication is the bundled spec mirror under `src/kie_api/resources/specs/`, which exists to support installed-package loading and is documented as a packaging tradeoff.
- Newly verified:
  - Nano Banana Pro provider model string `nano-banana-pro` from docs-side request examples.
  - Nano Banana 2 provider model string `nano-banana-2` from docs-side request examples.
  - Kling 3.0 prompt is live-required on the current live page surface.
  - Kling 2.6 prompt and `sound` are live-required in both text-to-video and image-to-video.
  - Kling 3.0 motion `background_source` exists in docs-side request examples, even though it is not visible on the live page surface.
- Remaining uncertainties:
  - Kling 3.0 single-shot `sound` omission/default behavior remains unverified; the live page shows it enabled in the UI, but that does not prove the provider default when omitted.
  - Installed-package spec loading now works, but the bundled spec mirror must stay synchronized with the repo authoring tree.

## 2026-03-25 — Slice 16: Fourth-pass local dry-run prompt profiles and pricing preflight
- Summary: Reworked prompt profiles into editable package-resource folders with markdown bodies, added default profile-key resolution in model specs, introduced versioned local pricing snapshots, and added a dry-run preflight gate that estimates cost and can warn or require confirmation without any live secrets.
- Files: `src/kie_api/registry/models.py`, `src/kie_api/registry/loader.py`, `src/kie_api/models.py`, `src/kie_api/api.py`, `src/kie_api/config.py`, `src/kie_api/services/prompt_enhancer.py`, `src/kie_api/services/pricing.py`, `src/kie_api/services/preflight.py`, `src/kie_api/services/credit_guard.py`, `src/kie_api/services/pricing_refresh.py`, `src/kie_api/services/__init__.py`, `src/kie_api/resources/prompt_profiles/*/metadata.yaml`, `src/kie_api/resources/prompt_profiles/*/prompt.md`, `src/kie_api/resources/pricing/2026-03-25_local_policy.yaml`, `specs/models/*.yaml`, `src/kie_api/resources/specs/models/*.yaml`, `tests/test_registry_loader.py`, `tests/test_prompt_enhancer.py`, `tests/test_pricing_and_credit_guard.py`, `tests/test_pricing_refresh.py`, `tests/test_public_api.py`, `tests/test_request_fixtures.py`, `tests/test_config.py`, `examples/dry_run_with_prompt_enhancement.py`, `examples/dry_run_cost_estimate.py`, `examples/dry_run_preflight_gate.py`, `README.md`, `docs/CONFIGURATION.md`, `docs/LIBRARY_USAGE.md`, `docs/PROMPT_PROFILES.md`, `docs/PRICING_AND_PREFLIGHT.md`, `docs/MATURITY_MAP.md`, `docs/planning/TASKS.md`, `docs/planning/IMPLEMENTATION_PLAN.md`.
- Tests run: `. .venv/bin/activate && python -m pytest` — passed (53 tests), skipped (3 smoke tests without env).
- Live sources checked: none in this slice by design; this was a local dry-run and editability pass only.
- Notes:
  - Prompt profiles are now edited in package resources under `src/kie_api/resources/prompt_profiles/` with `metadata.yaml` plus `prompt.md`.
  - Model specs now use `prompt.default_profile_key`, which can be changed in YAML without touching Python code.
  - The current pricing snapshot is intentionally labeled `local_policy`; it is for dry-run estimation and gating, not a claimed KIE billing truth.
  - A small public-page pricing scrape scaffold was added, but it is explicitly non-authoritative and not used as a source of truth.

## 2026-03-26 — Slice 17: Review remediation and contract hardening
- Summary: Closed the main review findings by separating non-authoritative numeric pricing estimates from provider-authoritative billing truth, making `CreditGuard` request-aware, adding an explicit bundled model-spec sync/drift guard, and choosing pricing snapshots by snapshot metadata instead of filename order alone.
- Files: `src/kie_api/models.py`, `src/kie_api/registry/models.py`, `src/kie_api/registry/loader.py`, `src/kie_api/services/pricing.py`, `src/kie_api/services/preflight.py`, `src/kie_api/services/credit_guard.py`, `src/kie_api/resources/pricing/2026-03-25_local_policy.yaml`, `scripts/sync_packaged_specs.py`, `tests/test_pricing_and_credit_guard.py`, `tests/test_request_fixtures.py`, `tests/test_registry_loader.py`, `README.md`, `docs/PRICING_AND_PREFLIGHT.md`, `docs/PROMPT_PROFILES.md`, `docs/MATURITY_MAP.md`, `docs/CONTROL_API_INTEGRATION.md`, `docs/planning/TASKS.md`, `docs/planning/IMPLEMENTATION_PLAN.md`.
- Tests run: `. .venv/bin/activate && python -m pytest` — passed (56 tests), skipped (3 smoke tests without env).
- Live sources checked: none in this slice; this was a local remediation and contract-safety pass.
- Notes:
  - `EstimatedCost.has_numeric_estimate` now means the library can compute a planning estimate, while `EstimatedCost.is_authoritative` and `EstimatedCost.is_known` are reserved for provider-authoritative pricing.
  - `CreditGuard.evaluate(...)` now accepts either a `NormalizedRequest` or a model key string. Model-key-only evaluation remains supported but emits compatibility warnings because request-specific pricing adjustments may be missing.
  - Bundled model-spec drift is now guarded by `scripts/sync_packaged_specs.py --check` plus a test.
  - Latest pricing snapshot selection now prefers snapshot metadata dates over filename sort.

## 2026-03-26 — Slice 18: Live-verification prep, callback HMAC, and public pricing API capture
- Summary: Added a real credit-balance probe client, implemented callback signature verification from the documented HMAC contract, upgraded pricing refresh from HTML regex to KIE's public site-pricing API, switched the default pricing snapshot to a live-observed site snapshot, and expanded the smoke tests/docs around live verification.
- Files: `src/kie_api/exceptions.py`, `src/kie_api/models.py`, `src/kie_api/config.py`, `src/kie_api/adapters/market.py`, `src/kie_api/clients/credits.py`, `src/kie_api/clients/callbacks.py`, `src/kie_api/clients/status.py`, `src/kie_api/clients/submit.py`, `src/kie_api/clients/__init__.py`, `src/kie_api/api.py`, `src/kie_api/__init__.py`, `src/kie_api/registry/models.py`, `src/kie_api/services/pricing_refresh.py`, `src/kie_api/services/__init__.py`, `src/kie_api/resources/pricing/2026-03-26_site_pricing_page.yaml`, `scripts/refresh_site_pricing_snapshot.py`, `fixtures/live_responses/pricing_count_2026-03-26.json`, `fixtures/live_responses/pricing_nano_banana_2026-03-26.json`, `fixtures/live_responses/pricing_kling_2026-03-26.json`, `tests/test_callbacks.py`, `tests/test_credits_client.py`, `tests/test_pricing_refresh.py`, `tests/test_pricing_and_credit_guard.py`, `tests/test_public_api.py`, `tests/smoke/test_live_api_smoke.py`, `README.md`, `docs/CONFIGURATION.md`, `docs/PRICING_AND_PREFLIGHT.md`, `docs/REAL_API_INTEGRATION_READINESS.md`, `docs/MATURITY_MAP.md`, `docs/LIVE_VERIFICATION_REPORT.md`, `docs/planning/TASKS.md`.
- Tests run: `. .venv/bin/activate && python -m pytest tests/test_callbacks.py tests/test_credits_client.py tests/test_pricing_refresh.py tests/test_pricing_and_credit_guard.py tests/test_public_api.py tests/smoke/test_live_api_smoke.py` — passed (18 tests), skipped (4 smoke tests without env). Full suite run pending at slice close.
- Live sources checked:
  - `https://kie.ai/pricing`
  - `https://api.kie.ai/client/v1/model-pricing/count`
  - `https://api.kie.ai/client/v1/model-pricing/page`
  - `https://docs.kie.ai/common-api/webhook-verification`
  - `https://docs.kie.ai/common-api/get-account-credits`
- Mismatches and uncertainties:
  - The pricing page API exposes live site pricing rows, but that still does not prove actual billed-credit behavior after task execution.
  - The callback HMAC helper now follows the documented signature contract, but a real signed callback sample is still needed to verify docs and reality match exactly.
  - Authenticated credits, upload, submit, and status responses were not captured in this slice because the live test env was not exercised from the automated runner.

## 2026-03-26 — Slice 20: Upload-first submission flow and live Nano Banana alignment
- Summary: Added a strict upload-first preparation stage, introduced wrapper-facing prepare/submit/wait helpers, enforced trusted KIE-hosted media URLs at payload-build time, parsed `resultJson` outputs from live-observed status payloads, and updated smoke coverage, examples, and docs around the real Nano Banana 2 flow.
- Files: `src/kie_api/api.py`, `src/kie_api/config.py`, `src/kie_api/exceptions.py`, `src/kie_api/models.py`, `src/kie_api/__init__.py`, `src/kie_api/adapters/market.py`, `src/kie_api/clients/status.py`, `src/kie_api/clients/submit.py`, `src/kie_api/services/preparation.py`, `src/kie_api/services/__init__.py`, `tests/test_preparation.py`, `tests/test_wait_for_task.py`, `tests/test_status_client.py`, `tests/test_submit_client.py`, `tests/test_public_api.py`, `tests/test_request_fixtures.py`, `tests/smoke/test_live_api_smoke.py`, `examples/build_submission_payload.py`, `examples/live_run_guarded.py`, `README.md`, `docs/LIBRARY_USAGE.md`, `docs/CONFIGURATION.md`, `docs/UPLOAD_POLICY.md`, `docs/LIVE_VERIFICATION_REPORT.md`, `docs/REAL_API_INTEGRATION_READINESS.md`, `docs/planning/TASKS.md`.
- Tests run: `. .venv/bin/activate && python -m pytest` — passed (72 tests), skipped (4 smoke tests without env).
- Live sources checked: no new browsing in this slice; implementation aligned to the previously observed Nano Banana 2 live run and the KIE File Upload API quickstart contract already validated during the session.
- Notes:
  - `prepare_request_for_submission(...)` now uploads every image, video, and audio input unless the URL is already hosted on a trusted KIE upload host.
  - `build_submission_payload(...)` now rejects local paths and arbitrary third-party URLs by design.
  - `wait_for_task(...)` defaults to an image-safe `20s` poll interval and `15m` timeout, and `StatusResult.output_urls` now includes URLs parsed from `data.resultJson`.

## 2026-03-26 — Slice 21: End-to-end flow documentation and output download
- Summary: Added regression tests that prove Nano Banana over-limit image requests fail before any upload is attempted, introduced a small output-download helper for final asset URLs, and documented the exact end-to-end agent/wrapper execution flow from raw request to saved output file.
- Files: `src/kie_api/models.py`, `src/kie_api/api.py`, `src/kie_api/__init__.py`, `src/kie_api/clients/download.py`, `src/kie_api/clients/__init__.py`, `tests/test_preparation.py`, `tests/test_download_client.py`, `README.md`, `docs/LIBRARY_USAGE.md`, `docs/UPLOAD_POLICY.md`, `docs/CONTROL_API_INTEGRATION.md`, `docs/END_TO_END_FLOW.md`, `docs/MATURITY_MAP.md`, `docs/planning/TASKS.md`.
- Tests run: `. .venv/bin/activate && python -m pytest` — passed (76 tests), skipped (4 smoke tests without env).
- Live sources checked: none in this slice; this was a local hardening and documentation pass built on the already captured Nano Banana 2 live responses.
- Notes:
  - Nano Banana Pro over-limit requests now have explicit regression coverage for `9` images, and Nano Banana 2 for `15` images.
  - Those over-limit preparation paths fail before any upload call is made.
  - `download_output_file(...)` is intentionally simple and useful for wrappers that want to save the final result locally after `wait_for_task(...)`.

## 2026-03-26 — Slice 22: Run artifact bundle subsystem
- Summary: Added a first-pass local run artifact bundle system with typed artifact models, predictable run folder creation, input/output copying, image and video derivative generation, machine-readable metadata files, human-readable notes, and an append-only `outputs/index.jsonl`.
- Files: `pyproject.toml`, `.gitignore`, `src/kie_api/api.py`, `src/kie_api/__init__.py`, `src/kie_api/exceptions.py`, `src/kie_api/artifacts/__init__.py`, `src/kie_api/artifacts/models.py`, `src/kie_api/artifacts/paths.py`, `src/kie_api/artifacts/index.py`, `src/kie_api/artifacts/inspect.py`, `src/kie_api/artifacts/images.py`, `src/kie_api/artifacts/videos.py`, `src/kie_api/artifacts/derivatives.py`, `src/kie_api/artifacts/writer.py`, `tests/test_artifact_paths.py`, `tests/test_artifact_images.py`, `tests/test_artifact_index.py`, `tests/test_artifact_writer.py`, `tests/test_artifact_videos.py`, `tests/test_public_api.py`, `examples/create_image_run_artifact.py`, `examples/create_video_run_artifact.py`, `examples/generate_derivatives_for_originals.py`, `examples/append_run_index.py`, `README.md`, `docs/LIBRARY_USAGE.md`, `docs/RUN_ARTIFACTS.md`, `docs/DERIVATIVES.md`, `docs/END_TO_END_FLOW.md`, `docs/MATURITY_MAP.md`, `docs/planning/TASKS.md`.
- Tests run: `. .venv/bin/activate && python -m pytest` — passed (85 tests), skipped (4 smoke tests without env).
- Live sources checked: none in this slice; this was intentionally a local filesystem and derivative-processing pass only.
- Notes:
  - The artifact bundle system is local and reusable, not a production media-management platform.
  - Image derivatives use Pillow, and video derivatives use `ffmpeg` plus `ffprobe`.
  - Poster extraction defaults to `.jpg` because the current local ffmpeg build does not include a WebP encoder.

## 2026-03-26 — Slice 23: Artifact indexing and query layer
- Summary: Added a filesystem-backed artifact browsing layer over `outputs/index.jsonl` and run folders, enriched `manifest.json` and `index.jsonl` for dashboard-style browsing, introduced configurable derivative settings and source context metadata, added duplicate-safe append/rebuild helpers, and exposed clean public query functions.
- Files: `src/kie_api/api.py`, `src/kie_api/__init__.py`, `src/kie_api/artifacts/__init__.py`, `src/kie_api/artifacts/models.py`, `src/kie_api/artifacts/index.py`, `src/kie_api/artifacts/query.py`, `src/kie_api/artifacts/images.py`, `src/kie_api/artifacts/videos.py`, `src/kie_api/artifacts/writer.py`, `tests/test_artifact_querying.py`, `tests/test_artifact_writer.py`, `tests/test_public_api.py`, `examples/query_artifact_runs.py`, `examples/rebuild_artifact_index.py`, `examples/create_artifact_with_custom_settings.py`, `examples/print_run_summary.py`, `README.md`, `docs/LIBRARY_USAGE.md`, `docs/RUN_ARTIFACTS.md`, `docs/DERIVATIVES.md`, `docs/ARTIFACT_INDEXING.md`, `docs/ARTIFACT_QUERYING.md`, `docs/MATURITY_MAP.md`, `docs/planning/TASKS.md`.
- Tests run: `. .venv/bin/activate && python -m pytest` — passed (90 tests), skipped (4 smoke tests without env).
- Live sources checked: none in this slice; this was intentionally a local artifact-query and metadata-shape pass only.
- Notes:
  - Query helpers prefer `outputs/index.jsonl` for recent/filter/latest browsing and only open `run.json` when full detail is requested.
  - `append_run_index(...)` is now duplicate-safe by `run_id`.
  - `rebuild_run_index(...)` can recover a missing or stale index by rescanning artifact folders.
  - Derivative settings are now configurable through `ArtifactDerivativeSettings`, and source context fields are preserved in artifact metadata.

## 2026-03-26 — Slice 24: Wrapper-facing prompt context and final prompt flow
- Summary: Added explicit request-level prompt profile and system prompt override fields, introduced a wrapper-facing prompt-context resolver and final-prompt application helper, fixed payload building to submit `final_prompt_used`, and documented the exact wrapper-side enhancement flow.
- Files: `src/kie_api/models.py`, `src/kie_api/services/normalizer.py`, `src/kie_api/services/prompt_enhancer.py`, `src/kie_api/adapters/market.py`, `src/kie_api/api.py`, `src/kie_api/__init__.py`, `tests/test_prompt_enhancer.py`, `tests/test_submit_client.py`, `tests/test_public_api.py`, `examples/wrapper_prompt_flow.py`, `README.md`, `docs/LIBRARY_USAGE.md`, `docs/PROMPT_PROFILES.md`, `docs/PROMPT_WRAPPER_FLOW.md`, `docs/CONTROL_API_INTEGRATION.md`, `docs/MATURITY_MAP.md`, `docs/planning/TASKS.md`.
- Tests run: `. .venv/bin/activate && python -m pytest` — passed (93 tests), skipped (4 smoke tests without env).
- Live sources checked: none in this slice; this was a local wrapper-contract and prompt-flow pass only.
- Notes:
  - `resolve_prompt_context(...)` now gives wrappers the resolved prompt profile plus effective system prompt without requiring registry logic in the wrapper repo.
  - `system_prompt_override` beats the profile markdown body for a single request, and `prompt_profile_key` beats the model default profile key.
  - `build_submission_payload(...)` now uses `final_prompt_used` first, which closes the gap between wrapper-side enhancement and what KIE actually receives.

## 2026-03-26 — Slice 25: Kling 3.0 frame-guidance dry-run hardening
- Summary: Verified the live Kling 3.0 page exposes start and end frame image inputs, tightened local validation so Kling image-to-video distinguishes single-image start-frame vs two-image first-last-frame guidance, rejected `aspect_ratio` on the two-image path, and added fixture/tests/examples for dry-run Nano-to-Kling chaining.
- Files: `src/kie_api/services/validator.py`, `src/kie_api/fixtures.py`, `tests/test_validator.py`, `tests/test_submit_client.py`, `examples/dry_run_kling_frame_guidance.py`, `README.md`, `docs/LIBRARY_USAGE.md`, `docs/planning/TASKS.md`.
- Tests run: `. .venv/bin/activate && python -m pytest` — pending at slice write time.
- Live sources checked: `https://kie.ai/kling-3-0`
- Notes:
  - The live page currently shows `image_urls` with `Start Frame` and `End Frame`, prompt required, duration required, mode required, and `aspect_ratio` invalid when first or last frames are provided.
  - The SDK still models this as `kling-3.0-i2v`, but now exposes `normalized_request.debug["frame_guidance_mode"]` as `start_frame` or `first_last_frames`.
  - Provider payload construction already preserved image order via `image_urls`; this slice added explicit test coverage for that ordering.

## 2026-03-26 — Slice 26: Prompt preset expansion and wrapper contract
- Summary: Expanded the old prompt-profile concept into a request-shape-aware built-in prompt preset system, added placeholder rendering and input-pattern-aware preset resolution, introduced explicit rendered-system-prompt output for wrappers, added new built-in Banana and Kling 3.0 preset resources, and documented how a future Control API should override presets without moving CRUD into this repo.
- Files: `src/kie_api/enums.py`, `src/kie_api/exceptions.py`, `src/kie_api/models.py`, `src/kie_api/registry/models.py`, `src/kie_api/registry/loader.py`, `src/kie_api/services/prompt_enhancer.py`, `specs/models/*.yaml`, `src/kie_api/resources/specs/models/*.yaml`, `src/kie_api/resources/prompt_profiles/*`, `tests/test_registry_loader.py`, `tests/test_prompt_enhancer.py`, `tests/test_public_api.py`, `examples/wrapper_prompt_flow.py`, `README.md`, `docs/LIBRARY_USAGE.md`, `docs/PROMPT_PROFILES.md`, `docs/PROMPT_WRAPPER_FLOW.md`, `docs/CONTROL_API_INTEGRATION.md`, `docs/MODEL_ONBOARDING.md`, `docs/planning/TASKS.md`.
- Tests run: `. .venv/bin/activate && python -m pytest` — passed (103 tests), skipped (4 smoke tests without env).
- Live sources checked: none in this slice; this was a local runtime-contract, resolver, and documentation pass.
- Notes:
  - `resolve_prompt_context(...)` now returns request-shape-aware preset metadata, input pattern, resolution source, raw template, and rendered system prompt.
  - The wrapper contract remains thin: the wrapper chooses or overrides presets, calls its own LLM, and writes the enhanced prompt back through `apply_enhanced_prompt(...)`.
  - Control API CRUD is still intentionally out of scope; this slice only documents the future precedence model for explicit request keys, DB overrides, and built-in defaults.
