# Pipeline Usage and Cost Logging

> Date: 2026-03-12
> Scope: backend pipeline observability, admin Pipeline Runs UI semantics

## Why

`Pipeline Runs` currently shows `—` or `0` for some failed runs even when the pipeline already spent money on OpenAI calls.

That happens because:

- `pipeline_logs` already has `tokens_used` and `cost_usd`
- but most AI pipeline stages do not populate those fields
- and the admin UI sometimes treats `null` as `0`

This creates the wrong mental model:

- `0` should mean "recorded and zero"
- `—` should mean "not recorded / unknown"

## Goal

Make new pipeline runs record OpenAI usage and estimated cost for every AI-backed stage that matters:

- `rank`
- `research.generate.en`
- `research.translate.ko`
- `business.fact_pack.en`
- `business.analysis.en`
- `business.persona.*.en`
- `business.translate.ko`

Then update the admin UI so:

- failed runs with actual logged usage show real token/cost totals
- legacy runs without usage logs continue to show `—`
- per-stage chips do not silently coerce `null` to `0`

## Cost Model

Costs are estimated from a backend pricing table keyed by model name.

Implementation rules:

- use OpenAI response `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`
- calculate estimated USD cost from model-specific input/output token rates
- if the model is unknown or usage is missing, record `tokens_used` if available and leave `cost_usd = null`

This is an observability estimate, not a billing source of truth.

## Logging Rules

- `pipeline_logs.tokens_used` stores total tokens for that stage call or aggregated stage operation
- `pipeline_logs.cost_usd` stores estimated USD cost for that stage call or aggregated stage operation
- `pipeline_runs` summary pages aggregate only recorded values
- `stageCount` comes from log rows, not from usage availability

## UI Rules

- `0` means recorded value is zero
- `—` means value is missing / not recorded
- stage cards should render `—` for null token/cost values
- run totals should stay `null` when no usage rows were recorded, even if stage logs exist

## Follow-up

If model pricing changes, update the backend pricing map and keep this document in sync.
