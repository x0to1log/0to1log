# 08 — AI Glossary Spec

> **문서 버전:** v1.0
> **최종 수정:** 2026-03-08
> **작성자:** Amy (Solo)
> **상태:** Planning
> **상위 문서:** `01_Project_Overview.md`
> **구현 계획:** `docs/plans/2026-03-07-handbook-h1-plan.md`

---

## 1. 개요

### Naming Boundary

- Public product language uses `AI News`, `Handbook`, and `Library`.
- Internal/admin language uses `Posts` and `Handbook`.
- Route compatibility remains unchanged: AI News articles continue to live under `/{locale}/log/`.
- Any legacy `Log` wording in older implementation notes should be read as the public AI News surface unless the context is explicitly internal/admin.

**AI Glossary**은 Notion에서 관리해온 CS/AI/Infra 용어 사전을 웹사이트에 `/handbook/` 경로로 공개하는 기능이다.

**목표:**
- Notion 데이터(KO)를 Supabase에 마이그레이션하고 EN 콘텐츠를 추가하는 이중 언어 사전 구축
- 어드민에서 검수 후 퍼블리시하는 워크플로우 제공
- 향후 AI 자동 수집 파이프라인을 붙일 수 있는 확장 가능한 구조

**Tech Stack:** Astro v5 (SSR), Supabase (PostgreSQL + RLS), Tailwind CSS v4, unified/remark (Markdown 렌더링)

---

## 2. 비즈니스 포지셔닝

### 핵심 가치: Log의 배경지식 레이어

단순한 용어 정의 사전은 Wikipedia, 나무위키와 경쟁할 수 없다.
**핸드북의 가치는 독립된 사전이 아니라 "Log의 배경지식 레이어"에 있다.**

### Jobs to Be Done

| Job | 기존 대안 | Handbook 차별점 |
|-----|-----------|-----------------|
| "이 용어가 뭔지 빨리 알고 싶어" | Google → Wikipedia | 쉬운 설명 + 실무 예시 + 난이도별 설명 |
| "면접/발표 준비 중 개념 정리" | 흩어진 블로그 글 | 체계적 카테고리 인덱스 + 커뮤니케이션 표현 |
| "기사 읽다가 모르는 단어" | 탭 열어서 검색 | 기사 내 용어 링크 → 같은 사이트에서 해결 |

### Inversion: 확실히 실패하는 조건

- 용어 정의만 있고 추가 가치 없음 → Wikipedia 열화 복사
- Log 기사와 연결 안 됨 → 고립된 페이지, 재방문 이유 없음
- SEO 최적화 안 됨 → 유입 경로 없음
- 10개 용어로 멈춤 → 검색 가치 없는 빈 페이지

### 콘텐츠 플라이휠

```
Log 기사 → 모르는 용어 → 핸드북 클릭 → 이해 → 다른 기사 읽음
     ↑                                            ↓
핸드북 SEO 유입 ←── Google 검색 ("RAG란?")
```

- 각 용어 페이지 = Long-tail SEO 진입점 ("RAG란 무엇인가", "LLM 쉬운 설명")
- Log 기사 안에서 용어 링크 = 사이트 체류 시간 증가 (Zeigarnik Effect)
- 용어 페이지에 "이 용어가 등장한 기사" 섹션 = 재방문 이유 + 내부 링크

### 실행 전략

| 전략 | 적용 모델 | 구현 시점 |
|------|-----------|-----------|
| Log 기사 본문에서 핸드북 용어 자동 링크 | Zeigarnik Effect | H1.5 |
| 각 용어 상세에 "관련 기사" 섹션 | Reciprocity | H1 |
| 용어 페이지 SEO 최적화 (한/영) | Long-tail SEO | H1 |
| 난이도별 설명 | 차별화 | H1 |
| AI 파이프라인으로 용어 자동 확장 | Flywheel | H2 |

---

## 3. Phase 구분

### Phase H1 — 이중 언어 사전 + 검수 워크플로우

