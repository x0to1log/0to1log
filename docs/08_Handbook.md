# 08_Handbook

> 문서 버전: v1.1
> 최종 수정: 2026-03-11
> 작성자: Amy (Solo)
> 상태: Active Spec
> 연관 문서: `01_Project_Overview.md`, `IMPLEMENTATION_PLAN.md`, `docs/plans/2026-03-07-handbook-h1-plan.md`

---

## 1. 개요

`AI Glossary`는 0to1log의 용어집 표면이다. 목적은 단순 정의 사전이 아니라, AI News와 Blog를 읽는 중 막히는 개념을 바로 이해하고 다시 돌아갈 수 있게 만드는 참조 레이어를 제공하는 것이다.

핵심 역할:
- AI/CS/Infra 용어를 EN/KO로 제공
- 공개 상세 페이지에서 빠른 이해용 `definition`과 읽기 레벨별 본문 제공
- 뉴스/블로그 본문에서 handbook 팝업과 링크로 연결
- 로그인 사용자의 저장/읽기 흐름과 연결
- admin에서 용어 작성, 발행, 보완 요청 처리

Naming boundary:
- Public product language: `AI News`, `AI Glossary`, `My Library`
- Internal/admin language: `Posts`, `Handbook`
- Route compatibility: public glossary route는 계속 `/{locale}/handbook/`

---

## 2. 현재 데이터 모델

### 2.1 canonical handbook_terms schema

현재 런타임 기준 handbook 주요 필드는 아래와 같다.

```sql
CREATE TABLE handbook_terms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  term TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  korean_name TEXT,
  categories TEXT[],
  related_term_slugs TEXT[],
  is_favourite BOOLEAN DEFAULT FALSE,

  definition_ko TEXT,
  definition_en TEXT,
  body_basic_ko TEXT,
  body_basic_en TEXT,
  body_advanced_ko TEXT,
  body_advanced_en TEXT,

  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
  notion_page_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  published_at TIMESTAMPTZ
);
```

### 2.2 legacy compatibility

과거 handbook 초안에는 아래 필드가 사용됐다.
- `difficulty`
- `plain_explanation_*`
- `technical_description_*`
- `example_analogy_*`
- `body_markdown_*`

`00015_handbook_difficulty_levels.sql`에서 현재 구조로 마이그레이션하면서:
- `body_basic_*`는 기존 `body_markdown + plain_explanation + example_analogy`를 합친 본문으로 seed
- `body_advanced_*`는 기존 `technical_description_*`를 seed
- `profiles.handbook_level` 추가

중요:
- `00017_drop_handbook_legacy_columns.sql`에서 legacy old column drop이 완료됐다.
- 현재 canonical handbook schema에는 `plain_explanation_*`, `technical_description_*`, `example_analogy_*`, `body_markdown_*`, `difficulty`가 더 이상 포함되지 않는다.

### 2.3 profiles.handbook_level

```sql
ALTER TABLE profiles
ADD COLUMN handbook_level TEXT DEFAULT 'basic'
CHECK (handbook_level IN ('basic', 'advanced'));
```

의미:
- handbook 상세는 로그인 사용자 profile의 `handbook_level`을 우선 사용
- 기본값은 `basic`
- 공개 페이지는 레벨 스위처로 `basic / advanced`를 전환 가능

### 2.4 term_feedback

```sql
CREATE TABLE term_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  term_id UUID NOT NULL REFERENCES handbook_terms(id) ON DELETE CASCADE,
  locale TEXT NOT NULL CHECK (locale IN ('en', 'ko')),
  reaction TEXT NOT NULL CHECK (reaction IN ('helpful', 'confusing')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (user_id, term_id, locale)
);
```

의미:
- handbook 상세 하단의 `도움 됨 / 헷갈림` 반응 저장
- 댓글이 아니라 lightweight feedback 수집용
- authenticated user만 자기 row를 읽고 쓸 수 있음

---

## 3. 공개 페이지 구조

### 3.1 목록 페이지

경로:
- `/en/handbook/`
- `/ko/handbook/`

현재 목록 페이지 계약:
- 검색창 1개
- category filter만 제공
- public list에는 difficulty filter를 두지 않음
- 정렬은 `term ASC`
- 카드에는 아래 정보가 표시됨
  - term
  - korean_name
  - localized definition excerpt
  - category pills
  - bookmark state

목록 우측 컬럼:
- glossary 소개
- popular terms
- category browse

### 3.2 상세 페이지

경로:
- `/en/handbook/[slug]/`
- `/ko/handbook/[slug]/`

