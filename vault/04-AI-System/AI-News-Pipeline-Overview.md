---
title: AI News Pipeline Overview
tags:
  - ai-system
  - pipeline
  - news
  - tier-1
source: docs/03_Backend_AI_Spec.md
aliases:
  - AI-Pipeline-Overview
---

# AI News Pipeline Overview

매일 06:00 KST 자동 실행. 뉴스 수집 → 랭킹 → 포스트 생성 (Expert-First Cascade + 전문 번역) → 검수의 순차 파이프라인.

## Daily News Pipeline 흐름

```mermaid
graph TD
    %% ── Trigger & Lock ──
    CRON["Vercel Cron · 06:00 KST"]
    CRON -->|"POST /api/admin/run-pipeline<br/>fire-and-forget"| RW["Railway FastAPI · 202 Accepted"]
    RW --> LOCK{"pipeline_runs<br/>run_key 중복 체크"}
    LOCK -->|"이미 존재"| SKIP(["스킵 · 멱등성 보장"])
    LOCK -->|"run_key 획득 ✓"| RESUME{"Resume Mode<br/>저장된 스냅샷?"}

    %% ── Resume 분기 ──
    RESUME -->|"스냅샷 있음"| REUSE["저장된 후보 + 랭킹 재사용"]
    RESUME -->|"없음 / force_refresh"| S1_ENTRY

    %% ── Step 1: 수집 ──
    subgraph STEP1 ["Step 1 — Multi-Source 뉴스 수집"]
        S1_ENTRY["collect_all_news()"]
        S1_ENTRY --> TAVILY["Tavily Search<br/>4 queries × max 3건<br/>search_depth = advanced"]
        S1_ENTRY --> HN["Hacker News<br/>Top 80 → AI 키워드 필터"]
        S1_ENTRY --> GH["GitHub Trending<br/>어제 생성 topic:ai Stars Top 3"]
        TAVILY --> DEDUP
        HN --> DEDUP
        GH --> DEDUP
        DEDUP["URL 정규화 · 중복 제거"]
    end

    %% ── Step 2: 랭킹 ──
    subgraph STEP2 ["Step 2 — Ranking Agent · gpt-4o-mini"]
        RANK["rank_candidates()<br/>JSON mode · 5-type 분류"]
        RANK --> R_OUT["research_pick"]
        RANK --> B_OUT["business_main_pick"]
        RANK --> REL_OUT["related_picks<br/>big_tech · industry_biz · new_tools"]
    end
    DEDUP --> RANK
    REUSE --> RANK

    %% ── Novelty Gate ──
    R_OUT --> NOVEL{"Novelty Gate<br/>URL 기발행 체크"}
    NOVEL -->|"신규 뉴스"| RGEN
    NOVEL -->|"중복 → has_news=false"| RGEN

    %% ── Step 3-A: Research 트랙 ──
    subgraph STEP3A ["Step 3-A — Research 트랙"]
        RGEN["generate_research_post() · gpt-4o<br/>뉴스 유무 분기"]
        RGEN -->|"ResearchPost EN<br/>PydanticAI 검증"| RTRANS["translate_post · gpt-4o<br/>EN 전문 → KO 전문 번역 1회"]
        RTRANS --> RSAVE[("Supabase news_posts<br/>status = published<br/>Research EN + KO")]
    end

    %% ── Step 3-B: Business 트랙 ──
    subgraph STEP3B ["Step 3-B — Business Expert-First 2-Call Cascade"]
        direction TB
        EXPERT["Call 1 · generate_business_expert() · gpt-4o<br/>Expert에 전체 context window 집중"]
        EXPERT -->|"fact_pack · source_cards<br/>content_analysis · content_expert<br/>guide_items · excerpt · focus_items"| DERIVE["Call 2 · derive_business_personas() · gpt-4o<br/>Expert 전문을 입력으로 파생"]
        DERIVE -->|"content_learner<br/>content_beginner"| ASSEMBLE["BusinessPost 조립<br/>3 persona × min 5,000자"]
        ASSEMBLE --> BTRANS["translate_post · gpt-4o<br/>EN 전문 → KO 전문 번역 1회"]
        BTRANS --> BSAVE[("Supabase news_posts<br/>status = draft<br/>Business EN + KO")]
    end
    B_OUT --> EXPERT
    REL_OUT --> EXPERT

    %% ── Step 6: Editorial ──
    subgraph STEP6 ["Step 6 — Editorial 검수"]
        EDIT["review_business_post() · gpt-4o<br/>초안 품질 평가"]
        EDIT --> ADMIN["Admin 대시보드 · 수동 발행"]
    end
    BSAVE --> EDIT

    %% ── Logging ──
    RSAVE --> LOG
    BSAVE --> LOG
    LOG[("pipeline_logs<br/>비용 · 토큰 · 모델 · 상태<br/>admin_notifications")]

    %% ── Styling ──
    classDef trigger fill:#e8daef,stroke:#7d3c98,color:#333
    classDef ai fill:#d4e6f1,stroke:#2471a3,color:#333
    classDef storage fill:#d5f5e3,stroke:#1e8449,color:#333
    classDef decision fill:#fdebd0,stroke:#ca6f1e,color:#333
    classDef skip fill:#f2f3f4,stroke:#aab7b8,color:#666

    class CRON,RW trigger
    class RANK,RGEN,RTRANS,EXPERT,DERIVE,BTRANS,EDIT ai
    class RSAVE,BSAVE,LOG storage
    class LOCK,RESUME,NOVEL decision
    class SKIP skip
```

