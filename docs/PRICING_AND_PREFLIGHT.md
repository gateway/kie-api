# Pricing and Preflight

The pricing layer is intentionally dry-run-safe and provenance-aware.

## Where pricing data lives

Versioned pricing snapshots live under:

- `src/kie_api/resources/pricing/*.yaml`

Current default snapshot:

- `src/kie_api/resources/pricing/2026-03-26_site_pricing_page.yaml`

## Important honesty rule

The default snapshot is sourced from KIE's public site pricing API. It is live-observed site pricing, not a verified billing contract.

Use it for:
- local cost estimation
- warning thresholds
- confirmation thresholds
- wrapper-level UX planning

Do not treat it as verified provider billing unless the snapshot notes explicitly say so.

## Estimate semantics

`EstimatedCost` now separates these states:
- `has_numeric_estimate`: the library has a numeric planning estimate
- `is_authoritative`: the estimate is backed by provider-authoritative billing data
- `is_known`: shorthand for provider-authoritative pricing only

That means a site-pricing snapshot can produce:
- `has_numeric_estimate=true`
- `is_authoritative=false`
- `is_known=false`

This is deliberate. Dry-run preflight can still use the numeric estimate for planning, but wrappers should not treat it as verified KIE billing.

## Snapshot structure

Each rule can define:
- `model_key`
- `pricing_status`
- `billing_unit`
- `provider`
- `interface_type`
- `anchor_url`
- `raw_credit_text`
- `raw_usd_text`
- `base_credits`
- `base_cost_usd`
- `multipliers`
- `adders_credits`
- `adders_cost_usd`
- `observed_at`
- `source_row_labels`
- `source_anchor_urls`
- `notes`

Each snapshot can also report coverage metadata:
- `priced_model_keys`
- `missing_model_keys`
- `unmapped_source_rows`

Wrappers should pass this metadata through when they expose pricing status to an operator. `missing_model_keys` means a supported model exists without a numeric pricing rule. `unmapped_source_rows` means KIE published rows that matched the known registry/provider surface but were not safe to attach to a model rule.

## How to change pricing without Python code

1. Edit the YAML snapshot file under `src/kie_api/resources/pricing/`.
2. Adjust base values or multipliers.
3. Run tests:

```bash
. .venv/bin/activate
python -m pytest
```

## Dry-run helpers

Public helpers:
- `estimate_request_cost(...)`
- `run_preflight(...)`

Service-layer helpers:
- `PricingRegistry`
- `PreflightService`
- `CreditGuard`

`CreditGuard` is now request-aware. Pass a `NormalizedRequest` when you need option-sensitive pricing behavior. Passing only a model key remains supported for compatibility, but it emits warnings because request-specific adjustments may be missing.

## Threshold behavior

Optional settings:
- `KIE_WARN_CREDIT_THRESHOLD`
- `KIE_CONFIRM_CREDIT_THRESHOLD`
- `KIE_WARN_COST_USD_THRESHOLD`
- `KIE_CONFIRM_COST_USD_THRESHOLD`

Preflight decisions:
- `allow`
- `warn`
- `require_confirmation`
- `reject`

## Remaining credits

Preflight can optionally check remaining credits only if:
- a `KIE_API_KEY` is present
- an upstream balance fetcher is injected

This repo now includes a KIE credit probe client, but the endpoint still needs verification against a real authenticated response in this environment.

## Optional pricing refresh scaffolding

`src/kie_api/services/pricing_refresh.py` now prefers KIE's public site pricing API discovered from the `https://kie.ai/pricing` page bundle:
- `GET https://api.kie.ai/client/v1/model-pricing/count`
- `POST https://api.kie.ai/client/v1/model-pricing/page`

That code is:
- optional
- site-derived
- not authoritative
- not a replacement for a verified billing API contract

Current examples:
- Seedance 2.0 Standard pricing is derived from the public site pricing API rows for:
  - `480p` vs `720p` vs `1080p`
  - `with video input` vs `no video input`
- Seedance 2.0 Fast uses the same request-shape pricing rule, but only maps the public `480p` and `720p` Fast rows because KIE does not publish Fast `1080p` rows.
- the runtime turns that into a dry-run `pricing_variant` internally based on request shape, so wrappers do not need to send pricing-only fields
- Kling 3.0 video pricing is now derived from public site rows for 720P, 1080P, and 4K, with mode plus sound modeled as an internal `pricing_variant` because 4K rows do not add a separate audio surcharge.
- GPT Image 2 text-to-image and image-to-image pricing is now mapped generically from KIE rows that share the same model anchor and publish `1k`, `2k`, and `4k` resolution labels:
  - `1K`: 6 credits / $0.03
  - `2K`: 10 credits / $0.05
  - `4K`: 16 credits / $0.08

The refresh builder first handles model-specific rows where pricing requires custom option semantics, then falls back to registry-driven image-resolution mapping by `model_key`, `provider_model`, `?model=...` anchor values, and normalized row descriptions.

Manual candidate refresh:

```bash
. .venv/bin/activate
python scripts/refresh_site_pricing_snapshot.py --output /tmp/kie-site-pricing.yaml
```

Directly install a refreshed snapshot into the bundled pricing resource directory:

```bash
. .venv/bin/activate
python scripts/refresh_site_pricing_snapshot.py --install
```

Suno pricing is currently kept as `unknown` on purpose when the public KIE pricing API does not
publish a matching music row. That allows the model to stay registered and visible to preflight
without fabricating a numeric estimate.
