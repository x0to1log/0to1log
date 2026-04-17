# Weekly Hardening Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add source metadata pipeline, quality scoring, persona titles, auto-publish, and length recalibration to the weekly news pipeline.

**Architecture:** 6 tasks in dependency order (T4→T3→T1→T2→T6→T5). Each task is self-contained with its own commit. Weekly pipeline (`run_weekly_pipeline` in `pipeline.py`) is the integration point; quality scoring lives in a new `_check_weekly_quality()` in `pipeline_quality.py`.

**Tech Stack:** Python 3.11, FastAPI, Supabase (PostgreSQL), OpenAI API, Astro v5 (frontend)

**Spec:** `vault/09-Implementation/plans/2026-04-17-weekly-hardening-phase2-design.md`

---

## Chunk 1: T4 + T3 (Length Target + Persona Titles)

### Task T4: Length Target 상향

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py:1125-1131` (expert length target)
- Modify: `backend/services/agents/prompts_news_pipeline.py:1227-1233` (learner length target)

- [ ] **Step 1: Update expert length target**

In `WEEKLY_EXPERT_PROMPT`, find the Length Target section (~line 1125):

```python
# Change this line:
- **Total EN content (en field): aim for 12000+ chars**
# To:
- **Total EN content (en field): aim for 16000+ chars**
```

Also update the component breakdown:
```python
# Change:
- Other sections (One-Line + Numbers + Watch Points + Open Source + Actions): ~3000-4000 chars combined
# To:
- Other sections (One-Line + Numbers + Watch Points + Open Source + Actions): ~4000-5000 chars combined
```

- [ ] **Step 2: Update learner length target**

In `WEEKLY_LEARNER_PROMPT`, find the Length Target section (~line 1227):

```python
# Change this line:
- **Total EN content (en field): aim for 10000+ chars**
# To:
- **Total EN content (en field): aim for 13000+ chars**
```

Also update the component breakdown:
```python
# Change:
- Other sections (One-Line + Numbers + Watch Points + Open Source + Actions): ~2500-3500 chars combined
# To:
- Other sections (One-Line + Numbers + Watch Points + Open Source + Actions): ~3500-4500 chars combined
```

- [ ] **Step 3: Run tests**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_news_digest_prompts.py -q --tb=short`
Expected: All pass

Run: `.venv/Scripts/python.exe -m ruff check services/agents/prompts_news_pipeline.py`
Expected: All checks passed

- [ ] **Step 4: Commit**

```bash
git add backend/services/agents/prompts_news_pipeline.py
git commit -m "chore(weekly): raise length targets to match Phase 1 output reality

Expert: 12000+ → 16000+ chars, Learner: 10000+ → 13000+ chars.
Based on W13-W14 actual output (expert 14k-19k, learner 14k-17k)."
```

---

### Task T3: Persona Titles

**Files:**
- Create: `supabase/migrations/00052_news_title_learner.sql`
- Modify: `backend/services/pipeline.py:1984-1985` (weekly headline save)
- Modify: `backend/services/pipeline.py:2045-2060` (weekly row build)
- Modify: `backend/services/pipeline_digest.py:926-931` (daily row build)
- Modify: `frontend/src/lib/personaTitle.ts:19-27,43-48` (add title_learner column support)
- Modify: `backend/core/config.py` (no change needed — title_learner is DB-only)

- [ ] **Step 1: Create migration**

Create `supabase/migrations/00052_news_title_learner.sql`:

```sql
-- Add top-level title_learner column to news_posts
ALTER TABLE news_posts ADD COLUMN IF NOT EXISTS title_learner TEXT;

-- Backfill from guide_items.title_learner for existing posts
UPDATE news_posts
SET title_learner = guide_items->>'title_learner'
WHERE guide_items->>'title_learner' IS NOT NULL
  AND title_learner IS NULL;
```

- [ ] **Step 2: Apply migration via Supabase dashboard**

Run the SQL in Supabase SQL Editor or via CLI:
```bash
# If using supabase CLI:
supabase db push
# Otherwise: paste SQL into Supabase Dashboard > SQL Editor > Run
```

Verify: `SELECT column_name FROM information_schema.columns WHERE table_name = 'news_posts' AND column_name = 'title_learner';` should return 1 row.

- [ ] **Step 3: Update weekly pipeline — headline extraction**

