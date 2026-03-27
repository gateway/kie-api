# KIE API First-Pass Implementation Plan

## Objectives
- Build a reusable Python package for KIE.AI integration without company-specific API routes, auth, databases, or orchestration.
- Use live `kie.ai` model pages and their Playground/API inputs as the primary source of truth for model specs.
- Keep the implementation portable enough to run as a standalone package or be imported by a future Control API.

## Architecture
- `specs/` holds explicit model specs, prompt profiles, and future Control API contract notes.
- `src/kie_api/` holds typed models, registry loading, normalization, validation, and provider client abstractions.
- `tests/` covers the registry, normalization, validation, prompt enhancement, transport payloads, and guard decisions.
- `examples/` holds local test scripts for direct package usage.

## Execution Order
1. Tracking docs and package skeleton
2. Typed runtime models
3. Spec schema and registry loader
4. Live spec harvest and correction
5. Normalizer
6. Validator
7. Upload client
8. Submit client
9. Status client
10. Prompt enhancement
11. Pricing and credit guard
12. Examples, docs, and final test sweep

## Deliverables
- Model registry and spec loader
- Normalization and validation layers
- Upload, submit, and status abstractions
- Prompt enhancement framework
- Pricing and credit guard hooks
- Typed request and response models
- Tests, examples, and Control API handoff docs

## Open Uncertainties
- KIE upload endpoint paths are documented in secondary docs, but the main model pages do not expose them directly.
- Some model options shown on `docs.kie.ai` are not visible on the live page API tabs; those remain omitted or marked uncertain until re-verified.
- KIE status payload variants can differ by model family, so the status normalizer is written to preserve raw payloads and tolerate missing fields.

## Second-Pass Hardening Addendum
- Audit every current first-wave spec field as `verified_live`, `verified_docs`, `inferred`, or `unknown`.
- Tighten validation outputs so wrapper repos can branch on `ready`, `ready_with_defaults`, `ready_with_warning`, `needs_input`, and `invalid`.
- Add reusable request fixtures and payload verification tests that mirror real user-style requests.
- Improve the public import surface so wrapper repos can use the package without reaching into internal modules.
- Document the wrapper contract and the remaining real-API readiness gaps explicitly instead of implying production completeness.

## Third-Pass Packaging Addendum
- Make spec loading work in both editable and installed package contexts.
- Reduce remaining unknowns with another live-plus-docs verification pass.
- Separate provider payload/response adapters from transport code.
- Improve explicit env/config handling without introducing secret files or company orchestration.
- Add opt-in live smoke scaffolding that stays skipped unless explicitly enabled.
- Publish an honest maturity map for what is library-ready versus what still needs live verification or wrapper infrastructure.

## Fourth-Pass Dry-Run Addendum
- Move prompt profiles to editable package resources so they can be changed with markdown and YAML only.
- Allow model specs to define default prompt profile keys without requiring Python edits.
- Add versioned local pricing snapshots and keep them explicit as local policy or other provenance classes.
- Add dry-run cost estimation and preflight gating that works with no API key.
- Keep pricing refresh/scrape work as optional scaffolding, not an implied verified billing source.
- Expand docs and examples so another developer can edit profiles, defaults, and pricing data without changing Python code.

## Review Remediation Addendum
- Separate “numeric estimate available” from “provider-authoritative pricing” in the public pricing contract.
- Make `CreditGuard` operate on real requests when provided and emit explicit warnings when only a model key is available.
- Guard bundled model-spec drift with an explicit sync/check script plus test coverage.
- Select pricing snapshots by snapshot metadata rather than filename ordering alone.
- Keep callback verification explicitly parse-only until live signing behavior is verified.

## Live Source Rule
- Prefer live `kie.ai` pages and their Playground/API surfaces over `docs.kie.ai`.
- Record any disagreement in the model spec `verification_notes`.
- Store source provenance directly in the YAML spec files.

## First-Wave Models
- Nano Banana Pro
- Nano Banana 2
- Kling 2.6 text-to-video
- Kling 2.6 image-to-video
- Kling 3.0 text-to-video
- Kling 3.0 image-to-video
- Kling 3.0 motion control
