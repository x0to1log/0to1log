---
title: AI Handbook Pipeline Overview
tags:
  - ai-system
  - pipeline
  - handbook
  - tier-1
source: docs/plans/2026-03-07-handbook-feature.md
---

# AI Handbook Pipeline Overview (v5)

Handbook(AI 용어집) 콘텐츠의 AI 생성·번역·연관 용어 탐색 파이프라인. Admin 에디터에서 수동 트리거하는 ==어드바이저 모드==와, 뉴스 파이프라인에서 자동으로 용어를 추출하는 ==파이프라인 모드==로 구분된다.

> [!note] v5 변경 (2026-03-23~25)
> - 모델: gpt-4o → **gpt-4.1** (main), gpt-4o-mini → **gpt-4.1-mini** (light)
> - Pipeline 추출: 상세 pre-filtering 추가 (긴 용어, modifier 접미사, 카테고리 검증)
> - 신뢰도 기반 라우팅: High → 자동 생성, Low → queued (수동 리뷰)
> - 동시성 제한: 세마포어 max 2 병렬 생성

## Handbook AI 전체 흐름

```mermaid
graph TD
    %% ── 두 가지 진입 경로 ──
    subgraph ENTRY ["진입 경로"]
        direction LR
        ADMIN["Admin Handbook Editor<br/>/admin/handbook/edit/[slug]"]
        PIPE["Daily News Pipeline<br/>뉴스 기사 본문"]
    end

    %% ── Admin 어드바이저 경로 ──
    ADMIN -->|"AI 버튼 클릭"| PROXY["Astro API Route<br/>POST /api/admin/ai/handbook-advise"]
    PROXY -->|"JWT 인증 + 프록시"| BACKEND["Railway FastAPI<br/>POST /admin/ai/handbook-advise"]
    BACKEND --> DISPATCH{"action 분기"}

    %% ── Action 1: Generate ──
    subgraph GEN ["Generate — 4-Call LLM 분리"]
        direction TB
        GEN_CTX["Tavily 검색 (5건) + 유형 분류<br/>gpt-4.1-mini · 병렬 실행"]
        GEN_C1["Call 1: 메타 + Basic KO<br/>term_full · korean_full · categories<br/>definition_ko/en · body_basic_ko"]
        GEN_C23["Call 2 + 3 (병렬)<br/>Call 2: Basic EN<br/>Call 3: Advanced KO (유형별 심화 프롬프트)"]
        GEN_C4SC["Call 4 + Self-Critique (병렬)<br/>Call 4: Advanced EN<br/>Self-Critique: Basic 품질 검사"]
        GEN_CTX --> GEN_C1 --> GEN_C23 --> GEN_C4SC
        GEN_C4SC --> GEN_OUT["GenerateTermResult"]
    end

    %% ── Action 2: Related Terms ──
    subgraph REL ["Related Terms — 연관 용어 탐색"]
        direction TB
        REL_LLM["Step 1 · LLM 제안<br/>gpt-4.1 · max 2,048 tokens"]
        REL_LLM -->|"10~15 용어 제안"| REL_EXA{"Exa API Key<br/>설정됨?"}
        REL_EXA -->|"있음"| REL_SEARCH["Step 2 · Exa 시맨틱 검색<br/>neural · 5건"]
        REL_EXA -->|"없음"| REL_DB
        REL_SEARCH --> REL_DB["Step 3 · DB 존재 확인<br/>handbook_terms ILIKE 조회"]
        REL_DB --> REL_OUT["RelatedTermsResult<br/>term · reason · exists_in_db · slug"]
    end

    %% ── Action 3: Translate ──
    subgraph TRANS ["Translate — KO↔EN 양방향 번역"]
        direction TB
        TRANS_DETECT["소스 언어 자동 감지<br/>KO 콘텐츠 ≥ EN → KO 기준<br/>force_direction 오버라이드 가능"]
        TRANS_DETECT --> TRANS_CALL["_run_translate()<br/>gpt-4.1 · max 4,096 tokens"]
        TRANS_CALL -->|"JSON mode"| TRANS_OUT["TranslateResult<br/>definition · body_basic · body_advanced<br/>source_lang · target_lang"]
    end

    DISPATCH -->|"generate"| GEN_CTX
    DISPATCH -->|"related_terms"| REL_LLM
    DISPATCH -->|"translate"| TRANS_DETECT

    %% ── 결과 → Admin UI ──
    GEN_OUT --> UI_RESULT
    REL_OUT --> UI_RESULT
    TRANS_OUT --> UI_RESULT
    UI_RESULT["Admin UI<br/>필드별 제안 카드 표시<br/>Use → Diff 미리보기 → Apply / Cancel<br/>Undo 지원"]

    %% ── 파이프라인 자동 추출 경로 ──
    subgraph PIPE_FLOW ["Pipeline 자동 용어 추출"]
        direction TB
        EXTRACT["extract_terms_from_content()<br/>gpt-4.1-mini · max 2,048 tokens<br/>기사 Expert EN 컨텐츠 입력"]
        FILTER["Pre-filtering<br/>· 3단어 초과 제거<br/>· modifier 접미사 제거 (-powered, -driven 등)<br/>· 유효 카테고리 검증 (12개)<br/>· DB 중복 체크 (slug + ILIKE)"]
        ROUTE{"신뢰도\n라우팅"}
        GEN_HIGH["High: generate_term_content()<br/>gpt-4.1 · 4-call 생성<br/>세마포어 max 2 동시"]
        SAVE_DRAFT[("handbook_terms<br/>source = pipeline<br/>status = draft")]
        SAVE_QUEUED[("handbook_terms<br/>source = pipeline<br/>status = queued")]
        EXTRACT --> FILTER --> ROUTE
        ROUTE -->|"High confidence"| GEN_HIGH --> SAVE_DRAFT
        ROUTE -->|"Low confidence"| SAVE_QUEUED
    end
    PIPE -->|"뉴스 기사 본문"| EXTRACT

    %% ── Styling ──
    classDef entry fill:#e8daef,stroke:#7d3c98,color:#333
    classDef ai fill:#d4e6f1,stroke:#2471a3,color:#333
    classDef storage fill:#d5f5e3,stroke:#1e8449,color:#333
    classDef decision fill:#fdebd0,stroke:#ca6f1e,color:#333
    classDef ui fill:#f5eef8,stroke:#7d3c98,color:#333

    class ADMIN,PIPE entry
    class GEN_CTX,GEN_C1,GEN_C23,GEN_C4SC,REL_LLM,REL_SEARCH,TRANS_CALL,TRANS_DETECT,EXTRACT,GEN_HIGH ai
    class SAVE_DRAFT,SAVE_QUEUED storage
    class DISPATCH,REL_EXA,ROUTE decision
    class UI_RESULT ui
```