Notion 데이터(KO) → Supabase 마이그레이션. EN 콘텐츠 작성. 어드민에서 검수 후 퍼블리시.

| Task ID | 내용 | 의존성 |
|---------|------|--------|
| H1-DB-01 | Supabase 테이블 생성 (이중 언어 스키마) | 없음 |
| H1-DB-02 | Notion → Supabase 마이그레이션 스크립트 | H1-DB-01 |
| H1-FE-01 | i18n 문자열 추가 | 없음 |
| H1-FE-02 | Handbook 목록 페이지 (`/en/handbook/`, `/ko/handbook/`) | H1-DB-01, H1-FE-01 |
| H1-FE-03 | Handbook 상세 페이지 (`/en/handbook/[slug]/`) | H1-DB-01, H1-FE-01 |
| H1-FE-04 | Navigation에 Handbook 링크 추가 | H1-FE-02 |
| H1-FE-05 | Handbook 검색 기능 (영/한 키워드 매칭) | H1-FE-02 |
| H1-ADMIN-01 | Admin Handbook 편집/검수 페이지 | H1-DB-01 |
| H1-ADMIN-02 | Draft → Published 워크플로우 | H1-ADMIN-01 |
| H1-QA-01 | 반응형/접근성/빌드 검증 | 전체 |

### Phase H1.5 — Log↔Handbook 인라인 연동

| Task ID | 내용 | 의존성 |
|---------|------|--------|
| H1.5-FE-01 | 기사 본문 내 용어 자동 감지 + 인라인 팝업 | H1 완료 |
| H1.5-FE-02 | 페르소나별 팝업 콘텐츠 적응 | H1.5-FE-01 |

### Phase H2 — AI 수집 파이프라인 (백엔드, 미래)

| Task ID | 내용 | 의존성 |
|---------|------|--------|
| H2-API-01 | 용어 수집 엔드포인트 (Tavily semantic search + OpenAI) | Phase 2B 완료 |
| H2-API-02 | 용어 생성 AI 파이프라인 — KO/EN 동시 생성 | H2-API-01 |
| H2-FE-01 | Admin AI 생성 리뷰 UI | H2-API-02 |

### Phase H3 — 사이트 전체 검색 (Log + Handbook 통합)

H1에서는 Handbook 내부 검색만. 추후 Log 기사 + Handbook 용어 통합 검색 구현.

---

## 4. 데이터 모델

### Notion Words DB 현황

- **용어 수:** 10개 이상 (LLM, RAG, SQL, CV, EDA, OAuth, Z-Score, CMMI, SI, SM 등)
- **카테고리:** 10개

### Notion 용어 페이지 구조

각 용어 페이지는 **속성(Properties)** + **본문(Body Content)**으로 구성:

**속성 (DB 컬럼으로 매핑):**

| Notion 속성 | 용도 |
|---|---|
| Term | 영어 용어명 (타이틀) |
| Korean (한글명) | 한국어 명칭 + 발음 |
| Definition (정의) | 1~2문장 정의 |
| Plain Explanation (쉬운 설명) | 비유 중심 쉬운 풀이 |
| Technical Description (기술적 설명) | 기술적 상세 설명 |
| Example/Analogy (예시/비유) | 실생활 비유 + 실제 예시 |
| Difficulty | Beginner / Intermediate / Advanced |
| Category | 카테고리 (relation) |
| Related Terms (관련 개념) | 다른 용어와의 관계 (self-relation) |
| Favourite | 즐겨찾기 여부 |

**본문 구조 (Markdown):**

```
## Understanding of Concept (개념 이해를 위한 정보)
  ├── Technical Description (기술적 설명)
  ├── Plain Explanation (쉬운 설명)
  └── Example/Analogy (예시·비유)

## Practical Use (실무 활용)
  ├── Practical Example (실무 사용 예시)
  ├── Why is it important? (왜 중요한가)
  └── Precautions (주의사항/함정)

## Learning Materials (학습 자료)
  └── Reference Link (참조 링크)

## Communication (커뮤니케이션)
  └── Frequently Used Expressions (자주 같이 쓰는 표현)

## Related Terms (연관 개념)
```

