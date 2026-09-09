# GPT Image 2.5

The registry includes four independent Kie Market models:

| Model key | Task mode | Default prompt preset |
| --- | --- | --- |
| `gpt-image-2-5-flare-text-to-image` | `text_to_image` | `gpt_image_2_5_text_to_image_v1` |
| `gpt-image-2-5-flare-image-to-image` | `image_edit` | `gpt_image_2_5_image_to_image_v1` |
| `gpt-image-2-5-sunburst-text-to-image` | `text_to_image` | `gpt_image_2_5_text_to_image_v1` |
| `gpt-image-2-5-sunburst-image-to-image` | `image_edit` | `gpt_image_2_5_image_to_image_v1` |

Each key is also its exact provider `model` string. Kie positions Flare for general-purpose generation with lower latency and Sunburst for premium creative/editing work. Both expose the same API fields. No measured performance guarantee is implied.

## Inputs and options

Prompts are required, nonempty, and at most 20,000 characters. T2I accepts no media. I2I requires 1–16 images and sends them as `input.input_urls`; the usual preparation service uploads local files or external URLs before submission. Neither mode accepts video or audio.

| Option | Allowed values | Wrapper default |
| --- | --- | --- |
| `aspect_ratio` | `auto`, `1:1`, `3:2`, `2:3`, `4:3`, `3:4`, `16:9`, `9:16`, `21:9`, `27:16`, `16:27`, `9:8`, `8:9` | `auto` |
| `resolution` | `1K`, `2K`, `4K` | `1K` |

The provider documents `auto` as the aspect default. Resolution `1K` is a local wrapper default to align submissions and estimates; the API schema does not specify its own default. The existing validation stage converts `1k`/`2k`/`4k` to uppercase provider values. Use validation/preparation before submission.

The implementation follows the actual API OpenAPI enums. It does not enforce the playground-only claim that `27:16`, `16:27`, `9:8`, and `8:9` require 1K. The two I2I schemas also have inconsistent `x-apidog-enum` display metadata; extra values from that metadata are excluded. Existing GPT Image 2 restrictions on square/auto high resolution remain scoped to the old models. Documented combinations are locally accepted; this does not establish that every combination succeeds on the backend.

No model-specific masks, seed, edit strength, negative prompt, output-format, batch-count, or conversation-state option is declared. File format/size limits are not specified in these model docs. Existing generic upload and request-validation behavior is unchanged.

## Dry-run example

```python
from kie_api import build_submission_payload, estimate_request_cost, validate_request
from kie_api.models import RawUserRequest

request = RawUserRequest(
    model_key="gpt-image-2-5-flare-text-to-image",
    prompt="A blue ceramic mug on a plain cream background, soft studio lighting.",
    options={"aspect_ratio": "3:2", "resolution": "2k"},
)
validation = validate_request(request)
payload = build_submission_payload(validation)
estimate = estimate_request_cost(validation.normalized_request)
```

For editing, select an I2I key, provide `images=["/path/to/reference.png"]`, and call `prepare_request_for_submission(validation)` before `submit_prepared_request(prepared)`. Use `callback_url` on the request when needed; the adapter places `callBackUrl` at the provider body root. These models reuse `/api/v1/jobs/createTask`, `/api/v1/jobs/recordInfo`, output downloads, and run artifacts.

## Pricing

The market banner observed on 2026-09-09 advertises 6 credits ($0.03) at 1K, 10 ($0.05) at 2K, and 16 ($0.08) at 4K for all four modes. The new versioned pricing snapshot preserves all previous rules and their observation dates. Rates remain `observed_site_pricing`, not authoritative billing guarantees. Top-up promotions are excluded.

## Verification

Local tests cover the documented ratio/resolution matrix, image and prompt boundaries, resolution aliases, exact payloads, both preset shapes, all pricing tiers, refresh matching, and source/package parity. The full non-live suite passed: 428 tests. Paid smoke tests are opt-in.

A wheel built from this change was also checked outside the source checkout: all four model specs, both presets, payload construction, resolution aliases, and pricing loaded successfully from packaged resources.

On 2026-09-09, all four live smoke paths succeeded with `aspect_ratio: 1:1` and `resolution: 1K`. Each returned a 1254×1254 PNG. Both T2I results showed a blue mug; both I2I results changed it to red while preserving the composition. Submission, status polling, I2I upload preparation, downloaded originals, web previews, thumbnails, and run artifacts were verified. Each run observed a 6-credit balance decrease (24 credits total).

| Model | Live task ID |
| --- | --- |
| `gpt-image-2-5-flare-text-to-image` | `c825deb440cc60a67f254431c5f3bc06` |
| `gpt-image-2-5-flare-image-to-image` | `2b69c6264326824ffb38af567827a4ea` |
| `gpt-image-2-5-sunburst-text-to-image` | `fd377df57a68f29ac8e31fcbf1cbc5da` |
| `gpt-image-2-5-sunburst-image-to-image` | `4f97a7d5d981ca234fdb82f6a0b1fefd` |

Local evidence is stored under `outputs/gpt_image_2_5_onboarding_2026_09_09/verification.json` and its `artifacts/` directory; these outputs are intentionally excluded from version control. High-resolution combinations and maximum-reference behavior still require separate live coverage. Callback delivery was not exercised; polling was verified.

To repeat the four 1K submit/upload/status/download checks with an existing `KIE_API_KEY` environment variable (estimated 24 credits total):

```bash
KIE_RUN_LIVE_SMOKE=1 KIE_SMOKE_ALLOW_GPT_IMAGE_25=1 \
  python -m pytest -q -s tests/smoke/test_live_api_smoke.py -k gpt_image_25
```

Media Studio installation, model discovery, option rendering, and composer validation are a separate downstream integration step.

## Sources

- [Kie market page](https://kie.ai/gpt-image-2-5)
- [Flare T2I](https://docs.kie.ai/market/gpt/gpt-image-2-5-flare-text-to-image)
- [Flare I2I](https://docs.kie.ai/market/gpt/gpt-image-2-5-flare-image-to-image)
- [Sunburst T2I](https://docs.kie.ai/market/gpt/gpt-image-2-5-sunburst-text-to-image)
- [Sunburst I2I](https://docs.kie.ai/market/gpt/gpt-image-2-5-sunburst-image-to-image)
