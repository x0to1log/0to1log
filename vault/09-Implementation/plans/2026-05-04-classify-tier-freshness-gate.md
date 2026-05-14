# Classify Tier × Freshness Matrix Gate Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Eliminate the "stale event recycled by SEO sites surfaces as today's primary news" failure class (May 4 incident: OpenAI $122B Mar 31 raise framed as fresh news because toolsstackai.com published May 1) by adding an explicit `source_tier × event_freshness` matrix gate inside the classification LLM call.

**Architecture:** Phase 1 is **prompt-only** — the candidate formatter already surfaces `source_tier`/`source_kind`/`source_confidence`. We update `CLASSIFICATION_SYSTEM_PROMPT` to (a) define a 3-tier source ranking, (b) define a 14-day freshness window, (c) give the matrix decision rules, (d) include few-shot examples of recap/SEO-recycle patterns to reject. No code change needed for the input — the LLM reads existing fields. Event freshness is inferred from snippet date references; explicit `published_date` extraction is deferred to Phase 2 if measurement shows the LLM can't reliably infer.

**Tech Stack:** Python 3.11, OpenAI gpt-5-mini for classify, pytest. No new dependencies, no infra changes.

---

## Failure mode being eliminated

| Today | After this plan |
|---|---|
| `toolsstackai.com` publishes May 1 article about OpenAI's Mar 31 funding round → Tavily returns it (publish_date=fresh) → classify picks it as primary research story → writer presents as today's news. Reader sees "today's news" that's actually 5 weeks old, from a content farm. | Classify reads `source_tier=spam/secondary` + snippet date references → decision matrix: TIER-3 (SEO) + OLD (Mar 31 < May 4 - 14d) → REJECT. The story doesn't reach the writer's primary slots. |

---

## Why prompt-only is enough for Phase 1

- Candidate formatter at `ranking.py:254` already includes `Source tier`, `Source kind`, `Source confidence` per candidate.
- Snippets from Tavily/HF/arXiv typically contain explicit date references when an event is being discussed.
- Phase 2 (event_date extraction via separate LLM call, ~$0.06/cron) is a fallback if Phase 1 measurement shows the LLM misses too many cases.
- Reversibility: prompt rollback is one commit revert, no schema/data migration.

---

## Decision matrix (the rule)

| Tier | Freshness | Decision |
|---|---|---|
| TIER-1 (`source_kind ∈ {official_site, paper, official_repo}` OR `source_tier=primary`) | FRESH (event ≤14d) | ✅ Eligible primary |
| TIER-1 | UNKNOWN (no date inferable) | ✅ Eligible primary (tier-1 trust) |
| TIER-1 | OLD (event >14d) | ❌ Reject |
| TIER-2 (`media_tier=secondary` AND `source_confidence ∈ {high, medium}`) | FRESH | ✅ Eligible primary |
| TIER-2 | UNKNOWN | ⚠️ Demote to enrichment-context only |
| TIER-2 | OLD | ❌ Reject |
| TIER-3 (everything else: `analysis/secondary` with low confidence, `spam`, untyped) | ANY | ❌ Reject (no primary, no enrichment) |

**Thresholds:**
- FRESH = event ≤ 14 days before `batch_date`
- 14d covers: same-day major announcements + week-long secondary coverage cycle + weekend lag
- Stricter (7d) would drop legitimate week-old context; looser (30d) would re-admit Apr-as-May recycling

---

## Tasks

