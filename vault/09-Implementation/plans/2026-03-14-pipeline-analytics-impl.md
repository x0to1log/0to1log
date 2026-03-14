# Pipeline Analytics Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 파이프라인 단계별 토큰/비용/품질을 트래킹하는 debug_meta 강화 + 어드민 대시보드 구현

**Architecture:** 백엔드는 기존 `pipeline_logs.debug_meta` JSONB에 input/output 토큰, attempts, quality_score를 추가 기록. 프론트엔드는 기존 [runId] 상세 페이지에 비용 breakdown 추가 + 신규 analytics 페이지에 Chart.js 시계열 차트 구현.

**Tech Stack:** FastAPI, Supabase (기존 테이블), Astro v5, Chart.js CDN

**Design doc:** `vault/09-Implementation/plans/2026-03-14-pipeline-analytics-dashboard.md`

---

### Task 1: business.py — expert/derive usage 분리 반환 + attempts

**Files:**
- Modify: `backend/services/agents/business.py`
- Test: `backend/tests/test_business_retry.py`

**Step 1: Update `generate_business_expert()` to include attempts in usage**

In `generate_business_expert()`, before returning, add `attempts` to `cumulative_usage`:

```python
# line 146-147, change:
logger.info("BusinessExpert success on attempt %d", attempt + 1)
return data, cumulative_usage
# to:
logger.info("BusinessExpert success on attempt %d", attempt + 1)
cumulative_usage["attempts"] = attempt + 1
return data, cumulative_usage
```

**Step 2: Update `derive_business_personas()` to include attempts in usage**

Same pattern at line 194-195:

```python
logger.info("BusinessDerive success on attempt %d", attempt + 1)
cumulative_usage["attempts"] = attempt + 1
return data, cumulative_usage
```

**Step 3: Change `generate_business_post()` to return expert/derive usage separately**

Change the return type and body (lines 210-240):

```python
async def generate_business_post(
    candidate: RankedCandidate,
    related: RelatedPicks | None,
    context: str,
    batch_id: str,
) -> tuple[BusinessPost, dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Generate a complete Business post using the Expert-First 2-Call Cascade.

    Returns (validated BusinessPost, total_usage, expert_usage, derive_usage).
    """
    expert_data, expert_usage = await generate_business_expert(
        candidate, related, context, batch_id,
    )
    derive_data, derive_usage = await derive_business_personas(
        expert_data.get("content_expert", ""),
    )

    combined = {
        **expert_data,
        "content_learner": derive_data.get("content_learner", ""),
        "content_beginner": derive_data.get("content_beginner", ""),
    }

    post = BusinessPost.model_validate(combined)
    total_usage = merge_usage_metrics(expert_usage, derive_usage)

    return post, total_usage, expert_usage, derive_usage
```

**Step 4: Run existing tests to verify no breakage**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_business_retry.py -v --tb=short`

Expected: Tests may fail if they unpack 2 values from `generate_business_post`. Fix any unpacking.

**Step 5: Commit**

```bash
git add backend/services/agents/business.py backend/tests/test_business_retry.py
git commit -m "feat: return expert/derive usage separately from generate_business_post"
```

---

### Task 2: research.py + ranking.py + translate.py — attempts 추가

**Files:**
- Modify: `backend/services/agents/research.py`
- Modify: `backend/services/agents/ranking.py`
- Modify: `backend/services/agents/translate.py`

**Step 1: research.py — add attempts to usage_recorder**

In `generate_research_post()`, after line 137-139 (`usage_recorder.update(aggregate_usage)`), add attempts tracking. The simplest: after the successful return (line 176), add `aggregate_usage["attempts"] = attempt + 1` before returning. Do this for both return paths (line 175 expanded return and line 176 normal return):

```python
# Before both `return validated` / `return expanded` lines, add:
aggregate_usage["attempts"] = attempt + 1
if usage_recorder is not None:
    usage_recorder.clear()
    usage_recorder.update(aggregate_usage)
```

**Step 2: ranking.py — add attempts (single-call, always 1)**

After line 49 (`usage_recorder.update(merged_usage)`), the ranking agent does a single call with no retry loop, so just add:

```python
if usage_recorder is not None:
    merged_usage["attempts"] = 1
    usage_recorder.clear()
    usage_recorder.update(merged_usage)
