# ACTIVE SPRINT — Phase 1a Foundation

> **스프린트 시작:** 2026-03-05
> **목표:** Astro + Supabase + SEO 기반 확보, 4개 페이지 골격 완성
> **참조:** MASTER → `docs/IMPLEMENTATION_PLAN.md` | 스펙 → `docs/03~05`

---

## 스프린트 완료 게이트

- [ ] `astro build` — 0 error, 0 warning
- [ ] Vercel 자동 배포 — main push → 프로덕션 배포 성공
- [ ] Supabase 읽기 연동 — published 포스트 브라우저 렌더링
- [ ] SEO — `/sitemap.xml` 200 응답 + JSON-LD 존재
- [ ] 보안 — `POST /api/revalidate` secret 불일치 시 401
- [ ] RLS — anon으로 draft 조회 시 0 rows
- [ ] 태스크 전체 `상태=done` + `체크=[x]` 일치
- [ ] `Current Doing` 슬롯이 비어 있음(`-`)
- [ ] 완료 태스크마다 `증거` 링크 최소 1개 존재

---

## Current Doing (1개 고정)

| Task ID | 상태 | 시작 시각 | Owner |
|---|---|---|---|
| - | - | - | Amy |

규칙:
- 문서 내 `상태: doing` 태스크가 있으면 이 표에는 반드시 1개만 기입한다.
- 문서 내 `상태: doing` 태스크가 0개면 표는 `-`를 유지한다.
- 태스크 상태 변경 시 이 표를 같은 커밋에서 함께 갱신한다.

---

## 상태 업데이트 규칙

- 혼합형 고정: `상태(todo/doing/review/done/blocked)` + `체크([ ]/[x])`를 함께 사용한다.
- `todo/review/doing/blocked`는 `체크: [ ]`로 유지한다.
- `done`은 반드시 `체크: [x]`로 변경한다.
- `상태`와 `체크`가 불일치하면 무효로 간주한다. 예: `상태: done` + `체크: [ ]` 금지.
- `증거`는 태스크 완료(`상태: done`) 시 필수이며, PR/로그/스크린샷 중 최소 1개 링크를 남긴다.

---

## 태스크 (실행 순서)

### 1. Repo + Vercel 초기화 `[P1-BOOT-01]`
- **체크:** [x]
- **상태:** done
- **산출물:** GitHub repo + Vercel 프로젝트 연결
- **완료 기준:** main push → 자동 배포
- **검증:** Vercel 배포 로그 확인
- **증거:** [Production Domain](https://0to1log.com), [Vercel Default Domain](https://0to1log.vercel.app)
- **참조:** 01 §Site Map, 05 §Vercel

### 2. Supabase 프로젝트 생성 `[P1-BOOT-02]`
- **체크:** [x]
- **상태:** done
- **산출물:** Supabase 프로젝트 + URL/anon key
- **완료 기준:** Dashboard에서 프로젝트 접근 가능
- **검증:** Supabase Dashboard 확인
- **증거:** [Supabase Dashboard](https://supabase.com/dashboard), [Supabase API Settings](https://supabase.com/dashboard/project/luwipptjfyjsleqouasj/settings/api)
- **참조:** 03 §DB 스키마, 05 §Supabase

### 3. Astro/Tailwind/Motion One 골격 `[P1-FE-01]`
- **체크:** [x]
- **상태:** done
- **산출물:** 레이아웃 + Home/Log/Portfolio/Admin 페이지 골격
- **완료 기준:** `astro build` 성공 + 4개 페이지 라우팅
- **검증:** `astro build` + 브라우저 확인
- **증거:** 커밋 `a8fcb88`~`ed13082`, `npm run build` 성공 (0 errors)
- **참조:** 04 §디자인 시스템, 04 §페이지 구조

### 4. 기본 DB 스키마 + RLS + 인증 `[P1-DB-01]`
- **체크:** [x]
- **상태:** done
- **산출물:** posts/admin_users 테이블 + RLS 정책
- **완료 기준:** Admin만 쓰기, public은 published만 읽기
- **검증:** SQL 시나리오 테스트 (anon SELECT draft → 0 rows, non-admin INSERT → RLS violation)
- **증거:** 커밋 `0ae69bd` — `supabase/migrations/00001_initial_schema.sql` (Supabase SQL Editor에서 실행 필요)
- **참조:** 03 §2 인증, 03 §3 DB 스키마

### 5. Supabase 읽기 연동 `[P1-FE-02]`
- **체크:** [x]
- **상태:** done
- **산출물:** Log 페이지 list/detail 렌더링
- **완료 기준:** published 포스트 목록 + 상세 페이지 노출
- **검증:** 브라우저 수동 확인
- **증거:** 커밋 `be37cea` — EN/KO 로그 페이지 Supabase 쿼리 연동 (locale 필터 적용)
- **참조:** 04 §11 Supabase 연동
- **의존성:** P1-FE-01, P1-DB-01

### 6. SEO/메타/사이트맵 `[P1-SEO-01]`
- **체크:** [x]
- **상태:** done
- **산출물:** JSON-LD (NewsArticle) + robots.txt + sitemap.xml + hreflang
- **완료 기준:** `/sitemap.xml` 200 응답 + 구조화 데이터 존재
- **검증:** URL 접근 + Rich Results Test
- **증거:** 커밋 `7ac506c` — JSON-LD 조건부 출력 + robots.txt + sitemap-index.xml 빌드 확인
- **참조:** 04 §SEO, 06 §4.1

### 7. Revalidate 보안 계약 `[P1-SEO-02]`
- **체크:** [x]
- **상태:** done
- **산출물:** `/api/revalidate` 엔드포인트 + REVALIDATE_SECRET 검증
- **완료 기준:** secret 불일치 → 401, 정상 → 200 + 캐시 무효화
- **검증:** curl 수동 호출 (잘못된 secret → 401, 올바른 secret → 200)
- **증거:** 커밋 `8972ad4` — `/api/revalidate` stub + Bearer secret 검증 구현
- **참조:** 04 §Policy Addendum, 05 §Revalidate 보안
- **의존성:** P1-FE-01

### 8. 반응형/접근성 QA `[P1-QA-01]`
- **체크:** [ ]
- **상태:** todo
- **산출물:** QA 체크 결과
- **완료 기준:** mobile/tablet/desktop 3개 브레이크포인트 + reduced-motion 검증
- **검증:** 수동 테스트 (Chrome DevTools)
- **증거:** PR/로그/스크린샷 링크 최소 1개 (완료 시 필수)
- **참조:** 04 §접근성
- **의존성:** P1-FE-02, P1-SEO-01, P1-SEO-02

---

## 의존성 흐름

```
P1-BOOT-01 ──┬── P1-FE-01 ──┬── P1-FE-02 ──── P1-QA-01
P1-BOOT-02 ──┘              │               ↗
              P1-DB-01 ─────┘  P1-SEO-01 ──┤
                                P1-SEO-02 ──┘
```

---

## 다음 스프린트 예고

Phase 1a 게이트 통과 시 → **Phase 1b Analytics** (P1-ANL-01, P1-ANL-02)
