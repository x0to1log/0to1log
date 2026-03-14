---
title: Content Strategy
tags:
  - content
  - strategy
  - tier-1
source: docs/02_Content_Strategy.md
---

# Content Strategy

0to1log의 콘텐츠 운영 원칙과 가치 전략. "오직 여기서만 얻을 수 있는 가치"를 핵심으로 설계.

## 발행 체계

| 콘텐츠 | 주기 | 방식 |
|---|---|---|
| **AI NEWS (Research)** | 매일 | 기술 심화, 자동 발행. 뉴스 없는 날 = "없음" 공지 + 최근 동향 보충 |
| **AI NEWS (Business)** | 매일 | 시장 분석, 수동 검수. [[Persona-System\|3페르소나]] + Related News |
| **서재 (Study)** | 주 1~2회 | 깊이 있는 기술 콘텐츠, 코드 포함 |
| **커리어 (Career)** | 비정기 | 작성자의 진솔한 목소리 우선 |
| **프로젝트 (Project)** | 비정기 | 실제 개발 과정 기록 |

## AI 워크플로우 분류

| 타입 | 적용 대상 | 방식 |
|---|---|---|
| **Research (자동 발행)** | AI NEWS 기술 심화 | Tavily 수집 → 랭킹 → 단일 포스트 → 자동 발행 |
| **Business (수동 검수)** | AI NEWS 시장 분석 | Tavily 수집 → 랭킹 → 3페르소나 + Related News → 수동 검수 |
| **Type A: Multi-Targeting** | 학습 (Study) | 하나의 원문 → 3개 페르소나 버전 자동 생성 |
| **Type B: Authentic Voice** | 커리어, 프로젝트 | 작성자 목소리 유지, AI는 구성/문장 다듬기 보조 |

## 다국어 운영 계약

> [!important] [[Global-Local-Intelligence]] 연동
> EN을 canonical source로 사용. KO는 EN 기준 localized derivative.

| 항목 | 계약 |
|---|---|
| **원본 언어** | EN canonical source |
| **파생 언어** | KO = EN 기준 localized derivative |
| **발행 방향** | EN-first, KO는 로컬라이징 검수 후 발행 |
| **독자 가치** | EN: 고밀도 큐레이션 / KO: 정보 비대칭 해소 + 맥락화 |
| **금지** | 직역 중심 기계 번역투, 근거 없는 과장형 카피 |

## 콘텐츠 가치 훅 (Core Value Hooks)

단순 정보 전달이 아닌 4가지 전략적 장치:

### ① "So What?" — 실천적 가치 제안

뉴스를 읽고 난 후, 독자가 ==당장 무엇을 해야 할지== 정의.

- **입문자:** 오늘 대화에서 아는 척하기 좋은 한 문장 요약
- **학습자:** 오늘 당장 내 프로젝트에 적용해 볼 수 있는 라이브러리/함수
- **현직자:** 내일 회의에서 제안해 볼 만한 비즈니스 아이디어

### ② "Connecting the Dots" — 맥락적 연결

단발성 소식이 아닌, 과거 사건이나 타 기술과의 연결 고리를 'PM의 시선'으로 분석.

- 관련 과거 포스팅 AI 자동 추천
- 두 소식 사이의 인과관계/경쟁 구도 분석

### ③ "The Prediction Game" — 예측과 베팅

뉴스 기반 미래 예측 + 게이미피케이션으로 재방문 유도 (Phase 4 본격 구현).

- 입문자용 미니 퀴즈 (뉴스 복습)
- 트렌드 베팅/투표 시스템
- 예측 성공 시 포인트 보상

### ④ "PM's Cost & Strategy Radar" — 비즈니스 리얼리티

엔지니어링 블로그가 놓치기 쉬운 '돈과 전략' 관점.

- 새 모델/서비스 출시 시 기존 대안 대비 가성비 비교 차트

## Phase별 콘텐츠 기능 구현 범위

| 기능 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| 기본 마크다운 발행 | ✅ | | | |
| [[Daily-Dual-News]] (Research + Business) | | ✅ | | |
| 페르소나 Switcher (Business) | | ✅ | | |
| [[Prompt-Guides\|프롬프트 가이드]] v1.3 적용 | | ✅ | | |
| Related News 3카테고리 | | ✅ | | |
| 뉴스 온도 시각화 | | ✅ | | |
| Connecting the Dots (관련글 추천) | | | ✅ | |
| Highlight to Share | | | ✅ | |
| 타임라인 인디케이터 | | | ✅ | |
| 포인트 시스템 전체 | | | | ✅ |
| Prediction Game (퀴즈/베팅) | | | | ✅ |

## 성공 기준 (Acceptance Criteria)

1. EN/KO 모두 동일 사실 집합(출처/수치/핵심 주장) 기반 작성
2. EN은 canonical source, KO는 localized derivative로 일관
3. Business 포스트는 EN/KO 모두 `guide_items` 5블록 저장
4. Tier B에서 EN compact 노출 시에도 저장 스키마(5블록) 유지
5. Persona 기본값: `DB > 쿠키 > beginner` 규칙 준수
6. Locale 전환 시 `translation_group_id` 기준 동일 콘텐츠 페어 이동
7. EN 문체 = evidence-first / KO 문체 = 자연스러운 한국어 설명 중심

## Related

- [[Daily-Dual-News]] — 콘텐츠 전략이 적용되는 핵심 기능
- [[Persona-System]] — 3페르소나 재가공 시스템
- [[Prompt-Guides]] — 5블록 프롬프트 가이드
- [[Global-Local-Intelligence]] — 다국어 운영 상세 전략
- [[AI-NEWS-Research-Writing]] — Research 작성 가이드
- [[AI-NEWS-Business-Writing]] — Business 작성 가이드
- [[Phases-Roadmap]] — 기능별 구현 시점
