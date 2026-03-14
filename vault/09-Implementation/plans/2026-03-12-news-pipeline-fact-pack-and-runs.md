# News Pipeline Fact Pack and Pipeline Runs Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add stage-level pipeline observability, a dedicated admin Pipeline Runs UI, structured fact-pack based business generation, and stronger research novelty/no-news handling.

**Architecture:** Extend the existing pipeline with structured stage logging and new content contracts for `fact_pack`, `source_cards`, and `content_analysis`. Keep the current publish flow, but split business generation into shared analysis plus persona-specific insights and surface the new metadata in admin and article detail layouts.

**Tech Stack:** FastAPI, Pydantic v2, Supabase PostgreSQL/JSONB, Astro, Supabase JS

---

### Task 1: Add database contracts

**Files:**
- Create: `supabase/migrations/00016_pipeline_logs_and_fact_pack.sql`
- Modify: `backend/models/common.py`
- Modify: `backend/models/business.py`
- Modify: `backend/models/research.py`

**Step 1: Write failing tests**

- Add backend tests asserting `BusinessPost` accepts `content_analysis`, `fact_pack`, and `source_cards`.
- Add backend tests asserting `ResearchPost` accepts `source_cards`.

**Step 2: Run tests to verify failure**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_fact_pack_models.py -q`

**Step 3: Write minimal implementation**

- Add nullable columns for `news_posts.content_analysis`, `news_posts.fact_pack`, `news_posts.source_cards`.
- Add `pipeline_logs.attempt`, `pipeline_logs.post_type`, `pipeline_logs.locale`, `pipeline_logs.debug_meta`.
- Add `FactPackItem` and `SourceCard` models and wire them into business/research models.

**Step 4: Run tests to verify pass**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_fact_pack_models.py -q`

**Step 5: Commit**

`git commit -m "feat: add fact pack storage contracts"`

### Task 2: Add pipeline logging helpers and research observability

**Files:**
- Modify: `backend/services/pipeline.py`
- Create: `backend/tests/test_pipeline_logging.py`
- Modify: `backend/tests/test_pipeline_research_gate.py`
- Modify: `backend/tests/test_research_retry.py`

**Step 1: Write failing tests**

- Assert stage logs are inserted with `pipeline_type`, `attempt`, `post_type`, `locale`, and `debug_meta`.
- Assert novelty gate emits pass/no-news logs with reason metadata.
- Assert research EN drafts below safe floor trigger expansion before KO translation.

**Step 2: Run tests to verify failure**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_pipeline_logging.py backend/tests/test_pipeline_research_gate.py backend/tests/test_research_retry.py -q`

**Step 3: Write minimal implementation**

- Add helper(s) for stage logging and normalized `last_error`.
- Log collect/rank/generate/translate/save/no-news decisions.
- Add research safe-floor expansion path and novelty gate reason tracking.

**Step 4: Run tests to verify pass**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_pipeline_logging.py backend/tests/test_pipeline_research_gate.py backend/tests/test_research_retry.py -q`

**Step 5: Commit**

`git commit -m "feat: add pipeline stage logging and research safeguards"`

### Task 3: Split business generation into fact pack, analysis, and personas

**Files:**
- Modify: `backend/services/agents/business.py`
- Modify: `backend/services/agents/prompts.py`
- Modify: `backend/services/agents/translate.py`
- Create: `backend/tests/test_business_fact_pack.py`
- Modify: `backend/tests/test_business_retry.py`
- Modify: `backend/tests/test_translation_strategy.py`

**Step 1: Write failing tests**

- Assert business generation returns `fact_pack`, `source_cards`, and `content_analysis`.
- Assert persona generation uses shared analysis inputs and still satisfies length requirements.
- Assert translation handles `content_analysis` and source card metadata.

**Step 2: Run tests to verify failure**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_business_fact_pack.py backend/tests/test_business_retry.py backend/tests/test_translation_strategy.py -q`

**Step 3: Write minimal implementation**

- Split prompts and generation flow into `fact_pack -> analysis -> personas`.
- Persist new fields in EN/KO save paths.
- Keep persona bodies long on first release.

**Step 4: Run tests to verify pass**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_business_fact_pack.py backend/tests/test_business_retry.py backend/tests/test_translation_strategy.py -q`

**Step 5: Commit**

`git commit -m "feat: split business pipeline into fact pack and personas"`

### Task 4: Add admin Pipeline Runs pages

**Files:**
- Modify: `frontend/src/components/admin/AdminSidebar.astro`
- Modify: `frontend/src/pages/admin/index.astro`
- Create: `frontend/src/pages/admin/pipeline-runs/index.astro`
- Create: `frontend/src/pages/admin/pipeline-runs/[runId].astro`
- Modify: `frontend/src/lib/admin/pipelineError.js`
- Create: `frontend/tests/admin-pipeline-runs-structure.test.cjs`

**Step 1: Write failing tests**

- Assert admin sidebar and dashboard link to Pipeline Runs.
- Assert runs list/detail pages exist and include summary, timeline, and raw error areas.

**Step 2: Run tests to verify failure**

Run: `node frontend/tests/admin-pipeline-runs-structure.test.cjs`

**Step 3: Write minimal implementation**

- Add list/detail pages backed by Supabase admin queries.
- Keep dashboard compact with latest-run summary and detail link.
- Surface normalized and raw errors plus stage metrics.

**Step 4: Run tests to verify pass**

Run: `node frontend/tests/admin-pipeline-runs-structure.test.cjs`

**Step 5: Commit**

`git commit -m "feat: add admin pipeline runs pages"`

### Task 5: Add article sources and business fact pack UI

**Files:**
- Modify: `frontend/src/lib/pageData/newsDetailPage.ts`
- Modify: `frontend/src/components/newsprint/NewsprintArticleLayout.astro`
- Create: `frontend/tests/news-fact-pack-structure.test.cjs`

**Step 1: Write failing tests**

- Assert business pages render Fact Pack, Core Analysis, Persona Insights, and Sources accordion.
- Assert research pages render Sources summary and expandable cards.
- Assert inline citation markers render as superscript links.

**Step 2: Run tests to verify failure**

Run: `node frontend/tests/news-fact-pack-structure.test.cjs`

**Step 3: Write minimal implementation**

- Load `fact_pack`, `source_cards`, `content_analysis` from detail queries.
- Add Sources accordion and citation rendering for research/business.
- Keep legacy posts working when new fields are null.

**Step 4: Run tests to verify pass**

Run: `node frontend/tests/news-fact-pack-structure.test.cjs`

**Step 5: Commit**

`git commit -m "feat: render fact pack and sources on news detail pages"`

### Task 6: Final verification

**Files:**
- No new files

**Step 1: Run backend test set**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_fact_pack_models.py backend/tests/test_pipeline_logging.py backend/tests/test_pipeline_research_gate.py backend/tests/test_research_retry.py backend/tests/test_business_fact_pack.py backend/tests/test_business_retry.py backend/tests/test_translation_strategy.py -q`

**Step 2: Run frontend test set**

Run: `node frontend/tests/admin-pipeline-runs-structure.test.cjs`

Run: `node frontend/tests/news-fact-pack-structure.test.cjs`

**Step 3: Run builds**

Run: `cd frontend && npm run build`

**Step 4: Spot-check changed behaviors**

- Pipeline dashboard still triggers runs.
- New Pipeline Runs pages load.
- Business detail page shows fact pack, analysis, personas, and collapsed sources.
- Research detail page shows sources without fact pack.

**Step 5: Commit**

`git commit -m "chore: verify news pipeline observability refactor"`
