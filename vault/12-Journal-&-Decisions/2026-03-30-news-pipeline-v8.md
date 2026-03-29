# 결정: AI 뉴스 파이프라인 v8 — 분류/랭킹 분리 + Research 프롬프트 리팩토링

> 날짜: 2026-03-30
> 맥락: v7(85.3점)에서 Research Expert 1문단 문제, CP 날조, Business 볼륨 부족을 진단하고 구조적 해결
> 세션: 2026-03-29~30 연속 작업 (20 커밋)

---

## 배경

v7에서 Business는 9점으로 안정됐지만 Research Expert가 지속적으로 짧은 문제가 있었다. 사용자 관점 심층 평가(7개 기준)를 수행하고, 근본 원인을 추적해 3가지 구조적 문제를 발견.

### 발견된 3가지 구조적 문제

**1. 분류와 랭킹이 분리되지 않음**
- 분류기가 "이 기사가 어디에 속하는가" + "중요도 점수"를 동시에 담당
- 점수가 피상적이라 Lead/Supporting 구분이 안 됨
- 글쓰기 LLM이 `Relevance: 85` 숫자를 보고 Lead를 알아서 판단해야 했는데, 5개 아이템 점수가 비슷하면 전부 동일 깊이로 작성

**2. Research Expert Guide에 "하지 마라"가 너무 많음**
- 569단어, DO:DONT = 2:1 (부정 지시 9개)
- Business Expert Guide: 201단어, DO:DONT = 4:1 → 9점
- "Do NOT explain basics" → LLM이 "짧게 써라"로 과해석 → 1문단 아이템
- "Skip a layer rather than hallucinate" → "4개 layer 다 생략해도 됨"으로 확대 해석

**3. Skeleton이 패턴을 제대로 보여주지 않음**
- 첫 아이템만 완전 작성, 나머지 `[3 paragraphs...]` placeholder
- LLM은 완전 작성된 아이템의 깊이만 따라가고, placeholder 아이템은 짧게 처리
- KO skeleton에 Open Source 섹션 누락, EN CP에 한국어 섞임

---

## 결정

### A. 파이프라인 구조 변경 — 분류/랭킹 분리

```
이전: 수집 → 분류 → 커뮤니티(상위3개) → 글쓰기
이후: 수집 → 분류 → 커뮤니티(전체) → ★랭킹 → 글쓰기
```

**rank_classified()** 함수 신규 추가 (`ranking.py`):
- gpt-4.1-mini로 카테고리별 5개 아이템을 비교 판단
- 출력: `{"lead": ["url1"], "supporting": ["url2", ...]}`
- 결과를 `item.reason`에 `[LEAD]`/`[SUPPORTING]` 태그로 저장
- 글쓰기 프롬프트 입력: `### [LEAD] [papers] AI Scientist-v2`

**모델 선택 의사결정:**
- 처음 o4-mini를 선택했으나, `response_format={"type": "json_object"}`를 지원하지 않아 빈 응답 반환
- `build_completion_kwargs()`가 o-series에서 response_format을 자동 제거하는 기존 로직 때문
- gpt-4.1-mini로 전환 — JSON 안정적, 비용 더 저렴($0.00007/call vs $0.001)
- 교훈: "추론 = o4-mini"라는 단순 매칭이 아니라 **JSON 호환성**을 먼저 확인해야 함

**커뮤니티 수집 확대:**
- 상위 3개만 → 분류된 전체 아이템(dedup 후 ~7-8개)으로 확대
- 랭킹 프롬프트에 engagement 메타데이터(upvotes, comments) 포함
- 비용: $0 (무료 API), 레이턴시: +2초 (병렬)

**커밋:** `d20f111`, `9b40ddd`

### B. Research Expert Guide 리팩토링

