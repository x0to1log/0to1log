# NQ-08: 분류/랭킹 분리 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 분류 후 별도 o4-mini 랭킹 호출로 Lead/Supporting를 명확히 구분하고, 글쓰기 LLM에 [LEAD]/[SUPPORTING] 태그로 전달하여 WEIGHTED DEPTH를 확실히 적용.

**Architecture:** `classify_candidates()` 이후, 커뮤니티 수집 이후에 `rank_classified()` 함수를 삽입. o4-mini가 카테고리별 5개 아이템을 비교 판단하여 Lead 1-2개를 결정. 글쓰기 프롬프트 입력의 `Relevance: score` → `[LEAD]`/`[SUPPORTING]` 태그로 교체. Rule 7도 태그 기반으로 수정.

**Tech Stack:** Python, OpenAI o4-mini, FastAPI pipeline

---

### Task 1: 랭킹 프롬프트 추가

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py` (파일 끝에 추가)

**Step 1: 프롬프트 상수 추가**

파일 끝(SKELETON_MAP 뒤)에 추가:

```python
# ---------------------------------------------------------------------------
# Ranking Prompt — determines Lead vs Supporting after classification
# ---------------------------------------------------------------------------

RANKING_SYSTEM_PROMPT_V2 = """You are an AI news editor deciding which story leads today's {category} digest.

Given {count} classified articles with community engagement data, pick the lead story.

## Ranking Criteria (in priority order)
1. **Impact**: How much does this change the AI landscape? A new SOTA, major funding, paradigm shift > incremental update
2. **Novelty**: Is this genuinely new? First-of-its-kind, exclusive, leak > routine release
3. **Evidence**: Concrete benchmarks, dollar amounts, user numbers > vague claims ("step change")
4. **Community signal**: High upvotes/comments indicate broad interest

## Articles
{items}

## Output JSON
Pick exactly 1 lead (rarely 2 if truly equal importance). All others are supporting.
Order supporting by importance.

{{"lead": ["url1"], "supporting": ["url2", "url3", "url4", "url5"]}}"""
```

**Step 2: Syntax check**

Run: `cd backend && .venv/Scripts/python.exe -c "import ast; ast.parse(open('services/agents/prompts_news_pipeline.py', encoding='utf-8').read()); print('OK')"`

**Step 3: Commit**

```bash
git add backend/services/agents/prompts_news_pipeline.py
git commit -m "feat(news): add RANKING_SYSTEM_PROMPT_V2 for lead/supporting separation"
```

---

### Task 2: `rank_classified()` 함수 구현

**Files:**
- Modify: `backend/services/agents/ranking.py` (함수 추가)

**Step 1: 함수 구현**

`classify_candidates()` 아래에 추가:

```python
async def rank_classified(
    items: list[ClassifiedCandidate],
    category: str,
    community_map: dict[str, str] | None = None,
) -> tuple[list[ClassifiedCandidate], dict[str, Any]]:
    """Rank classified items: assign [LEAD]/[SUPPORTING] role via o4-mini.

    Returns (reordered items with role in reason field, usage metrics).
    Lead items come first, then supporting in importance order.
    """
    if len(items) <= 1:
        # 1개면 그게 Lead
        if items:
            items[0].reason = f"[LEAD] {items[0].reason}"
        return items, {}

    from services.agents.prompts_news_pipeline import RANKING_SYSTEM_PROMPT_V2

    community_map = community_map or {}

    # Build input with engagement metadata
    item_lines = []
    for i, item in enumerate(items):
        source_domain = "/".join(item.url.split("/")[:3]) if "://" in item.url else "unknown"
        community = community_map.get(item.url, "")
        # Extract first line of community data for engagement summary
        engagement = "no community data"
        if community:
            first_line = community.split("\n")[0].strip()
            if first_line:
                engagement = first_line
        item_lines.append(
            f"[{i+1}] {item.title}\n"
            f"    URL: {item.url}\n"
            f"    Source: {source_domain}\n"
            f"    Subcategory: {item.subcategory}\n"
            f"    Community: {engagement}"
        )

    prompt = RANKING_SYSTEM_PROMPT_V2.format(
        category=category,
        count=len(items),
        items="\n".join(item_lines),
    )

    client = get_openai_client()
    model = settings.openai_model_reasoning  # o4-mini

    try:
        response = await client.chat.completions.create(
            **build_completion_kwargs(
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": "Rank these items."},
                ],
                max_tokens=256,
                temperature=0,
                response_format={"type": "json_object"},
            )
        )
        data = parse_ai_json(response.choices[0].message.content, f"Ranking-{category}")
        usage = extract_usage_metrics(response, model)
    except Exception as e:
        logger.warning("Ranking failed for %s: %s — falling back to classification order", category, e)
        # Fallback: 첫 번째를 Lead로
        items[0].reason = f"[LEAD] {items[0].reason}"
        for item in items[1:]:
            item.reason = f"[SUPPORTING] {item.reason}"
        return items, {}

    lead_urls = set(data.get("lead", []))
    supporting_urls = data.get("supporting", [])

    # Lead/Supporting 분리 + 태그 부여
    leads = []
    supports = []
    for item in items:
        if item.url in lead_urls:
            item.reason = f"[LEAD] {item.reason}"
            leads.append(item)
        else:
            item.reason = f"[SUPPORTING] {item.reason}"
            supports.append(item)

    # Supporting 순서를 랭킹 결과대로 정렬
    url_order = {url: i for i, url in enumerate(supporting_urls)}
    supports.sort(key=lambda x: url_order.get(x.url, 999))

    logger.info(
        "Ranking %s: lead=%d, supporting=%d",
        category, len(leads), len(supports),
    )
    return leads + supports, usage
