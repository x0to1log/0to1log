# ACTIVE SPRINT — Handbook H1 (Read-Only)

> **스프린트 시작:** 2026-03-07
> **목표:** `/en|ko/handbook` 읽기 전용 기능을 메인 app과 병렬로 구현한다.
> **참조:** `docs/08_Handbook.md`, `docs/IMPLEMENTATION_PLAN.md`
> **운영 방식:** 메인 `ACTIVE_SPRINT.md`와 분리된 병렬 스프린트

---

## 스프린트 완료 게이트

- [x] `handbook_terms` 테이블 + RLS 생성 완료
- [x] Notion → Supabase 마이그레이션 1회 완료
- [x] `/en/handbook/`, `/ko/handbook/` 목록 정상 렌더링
- [x] `/en/handbook/[slug]/`, `/ko/handbook/[slug]/` 상세 정상 렌더링
- [x] Handbook 검색 동작
- [x] Navigation Handbook 링크 동작
- [x] `cd frontend && npm run build` 0 error
- [x] handbook 태스크 전체 `상태=done` + `체크=[x]` 일치
- [x] `Current Doing`이 비어 있음 (`-`)

---

## Current Doing (1개 고정)

| Task ID | 상태 | 시작 시각 | Owner |
|---|---|---|---|
| - | - | - | - |

---

## 병렬 작업 규칙

- handbook sprint는 메인 sprint와 별도 관리한다.
- handbook sprint의 `doing`은 항상 1개만 유지한다.
- handbook 작업도 기본적으로 `main` 브랜치에서 직접 진행한다.
- handbook는 별도 sprint 문서로만 분리 관리하고, git 브랜치로 분리 관리하지 않는다.
- 공유 파일 변경은 최소화한다: `Navigation.astro`, `src/i18n/index.ts`, 검색/탐색 문서.
- 공유 파일 변경이 필요하면 handbook 전용 커밋으로 분리한다.
- 메인 sprint와 충돌하면 handbook 변경을 작은 커밋으로 나눠 순차 적용한다.
- `/portfolio` 작업은 handbook보다 우선순위가 낮다.

---

## 태스크

### 1. handbook_terms 테이블 생성 `[H1-DB-01]`
- 체크: [x]
- 상태: done
- 목적: handbook 전용 Supabase 테이블과 RLS를 만든다.
- 산출물: `supabase/migrations/00006_handbook_terms.sql`
- 완료 기준: 테이블/인덱스/RLS 정책 생성 확인
- 검증 명령: Supabase SQL 실행 후 `SELECT * FROM handbook_terms LIMIT 1;`
- 통과 조건: 테이블 존재, policy 생성 확인
- 증거: -
- 참조: `docs/08_Handbook.md` H1-DB-01
- 의존성: 없음

### 2. Notion → Supabase 마이그레이션 `[H1-DB-02]`
- 체크: [x]
- 상태: done
- 목적: 기존 Notion Words DB를 handbook_terms로 1회 이관한다.
- 산출물: `scripts/migrate-handbook-from-notion.ts`
- 완료 기준: Notion 용어 수와 DB row 수 일치
- 검증 명령: `SELECT count(*) FROM handbook_terms;`
- 통과 조건: Notion 용어 수와 동일, 샘플 3건 본문 일치
- 증거: -
- 참조: `docs/08_Handbook.md` H1-DB-02
- 의존성: H1-DB-01

### 3. i18n 문자열 추가 `[H1-FE-01]`
- 체크: [x]
- 상태: done
- 목적: handbook용 UI 문구를 EN/KO에 추가한다.
- 산출물: `frontend/src/i18n/index.ts`
- 완료 기준: handbook 관련 키 추가 완료
- 검증 명령: `cd frontend && npm run check`
- 통과 조건: 0 error
- 증거: -
- 참조: `docs/08_Handbook.md` H1-FE-01
- 의존성: 없음

