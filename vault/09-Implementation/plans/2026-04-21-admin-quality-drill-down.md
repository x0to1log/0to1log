# Admin Quality Drill-Down Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface v11 rubric sub-score evidence + issues + caps in the admin editor so Amy can see WHY a post scored 76 instead of 85 without reading pipeline_logs.

**Architecture:** Two-part change. **Backend**: persist the per-QC-call breakdowns (`expert_breakdown`, `learner_breakdown`, `frontload_breakdown`) that `_check_digest_quality` already computes but currently discards at save time. **Frontend**: new `QualityPanel.astro` component rendered on `/admin/edit/[slug]` that reads `fact_pack` and renders aggregate scores + per-QC-call sub-scores + evidence + issues with progressive disclosure (collapsible categories, color-coded chips). Back-compat for legacy data via shape detection.

**Tech Stack:** FastAPI backend (Python 3.11), Astro v5 frontend, Tailwind v4, Supabase JSONB.

**Spec:** None separate — this plan IS the spec. Derived from NQ-34 in ACTIVE_SPRINT.md + v11 journal's "forward-looking suggestions".

---

## Prerequisite context for implementer

### Current data shape (verified 2026-04-21)

`news_posts.fact_pack` contains after every digest save:
- `quality_score` (int 0-100)
- `quality_version` ("v1")
- `quality_breakdown` — 3-tier aggregate:
  ```json
  {"llm": {"expert_body": 17, "learner_body": 17, "frontload": 19},
   "raw_llm": {"expert_body": 84, "learner_body": 83, "frontload": 96},
   "deterministic": {"structure": 15, "traceability": 12, "locale": 10}}
  ```
- `quality_issues`: `[{severity, scope, category, message}, ...]`
- `quality_caps_applied`: `["major_source_cap_84", "locale_quality_cap_89", ...]`
- `structural_penalty` (int), `structural_warnings` (list)
- `auto_publish_eligible` (bool)
- `url_validation_failed` (bool), `url_validation_failures` (list)

### What's MISSING today (this plan adds)

`_check_digest_quality` in `pipeline_quality.py:539-541` already computes:
- `expert_breakdown` — nested v11 sub-scores from research/business_expert QC (e.g. `{structural_completeness: {sections_present: {evidence, score}, ...}, source_quality: {...}, technical_depth: {...}, language_quality: {...}}`)
- `learner_breakdown` — same shape for learner QC
- `frontload_breakdown` — `{factuality: {...}, calibration: {...}, clarity: {...}, locale_alignment: {...}}`

These are returned from `_check_digest_quality` but **not persisted** — `pipeline_digest.py` save payload doesn't read them. Admin can't see evidence trails.

### Back-compat expectations

- **Apr 20+** posts (v11 rubric era) → will have all 3 breakdowns IF this plan ships
- **Apr 19 and earlier** posts → fact_pack has aggregate `quality_breakdown` but NO per-call `*_breakdown` keys
- UI must render gracefully either way (show a "Legacy post — sub-score evidence not available" note when missing)

### Where it ships

Primary: `/admin/edit/[slug]` editor page. Secondary (out of scope, NQ-34b): `/admin/pipeline-runs/[runId]`.

---

## File Structure

| File | Responsibility | Changes |
|------|----------------|---------|
| `backend/services/pipeline_digest.py` | Daily digest save | Add `expert_breakdown`/`learner_breakdown`/`frontload_breakdown` to fact_pack |
| `backend/services/pipeline.py` | Rerun `from_stage=quality` branch | Same 3 keys when merging into existing fact_pack |
| `backend/tests/test_pipeline_quality_scoring.py` | QC persistence | Assert 3 new keys exist in saved payload |
| `backend/tests/test_pipeline_rerun.py` | Rerun persistence | Assert rerun's fact_pack merge includes breakdowns |
| `frontend/src/lib/admin/qualityPanel.ts` | Normalization helpers | New file — `normalizeQualityData(fact_pack)` returns a typed structure consumable by UI; handles both v10 legacy and v11 shape |
| `frontend/src/components/admin/QualityPanel.astro` | UI component | New file — renders normalized data with collapsible sections + color-coded chips |
| `frontend/src/pages/admin/edit/[slug].astro` | Editor mount | Fetch `fact_pack` (if not already) + mount `<QualityPanel>` in a sidebar/panel slot |

**NOT touching** (out of scope):
- `/admin/pipeline-runs/[runId]` — separate follow-up (NQ-34b if valuable)
- Weekly pipeline save — weekly has its own path + may not need drill-down in same iteration

---

## Chunk 1: Backend persistence

### Task 1: Persist per-QC-call breakdowns in daily digest save

**Files:**
- Modify: `backend/services/pipeline_digest.py` around line 1139-1152 (the `fact_pack` dict in row payload)
- Modify: `backend/tests/test_pipeline_quality_scoring.py` (add assertion)

