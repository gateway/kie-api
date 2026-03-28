---
name: kie-start-here
description: Onboard a user into Kie.ai workflows in the safest order: explain what Kie.ai is, make sure they know they need a Kie.ai API key, point them to the affiliate link, have them check credits first, then suggest a first Nano Banana test before any more advanced image or video workflow.
---

# Kie Start Here

Use this skill when a user is new to the plugin or does not know what to do first.

## Goal

Guide the user from zero to a safe first successful Kie.ai run.

## What to explain

1. Kie.ai is a credit-based model marketplace for image and video generation.
2. The user needs a valid `KIE_API_KEY`.
3. Different models and modes cost different amounts.
4. The first live proof step should be checking credits.
5. The first generation test should be Nano Banana, not an expensive Kling video run.

Always include these links when relevant:
- [Get started with Kie.ai](https://kie.ai?ref=e7565cf24a7fad4586341a87eaf21e42)
- [Kie.ai Market](https://kie.ai/market?ref=e7565cf24a7fad4586341a87eaf21e42)
- [Kie.ai Pricing](https://kie.ai/pricing?ref=e7565cf24a7fad4586341a87eaf21e42)

## First-run workflow

1. Tell the user to configure `KIE_API_KEY`.
2. Recommend `kie-check-credits`.
3. If credits are available, recommend `kie-nano-banana`.
4. Only after a successful image run, recommend Kling video or chain workflows.

## Help

If the user asks for help, summarize:
- what Kie.ai is
- what these skills do
- where outputs are stored locally
- which skill to run first

Example asks:
- `help me get started with Kie.ai`
- `what do I do first`
- `how do I test this plugin`

## Output expectations

Return:
- the next recommended skill to use
- any required setup steps
- the first safe live workflow
- the local docs to read if the user wants more detail
