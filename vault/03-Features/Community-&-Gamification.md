---
title: Community & Gamification
tags:
  - features
  - tier-3
  - tier-4
  - community
  - gamification
source:
  - docs/01_Project_Overview.md
  - docs/02_Content_Strategy.md
---

# Community & Gamification

Phase 4에서 도입. 사용자 참여 유도 + 수익 모델 검증.

## Tier 3 — 커뮤니티 (Phase 4)

| 기능 | 설명 |
|---|---|
| **포인트 시스템** | 로그인 보너스, 피드백 참여, 소셜 인터랙션 보상 |
| **Prediction Game** | 뉴스 기반 퀴즈, 트렌드 베팅, 투표 시스템 |
| **리워드 & 뱃지** | 포인트 교환 혜택, 네온 돼지저금통 UI, 명예의 전당 |
| **거버넌스 참여** | AI PM에게 질문권, 분석 주제 제안 |
| **프리미엄 구독 검토** | 콘텐츠 계층화 (무료/프리미엄) 가능성 검증 |
| **PWA 배포** | 앱 설치 경험 제공 + 네이티브 앱 수요 검증 |

### 공통 포인트 (Base Points)

| 행동 | 포인트 | 조건 |
|---|---|---|
| 일일 첫 접속 (로그인 보너스) | 5pt | 1일 1회 |
| 피드백 참여 | 5pt | 포스트당 1회 |
| SNS 공유 (Highlight to Share) | 20pt | 1일 최대 60pt |
| Best Comment (좋아요 10개+) | 50pt | — |
| Weekly Sharp Insight (작성자 선정) | 200pt | 주 1인 |

### AI NEWS 특화: The Prediction Game

| 행동 | 포인트 | 비고 |
|---|---|---|
| Daily RAG Quiz 정답 | 10pt | 뉴스 내용 기반 |
| Trend Betting 참여 | 5pt | 투표만으로 지급 |
| Trend Betting 예측 성공 | 배당 포인트 | 3일 뒤 결과 정산 |
| Insight Contributor 선정 | 100pt | — |

### 학습 특화: The Expertise XP

| 행동 | 포인트 | 비고 |
|---|---|---|
| Code Completion (코드 빈칸 채우기) | 30pt | 미션 성공 시 |
| Daily Streak (3일 연속 정독) | 50pt | 학습 카테고리 한정 |
| Deep-Dive Completion (끝까지 읽기) | 15pt | 체류시간 + 스크롤 감지 |

### 포인트 사용처 (Reward)

| 보상 | 설명 |
|---|---|
| 심화 리포트 잠금 해제 | 유료급 심화 분석 열람 |
| Vote Boost | 내 투표 영향력 일시 강화 |
| 커스터마이징 | 포인트 컬러 변경, 한정판 네온 뱃지 |
| 거버넌스 참여 | AI PM 질문권, 다음 분석 주제 제안 |

## 학습 모드 (Duolingo style) — Phase 4

> **결정 (2026-04-10):** 핸드북 sidebar의 "이해했나요?" 체크리스트와 학습 모드의 퀴즈는 **분리한다.** 체크리스트는 sidebar self-check로 유지, 퀴즈는 별도 product surface로 만든다.

### 분리 결정의 근거

| 측면 | 체크리스트 (현재) | 학습 모드 퀴즈 (Phase 4) |
|---|---|---|
| 학습 모드 | passive (review aid) | active (recall + practice) |
| 위치 | 본문 옆 사이드바 | 별도 routes (`/ko/learn/...`) |
| 사용 흐름 | 본문 읽다가 한 번 보고 끝 | 5~10분 lesson 단위 세션 |
| 콘텐츠 단위 | 용어 1개 = 4~5 open questions | 용어 1개 = 5~10 closed-form cards |
| 상태 추적 | 없음 (anonymous OK) | 진행도 + 점수 + 정답률 |
| 재방문 동기 | 없음 | streak / XP / spaced repetition |
| 의존성 | 없음 (단독) | 카테고리 prerequisite chain (skill tree) |

