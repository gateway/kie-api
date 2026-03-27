# Skill: kie-kling-video

Use this workflow when the user wants text-to-video or image-to-video with Kling 2.6 or Kling 3.0.

## What this skill is for

Use this when you want:
- text-to-video
- image-to-video with one first frame
- image-to-video with first and last frame guidance
- a chained image -> video flow

## Key request shapes

- no images: text-to-video
- one image: first-frame image-to-video
- two images on Kling i2v: first+last-frame guidance

## Important live behavior already observed

- Kling 3.0 needed `sound` to be present at submit time
- image/video inputs should be uploaded first through `prepare_request_for_submission(...)`
- successful outputs should be stored as run artifacts with originals, web derivatives, and posters

## Recommended testing order

1. do a dry-run payload check first
2. start with `mode=std`
3. use the shortest practical duration
4. prefer image-to-video before higher-cost text-to-video if you already have a source image

## Prompt preset guidance

Use the prompt preset that matches the shape:
- `kling-3.0-t2v`
- `kling-3.0-i2v-first-frame`
- `kling-3.0-i2v-first-last-frame`

The wrapper should:
1. call `resolve_prompt_context(...)`
2. send `rendered_system_prompt` plus the user prompt to its LLM
3. write the enhanced prompt back with `apply_enhanced_prompt(...)`
