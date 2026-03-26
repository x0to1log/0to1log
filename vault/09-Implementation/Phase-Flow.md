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

## Phase 1a — Foundation ✅

> 빈 껍데기지만 배포된 사이트. 테마, 폰트, 레이아웃 문제를 일찍 발견.

| 기능 | 완료 기준 |
|---|---|
| Astro + Tailwind 초기 세팅 + 3테마 CSS 변수 | 테마 전환 시 모든 토큰 정상 반영 |
| Shiki css-variables 코드 블록 구문 강조 | 3테마 모두 구문 강조 정상, 전환 시 깜빡임 없음 |
| 폰트 로딩 + 렌더링 테스트 (5개 항목) | 라이트 모드 코드 블록 가독성 포함 전부 통과 |
| BaseLayout (Nav + Footer + 스킵 네비게이션) | 데스크탑/모바일 반응형, 키보드 접근성 |
| Home (Hero + 하드코딩 더미 포스트) | 더미 데이터로 레이아웃 확인 |
| Vercel 배포 + 도메인 연결 (0to1log.com) | 프로덕션 URL 접속 가능 |

---

## Phase 1b — Data Connection ✅

> 실제 데이터가 연결된 MVP. 수동 포스트로 사이트 운영 가능.

| 기능 | 완료 기준 |
|---|---|
| Supabase 연동 (글 목록/상세 조회) | 실제 DB 데이터로 페이지 렌더링 |
| Astro hybrid 모드 설정 (SSR/SSG 분리) | Home, Log = SSR / Post Detail, Portfolio = SSG |
| Log (글 리스트 + 카테고리 필터) | 카테고리 필터 작동, 정렬 정상 |
| Post Detail (마크다운 렌더링 + 코드 블록) | Shiki 구문 강조 + 3테마 반영 |
| Admin (최소 CRUD — 글 목록 + status 변경) | Supabase Dashboard 외부 링크로 새 글 작성 |
| ARIA 라벨 + 키보드 네비게이션 + 포커스 스타일 | 스크린 리더 테스트 통과 |
| Vercel Analytics 활성화 | Core Web Vitals 대시보드 확인 가능 |

---

## Phase 2B — OPS (Backend) ✅

> 백엔드 기능 고정.

| 태스크 | 내용 |
| --- | --- |
| `P2B-API-01` | AI Agent 로직 + Prompt 튜닝 (외부 API 테스트는 Mock 필수) |
| `P2B-API-02` | Admin CRUD 엔드포인트 + 인증/권한 테스트 |
| `P2B-CRON-00` | Cron endpoint skeleton + 인증 헤더 검증 (실운영 연동 제외) |

**Gate**
- [x] OpenAPI 문서 고정 (목록/상세/에러 응답 포함)
- [x] `pytest` 통과
- [x] 401/403 분리 동작 확인

---

## Phase 2C — EXP (Frontend Experience) ✅

> 프론트 경험 고도화.

| 태스크 | 내용 |
| --- | --- |
| `P2C-UI-11` | Newsprint 토큰/테마/공통 컴포넌트 정리 |
| `P2C-UI-12` | `/en\|ko/log` 리스트/상세 + 다국어 스위처 + 화면 상태 (empty/error/loading) |
| `P2C-UI-13` | 썸네일 이미지 newsprint 필터 (`.img-newsprint` grayscale+sepia, hover 시 원본 복원) |
| `P2C-UI-14` | Admin Editor 화면 구현 (마크다운 작성/미리보기 + Save/Publish), mock 사용 |
| `P2C-UI-15` | Admin Editor 상태/권한 처리 구현, mock-first |
| `P2C-QA-11` | 반응형/접근성/성능 QA |

**Gate**
- [x] 반응형: mobile/tablet/desktop 레이아웃 정상
- [x] 접근성: `prefers-reduced-motion`, 키보드 포커스, 대비 기준 통과
- [x] Lighthouse: Perf/Best/SEO/Acc >= 85
- [x] Core Web Vitals: LCP < 2.8s, CLS < 0.1, INP < 250ms
- [x] `npm run build` 0 error
- [x] Admin Editor mock 워크플로우 정상

---

## Phase 2D — INT (Integration) ✅

> 통합 / E2E.

