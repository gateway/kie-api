# Prompt Wrapper Flow

This package already stores built-in prompt presets and rendered system prompts. A wrapper should not hardcode those rules in its own repo.

## Recommended wrapper sequence

1. Build a `RawUserRequest`.
2. Call `normalize_request(...)`.
3. Call `resolve_prompt_context(...)`.
4. Send `ResolvedPromptContext.rendered_system_prompt` plus `ResolvedPromptContext.raw_prompt` to your wrapper-side LLM skill.
5. Take the returned enhanced prompt text and apply it with `apply_enhanced_prompt(...)`.
6. Re-run `validate_request(...)` if the prompt text changed.
7. Preflight, prepare/upload, submit, and wait as normal.

## What `resolve_prompt_context(...)` gives you

It resolves:
- the model key
- provider model
- task mode
- prompt policy
- input pattern
- requested prompt preset key, if any
- model default prompt preset key
- resolved preset key, label, version, and rules
- raw preset template
- rendered system prompt
- resolution source
- system prompt source: `profile`, `override`, or `none`

That means a wrapper can stay thin and avoid duplicating preset lookup or template rendering rules.

## Wrapper-oriented example

```python
from kie_api import (
    apply_enhanced_prompt,
    normalize_request,
    resolve_prompt_context,
)
from kie_api.models import RawUserRequest

request = RawUserRequest(
    model_key="kling-3.0-t2v",
    prompt="A polished launch trailer with smooth camera movement.",
    enhance=True,
)

normalized = normalize_request(request)
context = resolve_prompt_context(normalized)

# wrapper-side LLM call
system_prompt = context.rendered_system_prompt or ""
enhanced_prompt = "Polished launch trailer, smooth cinematic camera movement, ..."

ready_for_submit = apply_enhanced_prompt(
    normalized,
    enhanced_prompt,
    enhanced_prompt=enhanced_prompt,
)
```

## Explicit overrides

If your wrapper wants to override the preset or system prompt for one request, it can set them directly on `RawUserRequest`:

```python
request = RawUserRequest(
    model_key="nano-banana-2",
    prompt="Turn this into a clean ad image.",
    prompt_preset_key="nano_banana_2_image_edit_v1",
    system_prompt_override="Use the house style system prompt for ad cleanup.",
)
```

Override rules:
- `system_prompt_override` wins over the profile markdown body
- `prompt_profile_key` / `prompt_preset_key` wins over the model spec default preset
- if neither is set, `kie-api` resolves the built-in preset from model + mode + input pattern

## Important payload rule

`build_submission_payload(...)` uses `NormalizedRequest.final_prompt_used` first, then falls back to `NormalizedRequest.prompt`.

That means if your wrapper enhances the prompt externally, it should apply the final prompt through `apply_enhanced_prompt(...)` before submission.

## What this does not do

- It does not call an LLM by itself unless you inject a backend into `PromptEnhancer`.
- It does not implement a Control API.
- It does not persist prompt history outside the local artifact bundle system.
