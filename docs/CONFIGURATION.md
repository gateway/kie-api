# Configuration

`kie-api` supports both environment-based configuration and explicit settings injection.

## Key handling

- `KIE_API_KEY` is required for live KIE requests.
- Do not commit your key.
- This repo now ignores local env files such as `.env.live`.
- Start from the tracked example file:

```bash
cp .env.example .env.live
```

- Then load it into your shell before running examples, scripts, or tests that talk to KIE:

```bash
set -a
source .env.live
set +a
```

`kie-api` does not auto-load dotenv files for you. It reads environment variables that are already present in the running shell, or it accepts explicit `KieSettings(...)` injection.

## Environment variables

Required for live API use:
- `KIE_API_KEY`

Optional endpoints:
- `KIE_MARKET_BASE_URL`
- `KIE_UPLOAD_BASE_URL`
- `KIE_CREATE_TASK_PATH`
- `KIE_STATUS_PATH`
- `KIE_CREDITS_PATH`
- `KIE_CREDIT_FALLBACK_PATHS`
- `KIE_UPLOAD_STREAM_PATH`
- `KIE_UPLOAD_URL_PATH`
- `KIE_UPLOAD_BASE64_PATH`
- `KIE_UPLOAD_DEFAULT_PATH`
- `KIE_TRUSTED_UPLOADED_MEDIA_HOSTS`

Optional security:
- `KIE_WEBHOOK_SECRET`

Optional timeout tuning:
- `KIE_CONNECT_TIMEOUT_SECONDS`
- `KIE_READ_TIMEOUT_SECONDS`
- `KIE_WRITE_TIMEOUT_SECONDS`
- `KIE_POOL_TIMEOUT_SECONDS`
- `KIE_UPLOAD_READ_TIMEOUT_SECONDS`
- `KIE_WAIT_POLL_INTERVAL_SECONDS`
- `KIE_WAIT_TIMEOUT_SECONDS`

Optional credit guard:
- `KIE_WARN_CREDIT_THRESHOLD`
- `KIE_CONFIRM_CREDIT_THRESHOLD`
- `KIE_WARN_COST_USD_THRESHOLD`
- `KIE_CONFIRM_COST_USD_THRESHOLD`

Optional live smoke test controls:
- `KIE_RUN_LIVE_SMOKE=1`
- `KIE_SMOKE_UPLOAD_SOURCE_URL`
- `KIE_SMOKE_ALLOW_SUBMIT=1`
- `KIE_SMOKE_SUBMIT_MODEL_KEY`
- `KIE_SMOKE_PROMPT`

## Example

```bash
export KIE_API_KEY="replace-me"
export KIE_MARKET_BASE_URL="https://api.kie.ai"
export KIE_UPLOAD_BASE_URL="https://kieai.redpandaai.co"
export KIE_CREDITS_PATH="/api/v1/chat/credit"
export KIE_CREDIT_FALLBACK_PATHS="/api/v1/user/credits"
export KIE_UPLOAD_DEFAULT_PATH="images/user-uploads"
export KIE_TRUSTED_UPLOADED_MEDIA_HOSTS="tempfile.redpandaai.co,kieai.redpandaai.co"
export KIE_WEBHOOK_SECRET="replace-me-if-you-have-one"
export KIE_WARN_CREDIT_THRESHOLD="12"
export KIE_CONFIRM_CREDIT_THRESHOLD="25"
```

Or use a local env file:

```bash
cp .env.example .env.live
set -a
source .env.live
set +a
```

## Explicit injection

```python
from kie_api.config import KieSettings

settings = KieSettings(
    api_key="replace-me",
    webhook_secret="replace-me",
    read_timeout_seconds=90,
)
```

## Notes
- No secrets are committed in this repo.
- `.env.live` is intended for local-only use and should never be committed.
- Environment loading is intentionally simple and explicit.
- Export `KIE_API_KEY` in the same shell where you run `pytest`, examples, or scripts.
- Upload-first is now the package default for all image, video, and audio inputs.
- The package implements KIE callback signature verification using `X-Webhook-Timestamp`, `X-Webhook-Signature`, and HMAC-SHA256 over `taskId.timestamp`.
- Preflight warning and confirmation thresholds are optional; if omitted, dry-run preflight only reports the estimate.
