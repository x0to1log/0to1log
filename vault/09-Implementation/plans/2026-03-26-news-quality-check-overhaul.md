# News Quality Check Overhaul

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 뉴스 품질 체크 프롬프트를 현행 digest 구조에 맞게 전면 재작성하고, Learner 평가를 추가하며, 프롬프트를 `prompts_news_pipeline.py`로 통합한다.

**Architecture:** pipeline.py에 인라인된 `QUALITY_CHECK_PROMPT_RESEARCH/BUSINESS`를 `prompts_news_pipeline.py`로 이동. Research/Business × Expert/Learner = 4개 프롬프트로 분리. 평가 기준을 현행 섹션명과 글쓰기 프롬프트의 의도에 맞게 재작성. `_check_digest_quality()`를 Expert+Learner 양쪽 평가하도록 확장.

**Tech Stack:** Python, OpenAI o4-mini, FastAPI pipeline

---

## Context

### 현재 상태
- 품질 체크 프롬프트 2개가 `pipeline.py:407-467`에 인라인
- Expert EN 콘텐츠만 평가 (Learner 평가 없음)
- 섹션명 미명시 ("All 5 sections")로 옛 섹션명 오탐 발생
- Research 기준이 리팩토링 이전 기준 (Technical Outlook 등)
- `quality_score` 필드가 `news_posts` 테이블에 integer로 저장 (0-100)
- `fact_pack` jsonb에 breakdown 저장

### 현행 섹션 구조 (프롬프트 기준)
```
Research Expert:  One-Line Summary, LLM & SOTA Models, Open Source & Repos, Research Papers, Why It Matters
Research Learner: One-Line Summary, LLM & SOTA Models, Open Source & Repos, Research Papers, Why It Matters
Business Expert:  One-Line Summary, Big Tech, Industry & Biz, New Tools, Connecting the Dots, Strategic Decisions
Business Learner: One-Line Summary, Big Tech, Industry & Biz, New Tools, What This Means for You, Action Items
```

### 0-5 룰 반영
Research 섹션(LLM & SOTA Models, Open Source & Repos, Research Papers)은 해당 일자에 뉴스가 없으면 의도적으로 생략 가능. 품질 체커는 이를 감점하면 안 됨.

---

### Task 1: prompts_news_pipeline.py에 프롬프트 4개 추가

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py` (파일 끝에 추가)

**Step 1: Research Expert 품질 체크 프롬프트 추가**

파일 맨 끝에 추가:

```python
# --- Quality Check Prompts ---
# Moved from pipeline.py and updated to match current digest sections.

QUALITY_CHECK_RESEARCH_EXPERT = """You are a strict quality reviewer for an AI tech research digest written for senior ML engineers.

Score this digest on 4 criteria (0-25 each, total 0-100):

1. **Section Completeness** (25):
   Required sections: One-Line Summary, LLM & SOTA Models, Open Source & Repos, Research Papers, Why It Matters.
   NOTE: LLM & SOTA Models, Open Source & Repos, and Research Papers may be intentionally omitted if no relevant news exists for that day. Do NOT penalize intentional omissions.
   - 25: All present sections have substantial content (200+ chars each). One-Line Summary is concise and accurate.
   - 18: Present sections are adequate but 1 is thin (<150 chars)
   - 10: 1+ present section is very thin or poorly structured
   - 0: Content structure is broken or unrecognizable

2. **Source Citations** (25):
   Expected format: [Source Title](URL) inline citations, arXiv IDs (arXiv:XXXX.XXXXX), or GitHub/HuggingFace links.
   - 25: Every technical claim cites a source; benchmark numbers are attributed; paper IDs and repo URLs are present
   - 18: Most items cite sources; 1-2 claims missing attribution
   - 10: Fewer than half of claims cite sources
   - 0: No source citations or fabricated URLs

3. **Technical Depth** (25):
   - 25: Specific numbers (parameter counts, benchmark scores, FLOPs, latency); comparisons to baselines; architecture details
   - 18: Some specifics but also vague claims ("significantly improved")
   - 10: Mostly vague; no concrete metrics or comparisons
   - 0: Contains factual errors or hallucinated benchmarks

4. **Language Quality** (25):
   - 25: Reads like a peer engineer's analysis; assertive tone; each news item is 3-4 paragraphs; natural and fluent
   - 18: Readable and professional; adequate length but some hedging ("may", "could")
   - 10: Choppy, translation-sounding, or some items are only 1 paragraph
   - 0: Barely readable or extremely short

Return JSON only:
{"score": 0-100, "sections": 0-25, "sources": 0-25, "depth": 0-25, "language": 0-25, "issues": ["issue1"]}"""


