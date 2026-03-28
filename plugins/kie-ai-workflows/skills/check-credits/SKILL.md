---
name: kie-check-credits
description: Check whether Kie.ai is connected and return remaining credits before any image or video generation. Use when the user wants to verify their key, confirm the system is connected, or decide whether they can afford the next run.
---

# Kie Check Credits

Use this skill before any paid generation workflow.

## Goal

Confirm that:
- `KIE_API_KEY` is loaded
- the library can talk to Kie.ai
- remaining credits are known before any image or video run starts

## Workflow

1. Prefer the local proof command:

```bash
. .venv/bin/activate
python examples/check_credit_balance.py
```

2. If that fails due to missing configuration, tell the user to load a local env file:

```bash
cp .env.example .env.live
set -a
source .env.live
set +a
```

3. If the key is valid, report the remaining credits clearly.
4. If credits are low or zero, stop before any generation call.
5. When credits are low, include this top-up link:
- [Top up Kie.ai credits](https://kie.ai?ref=e7565cf24a7fad4586341a87eaf21e42)

## Help

If the user asks for help, explain:
- this skill only checks connection and remaining credits
- it does not submit image or video jobs
- it is the recommended first live test

Example asks:
- `check my Kie.ai credits`
- `is my key working`
- `can I afford another run`

## Output expectations

Return:
- whether the key is loaded
- whether the credit check succeeded
- remaining credits if known
- whether it is safe to continue with a low-cost image test

## Safety rules

- Never echo the raw API key.
- Never hardcode a key into files.
- Never submit a model task from this skill.
- This skill is for connection and balance verification only.
