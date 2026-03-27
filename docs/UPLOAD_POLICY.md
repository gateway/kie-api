# Upload Policy

All model input media must be uploaded to KIE before submission payloads are built or sent.

This applies to:
- images
- videos
- audio

## Why

Live Nano Banana verification showed that KIE accepts uploaded media URLs cleanly, while direct external URLs and local file paths are not a safe submit-time contract for this SDK.
Validation also runs before upload, so impossible requests stop early without spending time or upload traffic.

The library now treats:
- local file paths
- arbitrary third-party HTTPS URLs

as pre-submit inputs only.

## Required flow

Use this order:
1. `normalize_request(...)`
2. `validate_request(...)`
3. `prepare_request_for_submission(...)`
4. `build_submission_payload(...)` or `submit_prepared_request(...)`
5. `wait_for_task(...)`

`prepare_request_for_submission(...)` uploads every media input unless it is already a trusted KIE-hosted URL.
If validation fails, no upload is attempted.

## Trusted uploaded hosts

Default trusted hosts:
- `tempfile.redpandaai.co`
- `kieai.redpandaai.co`

These are configurable through `KieSettings.trusted_uploaded_media_hosts` or `KIE_TRUSTED_UPLOADED_MEDIA_HOSTS`.

## What is rejected

`build_submission_payload(...)` will reject requests that still contain:
- local paths
- arbitrary remote media URLs

That failure is intentional. It prevents wrappers from silently submitting unprepared media refs.

It also prevents over-limit requests from reaching upload or submit.
Examples:
- Nano Banana Pro accepts at most 8 images
- Nano Banana 2 accepts at most 14 images

## Current upload endpoints

The library is aligned to KIE's File Upload API quickstart paths:
- `/api/file-stream-upload`
- `/api/file-url-upload`
- `/api/file-base64-upload`

Default upload path:
- `images/user-uploads`

For URL uploads, the library sends `fileUrl`, not `url`.