### `handbook_terms` 테이블 스키마

**설계 원칙:**
- **이중 언어 접미사 방식:** 콘텐츠 필드에 `_en` / `_ko` 접미사 사용. 하나의 용어 = 하나의 행.
  용어(LLM)는 어느 언어에서든 같은 개념이므로 행 분리(news_posts 방식)보다 적합.
- `term` (영어 용어명) + `korean_name` (한글명)은 언어 구분 없이 공통 메타데이터
- `locale` 컬럼 불필요 — 한 행에 양 언어 포함

```sql
CREATE TABLE handbook_terms (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 공통 메타 (언어 무관)
    term                    TEXT NOT NULL,
    slug                    TEXT UNIQUE NOT NULL,
    korean_name             TEXT,
    difficulty              TEXT CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
    categories              TEXT[],
    related_term_slugs      TEXT[],
    is_favourite            BOOLEAN DEFAULT FALSE,

    -- 한국어 콘텐츠
    definition_ko              TEXT,
    plain_explanation_ko       TEXT,
    technical_description_ko   TEXT,
    example_analogy_ko         TEXT,
    body_markdown_ko           TEXT,

    -- 영어 콘텐츠
    definition_en              TEXT,
    plain_explanation_en       TEXT,
    technical_description_en   TEXT,
    example_analogy_en         TEXT,
    body_markdown_en           TEXT,

    -- 워크플로우
    status                  TEXT NOT NULL DEFAULT 'draft'
                            CHECK (status IN ('draft', 'published', 'archived')),

    -- Migration tracking
    notion_page_id          TEXT,

    -- Timestamps
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW(),
    published_at            TIMESTAMPTZ
);
```

**인덱스:** `slug`, `categories (GIN)`, `difficulty`, `status`

**RLS 정책:**
- Public: `status = 'published'` 읽기 허용
- Admin: `admin_users.user_id = auth.uid()` 체크 → 전체 CRUD

### 카테고리 목록

| Slug | Label |
|------|-------|
| `ai-ml` | AI/ML & Algorithm |
| `db-data` | DB / Data Infra |
| `backend` | Backend / Service Architecture |
| `frontend-ux` | Frontend & UX/UI |
| `network` | Network / Communication |
| `security` | Security / Access Control |
| `os-core` | OS / Core Principle |
| `devops` | DevOps / Operation |
| `performance` | Performance / Cost Mgt |
| `web3` | Decentralization / Web3 |

---

## 5. 이중 언어 정책

### 콘텐츠 작성 워크플로우

```
1. Notion 마이그레이션 → KO 필드 채워짐, EN 필드 비어있음, status = 'draft'
2. Amy가 /admin/handbook/ 에서 draft 목록 확인
3. 용어별로 EN 콘텐츠 작성 (직접 또는 AI 보조)
4. KO + EN 모두 확인 → "Publish" → status = 'published'
5. /en/handbook/[slug]/ → EN 콘텐츠, /ko/handbook/[slug]/ → KO 콘텐츠
```

### EN Fallback 정책 (확정)

- `/en/handbook/[slug]/` 접근 시 EN 필드가 비어있으면 → **KO 콘텐츠를 fallback으로 표시** + "(Translation in progress)" 안내 배너
- EN 목록 페이지에서도 해당 용어는 **표시** (숨기지 않음)
- 어드민 목록에서 "EN 미완성" 배지로 작업 필요 용어 식별

### Locale 필드 선택 패턴

```javascript
// locale = 'ko' | 'en'
const def     = term[`definition_${locale}`]     || term[`definition_ko`];
const plain   = term[`plain_explanation_${locale}`] || term[`plain_explanation_ko`];
const tech    = term[`technical_description_${locale}`] || term[`technical_description_ko`];
const example = term[`example_analogy_${locale}`] || term[`example_analogy_ko`];
const body    = term[`body_markdown_${locale}`]  || term[`body_markdown_ko`];
```

