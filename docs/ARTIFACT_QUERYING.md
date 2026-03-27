# Artifact Querying

The artifact query layer is filesystem-backed and index-first.

Use these public helpers from `kie_api`:
- `list_recent_runs(...)`
- `list_runs_by_model(...)`
- `list_runs_by_status(...)`
- `list_runs_by_tag(...)`
- `get_run_by_id(...)`
- `get_latest_successful_run(...)`
- `get_latest_assets(...)`
- `load_run_artifact(...)`
- `get_run_summary(...)`
- `rebuild_run_index(...)`

## How querying works

### Index-first browsing

These helpers read `outputs/index.jsonl`:
- `list_recent_runs(...)`
- `list_runs_by_model(...)`
- `list_runs_by_status(...)`
- `list_runs_by_tag(...)`
- `get_latest_successful_run(...)`
- `get_latest_assets(...)`

That keeps browsing cheap and avoids opening every `run.json`.

### Full run loading

These helpers read full per-run files:
- `get_run_by_id(...)`
- `load_run_artifact(...)`
- `get_run_summary(...)`

Use these only when you need details beyond the index entry.

## Examples

List recent runs:

```python
from kie_api import list_recent_runs

for entry in list_recent_runs(limit=10):
    print(entry.model_dump())
```

Filter by model:

```python
from kie_api import list_runs_by_model

for entry in list_runs_by_model("nano-banana-2", limit=5):
    print(entry.run_id, entry.hero_thumb)
```

Get the latest successful run:

```python
from kie_api import get_latest_successful_run

entry = get_latest_successful_run()
print(entry.model_dump() if entry else None)
```

Get the latest assets for one model:

```python
from kie_api import get_latest_assets

print(get_latest_assets(model_key="nano-banana-pro"))
```

Load one run folder:

```python
from kie_api import get_run_summary, load_run_artifact

summary = get_run_summary("/absolute/path/to/run_dir")
run = load_run_artifact("/absolute/path/to/run_dir")

print(summary.hero_web)
print(run.provider_trace.task_id)
```

## Dashboard usage guidance

For dashboard list pages:
- use `index.jsonl`
- show `hero_thumb`
- show `prompt_summary`
- show `model_key`, `status`, `tags`, and `created_at`

For dashboard detail pages:
- load `manifest.json` first
- load `run.json` only when detailed asset and provider metadata is needed

## Current limits

- no full-text search
- no database-backed filtering
- no pagination beyond simple Python slicing
- no live file watch or auto-refresh mechanism

This is a first-pass local browsing layer, not a search service.