QUALITY_CHECK_RESEARCH_LEARNER = """You are a quality reviewer for an AI tech research digest written for beginners and curious developers.

Score this digest on 4 criteria (0-25 each, total 0-100):

1. **Section Completeness** (25):
   Required sections: One-Line Summary, LLM & SOTA Models, Open Source & Repos, Research Papers, Why It Matters.
   NOTE: LLM & SOTA Models, Open Source & Repos, and Research Papers may be intentionally omitted if no relevant news exists. Do NOT penalize intentional omissions.
   - 25: All present sections have substantial content. One-Line Summary is approachable.
   - 18: Present sections adequate but 1 is thin
   - 10: 1+ present section is very thin
   - 0: Broken structure

2. **Accessibility** (25):
   - 25: Technical terms are explained inline on first use; analogies help understanding; jargon is never left unexplained
   - 18: Most terms explained; 1-2 left without context
   - 10: Assumes too much prior knowledge; multiple unexplained terms
   - 0: Written like an expert brief; inaccessible to beginners

3. **Source Citations** (25):
   - 25: Key claims cite sources; paper and repo links are present where relevant
   - 18: Most items cite sources
   - 10: Fewer than half cite sources
   - 0: No citations

4. **Language Quality** (25):
   - 25: Conversational but substantive ("senior colleague over coffee"); each item 2-3 paragraphs; no tutorial/action-plan drift
   - 18: Readable; mostly appropriate tone; adequate length
   - 10: Too formal, too casual, or too short
   - 0: Barely readable

Return JSON only:
{"score": 0-100, "sections": 0-25, "accessibility": 0-25, "sources": 0-25, "language": 0-25, "issues": ["issue1"]}"""


QUALITY_CHECK_BUSINESS_EXPERT = """You are a strict quality reviewer for an AI business digest written for senior decision-makers.

Score this digest on 4 criteria (0-25 each, total 0-100):

1. **Section Completeness** (25):
   Required sections: One-Line Summary, Big Tech, Industry & Biz, New Tools, Connecting the Dots, Strategic Decisions.
   - 25: All 6 sections present with substantial content (200+ chars each)
   - 18: All present but 1 is thin
   - 10: Missing 1 section or 2+ very thin
   - 0: Missing 2+ sections

2. **Source Citations** (25):
   - 25: Every claim cites a source; funding amounts, dates, and deal terms attributed
   - 18: Most items cite sources; 1-2 unattributed claims
   - 10: Fewer than half cite sources
   - 0: No citations

3. **Analysis Quality** (25):
   - 25: "Connecting the Dots" reveals causation between 2+ news items with market forces analysis; "Strategic Decisions" are specific with situation/action/reasoning/risk format
   - 18: Analysis exists but surface-level; decisions somewhat generic
   - 10: Analysis just restates news; decisions are platitudes
   - 0: No analysis or completely generic

4. **Language Quality** (25):
   - 25: Reads like a strategic advisor's private briefing; assertive; each item 3-4 paragraphs; specific comparisons
   - 18: Professional and readable; adequate length
   - 10: Choppy or too general; some items only 1 paragraph
   - 0: Barely readable

Return JSON only:
{"score": 0-100, "sections": 0-25, "sources": 0-25, "analysis": 0-25, "language": 0-25, "issues": ["issue1"]}"""