**Context:** `quality_meta` param (the return value of `_check_digest_quality`) already contains `expert_breakdown`, `learner_breakdown`, `frontload_breakdown` — but the save path ignores them. Add them to the fact_pack dict.

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_pipeline_quality_scoring.py`, find an existing `test_check_digest_quality_*` test that runs QC end-to-end on mocked data. Add a new assertion block verifying the return dict contains the 3 breakdown keys:

```python
def test_check_digest_quality_returns_per_call_breakdowns_for_admin_drill_down():
    """_check_digest_quality must return expert_breakdown/learner_breakdown/
    frontload_breakdown — the nested v11 sub-score evidence structure that
    admin UI renders. These are produced internally (pipeline_quality.py:539-541)
    but tested explicitly here to guard against accidental removal."""
    # Reuse existing test harness pattern. Build a minimal classified group,
    # mock LLM to return v11-shape sub-scores, invoke _check_digest_quality,
    # and assert return shape:
    from services.pipeline_quality import _check_digest_quality
    # ... (use existing test utilities)
    result = await _check_digest_quality(...)

    assert "expert_breakdown" in result
    assert "learner_breakdown" in result
    assert "frontload_breakdown" in result
    # Breakdown shape — each is a nested dict of categories
    for k in ("expert_breakdown", "learner_breakdown", "frontload_breakdown"):
        assert isinstance(result[k], dict)
```

Find exactly one `test_check_digest_quality_*` that mocks the 3 LLM calls (there's one around line 129 `test_check_digest_quality_uses_ko_and_frontload_and_applies_cap`) and study its fixture pattern. Adapt it; don't rebuild from scratch.

- [ ] **Step 2: Run test — expect FAIL**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_pipeline_quality_scoring.py::test_check_digest_quality_returns_per_call_breakdowns_for_admin_drill_down -v
```

Actually — these 3 keys ARE already in `_check_digest_quality`'s return (pipeline_quality.py:539-541 shows that). So this test should PASS immediately, serving as a regression guard. If it fails, that's a real bug to fix.

- [ ] **Step 3: Modify fact_pack save in pipeline_digest.py**

In `backend/services/pipeline_digest.py`, find the `fact_pack` dict construction around line 1139:

```python
# BEFORE:
"fact_pack": {
    **digest_meta,
    "quality_score": quality_score,
    "quality_version": quality_meta.get("quality_version", "v1"),
    "quality_breakdown": quality_meta.get("quality_breakdown", {}),
    "quality_issues": quality_meta.get("quality_issues", []),
    "quality_caps_applied": quality_meta.get("quality_caps_applied", []),
    "structural_penalty": quality_meta.get("structural_penalty", 0),
    "structural_warnings": quality_meta.get("structural_warnings", []),
    "auto_publish_eligible": auto_publish,
    "url_validation_failed": bool(quality_meta.get("url_validation_failed", False)),
    "url_validation_failures": quality_meta.get("url_validation_failures", []),
},
```

Add 3 breakdown keys (from `_check_digest_quality` return, now persisted for admin drill-down):

```python
"fact_pack": {
    **digest_meta,
    "quality_score": quality_score,
    "quality_version": quality_meta.get("quality_version", "v1"),
    "quality_breakdown": quality_meta.get("quality_breakdown", {}),
    # Per-QC-call v11 sub-score breakdowns with evidence — surfaced in admin drill-down.
    # These are large (~1-2KB each for evidence strings) but JSONB storage is cheap;
    # value is the score explainability trail for auto-publish decisions.
    "expert_breakdown": quality_meta.get("expert_breakdown", {}),
    "learner_breakdown": quality_meta.get("learner_breakdown", {}),
    "frontload_breakdown": quality_meta.get("frontload_breakdown", {}),
    "quality_issues": quality_meta.get("quality_issues", []),
    "quality_caps_applied": quality_meta.get("quality_caps_applied", []),
    "structural_penalty": quality_meta.get("structural_penalty", 0),
    "structural_warnings": quality_meta.get("structural_warnings", []),
    "auto_publish_eligible": auto_publish,
    "url_validation_failed": bool(quality_meta.get("url_validation_failed", False)),
    "url_validation_failures": quality_meta.get("url_validation_failures", []),
},
```

- [ ] **Step 4: Run full pipeline test suite**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_pipeline_quality_scoring.py tests/test_pipeline_digest_validation.py -v
```
Expected: all pass. Focus on any test asserting the EXACT shape of fact_pack (these would need breakdown keys added).

- [ ] **Step 5: Ruff**

```
cd backend && .venv/Scripts/python.exe -m ruff check services/pipeline_digest.py
```
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add backend/services/pipeline_digest.py backend/tests/test_pipeline_quality_scoring.py
git commit -m "feat(qc): persist per-QC-call breakdowns to fact_pack for admin drill-down

_check_digest_quality already returns expert_breakdown/learner_breakdown/
frontload_breakdown (pipeline_quality.py:539-541) — the nested v11 sub-score
evidence structure. Daily digest save ignored them. Now included in fact_pack
so admin UI can render evidence trails (NQ-34).

Storage: JSONB, ~3-6KB additional per post (evidence strings). Small vs.
body content size (~10KB). Value: score explainability — admin can see
WHICH sub-score anchor is failing without reading pipeline_logs."
```

