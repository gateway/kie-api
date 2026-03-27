# Skills

This repo ships lightweight workflow guides under `skills/` to help operators and agents use the library consistently.

Current bundled skills:
- `skills/kie-nano-banana.md`
- `skills/kie-kling-video.md`
- `skills/kie-kling-motion.md`

## What they are

These are not executable plugins. They are concise operator guides for:
- which model family to use
- which workflow shape to follow
- what to validate before spending credits
- what the first safe test should be

## Suggested use

If you are using an LLM wrapper or a tool-driven agent, route by intent:
- Nano Banana image generation/editing -> `kie-nano-banana`
- Kling text/image video generation -> `kie-kling-video`
- Kling motion transfer -> `kie-kling-motion`

## Recommended future direction

If you later want a richer skill/help system in your Control API or dashboard:
- keep these repo guides as the source workflow notes
- let your Control API expose them as help text
- add per-skill example prompts and “first live test” recipes
- optionally store enabled/disabled preset guidance in your Control API database

For now, these skill files are intentionally simple and local to the library repo.
