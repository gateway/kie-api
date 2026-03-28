---
name: kie-nano-banana
description: Run Nano Banana image generation or image editing through kie-api. Use when the user wants a prompt-only image, an image edit, or a low-cost first live Kie.ai test with Nano Banana 2 or Nano Banana Pro.
---

# Kie Nano Banana

Use this skill for Nano Banana image workflows.

## Supported shapes

- prompt-only image generation
- image editing with reference images

## Working rules

Determine the request shape first:
- if no images are provided, treat it as prompt-only
- if one or more images are provided, treat it as image edit

Use the library flow:
1. `normalize_request(...)`
2. `resolve_prompt_context(...)`
3. optional external prompt enhancement
4. `validate_request(...)`
5. `estimate_request_cost(...)`
6. `run_preflight(...)`
7. `prepare_request_for_submission(...)`
8. `submit_prepared_request(...)`
9. `wait_for_task(...)`
10. `download_output_file(...)`
11. `create_run_artifact(...)`

## Missing-input behavior

Before submitting, surface missing or ambiguous fields clearly.

Examples:
- if the user did not specify model, prefer `nano-banana-2`
- if the user did not specify resolution, suggest `1K` for cheap tests
- if the user did not specify output format, suggest `jpg`
- if the user provided too many images, stop before upload

Important limits:
- Nano Banana Pro: up to 8 images
- Nano Banana 2: up to 14 images

## Cost behavior

Always estimate cost before submission.

If the estimate is high, tell the user before continuing.
If credits are low, point them to:
- [Kie.ai credits](https://kie.ai?ref=e7565cf24a7fad4586341a87eaf21e42)

## Default recommendation

For the first live test:
- model: `nano-banana-2`
- resolution: `1K`
- format: `jpg`

## Help

If the user asks for help, explain:
- Nano Banana can run prompt-only image generation or image edit flows
- `nano-banana-2` is usually the best low-cost place to start
- missing questions should be asked before submit

Example asks:
- `make an image with Nano Banana`
- `edit this image with Nano Banana`
- `run a cheap first image test`

## Output expectations

Return:
- chosen model
- request shape
- missing questions if any
- estimated credits
- whether the run is ready to submit
- provider task id after submit
- final remote image URL after success
- local downloaded image path after download
- artifact folder path
- hero asset paths:
  - original image path
  - web image path
  - thumb image path

Do not just say the run succeeded. Always give the user the actual image location and the artifact folder so they do not need to hunt for it.
