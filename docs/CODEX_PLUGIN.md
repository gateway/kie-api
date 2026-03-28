# Codex Plugin

This repo now includes a lightweight Codex plugin package under:

```text
plugins/kie-ai-workflows
```

## What it is

The plugin packages the existing Codex Kie.ai workflow skills into a repo-local plugin structure so Codex users can install and discover them through a cleaner plugin entry point.

It is intentionally lightweight:
- no MCP server
- no apps manifest
- no extra service layer
- just a plugin manifest plus bundled skills and onboarding docs

## Included plugin skills

- `kie-start-here`
- `kie-check-credits`
- `kie-nano-banana`
- `kie-kling-video`
- `kie-chain-image-to-video`
- `kie-find-latest-media`

## First-run experience

The recommended first-run path is:

1. configure `KIE_API_KEY`
2. run `kie-check-credits`
3. run `kie-nano-banana`
4. then move on to Kling or chained media flows

## Why this exists

The repo already had:
- the Python toolkit
- the docs
- the Codex skills

The plugin is a packaging layer that makes those easier to discover and reuse.

## Marketplace file

The repo also includes a local marketplace entry:

```text
.agents/plugins/marketplace.json
```

This points Codex at:

```text
./plugins/kie-ai-workflows
```

## Current limitations

- this is a first-pass local plugin package
- it does not add new runtime capabilities beyond the existing skills
- it does not bundle screenshots or custom icons yet
- it assumes the user still needs to configure a valid Kie.ai API key