---

### Task 2: Persist breakdowns in rerun_from=quality branch

**Files:**
- Modify: `backend/services/pipeline.py` around lines 1855-1888 (the fact_pack merge in rerun quality-only branch added by commit `a2fea9c`)
- Modify: `backend/tests/test_pipeline_rerun.py`

**Context:** Task 1 covers the daily fresh-run path. Rerun path merges QC results into existing fact_pack — must ALSO overlay the 3 breakdowns so rerunning a post refreshes the drill-down data.

- [ ] **Step 1: Update the test first**

In `backend/tests/test_pipeline_rerun.py`, modify `test_rerun_from_quality_skips_digest_generation_and_writes_payload`. Extend the `qc_mock.return_value` to include the 3 breakdowns, then assert they land in `payload["fact_pack"]`:

```python
qc_mock.return_value = {
    "score": 84,
    "quality_score": 84,
    "quality_flags": [],
    "quality_issues": [{"severity": "minor", "scope": "frontload", "message": "ex"}],
    "quality_breakdown": {"total_score": 84, "factuality": {}},
    # NEW: per-QC-call breakdowns (NQ-34)
    "expert_breakdown": {"structural_completeness": {"sections_present": {"evidence": "e1", "score": 10}}},
    "learner_breakdown": {"structural_completeness": {"sections_present": {"evidence": "e2", "score": 9}}},
    "frontload_breakdown": {"factuality": {"number_grounding": {"evidence": "e3", "score": 10}}},
    "quality_version": "v1",
    "quality_caps_applied": [],
    "structural_penalty": 0,
    "structural_warnings": [],
    "url_validation_failed": False,
    "url_validation_failures": [],
}
```

After the existing `fp["quality_breakdown"]` assertion, add:

```python
# Per-call breakdowns for admin drill-down (NQ-34)
assert "expert_breakdown" in fp
assert "learner_breakdown" in fp
assert "frontload_breakdown" in fp
assert fp["expert_breakdown"]["structural_completeness"]["sections_present"]["score"] == 10
```

- [ ] **Step 2: Run — expect FAIL**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_pipeline_rerun.py::test_rerun_from_quality_skips_digest_generation_and_writes_payload -v
```
Expected: FAIL on the `expert_breakdown in fp` assertion.

- [ ] **Step 3: Update pipeline.py rerun branch**

In `backend/services/pipeline.py`, find the `new_fp` dict construction inside the `if from_stage == "quality":` branch (approximately lines 1855-1888 post commit `a2fea9c`). Add 3 breakdown keys to the overlay:

```python
# BEFORE:
new_fp = {
    **existing_fp,
    "quality_score": score_int,
    "quality_version": qc_result.get(
        "quality_version", existing_fp.get("quality_version", "v1"),
    ),
    "quality_breakdown": qc_result.get("quality_breakdown", {}),
    "quality_issues": qc_result.get("quality_issues", []),
    "quality_caps_applied": qc_result.get(...),
    "structural_penalty": qc_result.get(...),
    "structural_warnings": qc_result.get(...),
    "url_validation_failed": bool(qc_result.get(...)),
    "url_validation_failures": qc_result.get(...),
}

# AFTER (add the 3 breakdowns right after quality_breakdown):
new_fp = {
    **existing_fp,
    "quality_score": score_int,
    "quality_version": qc_result.get(
        "quality_version", existing_fp.get("quality_version", "v1"),
    ),
    "quality_breakdown": qc_result.get("quality_breakdown", {}),
    # Per-QC-call v11 sub-score breakdowns (NQ-34 admin drill-down).
    # Rerun MUST overlay these — fresh QC produces new evidence trails.
    "expert_breakdown": qc_result.get(
        "expert_breakdown", existing_fp.get("expert_breakdown", {}),
    ),
    "learner_breakdown": qc_result.get(
        "learner_breakdown", existing_fp.get("learner_breakdown", {}),
    ),
    "frontload_breakdown": qc_result.get(
        "frontload_breakdown", existing_fp.get("frontload_breakdown", {}),
    ),
    "quality_issues": qc_result.get("quality_issues", []),
    "quality_caps_applied": qc_result.get(...),  # unchanged
    "structural_penalty": qc_result.get(...),     # unchanged
    "structural_warnings": qc_result.get(...),    # unchanged
    "url_validation_failed": bool(qc_result.get(...)),  # unchanged
    "url_validation_failures": qc_result.get(...),  # unchanged
}
```

The fallback to `existing_fp.get("expert_breakdown", {})` is important: if the fresh rerun (somehow) doesn't return breakdowns, we preserve the earlier run's snapshot rather than blanking.

- [ ] **Step 4: Run tests**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_pipeline_rerun.py -v
```
Expected: 8 passed (including the updated test).

- [ ] **Step 5: Ruff**

```
cd backend && .venv/Scripts/python.exe -m ruff check services/pipeline.py
```

- [ ] **Step 6: Commit**