### 에러 핸들링 & 재시도 흐름

```mermaid
graph LR
    subgraph RETRY ["모든 AI 호출 · 공통 재시도 패턴"]
        direction TB
        CALL["API 호출"] --> OK{"성공?"}
        OK -->|"✓"| DONE["다음 단계"]
        OK -->|"✗ 1회차"| R1["60초 대기 → 재시도 1"]
        R1 --> OK2{"성공?"}
        OK2 -->|"✓"| DONE
        OK2 -->|"✗ 2회차"| R2["120초 대기 → 재시도 2"]
        R2 --> OK3{"성공?"}
        OK3 -->|"✓"| DONE
        OK3 -->|"✗ 최종 실패"| FAIL["실패 처리"]
    end

    subgraph FALLBACK ["단계별 실패 동작"]
        direction TB
        F1["Research 실패<br/>→ has_news=false 공지 발행"]
        F2["Business Expert 실패<br/>→ 해당 뉴스 스킵"]
        F3["Business Derive 실패<br/>→ expert만 draft 저장"]
        F4["번역 실패<br/>→ EN만 저장, KO 누락 로그"]
        F5["Editorial 실패<br/>→ 수동 검수 필요 태그"]
    end

    FAIL --> F1
    FAIL --> F2
    FAIL --> F3
    FAIL --> F4
    FAIL --> F5

    classDef retry fill:#fdebd0,stroke:#ca6f1e,color:#333
    classDef fail fill:#fadbd8,stroke:#c0392b,color:#333
    classDef ok fill:#d5f5e3,stroke:#1e8449,color:#333

    class CALL,R1,R2 retry
    class FAIL,F1,F2,F3,F4,F5 fail
    class DONE ok
```

## Step 1: Multi-Source 뉴스 수집

`collect_news()` → `list[dict]`

| 소스 | 방식 | 수량 |
|---|---|---|
| **Tavily** | 4개 영어 쿼리 병렬 (search_depth=advanced, 24h) | 쿼리당 max 3건 |
| **Hacker News** | Top 80개 중 AI 키워드 필터 | 가변 |
| **GitHub Trending** | 어제 생성된 `topic:ai` Stars 상위 | 3개 |

- URL 정규화 중복 제거: `url.split("#")[0].split("?")[0].rstrip("/")`
- 실패 처리: Tavily 30초 후 1회 재시도, HN/GitHub 실패 시 빈 리스트

## Step 2: Ranking Agent (gpt-4o-mini)

`rank_news()` → `NewsRankingResult`

5가지 타입으로 분류 + 중요도 평가 (0~1):

| 타입 | 용도 |
|---|---|
| `research` | Top 1 기술 심화 뉴스 |
| `business_main` | Top 1 분석 가치 뉴스 |
| `big_tech` | Related News — 빅테크 |
| `industry_biz` | Related News — 업계/투자 |
| `new_tools` | Related News — 새 도구 |

