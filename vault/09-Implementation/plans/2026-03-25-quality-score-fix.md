# Quality Score Trend Fix & Improvement Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Quality Score Trend 차트에 데이터가 표시되지 않는 문제를 진단/수정하고, quality check를 o4-mini로 업그레이드한다.

**Architecture:** 기존 `_check_digest_quality()` 함수가 이미 존재하지만 데이터가 차트에 안 나타남. 원인을 진단하고, 모델을 o4-mini(추론 모델)로 교체하고, 프롬프트를 개선한다.

**Tech Stack:** FastAPI, OpenAI o4-mini, Supabase, Astro, Chart.js

---

## Task 1: 진단 — DB에 quality 로그가 있는지 확인

**Files:**
- Read: `frontend/src/pages/admin/pipeline-analytics.astro:46-56`

**Step 1: Supabase에서 quality 로그 직접 확인**

Supabase Dashboard → SQL Editor에서 실행:

```sql
-- quality 로그가 있는지 확인
SELECT pl.pipeline_type, pl.status, pl.debug_meta, pl.created_at,
       pr.run_key, pr.started_at
FROM pipeline_logs pl
JOIN pipeline_runs pr ON pl.run_id = pr.id
WHERE pl.pipeline_type IN ('quality:research', 'quality:business')
ORDER BY pl.created_at DESC
LIMIT 20;
```

**Expected:**
- 결과 있음 → 차트 렌더링 문제 (Task 3으로)
- 결과 없음 → quality check가 실패하고 있음 (Task 2로)
- 결과 있지만 `started_at`이 14일 이전 → 단순히 최근 실행이 없는 것 (Task 2에서 수동 실행으로 확인)

**Step 2: news_posts에 quality_score가 있는지 확인**

```sql
SELECT slug, quality_score, status, updated_at
FROM news_posts
WHERE quality_score IS NOT NULL
ORDER BY updated_at DESC
LIMIT 20;
```

---

## Task 2: quality check 실패 시 로깅 개선

**Files:**
- Modify: `backend/services/pipeline.py:433-488`

**Step 1: early return에도 로그 남기기**

현재 문제: expert 페르소나가 없으면 `return 0`으로 **로그 없이** 종료.

```python
# 현재 (line 445-447)
expert = personas.get("expert")
if not expert or not expert.en:
    return 0

# 수정 후
expert = personas.get("expert")
if not expert or not expert.en:
    logger.warning("Quality check skipped for %s: no expert content", digest_type)
    await _log_stage(
        supabase, run_id, f"quality:{digest_type}", "skipped", t0,
        output_summary="No expert content available",
        post_type=digest_type,
    )
    return 0
```

**Step 2: exception 로그에도 debug_meta 추가**

```python
# 현재 (line 482-488)
except Exception as e:
    logger.warning("Quality check failed for %s: %s", digest_type, e)
    await _log_stage(
        supabase, run_id, f"quality:{digest_type}", "failed", t0,
        error_message=str(e), post_type=digest_type,
    )
    return 0

# 수정 후
except Exception as e:
    logger.warning("Quality check failed for %s: %s", digest_type, e, exc_info=True)
    await _log_stage(
        supabase, run_id, f"quality:{digest_type}", "failed", t0,
        error_message=str(e), post_type=digest_type,
        debug_meta={"quality_score": 0, "error_type": type(e).__name__},
    )
    return 0
```

**Step 3: 커밋**

```bash
git add backend/services/pipeline.py
git commit -m "fix: add logging for skipped/failed quality checks"
```

---

## Task 3: 모델을 o4-mini로 교체

**Files:**
- Modify: `backend/services/pipeline.py:451-462`

**Step 1: openai_model_reasoning 사용으로 변경**

```python
# 현재
response = await client.chat.completions.create(
    model=settings.openai_model_light,
    messages=[
        {"role": "system", "content": prompt},
        {"role": "user", "content": expert.en[:4000]},
    ],
    response_format={"type": "json_object"},
    temperature=0.1,
    max_tokens=512,
)

# 수정 후 (o4-mini는 max_completion_tokens 사용)
response = await client.chat.completions.create(
    model=settings.openai_model_reasoning,
    messages=[
        {"role": "system", "content": prompt},
        {"role": "user", "content": expert.en[:4000]},
    ],
    response_format={"type": "json_object"},
    max_completion_tokens=1024,
)
```

Note: o4-mini는 `temperature` 파라미터 불필요 (추론 모델은 자체 reasoning), `max_tokens` → `max_completion_tokens`.

**Step 2: usage 추출도 모델명 변경**

```python
# 현재
usage = extract_usage_metrics(response, settings.openai_model_light)

# 수정 후
usage = extract_usage_metrics(response, settings.openai_model_reasoning)
```

**Step 3: 커밋**

```bash
git add backend/services/pipeline.py
git commit -m "feat: upgrade quality check to o4-mini reasoning model"
```

---

## Task 4: 프롬프트 개선

**Files:**
- Modify: `backend/services/pipeline.py:408-430`

