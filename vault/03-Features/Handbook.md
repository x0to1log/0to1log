---
title: Handbook (AI Glossary)
tags:
  - features
  - tier-1
  - handbook
  - glossary
source: docs/08_Handbook.md
---

# Handbook (AI Glossary)

AI/CS/Infra 용어집 기능. 단순 정의 사전이 아니라, AI News와 Blog를 읽는 중 막히는 개념을 바로 이해하고 다시 돌아갈 수 있게 만드는 ==참조 레이어==.

## 핵심 역할

- AI/CS/Infra 용어를 EN/KO로 제공
- 공개 상세 페이지에서 빠른 이해용 `definition` + 레벨별 본문
- 뉴스/블로그 본문에서 handbook 팝업과 링크 연결
- 로그인 사용자의 저장/읽기 흐름 연결
- admin에서 용어 작성, 발행, 보완 요청 처리

## Naming Boundary

| Context | Term |
|---|---|
| **Public product** | AI News, ==AI Glossary==, My Library |
| **Internal/admin** | Posts, ==Handbook== |
| **Route** | `/{locale}/handbook/` |

## Data Model

### handbook_terms

| Field | Type | Purpose |
|---|---|---|
| `id` | `uuid` PK | — |
| `term` | `text` NOT NULL | 용어명 (EN) |
| `slug` | `text` UNIQUE | URL slug |
| `korean_name` | `text` | 한국어 용어명 |
| `categories` | `text[]` | 카테고리 배열 |
| `related_term_slugs` | `text[]` | 관련 용어 slug 목록 |
| `is_favourite` | `boolean` | 즐겨찾기 |
| `definition_ko/en` | `text` | 간단 정의 (KO/EN) |
| `body_basic_ko/en` | `text` | 기초 본문 (KO/EN) |
| `body_advanced_ko/en` | `text` | 심화 본문 (KO/EN) |
| `status` | `text` | `draft` / `published` / `archived` |
| `published_at` | `timestamptz` | 발행 시각 |

> [!note] Legacy Migration
> `00015_handbook_difficulty_levels.sql`에서 `difficulty`, `plain_explanation_*`, `technical_description_*`, `example_analogy_*`, `body_markdown_*` → 현재 `body_basic_*` / `body_advanced_*` 구조로 마이그레이션 완료. `00017`에서 legacy columns drop 완료.

### profiles.handbook_level

- `profiles` 테이블에 `handbook_level` (`basic` / `advanced`, default `basic`) 추가
- 상세 페이지에서 로그인 사용자의 기본 레벨로 사용
- 비로그인 시 레벨 스위처로 전환

### term_feedback

| Field | Type | Purpose |
|---|---|---|
| `user_id` | `uuid` FK | 사용자 |
| `term_id` | `uuid` FK | 용어 |
| `locale` | `text` | `en` / `ko` |
| `reaction` | `text` | `helpful` / `confusing` |

- UNIQUE constraint: `(user_id, term_id, locale)`
- Authenticated user만 자기 row 읽기/쓰기

## Public Pages

### List Page (`/{locale}/handbook/`)

- 검색창 + category filter
- 정렬: `term ASC`
- 카드: term, korean_name, localized definition excerpt, category pills, bookmark state
- 우측 컬럼: glossary 소개, popular terms, category browse

### Detail Page (`/{locale}/handbook/[slug]/`)

- `definition` 먼저 노출
- `basic / advanced` 2레벨 본문 스위처
- `body_basic` / `body_advanced`를 markdown → HTML 렌더링
- Related terms + same category terms + related articles
- Handbook feedback block

> [!note] Locale Fallback
> EN 값이 비어 있으면 KO fallback 허용. 이 경우 "translation pending" 안내 표시.

### Handbook Popup

- 뉴스/블로그 본문에서 `definition` 중심 툴팁
- 장문 본문 미포함 — 빠른 정의 확인 후 상세로 이동시키는 구조

## Admin Operations

### Routes

- `/admin` — 대시보드
- `/admin/handbook` — 용어 목록
- `/admin/handbook/edit/[slug]` — 용어 편집
- Cross-reference: 상세 Admin UI → [[Admin]]

### Handbook List (Admin)

- Posts admin과 동일 문법: search, status filter, category filter
- Actions: publish / preview / edit
- ==일괄 액션==: 체크박스로 다중 선택 → 일괄 발행 / 일괄 아카이브 (`/api/admin/handbook/bulk-action`)
- ==완성도 도트==: KO Basic · KO Adv · EN Basic · EN Adv (4도트, 초록=채움 / 회색=빈칸)
- 3줄 메타 레이아웃: 배지+도트+소스 | 카테고리 태그 | 업데이트 날짜

### Editor Fields

| Group | Fields |
|---|---|
| **Meta** | `term`, `slug`, `korean_name`, `categories`, `related_term_slugs`, `is_favourite` |
| **Content** | `definition_ko/en`, `body_basic_ko/en`, `body_advanced_ko/en` |

- Language tabs: KO / EN
- Level tabs: Basic / Advanced
- Single scroll form + sticky save action

### Feedback Admin Use

- `term_feedback`의 목적: admin 보완 우선순위 수집
- `confusing` 비율 높은 용어를 우선 보완
- 추후 admin dashboard에서 aggregated feedback 노출 가능

## Verification Checklist

- [ ] handbook list render 정상
- [ ] category filter 정상
- [ ] search 정상
- [ ] detail page: `definition`, `body_basic`, `body_advanced` 정상 렌더링
- [ ] profile `handbook_level` 반영
- [ ] handbook popup이 definition-only로 정상 동작
- [ ] feedback 버튼 반응 저장 정상
- [ ] admin handbook save/publish 흐름 정상

## 품질 게이트

### 발행 게이트 (Publish Gate)

`status.ts` / `bulk-action.ts`에서 publish 전 검증:
- `term`, `slug`, `definition_ko` 필수
- `categories` 빈 배열 거부
- `body_basic_ko` 또는 `body_advanced_ko` 최소 1개 필수

### Soft Delete

삭제 시 `status='archived'`로 변경 (hard delete 아님).

## Future Work

- Admin에서 feedback 집계 보기
- AI pipeline이 handbook advanced body를 직접 보완하도록 연결 검토

> [!note] Canonical Source
> Schema: `00015`, `00016`, `00017` migrations / Public: `frontend/src/pages/*/handbook/*` / Admin: `frontend/src/pages/admin/handbook/*`

## Related

- [[Admin]] — Handbook admin 에디터가 포함된 관리자 시스템
- [[Handbook-Content-Rules]] — Handbook 콘텐츠 작성 규칙 (레벨 체계, 이중 언어)
- [[Database-Schema-Overview]] — 전체 DB 스키마
- [[Persona-System]] — 뉴스 3페르소나 vs 핸드북 2레벨 비교
- [[Daily-Dual-News]] — 핸드북 팝업이 연결되는 뉴스