| | Before | After |
|---|---|---|
| 단어 수 | 569 | **151** |
| DO 지시 | 18 | **7** (핵심만) |
| DONT 지시 | 9 | **0** |
| Layered Reading | 별도 블록 (4줄 중 3줄이 부정문) | **제거** |
| Priority layers | 별도 블록 + 조건/예외 5개 | **인라인 4줄** |

제거한 것:
- "Do NOT spend paragraphs explaining the basic concept"
- "Not every item will have all 4 layers"
- "Skip a layer rather than hallucinate it"
- "Do NOT write action bullets, strategic decisions"
- "Keep market commentary minimal"
- "Do not drift into competitive strategy"

유지한 핵심:
- peer engineer 톤
- 4개 priority (prior work, benchmarks, limitations, practical signal) — 인라인으로
- 벤치마크 + baseline 비교 필수
- 약어 풀네임 첫 사용
- [LEAD]/[SUPPORTING] 연동 최소 3문단

**설계 원칙:** Business Expert가 201단어, "해라"만으로 9점을 내고 있으니, 같은 패턴을 Research에도 적용.

**커밋:** `61e7087`

### C. Skeleton 정밀화

**Research Expert skeleton 2nd item 완전 작성 (MARCH):**

기존: `[3 paragraphs with benchmarks and architecture details...]`
변경: 3문단 완전 작성 — prior work(SelfCheckGPT), benchmark(HaluEval 91.2%, GPT-4 대비 1/20 비용), 한계(3x 추론 지연)

**MinerU (1st item) 수정:**
- 문단 3: "전망" → "한계" (224px 해상도 제한, 추론 비용 미보고)
- baseline 추가: "3.2x faster" → "than autoregressive baselines (Nougat, GOT-OCR)"

**KO skeleton 수정:**
- Open Source & Repos 섹션 누락 → placeholder 추가
- MinerU KO도 EN과 동일 패턴으로 수정

**EN/KO 분리 버그 수정:**
- EN CP에 한국어가 섞여있던 실수 → 영어로 재작성

**커밋:** `69ecade`, `f5615f4`

### D. 기타 품질 개선

**Learner 최소 문단 통일 (2p → 3p):**
- "Learner가 짧아야 한다"는 편견 제거
- Learner는 설명이 더 필요하니 Expert 이상으로 길 수 있음
- skeleton placeholder `[2-3 paragraphs]` → `[3 paragraphs]`
- 품질 체크 "2-3 paragraphs" → "at least 3"
- 근본 원인: 규칙을 6곳에서 반복해도 skeleton과 품질 체크가 "2-3"이면 LLM이 2를 선택

**커밋:** `eaef808`, `1916f84`

**Learner 숫자 생략 금지:**
- "4배 빠르다"가 Expert에만 있고 Learner에 없었음
- "NEVER omit key numbers — simplify the explanation but the numbers must appear"

**커밋:** `1916f84`

**max_tokens 16K → 32K:**
- Business Expert가 Learner보다 짧았던 근본 원인: 토큰 예산 부족
- 상한 올려도 비용은 실제 사용량 기준이라 변하지 않음

**커밋:** `ae034f9`

**Exa 독립 수집기 승격:**
- Tavily quota 소진 시 Business 재료 부족 문제 해결
- Exa를 fallback에서 독립 수집기로 승격 (4개 비즈니스 쿼리)
- Exa API 변경 대응: `type="news"` → `type="auto", category="news"`
- Business 후보: Tavily 0건이어도 Exa에서 ~20건 확보

**커밋:** `b2ff44e`

**Community Pulse 분위기 요약 전환:**
- 스레드 제목만 전달 → 실제 댓글 텍스트 수집 (HN Algolia + Reddit JSON)
- 인용 강제 → 분위기 요약 중심 (메타데이터 기반)
- 무관한 서브레딧(r/Epstein, r/wallstreetbets) 필터링 → 38개 화이트리스트
- KO 인용 한국어 번역 필수

**커밋:** `d2b5f2e`, `55fc897`, `3e8d111`, `17bf0fe`, `b2e6282`, `7cf8401`

