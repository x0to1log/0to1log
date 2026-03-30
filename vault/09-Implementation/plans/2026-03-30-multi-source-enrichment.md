# NQ-13: 같은 이벤트 다중 소스 수집 (Multi-Source Enrichment)

> **상태:** 계획 확정, 구현 대기
> **목표:** 같은 이벤트의 다른 기사들을 묶어서 Writer에 다중 소스로 전달, 분석 깊이와 citation 신뢰도 향상

---

## 현재 문제

1. **Writer가 기사 1개만 보고 작성** — `raw_content[:4000]` 1개 소스의 관점만 반영
2. **같은 이벤트가 별도 아이템으로 분류됨** — TechCrunch, Reuters, 공식 블로그가 같은 뉴스를 다뤄도 각각 분류
3. **citation이 1개뿐** — LEAD급 뉴스에 출처 1개는 "얇은 느낌"
4. **4000자 제한** — 기사 후반부(벤치마크, limitations) 잘림 가능

## 목표 상태

- 뉴스 아이템 1개 = 같은 이벤트의 기사 1~4개 × 전문
- Writer가 다각도 정보를 종합해서 더 깊은 분석 작성
- 1차/2차 수집 구분 없이 모든 소스 동등하게 취급

---

## 확정된 설계 결정

| # | 결정 사항 | 결정 | 이유 |
|---|----------|------|------|
| 1 | 글자 제한 | **제한 없음 (전문)** | gpt-4.1 컨텍스트의 3-5% 수준, 비용 차이 ~$0.03, 잘라서 품질 떨어지는 게 더 비쌈 |
| 2 | 2차 수집 방법 | **Exa `find_similar(url)`** | 같은 이벤트 정확도 높음, 결과 없으면 원본 1개로 진행 |
| 3 | 소스 상한 | **최대 4개** | 원본 + 다른 시각 3개, 충분히 다각도이면서 과하지 않음 |
| 4 | 이벤트 판별 | **날짜 필터만 (48시간)** | find_similar 자체가 같은 이벤트를 찾아줌, 날짜 필터로 오래된 기사만 제외 |
| 5 | 대상 | **전체 (LEAD + SUPPORTING)** | 비용 차이 미미, SUPPORTING 품질도 향상 |

---

## 파이프라인 흐름 변경

### Before
```
collect → classify → community → rank → write(기사 1개 × 4000자)
```

### After
```
collect → classify → community → rank → enrich(2차 수집, 전체) → write(기사 1~4개 × 전문)
```

### 왜 rank 뒤에 enrich?
- rank까지 끝나야 어떤 아이템이 최종 생존하는지 확정
- 탈락한 아이템에 2차 수집하면 비용 낭비
- community는 rank 전에 필요 (ranking criteria에 community signal 포함)

---

## 구현 계획

### Task 1: `enrich_sources()` 함수 추가

**파일:** `backend/services/news_collection.py`

Exa `find_similar`로 각 아이템의 추가 소스를 수집하는 함수.

```python
async def enrich_sources(
    items: list[ClassifiedCandidate],
    raw_content_map: dict[str, str],
    max_sources: int = 4,
) -> dict[str, list[dict]]:
    """각 아이템에 대해 같은 이벤트의 추가 소스를 수집.

    Returns:
        {item_url: [{"url": ..., "title": ..., "content": ...}, ...]}
        원본 포함 최대 max_sources개.
    """
```

**핵심 로직:**
- 각 아이템 URL로 `exa.find_similar(url, num_results=max_sources-1)` 호출
- `start_published_date` = 2일 전, `end_published_date` = 오늘 (날짜 필터)
- `text=True`로 본문도 함께 수집
- 원본 URL은 제외 (`exclude_source_domain` 불필요 — 같은 매체의 다른 기사도 가치 있을 수 있음)
- 결과에 원본을 포함시켜 반환 (1차/2차 동등 취급)
- 병렬 호출 (`asyncio.gather`)로 latency 최소화
- API 실패 시 원본 1개만으로 graceful fallback

### Task 2: `_generate_digest()` Writer 입력 포맷 변경

**파일:** `backend/services/pipeline.py`

