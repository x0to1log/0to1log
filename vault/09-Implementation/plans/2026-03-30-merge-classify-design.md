# NQ-16 v2: Classify → Merge 분리 설계

> **상태:** 설계 확정
> **목표:** classify와 merge를 분리하여 과묶기 방지 + 1차 수집 데이터 최대 활용 + 외부 enrich는 보충만
> **이전 설계 (v1):** classify+merge 동시 → subcategory 기준 과묶기 반복 발생 (3/16 papers 10개, 3/30 papers 5개)

---

## v1 실패 원인

classify+merge를 한 호출에서 시키면 LLM이 "분류"와 "묶기"를 혼동.
subcategory가 같으면 ("papers") 전부 하나로 묶어버림.
✅/❌ 예시를 넣어도 반복 발생 — 프롬프트로 해결 불가능한 구조적 문제.

---

## v2 파이프라인 흐름

```
수집(50-60) → dedup(URL)
    ↓
★ classify (gpt-4.1-mini) — 개별 아이템 7-8개 선별 (v8 방식 복원)
    ↓
★ merge (gpt-4.1-mini) — 선별된 아이템 기준으로 전체 50개에서 같은 이벤트 매칭
    → 최종 4-5 그룹/카테고리
    ↓
community (HN/Reddit) — 그룹 내 모든 URL
    ↓
rank (gpt-4.1-mini) — 그룹 단위 LEAD/SUPPORTING
    ↓
외부 enrich (Exa find_similar) — 소스 부족 그룹만 보충
    ↓
write (gpt-4.1) → 후처리 → quality check → DB
```

---

## 핵심 변경: 3단계 분리

### Step 1: Classify (기존 v8 방식 복원)

- 50개 후보에서 **개별 아이템 7-8개** 선별
- 출력: 기존 flat format `[{url, subcategory, reason, score}]`
- merge 책임 없음 — 순수하게 "어떤 뉴스가 중요한가"만 판단
- 카테고리당 0-8개 (기존 0-5에서 확대 — merge 후 최종 5그룹 이하로 줄어듦)

### Step 2: Merge (신규 — 별도 LLM 호출)

입력: classify에서 선별된 7-8개 + **전체 50개 후보 목록**

역할:
1. 선별된 아이템끼리 같은 이벤트면 묶기
2. 탈락한 42-43개 중에서 선별된 아이템과 같은 이벤트인 기사를 찾아 해당 그룹에 소스로 추가

출력: `ClassifiedGroup` 리스트 (기존 모델 재활용)

```json
{
  "research": [
    {
      "group_title": "TurboQuant: LLM KV Cache Compression",
      "subcategory": "papers",
      "items": [
        {"url": "arxiv.org/turboquant", "title": "TurboQuant paper"},
        {"url": "blog.com/turboquant-explained", "title": "탈락했지만 같은 이벤트"}
      ]
    },
    {
      "group_title": "AI Scientist-v2",
      "subcategory": "papers",
      "items": [
        {"url": "arxiv.org/ai-scientist-v2", "title": "..."}
      ]
    }
  ]
}
```

핵심 규칙:
- 같은 **구체적 이벤트/발표**만 묶기 (같은 subcategory라는 이유로 묶지 말 것)
- 탈락 후보에서 매칭 못 찾으면 1개 아이템 그룹도 OK
- 그룹당 아이템 수 제한 없음 (같은 이벤트면 자연스럽게 2-4개)

### Step 3: External Enrich (기존 유지)

- 소스 1개뿐인 그룹만 Exa find_similar
- 소스 2개 이상 그룹은 스킵

---

## v1 대비 장점

| | v1 (동시) | v2 (분리) |
|---|---|---|
| 과묶기 | subcategory로 10개 묶기 반복 | classify가 개별 선별 → merge는 5-8개만 비교 |
| 1차 수집 활용 | classify 통과한 것만 | 탈락 후보도 merge에서 소스로 활용 |
| LLM 부담 | 50개 분류+묶기 동시 | classify: 50개 선별 / merge: 8개+50개 매칭 (각각 단순) |
| 비용 | 1회 호출 | 2회 호출 (+$0.001) |
| 디버깅 | classify가 왜 묶었는지 불투명 | classify/merge 각각 로그로 추적 가능 |

---

## 비용 추정

| 단계 | 모델 | 예상 비용 |
|------|------|----------|
| classify | gpt-4.1-mini | $0.003 (기존과 동일) |
| merge | gpt-4.1-mini | ~$0.002 (선별 8개 + 후보 50개 제목) |
| 기타 (rank, enrich, write, QC) | 기존과 동일 | ~$0.44 |
| **총 run** | | **~$0.45** (현재와 동일) |

---

## 수정 파일

1. `prompts_news_pipeline.py` — CLASSIFICATION_SYSTEM_PROMPT 복원 (v8 개별 포맷) + MERGE_SYSTEM_PROMPT 신규
2. `ranking.py` — classify_candidates() 복원 (ClassifiedCandidate 반환) + merge_classified() 신규 (ClassifiedGroup 반환)
3. `pipeline.py` — classify → merge → community → rank → enrich → write 순서
4. `models/news_pipeline.py` — ClassifiedCandidate 복원 (classify용) + ClassifiedGroup 유지 (merge 이후용)

---

## 구현 순서

1. CLASSIFICATION_SYSTEM_PROMPT를 v8 개별 포맷으로 복원 (그룹 출력 제거)
2. classify_candidates()를 ClassifiedCandidate 리스트 반환으로 복원
3. MERGE_SYSTEM_PROMPT 신규 작성 — 선별된 아이템 + 전체 후보 → ClassifiedGroup 출력
4. merge_classified() 함수 신규 — 별도 LLM 호출
5. pipeline.py에서 classify → merge 2단계 호출로 변경
6. rank/enrich/digest는 ClassifiedGroup 기반으로 기존 유지
7. ruff check + 테스트
