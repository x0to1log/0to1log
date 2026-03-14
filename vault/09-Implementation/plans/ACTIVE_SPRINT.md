# ACTIVE SPRINT — Phase 3A-SEC (보안 하드닝)

> **스프린트 시작:** 2026-03-08
> **스프린트 완료:** 2026-03-09
> **목표:** CSP nonce 기반 전환으로 `unsafe-inline` 제거 + 보안 점검
> **참조:** MASTER → `docs/IMPLEMENTATION_PLAN.md`
> **이전 스프린트:** Phase 3-USER — 2026-03-08 게이트 전체 통과

---

> UI naming boundary: public labels use `AI News`, `Handbook`, `Library`; internal/admin labels use `Posts`; compatibility route remains `/{locale}/log/`.

> Status note: `3B-SHARE` is complete and reflected in `docs/IMPLEMENTATION_PLAN.md`.

## 스프린트 완료 게이트

- [x] CSP `script-src`에서 `unsafe-inline` 제거, nonce 기반으로 전환
- [x] 모든 인라인 스크립트(FOUC, GA4, Clarity, 날짜)에 nonce 속성 부여
- [x] vercel.json 정적 CSP 제거, middleware 동적 CSP 설정
- [x] `cd frontend && npm run build` → 0 error
- [x] 로컬 dev에서 CSP 위반 에러 없음
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

### 1. env.d.ts — Locals 타입 업데이트 `[P3A-TYPE-01]`
- **체크:** [x]
- **상태:** done
- **목적:** `App.Locals`에 `cspNonce` 타입 추가
- **산출물:** `frontend/src/env.d.ts` 수정
- **완료 기준:** TypeScript 컴파일 에러 없이 `Astro.locals.cspNonce` 접근 가능
- **검증:** `npm run build` 0 error
- **참조:** `docs/IMPLEMENTATION_PLAN.md` §3A-SEC
- **의존성:** 없음
- **증거:** `env.d.ts`에 `cspNonce?: string` 추가 완료

### 2. Middleware — nonce 생성 + 동적 CSP 헤더 `[P3A-MW-01]`
- **체크:** [x]
- **상태:** done
- **목적:** 매 요청마다 nonce 생성 → `context.locals.cspNonce` 저장 → response에 CSP 헤더 동적 설정
- **산출물:** `frontend/src/middleware.ts` 수정
- **완료 기준:** response 헤더에 `Content-Security-Policy`가 `nonce-*` 포함, `unsafe-inline` 없음 (script-src)
- **검증:** `npm run build` 0 error
- **참조:** `docs/IMPLEMENTATION_PLAN.md` §3A-SEC
- **의존성:** P3A-TYPE-01
- **증거:** `buildCspHeader()`, `nextWithCsp()` 함수 추가, 모든 return 경로에 CSP 적용

### 3. MainLayout — 인라인 스크립트 nonce 추가 `[P3A-LAYOUT-01]`
- **체크:** [x]
- **상태:** done
- **목적:** FOUC 방지(2개), GA4(2개), Clarity(1개) 인라인 스크립트에 `nonce={nonce}` 추가
- **산출물:** `frontend/src/layouts/MainLayout.astro` 수정
- **완료 기준:** 5개 `<script is:inline>` 태그 모두 nonce 속성 포함
- **검증:** `npm run build` 0 error
- **참조:** `docs/IMPLEMENTATION_PLAN.md` §3A-SEC
- **의존성:** P3A-MW-01
- **증거:** 5개 `<script is:inline nonce={nonce}>` 태그 확인

### 4. NewsprintShell — 날짜 스크립트 nonce 추가 `[P3A-SHELL-01]`
- **체크:** [x]
- **상태:** done
- **목적:** 날짜 로컬라이즈 인라인 스크립트에 nonce 추가
- **산출물:** `frontend/src/components/newsprint/NewsprintShell.astro` 수정
- **완료 기준:** `<script is:inline>` 태그에 nonce 속성 포함
- **검증:** `npm run build` 0 error
- **참조:** `docs/IMPLEMENTATION_PLAN.md` §3A-SEC
- **의존성:** P3A-MW-01
- **증거:** `<script is:inline nonce={nonce}>` 적용 완료

### 5. vercel.json — 정적 CSP 제거 `[P3A-VERCEL-01]`
- **체크:** [x]
- **상태:** done
- **목적:** middleware에서 동적 CSP를 설정하므로 vercel.json의 정적 CSP 항목 제거
- **산출물:** `frontend/vercel.json` 수정
- **완료 기준:** CSP 헤더 항목만 제거, 나머지 보안 헤더 유지
- **검증:** vercel.json 구조 확인
- **참조:** `docs/IMPLEMENTATION_PLAN.md` §3A-SEC
- **의존성:** P3A-MW-01
- **증거:** CSP 항목 제거, X-Content-Type-Options/X-Frame-Options/X-XSS-Protection/Referrer-Policy 유지

### 6. auth/callback.astro — FOUC 스크립트 nonce 추가 `[P3A-AUTH-01]`
- **체크:** [x]
- **상태:** done
- **목적:** auth callback 페이지의 별도 FOUC 방지 스크립트에 nonce 추가
- **산출물:** `frontend/src/pages/auth/callback.astro` 수정
- **완료 기준:** `<script is:inline>` 태그에 nonce 속성 포함
- **검증:** `npm run build` 0 error
- **참조:** `docs/IMPLEMENTATION_PLAN.md` §3A-SEC
- **의존성:** P3A-MW-01
- **증거:** `<script is:inline nonce={nonce}>` 적용 + `lang="en"` 추가