**변경 1:** `raw_content_map` → `enriched_sources_map` 사용

Before:
```python
body = raw_content_map.get(item.url, item.snippet)[:4000]
```

After:
```python
sources = enriched_map.get(item.url, [{"url": item.url, "content": raw_content_map.get(item.url, item.snippet)}])
```

**변경 2:** Writer 입력 포맷

Before:
```
### [LEAD] [llm_models] Article Title
Source URL (MUST cite this): https://...

{body — 4000자}
```

After:
```
### [LEAD] [llm_models] Article Title

Source 1: https://techcrunch.com/...
{content_1 — 전문}

Source 2: https://theverge.com/...
{content_2 — 전문}

Community Reactions (Reddit/HN):
{community}
```

**변경 3:** `[:4000]` 제한 제거

### Task 3: 파이프라인 오케스트레이션에 enrich 단계 삽입

**파일:** `backend/services/pipeline.py`

`generate_news_digest()` 함수에서 rank 후, write 전에 enrich 호출:

```python
# Stage: ranking
ranked = await rank_classified(classified_by_type, community_map)

# Stage: enrich (NEW)
enriched_map = await enrich_sources(ranked, raw_content_map)

# Stage: write (enriched_map 전달)
await _generate_digest(..., enriched_map=enriched_map, ...)
```

pipeline_logs에 enrich 단계 기록 추가 (소요 시간, 수집 소스 수).

### Task 4: 프롬프트 수정 — 다중 소스 citation

**파일:** `backend/services/agents/prompts_news_pipeline.py`

**Rule 1 (CITATION FORMAT) 수정:**
```
- News items: Cite ALL provided sources after the item title.
  Format: `### Item Title [1](URL1)[2](URL2)[3](URL3)`
```

**CHECKLIST 수정:**
- "Each news item cites all provided sources" 추가

### Task 5: 어드민 Pipeline Analytics에 enrich 단계 추가

**파일:** `frontend/src/pages/admin/pipeline-analytics.astro`

enrich 단계의 소요 시간, 수집된 추가 소스 수 표시.

### Task 6: 검증

- 파이프라인 1회 run
- 품질 평가: 다중 소스 반영 여부, citation 수, 분석 깊이
- 비용 확인: 예상 범위($0.28-0.29) 내인지

---

## Writer 입력 예시 (After)

```
### [LEAD] [llm_models] OpenAI releases GPT-5

Source 1: https://techcrunch.com/2026/03/30/openai-gpt5
OpenAI today announced GPT-5, its most powerful language model to date...
(전문 — 제한 없음)

Source 2: https://theverge.com/2026/03/30/openai-gpt5-launch
The Verge got early access to GPT-5 and found that pricing starts at...
(전문)

Source 3: https://openai.com/blog/gpt5
We're excited to introduce GPT-5, which achieves 92.3% on MMLU...
(전문)

Community Reactions (Reddit/HN):
**r/MachineLearning** (2.1k upvotes) — Impressed by MMLU jump but skeptical about reasoning claims
> "The benchmark numbers look great but I'd want to see independent eval" — u/ml_researcher
```

---

## 비용 영향 추정

| 단계 | 현재 | 추가 |
|------|------|------|
| 2차 수집 (Exa find_similar) | $0 | ~$0.005 (5건 × $0.001) |
| Writer 입력 토큰 증가 | ~$0.02 | ~$0.03 |
| **총 추가 비용** | | **~$0.03-0.04/run** |

현재 $0.25/run → **$0.28-0.29/run** (12-16% 증가)

---

## 위험 요소

1. **Exa `find_similar` 결과가 0개** — graceful fallback으로 원본 1개만 사용, 품질 저하 없음
2. **Writer 입력이 너무 길어짐** — gpt-4.1 컨텍스트 대비 미미하지만, 출력 품질에 영향 있는지 검증 필요
3. **같은 이벤트가 아닌 기사 혼입** — find_similar + 48시간 필터로 대부분 방지, 문제 시 LLM 판별 추가
4. **Exa API 장애** — 전체 enrich 단계 skip하고 기존 방식(원본 1개)으로 fallback