```bash
git add backend/services/pipeline.py backend/tests/test_pipeline_rerun.py
git commit -m "feat(rerun): persist per-QC-call breakdowns on quality rerun

Mirrors Task 1 (daily save path) — rerun_from=quality now overlays
expert_breakdown/learner_breakdown/frontload_breakdown into fact_pack,
preserving earlier snapshots when fresh rerun lacks them.

This closes the rerun parity gap: fresh daily runs and quality reruns
both ship the drill-down evidence trail to fact_pack."
```

---

## Chunk 2: Frontend normalization + rendering

### Task 3: Build quality data normalizer (TypeScript)

**Files:**
- Create: `frontend/src/lib/admin/qualityPanel.ts`
- Create: `frontend/tests/qualityPanel.test.ts` (if test infra exists) OR skip tests if Astro project has no test runner set up — verify manually.

**Context:** `fact_pack` shape varies: Apr 19 and earlier lacks breakdowns entirely; Apr 20+ has all 3. Component shouldn't branch on shape at every render site — centralize in a normalizer.

**Step 0 — decide on test infra:**

Check `frontend/package.json` and `frontend/vite.config.*` for vitest/jest setup:

```
cd frontend && cat package.json | grep -E '"test"|vitest|jest'
```

If no test runner — skip Step 1/2 (manual verification via dev server later), write plain TS only. Note outcome in Step 6 commit.

- [ ] **Step 1 (if tests available): Write normalizer tests**

Create `frontend/tests/qualityPanel.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { normalizeQualityData } from '../src/lib/admin/qualityPanel';

describe('normalizeQualityData', () => {
  it('returns null-safe empty shape for null fact_pack', () => {
    const result = normalizeQualityData(null);
    expect(result.isLegacy).toBe(true);
    expect(result.breakdowns).toEqual({ expert: null, learner: null, frontload: null });
    expect(result.issues).toEqual([]);
  });

  it('detects legacy post (no per-call breakdowns)', () => {
    const factPack = {
      quality_score: 75,
      quality_breakdown: {
        llm: { expert_body: 15, learner_body: 20, frontload: 20 },
        raw_llm: { expert_body: 76, learner_body: 100, frontload: 100 },
        deterministic: { structure: 15, traceability: 14, locale: 10 },
      },
      quality_issues: [{ severity: 'minor', scope: 'en', category: 'source', message: 'x' }],
    };
    const result = normalizeQualityData(factPack);
    expect(result.isLegacy).toBe(true);  // no breakdowns = legacy
    expect(result.aggregates.weightedLlm.expert_body).toBe(15);
    expect(result.aggregates.rawLlm.frontload).toBe(100);
    expect(result.aggregates.deterministic.structure).toBe(15);
    expect(result.issues).toHaveLength(1);
  });

  it('detects v11 post (per-call breakdowns present)', () => {
    const factPack = {
      quality_score: 88,
      quality_breakdown: {
        llm: { expert_body: 18, learner_body: 18, frontload: 20 },
        raw_llm: { expert_body: 90, learner_body: 90, frontload: 100 },
        deterministic: { structure: 15, traceability: 14, locale: 10 },
      },
      expert_breakdown: {
        structural_completeness: {
          sections_present: { evidence: 'All 5 sections present', score: 10 },
          section_depth: { evidence: 'Long coverage', score: 9 },
        },
        source_quality: {
          citation_coverage: { evidence: 'Every paragraph cited', score: 10 },
          primary_source_priority: { evidence: 'OpenAI first, techcrunch second', score: 9 },
          source_utilization: { evidence: 'Used 8/10 sources', score: 8 },
        },
      },
      learner_breakdown: { /* similar */ },
      frontload_breakdown: {
        factuality: { number_grounding: { evidence: '$510M matches body', score: 10 } },
      },
      quality_issues: [],
      quality_caps_applied: ['major_source_cap_84'],
    };
    const result = normalizeQualityData(factPack);
    expect(result.isLegacy).toBe(false);
    expect(result.breakdowns.expert).not.toBeNull();
    expect(result.breakdowns.expert!.structural_completeness.sections_present.score).toBe(10);
    expect(result.capsApplied).toContain('major_source_cap_84');
  });

  it('clamps malformed scores to [0, 10]', () => {
    const factPack = {
      expert_breakdown: {
        structural_completeness: {
          sections_present: { evidence: 'x', score: 15 },  // malformed > 10
          section_depth: { evidence: 'y', score: -3 },     // malformed < 0
        },
      },
    };
    const result = normalizeQualityData(factPack);
    const sp = result.breakdowns.expert!.structural_completeness.sections_present;
    const sd = result.breakdowns.expert!.structural_completeness.section_depth;
    expect(sp.score).toBe(10);
    expect(sd.score).toBe(0);
  });
});
```

- [ ] **Step 2 (if tests available): Run — expect FAIL**

```
cd frontend && npm test -- qualityPanel
```

- [ ] **Step 3: Implement the normalizer**

Create `frontend/src/lib/admin/qualityPanel.ts`:

