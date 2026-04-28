# Contributing

Thanks for helping improve the Kie.ai Python Workflow Toolkit.

## Setup

Use a local virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Create local environment variables for live Kie.ai calls:

```bash
export KIE_API_KEY="replace-with-your-kie-api-key"
```

Do not commit `.env`, `.env.live`, generated outputs, downloaded media, or account-specific artifacts.

## Development Rules

- Keep model onboarding spec-first: update model specs, registry wiring, request validation, pricing/credit behavior, and tests together.
- Preserve the public API where possible. If a breaking change is required, document the migration path.
- Use placeholder credentials and fixture paths in docs, tests, skills, and examples.
- Keep Codex, Claude, plugin, and agent docs public-safe. They are part of the product surface, but should not include private operator notes or local machine details.
- Do not commit generated run outputs unless they are intentionally small fixtures.

## Checks

Before submitting a change, run the focused tests for the area you touched. For broad registry or request-flow changes, run:

```bash
pytest
```

For docs-only changes, a secret/path scan is usually enough:

```bash
git grep -I -n -E "/(Users|home)/" -- .
git grep -I -n -E "AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9_]{20,}|PRIVATE KEY" -- .
```

## Pull Requests

Open pull requests with:
- a short summary of the behavior change
- the model families or workflows affected
- tests or scans run
- any docs updated
