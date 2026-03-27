# Getting Started

This guide takes you from a fresh checkout to a working local `kie-api` setup.

## 1. Clone and enter the repo

```bash
git clone <your-repo-url> kie-api
cd kie-api
```

## 2. Create a virtual environment

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

## 3. Add your KIE API key locally

Never commit your key.

This repo ignores local env files such as `.env.live`. Use the tracked example file as your template:

```bash
cp .env.example .env.live
```

Edit `.env.live` and set your real key:

```bash
KIE_API_KEY=your-real-kie-key
```

Load it into your current shell:

```bash
set -a
source .env.live
set +a
```

If you prefer, you can export the key directly instead:

```bash
export KIE_API_KEY="your-real-kie-key"
```

## 4. Run the local test suite

```bash
. .venv/bin/activate
python -m pytest
python scripts/sync_packaged_specs.py --check
```

## 5. Try a dry-run example

These examples do not require spending credits:

```bash
. .venv/bin/activate
python examples/normalize_and_validate.py
python examples/dry_run_with_prompt_enhancement.py
python examples/wrapper_prompt_flow.py
python examples/dry_run_cost_estimate.py
```

## 6. Try a live image flow

If your key is loaded, start with the low-cost image path:

```bash
. .venv/bin/activate
python examples/check_credit_balance.py
python examples/live_run_guarded.py
```

Recommended live sequence:
1. credit check
2. upload-first prepare
3. Nano Banana 2 image run
4. wait for completion
5. download outputs
6. create artifact bundle

If you want the fastest confidence check, the credit call is the first one to run. It proves:
- your key is valid
- your shell environment is loaded correctly
- the library can talk to KIE successfully

## 7. Where outputs go

Run artifacts are stored under:

```text
outputs/YYYY-MM-DD/RUN_ID/
```

Each bundle includes:
- `run.json`
- `manifest.json`
- `notes.md`
- copied inputs
- original outputs
- web derivatives
- thumbnails or posters
- provider logs when available

Cross-run browsing uses:

```text
outputs/index.jsonl
```

## 8. Most important docs

- `README.md`
- `docs/CONFIGURATION.md`
- `docs/LIBRARY_USAGE.md`
- `docs/END_TO_END_FLOW.md`
- `docs/PROMPT_WRAPPER_FLOW.md`
- `docs/RUN_ARTIFACTS.md`
- `docs/ARTIFACT_QUERYING.md`
- `docs/MODEL_ONBOARDING.md`

## 9. Basic usage pattern

The recommended wrapper flow is:

1. `normalize_request(...)`
2. `resolve_prompt_context(...)`
3. external LLM enhancement if desired
4. `apply_enhanced_prompt(...)`
5. `validate_request(...)`
6. `prepare_request_for_submission(...)`
7. `submit_prepared_request(...)`
8. `wait_for_task(...)`
9. `download_output_file(...)`
10. `create_run_artifact(...)`

## 10. KIE links

Primary KIE links used by this repo:
- [KIE.AI](https://kie.ai)
- [Models Market](https://kie.ai/market)
- [Pricing](https://kie.ai/pricing)

If you later want to swap those links for an affiliate URL in your own wrapper or dashboard, do that in your app layer or docs layer. Keep the library itself neutral.