In `backend/services/pipeline.py`, find lines ~1984-1985:

```python
# BEFORE:
headline_en = expert_data.get("headline") or learner_data.get("headline") or f"AI Weekly — {week_id}"
headline_ko = expert_data.get("headline_ko") or learner_data.get("headline_ko") or headline_en

# AFTER:
headline_en = expert_data.get("headline") or f"AI Weekly — {week_id}"
headline_learner_en = learner_data.get("headline") or headline_en
headline_ko = expert_data.get("headline_ko") or headline_en
headline_learner_ko = learner_data.get("headline_ko") or headline_ko
```

- [ ] **Step 4: Update weekly pipeline — row build**

In the `for locale in ("en", "ko"):` loop (~line 2015-2060), update title assignment and add title_learner to row:

```python
# BEFORE:
title = headline_en if locale == "en" else headline_ko

# AFTER:
title = headline_en if locale == "en" else headline_ko
title_learner = headline_learner_en if locale == "en" else headline_learner_ko
```

Add to row dict:
```python
row = {
    "title": title,
    "title_learner": title_learner,
    # ... rest unchanged
}
```

- [ ] **Step 5: Update daily pipeline — add title_learner to row**

In `backend/services/pipeline_digest.py`, find the row-build section near line 930. The existing code writes to `guide_items["title_learner"]`. Add a top-level column write alongside it:

After line `guide_items["title_learner"] = learner_title` (line 927), find where `row` is built (before the `supabase.table("news_posts").upsert(row, ...)` call) and add:

```python
row["title_learner"] = learner_title if learner_title else None
```

Keep the `guide_items["title_learner"]` write for backward compat.

- [ ] **Step 6: Update frontend personaTitle.ts**

In `frontend/src/lib/personaTitle.ts`, update the interface and resolution logic:

```typescript
// Update interface (line 19-27):
export interface PersonaResolvableContent {
  title?: string | null;
  title_learner?: string | null;  // NEW: top-level column
  excerpt?: string | null;
  guide_items?: {
    title_learner?: string;
    excerpt_learner?: string;
    [key: string]: any;
  } | null;
}

// Update resolution (line 43-48):
if (persona === 'learner') {
  const learnerTitle = post.title_learner || post.guide_items?.title_learner;
  return {
    title: learnerTitle || canonicalTitle,
    excerpt: post.guide_items?.excerpt_learner || canonicalExcerpt,
  };
}
```

- [ ] **Step 7: Run tests + build**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
cd ../frontend && npm run build
```

Expected: Both pass.

- [ ] **Step 8: Commit**

```bash
git add supabase/migrations/00052_news_title_learner.sql \
        backend/services/pipeline.py \
        backend/services/pipeline_digest.py \
        frontend/src/lib/personaTitle.ts
git commit -m "feat: add title_learner column for persona-specific headlines

- DB migration: title_learner column + backfill from guide_items
- Weekly pipeline: save expert/learner headlines separately
- Daily pipeline: dual-write to column + guide_items (backward compat)
- Frontend: personaTitle.ts prefers column over guide_items"
```

---

## Chunk 2: T1 (Source Pipeline)

### Task T1: Source Pipeline — Daily Metadata to Weekly LLM

**Files:**
- Modify: `backend/services/pipeline_persistence.py:169-171` (_fetch_week_digests select)
- Modify: `backend/services/pipeline.py:1861-1876` (persona_inputs build)
- Modify: `backend/services/pipeline.py:2004-2007` (_renumber_citations with allowed_urls)

- [ ] **Step 1: Extend _fetch_week_digests select**

In `backend/services/pipeline_persistence.py`, line 171:

```python
# BEFORE:
.select("slug, title, post_type, content_expert, content_learner, published_at, guide_items")

