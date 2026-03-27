
# AGENTS.md

## Purpose of this repo
This repo defines and implements the reusable `kie-api` Python integration layer.

It should contain:
- model specs
- model registry loader
- request normalizer
- prompt enhancement hooks
- upload service
- task submitter
- status checker
- pricing + credit guard support
- tests
- examples

It should not contain:
- company SQLite schema
- Control API FastAPI routes
- Slack/Discord/Telegram delivery code
- company-specific auth logic
- hardcoded secrets

## Source of truth
For model rules, always verify against:
1. Kie model page on `kie.ai`
2. the model Playground
3. the Playground API tab
4. `docs.kie.ai` as secondary reference

The Kie docs are useful, but may be stale or have naming/capitalization drift.
If a discrepancy is found, note it in the model spec and prefer the live Kie UI.

## Security
Never commit API keys.
Never hardcode secrets into examples or tests.
Use environment variables only.

## Build priorities
Phase 1:
1. registry
2. normalizer
3. upload service
4. task submitter
5. status checker

Phase 1.5:
6. prompt enhancement
7. missing-input handling
8. credit check
9. pricing registry
