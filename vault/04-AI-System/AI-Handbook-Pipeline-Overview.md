---
title: AI Handbook Pipeline Overview
tags:
  - ai-system
  - pipeline
  - handbook
  - tier-1
source: docs/plans/2026-03-07-handbook-feature.md
---

# AI Handbook Pipeline Overview

Handbook(AI 용어집) 콘텐츠의 AI 생성·번역·연관 용어 탐색 파이프라인. Admin 에디터에서 수동 트리거하는 ==어드바이저 모드==와, 뉴스 파이프라인에서 자동으로 용어를 추출하는 ==파이프라인 모드==로 구분된다.

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
    subgraph GEN ["Generate — 전체 필드 자동 생성"]
        direction TB
        GEN_CALL["_run_generate_term()<br/>gpt-4o · max 16,000 tokens"]
        GEN_CALL -->|"JSON mode"| GEN_OUT["GenerateTermResult"]
        GEN_OUT --> GEN_FIELDS["korean_name · categories<br/>definition_ko · definition_en<br/>body_basic_ko · body_basic_en<br/>body_advanced_ko · body_advanced_en"]
    end

    %% ── Action 2: Related Terms ──
    subgraph REL ["Related Terms — 연관 용어 탐색"]
        direction TB
        REL_LLM["Step 1 · LLM 제안<br/>gpt-4o · max 2,048 tokens"]
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
        TRANS_DETECT --> TRANS_CALL["_run_translate()<br/>gpt-4o · max 4,096 tokens"]
        TRANS_CALL -->|"JSON mode"| TRANS_OUT["TranslateResult<br/>definition · body_basic · body_advanced<br/>source_lang · target_lang"]
    end

    DISPATCH -->|"generate"| GEN_CALL
    DISPATCH -->|"related_terms"| REL_LLM
    DISPATCH -->|"translate"| TRANS_DETECT

    %% ── 결과 → Admin UI ──
    GEN_FIELDS --> UI_RESULT
    REL_OUT --> UI_RESULT
    TRANS_OUT --> UI_RESULT
    UI_RESULT["Admin UI<br/>필드별 제안 카드 표시<br/>Use → Diff 미리보기 → Apply / Cancel<br/>Undo 지원"]

    %% ── 파이프라인 자동 추출 경로 ──
    subgraph PIPE_FLOW ["Pipeline 자동 용어 추출"]
        direction TB
        EXTRACT["extract_terms_from_content()<br/>gpt-4o-mini · max 2,048 tokens<br/>기사 첫 4,000자 입력"]
        EXTRACT -->|"5~15 기술 용어"| GEN_AUTO["generate_term_content()<br/>gpt-4o · max 16,000 tokens"]
        GEN_AUTO --> SAVE_TERM[("handbook_terms<br/>source = pipeline<br/>status = draft")]
    end
    PIPE -->|"뉴스 기사 본문"| EXTRACT

    %% ── Styling ──
    classDef entry fill:#e8daef,stroke:#7d3c98,color:#333
    classDef ai fill:#d4e6f1,stroke:#2471a3,color:#333
    classDef storage fill:#d5f5e3,stroke:#1e8449,color:#333
    classDef decision fill:#fdebd0,stroke:#ca6f1e,color:#333
    classDef ui fill:#f5eef8,stroke:#7d3c98,color:#333

    class ADMIN,PIPE entry
    class GEN_CALL,REL_LLM,REL_SEARCH,TRANS_CALL,TRANS_DETECT,EXTRACT,GEN_AUTO ai
    class SAVE_TERM storage
    class DISPATCH,REL_EXA decision
    class UI_RESULT ui
```

### 데이터 모델 & 콘텐츠 구조

```mermaid
graph LR
    subgraph TERM ["handbook_terms 테이블"]
        direction TB
        META["term · slug · korean_name<br/>categories · status · source"]
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

## Action 1: Generate — 전체 필드 자동 생성

`_run_generate_term()` · `GENERATE_TERM_PROMPT`

| 항목 | 값 |
|---|---|
| **모델** | gpt-4o |
| **max_tokens** | 16,000 |
| **temperature** | 0.3 |
| **입력** | term + korean_name + categories + 기존 content (비어있지 않은 필드) |
| **출력** | `GenerateTermResult` — 8개 필드 (definition/body × ko/en) + korean_name + categories |
| **검증** | `GenerateTermResult.model_validate()` (soft-fail: 경고만 기록) |

