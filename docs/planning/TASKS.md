# KIE API Task Tracker

## 1. Planning and tracking docs
- [COMPLETED] Create `docs/planning/IMPLEMENTATION_PLAN.md` — 2026-03-25
- [COMPLETED] Create `docs/planning/TASKS.md` — 2026-03-25
- [COMPLETED] Create `docs/planning/CHANGELOG.md` — 2026-03-25

## 2. Package skeleton
- [COMPLETED] Create `pyproject.toml` and dependency scaffold — 2026-03-25
- [COMPLETED] Create package directories under `src/kie_api/` — 2026-03-25
- [COMPLETED] Add base package wiring modules — 2026-03-25

## 3. Domain models
- [COMPLETED] Add typed runtime request and response models — 2026-03-25
- [COMPLETED] Add shared enums and exceptions — 2026-03-25

## 4. Registry loader
- [COMPLETED] Add typed spec schema models — 2026-03-25
- [COMPLETED] Implement YAML spec and prompt profile loader — 2026-03-25
- [COMPLETED] Add registry loader tests — 2026-03-25

## 5. Live spec harvest
- [COMPLETED] Correct Nano Banana specs from live KIE pages — 2026-03-25
- [COMPLETED] Split Kling 3.0 into separate text and image specs — 2026-03-25
- [COMPLETED] Correct motion-control fields from live KIE pages — 2026-03-25

## 6. Normalizer
- [COMPLETED] Implement model and task-mode normalization — 2026-03-25
- [COMPLETED] Apply verified defaults only — 2026-03-25
- [COMPLETED] Add normalizer tests — 2026-03-25

## 7. Validator
- [COMPLETED] Implement required-input and option validation — 2026-03-25
- [COMPLETED] Return structured `needs_input` results — 2026-03-25
- [COMPLETED] Add validator tests — 2026-03-25

## 8. Upload client
- [COMPLETED] Implement upload client abstraction — 2026-03-25
- [COMPLETED] Normalize upload responses and errors — 2026-03-25
- [COMPLETED] Add upload tests — 2026-03-25

## 9. Submit client
- [COMPLETED] Implement task submitter abstraction — 2026-03-25
- [COMPLETED] Add provider payload mapping tests — 2026-03-25

## 10. Status client
- [COMPLETED] Implement status checker abstraction — 2026-03-25
- [COMPLETED] Add status normalization tests — 2026-03-25

## 11. Prompt enhancement
- [COMPLETED] Implement prompt enhancement framework — 2026-03-25
- [COMPLETED] Add policy and profile tests — 2026-03-25

## 12. Pricing and credit guard
- [COMPLETED] Implement pricing registry — 2026-03-25
- [COMPLETED] Implement credit guard decisions — 2026-03-25
- [COMPLETED] Add pricing and guard tests — 2026-03-25

## 13. Examples and docs
- [COMPLETED] Add local example scripts — 2026-03-25
- [COMPLETED] Update `README.md` — 2026-03-25
- [COMPLETED] Add Control API integration docs — 2026-03-25

## 14. Test sweep and final polish
- [COMPLETED] Run the full test suite — 2026-03-25
- [COMPLETED] Finalize the tracker and changelog entries — 2026-03-25

## 15. Second-pass hardening and live-verification
- [COMPLETED] Audit current model spec fields as `verified_live`, `verified_docs`, `inferred`, or `unknown` — 2026-03-25
- [COMPLETED] Tighten the normalizer and validator result contract for `ready`, `ready_with_defaults`, `ready_with_warning`, `needs_input`, and `invalid` — 2026-03-25
- [COMPLETED] Add reusable integration request fixtures for Control API wrapper tests — 2026-03-25
- [COMPLETED] Expand provider payload verification coverage for all supported models and modes — 2026-03-25
- [COMPLETED] Refine the public package surface for wrapper-friendly imports — 2026-03-25
- [COMPLETED] Strengthen Control API handoff docs and add a real API integration readiness checklist — 2026-03-25
- [COMPLETED] Run the full test suite for the second-pass hardening slice — 2026-03-25
- [COMPLETED] Append second-pass changelog entries and note remaining unknowns — 2026-03-25

## 16. Third-pass packaging and real-API readiness
- [COMPLETED] Resolve remaining live/docs verification gaps where possible — 2026-03-25
- [COMPLETED] Harden packaged spec loading for editable and installed usage — 2026-03-25
- [COMPLETED] Improve environment-driven config and timeout handling — 2026-03-25
- [COMPLETED] Separate provider payload and response adapters from transport code — 2026-03-25
- [COMPLETED] Add callback scaffolding and explicit non-implementation notes for signature verification — 2026-03-25
- [COMPLETED] Add opt-in live smoke test scaffolding with automatic skips when env vars are missing — 2026-03-25
- [COMPLETED] Expand external-use docs, configuration docs, and maturity map — 2026-03-25
- [COMPLETED] Run the full test suite for the third-pass packaging slice — 2026-03-25

## 17. Fourth-pass local dry-run editability
- [COMPLETED] Move prompt profiles to editable package-resource folders with `metadata.yaml` and `prompt.md` — 2026-03-25
- [COMPLETED] Add prompt profile resolver support and model default profile keys — 2026-03-25
- [COMPLETED] Add versioned local pricing snapshot resources and cost estimation — 2026-03-25
- [COMPLETED] Add dry-run preflight gating with warn and confirmation thresholds — 2026-03-25
- [COMPLETED] Add pricing refresh scaffolding and dry-run pricing tests — 2026-03-25
- [COMPLETED] Add prompt profile and pricing/preflight docs and examples — 2026-03-25
- [COMPLETED] Run the full test suite for the fourth-pass dry-run slice — 2026-03-25