```typescript
/**
 * Normalize fact_pack from news_posts row into a shape the QualityPanel UI
 * can render without branching at each element. Handles two data eras:
 *   - legacy (v10, Apr 19 and earlier): aggregate scores only, no per-call breakdowns
 *   - v11 (Apr 20+): aggregate + 3 per-QC-call sub-score breakdowns with evidence
 */

export interface SubScore {
  evidence: string;
  score: number;  // 0-10, clamped
}

export type SubScoreCategory = Record<string, SubScore>;  // e.g. {sections_present: {...}, section_depth: {...}}
export type Breakdown = Record<string, SubScoreCategory>;  // e.g. {structural_completeness: {...}, source_quality: {...}}

export interface QualityIssue {
  severity: 'major' | 'minor';
  scope: string;    // expert_body | learner_body | frontload | ko | en
  category: string; // source | locale | structure | clarity | overclaim | ...
  message: string;
}

export interface NormalizedQuality {
  score: number | null;              // aggregate 0-100
  autoPublishEligible: boolean;
  isLegacy: boolean;                 // true = no per-call breakdowns
  aggregates: {
    weightedLlm: { expert_body: number; learner_body: number; frontload: number };
    rawLlm:      { expert_body: number; learner_body: number; frontload: number };
    deterministic: { structure: number; traceability: number; locale: number };
  };
  breakdowns: {
    expert: Breakdown | null;
    learner: Breakdown | null;
    frontload: Breakdown | null;
  };
  issues: QualityIssue[];
  capsApplied: string[];
  structuralPenalty: number;
  structuralWarnings: string[];
  urlValidationFailed: boolean;
  urlValidationFailures: unknown[];
}

const ZERO_AGG = { expert_body: 0, learner_body: 0, frontload: 0 };
const ZERO_DET = { structure: 0, traceability: 0, locale: 0 };

function clampSubScore(raw: unknown): SubScore {
  if (!raw || typeof raw !== 'object') return { evidence: '', score: 0 };
  const obj = raw as Record<string, unknown>;
  const evidence = typeof obj.evidence === 'string' ? obj.evidence : '';
  const rawScore = typeof obj.score === 'number' ? obj.score : 0;
  const score = Math.max(0, Math.min(10, Math.round(rawScore)));
  return { evidence, score };
}

function normalizeBreakdown(raw: unknown): Breakdown | null {
  if (!raw || typeof raw !== 'object') return null;
  const obj = raw as Record<string, unknown>;
  // Empty object = breakdown not available (treat as null)
  if (Object.keys(obj).length === 0) return null;
  const out: Breakdown = {};
  for (const [categoryKey, categoryVal] of Object.entries(obj)) {
    if (!categoryVal || typeof categoryVal !== 'object') continue;
    const subs: SubScoreCategory = {};
    for (const [subKey, subVal] of Object.entries(categoryVal as Record<string, unknown>)) {
      subs[subKey] = clampSubScore(subVal);
    }
    if (Object.keys(subs).length > 0) out[categoryKey] = subs;
  }
  return Object.keys(out).length > 0 ? out : null;
}

function normalizeIssues(raw: unknown): QualityIssue[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((x): x is Record<string, unknown> => !!x && typeof x === 'object')
    .map((x) => ({
      severity: x.severity === 'major' ? 'major' : 'minor',
      scope: typeof x.scope === 'string' ? x.scope : '',
      category: typeof x.category === 'string' ? x.category : '',
      message: typeof x.message === 'string' ? x.message : '',
    }));
}

export function normalizeQualityData(factPack: unknown): NormalizedQuality {
  const fp = (factPack && typeof factPack === 'object') ? factPack as Record<string, unknown> : {};

  const qb = (fp.quality_breakdown && typeof fp.quality_breakdown === 'object')
    ? fp.quality_breakdown as Record<string, Record<string, number>>
    : {};

  const expert   = normalizeBreakdown(fp.expert_breakdown);
  const learner  = normalizeBreakdown(fp.learner_breakdown);
  const frontload = normalizeBreakdown(fp.frontload_breakdown);

  const isLegacy = expert === null && learner === null && frontload === null;

  return {
    score: typeof fp.quality_score === 'number' ? fp.quality_score : null,
    autoPublishEligible: fp.auto_publish_eligible === true,
    isLegacy,
    aggregates: {
      weightedLlm:   { ...ZERO_AGG, ...(qb.llm || {}) },
      rawLlm:        { ...ZERO_AGG, ...(qb.raw_llm || {}) },
      deterministic: { ...ZERO_DET, ...(qb.deterministic || {}) },
    },
    breakdowns: { expert, learner, frontload },
    issues: normalizeIssues(fp.quality_issues),
    capsApplied: Array.isArray(fp.quality_caps_applied) ? fp.quality_caps_applied as string[] : [],
    structuralPenalty: typeof fp.structural_penalty === 'number' ? fp.structural_penalty : 0,
    structuralWarnings: Array.isArray(fp.structural_warnings) ? fp.structural_warnings as string[] : [],
    urlValidationFailed: fp.url_validation_failed === true,
    urlValidationFailures: Array.isArray(fp.url_validation_failures) ? fp.url_validation_failures : [],
  };
}

/** Tailwind color class for a 0-10 sub-score (used by QualityPanel). */
export function scoreColorClass(score: number): string {
  if (score >= 8) return 'text-green-600 bg-green-50';
  if (score >= 4) return 'text-yellow-600 bg-yellow-50';
  return 'text-red-600 bg-red-50';
}

/** Human label for severity. */
export function severityLabel(s: 'major' | 'minor'): { label: string; className: string } {
  return s === 'major'
    ? { label: 'Major', className: 'bg-red-100 text-red-800' }
    : { label: 'Minor', className: 'bg-yellow-100 text-yellow-800' };
}
```

