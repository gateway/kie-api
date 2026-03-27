# Live Verification Report

This file records what was actually observed live versus what is still pending.

## Verified live in this pass
- KIE's public pricing page UI labels were observed from `https://kie.ai/pricing`.
- KIE's public pricing site API was observed from:
  - `GET https://api.kie.ai/client/v1/model-pricing/count`
  - `POST https://api.kie.ai/client/v1/model-pricing/page`
- Authenticated credit balance was observed with a real API key:
  - `GET https://api.kie.ai/api/v1/chat/credit`
  - current response shape was `{"code":200,"msg":"success","data":60.62}`
- Authenticated file upload was observed with a real API key against the quickstart file upload API:
  - `POST https://kieai.redpandaai.co/api/file-stream-upload`
  - `uploadPath` is required
  - successful response included `filePath`, `downloadUrl`, `fileSize`, `mimeType`, and `uploadedAt`
- Authenticated Nano Banana 2 submit was observed with a real API key:
  - `POST https://api.kie.ai/api/v1/jobs/createTask`
  - successful response shape included `code/msg/data.taskId/data.recordId`
- Authenticated status polling was observed with a real API key:
  - `GET https://api.kie.ai/api/v1/jobs/recordInfo`
  - image jobs can remain `waiting` for several minutes before completing
  - successful output URLs were returned inside `data.resultJson` as a JSON string
- The pricing site API returned structured rows for:
  - Nano Banana 2 image pricing tiers
  - Nano Banana Pro image pricing tiers
  - Kling 2.6 text-to-video pricing tiers
  - Kling 2.6 image-to-video pricing tiers
  - Kling 3.0 video pricing tiers with audio and resolution differences
  - Kling 3.0 motion control pricing tiers by resolution
- Sanitized public live response samples were saved under `fixtures/live_responses/`.

## Verified from current documentation in this pass
- KIE documents a webhook verification scheme using:
  - `X-Webhook-Timestamp`
  - `X-Webhook-Signature`
  - HMAC-SHA256 over `taskId.timestamp`
- KIE documents a credits endpoint at `GET /api/v1/chat/credit`.

## Not yet observed live in this pass
- Real callback payloads and signed callback headers
- Real audio or video upload payloads
- Real video submit/status payloads

## Important honesty notes
- The default pricing snapshot is now based on live-observed public site pricing, but it is still not treated as authoritative billing truth.
- Callback signature verification is implemented from the documented contract, but it still needs a real signed callback sample to prove the docs match reality.
- Nano Banana 2 full-flow artifacts were captured under `fixtures/live_responses/`.