| 태스크 | 내용 |
| --- | --- |
| `P2D-SEC-01` | Frontend/SSR 보안 하드닝 |
| `P2D-SEC-02` | Backend/API 보안 하드닝 |
| `P2D-AUTH-01` | Supabase Auth 실연동 |
| `P2D-SYNC-01` | 프론트 Mock 제거 후 실제 API fetch 연동 |
| `P2D-CRON-01` | Vercel Cron → Backend 파이프라인 실운영 연동 |
| `P2D-QA-01` | E2E 통합 테스트 |

**Gate**
- [x] 실데이터 기준 리스트/상세 렌더링 정상
- [x] `/api/trigger-pipeline` 공개 호출 차단
- [x] markdown raw HTML 차단/sanitize
- [x] Admin 로그인/세션 복원/보호 경로 정상
- [x] admin/cron rate limit 적용
- [x] 언어 전환 EN/KO pair 이동
- [x] Cron 파이프라인 실행 로그 확인
- [x] E2E 시나리오 통과

---

## Phase 3-USER ✅

> 일반 사용자 기능.

- **소셜 로그인:** GitHub + Google OAuth via Supabase Auth (`/login`)
- **DB:** `profiles`, `user_bookmarks`, `reading_history`, `learning_progress` 4개 테이블 + RLS
- **profiles 확장:** username, bio, preferred_locale, is_public, onboarding_completed
- **헤더:** Sign In / 아바타 드롭다운 (내 서재, 설정, 로그아웃)
- **읽기 기록:** 상세 페이지 방문 시 자동 기록, 리스트에서 읽은 글 `opacity: 0.55`
- **북마크:** 리스트 카드 + 상세 페이지 북마크 아이콘 (기사 + 용어 통합)
- **학습 진도:** Handbook 카테고리별 용어 학습 현황
- **내 서재:** `/library` — 읽은 글 탭 + 저장한 글 탭 + 학습 현황 탭

---

## Phase 3A-SEC ✅

> 후속 보안 하드닝.

- CSP nonce 기반 전환 (`unsafe-inline` 제거)
- analytics/script 로딩 nonce 재정비 (`strict-dynamic` 포함)
- Web Interface Guidelines 기반 보안 리뷰 수정 5건 (Open Redirect, lang, color-scheme, 버튼 로딩)

---

## Phase 3B-SHARE ✅

> 소셜 공유 버튼.

- X(Twitter), LinkedIn, URL 복사
- Web Share API 지원 시 네이티브 공유 시트 우선, 미지원 시 플랫폼별 폴백
- OG meta 태그 정비 (title, description, image) — 카드 미리보기 최적화

---

## Handbook H1 (Read-Only) ✅

> 병렬 트랙. AI 용어집 읽기 전용 기능.

- 용어 목록/상세/카테고리 페이지
- Admin 에디터 (생성/수정/삭제/발행)
- AI Advisor (generate, translate, related_terms, extract_terms)
- 8개 태스크 전체 완료 → [[90-Archive/2026-03/DONE_SPRINT_HANDBOOK_H1|아카이브]]

---

## Handbook Quality ✅

> H1 이후 품질 강화.

- AI 응답 검증: `GenerateTermResult` min_length 제약 + `validation_warnings` 반환
- 발행 게이트: body 필수 + categories 빈 배열 거부
- Soft delete: `status='archived'` (hard delete 제거)
- Bulk operations: 일괄 발행/아카이브 API + 리스트 체크박스
- 콘텐츠 완성도: 4-dot indicator (KO Basic/Adv, EN Basic/Adv)
- Pipeline batch dedup: 용어 추출 시 `in_()` 배치 DB 조회
- 테스트: `test_handbook_advisor.py` 8개

---

## News Pipeline v4 Quality Stabilization 🔄 (진행 중)

> 현재 스프린트: NP v4 스프링 코드 안정화 + 품질 개선. 상세 → [[plans/ACTIVE_SPRINT]]

**스프린트 기간:** 2026-03-15 ~ (진행 중, 예상 종료: 2026-03-30)
**진행률:** 50+ 태스크 중 48+ 완료 (96%) | 마지막 업데이트: 2026-03-26 17:45

### 구현된 주요 모듈

