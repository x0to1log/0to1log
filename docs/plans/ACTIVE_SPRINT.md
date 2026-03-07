# ACTIVE SPRINT — Phase 2C-EXP (Frontend Experience)

> **스프린트 시작:** 2026-03-07
> **목표:** Newsprint 테마 완성 + 리스트/상세 고도화 + 반응형/접근성/성능 QA
> **참조:** MASTER → `docs/IMPLEMENTATION_PLAN.md` | 스펙 → `docs/04~06`
> **이전 스프린트:** Phase 2B-OPS — 2026-03-07 게이트 전체 통과

---

## 스프린트 완료 게이트

- [ ] 반응형: mobile/tablet/desktop 레이아웃 정상
- [ ] 접근성: `prefers-reduced-motion`, 키보드 포커스, 대비 기준 통과
- [ ] Lighthouse: Perf/Best/SEO/Acc 각각 `>= 85`
- [ ] Core Web Vitals 목표: `LCP < 2.8s`, `CLS < 0.1`, `INP < 250ms`
- [ ] `cd frontend && npm run build` — 0 error
- [ ] Admin Editor mock 플로우(목록 → 상세 → 편집/미리보기 → 발행 CTA) 정상
- [ ] 태스크 전체 `상태=done` + `체크=[x]` 일치
- [ ] `Current Doing` 슬롯이 비어 있음(`-`)
- [ ] 완료 태스크마다 `증거` 링크 최소 1개 존재

---

## Current Doing (1개 고정)

| Task ID | 상태 | 시작 시각 | Owner |
|---|---|---|---|
| - | - | - | - |

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

### 1. Newsprint 토큰/테마/공통 컴포넌트 정리 `[P2C-UI-11]`
- **체크:** [x]
- **상태:** done
- **목적:** 기존 newsprint 컴포넌트(Shell, ListCard, SideRail, CategoryFilter, ArticleLayout) 정리 + 테마 토큰 통합 (dark/light/pink)
- **산출물:** `frontend/src/components/newsprint/` 정리 + `frontend/src/styles/global.css` 토큰 체계화
- **완료 기준:** `npm run build` 0 error + 3 테마 preview 페이지 정상 렌더링
- **검증:** `cd frontend && npm run build` + preview 페이지 수동 확인
- **증거:** commits f3c39c5..dc3ced5 (6 commits: 컴포넌트 5개 + CSS 토큰 3테마 + preview 3페이지 + 브랜딩 교체)
- **참조:** IMPLEMENTATION_PLAN §3 2C-EXP
- **의존성:** 없음

### 2. /en|ko/log 리스트/상세 + 다국어 스위처 + 화면 상태 `[P2C-UI-12]`
- **체크:** [x]
- **상태:** done
- **목적:** 리스트/상세 페이지에 newsprint 스타일 본격 적용 + 다국어 스위처 + empty/error/loading 상태 처리
- **산출물:** `frontend/src/pages/en|ko/log/` 페이지 업데이트 + `NewsprintNotice` 컴포넌트
- **완료 기준:** EN/KO 리스트/상세 정상 렌더링 + 언어 전환 동작 + 빈 상태 표시
- **검증:** `npm run build` 0 error ✅
- **증거:** 이번 커밋 (i18n 키 3개 + NewsprintNotice 컴포넌트 + 리스트/상세 에러 처리 + 404 UI)
- **비고:** Loading state는 SSR 구조상 해당 없음 (서버가 완성된 HTML 전송). 미연결/env 미설정 → empty, 쿼리 실패 → error로 구분.
- **참조:** IMPLEMENTATION_PLAN §3 2C-EXP
- **의존성:** P2C-UI-11

### 3. 썸네일 이미지 newsprint 필터 `[P2C-UI-13]`
- **체크:** [x]
- **상태:** done
- **목적:** Featured 카드에 og_image_url 기반 썸네일 렌더링 + 기존 .img-newsprint 필터 연결
- **산출물:** `global.css` grid 레이아웃 + EN/KO 리스트 featured 카드 이미지 + preview 3페이지 mock 이미지
- **완료 기준:** 이미지 기본 흑백+세피아 + hover 시 컬러 복원 transition 동작
- **검증:** `npm run build` 0 error ✅ + preview 페이지 시각 확인
- **증거:** commits 2f1316c..920102b (CSS grid + EN/KO featured thumbnail + preview mock images)
- **비고:** 나머지 카드는 텍스트 전용 유지. 상세 페이지 hero 이미지는 별도 태스크로 분리.
- **참조:** IMPLEMENTATION_PLAN §3 2C-EXP
- **의존성:** P2C-UI-12

