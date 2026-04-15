# Phase 1 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** pipeline.py 4-파일 분리 + 하드코딩 도메인 리스트 → Supabase 테이블 이관. Phase 2/3가 안전하게 들어갈 수 있는 기반 마련.

**Architecture:** 외부 import 호환성을 위해 `pipeline.py`는 새 모듈들에서 re-export하는 shim 역할을 유지한다 (routers/cron.py + 6개 테스트 파일이 `from services.pipeline import ...`를 직접 사용 중). 도메인 필터는 모듈 로드 시 1회 fetch 후 메모리 캐시.

**Tech Stack:** Python 3.11 / FastAPI / Supabase / pytest / ruff

**Spec reference:** [2026-04-15-news-pipeline-hardening-design.md](2026-04-15-news-pipeline-hardening-design.md) §4 (Phase 1)

---

## Critical Constraints (read before starting)

1. **외부 import 호환성 유지** — 다음 import는 절대 깨지면 안 됨:
   - `routers/cron.py:14` — `check_existing_batch, cleanup_existing_batch, promote_drafts, rerun_pipeline_stage, run_daily_pipeline, run_handbook_extraction`
   - `routers/cron.py:200` — `run_weekly_pipeline`
   - `tests/test_pipeline.py` — `run_daily_pipeline`, `_extract_and_create_handbook_terms`
   - `tests/test_pipeline_digest_validation.py` — `_find_digest_blockers`, `_check_structural_penalties`, `_generate_digest`
   - `tests/test_pipeline_quality_scoring.py` — `_normalize_scope`, `_apply_issue_penalties_and_caps`, `_extract_structured_issues`, `_check_digest_quality`
   - `tests/test_pipeline_rerun.py` — `rerun_pipeline_stage`

   **해결책**: pipeline.py가 새 모듈에서 re-export. 예: `from services.pipeline_quality import _check_digest_quality, _normalize_scope`. 외부 코드는 변경 0줄.

2. **TDD 안전 게이트** — 모든 함수 이동 작업의 패턴:
   - Step A: `pytest backend/tests/ -v` 전체 통과 확인 (baseline green)
   - Step B: 함수 이동 + import 업데이트
   - Step C: `pytest backend/tests/ -v` 다시 전체 통과 확인 (regression none)
   - Step D: commit

3. **import cycle 회피** — 추출 순서를 바닥부터 위로:
   1. `pipeline_persistence.py` 먼저 (다른 모듈에 의존성 없음)
   2. `pipeline_quality.py` (persistence를 import할 수도)
   3. `pipeline_digest.py` (quality를 import)
   4. `pipeline.py` orchestrator는 셋 다 import

4. **Branch policy** — CLAUDE.md대로 main 브랜치에 직접 작업, 작은 commit으로 자주 push.

---

## File Structure (target after Phase 1)

```
backend/services/
├── pipeline.py                  # ~1500 lines — orchestrator (run_daily, run_weekly, rerun, handbook_extraction)
│                                #   + general utilities + re-exports for backward compat
├── pipeline_digest.py           # ~900 lines — _generate_digest + content cleaners
├── pipeline_quality.py          # ~900 lines — _check_digest_quality + score normalizers + blockers
├── pipeline_persistence.py      # ~400 lines — promote_drafts, _send_draft_alert, _notify_auto_publish,
│                                #              week fetchers, weekly email
└── news_collection.py           # ~1500 lines (unchanged structure, but domain lists removed)
```

**참고**: spec의 "≤500줄" 이상치보다 pipeline.py가 큽니다. 이유는 `run_daily_pipeline`(423줄), `rerun_pipeline_stage`(309줄), `run_weekly_pipeline`(309줄) 등 entry-point 함수 자체가 큽니다. 이걸 더 쪼개려면 Phase 1 범위를 넘어가므로 다음 phase 또는 다음 spec으로 미룹니다.

---

## Chunk 1: Domain Filters Migration (워밍업 — 가장 작은 단위 먼저)

가장 작고 독립적이므로 먼저 해서 작업 흐름에 익숙해진다. 큰 리팩토링 들어가기 전 베이스라인 확인.

### Task 1: Baseline 테스트 통과 확인

**Files:** None (verification only)

- [ ] **Step 1.1: 현재 상태 git status 확인**

```bash
cd c:/Users/amy/Desktop/0to1log
git status
```
Expected: `working tree clean` 또는 알려진 변경사항만 있음

- [ ] **Step 1.2: 백엔드 테스트 baseline 실행**

```bash
cd backend && source .venv/Scripts/activate && pytest tests/ -v --tb=short 2>&1 | tail -50
```
Expected: 전체 PASS (또는 기존에 알려진 skip만). **fail이 있으면 Phase 1 시작 금지** — 먼저 그 문제 해결.

- [ ] **Step 1.3: ruff lint baseline**

```bash
cd backend && ruff check . 2>&1 | tail -20
```
Expected: clean 또는 기존에 알려진 warning만

---

### Task 2: Supabase 마이그레이션 작성

**Files:**
- Create: `supabase/migrations/00050_news_domain_filters.sql`

- [ ] **Step 2.1: 마이그레이션 파일 작성**

다음 내용으로 새 파일 생성:

```sql
-- 00050_news_domain_filters.sql
-- Replace hardcoded domain lists in backend/services/news_collection.py
-- (Phase 1 of news-pipeline-hardening, 2026-04-15)

create table if not exists public.news_domain_filters (
  domain text primary key,
  filter_type text not null check (filter_type in ('block_non_en', 'official_priority', 'media_tier')),
  notes text,
  created_at timestamptz default now()
);

-- RLS: read-only public, write via service role only
alter table public.news_domain_filters enable row level security;

create policy "news_domain_filters_read_all"
  on public.news_domain_filters
  for select
  using (true);

-- Seed data — current hardcoded values from news_collection.py L18-73
insert into public.news_domain_filters (domain, filter_type, notes) values
  -- _NON_EN_DOMAINS (L18-22)
  ('landiannews.com', 'block_non_en', 'Chinese tech news aggregator'),
  ('36kr.com', 'block_non_en', 'Chinese tech media'),
  ('unifuncs.com', 'block_non_en', 'Chinese aggregator'),
  ('minimaxi.com', 'block_non_en', 'Chinese AI company blog'),
  ('ithome.com', 'block_non_en', 'Chinese tech news'),
  ('oschina.net', 'block_non_en', 'Chinese open source community'),
  ('csdn.net', 'block_non_en', 'Chinese developer community'),
  ('juejin.cn', 'block_non_en', 'Chinese developer community'),
  ('zhihu.com', 'block_non_en', 'Chinese Q&A site'),
  ('bilibili.com', 'block_non_en', 'Chinese video platform'),
  ('baidu.com', 'block_non_en', 'Chinese search engine'),
  ('idctop.com', 'block_non_en', 'Chinese hosting news'),

  -- _OFFICIAL_SITE_DOMAINS (L52-61)
  ('openai.com', 'official_priority', 'OpenAI official'),
  ('anthropic.com', 'official_priority', 'Anthropic official'),
  ('techcommunity.microsoft.com', 'official_priority', 'Microsoft tech community'),
  ('blog.google', 'official_priority', 'Google blog'),
  ('blogs.nvidia.com', 'official_priority', 'NVIDIA blog'),
  ('developer.nvidia.com', 'official_priority', 'NVIDIA developer'),
  ('blog.cloudflare.com', 'official_priority', 'Cloudflare blog'),
  ('developer.apple.com', 'official_priority', 'Apple developer'),

  -- _MEDIA_DOMAINS (L63-73)
  ('venturebeat.com', 'media_tier', 'tech media'),
  ('techcrunch.com', 'media_tier', 'tech media'),
  ('theverge.com', 'media_tier', 'tech media'),
  ('yahoo.com', 'media_tier', 'general media'),
  ('reuters.com', 'media_tier', 'wire service'),
  ('bloomberg.com', 'media_tier', 'business media'),
  ('wsj.com', 'media_tier', 'business media'),
  ('ft.com', 'media_tier', 'business media'),
  ('wired.com', 'media_tier', 'tech media')
on conflict (domain) do nothing;
```

- [ ] **Step 2.2: 마이그레이션 적용 (Supabase)**

Supabase MCP 또는 SQL editor에서 적용:
```bash
# Option A: Supabase CLI (if available locally)
supabase db push

# Option B: SQL editor에서 위 SQL 직접 실행
```

검증:
```sql
select filter_type, count(*) from public.news_domain_filters group by filter_type;
```
Expected: `block_non_en: 12`, `official_priority: 8`, `media_tier: 9`

- [ ] **Step 2.3: Commit migration**

```bash
git add supabase/migrations/00050_news_domain_filters.sql
git commit -m "feat(db): add news_domain_filters table for runtime-configurable domain rules"
```

---

### Task 3: Domain filter loader 작성

**Files:**
- Modify: `backend/services/news_collection.py` (top of file, after imports)
- Test: `backend/tests/test_news_collection.py` (add new test)

- [ ] **Step 3.1: 실패하는 테스트 먼저 작성**

[backend/tests/test_news_collection.py](backend/tests/test_news_collection.py) 끝에 추가:

```python
def test_load_domain_filters_returns_three_categories():
    """domain filter loader가 3개 카테고리로 분류된 set을 반환한다."""
    from services.news_collection import _load_domain_filters

    filters = _load_domain_filters()
    assert "block_non_en" in filters
    assert "official_priority" in filters
    assert "media_tier" in filters
    assert isinstance(filters["block_non_en"], frozenset)
    # Sanity: 시드 데이터가 들어 있어야 함
    assert "openai.com" in filters["official_priority"]
    assert "36kr.com" in filters["block_non_en"]
```

- [ ] **Step 3.2: 테스트 실행 — fail 확인**

```bash
cd backend && pytest tests/test_news_collection.py::test_load_domain_filters_returns_three_categories -v
```
Expected: FAIL with `ImportError: cannot import name '_load_domain_filters'`

- [ ] **Step 3.3: Loader 구현**

**먼저 import 경로 확인** (1초):
```bash
cd backend && grep -n "from core" services/news_collection.py | head -3
```
`from core.config` 패턴이 보이면 `from core.database import get_supabase_client` 사용 가능. 만약 `from backend.core...` 패턴이면 그쪽으로. 이 프로젝트는 backend 디렉토리가 Python path 루트라 `from core...`가 표준.

[backend/services/news_collection.py](backend/services/news_collection.py)의 hardcoded `_NON_EN_DOMAINS = (...)` 바로 위 (line 18 직전)에 추가:

```python
from functools import lru_cache
from core.database import get_supabase_client


@lru_cache(maxsize=1)
def _load_domain_filters() -> dict[str, frozenset[str]]:
    """Load domain filter lists from Supabase news_domain_filters table.

    Cached for the lifetime of the process — restart Railway to refresh.
    Returns dict with keys: block_non_en, official_priority, media_tier.
    Falls back to empty sets if DB is unreachable (logs error).
    """
    result = {
        "block_non_en": frozenset(),
        "official_priority": frozenset(),
        "media_tier": frozenset(),
    }
    try:
        supabase = get_supabase_client()
        rows = supabase.table("news_domain_filters").select("domain, filter_type").execute()
        if not rows.data:
            logger.error("news_domain_filters table is empty — falling back to empty filters")
            return result
        buckets: dict[str, set[str]] = {k: set() for k in result}
        for row in rows.data:
            ftype = row.get("filter_type")
            domain = row.get("domain")
            if ftype in buckets and domain:
                buckets[ftype].add(domain.lower())
        return {k: frozenset(v) for k, v in buckets.items()}
    except Exception as e:
        logger.error("Failed to load news_domain_filters from DB: %s — falling back to empty", e)
        return result
```

- [ ] **Step 3.4: 테스트 재실행 — pass 확인**

```bash
cd backend && pytest tests/test_news_collection.py::test_load_domain_filters_returns_three_categories -v
```
Expected: **PASS locally with SUPABASE_URL set in .env; SKIP (or assertion subset fail) in CI without DB access.** CI에서 fail이 나면 Step 3.4 끝의 skipif 패턴 적용.

**참고**: 이 테스트는 실제 Supabase 연결을 시도합니다. CI에서 환경변수가 없으면 fallback 경로로 빈 set을 반환하므로 assertion 일부가 실패할 수 있습니다. 그 경우 테스트를 모킹 버전으로 수정하거나, `@pytest.mark.skipif` 추가:

```python
@pytest.mark.skipif(
    not os.getenv("SUPABASE_URL"),
    reason="Requires live Supabase connection"
)
def test_load_domain_filters_returns_three_categories():
    ...
```

- [ ] **Step 3.5: Commit loader**

```bash
git add backend/services/news_collection.py backend/tests/test_news_collection.py
git commit -m "feat(news): add Supabase-backed domain filter loader with process-level cache"
```

---

### Task 4: Hardcoded 리스트 → loader 호출로 교체

**Files:**
- Modify: `backend/services/news_collection.py:18-73` (replace hardcoded tuples)

- [ ] **Step 4.1: Hardcoded 정의 제거**

[news_collection.py:18-22](backend/services/news_collection.py) (`_NON_EN_DOMAINS`), [L52-61](backend/services/news_collection.py) (`_OFFICIAL_SITE_DOMAINS`), [L63-73](backend/services/news_collection.py) (`_MEDIA_DOMAINS`)을 다음으로 교체:

```python
# Domain filter lists are now loaded from Supabase via _load_domain_filters().
# See migration 00050_news_domain_filters.sql for schema and seed data.
# To modify: update the table directly, then restart Railway to refresh the cache.
```

- [ ] **Step 4.2: 사용처를 loader로 변경**

`_NON_EN_DOMAINS`, `_OFFICIAL_SITE_DOMAINS`, `_MEDIA_DOMAINS`를 사용하는 모든 코드를 grep으로 찾아서:

```bash
cd backend && grep -n "_NON_EN_DOMAINS\|_OFFICIAL_SITE_DOMAINS\|_MEDIA_DOMAINS" services/news_collection.py
```

각 사용처를:
```python
# Before
if hostname in _NON_EN_DOMAINS:
    ...

# After
if hostname in _load_domain_filters()["block_non_en"]:
    ...
```

이렇게 교체. (lru_cache 덕분에 매 호출이 캐시 히트 — 비용 0)

- [ ] **Step 4.3: 전체 테스트 실행**

```bash
cd backend && pytest tests/ -v --tb=short 2>&1 | tail -30
```
Expected: 전체 PASS. Fail이 나면 import 누락 또는 사용처 갱신 누락 — 디버깅.

- [ ] **Step 4.4: ruff 통과 확인**

```bash
cd backend && ruff check services/news_collection.py
```
Expected: clean

- [ ] **Step 4.5: Commit replacement**

```bash
git add backend/services/news_collection.py
git commit -m "refactor(news): replace hardcoded domain tuples with DB-backed loader"
```

---

### Task 5: 수동 통합 검증 (1회)

**Files:** None (operational verification)

- [ ] **Step 5.1: Local에서 admin trigger로 뉴스 파이프라인 1회 실행**

```bash
cd backend && source .venv/Scripts/activate
uvicorn main:app --reload --port 8000 &
# 별도 터미널 또는 admin dashboard에서:
curl -X POST http://localhost:8000/api/admin/news \
  -H "Authorization: Bearer <admin token>"
```

또는 admin dashboard `/admin/news/`에서 manual trigger 버튼.

- [ ] **Step 5.2: 결과 확인**

- Tavily 호출이 정상 작동하는가
- 중국계 도메인이 결과에서 제외되는가 (DB의 block_non_en 적용 확인)
- pipeline_runs 테이블에 stage 로그가 정상 기록되는가

