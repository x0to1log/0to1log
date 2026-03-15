---
title: Handbook AI 시스템 품질 강화
tags:
  - plan
  - handbook
  - quality
date: 2026-03-14
---

# Handbook AI 시스템 품질 강화

> Handbook(AI 용어집) 시스템의 **AI 품질 게이트 부재**, **Admin 운영 비효율**, **콘텐츠 무결성 구멍** 3가지 핵심 문제 해결.

## 배경

News Pipeline은 `MIN_CONTENT_CHARS=5000`, 2회 재시도, Pydantic 검증 실패 시 재생성까지 갖추고 있지만, Handbook은 AI 응답 검증이 사실상 없다 (soft-fail → `success: true` 항상 반환). 테스트도 0개.

> [!important] 근본 원인
> - Handbook은 "Admin이 직접 확인하고 발행"하는 구조 → UI가 판단 정보를 안 보여줌
> - Pipeline 자동 추출 용어가 draft로 쌓이는데 1건씩만 처리 가능 → 리뷰 포기
> - body 없이 발행 가능, hard delete, related_term_slugs 미검증 등 무결성 구멍

---

## Phase 1: 품질 블로커 수정 (즉시)

### 1-1. AI 응답 품질 검증

**파일:** `backend/services/agents/advisor.py`, `backend/models/advisor.py`

- `GenerateTermResult`에 `Field(min_length=...)`: `body_basic_*` ≥ 2000, `body_advanced_*` ≥ 3000, `definition_*` ≥ 80
- 검증 실패 시 `success: false` + `validation_warnings: list[str]` 반환
- `HandbookAdviseResponse`에 `validation_warnings: list[str] = []` 필드 추가
- Frontend 토스트로 warning 표시

### 1-2. 발행 게이트 강화

**파일:** `frontend/src/pages/api/admin/handbook/status.ts`

- `body_basic_ko` 또는 `body_advanced_ko` 중 최소 1개 필수
- `categories` 빈 배열 `[]` 거부

### 1-3. Hard delete → Soft delete

**파일:** `frontend/src/pages/api/admin/handbook/delete.ts`

- `.delete()` → `.update({ status: "archived", updated_at: new Date() })`
- Admin 리스트에서 archived 기본 숨김, 필터로 볼 수 있음

### 1-4. Handbook AI 테스트

**파일:** `backend/tests/test_handbook_advisor.py` (신규)

- `test_generate_term_returns_all_fields` — happy path
- `test_generate_term_validation_warns_on_short_body` — 길이 미달 시 warning
- `test_related_terms_returns_db_existence` — DB 조회 정상
- `test_translate_detects_source_language` — 언어 자동 감지
- `test_extract_terms_returns_list` — 용어 추출 기본

---

## Phase 2: Admin 운영 효율 (Bulk Operations)

### 2-1. 리스트 페이지 체크박스 + 일괄 액션

**파일:** `frontend/src/pages/admin/handbook/index.astro`

- 각 row 체크박스 (전체 선택 포함)
- 일괄 액션 바: **일괄 발행** · **일괄 삭제(archive)** · **일괄 번역**
- 토스트로 결과 표시

### 2-2. 일괄 액션 API

**파일:** `frontend/src/pages/api/admin/handbook/bulk-action.ts` (신규)

```
POST /api/admin/handbook/bulk-action
{ action: "publish" | "archive" | "translate", ids: string[] }
```

### 2-3. 콘텐츠 완성도 표시

- KO Basic / KO Advanced / EN Basic / EN Advanced 4칸 미니 도트
- 채워진 필드: 초록 도트, 비어있는 필드: 회색 도트

---

## Phase 3: 콘텐츠 품질 (중기)

### 3-1. 비용 효율화

| Action | 현재 | 변경 |
|---|---|---|
| related_terms | gpt-4o | **gpt-4o-mini** |
| translate | gpt-4o | **gpt-4o-mini** |
| generate max_tokens | 16,000 | **8,192** |

### 3-2. 용어 중복 체크

`extract_terms_from_content()` 반환 전 DB 조회로 `exists_in_db` 플래그 추가

### 3-3. Slug 유일성 사전 검증

새 용어 생성 시 slug 존재 여부 체크 → 409 Conflict

### 3-4. SEO 구조화 데이터

- `DefinedTerm` + `BreadcrumbList` JSON-LD 추가

---

## 실행 순서

```
Phase 1 ─ 품질 블로커
  ├── 1-1. AI 응답 검증
  ├── 1-2. 발행 게이트 강화
  ├── 1-3. Soft delete
  └── 1-4. 테스트

Phase 2 ─ 운영 효율
  ├── 2-1. 체크박스 + 일괄 액션 바
  ├── 2-2. Bulk action API
  └── 2-3. 완성도 표시

Phase 3 ─ 콘텐츠 품질
  ├── 3-1. 모델 변경 + 비용 추적
  ├── 3-2. 용어 중복 체크
  ├── 3-3. Slug 유일성 검증
  └── 3-4. SEO 구조화 데이터
```

## Related Plans

- [[plans/ACTIVE_SPRINT_HANDBOOK|핸드북 스프린트]]