**Action Items 실행 가능성:**
- "팔로우하세요", "모니터링하세요" → action이 아님, 제외
- 구체적 action이 3개 미만이면 억지로 채우지 않기

**커밋:** `7548c06`

**태그 누출 후처리:**
- LLM이 `[LEAD]`/`[SUPPORTING]` 입력 태그를 출력 제목에 복사하는 버그
- 후처리에서 `[LEAD]`, `[SUPPORTING]`, `([LEAD])`, `([SUPPORTING])` 제거

**커밋:** pipeline.py에 포함

**핸드북 auto-extract admin 설정 버그:**
- 3개 경로에서 admin 설정을 무시하고 추출이 실행되던 문제
- DB 쿼리 실패 시 기본값: enabled → **disabled**로 변경
- `/cron/handbook-extract` 엔드포인트에 admin 설정 체크 추가

**커밋:** `3c9ada6`

---

## 품질 추이

| 날짜 | 파이프라인 | R Expert | R Learner | B Expert | B Learner | 평균 |
|------|-----------|----------|-----------|----------|-----------|------|
| 3/28 | v5 (baseline) | 72 | 80 | 78 | 74 | **76.0** |
| 3/19 | v6 peak | 85 | 86 | 88 | 87 | **86.5** |
| 3/26 v2 | v7 과교정 | 78 | 75 | 55 | 58 | **66.5** |
| 3/26 v3 | v7 롤백 후 | 86 | 83 | 85 | 87 | **85.3** |
| 3/28 (1p 문제) | v8 초기 | 75 | 65 | 90 | 90 | **80.0** |
| **3/28 최종** | **v8 완성** | **90** | **90** | **90** | **90** | **90.0** |

→ v5(76) → v7(85.3) → v8 초기(80, Research 하락) → **v8 최종(90, 전 항목 균등)**

---

## v8 최종 구성

### 파이프라인 흐름

```
6개 소스 병렬 (Tavily + HF Papers + arXiv + GitHub + Exa + Google RSS)
    | 50-60 candidates/day
    v
URL dedup + 발행 이력 제외 (3일) + Google News URL 해석 + 필러 필터
    v
분류 (gpt-4.1-mini) → Research 0-5개, Business 0-5개
    v
커뮤니티 수집 (HN Algolia + Reddit JSON) — 전체 분류 아이템, 38개 서브레딧 화이트리스트
    v
★ 랭킹 (gpt-4.1-mini) — Research/Business 각각, engagement 데이터 포함
    → [LEAD]/[SUPPORTING] 태그 부여
    v
글쓰기 (gpt-4.1, max_tokens=32K) — [LEAD] 3-4p, [SUPPORTING] 3p+
    v
후처리: bold fix + [LEAD]/[SUPPORTING] 태그 제거
    v
품질 체크 (o4-mini × 4) — R/B × Expert/Learner
    v
DB 저장 → Admin 확인 → 발행
```

### 프롬프트 구조

| 컴포넌트 | Research Expert | Business Expert |
|---|---|---|
| Guide 단어 수 | 151 | 201 |
| DONT 지시 | 0 | 1 |
| Skeleton 완전 작성 아이템 | 2개 (EN+KO) | 1개 (EN+KO) |
| KO skeleton | ✅ 있음 | ✅ 있음 |

### 비용

| 추가된 항목 | 모델 | 비용/run |
|---|---|---|
| 랭킹 × 2 | gpt-4.1-mini | $0.00014 |
| 커뮤니티 수집 확대 | 무료 API | $0 |
| Exa 수집 | Exa API | 크레딧 기반 |
| max_tokens 32K | gpt-4.1 | $0 (실사용 기준) |

---

## 교훈

### 1. "하지 마라"를 빼면 더 잘한다

Research Expert Guide에서 DONT 9개를 전부 제거했더니 **1문단 → 3문단**으로 개선. LLM은 "하지 마라"를 확대 해석해서 의도하지 않은 축소를 만든다.

