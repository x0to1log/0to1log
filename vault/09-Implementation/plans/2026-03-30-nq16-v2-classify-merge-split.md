# NQ-16 v2: Classify/Merge 분리 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** classify+merge 동시 호출에서 발생하는 과묶기 문제를 해결. classify(개별 선별) → merge(같은 이벤트 매칭) 2단계 분리.

**Architecture:** classify가 v8 방식으로 개별 아이템 7-8개를 선별하고, 별도 merge LLM 호출이 선별된 아이템 기준으로 전체 50개 후보에서 같은 이벤트를 찾아 ClassifiedGroup으로 묶는다. 이후 단계(community, rank, enrich, write)는 기존 ClassifiedGroup 기반으로 동작.

**Tech Stack:** Python, OpenAI gpt-4.1-mini, FastAPI pipeline

---

### Task 1: CLASSIFICATION_SYSTEM_PROMPT를 v8 개별 포맷으로 복원

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py` (line 28~110)

**Step 1: CLASSIFICATION_SYSTEM_PROMPT 수정**

Rules 섹션에서 merge 관련 내용을 전부 제거하고, v8 개별 아이템 출력 포맷으로 복원:

```python
## Rules
1. Select 0-8 articles per category (research and business). If no article meets the Research criteria, return an empty list — do NOT lower the bar to fill a quota.
2. The same article CAN appear in both categories if relevant to both
3. Prefer breaking/exclusive news over incremental updates
4. Prefer news with concrete data (benchmarks, dollar amounts, dates)
5. Order by importance within each category (most important first)
6. Every selected article must have a subcategory
```

Output JSON 포맷을 flat으로 복원:

```json
{
  "research": [
    {"url": "...", "subcategory": "llm_models|open_source|papers", "reason": "...", "score": 0-100}
  ],
  "business": [
    {"url": "...", "subcategory": "big_tech|industry|new_tools", "reason": "...", "score": 0-100}
  ]
}
```

Cross-Category Rules는 유지.

**Step 2: ruff check**

Run: `backend/.venv/Scripts/python.exe -m ruff check services/agents/prompts_news_pipeline.py`

**Step 3: Commit**

```
feat(news): NQ-16v2 step1 — classify 프롬프트 v8 개별 포맷 복원
```

---

### Task 2: MERGE_SYSTEM_PROMPT 신규 작성

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py` (파일 끝, RANKING 프롬프트 근처에 추가)

**Step 1: MERGE_SYSTEM_PROMPT 추가**

```python
MERGE_SYSTEM_PROMPT = """You are an AI news editor. Your task: given a list of selected news articles and a full list of all candidates, find articles covering the SAME specific event or announcement and group them together.

## Selected Articles (already chosen as important)
{selected_items}

## All Candidates (including selected + unselected)
{all_candidates}

## Rules
1. For each selected article, check if any OTHER candidate (selected or not) covers the SAME specific event.
2. Group articles about the SAME event together. The selected article is the anchor; matched candidates become additional sources.
3. Only merge articles about the SAME specific event or announcement:
   - ✅ "OpenAI releases GPT-5" + "GPT-5 pricing announced" → same event
   - ✅ "TurboQuant paper" + "TurboQuant blog post" → same work
   - ❌ "AI Scientist-v2" + "Nested Learning" → different research
   - ❌ Multiple papers just because they share "papers" category
4. If no match is found, the article stays as a single-item group.
5. Keep the original category and subcategory from the selected article.

## Output JSON
```json
{{
  "research": [
    {{
      "group_title": "representative title",
      "subcategory": "from selected article",
      "reason": "from selected article",
      "score": 0-100,
      "items": [
        {{"url": "selected article url", "title": "..."}},
        {{"url": "matched candidate url", "title": "..."}}
      ]
    }}
  ],
  "business": [...]
}}
```"""
```

**Step 2: ruff check**

**Step 3: Commit**

```
feat(news): NQ-16v2 step2 — MERGE_SYSTEM_PROMPT 신규 작성
```

---

### Task 3: classify_candidates()를 ClassifiedCandidate 반환으로 복원

**Files:**
- Modify: `backend/services/agents/ranking.py` (line 93~192)
- Modify: `backend/models/news_pipeline.py` (ClassificationResult 변경)

**Step 1: ClassificationResult에 flat 필드 추가**

```python
class ClassificationResult(BaseModel):
    """LLM classification output."""
    research: list[ClassifiedGroup] = []
    business: list[ClassifiedGroup] = []
    # Flat picks from classify (before merge)
    research_picks: list[ClassifiedCandidate] = []
    business_picks: list[ClassifiedCandidate] = []
```

