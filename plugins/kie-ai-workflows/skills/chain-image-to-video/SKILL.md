---
name: kie-chain-image-to-video
description: Chain a generated image into a video workflow through kie-api. Use when the user wants to generate an image first, then use that image as the source for Kling image-to-video.
---

# Kie Chain Image To Video

Use this skill when the workflow is:
- prompt -> image
- image -> video

## Preferred chain

1. Generate the image with `nano-banana-2`
2. Download and store the image
3. Use that downloaded image as the first frame for `kling-3.0-i2v`
4. Download the video
5. Create artifacts for both runs
6. Preserve linkage between the image run and the video run

## Rules

- treat the image stage and the video stage as separate cost decisions
- do not submit the Kling stage until the image stage succeeded
- upload the generated image first before Kling submission
- record both artifact folders

## Help

If the user asks for help, explain:
- this skill runs a two-stage workflow
- the image stage and video stage are separate cost decisions
- the output image from stage one becomes the source image for stage two

Example asks:
- `generate an image then animate it`
- `make a Nano Banana image and pass it to Kling`

## Output expectations

Return:
- image task id
- video task id
- image remote output URL
- video remote output URL
- image local downloaded file path
- video local downloaded file path
- image artifact folder
- video artifact folder
- image hero asset paths
- video hero asset paths

Always return both stages clearly so the user can open the image and the video directly.
