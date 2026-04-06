# Skill: kie-model-onboarding

Use this workflow when you want to add a new image or video model into `kie-api` without breaking the repo's existing abstractions.

## What this skill is for

Use this when you want:
- a new Kie.ai model spec
- prompt presets for a new model or mode
- validation for new provider-specific shapes
- payload tests and a live smoke path

## Recommended order

1. read the live market page and docs page
2. capture the exact request shape
3. decide whether it fits an existing task shape
4. add the spec and provenance
5. add prompt presets
6. add tests
7. run the cheapest live smoke
8. inspect artifacts and update docs

## Seedance 2.0 note

Seedance 2.0 should be modeled as a multimodal video endpoint with mutually-exclusive scenarios:
- text-to-video
- first-frame
- first+last-frame
- multimodal reference

Do not assume Kling-style multi-shot or `multi_prompt` unless the docs or live API explicitly require it.
