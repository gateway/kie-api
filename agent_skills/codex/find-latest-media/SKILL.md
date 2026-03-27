---
name: kie-find-latest-media
description: Find the latest generated media from kie-api artifacts and index files. Use when the user wants the latest image, latest video, latest successful run, or wants media paths without rerunning generation.
---

# Kie Find Latest Media

Use this skill when the user wants to retrieve existing outputs instead of generating new ones.

## Goal

Find recent generated media quickly from:
- `outputs/index.jsonl`
- per-run `manifest.json`
- per-run `run.json` when deeper detail is needed

## Workflow

Prefer the artifact query layer:
1. `list_recent_runs(...)`
2. `list_runs_by_model(...)`
3. `list_runs_by_status(...)`
4. `get_latest_successful_run(...)`
5. `get_latest_assets(...)`

Load `run.json` only when the summary/index layer is not enough.

## Typical requests

- latest image
- latest video
- latest Nano Banana run
- latest Kling run
- latest successful run
- latest assets from a chained workflow

## Help

If the user asks for help, explain:
- this skill is for retrieval, not generation
- it reads the artifact index and run manifests
- it should be used when the user wants existing files quickly

Example asks:
- `show me the latest image`
- `find the latest Kling video`
- `what was the last successful run`

## Output expectations

Return:
- run id
- created_at
- model key
- status
- artifact folder path
- hero asset paths
- remote output URL if available in run metadata

If there are no matching runs, say that clearly instead of guessing.
