# Control API Integration Notes

This repo does not implement a Control API. It exposes reusable contracts and helpers that a separate upstream system can wrap.

## Recommended upstream flow
1. Receive a user-facing media request.
2. Choose or confirm a target model.
3. Build a `RawUserRequest`-shaped payload.
4. Normalize with `normalize_request(...)` or `RequestNormalizer`.
5. Validate with `validate_request(...)` or `RequestValidator`.
6. If validation returns `needs_input`, surface `missing_inputs` back to the caller.
7. If validation returns `ready_with_defaults` or `ready_with_warning`, decide whether to surface the defaults and warnings to the caller before submission.
8. Optionally run `PromptEnhancer` based on the upstream prompt policy.
9. Run pricing and credit checks before submission.
10. Call `prepare_request_for_submission(...)` so all input image, video, and audio refs are uploaded first.
11. Submit with `submit_prepared_request(...)`.
12. Poll with `wait_for_task(...)` or consume callbacks with `StatusClient`.
13. Use the final output URL(s) from `StatusResult.output_urls`.
14. Optionally save the returned asset locally with `download_output_file(...)`.

## Recommended request contract into this package
Upstream request objects should map cleanly to `RawUserRequest`.

```json
{
  "model_key": "kling-3.0",
  "task_mode": null,
  "prompt": "A premium launch trailer with strong camera movement.",
  "images": ["https://example.com/start.png"],
  "videos": [],
  "audios": [],
  "options": {
    "duration": 5,
    "mode": "pro"
  },
  "enhance": true,
  "prompt_policy": "auto",
  "prompt_profile_key": null,
  "system_prompt_override": null,
  "callback_url": "https://control.example.com/kie/callback",
  "metadata": {
    "upstream_job_id": "job_123"
  }
}
```

Notes:
- `model_key` should be explicit when possible.
- Family keys like `kling-3.0` are supported when the input shape allows safe normalization to a specific model spec.
- `options` should stay provider-agnostic where possible. The package normalizes names like `aspect-ratio` to `aspect_ratio`.
- `enhance` and `prompt_policy` should be passed by the upstream system, not hardcoded inside transport code.
- `prompt_profile_key` is optional and lets the wrapper choose a specific built-in preset instead of the model default.
- `prompt_preset_key` may be accepted as an alias by the wrapper or a future dashboard API.
- `system_prompt_override` is optional and lets the wrapper inject a one-off rendered system prompt for an external LLM enhancement pass.

## Recommended response contract back to the Control API
The wrapper should treat `ValidationResult` as the main pre-submit contract.

```json
{
  "state": "ready_with_warning",
  "normalized_request": {},
  "missing_inputs": [],
  "defaulted_fields": [
    {
      "field": "multi_shots",
      "value": false,
      "source": "option_default",
      "reason": "Applied spec option default for 'multi_shots'."
    }
  ],
  "warning_details": [
    {
      "field": "aspect_ratio",
      "code": "provider_inferred_from_media",
      "message": "Option 'aspect_ratio' was omitted and will be inferred from image input by Kling 3.0 Image to Video."
    }
  ],
  "impossible_inputs": [],
  "errors": [],
  "warnings": [
    "Option 'aspect_ratio' was omitted and will be inferred from image input by Kling 3.0 Image to Video."
  ]
}
```

Use the `state` field as the primary branch:
- `ready`: submit directly
- `ready_with_defaults`: optionally show what was defaulted, then submit
- `ready_with_warning`: optionally show warnings, then submit
- `needs_input`: ask the user for the specific missing fields in `missing_inputs`
- `invalid`: surface the invalid combination or value from `impossible_inputs`

## How prompt enhancement should be passed in
Recommended upstream controls:
- `enhance=true` maps to `PromptPolicy.AUTO`
- `enhance=false` maps to `PromptPolicy.OFF`
- explicit `prompt_policy` from the wrapper should override `enhance`
- use `resolve_prompt_context(...)` to load the per-model rendered system prompt and preset metadata
- if the wrapper enhances prompts externally, call `apply_enhanced_prompt(...)` before payload build or submission

Recommended storage per upstream job:
- original user prompt
- resolved system prompt
- resolved preset key
- rendered preset template
- enhancement policy requested
- enhanced prompt, if any
- final prompt used for submission

The package already preserves:
- `raw_prompt`
- `enhanced_prompt`
- `final_prompt_used`

Recommended wrapper sequence:
1. `normalize_request(...)`
2. `resolve_prompt_context(...)`
3. call your LLM skill with `rendered_system_prompt` plus `raw_prompt`
4. `apply_enhanced_prompt(...)`
5. `validate_request(...)`
6. pricing / credit guard
7. `prepare_request_for_submission(...)`
8. submit and wait

## How to surface missing input back to chat systems
Map each `MissingInput` entry into a chat-safe follow-up prompt.

Example:
```json
{
  "state": "needs_input",
  "missing_inputs": [
    {
      "field": "video",
      "message": "Kling 3.0 Motion Control requires at least 1 video input(s).",
      "media_type": "video",
      "min_count": 1,
      "current_count": 0
    }
  ]
}
```

Suggested chat rendering:
- ask only for the missing thing
- preserve the already-chosen model
- avoid re-asking for prompt or options that already validated

Example user-facing follow-up:
- `Kling 3.0 motion control still needs one motion reference video. Upload a .mp4 or .mov clip to continue.`

## Pricing and credit checks before submission
Recommended order:
1. normalize
2. validate
3. prompt enhancement, if any
4. revalidate if enhancement changes prompt constraints
5. pricing estimate
6. credit guard
7. prepare/upload
8. submit
9. wait or callback
10. download final asset if your wrapper needs a local copy

Wrapper behavior:
- `GuardDecision.ALLOW`: submit
- `GuardDecision.WARN`: show warning or log it, then submit according to wrapper policy
- `GuardDecision.REQUIRE_CONFIRMATION`: ask the user or upstream policy engine to confirm
- `GuardDecision.REJECT`: stop and surface the reason

Important:
- treat `estimated_cost.has_numeric_estimate` as a planning signal
- treat `estimated_cost.is_authoritative` and `estimated_cost.is_known` as billing-truth signals
- a local policy estimate can be numerically useful while still being non-authoritative

## Future Control API preset precedence

When the Control API eventually owns editable preset CRUD in SQLite, the recommended precedence is:
1. explicit preset key in the request
2. active Control API database override
3. built-in `kie-api` default preset

`kie-api` should remain the source of truth for:
- preset rendering behavior
- model-aware input-pattern detection
- built-in fallback presets

The Control API should remain the source of truth for:
- CRUD
- dashboard editing
- version assignment
- org/project-specific override policy

## Suggested Control API endpoints
- `POST /projects/media/jobs`
- `GET /projects/media/jobs/{job_id}`
- `POST /projects/media/jobs/{job_id}/confirm-cost`
- `POST /projects/media/webhooks/kie`

## Contract boundaries
- Keep company auth, SQLite models, job persistence, webhook verification, and project orchestration outside this package.
- Persist the upstream job and prompt state in your own repo if you need audit history or retries.
- Preserve the raw KIE payloads returned by this package if you need provider debugging later.
- The package exposes callback verification helpers, but they still need confirmation against a real signed callback sample.

## Explicit non-goals in this repo
- No FastAPI routes
- No webhook server implementation
- No company-specific auth, tenancy, or database models
- No opinionated persistence layer