### 데이터 모델 & 콘텐츠 구조

```mermaid
graph LR
    subgraph TERM ["handbook_terms 테이블"]
        direction TB
        META["term · term_full · slug<br/>korean_name · korean_full<br/>categories · status · source<br/>quality_score"]
        DEF["definition_ko · definition_en<br/>1~2문장 공유 정의"]
        BASIC["body_basic_ko · body_basic_en<br/>입문자용 · 비유 활용 · 2,000자+"]
        ADV["body_advanced_ko · body_advanced_en<br/>현직자용 · 기술 깊이 · 3,000자+"]
    end

    subgraph LEVELS ["2-Level 콘텐츠"]
        direction TB
        L_BASIC["Basic 레벨<br/>비유 · 쉬운 설명 · 왜 중요한가"]
        L_ADV["Advanced 레벨<br/>아키텍처 · 알고리즘 · 트레이드오프"]
    end

    subgraph SECTIONS_B ["Basic 구조"]
        direction TB
        SB1["What Is This?"]
        SB2["Easy Explanation"]
        SB3["Where Is It Used?"]
        SB4["Good to Know"]
        SB5["Common Expressions"]
        SB6["Related Terms"]
    end

    subgraph SECTIONS_A ["Advanced 구조"]
        direction TB
        SA1["Technical Overview"]
        SA2["How It Works"]
        SA3["Practical Application"]
        SA4["Why It Matters"]
        SA5["Pitfalls & Limitations"]
        SA6["References"]
        SA7["Related Terms"]
    end

    BASIC --> L_BASIC --> SECTIONS_B
    ADV --> L_ADV --> SECTIONS_A

    classDef meta fill:#fdebd0,stroke:#ca6f1e,color:#333
    classDef content fill:#d4e6f1,stroke:#2471a3,color:#333
    classDef level fill:#d5f5e3,stroke:#1e8449,color:#333

    class META,DEF meta
    class BASIC,ADV content
    class L_BASIC,L_ADV level
```