### 4. Handbook 목록 페이지 `[H1-FE-02]`
- 체크: [x]
- 상태: done
- 목적: `/en/handbook/`, `/ko/handbook/` 목록 페이지를 만든다.
- 산출물: `frontend/src/pages/en/handbook/index.astro`, `frontend/src/pages/ko/handbook/index.astro`
- 완료 기준: published handbook terms 목록 렌더링
- 검증 명령: `cd frontend && npm run build`
- 통과 조건: 0 error + 목록 페이지 렌더링 확인
- 증거: -
- 참조: `docs/08_Handbook.md` H1-FE-02
- 의존성: H1-DB-01, H1-FE-01

### 5. Handbook 상세 페이지 `[H1-FE-03]`
- 체크: [x]
- 상태: done
- 목적: `/en/handbook/[slug]/`, `/ko/handbook/[slug]/` 상세 페이지를 만든다.
- 산출물: `frontend/src/pages/en/handbook/[slug].astro`, `frontend/src/pages/ko/handbook/[slug].astro`
- 완료 기준: handbook 본문과 related terms 정상 렌더링
- 검증 명령: `cd frontend && npm run build`
- 통과 조건: 0 error + 상세 페이지 렌더링 확인
- 증거: -
- 참조: `docs/08_Handbook.md` H1-FE-03
- 의존성: H1-DB-01, H1-FE-01

### 6. Navigation 링크 추가 `[H1-FE-04]`
- 체크: [x]
- 상태: done
- 목적: handbook를 메인 탐색에 노출한다.
- 산출물: `frontend/src/components/Navigation.astro`
- 완료 기준: locale별 handbook 링크 동작
- 검증 명령: `cd frontend && npm run build`
- 통과 조건: 0 error + 링크 이동 확인
- 증거: -
- 참조: `docs/08_Handbook.md` H1-FE-04
- 의존성: H1-FE-02

### 7. Handbook 검색 `[H1-FE-05]`
- 체크: [x]
- 상태: done
- 목적: handbook 목록에서 영어/한국어 키워드 검색을 지원한다.
- 산출물: handbook index page updates
- 완료 기준: term/korean_name 검색과 no-result 상태 동작
- 검증 명령: `cd frontend && npm run build`
- 통과 조건: 0 error + 검색 결과 확인
- 증거: -
- 참조: `docs/08_Handbook.md` H1-FE-05
- 의존성: H1-FE-02

### 8. QA `[H1-QA-01]`
- 체크: [x]
- 상태: done
- 목적: handbook read-only 기능의 반응형/접근성/빌드를 확인한다.
- 산출물: QA 결과 기록
- 완료 기준: handbook routes, 검색, navigation, build 검증 완료
- 검증 명령: `cd frontend && npm run build`
- 통과 조건: 0 error + 주요 route 수동 확인
- 증거: -
- 참조: `docs/08_Handbook.md` H1-QA-01
- 의존성: H1-FE-01~05

---

## 다음 초안 태스크 (Handbook H2 Draft)

### 1. 피드백 집계 어드민 뷰 `[H2-FBK-01]`
- 상태: draft
- 목적: `term_feedback`의 `helpful / confusing` 비율과 최근 반응을 admin에서 확인한다.
- 산출물: `/admin/handbook` 집계 카드, 용어별 반응 컬럼

### 2. 헷갈림 상위 용어 큐레이션 `[H2-FBK-02]`
- 상태: draft
- 목적: `confusing` 비율이 높은 용어를 우선 보완 대상으로 정렬한다.
- 산출물: handbook admin 우측 rail 또는 별도 필터

### 3. Advanced 본문 AI 보강 `[H2-AI-01]`
- 상태: draft
- 목적: `body_advanced_*`를 AI 초안/보강 파이프라인과 연결한다.
- 산출물: handbook advanced draft 생성/검수 흐름

### 4. 관련 용어 추천 고도화 `[H2-REC-01]`
- 상태: draft
- 목적: categories + source + feedback 신호를 기반으로 related term 품질을 높인다.
- 산출물: handbook 상세 related terms 개선

## Related Plans

- [[plans/2026-03-14-handbook-quality-plan|핸드북 품질 계획]]