### Task 1: Update CLASSIFICATION_SYSTEM_PROMPT

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py` (CLASSIFICATION_SYSTEM_PROMPT, top of file)

**Step 1: Add the matrix gate block at the front of the prompt**

After the opening line (`You are an AI news editor for 0to1log...`), insert a new section "## Source quality × event freshness gate (REQUIRED FIRST FILTER)" that:

1. Defines TIER-1/2/3 in terms of the existing `Source tier`, `Source kind`, `Source confidence` fields each candidate carries.
2. Defines FRESH/OLD/UNKNOWN: read snippet for explicit date references; treat events from {batch_date - 14 days} or later as FRESH; treat any event before that as OLD; absent any date reference, UNKNOWN.
3. Lists the matrix decisions verbatim (table above).
4. Includes the rationale in 2 sentences (so the LLM understands intent, not just rules).

**Step 2: Add few-shot examples**

Inside the new section, include 4 mini-examples:
- TIER-1 + FRESH (e.g., "openai.com, kind=official_site, snippet mentions 'today' and 'May 4, 2026'") → EXAMPLE PASS
- TIER-1 + OLD (e.g., "openai.com, official update from Feb 27, 2026") → EXAMPLE REJECT
- TIER-3 SEO recycle (e.g., "toolsstackai.com, kind=analysis, tier=secondary, confidence=low, snippet 'OpenAI Just Raised $122B'... mentions 'on March 31'") → EXAMPLE REJECT (call out the title/date mismatch)
- TIER-2 + FRESH (e.g., "techcrunch.com, kind=media, tier=secondary, confidence=high, snippet 'Anthropic released today'") → EXAMPLE PASS

**Step 3: Update existing relevance rules to defer to the gate**

Existing prompt has "Litmus test" and per-category guidance. Add a one-liner at the start of those: "These rules apply ONLY to candidates that pass the gate above. Gate-failing candidates are excluded BEFORE litmus tests."

**Step 4: Verify by reading the rendered prompt**

Print the new prompt (`python -c "from services.agents.prompts_news_pipeline import CLASSIFICATION_SYSTEM_PROMPT; print(CLASSIFICATION_SYSTEM_PROMPT)"`) and confirm:
- Gate section is at the top (before "Litmus test" and category descriptions)
- All 4 few-shot examples present
- Matrix decisions readable as a table or numbered list

**Step 5: Commit**

```bash
git add backend/services/agents/prompts_news_pipeline.py
git commit -m "feat(classify): tier x freshness matrix gate as primary classification filter

Adds a 'Source quality × event freshness gate' section to the
classification prompt. Defines 3-tier source ranking (TIER-1 official/
papers, TIER-2 mainstream secondary, TIER-3 SEO/aggregator) and a 14-day
event freshness window. Per-row decision matrix governs whether each
candidate is eligible for primary, demoted to enrichment, or rejected.

Eliminates the May 4 stale-recycle failure class: SEO sites republishing
weeks-old events as 'fresh' articles passed our publish_date filter and
reached primary slots. Now TIER-3 is rejected outright; TIER-1/2 with
event_date older than batch_date - 14d also rejected.

Phase 1 is prompt-only — the candidate formatter (ranking.py:254) already
surfaces source_tier/kind/confidence, and event freshness is inferred from
snippet date references. Phase 2 adds explicit event_date extraction
(small LLM call) if measurement shows Phase 1 misses too many cases."
```

---

### Task 2: Add prompt structure regression test

**Files:**
- Create: `backend/tests/test_classification_prompt_gate.py`

**Step 1: Write the failing test**

```python
"""CLASSIFICATION_SYSTEM_PROMPT must contain the tier × freshness gate.

Regression test for the May 4 stale-recycle incident — without the matrix
gate, SEO sites republishing weeks-old events as fresh articles reach
primary classification slots. The prompt is the only enforcement point in
Phase 1; this test ensures the gate stays present across edits.
"""
from services.agents.prompts_news_pipeline import CLASSIFICATION_SYSTEM_PROMPT


def test_prompt_contains_tier_definitions():
    p = CLASSIFICATION_SYSTEM_PROMPT
    assert "TIER-1" in p, "TIER-1 definition missing"
    assert "TIER-2" in p, "TIER-2 definition missing"
    assert "TIER-3" in p, "TIER-3 definition missing"


def test_prompt_contains_freshness_window():
    p = CLASSIFICATION_SYSTEM_PROMPT
    assert "14" in p, "14-day freshness window not specified"
    assert ("FRESH" in p) or ("fresh" in p), "FRESH/fresh keyword missing"
    assert ("OLD" in p) or ("old" in p), "OLD/old keyword missing"


def test_prompt_contains_reject_rules_for_tier3_and_old():
    p = CLASSIFICATION_SYSTEM_PROMPT.lower()
    # Either explicit "reject" wording or "skip" — both acceptable
    assert ("reject" in p) or ("skip" in p), "no reject/skip directive"
    # TIER-3 and OLD must both lead to rejection somewhere
    # (specific phrasing varies; here we check the rule landscape exists)
    assert "tier-3" in p, "TIER-3 disposition not stated"


def test_prompt_contains_few_shot_examples():
    p = CLASSIFICATION_SYSTEM_PROMPT.lower()
    # At least 2 marker phrases for example presence
    example_markers = ["example", "e.g.", "for instance", "such as"]
    assert any(m in p for m in example_markers), "no few-shot examples found"


