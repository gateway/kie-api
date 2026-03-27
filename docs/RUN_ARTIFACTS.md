# Run Artifacts

This repo includes a first-pass local run artifact bundle system for completed or failed media runs.

The goal is simple:
- keep originals intact
- generate lightweight derivatives for browsing
- write machine-readable metadata
- write a small append-only global index

This is intentionally local filesystem infrastructure, not a production media pipeline.

## Default folder shape

```text
outputs/
  index.jsonl
  2026-03-26/
    20260326_214512_nano_banana_pro_cinematic_v01/
      run.json
      manifest.json
      notes.md
      request.json
      prompt.txt
      prompt_enhanced.txt
      inputs/
        ref_01.png
        motion_01.mp4
      original/
        output_01.png
        output_02.mp4
      web/
        output_01.webp
        output_02.mp4
      thumb/
        output_01.webp
        output_02_poster.jpg
      logs/
        submit_payload.json
        submit_response.json
        status_response_final.json
```

The exact files depend on what data is available for the run.

## Optional source and tag metadata

Artifact bundles can also carry optional context for future dashboards and agents:
- tags
- source type
- source user
- source channel
- source agent
- project name
- notes

This data is stored in `run.json`, summarized in `manifest.json`, and partially carried into `index.jsonl`.

## Derivative settings

Derivative behavior is configurable with `ArtifactDerivativeSettings`, including:
- image web max dimension/format/quality
- image thumb max dimension/format/quality
- video web width
- video poster width/format
- allow-upscale toggle
- sha256 enable/disable

## Naming rules

Run folders are named:

```text
YYYYMMDD_HHMMSS_model_key_optional_slug
```

Example:

```text
20260326_214512_nano_banana_pro_cinematic_v01
```

This sorts naturally by time.

## Core metadata files

### `run.json`

The full machine-readable artifact record. It includes:
- run id and created time
- model key and provider model
- task mode if known
- prompt record
- copied inputs
- copied outputs
- derivative paths and metadata
- options/defaults
- provider trace
- warnings/errors/tags

### `manifest.json`

A smaller summary optimized for fast browsing and future dashboard consumption. It includes:
- run id
- created time
- model key
- status
- hero output path
- thumbnail path
- prompt summary
- tags
- output count

### `notes.md`

A human-readable snapshot for quick inspection.

## Global index

Each completed artifact can append one JSON object to:

```text
outputs/index.jsonl
```

Each line is intentionally small:
- run id
- created time
- model key
- status
- hero output
- hero thumb
- prompt summary
- tags
- run path

This is designed so a future dashboard or agent can scan recent runs without opening every folder.

## Public entry points

Use these public helpers:
- `create_run_artifact(...)`
- `generate_image_derivatives(...)`
- `generate_video_derivatives(...)`
- `append_run_index(...)`

Typed models live under `kie_api.artifacts.models`.

## Failed runs are supported

Artifacts are not success-only.

A failed run can still produce:
- `run.json`
- `manifest.json`
- `notes.md`
- copied inputs
- provider logs
- warnings and errors

That means wrappers can preserve evidence even when generation does not complete.

## What is implemented
- predictable run folder creation
- copied input and output originals
- image derivatives
- video web derivatives and posters
- structured metadata files
- append-only `index.jsonl`

## What is not implemented
- deduplicated asset storage
- cloud sync
- database indexing
- background media processing queues
- resumable transcoding
- cleanup/retention policy