### 4. Admin Editor 화면(마크다운 작성/미리보기) `[P2C-UI-14]`
- **체크:** [x]
- **상태:** done
- **목적:** `/admin`에서 드래프트 편집 화면(마크다운 작성 + 미리보기 + Save/Publish 액션)을 newsprint 톤으로 구현
- **산출물:** Admin Editor UI 컴포넌트/페이지 업데이트
- **완료 기준:** 편집 입력, 미리보기 전환, Save/Publish CTA 노출 및 기본 동작(mock) 확인
- **검증:** `cd frontend && npm run build` 0 error ✅
- **증거:** commits d2015c8..529886c (milkdown install + admin CSS + dashboard + editor page)
- **참조:** IMPLEMENTATION_PLAN §3 2C-EXP, 04_Frontend_Spec §3-5
- **의존성:** P2C-UI-13

### 5. Admin Editor 상태/권한/에러 처리(mock) `[P2C-UI-15]`
- **체크:** [ ]
- **상태:** todo
- **목적:** Admin Editor의 loading/empty/404/401/403 상태와 저장/발행 피드백을 OpenAPI 고정 스키마 기반 mock으로 구현
- **산출물:** 상태별 UI, 오류 메시지, 액션 피드백 처리
- **완료 기준:** 권한/에러 상태별 화면과 메시지가 일관되게 노출되고, 편집 플로우가 중단 없이 복구 가능
- **검증:** `cd frontend && npm run build` + 상태별 수동 시나리오 점검
- **증거:** -
- **참조:** IMPLEMENTATION_PLAN §1 Hard Gate, §3 2C-EXP
- **의존성:** P2C-UI-14

### 6. 반응형/접근성/성능 QA `[P2C-QA-11]`
- **체크:** [ ]
- **상태:** todo
- **목적:** Lighthouse 측정 + Core Web Vitals + 접근성 점검
- **산출물:** Lighthouse 리포트 (Perf/Best/SEO/Acc >= 85) + 접근성 점검 결과
- **완료 기준:** Lighthouse 4개 항목 모두 >= 85, CWV 목표 충족, 접근성 기본 통과
- **검증:** Lighthouse CLI 또는 DevTools 측정 결과 캡처
- **증거:** -
- **참조:** IMPLEMENTATION_PLAN §3 2C Gate
- **의존성:** P2C-UI-15

---

## 의존성 흐름

```
P2C-UI-11 → P2C-UI-12 → P2C-UI-13 → P2C-UI-14 → P2C-UI-15 → P2C-QA-11
```

---

## 이전 스프린트 요약 (Phase 2B-OPS)

> Phase 2B-OPS (2026-03-07) — 게이트 전체 통과, 4개 태스크 완료, 49 tests passed.
> - OpenAPI 스키마 고정 (12 schemas, 6 endpoints)
> - AI Agent 3종 구현 (Ranking gpt-4o-mini, Research/Business gpt-4o)
> - Admin CRUD 실구현 (list/get/publish/update + 401/403 분리)
> - Cron skeleton (secret 검증 + 202 반환)

---

## 이전 스프린트 요약 (Phase 2A)

> Phase 2A (2026-03-06 ~ 03-07) — 게이트 전체 통과, 6개 태스크 완료.
> - DB 마이그레이션 (`supabase/migrations/00002_pipeline_tables.sql`, 5개 테이블 + RLS)
> - Pydantic 스키마 정의 (ranking, research, business, common)
> - 뉴스 수집 서비스 Mock 테스트 완료 (Tavily/HN/GitHub + dedup)
> - 파이프라인 Lock/Stale Recovery 구현 및 테스트 (8 passed)
> - Security 미들웨어 + Vercel Cron Trigger skeleton 완료

---

## 다음 스프린트 예고

Phase 2C 게이트 통과 시 → **Phase 2D-INT** (통합/E2E: Mock 제거 + 실API 연동 + E2E 테스트)

---

## 2C-EXP Addendum (Stitch Compatibility)

- [x] `2C-UI-01` Prototype compatibility cleanup completed
  Evidence: `frontend/example_dark.html`, `frontend/example_light.html`, `frontend/example_list.html`
- [x] `2C-UI-02` `/en|ko/log` list/detail style migration completed
  Evidence: `frontend/src/pages/en/log/index.astro`, `frontend/src/pages/ko/log/index.astro`, `frontend/src/pages/en/log/[slug].astro`, `frontend/src/pages/ko/log/[slug].astro`
- [x] `2C-QA-01` Preview routes added for visual validation
  Evidence: `frontend/src/pages/preview/newsprint-dark.astro`, `frontend/src/pages/preview/newsprint-light.astro`
