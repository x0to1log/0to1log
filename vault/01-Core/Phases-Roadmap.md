---
title: Phases Roadmap
tags:
  - core
  - roadmap
  - phases
source: docs/01_Project_Overview.md
---

# Phases Roadmap

MVP → Intelligence → Community → App 확장까지 5단계 로드맵.

## Phase 1: Foundation (1~2개월)

블로그 기본 골격 + 인증 + DB 연동 + 그로스 기반 설계

- [[Frontend-Stack|Astro + Tailwind + Motion One]] 기반 디자인 시스템
- 핵심 앱 구조: Home / News / Blog / Handbook / Library / Admin
- [[Database-Schema-Overview|Supabase]] 스키마 설계 및 CRUD
- Supabase Auth (Admin 이메일 + 사용자 소셜 로그인)
- 기본 마크다운 에디터
- 0to1log.com 커스텀 도메인 (Vercel)
- SEO 기반 설계: JSON-LD, 자동 사이트맵, 메타 태그
- GA4 + MS Clarity 설치

## Phase 2: AI Core (2~4개월)

==핵심 AI 파이프라인 구축 — 포트폴리오 임팩트의 핵심==

- Railway에 FastAPI 배포 (범용 API 서버)
- [[AI-News-Pipeline-Design|멀티 에이전트 파이프라인]] (Ranking → Research/Business → Editorial) — v4 완료 (2026-03-17, 2 페르소나 + Skeleton-map)
- [[Daily-Dual-News]]: Research(자동) + Business(수동 검수)
- [[Persona-System|Persona-Based RAG-Refine]] (Tavily → OpenAI → Supabase)
- PydanticAI 검증 레이어
- Persona Switcher: 로그인 DB > 쿠키 > beginner (3→2 페르소나로 축소: Expert + Learner)
- Vercel Cron Jobs 자동화
- AdSense 신청 (콘텐츠 30개+ 축적 후)
- [[Global-Local-Intelligence]] 전략 구체화
- **Handbook Redesign 완료 (2026-04-10):** Basic 13→7 + Advanced 11→7 + Hero card + References footer + Sidebar checklist

## Phase 3: Intelligence & Polish (4~6개월)

탐색 고도화 + 운영 도구 + 그로스 분석

- AI Semantic Search (Cmd+K) + pgvector
- Dynamic OG Image
- AI Ops Dashboard
- Railway Always-on 전환 (KPI 충족 시)
- Highlight to Share (바이럴 장치)
- 포트폴리오 쇼케이스
- [[KPI-Gates-&-Stages|AARRR 지표 대시보드]]
- [[SEO-&-GEO-Strategy|GEO 전략]] 적용

## Phase 4: Community & Monetization (6개월+)

사용자 참여 유도 + 수익 모델 검증

- [[Community-&-Gamification|통합 포인트 시스템]]
- Prediction Game (퀴즈, 베팅, 투표)
- 리워드 체계 (뱃지, 돼지저금통, 명예의 전당)
- 거버넌스 참여 기능
- 프리미엄 구독 모델 검토
- PWA 배포

> [!note] 왜 PWA를 먼저?
> 네이티브 앱 개발은 비용이 크다. PWA로 "앱처럼 설치"하는 경험을 먼저 제공하고, 실제 사용 데이터로 네이티브 앱 필요성을 검증한 뒤 Phase 5로 진행.

## Phase 5: Native App (Phase 4 안정화 후)

- Expo를 활용한 iOS/Android 앱
- 푸시 알림: 일일 AI 뉴스, 맞춤 추천
- 오프라인 읽기
- 구독 결제 연동 (Polar)
- 앱 스토어 출시

> [!important] Phase 5 진입 기준
> PWA 주간 활성 사용자 일정 수 이상 + 프리미엄 구독 전환율 검증 완료. 수치 기준은 Phase 4 데이터 기반.

## Related
- [[Project-Vision]] — 로드맵의 기반이 되는 비전
- [[Target-Audience]] — 로드맵이 서비스하는 오디언스

## See Also
- [[Phase-Flow]] — Phase별 프론트엔드 구현 범위 (09-Implementation)