---

## 6. 프론트엔드 설계

### 디자인 방향: Dictionary Cards

Newsprint 디자인 시스템 위에 사전(Dictionary) 톤을 입힌 접근.
기존 Newsprint Shell을 재사용하되, 용어 목록과 상세 페이지는 레퍼런스 스타일로 구성.

### 목록 페이지 (`/en/handbook/`, `/ko/handbook/`)

- **렌더링:** SSR (`prerender = false`)
- **레이아웃:** NewsprintShell (masthead: "AI Glossary", editionLabel: "CS · AI · Infra")
- **필터:** 카테고리 + 난이도 조합 (AND 관계)
- **검색:** 클라이언트사이드 필터링 (용어 수가 적으므로). 100개 이상 시 서버사이드로 전환 검토.
- **빈 상태 / 에러:** NewsprintNotice 재사용

**카드 레이아웃:**

```
┌──────────────────────────────────────┐
│  [Beginner]  AI/ML & Algorithm       │
│  LLM (Large Language Model)          │
│  [엘엘엠] 대규모 언어 모델            │
│  대규모 텍스트 데이터로 학습된 인공... │
└──────────────────────────────────────┘
```

**검색 UX:**

```
┌─────────────────────────────────────────┐
│  Search terms... / 용어 검색...          │
└─────────────────────────────────────────┘
  [All] [Beginner] [Intermediate] [Advanced]
  [AI/ML] [DB/Data] [Backend] [Frontend] ...
```

### 상세 페이지 (`/en/handbook/[slug]/`, `/ko/handbook/[slug]/`)

- **렌더링:** SSR (`prerender = false`)
- **상단 메타:** Term, Korean name, Difficulty 배지, Category
- **속성 요약 카드 (인포박스):**
  - Definition — `definition_{locale}`
  - Plain Explanation — `plain_explanation_{locale}`
  - Example/Analogy — `example_analogy_{locale}`
- **본문:** `body_markdown_{locale}` → `renderMarkdown()` → HTML
- **하단 — Related Terms:** `related_term_slugs` → 각각 `/{locale}/handbook/[slug]/` 링크
- **하단 — 관련 기사 (플라이휠 핵심):**
  - news_posts 테이블에서 tags에 해당 용어 포함된 기사 조회 (최대 5개)
  - 매칭 기사가 없으면 섹션 숨김
- **사이드 레일:** TOC + Related Terms + 같은 카테고리 용어

### SEO

- `<title>`: KO → `{term} ({korean_name}) — AI Glossary | 0to1log`, EN → `{term} — AI Glossary | 0to1log`
- `<meta description>`: `definition_{locale}` (150자 이내, fallback: `definition_ko`)
- Open Graph: term + definition + representative categories
- Structured Data: `DefinedTerm` schema.org (선택, QA에서 검토)

### Navigation

기존 `Log | Portfolio` 사이에 `Handbook` 링크 추가 → `Log | Handbook | Portfolio`

---

## 7. 어드민 워크플로우

### 목록 (`/admin/handbook/`)

