# Skill: kie-kling-motion

Use this workflow when the user wants motion transfer with Kling 3.0 Motion Control.

## What this skill is for

Use this when the user wants:
- motion transfer from a source motion clip
- an image plus motion clip combined into a guided video

## Validation reminders

- motion control needs the required image/video combination defined by the spec
- if required media is missing, the flow should return `needs_input` before upload/submit
- upload-first still applies to both the image and the motion clip

## Recommended workflow

1. normalize the request
2. resolve prompt context
3. validate before upload
4. upload all inputs with `prepare_request_for_submission(...)`
5. submit
6. wait for final status
7. download outputs
8. create a run artifact bundle