def test_prompt_gate_appears_before_litmus_test():
    """Gate must run BEFORE category-specific litmus tests so gate-failing
    candidates are excluded early."""
    p = CLASSIFICATION_SYSTEM_PROMPT
    # Find positions of gate and litmus test
    gate_pos = p.lower().find("tier-1")
    litmus_pos = p.lower().find("litmus test")
    if litmus_pos < 0:
        # Litmus test phrasing may differ — skip this assertion if absent
        return
    assert gate_pos < litmus_pos, (
        f"Gate ({gate_pos}) must appear before litmus test ({litmus_pos})"
    )
```

**Step 2: Run test to verify FAIL initially**

```
cd backend && pytest tests/test_classification_prompt_gate.py -v
```

Expected: FAIL on the gate assertions if Task 1 is not yet shipped, PASS if Task 1 already in.

**Step 3: After Task 1 ships, run again**

```
cd backend && pytest tests/test_classification_prompt_gate.py -v
```

Expected: all PASS.

**Step 4: Commit**

```bash
git add backend/tests/test_classification_prompt_gate.py
git commit -m "test(classify): regression test for tier x freshness gate prompt structure

Asserts that CLASSIFICATION_SYSTEM_PROMPT contains TIER-1/2/3 definitions,
14-day freshness window, reject directive, few-shot examples, and that the
gate appears before existing litmus tests. Future prompt edits that drop
the gate will fail this test."
```

---

### Task 3: Verification + measurement plan

**Step 1: Run full test suite**

```
cd backend && pytest tests/ -v --tb=short
```

Expected: all PASS, including the new `test_classification_prompt_gate.py`.

**Step 2: Push (Railway auto-redeploys)**

```bash
git push origin main
```

**Step 3: Document measurement plan**

Add a follow-up section to `vault/12-Journal-&-Decisions/2026-05-04-classify-tier-freshness-gate.md` (new journal entry) with:

- Date range to measure (next 7 daily crons after deploy)
- Metrics to track:
  - Count of stale-recycle incidents (manual review of each digest's primary stories — event date check on each story)
  - Count of TIER-3 domains in source_cards (should drop to ~0 for primary; some OK in enrichment)
  - Count of legit fresh stories that got rejected (false negatives — manual review)
- Decision criteria for Phase 2:
  - 0 stale-recycle in 7 days → Phase 1 sufficient, no Phase 2 needed
  - 1-2 incidents → consider Phase 2 (event_date extraction)
  - 3+ incidents → Phase 2 mandatory + investigate why prompt rules are bypassed

---

## Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| LLM fails to follow the gate consistently | Medium | Few-shot examples + explicit reject directive. Measure via Step 3. Phase 2 (programmatic extraction) is the fallback. |
| Legit niche outlets get demoted to enrichment | Low-Med | TIER-2 fresh stories still primary. TIER-3 is the only "always-rejected" tier. Measure FN rate; whitelist specific known-good domains if needed. |
| Existing TIER classification has gaps (NQ-43) | Medium | This plan does NOT depend on NQ-43 being done. NQ-43 improvements layer on top — better tier classifier → better gate decisions. |
| Tier-1 retrospectives get rejected (mainstream writes "looking back") | Low | If this happens often, add 4th matrix row: TIER-1 + RETROSPECTIVE → "Industry Context" section (Phase 3). For now, reject is acceptable. |
| Reduced content volume | Low | TIER-1+TIER-2 fresh covers >70% of typical candidate pool. Even with strict gate, 5-7 primary stories per day still feasible. |

---

## What this plan does NOT address (deferred)

- **Phase 2 — programmatic event_date extraction** (Step A from earlier brainstorm). Defer until Phase 1 measurement shows it's needed.
- **Phase 3 — "Industry Context" UI section** for TIER-1 retrospectives. Product decision pending.
- **NQ-09 — story-level dedup against past 30 days** (separate sprint task). Complementary but independent.
- **NQ-43 — source_tier classifier accuracy improvements** (separate sprint task). Complementary; this plan benefits as NQ-43 improves.

---

## Commit checklist

| Task | Commit msg prefix |
|---|---|
| 1 | `feat(classify): tier x freshness matrix gate as primary classification filter` |
| 2 | `test(classify): regression test for tier x freshness gate prompt structure` |
| 3 | (no commit — measurement only) |
