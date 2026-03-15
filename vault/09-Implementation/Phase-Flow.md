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

## News Pipeline v2 🔄 (진행 중)

> 현재 스프린트. 상세 → [[ACTIVE_SPRINT]]

**목표:** AI News Pipeline v2 백엔드 구현 (수집 → 팩트 추출 → 3 페르소나 생성 → 저장)

**주요 모듈:**
- 뉴스 수집 (Tavily API) → LLM 랭킹 → 커뮤니티 반응 수집
- 팩트 추출 (LLM Call 1) → 페르소나 생성 (LLM Call 2~4)
- 파이프라인 오케스트레이터 → Cron 엔드포인트
- 백필 지원 ✅ + 스테이지별 로깅 ✅

**Gate**
- [ ] 파이프라인 1회 실행 → research + business 포스트 draft 저장 성공
- [ ] 3 페르소나 × 2 언어(EN+KO) 본문이 news_posts에 저장됨
- [ ] `ruff check .` + `pytest tests/ -v` 통과
- [ ] Railway 배포 후 cron 트리거로 실제 실행 확인

---

## 다음: Handbook 2-Call Split

> NP2 완료 후 착수. [[ACTIVE_SPRINT]] 태스크 13~16.

- HB-SPLIT-01: Generate 액션을 2회 LLM 호출(메타+Basic / Advanced)로 분리
- HB-MODEL-01: `term_full`, `korean_full` 컬럼 추가
- HB-COST-01: Handbook AI 호출 토큰/비용을 pipeline_logs에 기록
- HB-ANALYTICS-01: Pipeline Analytics에 Handbook 탭 추가

---

## 다음: Phase 3-Intelligence (Draft)

> Handbook 2-Call 완료 후. AI 추천 + 학습 고도화.

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

**범위:**
- 프론트엔드: `/en/products/`, `/ko/products/` 목록 + `[slug]` 상세 (SSR)
- 컴포넌트: ProductHero, CategoryNav (sticky 탭), CategorySection, ProductCard, ProductDetail, MediaGallery
- DB: `ai_products` 테이블 (Supabase) — 7개 카테고리, 다국어 필드, featured 플래그
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

## Phase 4 — Community (미래)

| 기능 |
|---|
| AI Semantic Search (Cmd+K → pgvector) |
| Dynamic OG Image |
| Highlight to Share |
| 포인트 시스템 UI |
| Prediction Game UI |

---

## Related

- [[ACTIVE_SPRINT]] — 현재 진행 중인 태스크
- [[Implementation-Plan]] — 실행 계약 + 운영 원칙
- [[Checklists-&-DoD]] — 완료 기준 체크리스트
- [[Design-System]] — 디자인 토큰