현재 상세 페이지 계약:
- `definition`을 먼저 노출
- `basic / advanced` 2레벨 본문 스위처 제공
- `body_basic` / `body_advanced`를 markdown -> HTML로 렌더링
- related terms
- same category terms
- related articles
- handbook feedback block

필드 선택 규칙:

```ts
const definition = localField(term, 'definition', locale);
const bodyBasic = localField(term, 'body_basic', locale);
const bodyAdvanced = localField(term, 'body_advanced', locale);
```

fallback 규칙:
- EN 값이 비어 있으면 KO fallback 허용
- 이 경우 translation pending 안내를 보여줄 수 있음

### 3.3 handbook popup

뉴스/블로그 본문에서 handbook popup은 현재 `definition` 중심으로 단순화되어 있다.

의도:
- 툴팁 안에 장문 본문을 넣지 않음
- 빠른 정의 확인 후 handbook 상세로 이동시키는 구조 유지

---

## 4. Admin 운영 구조

### 4.1 admin routes

- `/admin`
- `/admin/handbook`
- `/admin/handbook/edit/[slug]`
- `/admin/content`
- `/admin/settings`

### 4.2 handbook list in admin

admin handbook list는 posts admin과 최대한 같은 문법을 따른다.
- search
- status filter
- category filter
- publish / preview / edit action

### 4.3 handbook edit current fields

현재 editor는 아래 필드를 직접 다룬다.
- `term`
- `slug`
- `korean_name`
- `categories`
- `related_term_slugs`
- `is_favourite`
- `definition_ko`, `definition_en`
- `body_basic_ko`, `body_basic_en`
- `body_advanced_ko`, `body_advanced_en`

편집 구조:
- language tabs: KO / EN
- level tabs: Basic / Advanced
- single scroll form + sticky save action

현재 editor에서 더 이상 핵심 입력 필드가 아닌 것:
- `plain_explanation_*`
- `technical_description_*`
- `example_analogy_*`
- `body_markdown_*`
- `difficulty`

### 4.4 handbook feedback and admin use

`term_feedback`의 목적은 public discussion이 아니라 admin 보완 우선순위 수집이다.

활용 방향:
- `confusing` 비율이 높은 용어를 우선 보완
- glossary copy 개선 근거로 사용
- 추후 admin dashboard에서 aggregated feedback 노출 가능

---

## 5. UX 원칙

### 5.1 glossary는 댓글 페이지가 아니다

뉴스 상세는 해석과 의견 교환이 목적이므로 댓글이 자연스럽다.
Handbook는 참조형 페이지이므로 일반 댓글보다 lightweight feedback이 더 적합하다.

현재 handbook interaction 원칙:
- `도움 됨 / 헷갈림`만 제공
- 빠른 이해가 핵심
- 토론보다 설명 개선 신호 수집에 집중

### 5.2 레벨 전환 원칙

- `basic`: 빠른 이해, 쉬운 설명, 읽는 중 바로 참고
- `advanced`: 더 기술적인 설명, 실무/구조 관점

이 구조는 기존 뉴스 persona 시스템과 유사하지만, handbook는 `basic / advanced` 2단계만 사용한다.

---

## 6. 검증 기준

핸드북 변경 시 최소 검증:
- handbook list render 정상
- category filter 정상
- search 정상
- detail page에서 `definition`, `body_basic`, `body_advanced` 정상 렌더링
- profile `handbook_level` 반영
- handbook popup이 definition-only로 정상 동작
- feedback 버튼 반응 저장 정상
- admin handbook save/publish 흐름 정상

SQL/데이터 검증 예시:

```sql
SELECT slug, definition_ko, body_basic_ko, body_advanced_ko, status
FROM handbook_terms
LIMIT 5;
```

적어도 아래는 확인해야 한다.
- `body_basic_*` 값 존재
- `body_advanced_*` 값 존재
- `categories`가 배열 형태로 저장됨
- `term_feedback` insert/upsert 가능

---

## 7. 남은 후속 작업

아직 남은 작업:
- handbook docs/plan의 remaining legacy snippets 추가 정리
- admin에서 feedback 집계 보기
- AI pipeline이 handbook advanced body를 직접 보완하도록 연결 검토

현재 기준 canonical runtime source of truth:
- schema: `00015_handbook_difficulty_levels.sql`, `00016_term_feedback.sql`, `00017_drop_handbook_legacy_columns.sql`
- public pages: `frontend/src/pages/*/handbook/*`
- admin pages: `frontend/src/pages/admin/handbook/*`