```
┌──────────────────────────────────────────────────────────┐
│  Handbook Admin                                          │
│  [Draft (5)]  [Published (3)]  [All (8)]                │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  LLM (Large Language Model)          [Draft]       │  │
│  │  KO: ✅ 완성  |  EN: ❌ 미작성                      │  │
│  │  카테고리: AI/ML  |  난이도: Beginner               │  │
│  │                             [Edit] [Publish]       │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

- status 필터 (Draft / Published / All)
- KO/EN 콘텐츠 완성도 표시 (✅/❌)
- Quick actions: Edit, Publish

### 편집 (`/admin/handbook/edit/[slug]`)

- 공통 필드: term, slug, korean_name, difficulty, categories
- **KO 탭:** definition_ko, plain_explanation_ko, technical_description_ko, example_analogy_ko, body_markdown_ko
- **EN 탭:** definition_en, plain_explanation_en, technical_description_en, example_analogy_en, body_markdown_en
- Markdown body 미리보기
- 저장 (draft 유지) / Publish (status 변경 + published_at 설정)

### 상태 전환

| 액션 | 동작 |
|------|------|
| Save Draft | `status = 'draft'`, `updated_at = NOW()` |
| Publish | 필수 필드 검증 → `status = 'published'`, `published_at = NOW()` |
| Unpublish | `status = 'draft'` |
| Archive | `status = 'archived'` |

**Publish 필수 필드:** `term`, `slug`, `definition_ko`, `categories`
(EN 없이 KO만 게시 가능 — EN은 fallback 처리됨)

---

## 8. 인라인 용어 팝업 (H1.5)

H1 완료 후 구현. 기사를 읽다가 모르는 용어를 바로 확인하는 경험이 플라이휠의 핵심.

### 동작 흐름

1. 기사 본문에서 핸드북에 등록된 용어가 **점선 밑줄**로 표시
2. 용어 클릭 → **팝업** (locale + persona에 맞는 내용)
3. "자세히 보기" → 핸드북 상세 페이지로 이동
4. 팝업 바깥 클릭 또는 ESC → 팝업 닫힘

### 페르소나별 콘텐츠 매핑

| 영역 | 비전공자 (Beginner) | 학습자 (Learner) | 현직자 (Expert) |
|------|---------------------|------------------|-----------------|
| 주요 설명 | `plain_explanation_{locale}` | `plain_explanation_{locale}` | `technical_description_{locale}` |
| 보조 설명 | `example_analogy_{locale}` | `example_analogy_{locale}` | `plain_explanation_{locale}` |
| 하단 | 난이도 · 카테고리 · 자세히 보기 | 난이도 · 카테고리 · 자세히 보기 | 카테고리 · 자세히 보기 |

**페르소나 설정:** `localStorage`에 `handbook-persona` 키 (`beginner` | `learner` | `expert`), 기본값 `learner`

### 팝업 와이어프레임

**비전공자/학습자 (KO):**
```
┌──────────────────────────────────────┐
│  엘엘엠 · 대규모 언어 모델           │
│  LLM (Large Language Model)          │
│                                      │
│  사람이 쓴 글을 엄청 많이 읽고 패턴  │
│  을 학습한 AI. 마치 수만 권의 책을   │
│  읽은 비서 같은 존재.                │
│                                      │
│  예: ChatGPT, Claude가 대표적인 LLM  │
│                                      │
│  Beginner · AI/ML    → 자세히 보기   │
└──────────────────────────────────────┘
```

**현직자 (EN):**
```
┌──────────────────────────────────────┐
│  LLM (Large Language Model)          │
│                                      │
│  Transformer-based neural network    │
│  trained on large text corpora via   │
│  self-supervised learning.           │
│                                      │
│  In simpler terms: an AI trained on  │
│  massive text to understand and      │
│  generate language.                  │
│                                      │
│  AI/ML             → Learn more      │
└──────────────────────────────────────┘
```

### 구현 방식 (권장: 빌드 타임)

| 방식 | 장점 | 단점 |
|------|------|------|
| **A. 빌드 타임 rehype 플러그인** | SSR에서 용어 감지, 깔끔 | 용어 변경 시 기사 재빌드 필요 |
| **B. 클라이언트 런타임 감지** | 용어 추가해도 재빌드 불필요 | DOM 조작, FOUC 가능성 |

권장: **방식 A** — 현재 SSR이고 용어 수가 적으므로 빌드 타임이 더 깔끔.

### 접근성

- 팝업: `role="tooltip"` 또는 `role="dialog"`
- ESC로 닫기, 포커스 트랩 (dialog)
- 스크린 리더: `aria-describedby` 연결

---

## 9. Notion 마이그레이션

### 접근 방식

1. Notion API로 Words DB 전체 조회
2. 속성 + 본문 추출 → Markdown 변환
3. Supabase `handbook_terms`에 INSERT
4. **KO 필드만 채움**, EN 필드는 NULL
5. **status = 'draft'** — Amy가 검수 후 직접 publish

### 주의사항

- Notion 본문의 테이블 → GFM 테이블 문법으로 변환
- 토글 블록 → `<details><summary>` HTML 유지
- 이미지 URL은 Notion S3 presigned URL (만료됨) → 현재 이미지 거의 없으므로 무시
- Slug: Term에서 특수문자 제거, 소문자, 공백→하이픈

### 검증 기준

- `SELECT count(*) FROM handbook_terms;` → Notion 용어 수와 일치
- 무작위 3개 용어의 `body_markdown_ko`가 Notion 본문과 일치
- `definition_en IS NULL` 확인
- 전체 `status = 'draft'` 확인

---

## 10. QA 체크리스트

- [ ] `npm run build` 0 error
- [ ] `/en/handbook/` 및 `/ko/handbook/` 목록 정상 표시
- [ ] `/en/handbook/[slug]/` 상세 페이지 정상 (EN 비어있으면 KO fallback + 배너)
- [ ] 카테고리 필터 + 난이도 필터 + 검색 조합 동작
- [ ] 검색: 영어 ("LLM") + 한국어 ("대규모 언어 모델") 매칭
- [ ] Related Terms 링크 정상 연결
- [ ] 관련 기사 섹션: 매칭 기사 있을 때 표시, 없을 때 숨김
- [ ] Navigation Handbook 링크 동작
- [ ] 다국어 스위처 (`/en/handbook/` ↔ `/ko/handbook/`) 동작
- [ ] 반응형: mobile / tablet / desktop
- [ ] 접근성: 키보드 네비게이션, 대비
- [ ] SEO: title, meta description, OG 태그
- [ ] 어드민: draft/published 필터, KO/EN 완성도 배지
- [ ] 어드민: 편집 페이지 KO/EN 탭 + 저장
- [ ] 어드민: Publish 시 필수 필드 검증
- [ ] 어드민: Draft → Published → Archive 상태 전환

---

## 11. 기존 코드 영향 범위

| 파일 | 변경 유형 | 영향 |
|------|-----------|------|
| `supabase/migrations/00003_handbook_terms.sql` | 통합 파일 | 없음 (handbook 전용) |
| `scripts/migrate-handbook-*.ts` | 새 파일 | 없음 (1회성) |
| `frontend/src/i18n/index.ts` | 수정 | handbook 키 추가만 |
| `frontend/src/lib/handbook*.ts` | 새 파일 | 없음 |
| `frontend/src/pages/*/handbook/` | 새 파일 | 없음 (새 라우트) |
| `frontend/src/pages/admin/handbook/` | 새 파일 | 없음 |
| `frontend/src/components/Navigation.astro` | 수정 | 링크 1개 추가 |

**기존 기능에 대한 영향: 없음.** 전부 새 파일이거나 기존 파일에 추가만 하는 변경.

---

## 12. 병렬 작업 안전성

Handbook 작업은 메인 Phase 작업과 **완전히 독립적:**

- **데이터:** 별도 테이블 (`handbook_terms` vs `news_posts`)
- **페이지:** 별도 라우트 (`/handbook/` vs `/news/`)
- **컴포넌트:** 기존 컴포넌트 재사용하되 수정하지 않음
- **공유 파일:** `Navigation.astro` (1줄), `i18n/index.ts` (키 추가)

### Parallel Sprint 운영

- `/log` AI News + `/handbook`이 메인 앱 surface. `/portfolio`는 secondary.
- Handbook 스프린트 문서: `docs/plans/ACTIVE_SPRINT_HANDBOOK.md` (별도 관리)
- 공유 파일 변경은 별도 커밋 후 rebase
- H1은 병렬 진행 가능. H2는 메인 Phase 2B-2D 안정화 후 시작.