QUALITY_CHECK_BUSINESS_LEARNER = """You are a quality reviewer for an AI business digest written for general audiences.

Score this digest on 4 criteria (0-25 each, total 0-100):

1. **Section Completeness** (25):
   Required sections: One-Line Summary, Big Tech, Industry & Biz, New Tools, What This Means for You, Action Items.
   - 25: All 6 sections present with substantial content
   - 18: All present but 1 is thin
   - 10: Missing 1 section or 2+ very thin
   - 0: Missing 2+ sections

2. **Accessibility** (25):
   - 25: Business concepts are explained in relatable terms; industry jargon is decoded; examples connect to daily life
   - 18: Most concepts accessible; 1-2 left unexplained
   - 10: Assumes business/AI background; jargon heavy
   - 0: Inaccessible to general audience

3. **Actionability** (25):
   - 25: "Action Items" are specific, concrete, and doable this week (not generic "learn AI"); "What This Means for You" connects news to real impact
   - 18: Actions exist but some are vague; meaning section is decent
   - 10: Actions are generic platitudes ("stay updated"); meaning section thin
   - 0: No actionable content or empty sections

4. **Language Quality** (25):
   - 25: Friendly but informative; each item 2-3 paragraphs; engaging tone
   - 18: Readable; adequate length
   - 10: Too dry, too short, or condescending
   - 0: Barely readable

Return JSON only:
{"score": 0-100, "sections": 0-25, "accessibility": 0-25, "actionability": 0-25, "language": 0-25, "issues": ["issue1"]}"""
```

**Step 2: Verify import**

Run: `cd backend && source .venv/Scripts/activate && python -c "from services.agents.prompts_news_pipeline import QUALITY_CHECK_RESEARCH_EXPERT, QUALITY_CHECK_RESEARCH_LEARNER, QUALITY_CHECK_BUSINESS_EXPERT, QUALITY_CHECK_BUSINESS_LEARNER; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add backend/services/agents/prompts_news_pipeline.py
git commit -m "feat(news): add 4 quality check prompts to prompts_news_pipeline.py"
```

---

### Task 2: pipeline.py에서 인라인 프롬프트 제거 + 임포트 교체

**Files:**
- Modify: `backend/services/pipeline.py:407-467` (프롬프트 삭제)
- Modify: `backend/services/pipeline.py:493` (임포트 교체)

**Step 1: 인라인 프롬프트 삭제**

`pipeline.py`에서 `QUALITY_CHECK_PROMPT_RESEARCH`와 `QUALITY_CHECK_PROMPT_BUSINESS` 변수 정의(line 407-467)를 삭제한다.

**Step 2: `_check_digest_quality` 함수의 프롬프트 참조 교체**

기존 (line 493):
```python
prompt = QUALITY_CHECK_PROMPT_RESEARCH if digest_type == "research" else QUALITY_CHECK_PROMPT_BUSINESS
```

교체:
```python
from services.agents.prompts_news_pipeline import (
    QUALITY_CHECK_RESEARCH_EXPERT, QUALITY_CHECK_RESEARCH_LEARNER,
    QUALITY_CHECK_BUSINESS_EXPERT, QUALITY_CHECK_BUSINESS_LEARNER,
)
```
(이 import는 함수 상단 또는 파일 상단에 추가)

**Step 3: Syntax check**

Run: `cd backend && python -c "import ast; ast.parse(open('services/pipeline.py', encoding='utf-8').read()); print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add backend/services/pipeline.py
git commit -m "refactor(news): remove inline quality prompts from pipeline.py"
```

---

### Task 3: `_check_digest_quality` 함수를 Expert+Learner 양쪽 평가로 확장

**Files:**
- Modify: `backend/services/pipeline.py` (`_check_digest_quality` 함수)

**Step 1: 함수 시그니처 및 로직 변경**

현재 함수는 `expert.en[:4000]`만 평가하고 하나의 score를 반환한다.

변경 후:
1. Expert EN + Learner EN 각각에 맞는 프롬프트로 2회 호출 (asyncio.gather로 병렬)
2. Expert 점수와 Learner 점수를 평균하여 최종 score 반환
3. breakdown에 expert/learner 각각의 세부 점수 포함
4. `fact_pack`에 `quality_breakdown` 추가

```python
async def _check_digest_quality(
    personas: dict[str, PersonaOutput],
    digest_type: str,
    classified: list,
    supabase,
    run_id: str,
    cumulative_usage: dict[str, Any],
) -> int:
    """Score quality of generated digest. Expert + Learner evaluated separately.
    Returns combined score 0-100 (average of expert and learner scores).
    """
    t0 = time.monotonic()
    from services.agents.prompts_news_pipeline import (
        QUALITY_CHECK_RESEARCH_EXPERT, QUALITY_CHECK_RESEARCH_LEARNER,
        QUALITY_CHECK_BUSINESS_EXPERT, QUALITY_CHECK_BUSINESS_LEARNER,
    )

    expert = personas.get("expert")
    learner = personas.get("learner")
    if not expert or not expert.en:
        logger.warning("Quality check skipped for %s: no expert content", digest_type)
        await _log_stage(
            supabase, run_id, f"quality:{digest_type}", "skipped", t0,
            output_summary="No expert content available",
            post_type=digest_type,
            debug_meta={"quality_score": 0, "skipped": True},
        )
        return 0

    if digest_type == "research":
        expert_prompt = QUALITY_CHECK_RESEARCH_EXPERT
        learner_prompt = QUALITY_CHECK_RESEARCH_LEARNER
    else:
        expert_prompt = QUALITY_CHECK_BUSINESS_EXPERT
        learner_prompt = QUALITY_CHECK_BUSINESS_LEARNER

    client = get_openai_client()
    reasoning_model = settings.openai_model_reasoning

    async def _score(prompt: str, content: str, label: str) -> tuple[int, dict, dict]:
        try:
            resp = await client.chat.completions.create(
                **build_completion_kwargs(
                    model=reasoning_model,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": content[:4000]},
                    ],
                    max_tokens=500,
                    temperature=0,
                    response_format={"type": "json_object"},
                )
            )
            data = parse_ai_json(resp.choices[0].message.content, label)
            usage = extract_usage_metrics(resp, reasoning_model)
            return int(data.get("score", 0)), data, usage
        except Exception as e:
            logger.warning("Quality check %s failed: %s", label, e)
            return 0, {}, {}

    # Run expert + learner quality checks in parallel
    tasks = [_score(expert_prompt, expert.en, f"Quality-{digest_type}-expert")]
    if learner and learner.en:
        tasks.append(_score(learner_prompt, learner.en, f"Quality-{digest_type}-learner"))

    results = await asyncio.gather(*tasks)

    expert_score, expert_breakdown, expert_usage = results[0]
    learner_score, learner_breakdown, learner_usage = (
        results[1] if len(results) > 1 else (0, {}, {})
    )

    # Combined score: average of expert and learner (or expert only if no learner)
    if learner and learner.en:
        combined_score = (expert_score + learner_score) // 2
    else:
        combined_score = expert_score

    merged_quality_usage = merge_usage_metrics(expert_usage, learner_usage) if learner_usage else expert_usage

    await _log_stage(
        supabase, run_id, f"quality:{digest_type}", "success", t0,
        output_summary=f"score={combined_score}/100 (expert={expert_score}, learner={learner_score})",
        usage=merged_quality_usage,
        post_type=digest_type,
        debug_meta={
            "score": combined_score,
            "quality_score": combined_score,
            "expert_score": expert_score,
            "learner_score": learner_score,
            "expert_breakdown": {k: v for k, v in expert_breakdown.items() if k != "score"},
            "learner_breakdown": {k: v for k, v in learner_breakdown.items() if k != "score"},
            "news_count": len(classified),
        },
    )

    logger.info(
        "Quality check %s: combined=%d/100 (expert=%d, learner=%d)",
        digest_type, combined_score, expert_score, learner_score,
    )
    return combined_score