| 모듈 | 파일 | 설명 |
|------|------|------|
| 뉴스 수집 | `news_collection.py` | Tavily API, 3개 쿼리 |
| LLM 랭킹/분류 | `pipeline.py` | 카테고리별 Research 3~5건 + Business 3~5건 선별 |
| 다이제스트 생성 | `pipeline.py` | Expert + Learner 2-페르소나 × EN+KO = 4개 포스트/일 |
| 핸드북 용어 추출 | `pipeline.py` | 뉴스 → 핸드북 용어 자동 추출 + Semaphore 병렬 처리 |
| 파이프라인 오케스트레이터 | `pipeline.py` | News Run / Handbook Run 분리, asyncio.gather 병렬 |
| Cron 엔드포인트 | `cron.py` | Vercel Cron → Railway FastAPI, 인증 헤더 검증 |
| 관측성 | `admin.py` | Pipeline Runs UI (News/Handbook 탭), Cancel/Stuck 타임아웃 |
| 퀄리티 스코어링 | `quality.py` | Research/Business 기준 분리, LLM 2차 용어 필터, 배지 표시 |
| KO 자동 복구 | `pipeline.py` | EN 있고 KO 없을 때 KO만 재호출 |

### 아키텍처 참조

- v1 설계 (3-페르소나, 모놀리식): [[AI-News-Pipeline-Design]], [[AI-News-Pipeline-Operations]]
- v4 설계 (2-페르소나, 모듈화): [[2026-03-17-news-pipeline-v4-design]]
- v1 삭제 포스트모템: [[2026-03-15-news-pipeline-v1-postmortem]]

### 파이프라인 버전 진화 히스토리

| 버전 | 시기 | 주요 변경 | 상태 |
|------|------|-----------|------|
| **v1** | 2025-12 | 3-페르소나(Expert/Learner/Beginner), `pipeline.py` 모놀리식 (~979줄) | 삭제됨 |
| **v2** | 2026-01 | 모듈 분리 재설계, Pydantic 모델 정의, Tavily 수집, 백필 지원 | 완료 ✅ |
| **v3** | 2026-03-15 | Daily Digest 형태 전환, 다이제스트 프롬프트(6 페르소나×R/B), 퀄리티 스코어링 | 완료 ✅ |
| **v4** | 2026-03-17 | 2-페르소나(Expert/Learner), Beginner 삭제, 비용 최적화 (-33%), 프론트 2탭 | 진행 중 🔄 (96% 완료, ~2026-03-30 완료 예상) |
| **v4.1+** | 2026-03-26 | Per-persona skeletons, quality stabilization, citation format, analytics expansion | 배포 중 🚀 |

### 남은 태스크 (블로킹 vs 선택)

**Blocking:**
- `PROMPT-AUDIT-01`: 프롬프트 감사 52개 이슈 (11개 fix 배포됨, 41개 남음, rolling fix 중)
  - Status: 진행 중 (~50% 완료, P0~P1 대부분 배포됨)
  - Completion gate: ruff + pytest 통과 (이 후 확정)

**High Priority (NP4 완료 전):**
- `COMMUNITY-01`: Reddit/HN/X 커뮤니티 반응 수집 → 다이제스트 반영
- `DIGEST-04`: Daily Digest 프론트엔드 최종 검증 + Quality Score 대시보드
- `WEEKLY-01`: Weekly Recap 프론트엔드 integration (backend done ✅)

**선택:**
- `AUTOPUB-01`: 자동 발행 (Phase 3 이후)

**Gate**
- [x] 파이프라인 1회 실행 → research + business 포스트 draft 저장 성공
- [x] 2 페르소나 × 2 언어(EN+KO) 본문이 news_posts에 저장됨
- [x] Railway 배포 후 cron 트리거로 실제 실행 확인
- [ ] `ruff check .` + `pytest tests/ -v` 통과 (PROMPT-AUDIT-01 완료 후)

---

## Handbook 2-Call Split ✅

> NP2와 병렬 진행. 완료.

- `HB-SPLIT-01`: Generate 액션을 4회 LLM 호출 분리 (KO Basic / EN Basic / KO Advanced / EN Advanced)
- `HB-MODEL-01`: `term_full`, `korean_full` 컬럼 추가
- `HB-COST-01`: Handbook AI 호출 토큰/비용을 pipeline_logs에 기록
- `HB-ANALYTICS-01`: Pipeline Analytics에 Handbook 탭 추가

---

## 다음: Phase 3-Intelligence (In Planning)

> NP4 Quality Stabilization 후. AI 추천 + 학습 고도화. 예상 시작: 2026-03-30

**Phase 3-Intelligence 진입 기준:**
- [x] News Pipeline v4 핵심 구현 완료
- [ ] PROMPT-AUDIT-01 70% 이상 배포 (예상 2026-03-28)
- [ ] COMMUNITY-01 설계 완료 (2026-03-26 ✅)
- [ ] DIGEST-04 프론트엔드 검증 (예상 2026-03-29)
- [ ] ruff check + pytest 통과