**둘을 합치면 둘 다 어중간해진다.** 체크리스트를 퀴즈로 만들면 사이드바가 무거워지고, 퀴즈를 사이드바에 끼워 넣으면 active learning 흐름이 깨진다. 분리가 architectural cleanness.

### 학습 모드 surface (예정)

```
/ko/learn/                       메인 학습 허브
  /skill-tree                    카테고리별 prerequisite chain
    cs-fundamentals (1~5 lessons)
      → ml-fundamentals (5~10 lessons)
        → deep-learning (10~15 lessons)
          → llm-genai (15+ lessons)
  /lesson/[term-slug]            개별 용어 lesson (5~10 cards)
  /streak                        일일 학습 기록
  /profile                       누적 XP, 배지, 진행도
```

### Lesson card types (기존 7섹션에서 자동 추출)

새 콘텐츠 생성 없이 기존 핸드북 본문을 LLM이 lesson cards로 변환:

| Card type | 추출 원천 |
|---|---|
| **Definition match** (정의 ↔ 용어) | `definition_ko/en` |
| **Fill-in-the-blank** (핵심 문장 빈칸) | `body_basic_ko_1_plain` 핵심 문장 |
| **Concept application** (시나리오 → 어떤 개념?) | `body_basic_ko_2_example` 시나리오 |
| **Code completion** (코드 빈칸) | `body_advanced_ko_3_code` |
| **True/False** (오해 vs 사실) | `body_basic_ko_5_caution` |
| **Matching** (개념 vs 대안) | `body_basic_ko_3_glance` 비교표 |
| **시나리오 → tradeoff** (적합 vs 부적합) | `body_advanced_ko_4_tradeoffs` |

### 핵심 설계 원칙

- **새 LLM 콘텐츠 생성 X** — 기존 7섹션 본문에서 cards 추출만
- **DB 신규 테이블**: `term_lesson_cards` (jsonb), `user_lesson_progress`, `user_xp`
- **Skill tree** = HQ-09의 9 카테고리 + prerequisite 관계 정의 필요 (별도 디자인 작업)
- **Streak / XP / hearts** — Duolingo 패턴 그대로 차용 가능

### 의존성 / 마일스톤

1. ✅ **핸드북 섹션 재설계 완료** (HB-REDESIGN B/A/C, 2026-04-10)
2. ⏳ **138개 published 용어 v4 전량 regenerate** (HB-MIGRATE-138, 다음 작업)
3. ⏳ **Skill tree 카테고리 prerequisite 정의** (별도 design plan)
4. ⏳ **Lesson card extraction prompt 작성** (별도 plan)
5. ⏳ **Phase 4 본격 도입** — Quiz UI + DB schema + Streak system

### 주의 — 시점 결정

> **Phase 4는 사용자 베이스가 작은 단계에서 도입하면 retention 가치 0이다.**
> 기본 콘텐츠가 충분히 안정화되고, 사용자 활동 데이터가 쌓인 후 design하는 게 옳다.
> 지금 단계에서는 **vision만 명확히 적어두고**, 본격 구현은 콘텐츠 마이그레이션 + 트래픽 안정화 후로.

## Tier 4 — 앱 확장 (Phase 5)

| 기능 | 설명 |
|---|---|
| **네이티브 앱 (Expo)** | iOS/Android 앱 — AI 뉴스 딜리버리 + 학습 플랫폼 |
| **구독 결제 (Polar)** | 프리미엄 구독 인앱 결제 |
| **푸시 알림** | 일일 AI 뉴스, 맞춤 콘텐츠 추천 |

## Related
- [[MyLibrary]] — 커뮤니티와 연결된 라이브러리 기능

## See Also
- [[Growth-Loop-&-Viral]] — 그로스 루프와 바이럴 (06-Business)