# AFTER:
.select("slug, title, post_type, content_expert, content_learner, published_at, guide_items, source_cards, source_urls")
```

- [ ] **Step 2: Build URL metadata map in run_weekly_pipeline**

In `backend/services/pipeline.py`, after the `_fetch_week_digests` calls (~line 1843) and before the `persona_inputs` build (~line 1861), add:

```python
        # Build URL → tier/kind map from daily source_cards
        url_meta: dict[str, dict] = {}
        for d in digests_en + digests_ko:
            for card in (d.get("source_cards") or []):
                url = card.get("url", "")
                if url and url not in url_meta:
                    url_meta[url] = {
                        "source_tier": card.get("source_tier", ""),
                        "source_kind": card.get("source_kind", ""),
                    }
        aggregate_urls = set(url_meta.keys())

        # Classify primary vs secondary for LLM reference
        primary_urls = [u for u, m in url_meta.items()
                        if (m.get("source_tier") or "").lower() == "primary"]
        secondary_urls = [u for u, m in url_meta.items()
                          if (m.get("source_tier") or "").lower() != "primary" and u not in primary_urls]
```

- [ ] **Step 3: Prepend SOURCE REFERENCE to persona_inputs**

In the persona_inputs build loop (~line 1862-1876), after building parts list and before joining, prepend the source reference:

```python
        # Build per-persona input (EN primary + KO reference)
        persona_inputs: dict[str, str] = {}

        source_ref_lines = []
        if primary_urls:
            source_ref_lines.append("PRIMARY: " + " | ".join(primary_urls[:30]))
        if secondary_urls:
            source_ref_lines.append("SECONDARY: " + " | ".join(secondary_urls[:30]))
        source_ref = ""
        if source_ref_lines:
            source_ref = "## SOURCE REFERENCE (for citation priority — cite PRIMARY URLs before SECONDARY)\n" + "\n".join(source_ref_lines) + "\n\n"

        for persona in ("expert", "learner"):
            content_key = f"content_{persona}"
            parts = []
            for d in digests_en:
                content = d.get(content_key, "")
                if content:
                    parts.append(f"--- {d['post_type'].upper()} EN ({d.get('published_at', '')}) ---\n# {d['title']}\n\n{content}")
            for d in digests_ko:
                content = d.get(content_key, "")
                if content:
                    parts.append(f"--- {d['post_type'].upper()} KO ({d.get('published_at', '')}) ---\n# {d['title']}\n\n{content}")
            persona_inputs[persona] = source_ref + "\n\n".join(parts)
```

- [ ] **Step 4: Pass allowed_urls to _renumber_citations**

In `backend/services/pipeline.py`, update the renumber calls (~line 2004-2007):

```python
# BEFORE:
en_expert, en_expert_cards = _renumber_citations(en_expert)
ko_expert, ko_expert_cards = _renumber_citations(ko_expert)
en_learner, en_learner_cards = _renumber_citations(en_learner)
ko_learner, ko_learner_cards = _renumber_citations(ko_learner)

# AFTER:
en_expert, en_expert_cards = _renumber_citations(en_expert, allowed_urls=aggregate_urls if aggregate_urls else None)
ko_expert, ko_expert_cards = _renumber_citations(ko_expert, allowed_urls=aggregate_urls if aggregate_urls else None)
en_learner, en_learner_cards = _renumber_citations(en_learner, allowed_urls=aggregate_urls if aggregate_urls else None)
ko_learner, ko_learner_cards = _renumber_citations(ko_learner, allowed_urls=aggregate_urls if aggregate_urls else None)
```

Note: `aggregate_urls` might be empty for weeks where daily posts lack source_cards (pre-Phase-1 data). The `if aggregate_urls else None` ensures graceful fallback (no URL stripping when allowlist is empty).

- [ ] **Step 5: Run tests + lint**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
.venv/Scripts/python.exe -m ruff check services/pipeline.py services/pipeline_persistence.py
```

Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add backend/services/pipeline_persistence.py backend/services/pipeline.py
git commit -m "feat(weekly): pass daily source_cards to weekly LLM for primary source priority

- _fetch_week_digests now selects source_cards + source_urls
- Build url_meta map (URL → tier/kind) from daily source_cards
- Prepend SOURCE REFERENCE section to weekly LLM input (PRIMARY vs SECONDARY)
- _renumber_citations now uses aggregate_urls as hallucination allowlist"
```

---

## Chunk 3: T2 (Quality Measurement)

### Task T2: Weekly Quality Scoring

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py` (add 2 new prompt constants)
- Modify: `backend/services/pipeline_quality.py` (add `_check_weekly_quality()`)
- Modify: `backend/services/pipeline.py` (call quality check in `run_weekly_pipeline`)

- [ ] **Step 1: Add QUALITY_CHECK_WEEKLY_EXPERT prompt**

