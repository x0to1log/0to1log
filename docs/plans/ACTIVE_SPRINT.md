# ACTIVE SPRINT — Phase 3-USER (일반 사용자 기능)

> **스프린트 시작:** 2026-03-08
> **목표:** 소셜 로그인 + 북마크 + 읽기 기록 + 학습 진도 + 내 서재
> **참조:** MASTER → `docs/IMPLEMENTATION_PLAN.md` | 설계 → `docs/plans/2026-03-08-user-features-design.md`
> **이전 스프린트:** Phase 2C-EXP — 2026-03-07 게이트 전체 통과

---

> UI naming boundary: public labels use `AI News`, `Handbook`, `Library`; internal/admin labels use `Posts`; compatibility route remains `/{locale}/log/`.

## 스프린트 완료 게이트

- [x] DB: `profiles`, `user_bookmarks`, `reading_history`, `learning_progress` 4개 테이블 생성 + RLS
- [x] 소셜 로그인: GitHub/Google OAuth 버튼 → Supabase Auth redirect 동작
- [x] 소셜 로그인: OAuth provider 외부 설정 완료 (GitHub App + Google Cloud + Supabase Dashboard)
- [x] 소셜 로그인: 실제 로그인 → 세션 유지 → 로그아웃 E2E 정상
- [x] 헤더: 비로그인 Sign In / 로그인 아바타 드롭다운 정상
- [x] 읽기 기록: 상세 페이지 방문 시 자동 기록 + 리스트에서 읽은 글 opacity 감소
- [x] 북마크: 리스트 카드 + 상세 페이지 북마크 토글 동작
- [x] 학습 진도: Handbook 상세 학습 완료 체크 + 카테고리별 진도 바
- [x] 내 서재: `/library` — 읽은 글 / 저장한 글 / 학습 현황 3탭 정상
- [x] `cd frontend && npm run build` → 0 error
- [x] 태스크 전체 `상태=done` + `체크=[x]` 일치
- [x] `Current Doing` 표가 비어 있음(`-`)
- [x] 완료 태스크마다 `증거` 마크 최소 1개 존재

---

## Current Doing (1개 고정)

| Task ID | 상태 | 시작 시점 | Owner |
|---|---|---|---|
| - | - | - | - |

규칙:
- 문서 내 `상태: doing` 태스크가 있으면 이 표에도 반드시 1개만 기입한다.
- 문서 내 `상태: doing` 태스크가 0개면 셀은 `-`를 유지한다.
- 태스크 상태 변경할 때마다 같은 커밋에서 즉시 갱신한다.

---

## 상태 업데이트 규칙

- 통합적 고정: `상태(todo/doing/review/done/blocked)` + `체크([ ]/[x])`를 즉시 사용한다.
- `todo/review/doing/blocked`은 `체크: [ ]`로 유지한다.
- `done`은 반드시 `체크: [x]`로 변경한다.
- `상태`와 `체크`가 불일치하면 무효로 간주한다. 예: `상태: done` + `체크: [ ]` 금지.
- `증거`는 태스크 완료(`상태: done`) 시 필수이며, PR/로그/스크린샷 중 최소 1개 마크를 기록한다.

---

## 태스크 (실행 순서)

### 1. DB 마이그레이션 — 사용자 테이블 4개 `[P3U-DB-01]`
- **체크:** [x]
- **상태:** done
- **목적:** `profiles`, `user_bookmarks`, `reading_history`, `learning_progress` 테이블 생성 + RLS 정책
- **산출물:** `supabase/migrations/00007_user_tables.sql`
- **완료 기준:** 테이블 4개 + RLS 정책 + 인덱스 생성 확인
- **검증:** SQL 파일 존재 + 스키마 구조 확인
- **증거:** `supabase/migrations/00007_user_tables.sql` 커밋 완료
- **참조:** `docs/plans/2026-03-08-user-features-design.md` §4
- **의존성:** 없음