```

**Step 2: import 추가**

`ranking.py` 상단의 import에 `RANKING_SYSTEM_PROMPT_V2`가 함수 내 지연 import이므로 추가 import 불필요.

**Step 3: Syntax check**

Run: `cd backend && .venv/Scripts/python.exe -c "import ast; ast.parse(open('services/agents/ranking.py', encoding='utf-8').read()); print('OK')"`

**Step 4: Commit**

```bash
git add backend/services/agents/ranking.py
git commit -m "feat(news): add rank_classified() for Lead/Supporting separation"
```

---

### Task 3: pipeline.py에 랭킹 단계 삽입

**Files:**
- Modify: `backend/services/pipeline.py:1034-1077`

**Step 1: import 추가**

`pipeline.py` 상단 import에 `rank_classified` 추가:

```python
from services.news_collection import collect_community_reactions, collect_news
```

아래에:

```python
from services.agents.ranking import classify_candidates, rank_classified
```

기존 `classify_candidates` import 위치를 확인하고 `rank_classified`를 같이 가져옴.

**Step 2: 커뮤니티 수집 대상 확대 + 랭킹 삽입**

현재 (line 1034-1077):
```python
# Stage: community reactions (top 3 items across both categories)
t0 = time.monotonic()
all_classified = sorted(
    classification.research + classification.business,
    key=lambda x: x.relevance_score, reverse=True,
)
top_items = all_classified[:3]
```

변경:
```python
# Stage: community reactions (all classified items, deduplicated)
t0 = time.monotonic()
all_classified = classification.research + classification.business
# Deduplicate by URL (same article can appear in both categories)
seen_urls: set[str] = set()
unique_items = []
for item in all_classified:
    if item.url not in seen_urls:
        seen_urls.add(item.url)
        unique_items.append(item)
community_map: dict[str, str] = {}
if unique_items:
    community_tasks = [
        collect_community_reactions(item.title, item.url)
        for item in unique_items
    ]
    community_results = await asyncio.gather(*community_tasks, return_exceptions=True)
    for item, result in zip(unique_items, community_results):
        if isinstance(result, str) and result.strip():
            community_map[item.url] = result

await _log_stage(
    supabase, run_id, "community", "success", t0,
    input_summary=f"{len(unique_items)} items queried",
    output_summary=f"{len(community_map)} reactions collected",
)

# Stage: ranking (Lead/Supporting assignment per category)
t0 = time.monotonic()
research_ranked, research_rank_usage = await rank_classified(
    classification.research, "research", community_map,
)
business_ranked, business_rank_usage = await rank_classified(
    classification.business, "business", community_map,
)
classification.research = research_ranked
classification.business = business_ranked
rank_usage = merge_usage_metrics(research_rank_usage, business_rank_usage)
cumulative_usage = merge_usage_metrics(cumulative_usage, rank_usage)