In `backend/services/agents/prompts_news_pipeline.py`, after `QUALITY_CHECK_FRONTLOAD` (~line 1529+), add:

```python
QUALITY_CHECK_WEEKLY_EXPERT = """You are a strict quality reviewer for a weekly AI industry recap written for strategic decision-makers.

The input contains BOTH the English and Korean body for the same persona. Evaluate both together. If either locale is noticeably weaker, reflect that in the score and issues. Do not give full marks when one locale has clear quality problems.

Score this weekly digest on 4 criteria (0-25 each, total 0-100).

**Scoring calibration** (0-25, use full range): 25 exemplary · 22-23 strong · 19-21 solid · 15-17 acceptable · 10-13 below bar · 5-8 weak · 0-3 broken. Default to 19-22 for typical "good but not exceptional"; reserve 25 for standout only. Ask "is there any gap I could name?" — if yes, drop to 22.

1. **Section Completeness** (25):
   Required sections: This Week in One Line, Week in Numbers, Top Stories, Trend Analysis, Watch Points, Open Source Spotlight, So What Do I Do?
   - 25: All 7 sections present with substantial content (200+ chars each), proper ## headings
   - 18: All sections present but 1-2 are thin (<150 chars)
   - 10: 1+ section missing or severely thin
   - 0: Content structure is broken

2. **Source Quality** (25):
   - 25: >80% of Top Stories cite primary source first (company blog, arxiv, official repo); Trend Analysis has per-paragraph citations; Watch Points and Actions cite sources
   - 18: >60% primary-first; most sections have citations but some gaps
   - 10: <50% primary-first or multiple sections lack citations
   - 0: Citations largely absent or hallucinated

3. **Depth & Synthesis** (25):
   - 25: Top Stories follow WHAT/WHY/CONTEXT structure with 4-5 sentences; Trend Analysis identifies 2+ distinct themes and traces evolution across the week (not headline restatement)
   - 18: Top Stories have structure but some are thin; Trend Analysis has themes but tracing is weak
   - 10: Top Stories are shallow summaries; Trend Analysis restates headlines
   - 0: Content is bullet-point news with no analysis

4. **Language & Tone** (25):
   - 25: Analyst voice; calibrated language (signals/suggests not predicts); no banned framing words; KO version is natural Korean with all citations preserved
   - 18: Mostly calibrated but 1-2 instances of prediction language or aggressive framing
   - 10: Multiple tone violations; KO citations partially lost
   - 0: Chatty tone, predictions throughout, or KO citation collapse

Return JSON only:
{
  "section_completeness": {"score": N, "issues": ["..."]},
  "source_quality": {"score": N, "issues": ["..."]},
  "depth_synthesis": {"score": N, "issues": ["..."]},
  "language_tone": {"score": N, "issues": ["..."]},
  "total_score": N,
  "summary": "One sentence overall assessment"
}"""
```

- [ ] **Step 2: Add QUALITY_CHECK_WEEKLY_LEARNER prompt**

Same file, after the expert prompt:

```python
QUALITY_CHECK_WEEKLY_LEARNER = """You are a quality reviewer for a weekly AI digest written for non-specialist knowledge workers.

The input contains BOTH the English and Korean body for the same persona. Evaluate both together. If either locale is noticeably weaker, reflect that in the score and issues. Do not give full marks when one locale has clear quality problems.

Score this weekly digest on 4 criteria (0-25 each, total 0-100).

**Scoring calibration** (0-25, use full range): 25 exemplary · 22-23 strong · 19-21 solid · 15-17 acceptable · 10-13 below bar · 5-8 weak · 0-3 broken. Default to 19-22 for typical "good but not exceptional"; reserve 25 for standout only.

1. **Section Completeness** (25):
   Required sections: This Week in One Line, Week in Numbers, Top Stories, Trend Analysis, Watch Points, Open Source Spotlight, What Can I Try?
   - 25: All 7 sections present with substantial content (200+ chars each)
   - 18: All sections present but 1-2 are thin
   - 10: 1+ section missing
   - 0: Content structure broken

2. **Source Quality** (25):
   - 25: Top Stories cite sources; Trend Analysis and Watch Points have citations; What Can I Try links to resources
   - 18: Most sections have citations but some gaps
   - 10: Multiple sections lack citations
   - 0: Citations largely absent

3. **Depth & Accessibility** (25):
   - 25: Top Stories follow WHAT/WHY/CONTEXT for non-specialists; acronyms expanded; analogies where helpful; Trend Analysis in plain language with real synthesis
   - 18: Mostly accessible but some jargon unexplained; Trend Analysis present but thin
   - 10: Too technical for target audience; Trend Analysis is headline list
   - 0: Inaccessible or trivially shallow

4. **Language & Tone** (25):
   - 25: Clear editorial prose (not chatty, not lecturing); no chat tone; KO citations preserved; numbers have context
   - 18: Mostly good but occasional tone slip
   - 10: Tone inconsistent; KO citations partially lost
   - 0: Chat tone throughout or KO broken

Return JSON only:
{
  "section_completeness": {"score": N, "issues": ["..."]},
  "source_quality": {"score": N, "issues": ["..."]},
  "depth_accessibility": {"score": N, "issues": ["..."]},
  "language_tone": {"score": N, "issues": ["..."]},
  "total_score": N,
  "summary": "One sentence overall assessment"
}"""
```

