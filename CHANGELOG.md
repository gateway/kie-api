# Changelog

## 0.2.0 — 2026-11-10

- Add GPT Image 2.6 Flare and Sunburst text-to-image and image-to-image model cards, packaged specs, and prompt profiles.
- Validate expanded image controls, reference limits, masks, markup, GIF and SVG options, including hosted input bytes before submission.
- Preserve GIF animation metadata and animated previews; keep SVG originals download-only.
- Ship published token pricing with explicit unknown per-request estimates; preserve token rules during catalog refresh.
- Document settings, validation, live-tested combinations, and downstream integration limits.

Verification: 509 offline tests passed; nine live generation/edit tasks passed. Live coverage is scoped in the GPT Image 2.6 settings guide. No Media Studio changes are included.
