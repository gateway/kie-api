# Agent Skills

This repo now ships two separate agent-skill bundles because Codex and Claude Code use different formats.

## Why two formats?

### Codex

In the current Codex environment, skills are folder-based bundles with a required `SKILL.md` file and optional bundled resources.

Repo path:

```text
agent_skills/codex/<skill-name>/SKILL.md
```

Install them locally with:

```bash
python3 scripts/install_codex_skills.py
```

### Claude Code

Claude Code project-level subagents are Markdown files with YAML frontmatter stored under:

```text
.claude/agents/*.md
```

Anthropic documents this format here:
- [Claude Code settings](https://docs.anthropic.com/en/docs/claude-code/settings)
- [Claude Code subagents](https://docs.anthropic.com/en/docs/claude-code/sub-agents)

## Included starter skills

Codex:
- `kie-find-latest-media`
- `kie-check-credits`
- `kie-nano-banana`
- `kie-kling-video`
- `kie-chain-image-to-video`

Claude Code:
- `.claude/agents/kie-find-latest-media.md`
- `.claude/agents/kie-check-credits.md`
- `.claude/agents/kie-nano-banana.md`
- `.claude/agents/kie-kling-video.md`
- `.claude/agents/kie-chain-image-to-video.md`

## What these skills do

### `kie-check-credits`
- verifies that the key is loaded
- checks remaining credits
- stops before paid generation
- points users to [Kie.ai](https://kie.ai?ref=e7565cf24a7fad4586341a87eaf21e42) if they need to top up

### `kie-nano-banana`
- supports prompt-only image generation
- supports image edit flows
- surfaces missing fields
- estimates cost before submit

### `kie-kling-video`
- supports text-to-video
- supports first-frame image-to-video
- supports first-last-frame flows
- warns about higher-cost video runs

### `kie-chain-image-to-video`
- generates an image first
- then feeds that image into Kling
- stores both artifacts

### `kie-find-latest-media`
- finds the latest image or video without rerunning generation
- reads the artifact index and manifest layer
- returns direct file paths so the user does not need to hunt

## Standard result contract

Generation skills should return the actual media, not just a success message.

For successful runs, return as many of these as are available:
- provider task id
- final remote output URL
- local downloaded file path
- artifact folder path
- hero asset paths
  - image runs: original, web, thumb
  - video runs: original, web, poster

This repo already has the artifact system to support that:
- `outputs/index.jsonl`
- per-run `manifest.json`
- per-run `run.json`
- artifact query helpers like `get_latest_assets(...)`

## Current limitation

These skills do not replace your wrapper or Control API. They are structured operating instructions for agents. The library itself already provides:
- validation
- missing-input reporting
- default application
- cost estimation
- upload-first submission flow

The skills sit on top of that logic and tell an agent how to use it.
