---
date: 2026-04-22
topic: NQ-40 Phase 2 — CP quality sub-scoring (measurement-only)
status: active
owner: Amy
related:
  - vault/12-Journal-&-Decisions/2026-04-21-news-pipeline-v11.md
  - backend/services/agents/prompts_news_pipeline.py
  - backend/services/pipeline_quality.py
---

# NQ-40 Phase 2 — Community Pulse Quality Sub-scoring

## Goal

Start measuring Community Pulse (CP) quality with 3 evidence-anchored sub-scores. **Phase 2a is measurement-only** — scores are collected & logged but excluded from the weighted total for 2 weeks (through ~2026-05-06). After observing distributions, decide whether to introduce weights (Phase 2b).

## Why now

Phase 1 (commit `4ec450a`) fixed the **language** problem — CP Korean now renders Korean via `_has_hangul` validation + mini-model retranslation in `summarize_community`. That plugs the English-leak hole.

What Phase 1 does NOT address:
- Quote **relevance** to the day's stories (random thread drift).
- Quote **substance** — "insight" vs "wow cool" fluff.
- Translation **fidelity** — KO preserves the EN quote's meaning/tone, not a generic paraphrase.

These aren't caught by existing rubric sub-scores (locale_integrity, citation_coverage, etc.). They're the plausible next-surface-area-of-concern once we've shipped Phase 1.

## Non-goals

- No few-shot CP examples. We do not have observed CP failure cases to base examples on; fabricating them would bias the judge. (Decision: 2026-04-22 conversation.)
- No separate LLM call for CP. The existing body QC call already reads the whole body incl. CP; add sub-scores inline.
- No immediate weighting. Weights stay at 0 during Phase 2a. Weight decision is deferred to Phase 2b after observation.

## Design

### Activation

- CP sub-block fires on every body QC invocation (all 4: research/business × expert/learner). No gating logic.
- When CP is absent from the body, judge scores each sub-score `10` with evidence `"## 커뮤니티 반응 section not present — N/A"`. This preserves the contract and avoids special-casing.

### The 3 sub-scores

Each sub-score follows the existing 10/7/4/0 anchor scale + evidence-required contract (same as `locale_integrity`, `plain_language_lead`, etc.).

1. **cp_relevance** — Do the CP quotes tie to the day's stories, or are they random HN/Reddit drift?
   - Anchors:
     - **10**: Every quote visibly relates to a story in the digest body (headline, company, model, paper mentioned).
     - **7**: Most quotes tie in; one is tangential.
     - **4**: Multiple quotes feel like generic tech chatter.
     - **0**: Quotes are unrelated to any story in the digest.
   - Evidence requirement: cite one quote + which story it connects to.

2. **cp_substance** — Do quotes carry technical/decision substance, or just reaction fluff?
   - Anchors:
     - **10**: Quotes add a perspective — a tradeoff, a failure mode, a decision criterion, benchmark skepticism, deployment constraint.
     - **7**: Most quotes substantive; one is fluff.
     - **4**: Mix of substantive + "this is cool" reactions.
     - **0**: All quotes are hype/reaction with no informational content.
   - Evidence requirement: quote the weakest one + say why.

3. **translation_fidelity** — Does the KO quote preserve the EN quote's meaning and tone? (Judge can compare because the payload has both `=== EN BODY ===` and `=== KO BODY ===`, and Phase 1 already guarantees 1:1 pair ordering via `valid_pairs` in `summarize_community`.)
   - Anchors:
     - **10**: KO quotes read as faithful translations — specifics preserved (numbers, named systems, sharp phrasing).
     - **7**: Mostly faithful; one softened or over-paraphrased.
     - **4**: Noticeable drift in 2+ quotes (generic paraphrase, stripped specifics, tone shift).
     - **0**: KO quotes are unrecognizable vs EN counterparts.
   - Evidence requirement: cite one EN↔KO pair and comment on preservation.

### Aggregation (measurement-only)