**Step 1: 평가 기준을 더 구체적으로**

현재 프롬프트는 기본적인 평가 기준만 있음. 채점 앵커(scoring examples)를 추가:

```python
QUALITY_CHECK_PROMPT_RESEARCH = """You are a strict quality reviewer for an AI tech news digest.

Score this Research digest on 4 criteria (0-25 each, total 0-100):

1. **Section Completeness** (25):
   - 25: All 5 sections present with substantial content (200+ chars each)
   - 15: All sections present but some thin (<100 chars)
   - 5: Missing 1+ sections
   - 0: Missing 3+ sections

2. **Source Citations** (25):
   - 25: Every claim cites a source URL; benchmark numbers attributed
   - 15: Most items cite sources; a few missing
   - 5: Fewer than half cite sources
   - 0: No source citations

3. **Technical Accuracy** (25):
   - 25: Specific numbers (params, benchmarks, dates); comparisons to prior work
   - 15: Some specifics but also vague claims ("significantly better")
   - 5: Mostly vague; no concrete metrics
   - 0: Contains factual errors or hallucinated details

4. **Language Quality** (25):
   - 25: Natural, fluent; min 500 chars per section; no translation artifacts
   - 15: Readable but some awkward phrasing; adequate length
   - 5: Choppy or translation-sounding; some sections too short
   - 0: Barely readable or extremely short

Return JSON only:
{"score": 0-100, "sections": 0-25, "sources": 0-25, "accuracy": 0-25, "language": 0-25, "issues": ["issue1", "issue2"]}"""

QUALITY_CHECK_PROMPT_BUSINESS = """You are a strict quality reviewer for an AI business news digest.

Score this Business digest on 4 criteria (0-25 each, total 0-100):

1. **Section Completeness** (25):
   - 25: All 6 sections present with substantial content (200+ chars each)
   - 15: All sections present but some thin
   - 5: Missing 1+ sections
   - 0: Missing 3+ sections

2. **Source Citations** (25):
   - 25: Every claim cites a source URL; funding amounts/dates attributed
   - 15: Most items cite sources
   - 5: Fewer than half cite sources
   - 0: No source citations

3. **Analysis Quality** (25):
   - 25: "Connecting the Dots" links 2+ news items into a coherent trend; "Strategic Decisions" are specific and actionable (not generic)
   - 15: Analysis exists but surface-level; decisions somewhat generic
   - 5: Analysis is just restating news; decisions are platitudes
   - 0: No analysis section or completely generic

4. **Language Quality** (25):
   - 25: Natural, fluent; adequate length; no translation artifacts
   - 15: Readable but some awkward phrasing
   - 5: Choppy or translation-sounding
   - 0: Barely readable

Return JSON only:
{"score": 0-100, "sections": 0-25, "sources": 0-25, "analysis": 0-25, "language": 0-25, "issues": ["issue1", "issue2"]}"""
```

**Step 2: 커밋**

```bash
git add backend/services/pipeline.py
git commit -m "feat: improve quality check prompts with scoring anchors"
```

---

## Task 5: 프론트엔드 차트 — "skipped" 상태도 표시

**Files:**
- Modify: `frontend/src/pages/admin/pipeline-analytics.astro:52-56`

**Step 1: qualityLogs 쿼리에 skipped 로그의 score=0도 포함되도록**

현재 코드는 `debug_meta.quality_score`가 number인 로그만 차트에 넣음 (line 141). Task 2에서 실패 시에도 `quality_score: 0`을 debug_meta에 넣으므로, 실패/스킵도 차트에 0으로 표시됨.

추가 변경 없음 — Task 2의 debug_meta 추가로 자동 해결.

---

## Task 6: 통합 테스트 — 파이프라인 수동 실행

**Step 1: Railway에서 파이프라인 수동 트리거**

어드민 대시보드에서 파이프라인을 수동 실행하거나 cron 엔드포인트 호출:
```
POST /api/cron/news-pipeline
x-cron-secret: <secret>
```

**Step 2: 확인 사항**

1. Railway 로그에서 `Quality check research: score=XX/100` 메시지 확인
2. Pipeline Analytics → Quality Score Trend 차트에 데이터 포인트 표시 확인
3. 어드민 뉴스 목록에서 새 draft에 `QXX` 배지 표시 확인
4. Pipeline Run 상세 페이지에서 `quality:research`, `quality:business` 스테이지 표시 확인

**Step 3: 커밋 (전체 통합)**

```bash
git push origin main
```

---

## Summary

| Task | 내용 | 난이도 |
|------|------|--------|
| 1 | DB 진단 (SQL 쿼리) | 수동 확인 |
| 2 | 실패/스킵 시 로깅 개선 | 간단 |
| 3 | o4-mini 모델 교체 | 간단 |
| 4 | 프롬프트 scoring anchor 추가 | 중간 |
| 5 | 프론트엔드 (변경 없음, Task 2로 해결) | - |
| 6 | 통합 테스트 | 수동 확인 |
