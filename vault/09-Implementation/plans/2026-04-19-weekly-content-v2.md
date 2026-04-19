# Weekly Recap Content v2 — Editorial Lock + Quiz Addition

> 관련: [[2026-03-25-weekly-recap-design]] — v1 설계 (이 문서가 보강)
> 관련: [[2026-03-25-weekly-recap-plan]] — v1 구현 계획 (완료)
> 작성: 2026-04-19

---

## Goal

옵션 B(주 1회 catch-up 독자) 타겟에 맞춰 Weekly 콘텐츠 방향을 잠그고, 신규로 **Weekly 전용 퀴즈**(3문제, 한 주 전체, 페르소나별 분리)를 추가한다.

---

## 편집 결정 (확정)

| 항목 | 결정 | 비고 |
|---|---|---|
| 타겟 독자 | 옵션 B — 주 1회 catch-up | Daily 보는 독자는 부수 효과 |
| 콘텐츠 분량 | **풍부함 유지** | TOP 5-7 (2026-04-19 7-10에서 조정), 트렌드 3-4단락, 액션 모두 유지 |
| Amy 편집 톤 | 안 넣음 | 자동화 친화 우선 |
| 한국 로컬 앵글 | 안 넣음 | 글로벌 뉴스 한국어판 포지션 유지 |
| Weekly 퀴즈 | **신규 추가** | 3문제 / 한 주 전체 / 페르소나별 분리 |

**가설 검증 포인트(미래)**: read-through rate(끝까지 읽음) ≥ 50% — 추적 수단 미정.

상세 근거: 메모리 `project_weekly_editorial.md` 참조.

---

## Out of Scope (이번 작업에서 안 함)

- ~~TOP 뉴스 개수 축소 (5-6개) — 거부됨, 7-10 유지~~ → 2026-04-19 **5-7로 재조정** (catch-up 독자 과부하 방지 + 큐레이션 강도 ↑)
- "그래서 나는?" 섹션 변경 — 유지
- 트렌드 분석 분량 축소 — 유지 (현 3-4단락)
- 한국 기업/규제 맥락 추가 — 거부됨
- Amy 한 줄 코멘트 — 거부됨
- 공유 이미지 카드 — 별도 작업으로 분리
- read-through 분석 추적 — 별도 작업으로 분리
- 어드민 퀴즈 편집 UI — 자동화 친화 우선, 실제 문제 빈도 확인 후 추후 결정

---

## Chunk 1: Backend — Weekly Quiz 생성

### Task 1: Weekly 프롬프트에 퀴즈 출력 추가

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py`

**변경 내용:**
`WEEKLY_EXPERT_PROMPT`와 `WEEKLY_LEARNER_PROMPT`의 JSON 출력 블록에 `weekly_quiz` 필드 추가. 기존 `headline`, `week_numbers`, `week_tool` 옆에 같은 LLM 호출 안에서 함께 출력 (추가 호출 비용 0).

각 페르소나 프롬프트는 자기 관점에 맞는 퀴즈를 생성:
- **Expert**: 의사결정/임팩트 중심 — "이 흐름이 의미하는 바는?"
- **Learner**: 사실 확인/개념 학습 중심 — "이번 주 어떤 일이 있었나?"

JSON 스키마:
```json
{
  ...,
  "weekly_quiz": [
    {
      "question": "이번 주 OpenAI가 발표한 신규 모델의 이름은?",
      "options": ["GPT-4.5", "GPT-5", "GPT-o3", "GPT-Turbo"],
      "answer": "GPT-5",
      "explanation": "한 줄 설명 + 어느 데일리에서 다뤘는지"
    },
    { ... 2번째 ... },
    { ... 3번째 ... }
  ]
}
```

**프롬프트 추가 규칙 (Expert/Learner 공통)**:
- 정확히 3문제. 한 주 다이제스트 전체에서 출제.
- options는 정확히 4개. answer는 options 중 하나와 정확히 일치.
- 모든 문제는 데일리 다이제스트에 명시된 사실에서만. 추측/외부지식 금지.
- 3문제는 서로 다른 뉴스 항목을 다룰 것 (한 뉴스에서 3문제 출제 금지).
- 출력 언어는 본문과 동일한 locale.

**Expert 추가 가이드**:
- 단순 사실 암기보다 "왜 중요한가" 또는 "임팩트가 무엇인가"를 묻는 형식 우선.
- 예: "GPT-5의 추론 성능 40% 향상이 가장 직접적으로 영향을 주는 시장은?"

**Learner 추가 가이드**:
- 핵심 용어/사실 확인 위주. 정답 explanation에 배경 설명 1-2문장.
- 예: "Mixture of Experts(MoE)는 무엇인가?" + 해설에 "용어 → Handbook 링크" 안내 가능.

### Task 2: 파이프라인에서 퀴즈를 guide_items에 저장

**Files:**
- Modify: `backend/services/pipeline.py` — `run_weekly_pipeline` 함수 내 `guide_items` 빌드 부분

**변경 내용:**
```python
guide_items = {
    "week_numbers": expert_json.get("week_numbers", []),
    "week_tool": expert_json.get("week_tool") or learner_json.get("week_tool", {}),
    "week_terms": [...],  # 기존 그대로
    "weekly_quiz_expert": expert_json.get("weekly_quiz", []),  # NEW
    "weekly_quiz_learner": learner_json.get("weekly_quiz", []),  # NEW
}
```

**검증**: 빈 리스트 fallback. 퀴즈 생성 실패해도 본문 발행은 막지 않음.

### Task 3: 퀴즈 검증 가드 + 옵션 셔플

**Files:**
- Modify: `backend/services/pipeline.py` (Task 2와 같은 위치)

**참조**: Daily 퀴즈 셔플 로직 [pipeline_digest.py:902-911](../../../backend/services/pipeline_digest.py)

**변경 내용**: guide_items에 저장 직전에 (a) 검증 + (b) 옵션 셔플을 각 문제별로 적용.

```python
import random as _random