**Phase 3-Intelligence 태스크:**

| ID | 내용 | 설명 |
| --- | --- | --- |
| `P3I-REC-01` | AI News 개인화 추천 | 읽기 기록, 북마크, 카테고리 선호 기반 추천 고도화 |
| `P3I-LIB-01` | My Library 재방문 흐름 | 저장한 뉴스/용어 resurfacing 규칙 + 재방문 UI |
| `P3I-HBK-01` | Handbook feedback 집계 | helpful/confusing 신호 admin 집계 + 보완 우선순위 |
| `P3I-HBK-02` | Handbook advanced body AI 보강 | `body_advanced_*`를 AI 파이프라인과 연결 |
| `P3I-QA-01` | 추천/학습 기능 QA | 추천 클릭률, feedback 반응률, 재방문율 지표 + QA |

---

## 다음: AI Products (Draft)

> 설계 완료. [[2026-03-15-ai-products-design]], [[2026-03-15-ai-products-schema]]

AI 도구/서비스 큐레이션 매거진 페이지. NP2 완료 후 독립 착수 가능.

**7개 카테고리:** LLM, Image Gen, Video Gen, Coding, Productivity, Research, Voice

**범위:**
- 프론트엔드: `/en/products/`, `/ko/products/` 목록 + `[slug]` 상세 (SSR)
- 컴포넌트: ProductHero, CategoryNav (sticky 탭), CategorySection, ProductCard, ProductDetail, MediaGallery
- DB: `ai_products` 테이블 (Supabase) — 다국어 필드, featured 플래그, affiliate_url, is_sponsored
- Admin: 제품 추가/수정 에디터
- 홈 연동: featured 5개를 메인 페이지 "주목할 AI 도구" 섹션에 노출
- Nav: 헤더에 "AI Products" / "AI 제품군" 추가

**설계 참조:**
- 기능 개요: [[AI-Products]]
- 카테고리 분류: [[AI-Products-Categories]]
- UX 레이아웃: [[AI-Products-Page-Layouts]]

---

## 다음: Factcheck (Draft)

> 설계 완료. [[2026-03-15-factcheck-design]]

- Quick Check: 핸드북/뉴스 에디터에서 원클릭 팩트체크
- Deep Verify: 출처 검증 + 교차 확인 + 신뢰도 점수

---

## 법률/컴플라이언스 — Privacy & Cookie Consent (시급)

> GA4 + MS Clarity가 이미 활성화 — 법적으로 지금 필요. [[Legal-&-Compliance]]

- Privacy Policy 페이지: `/en/privacy/`, `/ko/privacy/` (정적 페이지)
- Cookie Consent 배너: 자체 구현, localStorage 기반, 미동의 시 GA4/Clarity 차단
- Terms of Service: `/en/terms/`, `/ko/terms/`
- Footer에 Privacy / Terms 링크 상시 노출

---

## 비즈니스: RSS 피드 (Phase 2 범위)

> 구현 비용 최소, 리텐션 효과. [[Newsletter-&-Email-Strategy]]

- `@astrojs/rss` 플러그인으로 `/rss.xml`, `/en/rss.xml`, `/ko/rss.xml` 생성
- `<link rel="alternate" type="application/rss+xml">` 메타 태그
- Header/Footer RSS 아이콘 + 링크

---

## 비즈니스: AI Products Affiliate (Phase 3 초반)

> 첫 번째 수익원. [[Monetization-Roadmap]]

**Go Gate `[28D]`:**
- AI Products 등록 제품 20+ / 페이지 방문 500+ / 클릭률 15%+
- 최소 3개 제품 affiliate 프로그램 가입 완료
- Affiliate 고지 구현 완료 ([[Legal-&-Compliance]])

**구현:**
- `ai_products.affiliate_url` — 제휴 링크 (NULL이면 일반 url)
- `ai_products.is_sponsored` — Sponsored 라벨 표시
- 제품 카드/상세에 affiliate 고지 문구

---

## 비즈니스: AdSense (Phase 3 중반)

> 트래픽 검증 후 추가 수익 채널. [[Monetization-Roadmap]]

**Go Gate `[28D]`:**
- 게시글 30+ / 오가닉 세션 3,000+ / engagement time 90초+ / 재방문 20%+

**구현:**
- `ads.txt` 파일 설정
- 콘텐츠 하단/사이드바 배치 (읽기 경험 우선)
- CSP 설정 업데이트

---

## 비즈니스: Premium 구독 (Phase 4)

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
