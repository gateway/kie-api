# Model Onboarding

Use this checklist every time a new KIE model or mode is brought online in `kie-api`.

## Required steps

1. Add or update the model spec.
2. Record field-level provenance.
3. Add prompt preset coverage for each supported request shape.
4. Add dry-run normalizer and validator tests.
5. Add payload-construction tests.
6. Run the cheapest practical live verification path.
7. Verify download, artifacts, and derivatives.
8. Update docs and changelog.

## Provider capability updates

Classify provider announcements before changing code:

- Spec-only update: new enum values, higher resolutions, longer existing duration ranges, new aspect ratios, value aliases, updated defaults, pricing rows, or clearer docs for an already-modeled input pattern.
- Studio workflow update: new media slot concepts, new task modes, new input patterns, mixed media requirements that do not fit existing slots, provider-specific request arrays, or option types Studio cannot render safely.

For spec-only updates:

1. Update the canonical spec under `specs/models/`.
2. Keep option names aligned with pricing rules and Media Studio request options.
3. Add value aliases when provider casing differs from user-facing casing, such as `4k -> 4K`.
4. Refresh pricing if provider pricing changed.
5. Run registry, validator, payload, pricing, and packaged-spec sync checks.
6. Start Media Studio against this checkout and confirm `/media/models` exposes the changed option values through `studio_dynamic_options`.

For Studio workflow updates:

1. Hide or leave the model unexposed until Studio has an explicit composer contract.
2. Add or update prompt input-pattern metadata only after the request shape is understood.
3. Add Media Studio support-classifier coverage before exposing the model in the Studio picker.
4. Browser-smoke `/models` first; unsupported models should explain why they are hidden.

Option metadata may include UI-safe fields for downstream clients:

- `label`
- `help_text`
- `ui_group`
- `ui_order`
- `advanced`
- `hidden_from_studio`
- `ui_control` for explicit controls such as freeform `string` text inputs

Clients should treat KIE validation as authoritative. Media Studio may auto-render known option types from `/media/models`, but it should not invent provider payload fields or expose unknown input workflows.

## Prompt preset readiness

Every supported request shape should have either:
- a model-spec default preset
- or a resolvable built-in best-match preset

Typical request shapes:
- `prompt_only`
- `single_image`
- `first_last_frames`
- `image_edit`
- `motion_control`
- `multimodal_reference` when a provider supports mixed image/video/audio guidance that is not equivalent to first/last-frame or edit mode

A preset is ready when:
- the template exists
- `{{user_prompt}}` is used where appropriate
- required placeholders render without errors
- task mode and input pattern bindings are correct

## Dry-run checks

Before live spend:
- normalize request
- resolve prompt context
- inspect the rendered system prompt
- validate request
- preview payload
- estimate cost

## Live verification

Capture:
- submit response
- final status response
- output URL shape
- any provider validation errors

If live behavior differs from docs or assumptions:
- update the spec
- update preset defaults
- update tests
- record the mismatch in docs

For advanced provider-specific shapes such as Kling 3.0 multi-shot mode:
- add typed runtime request models where needed
- validate cross-field rules explicitly
- do not hide docs-only shape differences inside generic passthrough options

For image-edit models that use a nonstandard image URL field:
- set `transport.image_input_field` in the model spec
- keep the request shape as `image_edit` when the model still takes prompt plus image references
- add a payload test proving the provider field name, such as `input_urls` instead of `image_input`
- add validator tests for documented cross-field constraints before live spend

For multimodal video models such as Seedance 2.0:
- treat first-frame, first+last-frame, and multimodal-reference as mutually-exclusive validated scenarios if the provider documents them that way
- do not force them into a Kling-style multi-shot abstraction unless the provider request shape actually exposes shot arrays
- if multimodal references introduce mixed image/video/audio guidance, prefer a dedicated input-pattern binding over overloading existing `single_image` or `first_last_frames` logic
- use role-aware media references when the same endpoint needs to distinguish first-frame, last-frame, and general reference assets

Known current TODO:
- Kling 3.0 `kling_elements` / element-reference support is documented by Kie.ai, but is not yet modeled in the runtime request types or upload flow here

## Completion rule

A model is only wrapper-ready when:
- dry-run tests pass
- payload tests pass
- one live smoke path succeeds
- prompt preset resolution is documented
- artifact output has been inspected