### 2. OAuth 로그인 구현 — 코드 `[P3U-AUTH-01]`
- **체크:** [x]
- **상태:** done
- **목적:** `/login` 페이지 + OAuth 버튼 (GitHub/Google/Kakao) + callback 코드 교환 + httpOnly cookie 설정
- **산출물:** `frontend/src/pages/login.astro`, `frontend/src/pages/api/auth/callback.ts` 수정
- **완료 기준:** OAuth 버튼 클릭 → Supabase redirect 동작 확인, Kakao는 "준비 중" 표시
- **검증:** `npm run build` 0 error + 로컬에서 OAuth redirect 동작
- **증거:** commits dc4b11b, ff1aff1, 025e35a, 076302d (define:vars fix → import.meta.env fix → initLogin fix → Kakao button)
- **참조:** `docs/plans/2026-03-08-user-features-design.md` §3, §6.2
- **의존성:** P3U-DB-01

### 3. OAuth 로그인 — 외부 서비스 설정 `[P3U-AUTH-02]`
- **체크:** [x]
- **상태:** done
- **목적:** GitHub OAuth App, Google Cloud OAuth, Supabase Dashboard Provider 설정 → 실제 로그인 동작
- **산출물:** 외부 서비스 설정 완료 (코드 변경 없음)
- **완료 기준:** GitHub/Google 버튼 클릭 → provider 로그인 → 0to1log.com 으로 redirect → 세션 유지
- **검증:** 프로덕션에서 GitHub/Google 로그인 E2E 수동 테스트
- **증거:** GitHub OAuth App + Google Cloud Console + Supabase Dashboard 설정 완료, 프로덕션 로그인 확인
- **설정 체크리스트:**
  - [x] GitHub OAuth App: callback URL = `https://luwipptjfyjsleqouasj.supabase.co/auth/v1/callback`
  - [x] Google Cloud Console: OAuth 2.0 Client + redirect URI = 위와 동일
  - [x] Google OAuth Consent Screen: 테스트 사용자 등록
  - [x] Supabase Dashboard: GitHub provider 활성화 + Client ID/Secret 입력
  - [x] Supabase Dashboard: Google provider 활성화 + Client ID/Secret 입력
  - [x] Supabase Dashboard: Redirect URLs에 `https://0to1log.com/api/auth/callback` 추가
- **참조:** `docs/plans/2026-03-08-user-features-design.md` §3
- **의존성:** P3U-AUTH-01

### 4. Middleware 확장 — 사용자 경로 보호 `[P3U-MW-01]`
- **체크:** [x]
- **상태:** done
- **목적:** middleware.ts에 3-zone 인증 추가 (public / user-protected / admin-protected)
- **산출물:** `frontend/src/middleware.ts` 수정
- **완료 기준:** `/api/user/*`, `/library` 경로는 로그인 필수, 비로그인 시 redirect/401
- **검증:** `npm run build` 0 error
- **증거:** middleware.ts 3-zone 구현 커밋 완료
- **참조:** `docs/plans/2026-03-08-user-features-design.md` §3.3
- **의존성:** P3U-AUTH-01

### 5. User API 엔드포인트 4종 `[P3U-API-01]`
- **체크:** [x]
- **상태:** done
- **목적:** profile, bookmarks, reading-history, learning-progress CRUD API
- **산출물:** `frontend/src/pages/api/user/profile.ts`, `bookmarks.ts`, `reading-history.ts`, `learning-progress.ts`
- **완료 기준:** 인증된 사용자만 접근 가능, RLS 기반 데이터 격리
- **검증:** `npm run build` 0 error
- **증거:** 4개 API 파일 커밋 완료
- **참조:** `docs/plans/2026-03-08-user-features-design.md` §5
- **의존성:** P3U-MW-01

### 6. Navigation — Sign In / 아바타 드롭다운 `[P3U-NAV-01]`
- **체크:** [x]
- **상태:** done
- **목적:** 비로그인 시 Sign In 링크, 로그인 시 아바타 + 드롭다운 (Library, Admin, Sign Out)
- **산출물:** `frontend/src/components/Navigation.astro` 수정
- **완료 기준:** 로그인 상태에 따른 UI 분기 정상
- **검증:** `npm run build` 0 error
- **증거:** Navigation.astro 커밋 완료
- **참조:** `docs/plans/2026-03-08-user-features-design.md` §6.1
- **의존성:** P3U-AUTH-01

