# Derivatives

This package creates lightweight derivatives for local run artifacts.

The derivative strategy is intentionally simple:
- originals are archival truth
- web derivatives are for detail views
- thumbs/posters are for galleries and previews

Derivative behavior can be tuned with `ArtifactDerivativeSettings`.

## Image derivatives

Image derivatives use Pillow.

Default behavior:
- web derivative: WEBP, max dimension `1600`, quality `82`
- thumb derivative: WEBP, max dimension `384`, quality `76`

Rules:
- preserve aspect ratio
- auto-orient with EXIF transpose
- do not upscale smaller images unless explicitly configured

Captured metadata includes:
- width
- height
- mime type
- bytes
- sha256

## Video derivatives

Video derivatives use `ffmpeg` and `ffprobe`.

Default behavior:
- web video: MP4, H.264, browser-friendly, max width `1280`
- poster: single extracted frame, default output `.jpg`, target width around `640`

Rules:
- preserve original aspect ratio
- do not overwrite originals
- capture duration, width, height, codec, mime type, bytes, sha256

Current first-pass ffmpeg choices:
- `libx264`
- `yuv420p`
- `+faststart`
- `aac` audio for the web derivative

These are practical defaults, not a full production transcoding policy.

## Dependency expectations

Image derivatives require:
- Pillow

Video derivatives require:
- `ffmpeg`
- `ffprobe`

If `ffmpeg` or `ffprobe` are unavailable, video derivative generation raises a clear library error instead of silently pretending success.

## Relative paths in metadata

When derivatives are written through `create_run_artifact(...)`, metadata paths are stored relative to the run folder when practical:
- `original/output_01.png`
- `web/output_01.webp`
- `thumb/output_01.webp`

That keeps artifacts portable and easy to move or inspect.

## Current limitations
- no animated image derivatives
- no adaptive bitrate ladders
- no parallelized transcode queue
- no content-aware crop strategy
- no poster frame selection heuristics beyond a simple early frame