```

**Step 3: translate.py — add attempts to both translate functions**

In `_translate_research()` line 150-151, before return:
```python
cumulative_usage["attempts"] = attempt + 1
```

In `_translate_business()` line 210-211, before return:
```python
cumulative_usage["attempts"] = attempt + 1
```

**Step 4: Run tests**

Run: `cd backend && .venv/Scripts/python -m pytest tests/ -v --tb=short -k "agent or research or translation or ranking"`

Expected: PASS (attempts field is additive, doesn't break existing tests)

**Step 5: Commit**

```bash
git add backend/services/agents/research.py backend/services/agents/ranking.py backend/services/agents/translate.py
git commit -m "feat: add attempts count to all agent usage metrics"
```

---

### Task 3: pipeline.py — debug_meta 강화 + quality_score + business usage 분리

**Files:**
- Modify: `backend/services/pipeline.py`
- Test: `backend/tests/test_pipeline_logging.py`

**Step 1: Update business.generate.en caller to unpack 4 values**

Line 1042, change:
```python
business_post, business_usage = await generate_business_post(...)
```
to:
```python
business_post, business_usage, expert_usage, derive_usage = await generate_business_post(...)
```

**Step 2: Enhance research.generate.en debug_meta**

Line 966-971, change to:
```python
debug_meta={
    "research_en_len": len(research_post.content_original or ""),
    "has_news": research_post.has_news,
    "resumed_from_saved_en": saved_research_en_row is not None,
    "input_tokens": research_usage.get("input_tokens"),
    "output_tokens": research_usage.get("output_tokens"),
    "attempts": research_usage.get("attempts", 1),
},
```

**Step 3: Enhance research.translate.ko debug_meta**

Line 1003-1007, change to:
```python
debug_meta={
    "research_ko_len": len(ko_research.content_original or ""),
    "has_news": ko_research.has_news,
    "resumed_from_saved_en": saved_research_en_row is not None,
    "input_tokens": research_tr_usage.get("input_tokens"),
    "output_tokens": research_tr_usage.get("output_tokens"),
    "attempts": research_tr_usage.get("attempts", 1),
},
```

**Step 4: Enhance business.generate.en debug_meta with expert/derive split**

Line 1074-1085, change to:
```python
debug_meta={
    "business_analysis_len": len(business_post.content_analysis or ""),
    "persona_lengths": {
        "beginner": len(business_post.content_beginner or ""),
        "learner": len(business_post.content_learner or ""),
        "expert": len(business_post.content_expert or ""),
    },
    "fact_pack_keys": list((business_post.fact_pack or {}).keys()),
    "source_card_count": len(business_post.source_cards or []),
    "resumed_from_saved_en": saved_business_en_row is not None,
    "input_tokens": business_usage.get("input_tokens"),
    "output_tokens": business_usage.get("output_tokens"),
    "expert_call_tokens": {
        "input": expert_usage.get("input_tokens"),
        "output": expert_usage.get("output_tokens"),
    },
    "derive_call_tokens": {
        "input": derive_usage.get("input_tokens"),
        "output": derive_usage.get("output_tokens"),
    },
    "attempts": {
        "expert": expert_usage.get("attempts", 1),
        "derive": derive_usage.get("attempts", 1),
    },
},
```

**Step 5: Enhance business.translate.ko debug_meta**

Line 1116-1123, change to:
```python
debug_meta={
    "business_analysis_len": len(ko_business.content_analysis or ""),
    "persona_lengths": {
        "beginner": len(ko_business.content_beginner or ""),
        "learner": len(ko_business.content_learner or ""),
        "expert": len(ko_business.content_expert or ""),
    },
    "input_tokens": business_tr_usage.get("input_tokens"),
    "output_tokens": business_tr_usage.get("output_tokens"),
    "attempts": business_tr_usage.get("attempts", 1),
},
```

**Step 6: Add quality_score after KO research save**

After line 1019 (`log_pipeline_stage(run_id, "save.research.ko", ...)`), add:
```python
from services.quality import compute_quality
# ... (import at file top)

# After KO research save log:
research_quality_score, research_quality_flags = compute_quality(ko_research.model_dump())
log_pipeline_stage(
    run_id, "quality.research", "success",
    post_type="research", locale="ko",
    debug_meta={
        "quality_score": research_quality_score,
        "quality_flags": research_quality_flags,
    },
)
```

**Step 7: Add quality_score after KO business save**

After line 1135 (`log_pipeline_stage(run_id, "save.business.ko", ...)`), add:
```python
business_quality_score, business_quality_flags = compute_quality(ko_business.model_dump())
log_pipeline_stage(
    run_id, "quality.business", "success",
    post_type="business", locale="ko",
    debug_meta={
        "quality_score": business_quality_score,
        "quality_flags": business_quality_flags,
    },
)
```

**Step 8: Run all pipeline tests**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_pipeline_logging.py tests/test_pipeline_lock.py tests/test_pipeline_resume.py tests/test_quality.py -v --tb=short`

Expected: PASS

**Step 9: Commit**

```bash
git add backend/services/pipeline.py backend/tests/test_pipeline_logging.py
git commit -m "feat: enrich pipeline debug_meta with input/output tokens, attempts, quality_score"
```

