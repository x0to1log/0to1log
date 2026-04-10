---
title: Phase Flow
tags:
  - implementation
  - phases
---

# Phase Flow

Phase별 구현 범위, 태스크, 완료 기준을 관리하는 상세 문서.
실행 계약/원칙은 [[Implementation-Plan]] 참조. 현재 진행 중인 태스크는 [[plans/ACTIVE_SPRINT]] 참조.

> **마지막 업데이트:** 2026-04-10 (NP4-Q 클로즈 + HB-QM 선언 반영)

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

## Handbook Redesign (HB-REDESIGN) ✅ (2026-04-09~10)
**섹션 재설계 + redesign 필드** | Basic 13→7 + Advanced 11→7 + Hero card + References footer + Sidebar checklist

- [x] **HB-REDESIGN-KO** — Basic KO 프롬프트 재작성 + 조립 + Pydantic 마이그레이션 + dead code 제거
- [x] **HB-REDESIGN-B** — Basic EN 프롬프트 복제 (7섹션 + hero + refs + checklist), definition max_length 제거
- [x] **HB-REDESIGN-A** — DB migration (6개 신규 컬럼) + admin save + detail loader + 3 component (HeroCard/References/UnderstandingChecklist) + KO/EN [slug].astro 배치 + level switcher 확장
- [x] **HB-REDESIGN-C** — Advanced 프롬프트 KO/EN 재작성 + Basic body context 주입 (verbatim overlap 0건) + 차별화 매트릭스 검증
- [x] **HB-EDITOR-V2** — 어드민 에디터 redesign 필드 6개 편집 지원 + JSON live validation + UX polish

**결과:** 8개 샘플 용어 (overfitting, DPO, fine-tuning, Hugging Face, MCP, Transformer, CUDA, prompt injection) 모두 차별화 매트릭스 통과.
**설계/회고:** [[plans/2026-04-09-handbook-section-redesign]], [[12-Journal-&-Decisions/2026-04-10-handbook-section-redesign-shipped]]

---

## News Pipeline v4 Quality Stabilization (NP4-Q) ✅ (2026-03-15 ~ 2026-04-10)

**클로즈일:** 2026-04-10 | **기간:** 27일 | **commits:** 100+

### 핵심 완료 사항

**파이프라인 구조:**
- ✅ 2-페르소나 독립 생성 (Expert + Learner, 각각 EN+KO)
- ✅ Skeleton-map 라우팅 (R/B × Expert/Learner = 4 skeleton)
- ✅ 품질 점수링 v2 (0~100, Research/Business 기준 분리)
- ✅ Weekly Recap 백엔드 완료 (프론트 통합은 HB-QM OPTIONAL)
- ✅ 직접 FastAPI 호출 (Vercel 60s timeout 제거)

**뉴스 품질 v7 (NQ-*):** 17개 done (NQ-02/03/05/06/07/08/10/11/12/13/14/16/17/18/19/20/22)
- Classify/Merge 분리, Multi-Source Enrichment, Entity-First Search, Brave Discussions
- Community Summarizer, Writer 다중 소스 활용, 파이프라인 체크포인트
- 5개는 HB-QM으로 이월: NQ-09/15/21/23/24

**PROMPT-AUDIT 52개:** P0 2개 + P1 9개 배포, P2 40개는 rolling 프롬프트 개선에 흡수 → **별도 track 종료**

**자동화:**
- AUTOPUB-01 ✅ — Quality ≥85 자동 발행 + 2h 리뷰 윈도우 + 이메일 알림 + 어드민 dot
- FASTAPI-DIRECT-01 ✅ — Vercel 60s proxy timeout 완전 제거
- QUALITY-CHECK-02 ✅ — Expert/Learner 분리 평가

### 파이프라인 진화

| v | 시기 | 주요 변경 | 상태 |
|---|------|-----------|------|
| v2 | 2026-01 | 모듈화, Pydantic, Tavily | ✅ |
| v3 | 2026-03-15 | Daily Digest, 6 페르소나×R/B | ✅ |
| v4 | 2026-03-17 | 2 페르소나, -33% 비용 | ✅ |
| v4.1+ | 2026-03-26 ~ 04-10 | Skeleton-map, 품질 안정화, Weekly Recap, AUTOPUB | ✅ NP4-Q 완료 |

### NP4-Q 최종 게이트 (전부 통과)

- [x] v4 core (skeleton-map, 2 personas)
- [x] Weekly Recap 백엔드
- [x] FASTAPI-DIRECT-01 (Admin timeout 회피)
- [x] QUALITY-CHECK-02 (Expert/Learner 양쪽 평가)
- [x] PROMPT-AUDIT P0/P1 배포 (P2는 rolling 흡수)