## Action 1: Generate — 4-Call LLM 분리 생성

`_run_generate_term()` · `GENERATE_BASIC_PROMPT` / `GENERATE_ADVANCED_PROMPT`

KO/EN 누락 버그 해결을 위해 4회 LLM 호출로 분리 구현됨. Advanced는 Tavily 검색 + 유형 분류 기반 심화 프롬프트 사용.

| Call | 모델 | 생성 필드 | 병렬 | 특이사항 |
|---|---|---|---|---|
| **전처리** | Tavily + gpt-4.1-mini | 검색 컨텍스트 + 유형 분류 | 병렬 | Call 3-4에 주입 |
| **Call 1** | gpt-4.1 | `term_full`, `korean_full`, `categories`, `definition_ko/en`, `body_basic_ko` | — | 메타 + KO Basic, KO 누락 시 재시도 |
| **Call 2** | gpt-4.1 | `body_basic_en` | Call 2+3 병렬 | EN Basic (Call 1 definition 컨텍스트 전달) |
| **Call 3** | gpt-4.1 | `body_advanced_ko` | Call 2+3 병렬 | Tavily + 유형분류 + 유형별 심화 프롬프트 |
| **Call 4** | gpt-4.1 | `body_advanced_en` | Call 4+SC 병렬 | Call 3와 동일 컨텍스트 사용 |
| **Self-Critique** | gpt-4.1 | 품질 경고 | Call 4+SC 병렬 | Basic 섹션 품질 검사, score < 70 시 경고 |

- ==비어있는 필드만 생성==, 기존 콘텐츠가 있으면 해당 필드는 그대로 유지
- body_basic: 비유 중심, 일상 언어, 2,000자 이상
- body_advanced: 기술적 깊이, 아키텍처·알고리즘·복잡도 분석, 3,000자 이상
- 10개 카테고리: `ai-ml`, `db-data`, `backend`, `frontend-ux`, `network`, `security`, `os-core`, `devops`, `performance`, `web3`
- term_full: 영문 풀네임 (예: "Long Short-Term Memory") / korean_full: 한국어 풀네임 (예: "장단기 기억 네트워크")

## Advanced Quality System

`HANDBOOK-ADV-01` (2026-03-18) 구현. Advanced 콘텐츠를 시니어 개발자 레퍼런스 수준으로 끌어올리는 4단계 파이프라인.

### 흐름 (Call 3-4 전처리)

```
Tavily 검색 (5건) ─┐
                    ├─ 병렬 실행 ─→ combined_context → Advanced 프롬프트 주입
gpt-4.1-mini 유형분류 ─┘
         ↓
유형별 심화 프롬프트 (10가지 TYPE_DEPTH_GUIDES 중 1개 선택)
         ↓
Call 3 (KO Advanced) 생성
         ↓
Self-critique (score < 75 시 약점 피드백 + 재생성)
         ↓
Quality scoring (0~100, gpt-4.1-mini) → DB 저장
```

### 10가지 용어 유형 분류

| 유형 | 예시 |
|---|---|
| `algorithm_model` | BERT, Transformer, GAN, Gradient Descent |
| `infrastructure_tool` | Docker, Kubernetes, CUDA, TensorFlow |
| `business_industry` | Funding Round, SaaS, Product-Market Fit |
| `concept_theory` | Overfitting, Bias-Variance Tradeoff, CAP Theorem |
| `product_brand` | GPT-4o, Claude, Midjourney, GitHub Copilot |
| `metric_measure` | AUC, F1 Score, BLEU, Perplexity |
| `technique_method` | Data Augmentation, Prompt Engineering, A/B Testing |
| `data_structure_format` | Parquet, B-Tree, Protocol Buffers, ONNX |
| `protocol_standard` | OAuth 2.0, HTTP/3, gRPC, WebSocket |
| `architecture_pattern` | Microservices, Event Sourcing, CQRS, RAG |

### 비용 영향

- 추가 비용: ~$0.07/용어 (22% 증가, $0.32 → $0.39)
- Tavily 검색: ~5 API 호출/용어
- Self-critique: 조건부 (score < 75인 경우만 재생성)

