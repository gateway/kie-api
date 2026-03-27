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

Known current TODO:
- Kling 3.0 `kling_elements` / element-reference support is documented by Kie.ai, but is not yet modeled in the runtime request types or upload flow here

## Completion rule

A model is only wrapper-ready when:
- dry-run tests pass
- payload tests pass
- one live smoke path succeeds
- prompt preset resolution is documented
- artifact output has been inspected