### 7. 빌드 검증 + CLAUDE.md 업데이트 `[P3A-QA-01]`
- **체크:** [x]
- **상태:** done
- **목적:** 전체 빌드 통과 + frontend CLAUDE.md 보안 섹션 업데이트
- **산출물:** `npm run build` 로그 + `frontend/CLAUDE.md` 수정
- **완료 기준:** 빌드 0 error
- **검증:** `cd frontend && npm run build`
- **참조:** `docs/IMPLEMENTATION_PLAN.md` §3A-SEC
- **의존성:** P3A-LAYOUT-01, P3A-SHELL-01, P3A-VERCEL-01, P3A-AUTH-01
- **증거:** 빌드 성공 (0 error) + CLAUDE.md 보안 섹션 nonce 기반 CSP 문서화

### 8. 보안 리뷰 — Open Redirect 수정 `[P3A-SEC-01]` (HIGH)
- **체크:** [x]
- **상태:** done
- **목적:** `api/auth/callback.ts`의 `redirectTo` 파라미터 검증 없이 `Location` 헤더에 사용 → 외부 URL 유도 가능 취약점 수정
- **산출물:** `frontend/src/pages/api/auth/callback.ts` 수정
- **완료 기준:** `sanitizeRedirect()` 함수로 `/`로 시작하되 `//`는 거부하는 검증 적용
- **검증:** `npm run build` 0 error
- **참조:** Web Interface Guidelines 리뷰
- **의존성:** P3A-QA-01
- **증거:** `sanitizeRedirect()` 함수 추가, GET handler에 적용

### 9. 보안 리뷰 — strict-dynamic 추가 `[P3A-SEC-02]` (MED)
- **체크:** [x]
- **상태:** done
- **목적:** Clarity 스크립트의 동적 `<script>` 삽입이 nonce CSP에서 차단될 수 있어 `strict-dynamic` 추가
- **산출물:** `frontend/src/middleware.ts` 수정
- **완료 기준:** CSP `script-src`에 `'strict-dynamic'` 포함
- **검증:** `npm run build` 0 error
- **참조:** Web Interface Guidelines 리뷰
- **의존성:** P3A-MW-01
- **증거:** `buildCspHeader()`에 `'strict-dynamic'` 추가 완료

### 10. 보안 리뷰 — callback.astro lang 속성 `[P3A-SEC-03]` (LOW)
- **체크:** [x]
- **상태:** done
- **목적:** `auth/callback.astro`의 `<html>` 태그에 `lang` 속성 누락 수정
- **산출물:** `frontend/src/pages/auth/callback.astro` 수정
- **완료 기준:** `<html lang="en" data-theme="light">`
- **검증:** 소스 확인
- **참조:** Web Interface Guidelines 리뷰
- **의존성:** P3A-AUTH-01
- **증거:** `lang="en"` 추가 완료 (P3A-AUTH-01과 동시 적용)

### 11. 보안 리뷰 — color-scheme 속성 `[P3A-SEC-04]` (LOW)
- **체크:** [x]
- **상태:** done
- **목적:** FOUC 방지 스크립트에서 다크 테마 설정 시 `color-scheme`도 설정 → 네이티브 input/scrollbar 테마 매칭
- **산출물:** `frontend/src/layouts/MainLayout.astro` 수정
- **완료 기준:** FOUC 스크립트에 `document.documentElement.style.colorScheme` 설정 로직 포함
- **검증:** 소스 확인
- **참조:** Web Interface Guidelines 리뷰
- **의존성:** P3A-LAYOUT-01
- **증거:** `var cs = { dark: 'dark', light: 'light', pink: 'light' };` + `colorScheme` 설정 추가

### 12. 보안 리뷰 — OAuth 버튼 이중 클릭 방지 `[P3A-SEC-05]` (LOW)
- **체크:** [x]
- **상태:** done
- **목적:** 로그인 페이지 OAuth 버튼 클릭 시 모든 버튼 비활성화 + "Signing in…" 텍스트 변경
- **산출물:** `frontend/src/pages/login.astro` 수정
- **완료 기준:** 클릭 후 버튼 disabled + 텍스트 변경
- **검증:** 소스 확인
- **참조:** Web Interface Guidelines 리뷰
- **의존성:** 없음
- **증거:** `btn.disabled = true; btn.textContent = 'Signing in…'` 로직 추가

---

## 의존성 순서

```
P3A-TYPE-01 → P3A-MW-01 → P3A-LAYOUT-01 → P3A-QA-01 → P3A-SEC-01
                  ↓                                       ↓
              P3A-SHELL-01 → P3A-QA-01              P3A-SEC-02
                  ↓
              P3A-VERCEL-01 → P3A-QA-01
                  ↓
              P3A-AUTH-01 → P3A-QA-01 → P3A-SEC-03
```

---

## 이전 스프린트 요약 (Phase 3-USER)

> Phase 3-USER (2026-03-08) — 게이트 전체 통과, 11개 태스크 완료.
> - DB 마이그레이션 (profiles, bookmarks, reading_history, learning_progress)
> - OAuth 로그인 (GitHub/Google) 코드 + 외부 설정
> - Middleware 3-zone 인증
> - User API 4종 (profile, bookmarks, reading-history, learning-progress)
> - Navigation Sign In / 아바타 드롭다운
> - 읽기 기록 + 북마크 통합
> - Handbook 학습 진도
> - 내 서재 페이지 (/library)
> - OAuth E2E 검증

---

## 다음 스프린트 예고

Phase 3A-SEC 게이트 통과 → **Phase 3-Intelligence** (AI 추천 + 학습 고도화)