검증 SQL:
```sql
select stage, status, created_at
from pipeline_runs
where created_at > now() - interval '10 minutes'
order by created_at desc;
```

- [ ] **Step 5.3: Railway에 push & deploy**

```bash
git push origin main
# Railway 자동 배포 대기 (~3-5분)
# Railway dashboard에서 deploy 성공 확인
```

- [ ] **Step 5.4: Production daily cron 1회 성공 확인 (다음날 아침까지 대기 가능)**

다음 cron run 후 (또는 manual trigger로):
```sql
select run_id, status, completed_at
from pipeline_runs
where status = 'success'
  and created_at > now() - interval '24 hours'
order by created_at desc
limit 5;
```

**Done criteria gate**: production cron 1회 성공 확인 후 Chunk 2로 진행. 실패 시 멈추고 디버깅.

---

## Chunk 2: pipeline_persistence.py 추출 (가장 작은 모듈 먼저)

가장 의존성이 적고 분리하기 쉬운 부분부터. 다른 모듈에 의존하지 않고, 다른 모듈에서 import만 됨.

### Task 6: pipeline_persistence.py 신규 파일 생성

**Files:**
- Create: `backend/services/pipeline_persistence.py`

- [ ] **Step 6.1: 빈 파일 생성 (모듈 docstring + imports만)**

[backend/services/pipeline_persistence.py](backend/services/pipeline_persistence.py) 신규 작성:

```python
"""Persistence and notification helpers for the news pipeline.

Contains:
  - promote_drafts: scheduled draft → published promotion logic
  - _send_draft_alert: email/Slack alert when digest saved as draft
  - _notify_auto_publish: notification when draft auto-published
  - _fetch_week_digests, _fetch_week_handbook_terms: weekly aggregation helpers
  - _send_weekly_email: weekly recap email sender

Extracted from pipeline.py during 2026-04-15 news-pipeline-hardening Phase 1.
External callers should still import from `services.pipeline` (re-exported).
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)
```

- [ ] **Step 6.2: 파일 syntax 확인**

```bash
cd backend && python -c "import services.pipeline_persistence; print('ok')"
```
Expected: `ok`

- [ ] **Step 6.3: Commit empty module**

```bash
git add backend/services/pipeline_persistence.py
git commit -m "refactor(pipeline): scaffold pipeline_persistence.py module"
```

---

### Task 7: promote_drafts 및 알림 함수 이동

**Files:**
- Modify: `backend/services/pipeline.py` (remove L1701-1832: `_send_draft_alert`, `_notify_auto_publish`, `promote_drafts`)
- Modify: `backend/services/pipeline_persistence.py` (add the moved functions)

- [ ] **Step 7.1: Baseline 테스트 green 재확인**

```bash
cd backend && pytest tests/ -v --tb=short 2>&1 | tail -10
```
Expected: 전체 PASS

- [ ] **Step 7.2: 함수 이동 (cut & paste)**

[pipeline.py:1701-1832](backend/services/pipeline.py)의 다음 3개 함수를 [pipeline_persistence.py](backend/services/pipeline_persistence.py)로 이동:
- `_send_draft_alert` (L1701-1728)
- `_notify_auto_publish` (L1729-1749)
- `promote_drafts` (L1750-1832)

이동 시:
1. pipeline_persistence.py에 필요한 imports 추가 (각 함수가 사용하는 것: `core.config.settings`, `core.database.get_supabase_client` 등 — 이동된 함수 본문을 보고 결정)
2. pipeline.py에서 해당 줄 삭제
3. **`pipeline.py` 파일 끝에 re-export 추가**:

```python
# Backward-compat re-exports (Phase 1 refactoring 2026-04-15)
from services.pipeline_persistence import (
    _send_draft_alert,
    _notify_auto_publish,
    promote_drafts,
)
```

- [ ] **Step 7.3: 전체 테스트 실행**

```bash
cd backend && pytest tests/ -v --tb=short 2>&1 | tail -30
```
Expected: 전체 PASS — 만약 fail이면 import 누락. pipeline_persistence.py 상단 imports를 보강.

- [ ] **Step 7.4: ruff 통과 확인**

```bash
cd backend && ruff check services/pipeline.py services/pipeline_persistence.py
```
Expected: clean

- [ ] **Step 7.5: Commit move**

```bash
git add backend/services/pipeline.py backend/services/pipeline_persistence.py
git commit -m "refactor(pipeline): move promote_drafts + notification helpers to pipeline_persistence.py"
```

---

### Task 8: 주간 리포트 함수 이동

**Files:**
- Modify: `backend/services/pipeline.py` (remove L3413-3434, L3434-3452, L3761-end: weekly fetch/email)
- Modify: `backend/services/pipeline_persistence.py` (add weekly helpers)

- [ ] **Step 8.1: 함수 이동**

다음 3개 함수를 pipeline.py → pipeline_persistence.py로 이동:
- `_fetch_week_digests` (L3413)
- `_fetch_week_handbook_terms` (L3434)
- `_send_weekly_email` (L3761)

`_iso_week_id` (L3405)도 같이 가는 게 자연스러우면 함께 이동.

pipeline.py의 re-export 블록에 추가:
```python
from services.pipeline_persistence import (
    _send_draft_alert,
    _notify_auto_publish,
    promote_drafts,
    _fetch_week_digests,
    _fetch_week_handbook_terms,
    _send_weekly_email,
    _iso_week_id,
)
```

