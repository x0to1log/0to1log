---
title: Prompt Guides
tags:
  - ai-system
  - prompts
  - tier-1
source:
  - docs/02_Content_Strategy.md
  - docs/03_Backend_AI_Spec.md
---

# Prompt Guides — 전략적 추론 항목 (v5)

AI 콘텐츠 생성 시 활용하는 구조화된 항목 시스템. ==디폴트 + 회전 구조==로 운영하여 가독성과 발행 지속가능성 확보.

> [!note] v5 변경
> - 2 페르소나 (Expert/Learner) — Beginner 제거
> - 모델: gpt-4.1 (main), o4-mini (classification)
> - 독립 생성 방식 (Expert/Learner 각각 직접 생성, derive 아님)
> - EN+KO JSON 동시 출력 (번역 단계 제거)

## 전체 항목 리스트

| # | 항목 | 설명 | 용도 |
|---|---|---|---|
| 1 | **[The One-Liner]** | 핵심 정의 한 문장 (필요시 비유 포함) | 디폴트 |
| 2 | **[Action Item]** | 당장 적용할 수 있는 것 (Dev/PM 구분) | 디폴트 |
| 3 | **[Critical Gotcha]** | 화려한 수치 뒤 한계점 리얼리티 체크 | 디폴트 |
| 4 | **[Market Context]** | Winner & Loser + Why Now 시장 맥락 분석 | 회전 |
| 5 | **[Analogy for Laypeople]** | 일상 비유 설명 (기술 장벽 높은 뉴스) | 회전 |
| 6 | **[Source Check]** | 출처 유형 + 정보 신뢰도 한 줄 표기 | 회전 |
| + | **[Today's Quiz/Poll]** | 뉴스 기반 퀴즈 또는 투표 주제 | 고정 (하단) |

> [!note] Quiz/Poll
> Phase 4(포인트 시스템) 구현 전까지 UI 인터랙션 없이 텍스트로만 노출. 페르소나별 quiz_en + quiz_ko 생성.

## 매일 AI NEWS 포스트 구성 (5블록 구조)

| 슬롯 | 항목 | 비고 |
|---|---|---|
| 디폴트 | [The One-Liner] | 항상 노출 |
| 디폴트 | [Action Item] | 항상 노출 |
| 디폴트 | [Critical Gotcha] | 항상 노출 |
| 회전 (1개) | [Market Context] / [Analogy] / [Source Check] 중 택 1 | 뉴스 성격에 맞게 선택 |
| 고정 (하단) | [Today's Quiz/Poll] | Phase 4 전까지 텍스트만 |

> [!important] 적용 범위
> 5블록 구조는 ==Business 포스트==에 적용. Research 포스트는 기술 심화 버전으로 Critical Gotcha + Action Item 중심 구성. 디폴트 3개는 모든 다이제스트에 기본 포함, 회전 항목은 뉴스에 가장 적합한 1개 선택.

## Locale별 5블록 생성/노출 계약

| 구분 | EN (Canonical) | KO (Localized) |
|---|---|---|
| **저장** | `guide_items` 5블록 전체 생성/저장 | EN과 동시 생성 (JSON 내 KO 키) |
| **노출** | 5블록 전체 노출 | 5블록 전체 노출 |
| **Quiz/Poll** | 텍스트 또는 링크형 안내 | 텍스트 또는 링크형 안내 |
| **검수 포인트** | 증거/한계/맥락 명확성 | 자연스러운 한국어/국내 맥락 전달 |

> [!note] 핵심 계약
> EN+KO는 동시 생성. 데이터 저장 스키마는 KO/EN 모두 ==5블록을 유지==한다.

## 에이전트 시스템 프롬프트

각 에이전트의 시스템 프롬프트. 전문은 `backend/services/agents/` 코드 참조.

### Classification Agent (`CLASSIFICATION_SYSTEM_PROMPT`)

- 출력: `ClassificationResult` / 모델: **o4-mini** (reasoning)
- 역할: 수집된 뉴스를 research/business로 분류 + 서브카테고리 배정
- 서브카테고리:
  - **Research**: `llm_models`, `open_source`, `papers`
  - **Business**: `big_tech`, `industry`, `new_tools`
- 각 서브카테고리 3~5건, 교차 중복 시 높은 점수 쪽에만 유지

### Digest Generator — 2 페르소나 독립 생성 (v5)

> [!note] v5 변경
> 기존 v4의 "Expert-first 2-call cascade" → **Expert/Learner 완전 독립 생성**. 각 페르소나가 동일 입력(뉴스 + 반응 + handbook slugs)에서 직접 생성.

**Expert 페르소나** (`get_digest_prompt(type, "expert", slugs)`)
- 출력: EN+KO JSON / 모델: **gpt-4.1** / max_tokens: 16,000
- 원칙: 전문 용어 자유, 데이터 중심, 전략적 인사이트
- "누가 돈을 벌고 누가 위험해지는가" 관점

**Learner 페르소나** (`get_digest_prompt(type, "learner", slugs)`)
- 출력: EN+KO JSON / 모델: **gpt-4.1** / max_tokens: 16,000
- 원칙: 핵심 용어 설명 포함, 배경 맥락 보충, 실무 적용 초점
- Handbook 링크 적극 활용

**공통:**
- ==두 페르소나 모두 동일 분량== (목표 6,000~7,000자)
- 길이가 아닌 ==서술 방식==으로 차별화
- `temperature: 0.4`
- EN+KO 동시 JSON 생성 (별도 번역 불필요)
- 퀴즈: `quiz_en` + `quiz_ko` 페르소나별 생성

### Skeleton-Map 기반 프롬프트 라우팅 (v5.1+)

v5에서 추가된 skeleton 시스템으로 각 포스트 타입(Research/Business) × 페르소나(Expert/Learner)에 최적화된 프롬프트 구조 제공:

**4개 독립 Skeleton 상수:**
- `SKELETON_RESEARCH_EXPERT` — 기술 심화, 벤치마크/성능 중심
- `SKELETON_RESEARCH_LEARNER` — 기술 설명 포함, 배경 지식 보충
- `SKELETON_BUSINESS_EXPERT` — 시장 분석, 투자 시각
- `SKELETON_BUSINESS_LEARNER` — 실무 임팩트, 이사회 뉘앙스

**라우팅 메커니즘:**
- `SKELETON_MAP[post_type][persona]` 자동 선택
- 각 skeleton은 구조, 문맥, 깊이가 서로 다름 (일반 프롬프트보다 정확한 출력)
- 코드 위치: `backend/services/agents/prompts_news_pipeline.py`의 `SKELETON_MAP`

**효과:**
- Research 다이제스트: 논문/벤치마크 맥락 강조
- Business 다이제스트: 시장/전략 맥락 강조
- 페르소나별: Expert는 기술 용어 자유, Learner는 설명 포함

### Editorial Agent (`EDITORIAL_SYSTEM_PROMPT`)

- 출력: `EditorialFeedback` / 모델: gpt-4.1
- 검수 4항목: 기술 정확도, 가독성, SEO, 톤앤매너 (각 1~10)
- 판정: [[Quality-Gates-&-States#Editorial 판정 기준]] 참조

## Related

- [[AI-News-Pipeline-Design]] — 프롬프트가 실행되는 파이프라인
- [[Quality-Gates-&-States]] — 검증 대상 프롬프트 출력

## See Also

- [[Content-Strategy]] — 프롬프트가 서비스하는 콘텐츠 전략 (05-Content)