- [ ] **Step 4 (if tests available): Run — expect PASS**

```
cd frontend && npm test -- qualityPanel
```
Expected: 4 passed.

- [ ] **Step 5: Build check**

```
cd frontend && npm run build
```
Expected: no TS errors from the new file.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/admin/qualityPanel.ts
# If tests ran: also `git add frontend/tests/qualityPanel.test.ts`
git commit -m "feat(admin): add qualityPanel normalizer for fact_pack → NormalizedQuality

Centralizes fact_pack parsing for admin drill-down UI: clamps malformed
sub-scores, detects legacy (v10, no per-call breakdowns) vs v11 posts,
produces a typed NormalizedQuality the QualityPanel component can render
without branching at every element.

scoreColorClass + severityLabel exported for UI consistency."
```

---

### Task 4: Build QualityPanel Astro component

**Files:**
- Create: `frontend/src/components/admin/QualityPanel.astro`

**Context:** Stateless Astro component that accepts `fact_pack` prop and renders a structured quality panel. Collapsible sections via native `<details>` (no JS framework needed). Tailwind styling.

- [ ] **Step 1: Implement the component**

Create `frontend/src/components/admin/QualityPanel.astro`:

```astro
---
import {
  normalizeQualityData,
  scoreColorClass,
  severityLabel,
  type NormalizedQuality,
} from '../../lib/admin/qualityPanel';

interface Props {
  factPack: unknown;
}

const { factPack } = Astro.props;
const q: NormalizedQuality = normalizeQualityData(factPack);

const aggregateChips = [
  { label: 'Structure', value: q.aggregates.deterministic.structure, max: 15 },
  { label: 'Traceability', value: q.aggregates.deterministic.traceability, max: 15 },
  { label: 'Locale', value: q.aggregates.deterministic.locale, max: 10 },
  { label: 'Expert Body (wt)', value: q.aggregates.weightedLlm.expert_body, max: 24 },
  { label: 'Learner Body (wt)', value: q.aggregates.weightedLlm.learner_body, max: 24 },
  { label: 'Frontload (wt)', value: q.aggregates.weightedLlm.frontload, max: 12 },
];

const issuesByScope = q.issues.reduce<Record<string, typeof q.issues>>((acc, issue) => {
  const key = issue.scope || 'unknown';
  (acc[key] ||= []).push(issue);
  return acc;
}, {});

const majorIssues = q.issues.filter((i) => i.severity === 'major');
const minorIssues = q.issues.filter((i) => i.severity === 'minor');
---

