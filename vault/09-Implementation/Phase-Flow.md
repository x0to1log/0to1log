---
title: Phase Flow
tags:
  - implementation
  - phases
---

# Phase Flow

Phase별 구현 범위, 태스크, 완료 기준을 관리하는 상세 문서.
실행 계약/원칙은 [[Implementation-Plan]] 참조.

---

## Phase 1a — Foundation ✅ (2025-11~12)
**Astro v5 + Tailwind + 3테마** | 배포된 사이트의 기초 레이아웃 및 테마 시스템
- [x] 테마 전환, 폰트, 코드 블록 구문강조, Vercel 배포

## Phase 1b — Data Connection ✅ (2025-12)
**Supabase 연동 + Hybrid SSR/SSG** | 실제 데이터 렌더링 및 관리자 기초
- [x] 로그 목록/상세, Admin CRUD, Analytics 활성화

## Phase 2B — OPS (Backend) ✅ (2026-01)
**AI Agent + FastAPI** | 백엔드 AI 파이프라인 기초
- [x] OpenAPI 스펙, Agent 로직, Cron 엔드포인트, pytest

## Phase 2C — EXP (Frontend) ✅ (2026-01~02)
**UI/UX 고도화** | 반응형, 접근성, 성능 QA, Admin Editor mock
- [x] Lighthouse ≥85, Core Web Vitals 통과

## Phase 2D — INT (Integration) ✅ (2026-02)
**E2E 통합** | 실제 API, Auth, Cron, 보안 하드닝
- [x] Supabase Auth, Rate limit, CSP, E2E 시나리오

## Phase 3-USER ✅ (2026-02)
**사용자 기능** | 로그인, 북마크, 읽기 기록, 학습 진도
- [x] OAuth (GitHub/Google), `/library`, 프로필 관리

## Phase 3A-SEC ✅ (2026-03-09)
**보안 하드닝** | CSP nonce, Open Redirect, UX 개선
- [x] 5개 보안 리뷰 완료

## Phase 3B-SHARE ✅ (2026-03-13)
**소셜 공유** | X, LinkedIn, URL 복사, OG 태그
- [x] Web Share API, 카드 미리보기 최적화

---

## Handbook H1 (Read-Only) ✅ (2026-03-09~10)
**용어집 기초** | 목록/상세/카테고리, Admin 에디터, AI Advisor
- [x] 8개 태스크, GenerateTermResult 검증, 발행 게이트

## Handbook Quality ✅ (2026-03-13~16)
**품질 강화 + 4-call 분리** | Tavily 검색, 유형 분류, self-critique, 점수 매기기
- [x] term_full/korean_full 필드, 심화 품질 시스템, Bulk API

---

## News Pipeline v4 Quality Stabilization 🔄 (2026-03-15~진행 중)

> **현황:** 48+/50 tasks (96% 완료) | 마지막 업데이트: **2026-03-26 17:45**

### 핵심 완료 사항

**파이프라인 구조:**
- ✅ **News 수집**: Tavily + HF Daily Papers + arXiv + GitHub (3~5건씩)
- ✅ **분류**: o4-mini로 research/business 카테고리 배정 (0~5건 유연)
- ✅ **2-페르소나 독립 생성**: Expert + Learner (각각 EN+KO 동시)
- ✅ **Skeleton-map 라우팅**: R/B × Expert/Learner = 4개 skeleton으로 자동 선택
- ✅ **품질 점수링**: 0~100, Research/Business 기준 분리
- ✅ **Weekly Recap 백엔드**: 주간 요약 자동 생성 (프론트 통합 대기)
- ✅ **프론트 2-탭**: Expert/Learner 탭 분리 노출
- ✅ **자동 복구**: EN-only일 때 KO만 재호출

**최근 완료 (27+ commits, 2026-03-20~26):**
| 항목 | 상태 |
|------|------|
| Per-persona skeleton + Research Learner 접근성 | ✅ fc517fa |
| 프롬프트 구조 동등성 규칙 | ✅ 412ec85 |
| Perplexity 스타일 인용 형식 | ✅ 8af5625 |
| Analytics 탭 확장 (퀴즈, 피드백, 트래픽) | ✅ 80f2560 |
| KaTeX 수식 렌더링 보안 | ✅ 24aa89a |
| PROMPT-AUDIT P0/P1 배포 (11개) | ✅ rolling |

### 진행 중인 작업 (3개, ~2026-03-28)

| 태스크 | 목표 | 우선도 |
|--------|------|--------|
| **FASTAPI-DIRECT-01** | Vercel 60s timeout 회피 (직접 FastAPI 호출) | 🔴 CRITICAL |
| **QUALITY-CHECK-02** | 품질 체크 Expert/Learner 양쪽 평가 | 🔴 CRITICAL |
| **PROMPT-AUDIT-01** | P1/P2 41개 이슈 배포 (rolling) | 🟠 HIGH |

### 파이프라인 진화