- [ ] **Step 8.2: 전체 테스트 실행**

```bash
cd backend && pytest tests/ -v --tb=short 2>&1 | tail -30
```
Expected: PASS

- [ ] **Step 8.3: Commit weekly move**

```bash
git add backend/services/pipeline.py backend/services/pipeline_persistence.py
git commit -m "refactor(pipeline): move weekly recap helpers to pipeline_persistence.py"
```

---

### Task 9: check_existing_batch / cleanup_existing_batch 이동 (선택)

**Files:**
- Modify: `backend/services/pipeline.py` (L425-507)
- Modify: `backend/services/pipeline_persistence.py`

- [ ] **Step 9.1: 두 함수가 persistence layer에 속하는지 판단**

`check_existing_batch`와 `cleanup_existing_batch`는 batch row의 존재 확인/삭제이므로 persistence 성격이지만, 동시에 `run_daily_pipeline`의 직접 의존이라 orchestrator에 두어도 자연스러움. **이동 여부는 코드를 보고 결정**:
- 함수 본문이 Supabase 직접 호출만 한다면 → persistence로 이동
- pipeline state 검사 로직이 섞여 있다면 → orchestrator에 잔류

- [ ] **Step 9.2: 결정에 따라 이동 (또는 skip)**

이동하는 경우 Task 7과 같은 패턴 적용. Skip하는 경우 다음 chunk로 진행.

- [ ] **Step 9.3: (이동한 경우) Commit**

```bash
git add backend/services/pipeline.py backend/services/pipeline_persistence.py
git commit -m "refactor(pipeline): move batch existence checks to pipeline_persistence.py"
```

---

## Chunk 3: pipeline_quality.py 추출

품질검사 관련 함수들을 모두 한 모듈로. Phase 2에서 URL 검증이 들어갈 자리.

### Task 10: pipeline_quality.py 신규 파일 생성

**Files:**
- Create: `backend/services/pipeline_quality.py`

- [ ] **Step 10.1: 빈 모듈 생성**

```python
"""Quality scoring and validation for generated digests.

Contains:
  - _check_digest_quality: main quality gate (LLM-based scoring)
  - Score normalizers: _normalize_scope, _normalize_quality_issue, etc.
  - Score components: _compute_structure_score, _compute_traceability_score, _compute_locale_score
  - Penalty engine: _apply_issue_penalties_and_caps, _extract_structured_issues
  - Blockers: _find_digest_blockers, _check_structural_penalties

Phase 2 (2026-04-15 news-pipeline-hardening) will add validate_citation_urls() here.

Extracted from pipeline.py during 2026-04-15 Phase 1.
External callers should still import from `services.pipeline` (re-exported).
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)
```

- [ ] **Step 10.2: Syntax check + commit**

```bash
cd backend && python -c "import services.pipeline_quality; print('ok')"
git add backend/services/pipeline_quality.py
git commit -m "refactor(pipeline): scaffold pipeline_quality.py module"
```

---

### Task 11: Score normalizer & helper 함수 이동

**Files:**
- Modify: `backend/services/pipeline.py` (remove L1002-1144: normalizers + score components)
- Modify: `backend/services/pipeline_quality.py`

- [ ] **Step 11.1: Baseline green 확인**

```bash
cd backend && pytest tests/test_pipeline_quality_scoring.py -v
```
Expected: PASS — 이게 이번 chunk의 안전 게이트.

- [ ] **Step 11.2: 함수 이동 (8개)**

다음 함수들을 pipeline.py → pipeline_quality.py로 이동:
- `_normalize_scope` (L1002)
- `_normalize_quality_issue` (L1020)
- `_extract_structured_issues` (L1040)
- `_apply_issue_penalties_and_caps` (L1052)
- `_compute_structure_score` (L1087)
- `_compute_traceability_score` (L1108)
- `_compute_locale_score` (L1124)
- `_body_paragraphs_for_quality` (L946)
- `_build_body_quality_payload` (L965)
- `_build_frontload_quality_payload` (L976)

pipeline.py 끝의 re-export 블록 확장:
```python
from services.pipeline_quality import (
    _normalize_scope,
    _normalize_quality_issue,
    _extract_structured_issues,
    _apply_issue_penalties_and_caps,
    _compute_structure_score,
    _compute_traceability_score,
    _compute_locale_score,
    _body_paragraphs_for_quality,
    _build_body_quality_payload,
    _build_frontload_quality_payload,
)
```

- [ ] **Step 11.3: 테스트 실행**

```bash
cd backend && pytest tests/test_pipeline_quality_scoring.py -v
```
Expected: PASS

```bash
cd backend && pytest tests/ -v --tb=short 2>&1 | tail -20
```
Expected: 전체 PASS

- [ ] **Step 11.4: Commit normalizers**

```bash
git add backend/services/pipeline.py backend/services/pipeline_quality.py
git commit -m "refactor(pipeline): move quality score normalizers to pipeline_quality.py"
```

---

### Task 12: _check_digest_quality 본체 이동

**Files:**
- Modify: `backend/services/pipeline.py` (remove L1145-1331)
- Modify: `backend/services/pipeline_quality.py`

- [ ] **Step 12.1: 가장 큰 함수 이동**