- [ ] **Step 3: Add _check_weekly_quality() to pipeline_quality.py**

In `backend/services/pipeline_quality.py`, add a new function after `_check_digest_quality()`:

```python
async def _check_weekly_quality(
    content_expert_en: str,
    content_learner_en: str,
    content_expert_ko: str,
    content_learner_ko: str,
    source_urls: list[str],
    supabase,
    run_id: str,
    cumulative_usage: dict[str, Any],
) -> dict[str, Any]:
    """Score quality of generated weekly digest."""
    t0 = time.monotonic()
    from services.agents.prompts_news_pipeline import (
        QUALITY_CHECK_WEEKLY_EXPERT, QUALITY_CHECK_WEEKLY_LEARNER,
    )

    if not content_expert_en:
        logger.warning("Weekly quality check skipped: no expert EN content")
        await _log_stage(
            supabase, run_id, "quality:weekly", "skipped", t0,
            output_summary="No expert content", post_type="weekly",
        )
        return {"quality_score": 0, "quality_flags": ["no_expert_content"]}

    client = get_openai_client()
    model = settings.openai_model_main
    issues_all: list[str] = []
    llm_scores: list[int] = []

    # Expert quality check
    expert_input = f"## English Expert\n\n{content_expert_en}\n\n## Korean Expert\n\n{content_expert_ko}"
    try:
        expert_resp = await asyncio.wait_for(
            client.chat.completions.create(
                **compat_create_kwargs(
                    model,
                    messages=[
                        {"role": "system", "content": QUALITY_CHECK_WEEKLY_EXPERT},
                        {"role": "user", "content": expert_input},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2,
                    max_tokens=2000,
                )
            ),
            timeout=120,
        )
        expert_raw = expert_resp.choices[0].message.content or ""
        expert_usage = extract_usage_metrics(expert_resp, model)
        cumulative_usage.update(merge_usage_metrics(cumulative_usage, expert_usage))
        expert_data = parse_ai_json(expert_raw, "weekly-quality-expert")
        expert_score = expert_data.get("total_score", 0)
        llm_scores.append(expert_score)
        for cat in ["section_completeness", "source_quality", "depth_synthesis", "language_tone"]:
            for issue in (expert_data.get(cat, {}).get("issues") or []):
                issues_all.append(f"expert:{cat}:{issue}")
    except Exception as e:
        logger.warning("Weekly expert quality check failed: %s", e)
        expert_score = 0

    # Learner quality check
    if content_learner_en:
        learner_input = f"## English Learner\n\n{content_learner_en}\n\n## Korean Learner\n\n{content_learner_ko}"
        try:
            learner_resp = await asyncio.wait_for(
                client.chat.completions.create(
                    **compat_create_kwargs(
                        model,
                        messages=[
                            {"role": "system", "content": QUALITY_CHECK_WEEKLY_LEARNER},
                            {"role": "user", "content": learner_input},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.2,
                        max_tokens=2000,
                    )
                ),
                timeout=120,
            )
            learner_raw = learner_resp.choices[0].message.content or ""
            learner_usage = extract_usage_metrics(learner_resp, model)
            cumulative_usage.update(merge_usage_metrics(cumulative_usage, learner_usage))
            learner_data = parse_ai_json(learner_raw, "weekly-quality-learner")
            learner_score = learner_data.get("total_score", 0)
            llm_scores.append(learner_score)
            for cat in ["section_completeness", "source_quality", "depth_accessibility", "language_tone"]:
                for issue in (learner_data.get(cat, {}).get("issues") or []):
                    issues_all.append(f"learner:{cat}:{issue}")
        except Exception as e:
            logger.warning("Weekly learner quality check failed: %s", e)

    # URL validation
    url_penalty = 0
    if source_urls:
        fact_pack_for_validation = {"news_items": [{"url": u} for u in source_urls]}
        url_result = validate_citation_urls(content_expert_en, fact_pack_for_validation)
        hallucinated = url_result.get("hallucinated_count", 0)
        if hallucinated > 0:
            url_penalty = min(hallucinated * 3, 15)
            issues_all.append(f"url_validation:{hallucinated} hallucinated URLs (-{url_penalty})")

    # Structural penalties
    structural_penalty = 0
    structural_warnings: list[str] = []
    if len(content_expert_en) < 10000:
        structural_penalty += 5
        structural_warnings.append("expert_en_short")
    if content_expert_ko and len(content_expert_ko) < 6000:
        structural_penalty += 5
        structural_warnings.append("expert_ko_short")

    # Final score
    llm_avg = round(sum(llm_scores) / len(llm_scores)) if llm_scores else 0
    final_score = max(0, llm_avg - url_penalty - structural_penalty)

    quality_flags = []
    if url_penalty: quality_flags.append("url_hallucination")
    if structural_warnings: quality_flags.extend(structural_warnings)

    auto_publish_eligible = final_score >= settings.auto_publish_threshold

    logger.info(
        "Weekly quality: final=%d (llm_avg=%d, url_penalty=-%d, structural=-%d), eligible=%s",
        final_score, llm_avg, url_penalty, structural_penalty, auto_publish_eligible,
    )

    await _log_stage(
        supabase, run_id, "quality:weekly", "success", t0,
        output_summary=f"score={final_score} (llm={llm_avg}, url=-{url_penalty}, struct=-{structural_penalty})",
        post_type="weekly",
        debug_meta={"quality_score": final_score, "issues": issues_all[:20]},
    )

    return {
        "quality_score": final_score,
        "quality_flags": quality_flags,
        "content_analysis": {"issues": issues_all[:30]},
        "auto_publish_eligible": auto_publish_eligible,
    }
```