<section class="quality-panel rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
  <header class="quality-panel__header flex items-baseline justify-between gap-4 border-b border-gray-100 pb-3">
    <div>
      <h3 class="text-lg font-semibold text-gray-900">Quality Analysis</h3>
      <p class="text-xs text-gray-500">
        {q.isLegacy
          ? 'Legacy post (pre-v11 rubric) — aggregate scores only, sub-score evidence not available'
          : 'v11 rubric — click a category below to see sub-score evidence'}
      </p>
    </div>
    <div class="flex items-center gap-2">
      {q.score !== null && (
        <span class={`rounded px-3 py-1 text-lg font-bold ${q.score >= 85 ? 'bg-green-100 text-green-800' : q.score >= 70 ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'}`}>
          {q.score}/100
        </span>
      )}
      {q.autoPublishEligible && (
        <span class="rounded bg-green-50 px-2 py-1 text-xs font-medium text-green-700 ring-1 ring-green-200">
          Auto-publish eligible
        </span>
      )}
    </div>
  </header>

  {/* Aggregate chips */}
  <div class="quality-panel__aggregates mt-3 flex flex-wrap gap-2">
    {aggregateChips.map((chip) => (
      <span class="rounded bg-gray-50 px-2 py-1 text-xs ring-1 ring-gray-200">
        <span class="text-gray-500">{chip.label}:</span>{' '}
        <span class="font-medium text-gray-900">{chip.value}/{chip.max}</span>
      </span>
    ))}
  </div>

  {/* Caps + structural warnings */}
  {(q.capsApplied.length > 0 || q.structuralPenalty > 0 || q.urlValidationFailed) && (
    <div class="quality-panel__caps mt-3 space-y-1 text-xs">
      {q.capsApplied.map((cap) => (
        <p class="text-orange-700">🧢 Cap applied: <code class="rounded bg-orange-50 px-1">{cap}</code></p>
      ))}
      {q.structuralPenalty > 0 && (
        <p class="text-red-700">🔻 Structural penalty: {q.structuralPenalty}
          {q.structuralWarnings.length > 0 && ` — ${q.structuralWarnings.join('; ')}`}
        </p>
      )}
      {q.urlValidationFailed && (
        <p class="text-red-700">🔗 URL validation failed (auto-publish blocked)</p>
      )}
    </div>
  )}

  {/* Per-call breakdowns */}
  {!q.isLegacy && (
    <div class="quality-panel__breakdowns mt-4 space-y-2">
      {(['expert', 'learner', 'frontload'] as const).map((persona) => {
        const breakdown = q.breakdowns[personaToKey(persona)];
        if (!breakdown) return null;
        return (
          <details class="quality-panel__breakdown rounded border border-gray-100 bg-gray-50">
            <summary class="cursor-pointer px-3 py-2 text-sm font-medium text-gray-900 hover:bg-gray-100">
              {persona === 'expert' ? 'Expert Body' : persona === 'learner' ? 'Learner Body' : 'Frontload'}
            </summary>
            <div class="px-3 pb-3">
              {Object.entries(breakdown).map(([category, subs]) => (
                <div class="mt-2">
                  <h4 class="text-xs font-semibold uppercase tracking-wide text-gray-600">
                    {category.replace(/_/g, ' ')}
                  </h4>
                  <ul class="mt-1 space-y-1">
                    {Object.entries(subs).map(([subKey, sub]) => (
                      <li class="flex items-start gap-2 text-xs">
                        <span class={`inline-block min-w-[3rem] rounded px-1.5 py-0.5 text-center font-mono font-medium ${scoreColorClass(sub.score)}`}>
                          {sub.score}/10
                        </span>
                        <div class="flex-1">
                          <span class="font-medium text-gray-800">{subKey.replace(/_/g, ' ')}</span>
                          {sub.evidence && (
                            <p class="mt-0.5 text-gray-600">{sub.evidence}</p>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </details>
        );
      })}
    </div>
  )}

  {/* Issues */}
  {q.issues.length > 0 && (
    <div class="quality-panel__issues mt-4 border-t border-gray-100 pt-3">
      <h4 class="text-sm font-semibold text-gray-900">
        Issues ({majorIssues.length} major, {minorIssues.length} minor)
      </h4>
      <ul class="mt-2 space-y-1 text-xs">
        {q.issues.map((issue) => {
          const { label, className } = severityLabel(issue.severity);
          return (
            <li class="flex items-start gap-2">
              <span class={`inline-block rounded px-1.5 py-0.5 text-center font-medium ${className}`}>
                {label}
              </span>
              <div class="flex-1">
                <p>
                  <span class="font-mono text-gray-500">[{issue.scope || '?'}/{issue.category || '?'}]</span>{' '}
                  <span class="text-gray-800">{issue.message}</span>
                </p>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  )}
</section>

<script>
  // Helper: map persona label to breakdowns key
  function personaToKey(persona: 'expert' | 'learner' | 'frontload'): 'expert' | 'learner' | 'frontload' {
    return persona;  // identity — separate function keeps type narrowing clean in the Astro frontmatter
  }
</script>
```

**Note**: Astro frontmatter can't call functions defined in `<script>` tags. The `personaToKey()` in the `.map()` above should just be inline string (`persona` IS the key already). Fix during implementation:

```astro
{(['expert', 'learner', 'frontload'] as const).map((persona) => {
  const breakdown = q.breakdowns[persona];  // direct — same key
  // ...
})}
```

Remove the script block — not needed.

- [ ] **Step 2: Build check**

```
cd frontend && npm run build
```
Expected: no TS errors, no astro errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/admin/QualityPanel.astro
git commit -m "feat(admin): QualityPanel component — fact_pack drill-down UI

Collapsible per-QC-call breakdowns (expert/learner/frontload) with
color-coded sub-score chips (green ≥8, yellow 4-7, red <4), evidence
strings inline, issues grouped by severity, aggregate chips for
deterministic + weighted LLM scores.

Degrades gracefully for legacy posts (pre-v11 rubric) — renders
aggregates + issues only, notes 'sub-score evidence not available'."
```

---

### Task 5: Mount QualityPanel on admin editor page

**Files:**
- Modify: `frontend/src/pages/admin/edit/[slug].astro`

**Context:** The editor page already fetches the post row. Need to ensure `fact_pack` is in the selected columns, then mount `<QualityPanel factPack={post.fact_pack} />` in a visible slot.

- [ ] **Step 1: Ensure fact_pack is selected**

Open `frontend/src/pages/admin/edit/[slug].astro`. Find the Supabase query that fetches the post row (look for `.select(` targeting `news_posts`). Verify `fact_pack` is either explicitly listed OR the query uses `.select('*')`. If missing, add `fact_pack` to the column list.

- [ ] **Step 2: Import and mount the component**

At the top of the frontmatter (after existing imports):

```astro
import QualityPanel from '../../../components/admin/QualityPanel.astro';
```

Then in the template body, find a reasonable slot — ideally below the existing quality_score badge/display, or in a sidebar. Add:

```astro
<QualityPanel factPack={post.fact_pack} />
```

If there's no obvious sidebar, place it above or below the content editor, wrapped in whatever section container the page uses for secondary panels.

- [ ] **Step 3: Build check**

```
cd frontend && npm run build
```
Expected: build succeeds, no type errors.

- [ ] **Step 4: Manual visual verification**

```
cd frontend && npm run dev
```

Open in browser:
1. `/admin/edit/2026-04-21-research-digest` (v11-era post) — expect: full panel with aggregate chips, 3 collapsible persona breakdowns (empty since Apr 21 ran BEFORE Task 1 deploy), issues list.
2. `/admin/edit/2026-04-19-research-digest` (legacy post) — expect: "Legacy post" banner, aggregate chips, issues list, NO collapsible breakdowns.

Actually — until Task 1 ships to production and runs once, ALL existing rows will render as legacy. That's expected.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/admin/edit/[slug].astro
git commit -m "feat(admin): mount QualityPanel on editor page

Surfaces fact_pack quality drill-down in /admin/edit/[slug] so admin can
see sub-score evidence + issues + caps inline during review. Legacy posts
(pre-v11 rubric) show aggregates + 'no sub-score evidence' banner."
```

---

## Chunk 3: Validation

### Task 6: E2E smoke test on Apr 22 fresh run + Apr 19 legacy

**Files:** none (manual validation)

- [ ] **Step 1: Push Tasks 1-5 to main**

```bash
git push origin main
```

Wait for Railway deploy (~2-3 min) + Vercel deploy (~1-2 min).

- [ ] **Step 2: Trigger a fresh daily cron OR rerun existing batch**

Two options:
- Wait for Apr 22 00:33 UTC auto cron (~2-3 min window)
- OR trigger `rerun_from=quality` on Apr 21 via admin UI ("Quality only: Both")

Option B is faster — lets you verify the rerun path (Task 2) stores breakdowns in the same run.

- [ ] **Step 3: Query fact_pack to confirm breakdowns present**

```
cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "
import os, json
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client
sb = create_client(os.environ['SUPABASE_URL'], os.environ.get('SUPABASE_SERVICE_KEY') or os.environ.get('SUPABASE_KEY'))

for slug in ['2026-04-22-research-digest', '2026-04-21-research-digest']:
    r = sb.table('news_posts').select('fact_pack').eq('slug', slug).single().execute().data
    fp = r.get('fact_pack') or {}
    has_expert = bool(fp.get('expert_breakdown'))
    has_learner = bool(fp.get('learner_breakdown'))
    has_frontload = bool(fp.get('frontload_breakdown'))
    print(f'{slug}: expert={has_expert}, learner={has_learner}, frontload={has_frontload}')
"
```
Expected:
- Fresh v11 run: `expert=True, learner=True, frontload=True`
- Apr 19 (untouched): all False (legacy)

- [ ] **Step 4: Visual check on production admin**

Open 2-3 admin editor pages:
- Fresh post → collapsible breakdowns open, evidence visible, colors correct
- Legacy post → graceful banner, no breakdowns section rendered

- [ ] **Step 5: Confirm no regression**

Spot-check:
- Existing post editing (title, content) still works
- No console errors in browser devtools
- Other admin pages (/admin, /admin/pipeline-runs) still render

- [ ] **Step 6: Done**

No separate commit needed unless Step 4/5 reveals an issue (fix + commit normally).

---

## Done criteria (full plan)

- [ ] `fact_pack` has `expert_breakdown`/`learner_breakdown`/`frontload_breakdown` on fresh runs (Task 1).
- [ ] `rerun_from=quality` overlays the 3 breakdowns (Task 2).
- [ ] Frontend normalizer handles v10 + v11 + malformed shapes; typed exports (Task 3).
- [ ] `<QualityPanel>` Astro component renders aggregates, breakdowns, issues, caps (Task 4).
- [ ] Admin editor page mounts the panel (Task 5).
- [ ] `pytest tests/` clean — new assertions pass, no regressions.
- [ ] `npm run build` clean on frontend.
- [ ] Visual check: v11 post shows collapsible drill-down with evidence; legacy post shows aggregates + banner.

---

## Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| fact_pack grows 3-6KB per post → DB size concern | JSONB is cheap; 3-6KB × 400 posts/year × 2 locales = ~5MB/year. Negligible. |
| Existing tests assert exact fact_pack shape and break | Tests that check `{k1, k2, ...} == set(fact_pack.keys())` would fail. Search for such assertions in Step 3 of Task 1; widen to `<=` if found. |
| Astro component TypeScript errors on build | Keep component types loose (`unknown` for factPack prop); all parsing in normalizer which has strict types. |
| Legacy posts look "broken" in UI | Explicit "Legacy post" banner + conditional rendering. |
| Manual QA catches UI spacing/colors off | Iterate in Step 4 of Task 5; small component = fast rebuild. |

## Post-ship (NQ-34b follow-up, not this plan)

- `/admin/pipeline-runs/[runId]` — per-post breakdown in stage view
- Trend view: compare score/issues across batches (weekly chart)
- Issue filters: "show me all posts with `major/frontload/locale` issues this month"
