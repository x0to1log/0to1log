# DIGEST-01: 랭킹 → 카테고리별 분류 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `rank_candidates()`를 "1건 선정"에서 "카테고리별 3~5건 분류"로 전환

**Architecture:** 기존 `RankingResult(research, business)` → 새 `ClassificationResult(research: [...], business: [...])`로 변경. LLM 프롬프트가 여러 뉴스를 카테고리+서브카테고리로 분류하여 반환. 파이프라인은 이 결과를 받아서 다이제스트를 생성.

**Tech Stack:** Python, Pydantic, OpenAI gpt-4o, pytest

---

### Task 1: 새 Pydantic 모델 추가

**Files:**
- Modify: `backend/models/news_pipeline.py`

**Step 1: ClassifiedCandidate + ClassificationResult 모델 추가**

`RankingResult` 아래에 추가:

```python
class ClassifiedCandidate(BaseModel):
    """News candidate classified into a category and subcategory."""
    title: str
    url: str
    snippet: str = ""
    source: str = "tavily"
    category: str  # "research" or "business"
    subcategory: str  # e.g., "llm_models", "open_source", "papers", "big_tech", "industry", "new_tools"
    relevance_score: float = 0.0
    reason: str = ""


class ClassificationResult(BaseModel):
    """LLM classification output — multiple candidates per category."""
    research: list[ClassifiedCandidate] = []
    business: list[ClassifiedCandidate] = []
```

기존 `RankedCandidate`, `RankingResult`는 유지 (하위 호환).

**Step 2: Run tests**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_news_pipeline_models.py -v --tb=short`

**Step 3: Commit**

```bash
git add backend/models/news_pipeline.py
git commit -m "feat(models): add ClassifiedCandidate and ClassificationResult for v3 digest"
```

---

### Task 2: 분류 프롬프트 작성

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py`

**Step 1: CLASSIFICATION_SYSTEM_PROMPT 추가**

기존 `RANKING_SYSTEM_PROMPT` 아래에 추가:

```python
CLASSIFICATION_SYSTEM_PROMPT = """You are an AI news editor for 0to1log, a Korean-English bilingual AI news platform.

Your task: Given a list of AI news candidates, classify the most important ones into categories. Select 3-5 articles per category.

## Categories

### Research (기술/학술)
- **llm_models**: New model releases, benchmarks, architecture changes (GPT-5, Claude 4, Gemini, etc.)
- **open_source**: Notable open-source releases, trending GitHub/HuggingFace projects
- **papers**: Significant research papers, novel techniques, breakthrough results

### Business (시장/전략)
- **big_tech**: Major announcements from OpenAI, Google, Microsoft, Meta, Apple, Amazon, etc.
- **industry**: Startup funding, acquisitions, partnerships, regulatory changes
- **new_tools**: New AI products, services, or developer tools launched

## Rules
1. Select 3-5 articles per category (research and business)
2. The same article CAN appear in both categories if relevant to both
3. Prefer breaking/exclusive news over incremental updates
4. Prefer news with concrete data (benchmarks, dollar amounts, dates)
5. Order by importance within each category (most important first)
6. Every selected article must have a subcategory

## Output JSON format
```json
{
  "research": [
    {"url": "...", "subcategory": "llm_models|open_source|papers", "reason": "...", "score": 0.0-1.0}
  ],
  "business": [
    {"url": "...", "subcategory": "big_tech|industry|new_tools", "reason": "...", "score": 0.0-1.0}
  ]
}
```"""
```

**Step 2: Run lint**

Run: `cd backend && .venv/Scripts/python.exe -m ruff check .`

**Step 3: Commit**

```bash
git add backend/services/agents/prompts_news_pipeline.py
git commit -m "feat(prompts): add CLASSIFICATION_SYSTEM_PROMPT for v3 digest"
```

---

### Task 3: classify_candidates() 함수 구현

**Files:**
- Modify: `backend/services/agents/ranking.py`

**Step 1: classify_candidates() 함수 추가**

기존 `rank_candidates()` 유지하고 아래에 추가:

```python
from models.news_pipeline import ClassifiedCandidate, ClassificationResult
from services.agents.prompts_news_pipeline import CLASSIFICATION_SYSTEM_PROMPT


async def classify_candidates(
    candidates: list[NewsCandidate],
) -> tuple[ClassificationResult, dict[str, Any]]:
    """Classify news candidates into research/business subcategories.

    Returns 3-5 picks per category instead of 1.
    """
    if not candidates:
        logger.info("No candidates to classify")
        return ClassificationResult(), {}

    candidate_lines = []
    for i, c in enumerate(candidates):
        candidate_lines.append(
            f"[{i + 1}] {c.title}\n    URL: {c.url}\n    Snippet: {c.snippet[:300]}"
        )
    user_prompt = "\n\n".join(candidate_lines)

    client = get_openai_client()
    model = settings.openai_model_main
    usage: dict[str, Any] = {}

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=4096,
            )
            raw = response.choices[0].message.content
            data = parse_ai_json(raw, "Classification")
            usage = extract_usage_metrics(response, model)
            break
        except Exception as e:
            logger.warning("Classification attempt %d failed: %s", attempt + 1, e)
            if attempt == MAX_RETRIES:
                logger.error("Classification failed after %d retries", MAX_RETRIES + 1)
                return ClassificationResult(), usage
            continue

    url_map = {c.url: c for c in candidates}
    result = ClassificationResult()

    for category in ("research", "business"):
        picks = data.get(category, [])
        classified = []
        for pick in picks:
            url = pick.get("url", "")
            candidate = url_map.get(url)
            if not candidate:
                logger.warning("Classified URL not in candidates: %s", url)
                continue
            classified.append(ClassifiedCandidate(
                title=candidate.title,
                url=candidate.url,
                snippet=candidate.snippet,
                source=candidate.source,
                category=category,
                subcategory=pick.get("subcategory", ""),
                relevance_score=float(pick.get("score", 0)),
                reason=pick.get("reason", ""),
            ))
        setattr(result, category, classified[:5])  # Max 5 per category

    logger.info(
        "Classification complete: %d research, %d business",
        len(result.research), len(result.business),
    )
    return result, usage
```

**Step 2: Run lint**

Run: `cd backend && .venv/Scripts/python.exe -m ruff check .`

**Step 3: Commit**

```bash
git add backend/services/agents/ranking.py
git commit -m "feat(ranking): add classify_candidates() for v3 multi-news digest"
```

---

### Task 4: 테스트 추가

**Files:**
- Modify: `backend/tests/test_ranking.py`

**Step 1: classify_candidates 테스트 추가**

파일 끝에 추가:

```python
CLASSIFICATION_LLM_RESPONSE = {
    "research": [
        {"url": "https://c.com/3", "subcategory": "papers", "reason": "Novel architecture", "score": 0.92},
        {"url": "https://a.com/1", "subcategory": "llm_models", "reason": "Major release", "score": 0.88},
    ],
    "business": [
        {"url": "https://b.com/2", "subcategory": "industry", "reason": "Major funding", "score": 0.90},
        {"url": "https://a.com/1", "subcategory": "big_tech", "reason": "GPT-5 market impact", "score": 0.85},
    ],
}


@pytest.mark.asyncio
async def test_classify_candidates_returns_multiple():
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(CLASSIFICATION_LLM_RESPONSE)

    with patch("services.agents.ranking.get_openai_client", return_value=mock_client), \
         patch("services.agents.ranking.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.ranking import classify_candidates
        result, usage = await classify_candidates(SAMPLE_CANDIDATES)

    assert len(result.research) == 2
    assert len(result.business) == 2
    assert result.research[0].subcategory == "papers"
    assert result.business[0].subcategory == "industry"
    # Same article can appear in both categories
    assert any(c.url == "https://a.com/1" for c in result.research)
    assert any(c.url == "https://a.com/1" for c in result.business)


@pytest.mark.asyncio
async def test_classify_candidates_empty_list():
    from services.agents.ranking import classify_candidates
    result, usage = await classify_candidates([])
    assert result.research == []
    assert result.business == []
```

**Step 2: Run tests**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_ranking.py -v --tb=short`
Expected: All pass (existing + 2 new)

**Step 3: Run full test suite**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short && .venv/Scripts/python.exe -m ruff check .`
Expected: All 57 pass, ruff clean

**Step 4: Commit**

```bash
git add backend/tests/test_ranking.py
git commit -m "test: add classify_candidates tests for v3 digest"
```

---

## Summary

| Task | 파일 | 내용 |
|------|------|------|
| 1 | `models/news_pipeline.py` | ClassifiedCandidate + ClassificationResult 모델 |
| 2 | `prompts_news_pipeline.py` | CLASSIFICATION_SYSTEM_PROMPT |
| 3 | `ranking.py` | `classify_candidates()` 함수 |
| 4 | `test_ranking.py` | 분류 테스트 2개 |

> Note: 기존 `rank_candidates()` + `RankingResult`는 유지. pipeline.py에서 `classify_candidates()`로 교체하는 건 DIGEST-03에서 진행.