| v | 시기 | 주요 변경 | 상태 |
|---|------|-----------|------|
| v2 | 2026-01 | 모듈화, Pydantic, Tavily | ✅ |
| v3 | 2026-03-15 | Daily Digest, 6 페르소나×R/B | ✅ |
| **v4** | **2026-03-17** | **2 페르소나, -33% 비용** | **🔄 96%** |
| v4.1+ | 2026-03-26 | Skeleton-map, 품질 안정화 | 🚀 배포 |

### 게이트 기준 (NP4-Q 완료 조건)

- [x] v4 core (skeleton-map, 2 personas) — **완료**
- [x] Weekly Recap 백엔드 — **완료**
- 🔄 PROMPT-AUDIT 70% 배포 (41/52) — **~2026-03-28**
- 🔄 FastAPI direct calls — **~2026-03-27**
- 🔄 품질 체크 Expert/Learner — **~2026-03-28**
- ⏳ `ruff check . ` + `pytest` 통과 — **PROMPT-AUDIT 후**

---

---

## Phase 3-Intelligence 🎯 (2026-03-30 예정)

> NP4 완료 후 시작. **AI 추천 + 학습 고도화**

### 진입 기준 (목표 2026-03-30)
- [x] News Pipeline v4 완료 — **2026-03-17** ✅
- 🔄 PROMPT-AUDIT 70% 배포 — **~2026-03-28**
- 🔄 FastAPI direct + quality check — **~2026-03-28**
- ⏳ `ruff` + `pytest` 통과 — **이후**

### 핵심 태스크

**Wave 1: 개인화 기초 (2026-03-30~04-10)**
- 개인 학습 프로필 (사용자 선호도)
- 뉴스 추천 알고리즘
- Weekly Recap 프론트엔드 통합

**Wave 2: 커뮤니티 기반 (2026-04-10~04-20)**
- COMMUNITY-01: Reddit/HN/X 반응 수집
- 사용자 피드백 수집 (퀴즈, 북마크)
- 트렌드 분석 및 핫이슈

**Wave 3: 자동화 (2026-04-20~05-01)**
- AUTOPUB-01: Quality ≥80 자동 발행
- 스마트 발행 스케줄
- A/B 테스트 자동화

---

---

## 미래 기능 (설계 완료, 구현 대기)

### AI Products (Draft — 향후 Phase)
**7개 카테고리** (LLM, Image Gen, Video Gen, Coding, Productivity, Research, Voice)
- `/products/` 목록/상세, Admin 에디터, Featured 5개를 홈에 노출
- 파일 아카이브: [[90-Archive/2026-03/plans-archive/]]

### Factcheck (Draft — 향후 Phase)
**Quick Check + Deep Verify** — 핸드북/뉴스 에디터의 팩트체크, 신뢰도 점수

### Legal & Compliance (⚠️ 시급)
**Privacy Policy, Terms, Cookie Consent** — GA4/Clarity 이미 활성화
- `/privacy/`, `/terms/` 정적 페이지
- Cookie 배너 (localStorage, 미동의 시 분석 차단)

### RSS Feed (Phase 2 범위)
**피드 자동화** — `/rss.xml`, EN/KO 별도, Header/Footer 링크

### Monetization Roadmap (Phase 3~4)
**Affiliate** → **AdSense** → **Premium 구독**

> 신뢰 확보 후 유료화. Polar 기반. [[Monetization-Roadmap]]

**Go Gate `[8W-MA]` / `[28D]`:**
- WAU 500+ / 재방문 30%+ / 페르소나 전환 15%+
- 웨이트리스트 100+ / paywall 완독률 35%+ / 결제 전환율 2%+

**구현:**
- Free: Research 전체 + Business (입문자/학습자)
- Premium: Business Expert + 심층 분석 + 아카이브 검색
- Supabase RLS 구독 상태 기반 접근 제어
- 커뮤니티 가이드라인 + 환불 정책 추가

---

## Phase 4 — Community (미래)

| 기능 |
|---|
| AI Semantic Search (Cmd+K → pgvector) |
| Dynamic OG Image |
| Highlight to Share |
| 포인트 시스템 UI |
| Prediction Game UI |

---

## Phase 5 — Native App (미래)

> PWA 검증 후 네이티브 전환. [[Monetization-Roadmap]]

**Go Gate `[4W-Cohort]`:**
- PWA 설치율 4%+ (4주 연속) / 설치자 4주 유지율 25%+ / 푸시 opt-in 35%+

---

## Related

- [[plans/ACTIVE_SPRINT]] — 현재 진행 중인 태스크
- [[Implementation-Plan]] — 실행 계약 + 운영 원칙
- [[Checklists-&-DoD]] — 완료 기준 체크리스트
- [[Design-System]] — 디자인 토큰
- [[Monetization-Roadmap]] — 수익화 단계별 상세
- [[Legal-&-Compliance]] — 법률/컴플라이언스 정책
- [[Newsletter-&-Email-Strategy]] — RSS/뉴스레터 전략
