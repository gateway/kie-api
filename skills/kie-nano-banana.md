# Skill: kie-nano-banana

Use this workflow when the user wants image generation or image editing with Nano Banana Pro or Nano Banana 2.

## What this skill is for

Use this when you want:
- prompt-only image generation
- image editing with one or more reference images
- a low-cost first live KIE test

## Recommended first proof path

1. Load `KIE_API_KEY`
2. Check credit balance first
3. Run a simple `nano-banana-2` request
4. Wait for completion
5. Download the output
6. Create a run artifact bundle

## Recommended model choice

- Start with `nano-banana-2` for the cheapest practical image test
- Use `nano-banana-pro` when you want the stronger variant and accept higher cost

## Validation rules to remember

- validation happens before upload/submit
- Nano Banana Pro allows up to 8 reference images
- Nano Banana 2 allows up to 14 reference images
- if media count is invalid, the run should stop before any upload happens

## Prompt flow

Recommended wrapper flow:
1. `normalize_request(...)`
2. `resolve_prompt_context(...)`
3. external prompt enhancement if desired
4. `apply_enhanced_prompt(...)`
5. `validate_request(...)`
6. `prepare_request_for_submission(...)`
7. `submit_prepared_request(...)`
8. `wait_for_task(...)`

## First live test

Credit check:

```bash
. .venv/bin/activate
set -a
source .env.live
set +a
python examples/check_credit_balance.py
```

Then use:

```bash
python examples/live_run_guarded.py
```

## Example prompt

`Create a clean premium editorial illustration of a professional pilot looking frustrated while checking a phone, with soft branded background tones and lots of negative space.`