`_check_digest_quality` (L1145, 약 187줄)을 pipeline_quality.py로 이동.

이 함수가 사용하는 의존성을 pipeline_quality.py에 import 추가:
- `core.config.settings`
- `services.agents.client.get_openai_client, build_completion_kwargs, ...`
- 위에서 이미 이동한 normalizer/score 함수들 (같은 모듈 내부 호출이므로 import 불필요)
- 그 외 pipeline.py에 남아있는 helper에 의존하면 → 그것도 같이 이동하거나, pipeline_quality.py가 pipeline_common.py에서 import 하는 식으로 분리

pipeline.py re-export에 추가:
```python
from services.pipeline_quality import _check_digest_quality
```

- [ ] **Step 12.2: 테스트 실행**

```bash
cd backend && pytest tests/test_pipeline_quality_scoring.py::test_check_digest_quality -v
```
(테스트 이름 정확한 건 파일 확인 필요 — 대략 패턴)

Expected: PASS

```bash
cd backend && pytest tests/ -v --tb=short 2>&1 | tail -20
```
Expected: 전체 PASS

- [ ] **Step 12.3: Commit main quality function**

```bash
git add backend/services/pipeline.py backend/services/pipeline_quality.py
git commit -m "refactor(pipeline): move _check_digest_quality to pipeline_quality.py"
```

---

### Task 13: Blocker / structural penalty 함수 이동

**Files:**
- Modify: `backend/services/pipeline.py` (remove L1473-1700)
- Modify: `backend/services/pipeline_quality.py`

- [ ] **Step 13.1: 함수 이동**

다음을 pipeline_quality.py로:
- `_find_digest_blockers` (L1473)
- `_check_structural_penalties` (L1523)

pipeline.py re-export 추가:
```python
from services.pipeline_quality import _find_digest_blockers, _check_structural_penalties
```

- [ ] **Step 13.2: 테스트 실행**

```bash
cd backend && pytest tests/test_pipeline_digest_validation.py -v 2>&1 | tail -30
```
Expected: PASS (test_pipeline_digest_validation.py가 이 함수들을 직접 import해서 사용함)

- [ ] **Step 13.3: 전체 테스트**

```bash
cd backend && pytest tests/ -v --tb=short 2>&1 | tail -20
```
Expected: 전체 PASS

- [ ] **Step 13.4: Commit blockers**

```bash
git add backend/services/pipeline.py backend/services/pipeline_quality.py
git commit -m "refactor(pipeline): move blocker + structural penalty helpers to pipeline_quality.py"
```

---

## Chunk 4: pipeline_digest.py 추출

가장 큰 함수 `_generate_digest` (L1833, 약 733줄)와 content cleaner들.

### Task 14: pipeline_digest.py 신규 파일 생성

**Files:**
- Create: `backend/services/pipeline_digest.py`

- [ ] **Step 14.1: 빈 모듈 생성**

```python
"""Digest generation for daily news pipeline.

Contains:
  - _generate_digest: main per-persona digest generator (calls LLM, builds JSON output)
  - Content cleaners: _strip_empty_sections, _fix_bold_spacing, _clean_writer_output
  - Item extractors: _extract_digest_items, _map_digest_items_to_group_indexes

Extracted from pipeline.py during 2026-04-15 Phase 1.
External callers should still import from `services.pipeline` (re-exported).
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)
```

- [ ] **Step 14.2: Syntax + commit**

```bash
cd backend && python -c "import services.pipeline_digest; print('ok')"
git add backend/services/pipeline_digest.py
git commit -m "refactor(pipeline): scaffold pipeline_digest.py module"
```

---

### Task 15: Content cleaner 함수 이동

**Files:**
- Modify: `backend/services/pipeline.py` (remove L1332-1472)
- Modify: `backend/services/pipeline_digest.py`

- [ ] **Step 15.1: 함수 이동 (5개)**

다음을 pipeline.py → pipeline_digest.py로:
- `_strip_empty_sections` (L1332)
- `_fix_bold_spacing` (L1361)
- `_clean_writer_output` (L1367)
- `_extract_digest_items` (L1416)
- `_map_digest_items_to_group_indexes` (L1449)

pipeline.py re-export 추가:
```python
from services.pipeline_digest import (
    _strip_empty_sections,
    _fix_bold_spacing,
    _clean_writer_output,
    _extract_digest_items,
    _map_digest_items_to_group_indexes,
)
```

- [ ] **Step 15.2: 테스트**

```bash
cd backend && pytest tests/ -v --tb=short 2>&1 | tail -20
```
Expected: 전체 PASS

- [ ] **Step 15.3: Commit cleaners**

```bash
git add backend/services/pipeline.py backend/services/pipeline_digest.py
git commit -m "refactor(pipeline): move digest content cleaners to pipeline_digest.py"
```

---

### Task 16: _generate_digest 본체 이동 (가장 큰 함수)

**Files:**
- Modify: `backend/services/pipeline.py` (remove L1833-2565: `_generate_digest`)
- Modify: `backend/services/pipeline_digest.py`

- [ ] **Step 16.1: Baseline 재확인 — digest 테스트**

```bash
cd backend && pytest tests/test_pipeline_digest_validation.py -v 2>&1 | tail -20
```
Expected: PASS — 이 chunk의 안전 게이트.

- [ ] **Step 16.2: _generate_digest 이동**