await _log_stage(
    supabase, run_id, "ranking", "success", t0,
    input_summary=f"research={len(classification.research)}, business={len(classification.business)}",
    output_summary=f"leads assigned",
    usage=rank_usage,
)
```

**Step 3: 글쓰기 프롬프트 입력 형식 변경**

현재 (line 574-578):
```python
news_items.append(
    f"### [{item.subcategory}] {item.title}\n"
    f"Source URL (MUST cite this): {item.url}\n"
    f"Relevance: {item.relevance_score}\n\n"
    f"{body}{community_block}"
)
```

변경:
```python
# Extract role tag from reason field ([LEAD] or [SUPPORTING])
role_tag = "[LEAD]" if item.reason.startswith("[LEAD]") else "[SUPPORTING]"
news_items.append(
    f"### {role_tag} [{item.subcategory}] {item.title}\n"
    f"Source URL (MUST cite this): {item.url}\n\n"
    f"{body}{community_block}"
)
```

`Relevance: score` 제거, `[LEAD]/[SUPPORTING]` 태그 추가.

**Step 4: Syntax check**

Run: `cd backend && .venv/Scripts/python.exe -c "import ast; ast.parse(open('services/pipeline.py', encoding='utf-8').read()); print('OK')"`

**Step 5: Commit**

```bash
git add backend/services/pipeline.py
git commit -m "feat(news): insert ranking stage + expand community collection + LEAD/SUPPORTING tags"
```

---

### Task 4: Rule 7 + CHECKLIST 태그 기반으로 수정

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py:223-227, 274`

**Step 1: Rule 7 수정**

현재:
```
7. WEIGHTED DEPTH: Not all news items are equally important. Allocate depth by significance:
   - **Lead story** (1, at most 2): The most significant item(s) today. 3-4 paragraphs for both Expert and Learner.
   - **Supporting stories** (rest): Every remaining item MUST get at least 3 paragraphs for BOTH Expert and Learner.
```

변경:
```
7. WEIGHTED DEPTH: Items are tagged [LEAD] or [SUPPORTING] in the input.
   - **[LEAD] items**: Write 3-4 paragraphs. These are today's most important stories.
   - **[SUPPORTING] items**: Write at least 3 paragraphs for BOTH Expert and Learner.
   - Both Expert and Learner should provide substantial, thorough coverage. The difference is WHAT they write — not how MUCH.
   - Include context for numbers. Do NOT exceed 4 paragraphs per item even for the lead story.
```

**Step 2: CHECKLIST 3 수정**

현재:
```
3. Does the lead story have 3-4 paragraphs, and do ALL supporting stories have at least 3 paragraphs (both expert and learner)? Expand if below minimum.
```

변경:
```
3. Do [LEAD] items have 3-4 paragraphs, and do ALL [SUPPORTING] items have at least 3 paragraphs? Expand if below minimum.
```

**Step 3: Syntax check**

**Step 4: Commit**

```bash
git add backend/services/agents/prompts_news_pipeline.py
git commit -m "feat(news): Rule 7 + CHECKLIST use [LEAD]/[SUPPORTING] tags from ranking"
```

---

### Task 5: 전체 검증 + 최종 커밋

**Step 1: 전체 syntax check**

```bash
cd backend && .venv/Scripts/python.exe -c "
import ast
for f in ['services/agents/prompts_news_pipeline.py', 'services/agents/ranking.py', 'services/pipeline.py']:
    ast.parse(open(f, encoding='utf-8').read())
    print(f'{f}: OK')
"
```

**Step 2: import 검증**

```bash
cd backend && .venv/Scripts/python.exe -c "
from services.agents.prompts_news_pipeline import RANKING_SYSTEM_PROMPT_V2
print('Prompt import OK')
"
```

**Step 3: Push**

```bash
git push origin main
```

---

## 검증 (다음 파이프라인 run)

파이프라인 실행 후 확인:
1. **pipeline_logs에 "ranking" 스테이지**가 기록되는지
2. **fact_pack에 Lead URL**이 기록되는지
3. **글쓰기 출력에서 Lead 아이템이 다른 아이템보다 깊이 있는지** (문단 수 차이)
4. **Research에서도 Lead 구분이 되는지** (이전에는 5개 전부 3p로 동일)
5. **커뮤니티 수집이 전체 아이템 대상인지** (이전 3개 → 7-8개)

## 비용/레이턴시 영향

| 항목 | 추가 비용 | 추가 시간 |
|------|----------|----------|
| 랭킹 (o4-mini × 2) | $0.002/run | ~3초 |
| 커뮤니티 수집 확대 (3→8개) | $0 (무료 API) | ~2초 (병렬) |
| **월간** | **$0.06** | — |