- ==비어있는 필드만 생성==, 기존 콘텐츠가 있으면 해당 필드는 그대로 유지
- body_basic: 비유 중심, 일상 언어, 2,000자 이상
- body_advanced: 기술적 깊이, 아키텍처·알고리즘·복잡도 분석, 3,000자 이상
- 10개 카테고리: `ai-ml`, `db-data`, `backend`, `frontend-ux`, `network`, `security`, `os-core`, `devops`, `performance`, `web3`

## Action 2: Related Terms — 연관 용어 탐색

`_run_related_terms()` · `RELATED_TERMS_PROMPT`

3단계 파이프라인:

1. **LLM 제안** (gpt-4o, 2,048 tokens) — 10~15개 연관 용어 + 이유
2. **Exa 시맨틱 검색** (선택, `exa_api_key` 설정 시) — neural 검색 5건, LLM 제안과 중복 제거 후 병합
3. **DB 존재 확인** — 각 용어를 `handbook_terms`에서 ILIKE 조회 → `exists_in_db` + `slug` 반환

> [!tip] Admin UI 활용
> `exists_in_db=true`인 용어는 클릭하면 해당 용어 편집 페이지로 이동. `false`인 용어는 "새 용어 만들기" 액션으로 연결.

## Action 3: Translate — KO↔EN 양방향 번역

`_run_translate()` · `TRANSLATE_PROMPT`

| 항목 | 값 |
|---|---|
| **모델** | gpt-4o |
| **max_tokens** | 4,096 |
| **temperature** | 0.2 |
| **소스 언어 감지** | KO 콘텐츠 길이 ≥ EN → KO→EN, 그 반대면 EN→KO |
| **오버라이드** | `force_direction`: `"ko2en"` 또는 `"en2ko"` |
| **출력** | `TranslateResult` — definition + body_basic + body_advanced + source/target_lang |

- 마크다운 포맷 보존
- basic은 비유·일상 톤 유지, advanced는 기술적 정밀 톤 유지
- 비어있는 필드는 번역하지 않음

## Pipeline 자동 용어 추출

뉴스 파이프라인 실행 중 기사 본문에서 기술 용어를 자동 추출하여 Handbook 초안을 생성한다.

| 단계 | 함수 | 모델 | 설명 |
|---|---|---|---|
| **Extract** | `extract_terms_from_content()` | gpt-4o-mini | 기사 첫 4,000자에서 5~15개 기술 용어 추출 |
| **Generate** | `generate_term_content()` | gpt-4o | 추출된 용어별 전체 콘텐츠 자동 생성 |
| **Save** | DB insert | — | `handbook_terms`에 `source='pipeline'`, `status='draft'`로 저장 |

> [!note] 검수 필요
> 파이프라인이 자동 생성한 용어는 항상 ==draft 상태==로 저장되어, Admin이 검토 후 수동 발행한다.

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

| 함수 | 모델 | max_tokens | temperature | 입력 | 출력 스키마 |
|---|---|---|---|---|---|
| `_run_generate_term()` | gpt-4o | 16,000 | 0.3 | term + 기존 content | `GenerateTermResult` |
| `_run_related_terms()` | gpt-4o | 2,048 | 0.3 | term + definition | `RelatedTermsResult` |
| `_run_translate()` | gpt-4o | 4,096 | 0.2 | source content + direction | `TranslateResult` |
| `extract_terms_from_content()` | gpt-4o-mini | 2,048 | 0.2 | 기사 본문 (4,000자) | `ExtractTermsResult` |
| `generate_term_content()` | gpt-4o | 16,000 | 0.3 | term_name + korean_name | `GenerateTermResult` |

## 핵심 파일

| 파일 | 역할 |
|---|---|
| `backend/services/agents/advisor.py` | Handbook AI 함수 구현 |
| `backend/services/agents/prompts_advisor.py` | 프롬프트 상수 |
| `backend/models/advisor.py` | Request/Response Pydantic 스키마 |
| `backend/routers/admin_ai.py` | `/admin/ai/handbook-advise` 엔드포인트 |
| `frontend/src/pages/admin/handbook/edit/[slug].astro` | 에디터 UI + AI 패널 |
| `frontend/src/pages/api/admin/ai/handbook-advise.ts` | 프록시 API Route |

## Related

- [[AI-News-Pipeline-Overview]] — 뉴스 수집·생성 파이프라인
- [[Handbook]] — Handbook 기능 상세 (데이터 모델, 피드백, 검증)
- [[Handbook-Content-Rules]] — 콘텐츠 작성 규칙
- [[Prompt-Guides]] — 프롬프트 엔지니어링 가이드
- [[Admin]] — Admin 대시보드 기능
