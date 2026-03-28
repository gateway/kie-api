---
name: kie-kling-video
description: Run Kling video workflows through kie-api. Use when the user wants text-to-video, image-to-video with one start frame, or first-last-frame video generation with Kling 2.6 or Kling 3.0.
---

# Kie Kling Video

Use this skill for Kling video workflows.

## Supported shapes

- text-to-video
- image-to-video with one image
- image-to-video with first and last frames

## Shape detection

- no images: text-to-video
- one image: first-frame image-to-video
- two images on Kling i2v: first-last-frame guidance

## Workflow

1. normalize the request
2. resolve prompt context
3. validate before upload
4. estimate cost
5. run preflight
6. upload media first
7. submit the task
8. wait for completion
9. download outputs
10. create a run artifact bundle

## Missing-input behavior

Ask for missing fields before submitting:
- duration
- mode
- prompt when required

Explain defaults and warnings:
- sound may be defaulted
- aspect ratio may be inferred from source media depending on the model/mode

## Cost behavior

Video runs are more expensive than image runs.
Always estimate credits before submission.
If the run is expensive, require explicit confirmation.
If credits are low, point the user to:
- [Kie.ai credits](https://kie.ai?ref=e7565cf24a7fad4586341a87eaf21e42)

## Default recommendation

For the first Kling test:
- use `kling-3.0-i2v`
- use one image
- `duration=5`
- `mode=std`

Prefer dry-run validation before real video submission.

## Help

If the user asks for help, explain:
- the difference between text-to-video, first-frame image-to-video, and first-last-frame guidance
- that video runs cost more than image runs
- that duration and mode should be confirmed before submit

Example asks:
- `make a Kling video from this image`
- `turn this prompt into a video`
- `use these two images as first and last frame`

## Output expectations

Return:
- chosen model and request shape
- provider task id
- final remote video URL
- local downloaded video path
- artifact folder path
- hero asset paths:
  - original video path
  - web video path
  - poster path

If the run did not finish, return the latest task status and the current artifact/log location.