---

### Task 4: AdminSidebar — Analytics 링크 추가

**Files:**
- Modify: `frontend/src/components/admin/AdminSidebar.astro`

**Step 1: Add activeSection type**

Line 3, change:
```typescript
activeSection?: 'dashboard' | 'posts' | 'pipeline' | 'blog' | 'handbook' | 'settings';
```
to:
```typescript
activeSection?: 'dashboard' | 'posts' | 'pipeline' | 'analytics' | 'blog' | 'handbook' | 'settings';
```

**Step 2: Add Analytics link after Pipeline Runs link**

After the Pipeline Runs `<a>` tag (line 34), add:
```html
<a href="/admin/pipeline-analytics" class:list={['admin-sidebar-link', { 'admin-sidebar-link--active': activeSection === 'analytics' }]}>
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
    <path d="M2 14l4-6 3 3 5-8" />
  </svg>
  <span>Analytics</span>
</a>
```

**Step 3: Commit**

```bash
git add frontend/src/components/admin/AdminSidebar.astro
git commit -m "feat: add Analytics link to admin sidebar"
```

---

### Task 5: [runId] 상세 페이지 — Cost Breakdown + 칩 강화

**Files:**
- Modify: `frontend/src/pages/admin/pipeline-runs/[runId].astro`

**Step 1: Add cost breakdown data computation**

After `const resumedFromSavedEn = ...` (line 153), add:
```typescript
// Cost breakdown — AI stages only
const AI_STAGES = ['rank', 'research.generate.en', 'research.translate.ko', 'business.generate.en', 'business.translate.ko', 'terms.extract'];
const costLogs = logs.filter((l) => AI_STAGES.includes(l.pipeline_type) && parseCost(l.cost_usd) !== null);
const costBreakdown = costLogs.map((l) => ({
  stage: l.pipeline_type,
  cost: parseCost(l.cost_usd) ?? 0,
  tokens: l.tokens_used ?? 0,
  inputTokens: (l.debug_meta as Record<string, unknown>)?.input_tokens as number | null,
  outputTokens: (l.debug_meta as Record<string, unknown>)?.output_tokens as number | null,
  attempts: (l.debug_meta as Record<string, unknown>)?.attempts,
  qualityScore: (l.debug_meta as Record<string, unknown>)?.quality_score as number | null,
}));
const breakdownTotal = costBreakdown.reduce((s, b) => s + b.cost, 0);
```

**Step 2: Add Cost Breakdown section in HTML**

Between the Reuse Signals section and Stage Timeline section, add:

```html
{costBreakdown.length > 0 && (
  <section class="pipeline-run-section">
    <div class="pipeline-run-section__header">
      <div>
        <h2 class="pipeline-run-section__title">Cost Breakdown</h2>
        <p class="pipeline-run-section__hint">
          Per-stage cost share. Hover for token details.
        </p>
      </div>
    </div>
    <div class="pipeline-cost-breakdown">
      {costBreakdown.map((b) => {
        const pct = breakdownTotal > 0 ? (b.cost / breakdownTotal) * 100 : 0;
        return (
          <div class="pipeline-cost-row">
            <span class="pipeline-cost-row__label">{b.stage}</span>
            <div class="pipeline-cost-row__bar-wrap">
              <div class="pipeline-cost-row__bar" style={`width: ${Math.max(pct, 1)}%`}></div>
            </div>
            <span class="pipeline-cost-row__value">{formatCurrency(b.cost)}</span>
            <span class="pipeline-cost-row__pct">{pct.toFixed(0)}%</span>
          </div>
        );
      })}
    </div>
  </section>
)}
```

**Step 3: Enhance stage card chips with input/output tokens**

In the chips section (around line 327-338), after the existing Tokens chip, add conditional input/output chips:

```html
{(() => {
  const meta = debugMetaObject(log);
  const inTok = meta.input_tokens as number | undefined;
  const outTok = meta.output_tokens as number | undefined;
  const qScore = meta.quality_score as number | undefined;
  return (
    <>
      {typeof inTok === 'number' && typeof outTok === 'number' && (
        <span class="pipeline-stage-chip">
          <span class="pipeline-stage-chip__label">In/Out</span>
          <span class="pipeline-stage-chip__value">{inTok.toLocaleString()} / {outTok.toLocaleString()}</span>
        </span>
      )}
      {typeof qScore === 'number' && (
        <span class={`pipeline-stage-chip pipeline-stage-chip--quality-${qScore >= 3 ? 'good' : qScore >= 2 ? 'mid' : 'low'}`}>
          <span class="pipeline-stage-chip__label">Quality</span>
          <span class="pipeline-stage-chip__value">{qScore}/4</span>
        </span>
      )}
    </>
  );
})()}
```