```

**Step 2: Syntax check**

Run: `cd backend && python -c "import ast; ast.parse(open('services/pipeline.py', encoding='utf-8').read()); print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add backend/services/pipeline.py
git commit -m "feat(news): evaluate expert + learner quality in parallel"
```

---

### Task 4: 테스트 업데이트

**Files:**
- Modify: `backend/tests/test_news_pipeline_models.py` (if quality-related tests exist)
- Check: `backend/tests/test_pipeline.py` (if exists)

**Step 1: 기존 테스트 확인 및 통과 검증**

Run: `cd backend && source .venv/Scripts/activate && python -m pytest tests/ -v --tb=short -k "quality or pipeline" 2>&1 | head -50`

**Step 2: 프롬프트 임포트 테스트 추가 (필요 시)**

If no existing test covers the imports, add a simple import test:

```python
def test_quality_check_prompts_importable():
    from services.agents.prompts_news_pipeline import (
        QUALITY_CHECK_RESEARCH_EXPERT,
        QUALITY_CHECK_RESEARCH_LEARNER,
        QUALITY_CHECK_BUSINESS_EXPERT,
        QUALITY_CHECK_BUSINESS_LEARNER,
    )
    assert "Section Completeness" in QUALITY_CHECK_RESEARCH_EXPERT
    assert "Accessibility" in QUALITY_CHECK_RESEARCH_LEARNER
    assert "Analysis Quality" in QUALITY_CHECK_BUSINESS_EXPERT
    assert "Actionability" in QUALITY_CHECK_BUSINESS_LEARNER