## Step 3: 포스트 생성 (순차)

> [!note] v4 변경
> Research → Business 순차 실행. Business는 ==Expert-First 2-Call Cascade==로 생성, 번역은 ==전문 번역== (포스트 전체 1회 호출).

### Step 3-A: Research EN (gpt-4o)

`generate_research_post()` → `ResearchPost`

- **뉴스 있음:** 기술 심화 포스트 + 5블록 → ==자동 발행==
- **뉴스 없음:** "없음" 공지 + 최근 동향 보충 → 자동 발행

### Step 3-A-KO: Research 번역 (gpt-4o)

`translate_post()` — EN 전문을 KO로 1회 호출 번역.
- 동적 threshold: `max(KO_MIN, int(en_len × 0.65))` — EN이 길수록 KO도 비례
- 프롬프트에 실제 EN 글자 수와 KO 목표치 명시
- `finish_reason=length` 감지 시 truncation 경고

### Step 3-B: Business Expert-First 2-Call Cascade (gpt-4o)

| Call | 함수 | 입력 | 출력 |
|---|---|---|---|
| **Call 1** | `generate_business_expert()` | 뉴스 원문 + 분석 지시 | `fact_pack` + `source_cards` + `content_analysis` + `content_expert` |
| **Call 2** | `derive_business_personas()` | expert 전문 | `content_learner` + `content_beginner` |

- Expert에 전체 context window 집중 → 깊이 있는 분석
- Learner/Beginner는 expert 기반 파생 — ==길이 동일 (min 5,000자)==, 서술 방식만 차별화
- [[Persona-System\|3페르소나]] + [[Prompt-Guides\|5블록]] → ==검수 대기 (draft)==

### Step 3-B-KO: Business 번역 (gpt-4o)

`translate_post()` — Business EN 전문 (3 persona + analysis)을 KO로 1회 호출 번역.
- 각 필드별 동적 threshold: `max(KO_MIN, int(en_len × 0.65))`
- 프롬프트에 필드별 EN 글자 수 → KO 최소치 명시

## Step 4-5: 검증 & 저장

- [[Quality-Gates-&-States\|PydanticAI]] 스키마 검증
- `save_post()`: Pydantic → Supabase `news_posts` 테이블
- guide_items → JSONB, related_news → JSONB, persona → 개별 컬럼
- 멱등 저장: `upsert(on_conflict="slug")`

## Step 6: Editorial Agent (gpt-4o)

`review_business_post()` → `EditorialFeedback`

Business 초안 품질 검수 → [[Admin]] 대시보드에서 확인 후 수동 발행.

## 오케스트레이터 핵심 규칙

| 규칙 | 설명 |
|---|---|
| **batch_id** | KST 기준 `YYYY-MM-DD` |
| **중복 방지** | `pipeline_runs` 테이블 `run_key = "daily:{batch_id}"` 락 |
| **순차 실행** | Research EN → KO → Business Expert → Derive → KO (v4) |
| **slug 패턴** | `{batch_id}-research-daily`, `{batch_id}-business-daily` |
| **로그** | `pipeline_logs`에 결과 기록, 실패 시 `admin_notifications` |

## 성공 기준

1. `collect_news()` 중복 URL 0개
2. 1회 실행 → Research(published) 1행 + Business(draft) 1행
3. 동일 batch_id 2회 트리거 → 2번째 스킵 (run_key 락)
4. `pipeline_logs` 최종 행 `status=success`

## Related

- [[AI-Handbook-Pipeline-Overview]] — Handbook AI 어드바이저 파이프라인
- [[Prompt-Guides]] — 에이전트 프롬프트 상세
- [[Quality-Gates-&-States]] — PydanticAI 검증 + 에러 핸들링
- [[Backend-Stack]] — 파이프라인이 동작하는 백엔드
- [[Database-Schema-Overview]] — 파이프라인 결과 저장 스키마
- [[Daily-Dual-News]] — 파이프라인이 생성하는 콘텐츠
- [[Cost-Model-&-Stage-AB]] — 파이프라인 실행 비용