**핵심 파일:**
- `backend/services/agents/prompts_handbook_types.py` — 유형 분류 프롬프트 + 10가지 심화 가이드 + Self-critique 프롬프트

---

## Action 2: Related Terms — 연관 용어 탐색

`_run_related_terms()` · `RELATED_TERMS_PROMPT`

3단계 파이프라인:

1. **LLM 제안** (gpt-4.1, 2,048 tokens) — 10~15개 연관 용어 + 이유
2. **Exa 시맨틱 검색** (선택, `exa_api_key` 설정 시) — neural 검색 5건, LLM 제안과 중복 제거 후 병합
3. **DB 존재 확인** — 각 용어를 `handbook_terms`에서 ILIKE 조회 → `exists_in_db` + `slug` 반환

> [!tip] Admin UI 활용
> `exists_in_db=true`인 용어는 클릭하면 해당 용어 편집 페이지로 이동. `false`인 용어는 "새 용어 만들기" 액션으로 연결.

## Action 3: Translate — KO↔EN 양방향 번역

`_run_translate()` · `TRANSLATE_PROMPT`

| 항목 | 값 |
|---|---|
| **모델** | gpt-4.1 |
| **max_tokens** | 4,096 |
| **temperature** | 0.2 |
| **소스 언어 감지** | KO 콘텐츠 길이 ≥ EN → KO→EN, 그 반대면 EN→KO |
| **오버라이드** | `force_direction`: `"ko2en"` 또는 `"en2ko"` |
| **출력** | `TranslateResult` — definition + body_basic + body_advanced + source/target_lang |

- 마크다운 포맷 보존
- basic은 비유·일상 톤 유지, advanced는 기술적 정밀 톤 유지
- 비어있는 필드는 번역하지 않음

## Pipeline 자동 용어 추출 (v5)

뉴스 파이프라인 실행 후 기사 본문에서 기술 용어를 자동 추출하여 Handbook 초안을 생성한다.

### 추출 & 필터링

| 단계 | 함수 | 모델 | 설명 |
|---|---|---|---|
| **Extract** | `extract_terms_from_content()` | gpt-4.1-mini | Expert EN 다이제스트 콘텐츠에서 기술 용어 추출 |
| **Filter** | Pre-filtering | — | 3단어 초과 제거, modifier 접미사 제거 (-powered, -driven, -based 등), 유효 카테고리 12개 검증 |
| **Dedup** | DB batch check | — | slug + ILIKE 배치 쿼리로 기존 용어 스킵 |
| **Route** | 신뢰도 기반 | — | High → 자동 생성, Low → `status=queued` (수동 리뷰) |
| **Generate** | `generate_term_content()` | gpt-4.1 | 4-call 생성 (세마포어 max 2 동시) |
| **Save** | DB insert | — | `source='pipeline'`, `status='draft'` 또는 `'queued'` |

> [!note] 검수 필요
> 파이프라인이 자동 생성한 용어는 항상 ==draft 또는 queued 상태==로 저장되어, Admin이 검토 후 수동 발행한다.

### 유효 카테고리 (12개)

`ai-ml`, `db-data`, `backend`, `frontend-ux`, `network`, `security`, `os-core`, `devops`, `performance`, `web3`, `product`, `business`

## Admin UI 인터랙션

```mermaid
graph LR
    subgraph EDITOR ["Handbook Editor"]
        FORM["폼 입력<br/>term · korean_name<br/>definition · body"]
        AI_BTN["AI 패널 (사이드바)"]
        PER_BTN["Per-field AI 버튼<br/>body별 개별 생성"]
    end

    AI_BTN -->|"Generate All"| GEN_ACTION["generate action"]
    AI_BTN -->|"Related Terms"| REL_ACTION["related_terms action"]
    AI_BTN -->|"Translate"| TRANS_ACTION["translate action"]
    PER_BTN -->|"해당 body만 재생성"| GEN_ACTION

    GEN_ACTION & REL_ACTION & TRANS_ACTION --> RESULT["결과 카드"]

    RESULT --> DIFF["필드별 Diff 미리보기"]
    DIFF -->|"Apply"| APPLY["폼에 적용"]
    DIFF -->|"Cancel"| CANCEL["취소"]
    APPLY --> UNDO["Undo 버튼 활성화"]

    classDef action fill:#d4e6f1,stroke:#2471a3,color:#333
    classDef ui fill:#f5eef8,stroke:#7d3c98,color:#333

    class GEN_ACTION,REL_ACTION,TRANS_ACTION action
    class FORM,AI_BTN,PER_BTN,RESULT,DIFF ui
```