### 7. 읽기 기록 + 북마크 — Log/Handbook 페이지 통합 `[P3U-UI-01]`
- **체크:** [x]
- **상태:** done
- **목적:** 상세 페이지 자동 읽기 기록 + 북마크 토글 + 리스트에서 읽은 글 opacity 감소
- **산출물:** EN/KO log/handbook 리스트 및 상세 페이지 수정, `frontend/src/scripts/bookmark.ts`
- **완료 기준:** 로그인 사용자의 읽기 기록 자동 기록 + 북마크 동작 + 비로그인 시 redirect
- **검증:** `npm run build` 0 error
- **증거:** log/handbook 페이지 + bookmark.ts 커밋 완료
- **참조:** `docs/plans/2026-03-08-user-features-design.md` §6.3~6.5
- **의존성:** P3U-API-01

### 8. Handbook 학습 진도 `[P3U-UI-02]`
- **체크:** [x]
- **상태:** done
- **목적:** Handbook 상세에 "학습 완료" 체크 버튼 + learning_progress API 연동
- **산출물:** EN/KO handbook 상세 페이지 수정
- **완료 기준:** read → learned 전환 + 비로그인 시 버튼 숨김
- **검증:** `npm run build` 0 error
- **증거:** handbook 상세 페이지 커밋 완료
- **참조:** `docs/plans/2026-03-08-user-features-design.md` §6.6
- **의존성:** P3U-UI-01

### 9. 내 서재 페이지 `[P3U-LIB-01]`
- **체크:** [x]
- **상태:** done
- **목적:** `/library` — 읽은 글 / 저장한 글 / 학습 현황 3탭 페이지
- **산출물:** `frontend/src/pages/library/index.astro`
- **완료 기준:** 3탭 동작 + 카테고리별 학습 진도 바 + 비로그인 시 redirect
- **검증:** `npm run build` 0 error
- **증거:** library/index.astro 커밋 완료
- **참조:** `docs/plans/2026-03-08-user-features-design.md` §6.7
- **의존성:** P3U-UI-02

### 10. User feature CSS `[P3U-CSS-01]`
- **체크:** [x]
- **상태:** done
- **목적:** 로그인/북마크/읽기기록/서재 관련 CSS 스타일 추가
- **산출물:** `frontend/src/styles/global.css` 수정
- **완료 기준:** login-oauth-btn, user-avatar, user-dropdown, bookmark, library-tabs 등 스타일 정상
- **검증:** `npm run build` 0 error
- **증거:** global.css 커밋 완료
- **참조:** `docs/plans/2026-03-08-user-features-design.md` §6
- **의존성:** 없음

### 11. OAuth E2E 검증 `[P3U-QA-01]`
- **체크:** [x]
- **상태:** done
- **목적:** 프로덕션에서 소셜 로그인 → 북마크 → 읽기 기록 → 학습 진도 → 서재 전체 흐름 검증
- **산출물:** 수동 E2E 테스트 결과
- **완료 기준:** 설계 문서 §12의 검증 항목 16개 전체 통과
- **검증:** 프로덕션에서 수동 테스트
- **증거:** 프로덕션 E2E 수동 테스트 통과
- **참조:** `docs/plans/2026-03-08-user-features-design.md` §12
- **의존성:** P3U-AUTH-02

---

## 의존성 순서

```
P3U-DB-01 → P3U-AUTH-01 → P3U-AUTH-02 → P3U-QA-01
                ↓
            P3U-MW-01 → P3U-API-01 → P3U-UI-01 → P3U-UI-02 → P3U-LIB-01
                ↓
            P3U-NAV-01

P3U-CSS-01 (독립)
```

---

## 이전 스프린트 요약 (Phase 2C-EXP)

> Phase 2C-EXP (2026-03-07) — 게이트 전체 통과, 6개 태스크 완료.
> - Newsprint 토큰/테마/공통 컴포넌트 정리
> - /en|ko/log 리스트/상세 + 다국어 스위처
> - 썸네일 이미지 newsprint 필터
> - Admin Editor 화면(마크다운 작성/미리보기)
> - Admin Editor 상태/권한/에러 처리(mock)
> - 반응형/접근성/성능 QA (Perf 87 / Acc 98 / SEO 100 / BP 77)

---

## 다음 스프린트 예고

Phase 3-USER 게이트 통과 후 → **Phase 3-Intelligence** (AI 추천 + 학습 고도화)
