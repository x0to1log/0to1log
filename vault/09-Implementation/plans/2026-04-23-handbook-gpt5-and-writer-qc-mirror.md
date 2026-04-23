# Handbook GPT-5 Efficiency + Writer-QC Mirror Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Each task ends with a commit. Do NOT batch unrelated changes into one commit.

**Goal:** Port proven GPT-5 efficiency patterns (prompt_cache_key, flex tier, usage telemetry) from the news pipeline to the handbook pipeline, **and** port 4 writer-prompt improvements (writer-QC mirror, claim calibration, temporal anchoring, arxiv depth) that were validated on the news side during 2026-04-17 → 2026-04-23. Phase 1 only — generation-call flex + `with_flex_retry` wrapping and Tier 2-C numeric drift post-processing are deferred.

**Architecture:** 7 independent tasks ordered by risk (lowest first). Telemetry first so every downstream change is observable, then cache key (no behavior change), then flex tier (fail-open safety), then 4 prompt additions. All writer prompts live in [backend/services/agents/prompts_advisor.py](backend/services/agents/prompts_advisor.py); the judge lives in [backend/services/agents/prompts_handbook_types.py](backend/services/agents/prompts_handbook_types.py).

**Tech Stack:** Python 3.11+, OpenAI SDK (`openai>=1.x`), Supabase (`pipeline_logs.debug_meta` JSONB), pytest.

---

## Background — Verified 2026-04-23

### GPT-5 optimizations News has that Handbook is missing