- The new `community_pulse` group is **excluded** from `_aggregate_subscores` during Phase 2a. Exclusion is explicit — add `community_pulse` to the skip set in `_aggregate_subscores`.
- Sub-scores still flow through to `expert_breakdown` / `learner_breakdown` (existing code at [pipeline_quality.py:546-547](backend/services/pipeline_quality.py#L546-L547)), so they persist to `digest_quality_scores.expert_breakdown` (JSONB) automatically. No schema change needed.
- Add one structured log line per body QC: `logger.info("cp_quality %s %s: relevance=%d substance=%d fidelity=%d", digest_type, persona, ...)`. This is the primary observation channel for Phase 2a — distributions visible in Railway logs without querying the DB.

### Failure modes & mitigations

- **Judge invents CP violations** when CP is absent. Mitigated by the explicit `"not present — N/A"` evidence template in the rubric.
- **Translation fidelity false positives** because judge can't see the original EN source (only the rendered quotes). This is acceptable: we only need fidelity *between* EN quote and KO quote as rendered, not against the upstream source. The judge has both.
- **Rubric-bloat regressions** — adding 3 sub-scores to each prompt extends the rubric by ~40 lines × 4 files. If the Apr 22 attention-dilution regression repeats (judge missing other sub-scores), roll back the prompt change and move CP to a separate LLM call. Mitigation: keep the new block compact, reuse shared anchor language.

## Chunks

### Chunk 1: Prompt changes (4 files, 1 edit target)

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py`
  - `QUALITY_CHECK_RESEARCH_EXPERT` (~1593-1646)
  - `QUALITY_CHECK_RESEARCH_LEARNER` (~1649-1702)
  - `QUALITY_CHECK_BUSINESS_EXPERT` (~1705 onward)
  - `QUALITY_CHECK_BUSINESS_LEARNER` (~1785 onward — locate)

**Steps:**
- [ ] Define a shared `_QC_CP_QUALITY_BLOCK` f-string near `_QC_SHARED_RUBRIC_HEADER` with the 3 sub-score definitions + anchors + N/A fallback contract.
- [ ] Append a `### Community Pulse Quality (3)` section (referencing `_QC_CP_QUALITY_BLOCK`) to the sub-dimensions list in each of the 4 prompts.
- [ ] Add `"community_pulse": {cp_relevance, cp_substance, translation_fidelity}` to the output JSON schema in each of the 4 prompts.
- [ ] Update the "X sub-scores grouped into Y categories" header counts (e.g., "10 sub-scores grouped into 4 categories" → "13 sub-scores grouped into 5 categories").
- [ ] Commit: `feat(quality): add CP quality sub-scoring (measurement-only, weight=0)`

### Chunk 2: Aggregation exclusion

**Files:**
- Modify: [backend/services/pipeline_quality.py:166-198](backend/services/pipeline_quality.py#L166-L198) — `_aggregate_subscores`

**Steps:**
- [ ] Add `"community_pulse"` to the `if group_key in {...}: continue` skip set. Add a one-line comment noting this is Phase 2a measurement-only; weight decision deferred.
- [ ] No other changes — sub-scores still propagate to `expert_breakdown` via the existing `.get("subscores", {k: v for k, v in expert_breakdown.items() if k not in {"score", "issues"}})` at lines 546-548. `community_pulse` will naturally ride along.
- [ ] Commit (same commit as Chunk 1 if small).

### Chunk 3: Observability log line

**Files:**
- Modify: `backend/services/pipeline_quality.py` in `_check_digest_quality` — after `results = await asyncio.gather(*tasks)` at line 482.

**Steps:**
- [ ] Helper `_log_cp_subscores(digest_type, persona_label, breakdown_dict)` that reads `breakdown_dict.get("community_pulse", {})` and emits a single `logger.info` with the 3 score values. Missing keys → `None`, logged as `"n/a"`.
- [ ] Call it for `expert_breakdown` and (if present) `learner_breakdown`.
- [ ] Commit.

### Chunk 4: Tests

**Files:**
- Create: `backend/tests/test_cp_quality_subscoring.py`

**Steps:**
- [ ] Test: `_aggregate_subscores` excludes `community_pulse` — supply nested dict with 2 normal groups + community_pulse, assert total matches average of non-CP groups only.
- [ ] Test: `_aggregate_subscores` works unchanged when `community_pulse` is absent.
- [ ] Test: CP block renders in each of the 4 prompts (simple substring check for `"cp_relevance"`, `"cp_substance"`, `"translation_fidelity"`, and N/A fallback phrase).
- [ ] Test: quality result's `expert_breakdown` contains `community_pulse` key when the LLM returned it (mock LLM response).
- [ ] Commit.

### Chunk 5: Observation window (no code)

- [ ] Starting next published digest, run 2 weeks (~2026-04-22 → 2026-05-06).
- [ ] Weekly pass: query `digest_quality_scores` for `expert_breakdown->community_pulse` sub-score distribution per persona/digest_type. Note median, p10, p90, and any `0` scores (with evidence).
- [ ] Decision gate at end of window: if distributions are (a) stable, (b) correlated with subjective quality, and (c) don't track existing sub-scores too tightly (redundant signal), introduce weights in Phase 2b. Otherwise iterate rubric or move CP to separate call.

## Rollback

If Chunk 1-3 land and Apr 23+ digests show judge attention-dilution regression (similar to the 93→77 class of movement seen with earlier rubric changes on Apr 22), revert the 4 prompt edits and the skip-set addition in a single commit. Tests from Chunk 4 will need the same revert. No data migration needed — `community_pulse` keys in `expert_breakdown` JSONB can be left in historical rows.

## Open questions (not blockers)

- Do we need to persist `community_pulse` in a dedicated column for easier analytics, or is JSONB sufficient? **Deferred to Phase 2b.** JSONB is fine for 2 weeks of observation.
- Should `cp_quality` factor into blocker/auto-publish gates in Phase 2b? **Deferred.** Current decision: no — it's editorial quality, not correctness.