Business Expert가 201단어, "해라"만으로 9점을 내는 게 증거. **규칙이 많다고 좋은 게 아니라, 핵심만 간결하게 말하는 게 효과적.**

### 2. 규칙과 skeleton이 충돌하면 skeleton이 이긴다

규칙을 6곳에서 "최소 3문단"이라고 해도, skeleton에 `[2-3 paragraphs]`가 있으면 LLM이 2문단을 선택한다. 품질 체크 프롬프트에서 "2-3 paragraphs = 25점"이면 역시 2문단을 정당화한다.

**규칙-skeleton-품질체크 3곳이 일관**되어야 LLM이 의도대로 동작한다.

### 3. 분류와 랭킹은 다른 작업이다

분류: "이 기사가 어디에 속하는가" — 카테고리 매칭
랭킹: "이 5개 중 뭐가 1등인가" — 비교 판단

한 호출에서 둘 다 하면 랭킹이 피상적이 된다. 분리하면 각각 더 잘한다. 비용은 $0.00014/run 추가.

### 4. o-series 모델의 JSON 제한을 알아야 한다

o4-mini에서 `response_format={"type": "json_object"}`가 작동하지 않는다. `build_completion_kwargs()`가 자동으로 제거하기 때문. 랭킹처럼 간단한 JSON 응답은 gpt-4.1-mini가 더 안정적이고 저렴하다.

### 5. 프롬프트 수정은 반드시 skeleton까지 검증해야 한다

Guide만 고치고 skeleton을 안 보면 불일치가 생긴다. EN skeleton에 한국어가 섞이거나, KO에 섹션이 누락되는 실수도 skeleton 검증으로 잡을 수 있다.

---

## 커밋 목록

| 커밋 | 내용 |
|------|------|
| `a4c73be` | 빈 섹션 placeholder 방지 강화 |
| `55fc897` | CP 관련 있는 인용만, 없으면 생략 |
| `b2ff44e` | Exa 독립 수집기 승격 |
| `d2b5f2e` | NQ-02 baseline + NQ-06 CP 분위기 + NQ-03+05+07 KO skeleton |
| `7548c06` | Action Items "팔로우" 금지 |
| `ae034f9` | max_tokens 32K + CHECKLIST 11 |
| `1916f84` | Learner 숫자 생략 금지 + 최소 3p 통일 |
| `d20f111` | 분류/랭킹 분리 + [LEAD]/[SUPPORTING] 태그 |
| `17bf0fe` | CP 인용 KO 번역 필수 |
| `3e8d111` | CP 인용 출처 `— Reddit` 필수 |
| `25a28a1` | 어드민 ranking/community 스테이지 추가 |
| `b2e6282` | 서브레딧 화이트리스트 21개 |
| `7cf8401` | 서브레딧 화이트리스트 38개 |
| `9b40ddd` | 랭킹 모델 o4-mini → gpt-4.1-mini |
| `eaef808` | skeleton/품질체크 "2-3p" → "3p" 통일 |
| `e64f83d` | Layered Reading 과해석 방지 |
| `61e7087` | **Research Expert Guide 리팩토링 569→151단어** |
| `69ecade` | Research Expert skeleton 2nd item 완전 작성 |
| `f5615f4` | skeleton 정확성 + EN/KO 분리 수정 |
| `3c9ada6` | 핸드북 auto-extract admin 설정 버그 |

## Related

- [[2026-03-29-news-pipeline-v7]] — 이전 세션 (수집 다변화, 품질 체크 4개)
- [[2026-03-25-research-news-quality]] — 최초 리서치 품질 문제 진단
- [[ACTIVE_SPRINT]] — NQ-08 done, NQ-09 todo (어제 발행 뉴스 중복 방지)
- [[2026-03-29-ranking-separation]] — 랭킹 분리 구현 계획