**Step 2: classify_candidates() 파싱을 flat으로 복원**

classify_candidates()가 `ClassifiedCandidate` 리스트를 `research_picks`/`business_picks`에 저장.
`research`/`business` (ClassifiedGroup)는 비워두고 merge 단계에서 채움.

```python
for category in ("research", "business"):
    picks = data.get(category, [])
    classified = []
    for pick in picks:
        url = pick.get("url", "")
        candidate = url_map.get(url)
        if not candidate:
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
    setattr(result, f"{category}_picks", classified[:8])
```

**Step 3: import 복원** — `ClassifiedCandidate`를 ranking.py import에 복원

**Step 4: ruff check + commit**

```
feat(news): NQ-16v2 step3 — classify를 flat ClassifiedCandidate 반환으로 복원
```

---

### Task 4: merge_classified() 함수 신규 작성

**Files:**
- Modify: `backend/services/agents/ranking.py` (classify_candidates 뒤에 추가)

**Step 1: merge_classified() 구현**

```python
async def merge_classified(
    classification: ClassificationResult,
    candidates: list[NewsCandidate],
) -> tuple[ClassificationResult, dict[str, Any]]:
    """Merge selected picks with matching candidates from the full pool.

    For each selected article, finds other candidates covering the same event
    and groups them together as ClassifiedGroup.
    """
```

핵심 로직:
1. selected items (research_picks + business_picks) 포맷
2. all candidates 포맷 (제목+URL만)
3. MERGE_SYSTEM_PROMPT에 넣어서 LLM 호출
4. 응답 파싱 → ClassifiedGroup 리스트 생성
5. `classification.research` / `classification.business`에 저장
6. fallback: merge 실패 시 각 pick을 1-item 그룹으로 변환

**Step 2: ruff check + commit**

```
feat(news): NQ-16v2 step4 — merge_classified() 함수 신규 작성
```

---

### Task 5: pipeline.py 오케스트레이션 변경

**Files:**
- Modify: `backend/services/pipeline.py` (line ~1110-1200)

**Step 1: classify → merge 2단계 호출로 변경**

기존:
```python
classification, classify_usage = await classify_candidates(candidates)
```

변경:
```python
# Stage: classify (개별 선별)
classification, classify_usage = await classify_candidates(candidates)

# Stage: merge (같은 이벤트 매칭)
classification, merge_usage = await merge_classified(classification, candidates)
```

**Step 2: classify 로그 수정** — picks 수 기반으로 로깅

```python
classify_output = {
    "research": [{"title": c.title, "url": c.url, "subcategory": c.subcategory} for c in classification.research_picks],
    "business": [{"title": c.title, "url": c.url, "subcategory": c.subcategory} for c in classification.business_picks],
}
output_summary = f"research={len(classification.research_picks)}, business={len(classification.business_picks)}"
```

**Step 3: merge 로그 추가**

```python
await _log_stage(
    supabase, run_id, "merge", "success", t0,
    input_summary=f"{len(classification.research_picks)+len(classification.business_picks)} picks + {len(candidates)} candidates",
    output_summary=f"research={len(classification.research)} groups, business={len(classification.business)} groups",
    usage=merge_usage,
)
```

**Step 4: import merge_classified 추가**

**Step 5: ruff check + commit**

```
feat(news): NQ-16v2 step5 — pipeline classify→merge 2단계 분리
```

---

### Task 6: 어드민 analytics에 merge 단계 추가

**Files:**
- Modify: `frontend/src/pages/admin/pipeline-analytics.astro` (stageNames, stageLabels, colorMap)

**Step 1: stageNames에 'merge' 추가** (enrich 앞에)

```javascript
const stageNames = [
  'collect', 'classify', 'merge', 'community', 'ranking', 'enrich',
  ...
];
const stageLabels = {
  ..., 'merge': 'Merge', ...
};
// colorMap에 'Merge': '#334155' (slate-700) 추가
```

**Step 2: commit**

```
feat(admin): pipeline analytics에 merge 단계 표시
```

---

### Task 7: ruff check 전체 + 동작 검증

**Files:** 전체 수정 파일

**Step 1: ruff check**

```bash
backend/.venv/Scripts/python.exe -m ruff check models/news_pipeline.py services/agents/ranking.py services/agents/prompts_news_pipeline.py services/pipeline.py
```

**Step 2: 커밋 + 푸시**

**Step 3: 파이프라인 backfill run으로 검증**
- classify 로그: 개별 7-8개 선별 확인
- merge 로그: 그룹 수 + 아이템 수 확인
- 과묶기 없음 확인 (papers 10개 한 그룹 X)
- 비용: ~$0.45 유지 확인
