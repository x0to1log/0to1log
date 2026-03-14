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

# Prompt Guides — 전략적 추론 항목 (v1.4)

AI 콘텐츠 생성 시 활용하는 구조화된 항목 시스템. ==디폴트 + 회전 구조==로 운영하여 가독성과 발행 지속가능성 확보.

## 전체 항목 리스트

| # | 항목 | 설명 | 용도 |
|---|---|---|---|
| 1 | **[The One-Liner]** | 핵심 정의 한 문장 (필요시 비유 포함) | 디폴트 (입문자) |
| 2 | **[Action Item]** | 당장 적용할 수 있는 것 (Dev/PM 구분) | 디폴트 (학습자) |
| 3 | **[Critical Gotcha]** | 화려한 수치 뒤 한계점 리얼리티 체크 | 디폴트 (현직자) |
| 4 | **[Market Context]** | Winner & Loser + Why Now 시장 맥락 분석 | 회전 |
| 5 | **[Analogy for Laypeople]** | 일상 비유 설명 (기술 장벽 높은 뉴스) | 회전 |
| 6 | **[Source Check]** | 출처 유형 + 정보 신뢰도 한 줄 표기 | 회전 |
| + | **[Today's Quiz/Poll]** | 뉴스 기반 퀴즈 또는 투표 주제 | 고정 (하단) |

> [!note] Quiz/Poll
> Phase 4(포인트 시스템) 구현 전까지 UI 인터랙션 없이 텍스트로만 노출.

## 매일 AI NEWS 포스트 구성 (5블록 구조)

| 슬롯 | 항목 | 비고 |
|---|---|---|
| 디폴트 (입문자) | [The One-Liner] | 항상 노출 |
| 디폴트 (학습자) | [Action Item] | 항상 노출 |
| 디폴트 (현직자) | [Critical Gotcha] | 항상 노출 |
| 회전 (1개) | [Market Context] / [Analogy] / [Source Check] 중 택 1 | 뉴스 성격에 맞게 선택 |
| 고정 (하단) | [Today's Quiz/Poll] | Phase 4 전까지 텍스트만 |

> [!important] 적용 범위
> 5블록 구조는 ==Business 포스트==에 적용. Research 포스트는 단일 기술 심화 버전으로 Critical Gotcha + Action Item 중심 구성. 디폴트 3개는 각 페르소나 포스트에 기본 포함, 회전 항목은 뉴스에 가장 적합한 1개 선택.

## Locale별 5블록 생성/노출 계약

| 구분 | EN (Canonical) | KO (Localized) |
|---|---|---|
| **저장** | `guide_items` 5블록 전체 생성/저장 | EN 기준 의미 보존 + 5블록 전체 저장 |
| **노출 (Tier A)** | 5블록 전체 노출 | 5블록 전체 노출 |
| **노출 (Tier B)** | Compact 허용 (핵심 3블록 우선), 저장은 5블록 유지 | 5블록 노출 유지 (요약 강도 조절 가능) |
| **Quiz/Poll** | 텍스트 또는 링크형 안내 | 텍스트 또는 링크형 안내 |
| **검수 포인트** | 증거/한계/맥락 명확성 | 자연스러운 한국어/국내 맥락 전달 |

> [!note] 핵심 계약
> EN이 요약형으로 노출되더라도, 데이터 저장 스키마는 KO/EN 모두 ==5블록을 유지==한다.

## 에이전트 시스템 프롬프트

각 에이전트의 시스템 프롬프트. 전문은 `docs/03_Backend_AI_Spec.md` §5 및 `backend/services/agents/` 코드 참조.

### Ranking Agent (`RANKING_SYSTEM_PROMPT`)

- 출력: `NewsRankingResult` / 모델: gpt-4o-mini
- 역할: Tavily 수집 뉴스를 5가지 타입으로 분류 + 중요도 평가
- 핵심: research Top 1, business_main Top 1, Related 각 1개 (없으면 null)

### Research Engineer Agent (`RESEARCH_SYSTEM_PROMPT`)

- 출력: `ResearchPost` / 모델: gpt-4o
- 원칙: 마케팅 미사여구 금지, 미확인 수치 "미확인" 표기, 출처 필수
- 뉴스 있음: 기술 변경점 + 정량 지표 + 실무 적용 + 코드/논문 + 5블록
- 뉴스 없음: `has_news=false` + no_news_notice + recent_fallback

### Business Analyst Agent — Expert-First 2-Call Cascade (v4)

> [!note] v4 변경
> 기존 단일 `BUSINESS_SYSTEM_PROMPT` → 2개 프롬프트로 분리. 5회 호출 → 2회 호출.

**Call 1 — `BUSINESS_EXPERT_PROMPT`**
- 출력: `fact_pack` + `source_cards` + `content_analysis` + `content_expert` / 모델: gpt-4o
- 원칙: "누가 돈을 벌고 누가 위험해지는가" 관점
- Expert에 전체 context window 집중 — 깊이 있는 시장 분석 + 기술적 인사이트

**Call 2 — `BUSINESS_DERIVE_PROMPT`**
- 입력: expert 전문 / 출력: `content_learner` + `content_beginner` / 모델: gpt-4o
- ==3페르소나 모두 동일 분량 (min 5,000자, 목표 6,000~7,000자)==
- 길이가 아닌 ==서술 방식==으로 차별화:
  - expert: 기술 용어 OK, 데이터 중심, 산업 맥락 깊이
  - learner: 핵심 용어 설명 포함, 배경 맥락 보충
  - beginner: 비유 활용, 전문 용어 풀어쓰기, "왜 중요한가" 강조
- Related News: Big Tech / Industry & Biz / New Tools 각 한 줄 요약

### Translation Agent (`TRANSLATE_SYSTEM_PROMPT`) (v4)

- EN canonical → KO localized derivative
- ==전문 번역==: 포스트 전체 마크다운을 1회 호출로 번역 (기존 섹션별 번역 폐기)
- 규칙: 의역 (번역투 금지), 기술 용어는 영어 병기, 마크다운/URL/구조 보존
- 최소 총 길이 지정으로 번역 축약 방지

### Editorial Agent (`EDITORIAL_SYSTEM_PROMPT`)

- 출력: `EditorialFeedback` / 모델: gpt-4o
- 검수 4항목: 기술 정확도, 가독성, SEO, 톤앤매너 (각 1~10)
- 판정: [[Quality-Gates-&-States#Editorial 판정 기준]] 참조

## Related

- [[Content-Strategy]] — 프롬프트가 서비스하는 콘텐츠 전략
- [[Persona-System]] — 프롬프트가 대응하는 3페르소나
- [[AI-News-Pipeline-Overview]] — 프롬프트가 실행되는 파이프라인
- [[AI-NEWS-Business-Writing]] — Business 포스트 작성 가이드
- [[AI-NEWS-Research-Writing]] — Research 포스트 작성 가이드
- [[Global-Local-Intelligence]] — Locale별 톤 & 스타일 상세