**Step 4: Add CSS for cost breakdown + quality chip**

Append to the `<style>` block:

```css
.pipeline-cost-breakdown {
  display: grid;
  gap: 0.5rem;
}

.pipeline-cost-row {
  display: grid;
  grid-template-columns: 200px 1fr 70px 40px;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.86rem;
}

.pipeline-cost-row__label {
  font-family: var(--font-code);
  color: var(--color-text-secondary);
  font-size: 0.8rem;
}

.pipeline-cost-row__bar-wrap {
  height: 18px;
  background: color-mix(in srgb, var(--color-bg-secondary) 80%, transparent);
  border: 1px solid var(--color-border);
}

.pipeline-cost-row__bar {
  height: 100%;
  background: var(--color-accent);
  opacity: 0.7;
  transition: width 0.3s ease;
}

.pipeline-cost-row__value {
  font-family: var(--font-code);
  text-align: right;
}

.pipeline-cost-row__pct {
  font-family: var(--font-code);
  color: var(--color-text-muted);
  text-align: right;
}

.pipeline-stage-chip--quality-good {
  border-color: color-mix(in srgb, var(--color-success) 60%, var(--color-border));
  background: color-mix(in srgb, var(--color-success) 12%, transparent);
}

.pipeline-stage-chip--quality-mid {
  border-color: color-mix(in srgb, var(--color-accent) 60%, var(--color-border));
  background: color-mix(in srgb, var(--color-accent) 12%, transparent);
}

.pipeline-stage-chip--quality-low {
  border-color: color-mix(in srgb, var(--color-error) 60%, var(--color-border));
  background: color-mix(in srgb, var(--color-error) 12%, transparent);
}

@media (max-width: 720px) {
  .pipeline-cost-row {
    grid-template-columns: 1fr 70px 40px;
  }
  .pipeline-cost-row__label {
    grid-column: 1 / -1;
  }
}
```

**Step 5: Build check**

Run: `cd frontend && npm run build`

Expected: 0 errors

**Step 6: Commit**

```bash
git add frontend/src/pages/admin/pipeline-runs/[runId].astro
git commit -m "feat: add cost breakdown and enhanced chips to pipeline run detail"
```

---

### Task 6: Analytics 페이지 (신규)

**Files:**
- Create: `frontend/src/pages/admin/pipeline-analytics.astro`

**Step 1: Create the analytics page**

Create `frontend/src/pages/admin/pipeline-analytics.astro` with:
- `export const prerender = false;`
- MainLayout + AdminSidebar (activeSection="analytics")
- Supabase query: last 30 days of pipeline_logs joined with pipeline_runs
- Server-side data aggregation into JSON for Chart.js
- Chart.js CDN loaded via `<script src="..." nonce={Astro.locals.cspNonce || ''}>`
- 4 charts: total cost line, stacked cost bar, token grouped bar, quality line
- Statistics summary table
- Responsive CSS matching existing admin patterns

The full page implementation is large. Key sections:

**Data query (frontmatter):**
```typescript
const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
const { data: rawLogs } = await sb
  .from('pipeline_logs')
  .select('*, pipeline_runs!inner(run_key, status, started_at)')
  .gte('pipeline_runs.started_at', thirtyDaysAgo)
  .not('pipeline_type', 'in', '("pipeline","research.novelty_gate","candidates.save","save.research.en","save.research.ko","save.business.en","save.business.ko","quality.research","quality.business")')
  .order('created_at', { ascending: true });
```

**Chart data preparation (also frontmatter):**
Group logs by `run_key`, compute per-stage costs/tokens, extract quality scores from quality.* logs.

**HTML:**
- Summary stats grid (same pattern as pipeline-runs index)
- 2x2 chart grid with `<canvas>` elements
- Statistics table

**Script:**
- Chart.js initialization with the server-prepared JSON data
- CSS variable-aware colors for dark/light theme

**Step 2: Build check**

Run: `cd frontend && npm run build`

Expected: 0 errors

**Step 3: Commit**

```bash
git add frontend/src/pages/admin/pipeline-analytics.astro
git commit -m "feat: add pipeline analytics page with cost/token/quality charts"
```

---

### Task 7: Final integration test + ruff check

**Step 1: Run backend linter**

Run: `cd backend && .venv/Scripts/python -m ruff check .`

Expected: 0 errors (fix any issues)

**Step 2: Run all backend tests**

Run: `cd backend && .venv/Scripts/python -m pytest tests/ -v --tb=short`

Expected: All pass

**Step 3: Run frontend build**

Run: `cd frontend && npm run build`

Expected: 0 errors

**Step 4: Final commit if any fixes needed**

```bash
git commit -m "chore: lint fixes for pipeline analytics"
```