## 에이전트 함수 명세

| 함수 | 모델 | max_tokens | temperature | 역할 |
|---|---|---|---|---|
| `_run_generate_term()` | gpt-4.1 | 16,000×4 | 0.3 | 4-call 생성 오케스트레이터 |
| `_run_related_terms()` | gpt-4.1 | 2,048 | 0.3 | 연관 용어 탐색 (LLM + Exa + DB) |
| `_run_translate()` | gpt-4.1 | 4,096 | 0.2 | KO↔EN 번역 |
| `extract_terms_from_content()` | gpt-4.1-mini | 2,048 | 0.2 | 뉴스 기사에서 기술 용어 추출 |
| `generate_term_content()` | gpt-4.1 | 16,000 | 0.3 | 파이프라인 자동 추출용 생성 |
| `_search_term_context()` | Tavily API | — | — | Advanced 전처리 — 웹 검색 5건 |
| `_classify_term_type()` | gpt-4.1-mini | 100 | 0 | Advanced 전처리 — 10유형 분류 |
| `_self_critique_advanced()` | gpt-4.1 | 2,000 | 0.2 | Advanced 검토 + 재생성 판단 |
| `_check_handbook_quality()` | gpt-4.1-mini | 500 | 0 | 0~100 품질 점수 산정 |

## 품질 검증

### Generate 검증 게이트

`GenerateTermResult`에 `Field(min_length=...)` 적용:

| 필드 | 최소 길이 |
|---|---|
| `definition_ko/en` | 80자 |
| `body_basic_ko/en` | 2,000자 |
| `body_advanced_ko/en` | 3,000자 |

- 검증 실패 시 `success: false` + `validation_warnings: list[str]` 반환 (결과 데이터는 그대로 포함)
- Frontend에서 warning 토스트 표시

### 발행 게이트

`status.ts`에서 publish 전 검증:
- `term`, `slug`, `definition_ko` 필수
- `categories` 빈 배열 거부
- `body_basic_ko` 또는 `body_advanced_ko` 최소 1개 필수

### Soft Delete

삭제 시 `status='archived'`로 변경 (hard delete 아님). Admin 리스트에서 기본 표시, 필터로 구분.

### Pipeline 용어 배치 중복 체크

`_extract_and_create_terms()`에서 추출된 용어를 `in_()` 배치 쿼리로 한 번에 DB 존재 확인 → 이미 있는 용어는 `generate_term_content()` 호출 없이 스킵.

## 핵심 파일

| 파일 | 역할 |
|---|---|
| `backend/services/agents/advisor.py` | Handbook AI 함수 구현 |
| `backend/services/agents/prompts_advisor.py` | 프롬프트 상수 |
| `backend/services/agents/prompts_handbook_types.py` | 유형 분류 + 10가지 심화 가이드 |
| `backend/models/advisor.py` | Request/Response Pydantic 스키마 |
| `backend/routers/admin_ai.py` | `/admin/ai/handbook-advise` 엔드포인트 |
| `backend/tests/test_handbook_advisor.py` | Handbook AI 테스트 (8개) |
| `frontend/src/pages/admin/handbook/edit/[slug].astro` | 에디터 UI + AI 패널 |
| `frontend/src/pages/admin/handbook/index.astro` | 리스트 + 일괄 액션 + 완성도 도트 |
| `frontend/src/pages/api/admin/ai/handbook-advise.ts` | 프록시 API Route |
| `frontend/src/pages/api/admin/handbook/bulk-action.ts` | 일괄 발행/아카이브 API |

## Related

- [[Prompt-Guides]] — 프롬프트 엔지니어링 가이드
- [[Quality-Gates-&-States]] — 품질 게이트
- [[AI-News-Pipeline-Design]] — 뉴스 파이프라인 (같은 패턴)

## See Also

- [[Handbook]] — Handbook 기능 상세 (03-Features)