def _validate_and_shuffle_weekly_quiz(quiz_list: list) -> list:
    """Validate each question and shuffle its options.

    Drops invalid items (answer not in options, missing fields, etc.).
    Returns up to 3 valid items.
    """
    cleaned = []
    for q in (quiz_list or [])[:3]:
        if not isinstance(q, dict):
            continue
        question = q.get("question", "").strip()
        options = list(q.get("options", []))
        answer = q.get("answer", "").strip()
        explanation = q.get("explanation", "").strip()
        if not question or len(options) != 4 or answer not in options:
            logger.warning("Weekly quiz item dropped (invalid): %s", q)
            continue
        # Shuffle this question's options independently
        _random.shuffle(options)
        cleaned.append({
            "question": question,
            "options": options,
            "answer": answer,
            "explanation": explanation,
        })
    return cleaned

# Apply per persona
guide_items["weekly_quiz_expert"] = _validate_and_shuffle_weekly_quiz(
    expert_json.get("weekly_quiz", [])
)
guide_items["weekly_quiz_learner"] = _validate_and_shuffle_weekly_quiz(
    learner_json.get("weekly_quiz", [])
)
```

**가드 규칙 (드롭 조건)**:
- `options`가 정확히 4개 아닌 경우
- `answer`가 `options` 안에 없는 경우 (LLM 오류)
- `question` 비어있는 경우
- 4번째 이후 문제 (3개 초과 출제 시 잘라냄)

**셔플 규칙**:
- 각 문제의 options를 **독립적으로** 셔플 (`_random.shuffle()` 문제마다 호출).
- LLM이 정답을 자꾸 첫 번째/두 번째 위치에 배치하는 편향 방지 — Daily 퀴즈와 동일한 패턴.
- answer 문자열은 그대로 — 위치만 바뀌니까 매칭은 유지됨.

이유: 가벼운 가드. weekly run을 실패시키지 않음 — 퀴즈는 보너스 콘텐츠. 다만 셔플은 누락하면 사용자 경험에 직접 영향(정답 위치 패턴 노출)이라 필수.

---

## Chunk 2: Frontend — Weekly Quiz 렌더링

### Task 4: 페르소나 탭 전환에 따라 퀴즈 3문제 렌더링

**Files:**
- Modify: `frontend/src/components/newsprint/NewsprintArticleLayout.astro` (or wherever daily quiz is rendered)
- Modify: `frontend/src/lib/pageData/newsDetailPage.ts` — guide_items 파싱

**변경 내용:**
1. `post_type === 'weekly'`일 때 본문 하단 "이번 주 퀴즈" 섹션을 추가.
2. 활성 페르소나(`expert`/`learner`)에 맞춰 `weekly_quiz_expert` 또는 `weekly_quiz_learner` 리스트를 렌더.
3. Daily 퀴즈 렌더 컴포넌트가 단일 객체 기반이면, 리스트를 받아 반복 렌더링하는 wrapper 추가.

**UX 결정**:
- 모든 문제가 한 번에 보임 (아코디언 아님). catch-up 독자가 한 번에 다 풀고 끝낼 수 있게.
- 답 클릭 즉시 정답/해설 노출 (Daily와 동일).
- 3문제 다 풀면 "이번 주 catch-up 완료!" 같은 완료 표시 (선택, 추가 작업으로 분리 가능).

### (Deferred) 어드민 퀴즈 편집 UI

이번 작업에서 제외 — Amy 자동화 친화 우선. 실제로 이상한 퀴즈가 자주 나오는 게 확인되면 그때 추가.

---

## Chunk 3: Verification

### Task 6: 백필 테스트 + 셔플 단위 테스트

**E2E 백필 (LLM 호출 1회)**:
- 지난 주 weekly run 1회 재실행 (또는 새 주차 강제 실행)
- guide_items.weekly_quiz_expert / _learner 둘 다 3개씩 들어왔는지 확인
- answer가 options에 포함되는지 검증
- 프론트엔드에서 페르소나 탭 전환 시 퀴즈도 같이 바뀌는지 확인

**셔플 단위 테스트 (LLM 호출 0)**:
- `tests/test_weekly_quiz_shuffle.py` 신규
- `_validate_and_shuffle_weekly_quiz()`에 가짜 퀴즈 1000회 입력
- 정답 위치 분포가 4지선다 균등(각 ~25%, 허용 오차 ±5%p)인지 검증
- 잘못된 입력(answer ∉ options, options ≠ 4개) 드롭되는지 검증
- 비용 0, 결정론적, 회귀 방지에 더 적합

### Task 7: 비용/시간 회귀 체크

- Weekly 1회 실행 비용이 기존 ~$0.15에서 크게 늘지 않는지 (퀴즈 추가만으로 토큰 ~10% 증가 예상)
- 응답 시간 120초 timeout 안에 끝나는지

---

## DB

스키마 변경 없음. `news_posts.guide_items`(JSONB)에 새 필드만 추가.

---

## 비용 예상

| 항목 | v1 | v2 |
|---|---|---|
| 호출 수 | 4회 (페르소나 × 언어) | 4회 (변동 없음) |
| 토큰 증가 | — | 페르소나당 ~300 토큰 (퀴즈 출력) |
| 주간 총 비용 | ~$0.15 | ~$0.16~0.17 |

---

## 구현 태스크 요약

```
Chunk 1: Backend
  WEEKLY-V2-PROMPT-01  -> 프롬프트에 weekly_quiz 출력 (Expert/Learner 각각)
  WEEKLY-V2-PIPE-01    -> guide_items에 weekly_quiz_expert/learner 저장
  WEEKLY-V2-GUARD-01   -> 퀴즈 검증 가드 + 옵션 셔플 (Daily와 동일 패턴, 문제별 독립 셔플)

Chunk 2: Frontend
  WEEKLY-V2-FE-01      -> 본문 하단 퀴즈 3문제 렌더 + 페르소나 탭 연동

Chunk 3: 검증
  WEEKLY-V2-TEST-01    -> 백필 (LLM 1회) + 셔플 단위 테스트 (LLM 0회) + 비용 회귀
```

---

## Open Questions (별도 작업으로 분리)

1. **Read-through tracking**: 옵션 B 가설 검증을 위한 분석 도구. 스크롤 깊이 또는 머무는 시간 기반. 별도 plan 문서.
2. **퀴즈 완료 트리거**: 3문제 다 풀면 어떤 인터랙션? (배지, 통계, 다음 주 알림 등). 별도 작업.
3. **Daily 퀴즈와 차별성 검증**: Weekly 퀴즈가 실제로 Daily와 다르게 느껴지는지 — 첫 발행 후 2주 모니터링.

---

## Related

- [[2026-03-25-weekly-recap-design]] — v1 설계
- [[2026-03-25-weekly-recap-plan]] — v1 구현 계획
- 메모리: `project_weekly_editorial.md` — 편집 결정 근거
