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
- detect image output MIME type from content and correct the archived extension when needed; keep the source filename in metadata
- preserve alpha in preview formats that support it, including palette transparency
- preserve the original animated GIF and create an animated web preview (WebP by default) plus a static first-frame thumbnail. A frame count and total canvas pixel budget bound inspection and preview work.
- preserve SVG bytes as a download; the SDK does not render SVG or point preview fields to it
- if an image preview cannot be made, retain the original and run metadata, record the warning, and leave the preview fields empty

Captured metadata includes:
- width
- height
- mime type
- bytes
- sha256

GIF originals and animated previews report `metadata.is_animated`, `metadata.frame_count`, and `metadata.loop_count`. The loop count is the total number of plays, with zero for continuous playback. A GIF without a loop extension plays once. The record's `duration_seconds` measures one cycle from the encoded frame delays. The manifest uses that duration when the animation is the first output. Static thumbnails have one frame and no playback duration. If animation inspection fails or reaches the budget, the original stays available and `metadata.animation_metadata_incomplete` flags missing details.

## Video derivatives

Video derivatives use `ffmpeg`. KIE API first uses a system `ffmpeg` binary when one is available, then falls back to the `imageio-ffmpeg` binary installed with the Python environment. `ffprobe` is optional and is only used for richer video metadata when it is available on `PATH`.

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
- optional `ffprobe` for duration, dimensions, and codec metadata

If `ffmpeg` is unavailable, video derivative generation raises a clear library error instead of silently pretending success. If only `ffprobe` is unavailable, derivatives are still generated and video metadata falls back to mime type, byte size, and sha256.

## Relative paths in metadata

When derivatives are written through `create_run_artifact(...)`, metadata paths are stored relative to the run folder when practical:
- `original/output_01.png`
- `web/output_01.webp`
- `thumb/output_01.webp`

That keeps artifacts portable and easy to move or inspect.

## Current limitations
- animated previews are generated from GIF sources
- no adaptive bitrate ladders
- no parallelized transcode queue
- no content-aware crop strategy
- no poster frame selection heuristics beyond a simple early frame