[pipeline.py:1833-2565](backend/services/pipeline.py)의 `_generate_digest` 함수 (~733줄)를 pipeline_digest.py로 이동.

이 함수는 다음에 의존:
- `services.pipeline_quality._check_digest_quality` (이미 이동됨)
- 다양한 cleaner 함수들 (이미 같은 모듈로 이동됨)
- `services.pipeline.check_existing_batch, cleanup_existing_batch` 등 — pipeline.py에 남아있다면 그대로 import
- LLM 호출 helpers (services.agents.client)
- Pydantic 모델들 (models.news_pipeline)

**핵심 주의사항**: 
1. 이동 후 import 누락이 가장 흔한 fail 원인. pipeline_digest.py 상단에 필요한 모든 import 추가.
2. `_generate_digest`가 pipeline.py 내부의 다른 helper(예: `_renumber_citations`, `_dedup_source_cards`)를 호출한다면 **그 helper도 같이 pipeline_digest.py로 이동**해야 한다. **절대 `from services.pipeline import _renumber_citations` 형태로 import하지 말 것** — pipeline.py가 이미 pipeline_digest.py에서 re-export하고 있어서 즉시 circular import 발생. 만약 helper가 여러 모듈에서 공유되어야 한다면 `pipeline_common.py` 신규 모듈로 추출해서 거기서 import.

pipeline.py re-export 추가:
```python
from services.pipeline_digest import _generate_digest
```

- [ ] **Step 16.3: 디지스트 테스트 우선 실행**

```bash
cd backend && pytest tests/test_pipeline_digest_validation.py -v 2>&1 | tail -30
```
Expected: PASS

만약 fail이 나면 import 문제일 가능성 99%. Trace를 보고 누락 import를 보강.

- [ ] **Step 16.4: 전체 테스트**

```bash
cd backend && pytest tests/ -v --tb=short 2>&1 | tail -20
```
Expected: 전체 PASS

- [ ] **Step 16.5: ruff 통과**

```bash
cd backend && ruff check services/pipeline.py services/pipeline_digest.py
```
Expected: clean

- [ ] **Step 16.6: Commit (가장 큰 commit)**

```bash
git add backend/services/pipeline.py backend/services/pipeline_digest.py
git commit -m "refactor(pipeline): move _generate_digest (~730 lines) to pipeline_digest.py"
```

---

### Task 17: Daily/weekly run_* 함수의 import 정리

**Files:**
- Modify: `backend/services/pipeline.py` (`run_daily_pipeline`, `rerun_pipeline_stage`, `run_handbook_extraction`, `run_weekly_pipeline`)

- [ ] **Step 17.1: orchestrator 함수가 사용하는 helper들의 import 경로 점검**

이제 `run_daily_pipeline` 등이 호출하는 helper 함수들이 일부는 같은 파일(pipeline.py), 일부는 새 모듈(pipeline_digest.py 등)에 있음.

같은 파일 내부 호출은 그대로, 다른 모듈은 명시적으로 import:

```python
# pipeline.py 상단
from services.pipeline_digest import _generate_digest
from services.pipeline_quality import _check_digest_quality, _find_digest_blockers
from services.pipeline_persistence import promote_drafts, _send_draft_alert, _notify_auto_publish
```

- [ ] **Step 17.2: 전체 테스트**

```bash
cd backend && pytest tests/ -v --tb=short 2>&1 | tail -20
```
Expected: 전체 PASS

- [ ] **Step 17.3: 줄 수 측정**

```bash
wc -l backend/services/pipeline.py backend/services/pipeline_digest.py backend/services/pipeline_quality.py backend/services/pipeline_persistence.py
```
Expected (대략):
- pipeline.py: ~1500-1700줄 (orchestrator + handbook extraction + utilities + re-exports)
- pipeline_digest.py: ~900줄
- pipeline_quality.py: ~900줄
- pipeline_persistence.py: ~400줄

- [ ] **Step 17.4: Commit final imports**

```bash
git add backend/services/pipeline.py
git commit -m "refactor(pipeline): tidy explicit imports between split modules"
```

---

## Chunk 5: Final Verification & Deployment

### Task 18: 전체 회귀 검증

**Files:** None (verification)

- [ ] **Step 18.1: 전체 백엔드 테스트**

```bash
cd backend && pytest tests/ -v --tb=short 2>&1 | tail -50
```
Expected: 전체 PASS, skip 외 fail 0건

- [ ] **Step 18.2: ruff 전체**

```bash
cd backend && ruff check . 2>&1 | tail -20
```
Expected: clean

- [ ] **Step 18.3: import cycle 검사**

```bash
cd backend && python -c "
import services.pipeline
import services.pipeline_digest
import services.pipeline_quality
import services.pipeline_persistence
import services.news_collection
print('all imports clean')
"
```
Expected: `all imports clean`

- [ ] **Step 18.4: 외부 import 호환성 검증**

```bash
cd backend && python -c "
from services.pipeline import (
    check_existing_batch,
    cleanup_existing_batch,
    promote_drafts,
    rerun_pipeline_stage,
    run_daily_pipeline,
    run_handbook_extraction,
    run_weekly_pipeline,
    _extract_and_create_handbook_terms,
    _find_digest_blockers,
    _check_structural_penalties,
    _generate_digest,
    _normalize_scope,
    _apply_issue_penalties_and_caps,
    _extract_structured_issues,
    _check_digest_quality,
)
print('backward compat OK')
"
```
Expected: `backward compat OK`