Ensure the necessary imports are available at the top of `pipeline_quality.py`:
- `asyncio`, `time`, `logger` (already imported)
- `get_openai_client`, `extract_usage_metrics`, `merge_usage_metrics`, `parse_ai_json` — import from `services.agents.client`
- `build_completion_kwargs` — already imported in pipeline_quality.py (line 25). Use this instead of `compat_create_kwargs`.
- `settings` from `core.config`
- `_log_stage` (already in the file or imported)

**IMPORTANT**: In the code above, replace all `compat_create_kwargs(` with `build_completion_kwargs(`. pipeline_quality.py uses `build_completion_kwargs`, not `compat_create_kwargs`.

- [ ] **Step 4: Call _check_weekly_quality from run_weekly_pipeline**

In `backend/services/pipeline.py`, after the renumber block (~line 2012) and before the save loop (~line 2014), add:

```python
            # Quality check
            from services.pipeline_quality import _check_weekly_quality
            quality_result = await _check_weekly_quality(
                content_expert_en=en_expert,
                content_learner_en=en_learner,
                content_expert_ko=ko_expert,
                content_learner_ko=ko_learner,
                source_urls=list(aggregate_urls) if aggregate_urls else [],
                supabase=supabase,
                run_id=run_id,
                cumulative_usage=cumulative_usage,
            )
            quality_score = quality_result.get("quality_score")
            quality_flags = quality_result.get("quality_flags")
            content_analysis = quality_result.get("content_analysis")
            auto_publish = quality_result.get("auto_publish_eligible", False)
```

Then in the row dict (~line 2045+), add these fields:

```python
                row = {
                    # ... existing fields ...
                    "quality_score": quality_score,
                    "quality_flags": quality_flags,
                    "content_analysis": content_analysis,
                    "fact_pack": {},  # weekly has no classified items; empty dict for schema consistency
                }
```

