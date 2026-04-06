---
name: kie-model-onboarding
description: Onboard a new Kie.ai image or video model into kie-api using the repo's spec-first workflow. Use when adding a new Kie.ai model or mode, verifying docs vs live behavior, creating prompt presets, adding tests, and preparing the model for wrapper or dashboard use.
---

# Kie Model Onboarding

Use this skill when bringing a new Kie.ai model online in `kie-api`.

This is not a generation skill. It is a spec-first implementation workflow.

## Primary goal

Bring a new model online in a way that matches the existing system:
- model spec
- validation
- prompt preset coverage
- payload construction
- pricing/preflight
- live smoke verification
- artifact compatibility

## Required workflow

1. Read the live Kie.ai market page and docs page.
2. Capture the provider model string and exact request body shape.
3. Decide whether the model should be:
   - a new standalone model key
   - a family alias branch
   - or a new request shape on an existing endpoint
4. Add or update the model spec under `specs/models/`.
5. Record field-level provenance.
6. Add prompt presets for every supported request shape.
7. Add dry-run tests for:
   - normalization
   - validation
   - payload building
   - preset resolution
8. Run the cheapest practical live smoke path.
9. Verify outputs, download flow, and artifacts.
10. Update docs.

## Decision rules

- Do not invent provider fields that the docs or live surface do not expose.
- If docs and live behavior disagree, prefer live provider truth and document the mismatch.
- If a model supports multiple mutually-exclusive input scenarios, model that explicitly in validation instead of hiding it inside passthrough options.
- Reuse existing request shapes when they truly fit.
- Add a new input-pattern concept only when the current patterns are not expressive enough.

## Existing shape system

Common task shapes already used in this repo:
- `prompt_only`
- `single_image`
- `first_last_frames`
- `image_edit`
- `motion_control`

If a new model introduces a materially different shape, add it deliberately and document why.

## Seedance 2.0 guidance

For Seedance 2.0 specifically:
- provider model is `bytedance/seedance-2`
- it is one multimodal video endpoint with mutually-exclusive scenarios
- first-frame / first+last-frame / multimodal-reference should be treated as separate validated shapes
- do not model it as Kling-style `multi_prompt` unless the docs and live API explicitly require that
- multimodal reference support should account for:
  - `reference_image_urls`
  - `reference_video_urls`
  - `reference_audio_urls`
- the current docs indicate:
  - `resolution`: `480p | 720p`
  - `aspect_ratio`: `16:9 | 4:3 | 1:1 | 3:4 | 9:16 | 21:9`
  - `duration`: provider-controlled numeric seconds
  - `return_last_frame`
  - `generate_audio`
  - `web_search`

## Required files to update

- `specs/models/*.yaml`
- packaged spec copy under `src/kie_api/resources/specs/models/`
- `specs/prompt_profiles/*` when new presets are needed
- packaged preset copy under `src/kie_api/resources/prompt_profiles/*`
- runtime request/validator/normalizer/payload code when shape support changes
- tests
- docs

## Validation gates

Before calling a model wrapper-ready, all of these should be true:
- dry-run normalization works
- validation catches impossible combinations
- payload tests pass
- prompt preset resolution is correct
- one live smoke path succeeds
- artifact output was inspected

## Help

If the user asks for help, explain:
- this skill is for adding or hardening models, not running generation
- the repo is spec-first
- the safest order is docs -> spec -> tests -> live smoke -> docs update