---

### Task 19: Production 배포 + Daily Cron 검증

**Files:** None (operational)

- [ ] **Step 19.1: Push to main**

```bash
git push origin main
```

- [ ] **Step 19.2: Railway 배포 성공 확인**

Railway dashboard에서 build/deploy 성공 확인 (~3-5분).

- [ ] **Step 19.3: Health check**

```bash
curl https://<your-railway-domain>/health
```
Expected: `{"status": "ok"}`

- [ ] **Step 19.4: Manual trigger로 1회 검증 (또는 다음 cron 대기)**

Admin dashboard `/admin/news/`에서 manual trigger, 또는 다음날 아침 cron 자동 실행 대기.

- [ ] **Step 19.5: Pipeline run 결과 검증**

먼저 `run_type` 컬럼의 실제 값 확인 (이 SQL은 paste 전 검증용):
```sql
select distinct run_type from pipeline_runs order by run_type;
```

그 다음 실제 검증 (run_type 값을 위 결과로 치환):
```sql
select run_id, status, created_at, completed_at
from pipeline_runs
where created_at > now() - interval '24 hours'
  -- and run_type = '<actual value from above query>'  -- e.g., 'daily', 'news_daily', or whatever
order by created_at desc
limit 5;
```

Expected: 적어도 1건이 `status='success'`

- [ ] **Step 19.6: Generated digest 품질 sanity check**

```sql
select id, title, post_type, status, quality_score, auto_publish_eligible, created_at
from news_posts
where created_at > now() - interval '24 hours'
order by created_at desc
limit 5;
```

Expected: research/business digest 둘 다 생성, quality_score는 normal range

---

### Task 20: Phase 1 완료 및 Evidence 기록

**Files:**
- Modify: `vault/09-Implementation/plans/2026-04-15-news-pipeline-hardening-design.md` (Evidence 섹션)

- [ ] **Step 20.1: Evidence 섹션 채우기**

[design.md](2026-04-15-news-pipeline-hardening-design.md)의 Evidence 섹션 Phase 1 부분에 다음 기록:

```markdown
### Phase 1
- Commit hashes:
  - feat(db): news_domain_filters table — `<hash>`
  - feat(news): domain filter loader — `<hash>`
  - refactor(news): replace hardcoded tuples — `<hash>`
  - refactor(pipeline): scaffold + move persistence — `<hash>`
  - refactor(pipeline): move quality + blockers — `<hash>`
  - refactor(pipeline): move _generate_digest — `<hash>`
  - refactor(pipeline): tidy imports — `<hash>`
- Daily cron run_id (성공 확인): `<run_id>` at `<timestamp>`
- 측정:
  - pipeline.py before: 3794 lines
  - pipeline.py after: <X> lines
  - 신규 모듈: pipeline_digest.py (<Y> lines), pipeline_quality.py (<Z> lines), pipeline_persistence.py (<W> lines)
  - 테스트: 전체 PASS, 회귀 0건
```

- [ ] **Step 20.2: Phase 1 완료 commit**

```bash
git add vault/09-Implementation/plans/2026-04-15-news-pipeline-hardening-design.md
git commit -m "docs(plans): record Phase 1 evidence — pipeline split + domain filters"
git push origin main
```

- [ ] **Step 20.3: ACTIVE_SPRINT.md 업데이트 (선택)**

`vault/09-Implementation/plans/ACTIVE_SPRINT.md`가 있다면 Phase 1 완료 표시 + 다음 작업(Phase 2 plan 작성) 기재.

---

## Done Criteria Checklist (spec §4.2 매핑)

- [ ] `pipeline.py`가 4개 파일로 분리됨 (`pipeline.py` ≤500줄 목표 — 실제 ~1500줄로 완화 가능, single responsibility 충족)
- [ ] `ruff check backend/` 통과, import cycle 없음
- [ ] `pytest tests/ -v` 전체 통과 (회귀 0건)
- [ ] Railway 배포 후 daily cron 최소 1회 성공
- [ ] Supabase `news_domain_filters` 테이블 생성, 기존 도메인 시드 완료, 코드 하드코딩 제거
- [ ] `news_collection.py`가 DB에서 도메인 목록을 로드하고 Tavily 호출에 반영되는 것 수동 검증

---

## Risks & Pitfalls

1. **Import 누락이 가장 흔한 fail 원인**. 함수 이동 시 그 함수가 사용하는 모든 의존성을 새 파일에 import해야 함. 테스트 fail 메시지의 `NameError`, `ImportError`를 즉시 확인.
2. **Re-export 누락으로 외부 코드 깨짐**. routers/cron.py와 6개 테스트 파일이 직접 import하는 함수 목록(Critical Constraints §1)을 매 chunk 후 검증.
3. **`_generate_digest` 이동의 복잡도**. ~730줄에 다양한 helper 의존. Step 16에서 import trace를 꼼꼼히.
4. **Domain filter loader의 production 캐시 갱신**. `lru_cache` 때문에 DB의 도메인을 추가/삭제해도 Railway 재시작 전까지 반영 안 됨. 운영 정책으로 메모.
5. **Migration 00050 충돌 가능성**. 이미 누군가 00050을 사용했다면 00051로 변경.