```

**Step 3: Full test run**

Run: `cd backend && source .venv/Scripts/activate && python -m pytest tests/ -v --tb=short`
Expected: All tests pass

**Step 4: Ruff check**

Run: `cd backend && source .venv/Scripts/activate && python -m ruff check .`
Expected: No errors

**Step 5: Commit**

```bash
git add backend/tests/
git commit -m "test(news): add quality check prompt import tests"
```

---

### Task 5: 최종 검증 + 푸시

**Step 1: 전체 문법 검증**

Run: `cd backend && python -c "import ast; [ast.parse(open(f, encoding='utf-8').read()) for f in ['services/pipeline.py', 'services/agents/prompts_news_pipeline.py']]; print('All OK')"`

**Step 2: 커밋 히스토리 확인**

Run: `git log --oneline -5`

**Step 3: Push**

Run: `git push origin main`

---

## 변경 요약

| 항목 | Before | After |
|---|---|---|
| 프롬프트 위치 | pipeline.py 인라인 | prompts_news_pipeline.py |
| 프롬프트 개수 | 2개 (R/B) | 4개 (R-Expert, R-Learner, B-Expert, B-Learner) |
| 평가 대상 | Expert EN만 | Expert EN + Learner EN 병렬 |
| 섹션명 | "All 5 sections" (미명시) | 정확한 섹션명 나열 |
| Research 0-5 룰 | 빈 섹션 = 감점 | 의도적 생략 = 감점 안 함 |
| Business 기준 3 | Analysis Quality | 동일 (Expert), Actionability (Learner) |
| Research 기준 3 | Technical Accuracy | Technical Depth (Expert), Accessibility (Learner) |
| score 저장 | 단일 score | 평균 score + breakdown에 expert/learner 각각 |
| 비용 | o4-mini 1회/digest | o4-mini 2회/digest (병렬, +~$0.004) |
