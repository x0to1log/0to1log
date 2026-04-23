# AI 뉴스 파이프라인 개발 여정

> **프로젝트:** [0to1log](https://0to1log.com) — AI 뉴스 큐레이션 + AI 용어집 + IT 블로그 플랫폼
> **기간:** 2026년 2월 중순 – 4월 23일 (기획 2주 + 개발 50일)
> **역할:** 1인 풀스택 개발 (기획, 설계, 프론트엔드, 백엔드, AI, 인프라)
> **스택:** Astro v5 · FastAPI · Supabase · OpenAI (gpt-5) · Tavily · Exa · Brave · Vercel · Railway

---

## 한눈에 보기

7개 소스에서 매일 50–60건의 AI 뉴스를 수집하고, 같은 이벤트를 자동 그룹화한 뒤 분류·랭킹·다중 소스 보강·요약하여 2종의 다이제스트(Research + Business)를 Expert/Learner 페르소나로 발행하는 파이프라인. 50일간 12번의 버전을 거쳤고, v10에서 gpt-5 전환, v11에서 품질 평가 재설계, v12에서 효율성 혁신을 했다.

| | 시작 (v2) | v8 | v10 | v11 | 현재 (v12) |
|---|---|---|---|---|---|
| **Run당 비용** | $0.18 | $0.25 | $0.58 | $0.54 | **$0.33** |
| **모델** | gpt-4o | gpt-4.1 | gpt-5 | gpt-5 | gpt-5 (flex + cache) |
| **품질 평가** | 없음 | 4×25 단일점수 | 4×25 + 구조 감점 | 10 sub-score + evidence | **14-15 sub-score + schema enum** |
| **URL 환각 방지** | 없음 | 프롬프트 지시 | 프롬프트 지시 | URL liveness 검증 | **API schema enum (100%)** |
| **Prompt 캐시** | — | — | — | — | **52% 평균 적중** |
| **QC 재실행 비용** | 전체 $0.25 | 전체 $0.25 | 전체 $0.58 | QC만 $0.05 (-90%) | QC만 $0.02 (flex) |
| **품질 점수 (R/B)** | 75.8 / 82.9 | 91.8 / 94.8 | 96 / 91 | 76 / 93 | **89–97 안정** |

v2–v8까지 Run당 $0.18–$0.25로 품질을 9.3배 개선. v9에서 비용 폭발($0.77) → merge로 $0.43 복귀. v10에서 gpt-5 전환. v11에서 rubric 재설계 + 3-layer 소스 게이트 + QC 재실행 경로. v12에서 **비용 $0.33으로 34% 절감과 동시에 citation density 3–6x 회복** (schema enum으로 URL 환각 API 레벨 차단, flex tier + prompt cache 도입). 모든 수치는 프로덕션 DB 실측.

핵심 발견:
1. **"하지 마라"를 빼면 LLM이 더 잘한다.** Research Expert Guide를 569단어에서 151단어로 줄이고 DON'T 9개를 전부 삭제하자 아이템당 1문단이 3문단으로 늘어났다.
2. **LLM에게 한 번에 하나의 역할만 시켜야 한다.** 분류/랭킹(v8), classify/merge(v9), Writer/Summarizer(v10) 세 번의 검증. 분리할 때마다 정확도가 즉시 개선.
3. **입력의 질이 출력의 질을 결정한다.** "다양하게 써라"는 지시보다 실제로 다양한 소스를 넣어주는 게 근본 해결. merge로 중복 입력을 정리하자 비용 44% 감소, 품질 유지.
4. **reasoning 모델은 파라미터 체계가 다르다.** gpt-5에서 빈 응답이 나오면 버그가 아니라 추론 토큰이 출력 예산을 소진한 것. reasoning_effort=low + 3x 헤드룸으로 해결. **실제로 output의 60–72%가 reasoning 토큰** — body는 30–40%뿐.
5. **좋은 소스 필터링이 좋은 생성 프롬프트보다 중요하다.** 스팸/콘텐츠 팜/죽은 URL/포크 리포지토리를 enrich 단계에서 차단. Apr 19 사고의 13개 문제 URL 전량 차단. 품질은 Writer 튜닝이 아니라 입력 게이트에서 만들어진다.
6. **품질 노브를 올릴 때는 비용 노브도 같이 돌려라.** v12에서 `reasoning_effort=low → high`만 올리면 +72% ($0.50 → $0.86). `flex tier (-50%) + prompt_cache_key (-30%)`를 함께 적용하면 오히려 -34% ($0.33). 한 축만 조정하면 비용이 폭발한다.
7. **API schema enum은 프롬프트보다 100% 확실하다.** URL 환각을 프롬프트로 막으면 85–97% 준수, `json_schema` + `citations[].url: enum`으로 강제하면 API가 서버에서 거부 → 100%. 프롬프트가 안 통할 땐 스키마로 올려라.

---

## 목차

1. [프로젝트 개요와 아키텍처](#1-프로젝트-개요와-아키텍처)
2. [정량적 결과](#2-정량적-결과)
3. [핵심 의사결정과 교훈](#3-핵심-의사결정과-교훈)
4. [뉴스 파이프라인의 진화](#4-뉴스-파이프라인의-진화)
5. [핸드북 파이프라인](#5-핸드북-파이프라인)
6. [기술 스택](#6-기술-스택)

---

## 1. 프로젝트 개요와 아키텍처

0to1log는 AI/IT 분야의 최신 소식을 자동으로 수집·분류·요약하여 매일 발행하는 뉴스 큐레이션 플랫폼이다. 뉴스에서 등장하는 AI 용어를 자동 추출하여 용어집(Glossary)으로 축적하고, 독자의 수준에 맞춰 Expert/Learner 두 가지 페르소나로 콘텐츠를 제공한다.

실제 다이제스트는 [0to1log.com](https://0to1log.com)에서 확인할 수 있다.

### 왜 이 프로젝트를 만들었나

AI 뉴스는 매일 쏟아지지만, 한국어로 된 양질의 기술 브리프는 드물다. 뉴스 사이트들은 보도자료를 그대로 옮기거나, 기술적 맥락 없이 제목만 나열한다. "리서치 엔지니어가 출근길에 읽을 만한 AI 브리프"와 "AI를 처음 접하는 사람도 이해할 수 있는 해설" — 이 두 가지를 하나의 플랫폼에서 자동으로 제공하고 싶었다.

### 현재 파이프라인 아키텍처

```
+-----------------------------------------------------------------------+
| 수집 — 7개 소스 병렬                                                   |
| Tavily | HuggingFace | arXiv | GitHub | Google RSS | Exa | Brave     |
+-----------------------------------------------------------------------+
    | 50-60건/일
    v
중복 제거 + 필터 (URL 중복, 발행 이력 3일, 카테고리 페이지, 필러)
    v
분류 (gpt-5-mini) --> Research 0-5 / Business 0-5 (개별 아이템)
    v
Merge (gpt-5-mini) --> 같은 이벤트 기사 그룹화 ($0.002)
    v
커뮤니티 수집 (HN Algolia + Brave Discussions)
    v
커뮤니티 요약 (gpt-5-mini) --> sentiment + quotes(EN/KO) + key_point
    v
랭킹 (gpt-5-mini) --> [LEAD] / [SUPPORTING] (그룹 단위)
    v
조건부 소스 보강 (Exa find_similar — 소스 1개뿐인 그룹만)
    + 소스 품질 게이트 (스팸 / 콘텐츠 팜 drop, 원본 repo > fork)
    v
+-- Research 다이제스트 -------+   +-- Business 다이제스트 -------+
|  Expert EN+KO (gpt-5 flex)  |   |  Expert EN+KO (gpt-5 flex)  |
|  Learner EN+KO (gpt-5 flex) |   |  Learner EN+KO (gpt-5 flex) |
|  + JSON schema: citations[] |   |  + JSON schema: citations[] |
|    url: enum [allowlist]    |   |    url: enum [allowlist]    |
|  + prompt_cache_key (52% ↑) |   |  + prompt_cache_key (52% ↑) |
+------------------------------+   +------------------------------+
    v
후처리 (bold fix + 태그 제거 + [CITE_N] → [N](URL) 치환)
    v
품질 검사 (gpt-5 flex x 4: R/B x Expert/Learner)
    + 14-15 sub-score + evidence (LLM), 총점 aggregate (코드)
    + 코드 감점 (CP 누락 -15, 구조 불일치 -5)
    + Health Check (분류 0건, 과묶기, 수집 실패 감지)
    v
draft 저장 --> 관리자 확인 --> 발행
    |
    v (조건부)
핸드북 용어 자동 추출
```

---

## 2. 정량적 결과

아래 모든 수치는 프로덕션 데이터베이스에서 측정한 실측 데이터이다 (비용: `pipeline_logs`, 품질: `news_posts`).

### Run당 비용 (pipeline_logs, 실패 run 제외)

| 구간 | Run 수 | 평균 비용/run | 범위 | 핵심 변화 |
|------|--------|-------------|------|----------|
| v2–v4 | 13 | **$0.18** | $0.13–$0.21 | 단일 소스, 4000자 제한 |
| v5–v6 | 10 | **$0.20** | $0.11–$0.28 | 4소스 + 스켈레톤 맵 |
| v7–v8 | 4 | **$0.25** | $0.20–$0.27 | 랭킹 분리 + DON'T 제거 |
| v9 초기 | 3 | **$0.62** | $0.46–$0.77 | 다중 소스 종합 (입력 폭발) |
| v9 + merge | 4 | **$0.43** | $0.32–$0.52 | merge로 입력 중복 제거 (v8 수준 복귀) |
| v10 (gpt-5) | 6 | **$0.58** | $0.51–$0.64 | gpt-5 전환 + CP Summarizer + 코드 감점 |
| v11 | 측정 중 | **$0.54** | — | Rubric v2 + 소스 게이트 + rerun=quality ($0.05) |
| v12 초기 (high only) | 1 | $0.86 | — | reasoning_effort=high만 적용 (+72%, 교훈) |
| v12 최종 (flex+cache) | 1 | **$0.33** | — | flex tier + prompt_cache + liveness 제거 (-34%) |

### 품질 추이 (news_posts, EN, Research/Business 분리)

| 지표 | | v2–v4 | v5–v6 | v7–v8 | v9 | v10 | v11 | v12 |
|------|---|-------|-------|-------|-----|-----|-----|-----|
| **품질 점수** | Research | 75.8 | 92.2 | 91.8 | 94 | 96 | 76 | **90–97** |
| | Business | 82.9 | 94.1 | 94.8 | 95 | 91 | 93 | **89–95** |
| **Expert citation** | Research | 1.8 | 12.9 | 16.8 | 17.5 | 17.5 | 17.5 | **30** (peak) |
| | Business | 2.7 | 13.9 | 14.2 | 20.5 | 20.5 | 20.5 | 21 |
| **Run당 비용** | 전체 | $0.18 | $0.20 | $0.25 | $0.43 | $0.58 | $0.54 | **$0.33** |

*품질 점수는 자동 LLM 평가 (100점 만점). v5부터 4개 페르소나별 평가로 전환하여 기준이 더 엄격해졌음에도 점수가 상승. **v11의 점수는 rubric 아키텍처 자체가 바뀌었기 때문에 v10 이전과 직접 비교 불가** — 10 sub-score + evidence 구조로 재설계되면서 점수 분포가 다르다. v12는 v11 rubric을 14–15 sub-score로 확장 + schema enforcement로 3일 평균 92.7점(89–97 안정).*

**요약:** v2–v8까지 $0.18–$0.25로 citation 9.3배 달성. v9에서 $0.77 폭발 → merge로 $0.43 복귀. v10에서 gpt-5 전환. v11에서 rubric 재설계 + 소스 게이트 + QC 재실행 경로. **v12에서 schema enum으로 URL 환각 API 레벨 차단, flex tier + prompt cache로 $0.33 (-34%), citation density 3–6x 회복.** 품질과 비용을 동시에 개선한 사례.

### 프롬프트 반복 이력 (12회)

| 반복 | 점수 | 핵심 변경 | 키워드 |
|------|------|----------|--------|
| v1 | **56** | 13개 작성 규칙 나열 | 규칙 무시 |
| v2 | **48** | gpt-4o A/B 테스트 | 모델 아닌 프롬프트 |
| v3 | **75** | Few-shot 스켈레톤 1개 | 예시 > 규칙 |
| v4 | **84** | KO 스켈레톤 + 구조 동등성 | 구조로 KO 검증 |
| v5 | **84** | 4소스 + 품질 체계 | 소스 다변화 |
| v6 | **90** | 페르소나별 스켈레톤 4개 | 스타일 오염 방지 |
| v7 | **85.3** | 사용자 관점 평가 + 롤백 | 변경 누적 = 회귀 |
| v8 | **90.0** | DON'T 제거 | 과교정 제거 |
| v9 | **95** | 다중 소스 + merge + citation 코드화 | 비용 폭발 → merge로 복구 |
| v10 | **96** | gpt-5 전환 + CP 재설계 + 코드 감점 | reasoning 모델 마이그레이션 |
| v11 | **재측정** | 10 sub-score + 소스 게이트 + rerun=quality | LLM/코드 역할 재분리 |
| v11.1 | **95/100** | Writer-QC 미러 동기화 + Phase 2a 측정 | QC와 Writer는 쌍으로 변경 |
| v12 | **89–97 안정** | Schema enum + flex + cache, liveness 제거 | 비용 -34% + citation 3–6x 회복 |

---

## 3. 핵심 의사결정과 교훈

### 의사결정

**4-Tier 모델 구조 (v10, gpt-5 전환 후)**

| 티어 | 모델 | 용도 |
|------|------|------|
| Main | gpt-5 | 다이제스트 생성, Weekly Recap |
| Light | gpt-5-mini | 분류, merge, 랭킹, CP 요약 |
| Nano | gpt-5-nano | 핸드북 경량 작업 |
| Reasoning | gpt-5-mini | 품질 평가, 팩트체크 |

**모델 전환 이력:** gpt-4o(v1–v4) → gpt-4.1(v5–v9, IFEval +6%, 비용 -20%) → gpt-5(v10, reasoning 모델 전환). gpt-5는 reasoning 모델이라 파라미터 체계가 다르다 — max_tokens → max_completion_tokens, temperature 미지원, 추론 토큰이 출력 예산을 소진하면 빈 응답. reasoning_effort=low + 3x 헤드룸으로 해결. `.env`에서 모델명만 바꾸면 코드 변경 없이 전환/롤백 가능하도록 설계.

**Draft-First 원칙**

> "콘텐츠 품질로 파이프라인을 멈추지 않는다. 인프라 에러만 재시도."

품질이 기준 미달이면 draft로 저장하고 admin이 확인한다. 파이프라인 자체는 절대 멈추지 않는다. 이 원칙이 v1에서 v2로의 가장 큰 아키텍처 변화였다.

**품질 평가 설계 — 3개 레이어**

Draft-First로 파이프라인을 멈추지 않는 대신, 품질을 3개 레이어로 추적한다.

**레이어 1 — LLM 자동 평가 (v12: 14–15 sub-score + evidence + schema enum)**

페르소나별 4개 기준 × 25점 체계로 시작했지만, v11에서 **10 sub-score (각 0–10) + 각 점수마다 근거 서술** 구조로 재설계. v11.1에서 `claim_calibration` + `temporal_anchoring` + `internal_consistency` 추가로 14–15개로 확장. LLM은 sub-score와 근거만 제공하고, **총점은 코드가 합산**한다.

| 페르소나 | sub-score 수 | 주요 차원 |
|----------|------------|---------|
| Research Expert | 14 | section_completeness, source_quality, technical_depth, locale_integrity, claim_calibration, temporal_anchoring, internal_consistency, ... |
| Research Learner | 14 | section_completeness, accessibility, source_quality, locale_integrity, ... |
| Business Expert | 15 | + claim_coverage (focus_items 평가형 문구 금지) |
| Business Learner | 14 | section_completeness, accessibility, actionability, locale_integrity, ... |

**왜 LLM이 총점을 계산하지 않는가:** LLM은 qualitative 평가에는 강하지만 산수에 약하다. 정성 평가와 arithmetic을 분리하면 각각 더 정확해진다. `locale_integrity`는 v11에서 severity 마커에서 explicit sub-dimension으로 승격 — Apr 19 사고(KO 다이제스트에 영어 인용만, 96점) 재발 방지.

**4개 QC 경로 완전 통일:** body / frontload / weekly / handbook이 모두 같은 rubric 구조를 사용하여 parity 확보.

**v12 schema enum 강제:** Writer 출력이 OpenAI strict `json_schema`로 제약 — `citations[].url`을 fact_pack allowlist의 enum으로 한정. **API가 서버에서 잘못된 URL을 거부**하므로 URL 환각은 프롬프트가 아닌 스키마 레벨에서 100% 차단. v11의 URL liveness HEAD check는 false positive 70–85%로 citation 90%를 잘못 drop시켜 제거됨 — schema enum이 더 정확한 해결책.

**레이어 2 — 코드 기반 소스 게이트 + 구조 검증 + 감점**

LLM 채점 전후로 코드가 3가지를 담당한다.

**2a. 소스 품질 게이트 (v11, 수집 단계):**
- **Source quality gate** — 스팸 tier / content farm (introl.com, neuraplus-ai.github.io 등) drop
- **Authority rule** — GitHub 원본 repo > fork/mirror (CoT + few-shot으로 판단)
- **URL liveness** — HEAD 요청으로 404/410/DNS 실패/잘못된 redirect drop

Apr 19 사고의 13개 문제 URL 전량 차단. 좋은 품질은 Writer 튜닝이 아니라 **입력 게이트**에서 만들어진다.

**2b. 생성 후 구조 감점:**

최종 점수 = LLM aggregate 점수 - 코드 감점(최대 -30)

CP 데이터 있는데 섹션 누락: -15, EN/KO 섹션 불일치: -5, 빈 citation: -5, Supporting 3문단 미만: -5/item.

**2c. Health Check:** 분류 0건, merge 과묶기(5+ 아이템), 커뮤니티 수집 0건, enrich 실패. 경고를 기록하되 파이프라인을 차단하지 않는다.

**레이어 3 — 사람의 최종 판단**

자동 발행은 의도적으로 미구현했다. 점수와 Health Check 결과는 admin 대시보드에 표시되고, 최종 발행 판단은 사람이 한다.

**왜 LLM이 LLM을 평가하는가:** 자체 평가의 한계를 알고 있다 — v7에서 자동 90점이었지만 사용자 관점은 76점이었다. 하지만 일관된 기준으로 매일 자동 측정하여 **추세를 추적**하는 데 가치가 있다. 절대 점수보다 변화 감지가 목적이다.

핸드북 파이프라인에도 동일한 철학을 적용했다: Self-Critique(생성 중 score < 75 → 재생성) + Quality Check(깊이/정확성/고유성/완성도, < 60 → 경고). 뉴스와 핸드북 모두 "자동으로 측정하되, 최종 판단은 사람이" 원칙.

**0-5 룰**

Research 카테고리에 적합한 뉴스가 없으면 **빈 리스트를 허용**한다. "3–5건 선택"이라는 강제 할당량이 품질을 오히려 떨어뜨렸다 — 기준 미달 기사를 억지로 채워넣게 되기 때문이다.

**rerun_from=quality — QC만 재실행하는 경로 (v11)**

프롬프트 튜닝 시 매번 Writer부터 다시 돌리면 run당 $0.54. QC 프롬프트만 조정할 때는 Writer 결과를 재사용하고 품질 평가만 재실행하는 경로를 추가. **run당 $0.05 (10배 절감).**

**왜 중요한가:** 프롬프트 엔지니어링은 반복 비용이 쌓이는 작업이다. 반복 비용을 1/10로 줄이면 실험 빈도가 10배가 된다. 저비용 rescore 경로 없이는 rubric v2 같은 대규모 프롬프트 재설계 자체가 경제적으로 비쌌다.

**비용 절감을 위해 검토했지만 채택하지 않은 것들 (v5–v8 시기)** — 비용을 줄이는 것보다 품질을 지키는 게 더 중요한 경우가 있었다.

| 고려한 것 | 결정 | 이유 |
|-----------|------|------|
| 분류에 경량 모델 사용 | 미채택 | 약 $0.03/일 절감이지만 분류 품질 리스크 |
| 품질 체크 제거 | 미채택 | 약 $0.004/일 절감이지만 자동 발행의 선행 조건 |
| 핸드북 Self-Critique 제거 | 미채택 | 약 $0.02/용어 절감이지만 품질 하한선 보장 필요 |

### 교훈

**품질 기준이 내려가면 아키텍처가 잘못된 것이다.** v1에서 품질 기준을 5,000자 → 3,500자 → 2,500자로 낮추고 있었다. 이 시점에서 멈추고 재설계해야 했다. v2에서 아키텍처를 바꾸자 v1의 400줄 방어 코드가 전부 불필요해졌다.

**"하지 마라"를 빼면 LLM이 더 잘한다.** Research Expert Guide의 DON'T 9개를 전부 삭제했더니 아이템당 1문단 → 3문단. Business Expert Guide가 201단어, DONT 0개로 90점을 내고 있었다 — 같은 패턴을 적용한 것.

**스켈레톤이 규칙을 이긴다.** "최소 3문단"을 6곳에 적어도, 스켈레톤에 `[2-3 paragraphs]`가 있으면 LLM이 2문단을 선택한다. 규칙, 스켈레톤, 품질 체크 3곳이 일관되어야 의도대로 동작한다.

**프롬프트 변경은 한 번에 하나씩.** v7에서 3가지 변경을 한 커밋에 넣었더니 점수가 86.5 → 66.5로 폭락. "롤백 후 선별 재적용"이 "패치 위에 패치"보다 안전하다.

**프롬프트의 예시는 중립적이지 않다.** Citation 형식 예시에 빈 괄호 `[](URL)`를 넣었더니 4개 페르소나 중 3개가 citation을 완전히 생략. `[1](URL)`로 복원하자 즉시 정상화. LLM은 예시의 패턴을 문자 그대로 따른다.

**LLM의 한계를 인정하고 코드로 보완.** 핸드북 용어 링크는 프롬프트로 시키면 정확도 약 70%, 코드 후처리는 100%. Citation 넘버링도 LLM이 섹션마다 리셋하는 문제를 코드로 전환하여 100% 정확.

**한 호출에 두 가지 작업을 결합하면 두 작업 모두 정확도가 떨어진다.** 분류/랭킹(v8), classify/merge(v9), Writer/Summarizer(v10)에서 세 번 반복 검증 — 각각 분리하면 둘 다 잘하고, 합치면 둘 다 부정확해진다.

**reasoning 모델은 파라미터 체계가 다르다.** gpt-5에서 빈 응답이 나오면 버그가 아니라 추론 토큰이 출력 예산을 소진한 것. reasoning_effort=low + 3x 헤드룸이 해결책. system에 데이터를 넣으면 무시하므로 system=규칙, user=데이터로 분리해야 안정적.

**채점 모델이 바뀌면 점수 기준이 깨진다.** 같은 콘텐츠를 gpt-4.1-mini(85점)와 gpt-5-mini(36점)가 전혀 다르게 채점. calibration 지시와 content 잘림 한도를 반드시 조정해야.

**LLM에게 산수를 맡기지 말라.** Rubric v2에서 10 sub-score 합산을 코드로 이관. LLM은 qualitative 평가에 강하고 코드는 arithmetic에 정확 — 둘을 섞으면 LLM이 정성 평가에 산수까지 얹으면서 둘 다 불안정해진다. 역할을 분리하는 게 각각을 더 잘하게 만든다.

**구조 검증과 도달 가능성은 다르다.** URL이 올바른 문자열 형식이어도 실제로 도달 가능한지는 별개. HEAD 요청으로 실제 라이브 여부를 확인하는 gate가 필요하다. Apr 19 사고의 13개 문제 URL 중 상당수가 형식상 정상이었다.

**Rubric 아키텍처를 바꾸면 점수 추이가 끊어진다.** v10의 85점과 v11의 85점은 직접 비교 불가 — 자동 발행 threshold도 재보정 필요. 추세 추적이 평가 시스템의 목적일 때, rubric 변경은 단절 지점을 만든다는 것을 인지하고 설계해야.

**API schema enum은 프롬프트보다 확실하다.** URL 환각을 프롬프트로 막으면 85–97% 준수, OpenAI strict `json_schema` + `citations[].url: enum`으로 강제하면 API가 서버에서 거부 → 100%. 프롬프트가 안 통할 땐 스키마로 올려라 — "LLM에게 시킬 것 vs 코드에게 맡길 것"의 경계를 넘어 "API에게 강제할 것"이라는 세 번째 레이어.

**False positive가 정확도보다 비쌀 수 있다.** v11에서 추가한 URL liveness HEAD 체크가 70–85% false positive → citation 90% 손실. v12에서 제거하는 게 해결책이었다. 검증 시스템의 **오탐률**은 탐지율 못지않게 중요 — 추가가 항상 답이 아니다.

**품질 노브를 올릴 때는 비용 노브도 같이 돌려라.** v12에서 `reasoning_effort=low → high`만 올리면 $0.50 → $0.86 (+72%). `flex tier (-50%) + prompt_cache_key (-30%)`를 함께 적용하면 오히려 $0.33 (-34%). 한 축만 조정하면 비용이 폭발한다. **개별 knob 튜닝 사고방식의 함정**: "이번에 품질 노브 올리고, 다음에 비용 노브 돌리자"는 접근이 일반적이지만 중간 상태가 배포되면 과금 폭탄 + 롤백 압박 → 품질 성과까지 되돌려야 함. **품질과 비용 변경은 반드시 같은 릴리스에 패키지**하고, 최소한 staging에서 통합 검증한 뒤 프로덕션에 올려야 한다.

**구조적 enforcement를 rubric 상승 앞에 둬라.** Rubric bar를 한 달간 지속적으로 올렸는데 점수가 89–97 안정 유지. 이유: schema + code validation으로 bottom-line을 먼저 고정했기 때문. 반대 순서 (rubric만 먼저 올리기)는 점수 롤러코스터.

---

## 4. 뉴스 파이프라인의 진화

### 한눈에 보는 버전 히스토리

```
v1 ████████████████████████████████████████ 5일 (근본 원인 발견)
v2 ████████                                 1일 (성공)
v3 ████                                     반나절 (성공)
v4 ██                                       반나절 (성공)
v5 ████████████████                         8일 (안정화)
v6 ██                                       1일 (최적화)
v7 ████████                                 2일 (품질 전면 리팩토링 + 롤백)
v8 ████████                                 2일 (구조 분리)
v9 ████                                     1일 (다중 소스 종합)
v10 ██████████████████████████               7일 (gpt-5 전환 + CP 재설계)
v11 ████████████████████████████████████████████████████  15일 (rubric v2 + 소스 게이트)
v11.1 ████                                                1일 (Writer-QC 미러)
v12  ████                                                 1일 (schema enum + flex + cache)
```

| | v1 | v2–v4 | v5–v6 | v7–v8 | v9 | v10 | v11 | v12 |
|---|---|---|---|---|---|---|---|---|
| **기간** | 3/10–14 | 3/15–17 | 3/18–26 | 3/28–30 | 3/30 | 3/31–4/6 | 4/7–4/22 | 4/23 |
| **결과** | 근본 원인 발견 | 동작 → 안정 | 안정화 + 최적화 | 품질 개선 + 분리 | 다중 소스 + merge | gpt-5 + 코드 감점 | Rubric v2 + 소스 게이트 | schema enum + flex + cache |
| **모델** | gpt-4o | gpt-4o | gpt-4.1 | gpt-4.1 | gpt-4.1 | gpt-5 | gpt-5 | gpt-5 flex |
| **비용/run** | N/A | $0.13–0.17 | $0.20 | $0.25 | $0.43 | $0.58 | $0.54 | **$0.33** |
| **품질 평가** | 없음 | 없음 | 4×25 | 4×25 + 구조 감점 | 4×25 + 구조 감점 | 4×25 + 구조 감점 | 10 sub-score + evidence | 14–15 sub-score + schema enum |

---

### v1: 근본 원인 발견 (3/10–14, 5일)

첫 5일간 발행 가능한 결과물은 나오지 않았다 — 하지만 시스템을 직접 만들고 테스트하지 않았으면 보이지 않았을 세 가지 아키텍처 결함을 발견했다. 이 결함 각각이 v2의 설계 요구사항이 되었다.

초기 전략은 단순했다: 뉴스 1건을 선택해서 영어로 심층 분석을 쓰고, 한국어로 번역하고, 3개 페르소나(전문가/중급/초급)로 변환한다.

5일 동안 일어난 일:

**1일차–2일차:** 기본 파이프라인 구현. LLM이 5,000자 이상의 글을 안정적으로 생성하지 못하는 문제 발견. 재시도 로직을 추가했다.

**3일차:** EN→KO 번역 시 길이가 50–70%로 줄어드는 문제. 번역 프롬프트에 "원문과 동일한 길이로" 지시를 추가했지만 효과 없음. 품질 기준을 5,000자에서 3,500자로 낮췄다.

**4일차:** 간헐적 JSON 파싱 실패. artifact/resume 시스템을 구현해서 중간 실패 시 이어서 생성할 수 있게 했다. pipeline.py가 979줄에서 1,346줄로 불어났다. 방어 코드만 400줄 이상.

**5일차:** 품질 기준을 2,500자까지 낮췄다. 원래 목표의 50%. 여기서 멈추고 전체를 삭제했다.

**근본 원인:** 잘못된 아키텍처 위에 패치를 쌓고 있었다. KO 번역 길이가 부족하면 품질 기준을 낮추고, LLM이 긴 글을 못 쓰면 재시도 로직을 추가하고, 중간에 실패하면 artifact/resume 시스템을 만들었다 — 모두 증상에 대한 패치였다. 진짜 원인은 순차 번역 구조, 1회 호출 전체 생성, hard validation이었다.

**발견의 비용:** LLM 호출 $15–25(추정), 발행 가능한 결과물 0. 하지만 여기서 발견한 세 가지 근본 원인 — 순차 번역, 단일 호출 생성, hard validation — 이 v2의 정확한 설계 요구사항이 되었다. 이 단계 없이 v2의 "하루 만에 완성"은 불가능했다.

---

### v2: 근본 원인을 해결하니 코드가 줄었다 (3/15, 1일)

v1의 세 가지 근본 원인을 직접 공격했다: 순차 번역을 **EN+KO 동시 생성**으로 대체하고, 1회 호출 전체 생성을 **팩트 추출 → 페르소나별 분리 생성**으로 바꾸고, hard validation을 **draft 저장** 방식으로 전환했다.

**왜 이 방식을 선택했나:** 대안은 EN→KO 번역 프롬프트를 개선하는 것이었다 — 길이 제약 추가, 짧은 출력 시 재시도 등. 하지만 근본 원인은 아키텍처에 있었다: 번역은 본질적으로 내용을 손실시킨다. 같은 FactPack에서 두 언어를 동시에 생성하면 문제 자체가 사라진다.

**결과:** 코드가 1/3로 줄었고, 하루 만에 동작했다. v1에서 5일간 쌓은 방어 코드가 전부 불필요해졌다.

---

### v3–v6: 안정화와 최적화 (3/16–26, 11일)

v2의 인프라 위에서 콘텐츠 전략, 페르소나, 수집, 프롬프트 구조를 빠르게 반복했다. 인프라를 한 번 제대로 만들면 제품 변경이 기하급수적으로 빨라진다.

**v3 (반나절):** 단일 뉴스 → **데일리 다이제스트** (3–5건 큐레이션). 파이프라인 골격은 그대로, 프롬프트만 교체.

**v4 (반나절):** 3 페르소나 → 2 페르소나 (Expert + Learner). Intermediate가 Expert와 70% 겹쳤다 — 차별화보다 제거가 나았다. LLM 호출 6→4회, 비용 -33%. 동시에 병렬화로 170초 → 90초 (47% 단축).

**v5 (8일):** Research 다이제스트에 논문이 하나도 없는 문제 발견. 근본 원인: Tavily만 사용. 4소스 병렬 수집(+ HuggingFace + arXiv + GitHub), 분류 프롬프트 강화(0–5 룰), 52개 프롬프트 이슈 감사, gpt-4o → gpt-4.1 전환(IFEval +6%, 비용 -20%), 자동 품질 스코어링 도입.

**v6 (1일):** 13개 규칙 나열 → 4개 페르소나별 스켈레톤. 원하는 출력의 뼈대를 직접 보여주자 점수가 56 → 75 → 90으로 상승. **핵심 발견: LLM은 "이렇게 해라"보다 "이것처럼 해라"를 훨씬 잘 따른다.**

---

### v7: 품질 중심 전면 리팩토링과 롤백의 교훈 (3/28–29, 2일)

자동 점수 90이었지만 사용자 관점 평가는 76. 5가지 문제(redirect URL, 필러 기사, Expert/Learner 겹침, 동일 깊이, 커뮤니티 반응 없음)를 해결: Layered Reading, Weighted Depth, 실제 댓글 기반 Community Pulse, 4개 품질 체크 프롬프트.

**롤백:** 3가지 변경을 한 커밋에 넣었더니 86.5 → 66.5. 롤백 후 선별 재적용으로 85.3 복구.

---

### v8: 구조 분리와 DON'T 제거 (3/29–30, 2일)

Research Expert가 아이템당 1문단만 작성하는 문제. 세 가지 원인: 분류/랭킹 결합, DON'T 과다(569단어, 9개), 스켈레톤 placeholder.

**해결:** 분류/랭킹 분리(`rank_classified()`, $0.00014/run), Research Expert Guide 569 → 151단어, DONT 9 → 0, 스켈레톤 2nd item 완전 작성, Exa 독립 수집기 승격(5 → 6소스), Community Pulse 개편.

**왜 수정이 아니라 제거인가:** Business Expert Guide가 이미 증명하고 있었다 — 더 적은 단어, DONT 0개로 더 높은 점수. 아이템당 1문단이 3문단으로 늘어났다.

**결과:** 4개 페르소나 모두 90점 — 모든 조합이 동일한 점수를 받은 첫 번째 버전.

---

### v9: 다중 소스 종합, 비용 폭발, 그리고 복구 (3/30–31, 2일)

**Phase 1 — 다중 소스 도입과 비용 폭발**

v8의 backfill 테스트에서 두 가지 구조적 문제를 발견했다: Writer가 1개 소스만 봤고(`raw_content[:4000]`), citation 번호가 섹션마다 리셋됐다.

**해결:** Exa `find_similar`로 기사당 최대 4개 관련 소스를 추가 수집하고, citation 넘버링을 코드 후처리로 전환했다. **왜 이 방식인가:** Writer는 받은 소스 이상을 알 수 없다 — "다양한 관점을 반영하라"는 지시보다 소스 자체를 다변화하는 게 근본 해결.

**문제:** 비용이 $0.25 → $0.77로 3배 폭발. 5개 아이템 x 4개 소스 x 전문 텍스트 = Writer input이 57K → 318K 토큰.

**Phase 2 — merge로 비용 복구**

같은 이벤트를 다룬 기사가 별도 아이템으로 분류되어 있었다 — "OpenAI $110B 투자"를 TechCrunch, Reuters, 공식 블로그가 각각 1개 아이템으로 3번 처리. 이 중복이 입력 폭발의 근본 원인.

**해결:** classify 후 별도 merge 단계를 추가하여 같은 이벤트 기사를 그룹화. merge된 그룹은 이미 다중 소스를 갖고 있으므로 Exa 호출을 스킵(조건부 enrich).

**merge v1 실패 → v2:** 처음에는 classify와 merge를 한 호출에서 동시에 처리했더니 LLM이 subcategory가 같은 기사를 전부 묶어버렸다 (논문 10개 → 1그룹). v8의 분류/랭킹 분리와 같은 교훈 — **한 호출에 두 가지 작업을 결합하면 두 작업 모두 정확도가 떨어진다.** classify와 merge를 분리하자 해결. 추가 비용 $0.002.

**결과:**

| 단계 | Writer 토큰 | Run 비용 |
|------|-----------|---------|
| v8 (단일 소스) | 57K | $0.27 |
| v9 enrich only | 318K | $0.77 (3배 폭발) |
| **v9 + merge (4 runs 평균)** | **73–203K** | **$0.43** (v8 수준 복귀) |

merge가 입력 중복을 제거하여 비용이 44% 감소($0.77 → $0.43 평균)했고, 다중 소스 품질은 그대로 유지되었다.

---

### v10: gpt-5 전환과 코드 기반 품질 관리 (3/31–4/6, 7일)

**gpt-5 마이그레이션**

gpt-5는 reasoning 모델이라 기존 파라미터가 작동하지 않는다 — `max_tokens` → `max_completion_tokens`, `temperature` 미지원, 추론 토큰이 출력 토큰을 소진하면 빈 응답 반환. 한번에 전부 바꿔서 실패한 경험을 반영하여 단계별로 검증하며 전환:

1. `_apply_gpt5_compat()` 함수로 파라미터 호환을 한 곳에서 처리 (28곳 적용)
2. `reasoning_effort: "low"` + `max_completion_tokens` 3x 헤드룸으로 빈 응답 해결
3. system prompt에 데이터를 넣으면 gpt-5가 무시하는 문제 → system=규칙, user=데이터로 분리

**Community Pulse 파이프라인 재설계**

Writer가 raw comment를 직접 처리하던 구조에서 Summarizer 단계를 분리. v8(분류/랭킹), v9(classify/merge)에 이어 세 번째 "역할 분리" 적용.

**왜 이 방식인가:** Writer에게 "코멘트 선별 + 요약 + 포맷 + KO 번역"을 한꺼번에 시키면 4가지 중 하나는 실패한다. Summarizer가 선별+요약+KO 번역을 담당하고, Writer는 정제된 데이터만 포맷하도록 분리. Brave Discussions로 Reddit 검색을 대체하고, Entity-First Search로 HN 검색 정확도도 개선.

**코드 기반 품질 관리**

LLM 채점(주관적 품질)에 코드 감점(구조적 규칙 위반)을 합산하는 시스템 도입. 최종 점수 = LLM 점수 - 코드 감점(최대 -30). CP 누락, 빈 섹션, EN/KO 불일치 등을 코드가 100% 정확하게 감지.

**품질 추이:**

| 단계 | Research | Business | 비고 |
|------|----------|----------|------|
| v10 초기 (gpt-5) | 61 | 59 | 채점 모델 calibration 부재 |
| v10 안정화 | 89 | 87 | calibration + 구조 감점 0 |
| v10 최종 (4/6) | **96** | **91** | [BODY] 마커 + 이벤트 중복 감점 |

---

### v11: Rubric 재설계와 소스 품질 게이트 (4/7–4/21, 15일)

Apr 19 사고에서 시작됐다. KO Research 다이제스트가 자동 점수 **96점**인데 실제로는 Community Pulse에 영어 인용만 있는 상태였다. 단일 총점 rubric이 locale 문제를 가리고 있었다 — 높은 점수가 콘텐츠 결함을 감춘 것.

**1. Rubric v2 — 10 sub-score + evidence + 코드 aggregate**

기존 4×25 단일 점수 → 10개 sub-score 각각 0–10점 + 근거 서술. LLM이 총점을 계산하지 않고 **코드가 합산**. `locale_integrity`가 severity 마커에서 explicit sub-dimension으로 승격.

**왜 이 방식인가:** LLM은 qualitative 평가에 강하지만 산수에 약하다. 둘을 섞으면 LLM이 정성 평가에 arithmetic까지 얹으면서 둘 다 불안정해진다. 역할을 분리하면 각각 더 정확해진다. body/frontload/weekly/handbook 4개 QC 경로가 같은 rubric으로 통일되어 parity 확보.

**2. 3-layer 소스 품질 게이트**

Apr 19 사고의 근본 원인은 low-quality 소스가 Writer에 그대로 전달된 것. 수집 후 Writer 전에 3개 게이트를 추가했다.

**A. Source quality gate** — 스팸 tier, content farm (introl.com, neuraplus-ai.github.io 등) drop. exa_enrich official_repo 오매칭도 drop.

**B. Authority rule** — GitHub 원본 repo > fork/mirror 구분. 이전에는 LLM이 fork를 원본처럼 취급. CoT + few-shot으로 authority 판단 개선.

**C. URL liveness gate** — HEAD 요청으로 404/410/DNS 실패/잘못된 redirect drop. 문자열 형식이 올바른 것과 실제 도달 가능한 것은 다른 검증.

Apr 19의 13개 문제 URL 전량 차단 확인.

**3. Pipeline Hardening (Phase 1–3)**

3일간 대규모 리팩터:
- `pipeline.py` **3,794줄 → 2,149줄 (-43%)**. 4-file split + shim re-export로 20+ import 지점 무중단
- 유료 API 쿼리 **24 → 11건 (-46%)**. Brave 전량 제거, Exa 12→5, Tavily 중복 2개 제거
- SEO-spam 도메인 **47% → 0%**
- QUALITY_CHECK 공유 블록 단축 → **-1,956 토큰** (목표의 156%)

**4. `rerun_from=quality` — 프롬프트 실험 비용 혁신**

QC만 재실행하는 경로 추가. run당 $0.54 → $0.05 (10배 절감). Writer 결과를 DB에서 재사용하고 품질 평가만 다시 돌린다. Rubric v2 같은 대규모 재설계를 경제적으로 가능하게 만든 전제 조건.

**5. Community Pulse Thread URL 보존**

수집 시점에 HN `story_id`와 Reddit `permalink`을 CommunityInsight에 embed. Writer가 순서를 바꿔도 살아남는 **upvote-count-based 매칭**으로 구조적 키 사용. 포지셔널 매칭은 LLM이 재배열하면 깨진다.

**v11 품질 지표:** Research 76 / Business 93 (v11 rubric 기준). **v10 85와 v11 85는 직접 비교 불가** — rubric 아키텍처가 바뀌면 점수 추이가 단절된다.

---

### v11.1: Writer-QC 미러 동기화 (4/22, 1일)

v11에서 QC에 새 sub-score (`claim_calibration`, `temporal_anchoring`, `internal_consistency`)를 추가했지만 **Writer 측에는 해당 규칙이 없어** 불일치 발생. Apr 21 실사고: Business 다이제스트에서 `$8.3 billion`을 `8.3억 달러`로 번역 (실제로는 `83억 달러`, **100배 오역**).

**해결:** Writer 측 `BODY_LOCALE_PARITY` 블록 신설, HALLUCINATION_GUARD 확장, FINAL CHECKLIST 3개 항목 추가. QC와 Writer 규칙을 **같은 커밋에 쌍으로** 변경하도록 원칙화.

**NQ-40 Phase 2a — Community Pulse 전용 sub-score 3개** (`cp_relevance`, `cp_substance`, `translation_fidelity`) 추가. **weight=0으로 2주 측정만** — 분산을 관찰하고 Phase 2b에서 가중치 결정 (가설 먼저 검증하는 점진적 도입).

**결과:** Apr 21 재실행 — Research 76→**95**, Business 93→**100**. 오역 원인 제거.

---

### v12: GPT-5 Efficiency Overhaul (4/23, 1일)

v11까지 구조적 과제를 해결하자 다음 관문이 드러났다: **비용 $0.50과 URL 환각**. v12는 이 둘을 동시에 해결했다.

**문제 4가지:**
1. URL 환각 — Writer가 `liner.com`, `axiomlogica.com` 같은 날조 URL 생성
2. Citation 대량 손실 — v11의 `_validate_urls_live` HEAD 체크가 70–85% false positive → citation 90% drop
3. EN/KO 비대칭 — locale별 다른 allowlist → body 불일치
4. 비용 추적 부정확 — DB에 저장된 cost가 standard tier 기준, flex 할인 미반영

**해결 A: Schema enum으로 URL 환각 API 레벨 차단**

새 Writer output contract:
```
body: "... [CITE_1] ... [CITE_2] ..."
citations: [
  {n: 1, url: "https://...allowlist_url_1..."},
  {n: 2, url: "https://...allowlist_url_2..."}
]
```

OpenAI strict `json_schema` + `citations[].url: enum [fact_pack.source_urls]` → **API가 서버에서 allowlist 외 URL 거부**. 프롬프트 준수율 85–97% → **스키마 100%**. `apply_citations()` 후처리가 placeholder를 `[N](URL)`로 치환.

**왜 이 방식인가:** 프롬프트로 "URL을 날조하지 마라"를 반복해도 완벽히 막을 수 없다. LLM이 따르지 않을 수 있다는 가능성을 **구조적으로 제거** — API 레벨에서 애초에 잘못된 응답을 만들 수 없게.

**해결 B: v11 URL liveness check 제거**

v11에서 도입한 HEAD 요청 검증이 70–85% false positive를 내면서 citation 90%를 잘못 drop. Schema enum으로 URL 정확성이 보장되자 liveness check가 불필요 → 완전 제거. 결과: paragraph coverage 29% → **94%**, URLs 5 → 14 (2.8x), citations 5 → 16 (3.2x).

**교훈: 추가가 항상 답이 아니다.** v11에서 추가한 검증이 false positive로 더 큰 문제를 만들었고, v12에서 제거하는 게 해결책이었다.

**해결 C: GPT-5 Flex Tier + Prompt Caching**

- `service_tier="flex"` (50% 할인) + `with_flex_retry` helper (429 exponential backoff)
- `prompt_cache_key` per persona — 3일 평균 **52% 캐시 적중** (4/23: 183K/350K input 캐시됨)
- `reasoning_effort="high"` 전체 적용

**reasoning_effort A/B (4/23, high vs medium 각 1회 실행):** Research expert가 결정적 — high `30 cites / 15 unique URLs` vs medium `17 / 9`. 다논문 cross-reference synthesis (μLM → Latent-Guided → SLM-MUX를 "latency-centric vs accuracy-centric"이라는 추상 축 위에 positioning하는 문단)에서 2배 밀도 차이. Business는 medium 96점 vs high 91점으로 거의 동등 — 1-sample variance로 판정. **Mixed (research expert만 high) 대신 uniform high 선택**: code simplicity + 멘탈 모델 일관성 + $2/month 차이로 trade-off.

**해결 D: 비용 추적 single-source-of-truth**

- `extract_usage_metrics`가 `response.service_tier` 자동 읽기 → flex 자동 적용
- `reasoning_tokens` 추출 + admin UI 표시

**3단계 비용 진화 (가장 중요한 교훈):**

| 단계 | 설정 | 일일 비용 | vs 기준선 |
|------|------|---------|----------|
| (1) Baseline | low reasoning, standard, liveness ON | $0.50 | — |
| (2) High-only blip | high reasoning, standard, no flex | **$0.86** | **+72%** |
| (3) Final | high + flex + cache + liveness off | **$0.33** | **-34%** |

월 $15 → $26 (naive) → **$10** (final). 연 $192 절감 vs naive.

**Reasoning tokens의 현실 (4/23 측정):**

| Stage | Output | Reasoning | Reasoning % |
|------|-------|----------|-------------|
| digest:business:expert | 16,811 | 11,328 | **67.4%** |
| digest:business:learner | 18,470 | 13,248 | **71.7%** |
| digest:research:expert | 17,555 | 11,392 | 64.9% |
| digest:research:learner | 12,357 | 7,360 | 59.6% |

**Output의 60–72%가 내부 추론** — 실제 body는 30–40%뿐. Reasoning token도 output rate($8/M)로 과금됨. OpenAI 문서에 명시되어 있지만 체감되지 않는 비용 구조 — `completion_tokens_details.reasoning_tokens`를 admin UI에 노출시켜서 reasoning_effort 튜닝 판단 근거를 확보했다.

---

### Rubric Evolution × Stable Scores — 한 달간의 교차 관찰

지난 한 달간 QC rubric을 지속적으로 엄격하게 조였는데 (9 → 14–15 sub-score, schema enforcement, CP 전용 차원 추가), writer 품질 점수가 떨어지지 않고 **89–97로 안정 유지**. 일반적으로 새 검사 추가 시 일시적 drop → 프롬프트 조정 → 회복 사이클이 필요한데, 이번엔 drop이 없었다.

**5가지 이유:**

1. **Schema enforcement가 구조적 실패를 선제 차단** — URL 환각이 API 레벨에서 원천 차단되어 `url_validation_failed=0`. 해당 rubric 사분면 점수 손실 없음.

2. **프롬프트 강화가 writer behavior 내재화** — HALLUCINATION_GUARD의 구체 예시들(forbidden 동사 리스트, 날짜 절대화 worked example, `$X million` 변환 예시)이 writer의 "주의 대상"을 명확히 해서 self-check에서 자동 회피.

3. **`reasoning_effort=high`가 self-check 루프 철저화** — FINAL CHECKLIST 11개 항목을 low에서는 skim, high에서는 실제 검증 후 제출.

4. **BODY_LOCALE_PARITY + schema enum → EN/KO 자동 대칭** — citation이 공통 `citations[]` 배열에서 substitute되므로 count 자동 일치.

5. **Code-level validation이 LLM-level validation 대체** — `_renumber_citations`, `apply_citations` 같은 코드 검증이 구조를 보장하므로 LLM은 **내용 품질**에 reasoning token을 집중할 수 있음.

**Rubric drift 문제:** Apr 21의 94점과 Mar 10의 94점은 같은 94가 아니다. 기준이 올라갔으니 **지금의 94가 더 높은 품질**. 절대 점수로는 "bar가 올라갔다"를 측정할 수 없다는 한계 — 향후 같은 기사를 신/구 rubric으로 재채점해서 offset을 구하는 방식 검토 중.

---

## 5. 핸드북 파이프라인

핸드북(AI 용어집)은 뉴스 파이프라인과 연동된다. 뉴스에서 등장한 AI 용어를 자동 추출하여, 기초(중학생도 이해 가능)와 심화(시니어 엔지니어 레퍼런스) 두 수준의 해설을 생성한다.

### 4-Call 분리

하나의 LLM 호출로 16개 필드를 한 번에 생성하면 후반부가 누락. 4단계로 분리하고 Call 2/3은 병렬 실행.

### 10개 용어 유형 분류

gpt-4.1-mini로 용어를 10개 유형(알고리즘/모델, 인프라/도구, 비즈니스/산업, 개념/이론, 제품/브랜드, 메트릭/지표, 기법/방법론, 데이터 구조/포맷, 프로토콜/표준, 아키텍처 패턴) 중 하나로 분류하고, 유형별 전용 심화 프롬프트를 사용. 분류 비용: 약 $0.001/용어.

### Tavily 통합 + Self-Critique

용어 생성 전 Tavily 웹 검색으로 최신 정보 5건 수집 → 4개 Call 모두에 컨텍스트 제공. Self-Critique로 점수 75 미만이면 재생성. Quality Scoring 4개 기준 x 25점.

### 신뢰도 기반 라우팅

접미사 패턴 매칭(1차, 비용 0) + LLM 2차 필터링(약 $0.01). High confidence → 자동 생성, Low confidence → `status: queued` (사람이 리뷰).

```
용어 입력 (뉴스 자동 추출 또는 Admin 수동)
    v
+-- Tavily 웹 검색 (5건)     --+
|                               |  병렬
+-- Type 분류 (gpt-5-mini)  --+
    v
유형별 심화 프롬프트 선택 (10개 유형)
    v
+-----------------------------------+
| Generate (gpt-5 x 4-Call)         |
|   Call 1: 메타 + Basic KO         |
|   Call 2: Basic EN     --+  병렬  |
|   Call 3: Advanced KO  --+        |
|   Call 4: Advanced EN             |
+-----------------------------------+
    v
Self-Critique (gpt-5-mini, < 75 --> 재생성)
    v
Quality Check (4기준 x 25점, < 60 --> warning)
    v
Save (High confidence --> draft, Low --> queued)
```

---

## 6. 기술 스택

| 레이어 | 기술 | 호스팅 |
|--------|------|--------|
| Frontend | Astro v5 + Tailwind CSS v4 + TypeScript | Vercel |
| Backend | FastAPI + PydanticAI | Railway |
| AI | OpenAI (gpt-5 / gpt-5-mini / gpt-5-nano) + Tavily + Exa + Brave | - |
| Database | Supabase (PostgreSQL + Auth + RLS) | Supabase |

---

> 이 문서는 0to1log 프로젝트의 AI 파이프라인 개발 과정을 정리한 것입니다.
> 12번의 파이프라인 버전, gpt-4o에서 gpt-5 flex까지의 모델/인프라 전환,
> 비용 폭발 → merge 복구 → reasoning 모델 마이그레이션 → rubric 재설계
> → schema enum + flex + cache로 품질과 비용을 동시에 혁신한 여정.
> 14–15 sub-score rubric + 3-layer 소스 게이트 + API schema enforcement로
> LLM/코드/API 3개 레이어에 걸쳐 품질 관리 시스템을 만들었습니다.
> 솔로 프로젝트로서 기획부터 배포까지 전 과정을 담당했습니다.