## 18. Review remediation pass
- [COMPLETED] Make pricing estimate provenance explicit and non-authoritative by default for local policy snapshots — 2026-03-26
- [COMPLETED] Make `CreditGuard` request-aware while keeping model-key compatibility warnings — 2026-03-26
- [COMPLETED] Add bundled model-spec sync script and drift test — 2026-03-26
- [COMPLETED] Select latest pricing snapshot by snapshot metadata instead of filename order alone — 2026-03-26
- [COMPLETED] Update docs for pricing truth semantics, packaged-spec sync, and callback guardrails — 2026-03-26
- [COMPLETED] Run the full test suite for the review remediation slice — 2026-03-26

## 19. Live-verification prep and public pricing pass
- [COMPLETED] Implement a credit balance probe client with fallback endpoint support — 2026-03-26
- [COMPLETED] Replace callback signature stubs with documented HMAC verification — 2026-03-26
- [COMPLETED] Add public site-pricing API capture and snapshot-building utilities — 2026-03-26
- [COMPLETED] Add sanitized live pricing response fixtures and refresh script — 2026-03-26
- [COMPLETED] Add opt-in credit smoke coverage and keep submit smoke image-only — 2026-03-26
- [COMPLETED] Update docs, readiness notes, and live verification report — 2026-03-26

## 20. Upload-first submission flow and live Nano Banana alignment
- [COMPLETED] Add `PreparedRequest` and enforce upload-first media preparation — 2026-03-26
- [COMPLETED] Reject non-KIE media URLs and local paths at payload-build time — 2026-03-26
- [COMPLETED] Add `submit_prepared_request(...)` and `wait_for_task(...)` helpers — 2026-03-26
- [COMPLETED] Parse `resultJson` output URLs from live-observed status responses — 2026-03-26
- [COMPLETED] Extend settings with trusted-host and polling controls — 2026-03-26
- [COMPLETED] Update smoke tests, examples, and docs to the upload-first flow — 2026-03-26
- [COMPLETED] Run the full test suite for the upload-first slice — 2026-03-26

## 21. End-to-end flow documentation and output download
- [COMPLETED] Add regression tests that over-limit Nano Banana requests stop before upload — 2026-03-26
- [COMPLETED] Add a small output download helper for final result URLs — 2026-03-26
- [COMPLETED] Add end-to-end execution docs for agent and wrapper usage — 2026-03-26
- [COMPLETED] Run the full test suite for the end-to-end flow slice — 2026-03-26

## 22. Run artifact bundle subsystem
- [COMPLETED] Add artifact models, path helpers, and append-only index support — 2026-03-26
- [COMPLETED] Add image and video derivative generation helpers — 2026-03-26
- [COMPLETED] Add run artifact bundle writer with metadata files and notes — 2026-03-26
- [COMPLETED] Add artifact examples, docs, and repo output ignore rules — 2026-03-26
- [COMPLETED] Add artifact tests for naming, derivatives, manifests, and indexing — 2026-03-26
- [COMPLETED] Run the full test suite for the artifact subsystem slice — 2026-03-26

## 23. Artifact indexing and query layer
- [COMPLETED] Add richer manifest and index fields for dashboard-friendly browsing — 2026-03-26
- [COMPLETED] Add configurable derivative settings and source context support — 2026-03-26
- [COMPLETED] Add duplicate-safe append, index rebuild, and artifact scan helpers — 2026-03-26
- [COMPLETED] Add query helpers for recent runs, filtering, latest success, and latest assets — 2026-03-26
- [COMPLETED] Add note-regeneration helper and new query/examples docs — 2026-03-26
- [COMPLETED] Add tests for query helpers, rebuild flow, duplicate-safe append, and custom settings — 2026-03-26
- [COMPLETED] Run the full test suite for the artifact indexing slice — 2026-03-26

## 24. Wrapper-facing prompt context and final prompt flow
- [COMPLETED] Add explicit request fields for prompt profile selection and system prompt override — 2026-03-26
- [COMPLETED] Add wrapper-facing prompt context resolution and final-prompt application helpers — 2026-03-26
- [COMPLETED] Make submission payload building honor `final_prompt_used` before the raw prompt — 2026-03-26
- [COMPLETED] Add tests, docs, and example flow for wrapper-side prompt enhancement — 2026-03-26
- [COMPLETED] Run the full test suite for the wrapper prompt slice — 2026-03-26

## 25. Kling 3.0 frame-guidance dry-run hardening
- [COMPLETED] Confirm live Kling 3.0 frame guidance semantics against the live page/API surface — 2026-03-26
- [COMPLETED] Make Kling 3.0 validation distinguish start-frame vs first-last-frame guidance — 2026-03-26
- [COMPLETED] Reject `aspect_ratio` when Kling 3.0 uses both first and last frame images — 2026-03-26
- [COMPLETED] Add dry-run fixture, payload-order coverage, and local example for Kling frame guidance — 2026-03-26
- [COMPLETED] Run the full test suite for the Kling frame-guidance slice — 2026-03-26

## 26. Prompt preset expansion and wrapper contract
- [COMPLETED] Expand the prompt resource schema to support preset metadata, request-shape matching, and template placeholders — 2026-03-26
- [COMPLETED] Add input-pattern-aware preset resolution and rendered system prompt output in the wrapper context — 2026-03-26
- [COMPLETED] Add built-in prompt presets for Banana and Kling 3.0 request shapes while keeping old profiles backward-compatible — 2026-03-26
- [COMPLETED] Document preset resolution, Control API override precedence, and future model onboarding expectations — 2026-03-26
- [COMPLETED] Add dry-run tests for preset selection, placeholder rendering, alias handling, and wrapper flow — 2026-03-26
- [COMPLETED] Run the full test suite for the prompt preset slice — 2026-03-26