| # | Optimization | News uses it at | Handbook status |
|---|---|---|---|
| 1 | `service_tier="flex"` on quality scoring | [pipeline_quality.py:455, 1097, 1142](backend/services/pipeline_quality.py#L455) | ❌ missing on 3 quality calls |
| 2 | `prompt_cache_key` on writer + QC | [pipeline_quality.py:456, 1098, 1143](backend/services/pipeline_quality.py#L456); [pipeline.py:2427, 2496](backend/services/pipeline.py#L2427); [pipeline_digest.py:686, 800, 861, 1005](backend/services/pipeline_digest.py#L686) | ❌ missing on all 11 handbook calls |
| 3 | Log `cached_tokens` in `pipeline_logs.debug_meta` | auto via `extract_usage_metrics` + [pipeline.py:487-488](backend/services/pipeline.py#L487) | ❌ `_log_handbook_stage` (advisor.py:2113) omits the field |
| 4 | Log `service_tier` in `pipeline_logs.debug_meta` | auto via `extract_usage_metrics` + [pipeline.py:491-492](backend/services/pipeline.py#L491) | ❌ same — field omitted |

### Infrastructure already in place (no plumbing work)

- [client.py:113-140](backend/services/agents/client.py#L113) — `build_completion_kwargs` already accepts `service_tier`, `prompt_cache_key`, `verbosity`. Used by all 3 quality calls.
- [client.py:104-110](backend/services/agents/client.py#L104) — `compat_create_kwargs` passes `**kwargs` through, so generation calls can pass `service_tier` / `prompt_cache_key` directly without wrapper changes.
- [client.py:158-194](backend/services/agents/client.py#L158) — `estimate_openai_cost_usd` auto-applies flex (50%) + cached-token (90% input discount) reductions. Cost log auto-updates once we pass the flags.
- [client.py:197-237](backend/services/agents/client.py#L197) — `extract_usage_metrics` already extracts `cached_tokens` + `service_tier` from the response. The only missing piece is propagating them into `debug_meta`.

### Writer prompt improvements to port from news

Investigation found 5 patterns worth porting. Tier 1+2-H are in Phase 1; Tier 2-C is deferred.

- **Tier 1-A — Writer-QC mirror:** Writer prompt explicitly lists the 10 sub-scores the judge evaluates. Shipped in news writer prompts to reduce variance in what the writer optimizes for.
- **Tier 1-G — Claim calibration + prediction guard:** Distinguishes overclaim ("revolution", "breakthrough") from forward-looking framing ("will disrupt", "is set to").
- **Tier 1-B — Temporal anchoring:** Prefer absolute dates ("2026년 4월") over relative ("최근", "지난주") to prevent decay.
- **Tier 2-H — ArXiv depth requirement:** If advanced body cites an arxiv paper, require at least one of {concrete algorithm step, hyperparameter, training recipe, evaluation protocol} — not just an abstract paraphrase.

Tier 2-C (internal consistency / numeric drift across basic/advanced) requires backend post-processing logic — deferred to a separate sprint.

### Call-site inventory (verified 2026-04-23 via grep)

**Quality check calls (all use `build_completion_kwargs` → easy port):**

| Function | File:Line | Purpose |
|---|---|---|
| `_check_handbook_quality` | [advisor.py:1167](backend/services/agents/advisor.py#L1167) | 10 sub-score judge on advanced body |
| `_self_critique_basic` | [advisor.py:1212](backend/services/agents/advisor.py#L1212) | Feedback loop for basic KO+EN |
| `_check_basic_quality` | [advisor.py:1260](backend/services/agents/advisor.py#L1260) | 10 sub-score judge on basic body |

**Generation calls (all use `compat_create_kwargs` → pass `prompt_cache_key` via `**kwargs`):**

| Call | File:Line | Purpose |
|---|---|---|
| Call 1 | [advisor.py:2165](backend/services/agents/advisor.py#L2165) | Meta + KO basic |
| Call 2 | [advisor.py:2339](backend/services/agents/advisor.py#L2339) | EN basic |
| Call 3 | [advisor.py:2350](backend/services/agents/advisor.py#L2350) | KO advanced |
| Call 4 | [advisor.py:2411](backend/services/agents/advisor.py#L2411) | EN advanced |
| Call 1b | [advisor.py:2451](backend/services/agents/advisor.py#L2451) | Regenerate KO basic |
| Call 2b | [advisor.py:2473](backend/services/agents/advisor.py#L2473) | Regenerate EN basic |
| Call 3b | [advisor.py:2520](backend/services/agents/advisor.py#L2520) | Regenerate KO advanced |
| Call 4b | [advisor.py:2557](backend/services/agents/advisor.py#L2557) | Regenerate EN advanced |

### Why only quality calls get flex in Phase 1

- **Quality check fail-open:** `_check_handbook_quality` / `_check_basic_quality` / `_self_critique_basic` each have `except Exception: return None/False, {}, {}` — a 429 or transient flex capacity error degrades gracefully (score = None, pipeline continues). No retry wrapper needed.
- **Generation failure is fatal:** If Call 1 fails, the handbook term isn't created. News adopted `with_flex_retry` ([pipeline.py:2433, 2502](backend/services/pipeline.py#L2433); [pipeline_digest.py:695, 806, 867, 1011](backend/services/pipeline_digest.py#L695)) specifically because flex tier can return 429 on capacity — retry is free on flex. Introducing the wrapper + retesting 8 call sites is a larger change and belongs in a separate plan.

---

## Cache key naming convention

All keys are `hb-{kind}-{variant}`. Stable across deploys so the cache warms across runs.

| Purpose | Cache key |
|---|---|
| `_check_handbook_quality` | `hb-quality-advanced` |
| `_check_basic_quality` | `hb-quality-basic` |
| `_self_critique_basic` | `hb-critique-basic` |
| Call 1 (KO basic) | `hb-generate-basic` |
| Call 2 (EN basic) | `hb-generate-en-basic` |
| Call 3 (KO advanced) | `hb-generate-advanced` |
| Call 4 (EN advanced) | `hb-generate-en-advanced` |
| Call 1b (regen KO basic) | `hb-regen-basic` |
| Call 2b (regen EN basic) | `hb-regen-en-basic` |
| Call 3b (regen KO advanced) | `hb-regen-advanced` |
| Call 4b (regen EN advanced) | `hb-regen-en-advanced` |

Note: OpenAI prompt caching requires ≥1024 token identical prefix within ~5 min. With 11 distinct keys and typical system prompts 1.5-4k tokens, cache hits will come primarily within a single batch run (generating many terms sequentially with the same system prompt). Regenerate paths share prompts with their generate counterparts but different cache keys are kept for cleaner observability — we can unify if hit-rate telemetry suggests it's wasted fragmentation.

---

## Task Order Rationale

1. **Task 1 — Telemetry first** (cached_tokens + service_tier into `debug_meta`). Zero behavior change. Makes every downstream optimization measurable. Pure win.
2. **Task 2 — prompt_cache_key on all 11 calls.** Zero behavior change on cache miss. Cache hits are gradual cost wins, no risk.
3. **Task 3 — service_tier="flex" on 3 quality calls.** ~50% cost reduction on judge calls. Fail-open design means no new failure modes.
4. **Task 4 — Tier 1-B Temporal anchoring** (smallest prompt change, 2-3 lines).
5. **Task 5 — Tier 1-G Claim calibration** (2-3 lines).
6. **Task 6 — Tier 2-H ArXiv depth** (3-4 lines, advanced prompt only).
7. **Task 7 — Tier 1-A Writer-QC mirror** (largest prompt addition — 10 sub-score block). Ships last so earlier prompt tweaks are isolated in git history.

Each task = one commit. Tasks 4-7 can be validated cheaply by regenerating 1-2 test terms per commit and spot-checking output.

---

## Task 1: Log `cached_tokens` + `service_tier` in `_log_handbook_stage`

**Context:** [advisor.py:2113-2136](backend/services/agents/advisor.py#L2113) already receives the full `usage` dict from `extract_usage_metrics` but only forwards `input_tokens` and `output_tokens` into `debug_meta`. Two missing lines.

**Files:**
- Modify: [backend/services/agents/advisor.py:2113-2136](backend/services/agents/advisor.py#L2113)

**Change:**

```python
# Current (advisor.py:2118-2123):
meta = {
    "term": req.term,
    "source": source,
    "input_tokens": usage.get("input_tokens"),
    "output_tokens": usage.get("output_tokens"),
}

# Change to:
meta = {
    "term": req.term,
    "source": source,
    "input_tokens": usage.get("input_tokens"),
    "output_tokens": usage.get("output_tokens"),
    "cached_tokens": usage.get("cached_tokens"),
    "service_tier": usage.get("service_tier"),
}
```

**Verify:**
- Regenerate 1 existing term locally.
- Query: `SELECT debug_meta FROM pipeline_logs WHERE pipeline_type LIKE 'handbook.generate.%' ORDER BY created_at DESC LIMIT 1;`
- Confirm `cached_tokens` is numeric (may be 0 on first call) and `service_tier` is present (value from response).

**Commit:** `chore(handbook): log cached_tokens + service_tier in pipeline_logs.debug_meta`

---

## Task 2: Add `prompt_cache_key` to all 11 handbook calls

**Context:** Cache keys enable OpenAI's prompt-cache hit rate to stick across sequential calls with identical system prefixes (the 10-point rubric system prompt for quality; the category-specific system prompt for generation). Free discount once the prefix caches.

### Task 2.1: Quality calls (3 call sites, `build_completion_kwargs` signature)

**Files:**
- Modify: [backend/services/agents/advisor.py:1167, 1212, 1260](backend/services/agents/advisor.py#L1167)

**Change pattern** (example for `_check_handbook_quality` at line 1167):

```python
# Before:
resp = await client.chat.completions.create(
    **build_completion_kwargs(
        model=reasoning_model,
        messages=[...],
        max_tokens=1800,
        response_format={"type": "json_object"},
    )
)

# After:
resp = await client.chat.completions.create(
    **build_completion_kwargs(
        model=reasoning_model,
        messages=[...],
        max_tokens=1800,
        response_format={"type": "json_object"},
        prompt_cache_key="hb-quality-advanced",
    )
)
```

Apply to all 3 call sites with keys from the naming table above.

### Task 2.2: Generation calls (8 call sites, `compat_create_kwargs` pass-through)

**Files:**
- Modify: [backend/services/agents/advisor.py:2165, 2339, 2350, 2411, 2451, 2473, 2520, 2557](backend/services/agents/advisor.py#L2165)

**Change pattern** (example for Call 1 at line 2165):

```python
# Before:
resp1 = await client.chat.completions.create(
    **compat_create_kwargs(
        model,
        messages=[...],
        response_format={"type": "json_object"},
        max_tokens=16000,
    )
)

# After:
resp1 = await client.chat.completions.create(
    **compat_create_kwargs(
        model,
        messages=[...],
        response_format={"type": "json_object"},
        max_tokens=16000,
        prompt_cache_key="hb-generate-basic",
    )
)
```

Apply to all 8 call sites with keys from the naming table above.

**Verify:**
- Regenerate 2-3 terms back-to-back.
- Query `debug_meta->>'cached_tokens'` from pipeline_logs for the batch. First call per key: likely 0 (fills cache). Second call: should be non-zero on prefix tokens.
- Confirm no regression in term content quality (spot-check 1 term manually).

**Commit:** `feat(handbook): add prompt_cache_key to 11 writer + QC calls for cache hit rate observability`

---

## Task 3: Add `service_tier="flex"` to the 3 quality calls

**Context:** Flex tier = 50% cost on input+output, synchronous, lower-priority queue. News uses it on all quality calls with no retry wrapper because quality-check failure is fail-open ([advisor.py:1184-1186](backend/services/agents/advisor.py#L1184)). Cost estimate auto-adjusts via [client.py:185](backend/services/agents/client.py#L185) — no further code changes.

**Files:**
- Modify: [backend/services/agents/advisor.py:1167, 1212, 1260](backend/services/agents/advisor.py#L1167)

**Change pattern** (append one parameter to each call):

```python
resp = await client.chat.completions.create(
    **build_completion_kwargs(
        model=reasoning_model,
        messages=[...],
        max_tokens=1800,
        response_format={"type": "json_object"},
        prompt_cache_key="hb-quality-advanced",
        service_tier="flex",  # NEW
    )
)
```

**Do NOT apply to generation calls** (Phase 2 — requires `with_flex_retry` wrapper).

**Verify:**
- Score an existing term via the admin UI (triggers `_check_handbook_quality`).
- Query pipeline_logs: `debug_meta->>'service_tier'` should equal `"flex"` (or `"default"` if flex capacity was exhausted — still acceptable).
- Cost per quality call in `cost_usd` should drop ~50% vs a pre-change row of the same term.
- No increase in quality-check null-score rate over 5-10 scoring calls.

**Commit:** `feat(handbook): use service_tier=flex on 3 quality-check calls (50% cost reduction, fail-open)`

---

## Task 4: Tier 1-B — Temporal anchoring

**Context:** Handbook definitions and bodies currently accept relative time phrases ("최근", "지난주", "recently") that decay immediately. News writer prompts were updated to prefer absolute dates ("2026년 4월", "April 2026"). Port the same rule.

**Files:**
- Modify: [backend/services/agents/prompts_advisor.py](backend/services/agents/prompts_advisor.py) — `GENERATE_BASIC_PROMPT` and `GENERATE_ADVANCED_PROMPT`
- Reference for phrasing: grep news prompts for "absolute date" / "절대 날짜" in [backend/services/agents/prompts_news_pipeline.py](backend/services/agents/prompts_news_pipeline.py)

**Rule to add (in both basic and advanced sections where date references can appear):**

> **Temporal anchoring:** When referencing time, prefer absolute dates ("2026년 4월", "April 2026", "2024-2025") over relative phrases ("최근", "지난주", "recently", "currently"). The handbook is read months or years after generation — relative phrases decay. Exception: when the absolute date is unknown or uncertain, use a qualified phrase like "2024년 이후" rather than inventing a specific date.

Place immediately after the existing "Scope discipline" rule so the writer sees it before drafting.

**Verify:**
- Regenerate 1 term whose existing body uses "최근" / "recently".
- Confirm new output substitutes absolute date (or qualified range).
- Quality score on the regenerated term should not drop (temporal anchoring doesn't affect sub-scores; just a safeguard check).

**Commit:** `feat(handbook): prefer absolute dates over relative temporal phrases (Tier 1-B port)`

---

## Task 5: Tier 1-G — Claim calibration + prediction guard

**Context:** News writer prompts were updated (commit history around 2026-04-18 → 2026-04-20) to separate two overlapping issues: (a) overclaim words ("revolution", "breakthrough", "game-changer") that inflate without evidence; (b) prediction framing ("will disrupt", "is set to") that may be legitimate forward-looking but should be clearly marked. Handbook currently has neither rule.

**Files:**
- Modify: [backend/services/agents/prompts_advisor.py](backend/services/agents/prompts_advisor.py) — `GENERATE_ADVANCED_PROMPT` (advanced only; basic intentionally engages more but shouldn't overclaim either — copy to basic if Amy approves after first test)

**Rule to add:**

> **Claim calibration:**
> - Avoid overclaim words ("revolution", "revolutionary", "breakthrough", "game-changer", "paradigm shift", "혁명적", "획기적") unless the claim is backed by a specific citation in the body.
> - Predictions / forward-looking claims ("will disrupt", "is set to", "expected to dominate", "앞으로 대체할", "곧 주류가 될") must be explicitly framed as prediction, with the basis ("based on X trend", "per Y paper's results") in the same sentence. Do not present future projections as current facts.

Place alongside the existing "accuracy" block in the advanced prompt.

**Verify:**
- Regenerate 1 term in a hype-prone category (e.g., `technique_algorithm`).
- Spot-check advanced body for overclaim words; should be reduced or absent.
- Quality judge's `accuracy` sub-scores should be stable or slightly improved over 2-3 regens.

**Commit:** `feat(handbook): claim calibration + prediction framing in advanced writer prompt (Tier 1-G port)`

---

## Task 6: Tier 2-H — ArXiv depth requirement

**Context:** Handbook advanced bodies frequently cite arxiv papers but paraphrase only the abstract — low information density per citation. News adopted a rule: if the body cites an arxiv paper, include at least one concrete detail (algorithm step, hyperparameter, training recipe, or evaluation protocol) from that paper.

**Files:**
- Modify: [backend/services/agents/prompts_advisor.py](backend/services/agents/prompts_advisor.py) — `GENERATE_ADVANCED_PROMPT`

**Rule to add:**

> **ArXiv depth requirement:** When citing an arxiv paper (or doi/paperswithcode link) in advanced_ko or advanced_en, include at least ONE concrete detail from the paper beyond the abstract: a specific algorithm step, a hyperparameter or architectural choice, a training recipe (data/optimization), or an evaluation protocol (benchmark/metric/result). An abstract paraphrase alone does not satisfy this. If you cannot recall a concrete detail, cite a textbook / official doc / blog post with the detail instead, rather than the arxiv paper alone.

Place alongside the existing paper-reference block (search `PAPER_REFERENCE_PATTERNS` usage or "et al." rule in the advanced prompt).

**Verify:**
- Regenerate 1 term with known arxiv-heavy citation (e.g., a term in `ARCHITECTURE_REQUIRED_TYPES` or `PAPER_REFERENCE_REQUIRED_TYPES`).
- Confirm advanced body now contains at least one concrete detail per arxiv citation.
- Quality judge's `technical_depth` sub-scores (if exposed) should improve or hold.

**Commit:** `feat(handbook): require concrete detail when citing arxiv papers (Tier 2-H port)`

---

## Task 7: Tier 1-A — Writer-QC mirror block

**Context:** Writer optimizes against the rubric it's shown. News writer prompts explicitly list the 10 sub-scores the judge evaluates — this reduced variance in what writers emphasize. Handbook writers currently don't see the judge rubric. Adding a condensed mirror in `GENERATE_BASIC_PROMPT` and `GENERATE_ADVANCED_PROMPT` is the largest-impact prompt change of this plan.

**Sub-scores to mirror (per [backend/services/agents/prompts_handbook_types.py](backend/services/agents/prompts_handbook_types.py) — `HANDBOOK_QUALITY_CHECK_PROMPT` and `BASIC_QUALITY_CHECK_PROMPT`):**

**Advanced (9 sub-scores, max 90 raw):**
- technical_depth: architecture_parameters, training_evaluation, trade-off_analysis
- accuracy: factual_precision, temporal_currency
- uniqueness: novel_framing, beyond_wikipedia
- structural_completeness: section_coverage, format_compliance

**Basic (10 sub-scores, max 100 raw):**
- engagement: hook_strength, analogy_clarity, reader_accessibility
- accuracy: factual_precision, temporal_currency, no_overclaim
- uniqueness: novel_framing, memorable_phrasing
- structural_completeness: section_coverage, format_compliance

**Files:**
- Modify: [backend/services/agents/prompts_advisor.py](backend/services/agents/prompts_advisor.py) — both `GENERATE_BASIC_PROMPT` and `GENERATE_ADVANCED_PROMPT`

**Block to add (placed near the top of each prompt after the role setup):**

For `GENERATE_ADVANCED_PROMPT`:

> **What the quality judge scores (10 sub-scores, 0-10 each — aim for 7+ on each):**
> - **Technical depth (3):** architecture / parameter specifics · training or evaluation details · real trade-off analysis (not just pros/cons lists)
> - **Accuracy (2):** factual precision · temporal currency (current-gen models, dated claims anchored to year)
> - **Uniqueness (2):** novel framing (not a Wikipedia rehash) · insight beyond common web content
> - **Structural completeness (2):** all required sections present · format compliance (headings, markers)
>
> Write to these dimensions explicitly. Do not repeat them in the output.

For `GENERATE_BASIC_PROMPT`, mirror with the basic 10 sub-scores (engagement × 3, accuracy × 3, uniqueness × 2, structural_completeness × 2).

**Verify:**
- Regenerate 3 terms across different categories (e.g., a `model_family`, a `technique_algorithm`, a `foundational_concept`).
- Run quality judge on each.
- Compare pre/post sub-score distribution — expect modest uplift in `technical_depth` and `uniqueness` sub-scores; accuracy should be stable.
- No regression in `structural_completeness` (writer might over-focus on sub-scores and skip sections — explicit check).

**Commit:** `feat(handbook): writer-QC mirror block in basic + advanced prompts (Tier 1-A port)`

---

## Out of Scope (Phase 2 — separate plan)

1. **Generation-call flex tier + `with_flex_retry` wrapper.** 8 call-site changes + new retry pattern. Largest remaining efficiency win (~50% on generation, which is most of handbook cost), but non-trivial risk surface. Handle after Phase 1 telemetry confirms quality-call flex is stable.
2. **Tier 2-C — Internal consistency / numeric drift across basic/advanced bodies.** Requires backend post-processing to extract numeric claims (parameter counts, benchmark scores) and cross-check across the two bodies.
3. **GPT-5-mini vs gpt-5-nano A/B for quality judge.** Judge currently uses `gpt-5-mini`. Nano is ~3× cheaper but may collapse on evidence justification. Separate A/B probe with gold-standard corpus.
4. **Per-term-type sub-score weights.** Highest-value scoring improvement identified in 2026-04-23 forward-thinking audit. Separate plan.
5. **Rescore 57 already-published terms with new rubric.** Calibration backfill.

---

## Success Criteria (Phase 1 complete when all hold)

- [ ] `debug_meta` on handbook-generate pipeline_logs rows includes `cached_tokens` and `service_tier` (non-null).
- [ ] `prompt_cache_key` present on all 11 handbook OpenAI calls (grep `pipeline_logs` debug meta or inspect network).
- [ ] 3 quality calls show `service_tier="flex"` (or `"default"` on flex capacity exhaustion) in usage metrics; cost per call dropped ~50% vs pre-change baseline.
- [ ] `prompts_advisor.py` GENERATE_BASIC_PROMPT / GENERATE_ADVANCED_PROMPT contain all 4 new rule blocks (temporal anchoring, claim calibration, arxiv depth, writer-QC mirror).
- [ ] Regression spot-check: regenerate 3 existing terms, compare pre/post content — no drop in quality-judge score; output remains parseable JSON.
- [ ] No new pipeline errors over first 5-10 handbook generations after deploy.

---

## Related Files

- Writer prompts: [backend/services/agents/prompts_advisor.py](backend/services/agents/prompts_advisor.py)
- Judge prompts: [backend/services/agents/prompts_handbook_types.py](backend/services/agents/prompts_handbook_types.py)
- Pipeline orchestration: [backend/services/agents/advisor.py](backend/services/agents/advisor.py)
- OpenAI client wrappers: [backend/services/agents/client.py](backend/services/agents/client.py)
- News reference (port source): [backend/services/pipeline_quality.py](backend/services/pipeline_quality.py), [backend/services/pipeline.py](backend/services/pipeline.py), [backend/services/pipeline_digest.py](backend/services/pipeline_digest.py), [backend/services/agents/prompts_news_pipeline.py](backend/services/agents/prompts_news_pipeline.py)

## Related Plans

- Prior selection hardening (shipped 2026-04-20): `2026-04-17-handbook-term-selection-hardening-plan.md`
- GPT-5 optimization on news side: `2026-04-23-gpt5-optimization.md`
- Legacy model cleanup (shipped): `2026-04-23-legacy-model-cleanup.md`
