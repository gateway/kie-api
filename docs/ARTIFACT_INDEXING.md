# Artifact Indexing

The artifact subsystem uses three layers of metadata:

## 1. `run.json`

This is the full per-run truth.

Use it when you need:
- complete prompt details
- full input/output asset records
- provider trace paths
- warnings/errors/defaults
- derivative settings
- source metadata and source context

## 2. `manifest.json`

This is the per-run summary for fast browsing.

It now includes:
- `run_id`
- `created_at`
- `status`
- `model_key`
- `task_mode`
- `hero_original`
- `hero_output_path`
- `hero_web`
- `hero_thumb`
- `prompt_summary`
- `tags`
- `input_count`
- `output_count`
- `has_video`
- `has_image`
- `duration_seconds`
- `run_folder`

Use it for:
- dashboard cards
- quick previews
- list views
- lightweight run summaries

## 3. `outputs/index.jsonl`

This is the cross-run summary layer.

Each line is one `RunIndexEntry`.

It is intentionally compact but dashboard-friendly:
- `run_id`
- `created_at`
- `status`
- `model_key`
- `task_mode`
- `tags`
- `prompt_summary`
- `hero_original`
- `hero_output`
- `hero_web`
- `hero_thumb`
- `input_count`
- `output_count`
- `has_video`
- `has_image`
- `duration_seconds`
- `run_path`

## Duplicate-safe append

`append_run_index(...)` is duplicate-safe by `run_id`.

If a matching `run_id` already exists in `index.jsonl`, the helper does not append a second copy.

## Rebuilding the index

If `outputs/index.jsonl` is missing or stale:

```python
from kie_api import rebuild_run_index

rebuild_run_index()
```

This rescans artifact folders, loads `run.json` and `manifest.json`, rebuilds the index, and writes a fresh `index.jsonl`.

## Intended use

- `run.json`: archival truth
- `manifest.json`: per-run browse summary
- `index.jsonl`: cross-run browse/query summary

This is filesystem-only and intentionally simple. It is designed so a future dashboard or agent can list and filter runs without loading every `run.json` manually.
