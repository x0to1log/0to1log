# NQ-16: 같은 주제 아이템 Merge + Classify 통합 설계

> **상태:** 설계 확정 대기
> **목표:** 1차 수집 결과에서 같은 이벤트/주제 기사를 묶어서 분류, Writer 입력 폭발 방지 + 다중 소스 자연 확보

---

## 현재 문제

1. **같은 이벤트가 별도 아이템으로 분류됨**
   - 3/22 Research: HuggingFace 관련 4개가 각각 별도 아이템 → 4 × 4소스 = 16소스 전문
   - 3/30 Research Expert: 입력 84K 토큰 → 출력 비정상 축소 (EN 3,744자, KO 1,749자)

2. **enrich가 이미 묶인 소스를 또 추가**
   - merge 없이 enrich만 하면 같은 이벤트 기사가 분산된 채 각각 추가 소스를 받음
   - 5 아이템 × 4 소스 = 20소스 → 입력 폭발

---

## 변경 후 파이프라인 흐름

### Before
```
수집(50-60) → dedup(URL) → classify(개별 10개) → community → rank → enrich(전체 × 4) → write
```

### After
```
수집(50-60) → dedup(URL) → ★merge+classify(그룹 단위) → community → rank → enrich(소스 부족한 그룹만) → write
```

---

## 핵심 변경: 분류기가 merge를 동시에 수행

### 현재 분류기 출력

```json
{
  "research": [
    {"url": "arxiv.org/nemotron", "subcategory": "papers", "reason": "...", "score": 85},
    {"url": "nvidia.com/nemotron-blog", "subcategory": "llm_models", "reason": "...", "score": 82},
    {"url": "github.com/huggingface/transformers", "subcategory": "open_source", "reason": "...", "score": 80},
    {"url": "ryzlabs.com/best-llms", "subcategory": "open_source", "reason": "...", "score": 75},
    {"url": "huggingface.co/viralsuite", "subcategory": "open_source", "reason": "...", "score": 70}
  ],
  "business": [...]
}
```

### 변경 후 분류기 출력

```json
{
  "research": [
    {
      "group_title": "Nemotron 3 Super: Hybrid Mamba-Transformer for Agentic AI",
      "subcategory": "llm_models",
      "reason": "Major open model release with novel architecture",
      "score": 85,
      "items": [
        {"url": "arxiv.org/nemotron", "title": "..."},
        {"url": "nvidia.com/nemotron-blog", "title": "..."}
      ]
    },
    {
      "group_title": "Hugging Face Ecosystem: Transformers v5.4 & Open Source LLM Rankings",
      "subcategory": "open_source",
      "reason": "Major framework release + community benchmarks",
      "score": 80,
      "items": [
        {"url": "github.com/huggingface/transformers", "title": "..."},
        {"url": "ryzlabs.com/best-llms", "title": "..."},
        {"url": "huggingface.co/viralsuite", "title": "..."}
      ]
    }
  ],
  "business": [...]
}
```

### 변경 포인트

- 개별 URL → **그룹 단위** (같은 이벤트/주제는 1개 그룹)
- `group_title`: 분류기가 묶으면서 대표 제목 생성
- `items`: 그룹에 속한 개별 기사 URL+제목 목록
- `subcategory`, `score`, `reason`은 그룹 단위로 부여
- 카테고리당 0-5 **그룹** (기존: 0-5 개별 아이템)

---

## 데이터 모델 변경

### 현재: ClassifiedCandidate (URL 1개)

```python
class ClassifiedCandidate(BaseModel):
    title: str
    url: str          # 1개
    snippet: str = ""
    source: str = "tavily"
    category: str
    subcategory: str
    relevance_score: float = 0.0
    reason: str = ""
```

### 변경: ClassifiedGroup (URL N개)

```python
class GroupedItem(BaseModel):
    """Individual item within a classified group."""
    url: str
    title: str

class ClassifiedGroup(BaseModel):
    """Group of related news items classified together."""
    group_title: str          # 대표 제목
    items: list[GroupedItem]  # 같은 이벤트의 기사들
    category: str             # "research" or "business"
    subcategory: str
    relevance_score: float = 0.0
    reason: str = ""

    @property
    def primary_url(self) -> str:
        """First item's URL (for community lookup, ranking compatibility)."""
        return self.items[0].url if self.items else ""

class ClassificationResult(BaseModel):
    research: list[ClassifiedGroup] = []
    business: list[ClassifiedGroup] = []
```

---

## enrich 조건부 실행

merge 후 그룹의 소스 수에 따라:

```python
async def enrich_sources(groups, raw_content_map, ...):
    for group in groups:
        if len(group.items) >= 2:
            # 이미 다중 소스 확보 → enrich 스킵
            continue
        # 소스 1개뿐 → Exa find_similar로 보충
        similar = exa.find_similar_and_contents(
            url=group.items[0].url, ...
        )
        group.items.extend(similar)
```

### 예상 효과

| 시나리오 | merge 전 enrich | merge 후 enrich |
|---------|----------------|----------------|
| GPT-5 출시 (3개 기사) | 3 × 4 = 12소스 | 이미 3소스 → enrich 스킵 |
| 마이너 논문 (1개 기사) | 1 × 4 = 4소스 | 1소스 → enrich 실행 → 3-4소스 |
| 총 API 호출 | 5회 | 1-2회 |

---

## Writer 입력 포맷 변경

### Before (개별 아이템)

```
### [LEAD] [llm_models] NVIDIA Nemotron 3 Super

Source 1: https://arxiv.org/...
{content}

---

### [SUPPORTING] [llm_models] NVIDIA Nemotron Blog Post

Source 1: https://nvidia.com/blog/...
{content}
```

### After (그룹 단위)

```
### [LEAD] [llm_models] Nemotron 3 Super: Hybrid Mamba-Transformer for Agentic AI

Source 1: https://arxiv.org/...
{content}

Source 2: https://nvidia.com/blog/...
{content}
```

같은 그룹의 소스가 하나의 `###` 블록 안에 모여서 Writer가 자연스럽게 교차 인용.

---

## downstream 영향 (변경 필요한 코드)

### 1. 프롬프트 (`prompts_news_pipeline.py`)
- `CLASSIFICATION_SYSTEM_PROMPT`: 출력 JSON 포맷 변경 (개별 → 그룹)
- merge 규칙 추가: "같은 이벤트/주제 기사는 하나의 group으로 묶어라"

### 2. 분류 함수 (`ranking.py`)
- `classify_candidates()`: 반환 타입 `ClassifiedCandidate` → `ClassifiedGroup`
- 파싱 로직: `items` 배열 처리

### 3. 랭킹 함수 (`ranking.py`)
- `rank_classified()`: 입력이 `ClassifiedGroup` 리스트로 변경
- LEAD/SUPPORTING을 그룹 단위로 판단

### 4. 파이프라인 (`pipeline.py`)
- `community_map`: 그룹의 primary_url 또는 전체 items URL로 수집
- `raw_content_map` 조회: 그룹 내 모든 items URL
- `enrich_sources()`: 조건부 실행 (소스 2개 이상이면 스킵)
- `_generate_digest()`: Writer 입력 포맷 변경 (그룹 → 다중 소스 블록)

### 5. 데이터 모델 (`models/news_pipeline.py`)
- `ClassifiedGroup`, `GroupedItem` 추가
- `ClassificationResult` 타입 변경

---

## 비용 영향 추정

| 항목 | 현재 | 변경 후 |
|------|------|---------|
| classify | $0.003 (동일) | $0.003 (merge 추가 부담 미미) |
| enrich | $0.005 (5회 호출) | $0.001-0.002 (1-2회만) |
| Writer 입력 | 84K 토큰 (Research) | ~45K 토큰 (그룹화 + 조건부 enrich) |
| Writer 비용 | $0.47 (Research) | ~$0.25 (40% 감소 추정) |
| **총 run** | **$0.77** | **~$0.50** |

---

## 구현 순서 (예상)

1. `GroupedItem`, `ClassifiedGroup` 모델 추가
2. `CLASSIFICATION_SYSTEM_PROMPT` 수정 (merge+classify 통합 출력)
3. `classify_candidates()` 파싱 로직 변경
4. `rank_classified()` 그룹 단위 입력 대응
5. `enrich_sources()` 조건부 실행
6. `_generate_digest()` Writer 입력 포맷 변경 (그룹 → 다중 소스)
7. `pipeline.py` 오케스트레이션 수정
8. 검증: 파이프라인 run + 품질/비용 확인

---

## 위험 요소

1. **분류기 과부하**: merge까지 시키면 출력 JSON이 복잡해져서 파싱 실패 가능
   → 대응: 기존 개별 포맷을 fallback으로 유지
2. **과도한 merge**: 관련 없는 기사를 묶을 위험
   → 대응: "같은 이벤트/발표"만 묶고, "같은 분야"는 묶지 않도록 프롬프트에 명시
3. **downstream 호환성**: ClassifiedCandidate를 쓰는 모든 코드 수정 필요
   → 대응: ClassifiedGroup에 호환 속성(primary_url, title) 유지