- [ ] **Step 5: Run tests + lint**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
.venv/Scripts/python.exe -m ruff check services/pipeline.py services/pipeline_quality.py services/agents/prompts_news_pipeline.py
```

- [ ] **Step 6: Commit**

```bash
git add backend/services/agents/prompts_news_pipeline.py \
        backend/services/pipeline_quality.py \
        backend/services/pipeline.py
git commit -m "feat(weekly): add quality scoring with _check_weekly_quality()

- QUALITY_CHECK_WEEKLY_EXPERT + _LEARNER prompts (4-axis, 0-100)
- _check_weekly_quality(): LLM scoring + URL validation + structural checks
- run_weekly_pipeline calls quality check, saves quality_score/flags/analysis"
```

---

## Chunk 4: T6 + T5 (Auto-publish + Few-shot)

### Task T6: Auto-publish

**Files:**
- Modify: `backend/core/config.py` (add setting)
- Modify: `backend/services/pipeline.py` (auto-publish logic in run_weekly_pipeline)

- [ ] **Step 1: Add config setting**

In `backend/core/config.py`, in the Settings class:

```python
# Add after weekly_email_enabled:
weekly_auto_publish: bool = False
```

- [ ] **Step 2: Add auto-publish logic to run_weekly_pipeline**

In `backend/services/pipeline.py`, in the save loop where `row["status"]` is set (~line 2051):

```python
# BEFORE:
"status": "draft",

# AFTER:
"status": "published" if (auto_publish and settings.weekly_auto_publish) else "draft",
# Note: auto_publish uses settings.auto_publish_threshold (currently 85).
# Spec suggested 70 for weekly but we inherit the global 85 for now.
# Adjust via env var AUTO_PUBLISH_THRESHOLD if needed.
```

- [ ] **Step 3: Run tests + lint**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
.venv/Scripts/python.exe -m ruff check core/config.py services/pipeline.py
```

- [ ] **Step 4: Commit**

```bash
git add backend/core/config.py backend/services/pipeline.py
git commit -m "feat(weekly): auto-publish when WEEKLY_AUTO_PUBLISH=true and quality passes

Reads WEEKLY_AUTO_PUBLISH env var (default false). When enabled, weekly
posts with quality_score >= auto_publish_threshold get status=published
instead of draft."
```

---

### Task T5: Few-shot Examples

**Prerequisite:** T2 complete + 4 weeks of quality data (W13-W16). This task should be deferred until data is available.

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py` (WEEKLY_EXPERT_PROMPT, WEEKLY_LEARNER_PROMPT)

- [ ] **Step 1: Select best-scoring weekly output**

```sql
SELECT slug, quality_score, content_expert, content_learner
FROM news_posts
WHERE post_type = 'weekly' AND locale = 'en' AND quality_score IS NOT NULL
ORDER BY quality_score DESC
LIMIT 1;
```

- [ ] **Step 2: Extract 1 Top Story item + 1 Trend Analysis paragraph**

From the best-scoring output, manually select:
- 1 Top Story that has primary-source-first citation, WHAT/WHY/CONTEXT, 4-5 sentences
- 1 Trend Analysis paragraph with theme evolution and per-paragraph citation

Total: ~300-400 tokens.

- [ ] **Step 3: Add few-shot to WEEKLY_EXPERT_PROMPT**

In the `## CRITICAL: "en" field structure example` section, replace the generic example with the real one extracted in Step 2. Keep the structure markers (`## Top Stories`, `## Trend Analysis`) intact.

- [ ] **Step 4: Add few-shot to WEEKLY_LEARNER_PROMPT**

Same pattern, using the learner version of the best output.

- [ ] **Step 5: Run tests + lint**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/test_news_digest_prompts.py -q --tb=short
.venv/Scripts/python.exe -m ruff check services/agents/prompts_news_pipeline.py
```

- [ ] **Step 6: Commit**

```bash
git add backend/services/agents/prompts_news_pipeline.py
git commit -m "feat(weekly): add few-shot examples from highest-scoring weekly output

Expert and learner prompts each get 1 real Top Story + 1 Trend Analysis
paragraph from W[XX] (score=[YY]) as quality anchors."
```
