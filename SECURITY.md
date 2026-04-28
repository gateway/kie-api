# Security Policy

## Reporting a Vulnerability

Please report security issues through GitHub Security Advisories for this repository. If advisories are not available, open a minimal private report through the project maintainer before publishing details.

Do not open a public issue that includes:
- API keys, access tokens, webhook secrets, or account identifiers
- exploit payloads that can be directly reused against live systems
- private user media, prompts, outputs, or task IDs
- local machine paths that reveal personal or internal environments

## Secret Handling

This project talks to Kie.ai and may be used with live account credentials. Keep secrets in local environment variables or untracked local files only.

Expected local variables include:
- `KIE_API_KEY`
- `KIE_WEBHOOK_SECRET`, when webhook validation is used

Never commit real secrets, generated run outputs, private media, or downloaded task artifacts.

## Public Agent Assets

The Codex, Claude, and agent-facing files in this repository are intentional public product assets. They are meant to help LLMs and wrappers use the toolkit correctly.

Keep those files generic and reusable:
- use placeholder credentials only
- use fixture paths instead of local absolute paths
- avoid customer names, internal review notes, and private operational details
- document workflow behavior, not private account state

## Supported Versions

Security fixes are applied to the current `main` branch. If release tags are introduced, this policy should be updated with the currently supported versions.