**ruff/pytest 최종 검증은 HB-QM 게이트로 이월** (HB-MIGRATE-138 완료와 함께 실행).

---

## Handbook Quality & Content Migration (HB-QM) 🔄 (2026-04-10 ~ 현재)

> **상세:** [[plans/ACTIVE_SPRINT]]

### 스프린트 목표

핸드북 콘텐츠 품질 및 규모 확장 — 138개 전량 재생성 + P0 품질 수정 + SEO 구조화 데이터

### 게이트 (BLOCKING)

- [ ] **HB-MIGRATE-138** — 138개 published 용어 v4 7섹션 구조 + redesign 필드로 regenerate
- [ ] **HQ-01** — Hallucination 즉시 수정 (stereo matching, ecosystem integration adv)
- [ ] **HQ-02** — 비기술 용어 archived 처리
- [ ] **HQ-11** — SEO 구조화 데이터 (DefinedTerm + FAQPage + BreadcrumbList)
- [ ] **최종 검증** — `ruff check .` + `pytest tests/ -v`

### 선택 목표

- HQ-03 (구세대 재생성), HQ-05 (quality_scores 버그), HQ-12 (톤 재설계), HQ-13 (term type + facet)
- GPT5-01~05 (gpt-5 단계별 마이그레이션 완료)
- Weekly Recap 프론트 통합 (WEEKLY-FE-01)

---

## Phase 3-Intelligence 🎯 (HB-QM 완료 후 시작)

> HB-QM 게이트 통과 후 시작. **AI 추천 + 학습 고도화**

### 진입 기준

- [x] News Pipeline v4 완료 (NP4-Q)
- [x] HB-REDESIGN ship (2026-04-10)
- [ ] HB-MIGRATE-138 완료
- [ ] HQ P0 (01, 02, 11) 배포
- [ ] ruff + pytest 통과

### 핵심 태스크 (HB-QM 이후)

**Wave 1: 개인화 기초**
- 개인 학습 프로필 (사용자 선호도 저장)
- 뉴스 추천 알고리즘 (관심 기반)
- Weekly Recap 프론트엔드 통합

**Wave 2: 커뮤니티 기반**
- COMMUNITY-01 — Reddit/HN/X 반응 수집
- 사용자 피드백 수집 (퀴즈, 북마크, 댓글)
- 트렌드 분석 및 핫이슈 추천

**Wave 3: 자동화 확장**
- 스마트 발행 스케줄 (최적 시간)
- A/B 테스트 자동화

> **주의:** 이전 Phase-Flow에 있던 Wave 1/2/3 날짜(2026-03-30~05-01)는 NP4-Q와 HB-REDESIGN 때문에 미뤄짐. 새 날짜는 HB-QM 종료 후 결정.

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

### 학습 모드 (Duolingo style) — Phase 4
- 핸드북 7섹션 본문에서 lesson cards 자동 추출 (새 LLM 생성 X)
- Skill tree = HQ-09의 9 카테고리 + prerequisite 관계
- DB 신규: `term_lesson_cards` (jsonb), `user_lesson_progress`, `user_xp`
- 상세: [[03-Features/Community-&-Gamification|Community & Gamification]] — 학습 모드 섹션

> **주의 — 시점 결정:** Phase 4는 사용자 베이스 + 활동 데이터가 쌓인 후. 지금은 vision만 명확히.

---

## Phase 4 — Community (Phase 3-Intelligence 이후)

| 기능 |
|---|
| AI Semantic Search (Cmd+K → pgvector) |
| Dynamic OG Image |
| Highlight to Share |
| 포인트 시스템 UI |
| Prediction Game UI |
| 학습 모드 (lesson cards + skill tree + streak) |

---

## Phase 5 — Native App (미래)

> PWA 검증 후 네이티브 전환. [[Monetization-Roadmap]]

**Go Gate `[4W-Cohort]`:**
- PWA 설치율 4%+ (4주 연속) / 설치자 4주 유지율 25%+ / 푸시 opt-in 35%+

---

## Related

- [[plans/ACTIVE_SPRINT]] — 현재 진행 중인 태스크 (HB-QM)
- [[Implementation-Plan]] — 실행 계약 + 운영 원칙
- [[Checklists-&-DoD]] — 완료 기준 체크리스트
- [[Design-System]] — 디자인 토큰
- [[Monetization-Roadmap]] — 수익화 단계별 상세
- [[Legal-&-Compliance]] — 법률/컴플라이언스 정책
- [[Newsletter-&-Email-Strategy]] — RSS/뉴스레터 전략
- [[Phases-Roadmap]] — 상위 5단계 전략 로드맵
