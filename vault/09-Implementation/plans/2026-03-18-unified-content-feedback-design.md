# 통합 콘텐츠 피드백 시스템 설계

> **작성일:** 2026-03-18
> **목적:** 모든 콘텐츠 타입에 대한 사용자 피드백 수집 + 어드민 관리 대시보드
> **대상:** 뉴스, 핸드북, 블로그, 제품
> **이전 시스템:** `term_feedback` (핸드북 전용) → `content_feedback` (통합)으로 전환

---

## 1. 설계 결정 요약

| 항목 | 결정 |
|------|------|
| 목적 | 콘텐츠 품질 개선 시그널 + UX 피드백 (콘텐츠 내) |
| 수집 범위 | 뉴스, 핸드북, 블로그, 제품 (사이트 전반 UX는 제외 — 추후 확장) |
| 리액션 타입 | 👍/👎 (positive/negative) 통일 |
| 부정 피드백 상세화 | 👎 클릭 시 Bottom Sheet → 콘텐츠별 맞춤 reason 선택지 + 자유 메시지 |
| UI 위치 | 본문 하단 섹션 (사이드 레일 아님 — 버튼 과밀 방지) |
| DB 구조 | 범용 `content_feedback` 테이블 1개 (기존 `term_feedback` 이관 후 제거) |

---

## 2. DB 스키마

### 2.1 `content_feedback` 테이블

```sql
CREATE TABLE content_feedback (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL CHECK (source_type IN ('news','handbook','blog','product')),
  source_id   UUID NOT NULL,
  locale      TEXT NOT NULL CHECK (locale IN ('ko','en')),
  reaction    TEXT NOT NULL CHECK (reaction IN ('positive','negative')),
  reason      TEXT,
  message     TEXT,
  archived    BOOLEAN NOT NULL DEFAULT FALSE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, source_type, source_id, locale)
);

ALTER TABLE content_feedback ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_content_feedback_source ON content_feedback(source_type, source_id, locale);
CREATE INDEX idx_content_feedback_user ON content_feedback(user_id);
CREATE INDEX idx_content_feedback_archived ON content_feedback(archived);
```

**`source_id` FK 참고:** 다형성(polymorphic) 테이블이므로 `source_id`에 FK constraint를 걸 수 없음. 콘텐츠가 삭제되면 고아 피드백이 남을 수 있으므로, 어드민 대시보드에서 `content_title IS NULL`인 피드백을 "삭제된 콘텐츠" 로 표시하고 일괄 정리 기능을 제공한다.

**`updated_at` 관리:** 애플리케이션 레벨에서 UPSERT 시 `updated_at: new Date().toISOString()` 설정 (기존 패턴 동일). DB 트리거 없음.

### 2.2 부정 피드백 reason 선택지

| source_type | reason 값 | 한국어 레이블 | 영어 레이블 |
|---|---|---|---|
| news | `inaccurate` | 부정확함 | Inaccurate |
| news | `hard_to_understand` | 이해하기 어려움 | Hard to understand |
| news | `too_shallow` | 깊이가 부족함 | Too shallow |
| handbook | `confusing` | 설명이 혼란스러움 | Confusing explanation |
| handbook | `lacks_examples` | 예시가 부족함 | Lacks examples |
| handbook | `outdated` | 정보가 오래됨 | Outdated information |
| blog | `not_helpful` | 도움 안 됨 | Not helpful |
| blog | `lacks_depth` | 내용이 부족함 | Lacks depth |
| product | `inaccurate_info` | 정보가 부정확함 | Inaccurate info |
| product | `not_useful` | 유용하지 않음 | Not useful |

각 source_type에 공통으로 `other` reason도 허용 (선택지에 없는 이유를 message로 보완).

| 공통 | `other` | 기타 | Other |

- reason은 DB CHECK constraint 없이 애플리케이션 레벨에서 검증 (콘텐츠별 선택지가 다르므로)
- reason 검증 규칙:
  - `reaction === 'positive'` → `reason`은 반드시 null
  - `reaction === 'negative'` → `reason`은 해당 `source_type`의 허용 값 중 하나 (필수)
- 긍정 시 reason null, 부정 시 reason 필수.

### 2.3 RLS 정책

```sql
-- 인증 사용자: 본인 피드백 CRUD
CREATE POLICY "select_own" ON content_feedback FOR SELECT TO authenticated
  USING (auth.uid() = user_id);
CREATE POLICY "insert_own" ON content_feedback FOR INSERT TO authenticated
  WITH CHECK (auth.uid() = user_id);
CREATE POLICY "update_own" ON content_feedback FOR UPDATE TO authenticated
  USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "delete_own" ON content_feedback FOR DELETE TO authenticated
  USING (auth.uid() = user_id);

-- 어드민: 전체 읽기 + 업데이트 (아카이브용)
CREATE POLICY "admin_read_all" ON content_feedback FOR SELECT
  USING (EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid()));
CREATE POLICY "admin_update_all" ON content_feedback FOR UPDATE
  USING (EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid()));
```

---

## 3. API 엔드포인트

기존 `/api/user/term-feedback.ts` → `/api/user/content-feedback.ts`로 교체.

### 3.1 GET `/api/user/content-feedback`

**Query params:** `source_type`, `source_id`, `locale`

**Response:** `{ reaction, reason, message }` 또는 `null` (피드백 없을 때)

### 3.2 POST `/api/user/content-feedback`

**Body:**
```json
{
  "source_type": "news",
  "source_id": "uuid",
  "locale": "ko",
  "reaction": "negative",
  "reason": "inaccurate",
  "message": "날짜가 틀렸어요"
}
```

**동작:** UPSERT on conflict `(user_id, source_type, source_id, locale)`

**Response:** `{ reaction, reason, message }`

**검증:**
- `source_type` ∈ `['news','handbook','blog','product']`
- `locale` ∈ `['ko','en']`
- `reaction` ∈ `['positive','negative']`
- `reaction === 'positive'` → `reason` must be null
- `reaction === 'negative'` → `reason` must be valid for the given `source_type` (§2.2)
- `message` max 500자
- 인증 필수

### 3.3 DELETE `/api/user/content-feedback`

**Query params:** `source_type`, `source_id`, `locale`

**동작:** 해당 사용자의 피드백 삭제 (피드백 철회)

**Response:** `{ success: true }` 또는 404

---

## 4. 프론트엔드 UI

### 4.1 컴포넌트 구조

**기존 파일 → 범용화:**
- `HandbookFeedback.astro` → `ContentFeedback.astro`
- `handbookFeedback.ts` → `contentFeedback.ts`
- Bottom Sheet CSS는 기존 `global.css` 것 재활용

**`ContentFeedback.astro` Props:**
```ts
interface Props {
  sourceType: 'news' | 'handbook' | 'blog' | 'product';
  sourceId: string;
  locale: 'ko' | 'en';
  isAuthenticated: boolean;
  loginUrl: string;
  previewMode?: boolean;
}
```

### 4.2 UI 동작

**본문 하단 섹션 (모든 콘텐츠 공통):**

```
┌─────────────────────────────────────────┐
│  이 콘텐츠가 도움이 되었나요?              │
│  피드백은 콘텐츠 개선에 활용됩니다.         │
│                                         │
│  [ 👍 도움이 됐어요 ]  [ 👎 별로에요 ]     │
└─────────────────────────────────────────┘
```

**👍 클릭:** 즉시 API POST → 버튼 하이라이트 + "감사합니다!" 메시지.

**👎 클릭:** Bottom Sheet 열림:

```
┌─────────────────────────────────────────┐
│  어떤 점이 아쉬웠나요?                     │
│                                         │
│  ○ {reason 1}                           │
│  ○ {reason 2}                           │
│  ○ {reason 3}                           │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ 추가 의견이 있다면... (선택사항)   │    │
│  └─────────────────────────────────┘    │
│                                         │
│  [ 제출하기 ]                            │
└─────────────────────────────────────────┘
```

- reason 선택지는 `sourceType`에 따라 동적 (§2.2 참조)
- reason 선택 필수, 메시지는 선택
- 제출 후 "감사합니다!" + Bottom Sheet 닫힘

**비로그인 사용자:** 버튼 클릭 시 로그인 프롬프트 표시 (기존 핸드북 패턴).

### 4.3 마운트 위치

| 페이지 | 파일 | 위치 |
|--------|------|------|
| 뉴스 상세 | `/ko/news/[slug].astro`, `/en/news/[slug].astro` | 본문 끝, 소스 카드 아래 |
| 핸드북 상세 | `/ko/handbook/[slug].astro`, `/en/handbook/[slug].astro` | 기존 HandbookFeedback 위치 교체 |
| 블로그 상세 | `/ko/blog/[slug].astro`, `/en/blog/[slug].astro` | 본문 끝, 다음 글 링크 위 |
| 제품 상세 | `/ko/products/[slug].astro`, `/en/products/[slug].astro` | 본문 끝 |

---

## 5. 어드민 피드백 대시보드

**URL:** `/admin/feedback/`

### 5.1 레이아웃

기존 어드민 리스트 패턴 (`/admin/posts/`, `/admin/handbook/` 등)과 동일.

- **탭:** All / News / Handbook / Blog / Product
- **필터:** 전체 / 긍정(👍) / 부정(👎) — 각각 카운트 표시
- **검색:** 콘텐츠 제목 또는 메시지 텍스트
- **정렬:** `updated_at DESC` (최신순)

### 5.2 리스트 항목

```
[뉴스] "AI 업계 주요 뉴스" | 👎 부정확함 | user@email.com | 3시간 전
         "날짜가 틀렸어요"
```

- 콘텐츠 제목 클릭 → 해당 에디터로 이동
- reason이 있으면 태그로 표시
- message가 있으면 제목 아래에 미리보기

### 5.3 데이터 조회

```sql
SELECT cf.*,
  CASE cf.source_type
    WHEN 'news' THEN np.title
    WHEN 'handbook' THEN ht.term
    WHEN 'blog' THEN bp.title
    WHEN 'product' THEN p.name
  END AS content_title,
  pr.display_name, au.email
FROM content_feedback cf
LEFT JOIN news_posts np ON cf.source_type = 'news' AND cf.source_id = np.id
LEFT JOIN handbook_terms ht ON cf.source_type = 'handbook' AND cf.source_id = ht.id
LEFT JOIN blog_posts bp ON cf.source_type = 'blog' AND cf.source_id = bp.id
LEFT JOIN ai_products p ON cf.source_type = 'product' AND cf.source_id = p.id
LEFT JOIN profiles pr ON cf.user_id = pr.id
LEFT JOIN auth.users au ON cf.user_id = au.id
ORDER BY cf.updated_at DESC
LIMIT 50 OFFSET 0;  -- 페이지네이션 적용
```

**참고:** `content_title IS NULL`인 행은 원본 콘텐츠가 삭제된 피드백. "삭제된 콘텐츠"로 표시하고 일괄 정리 가능.

---

## 6. 마이그레이션 계획

실행 순서:

1. **`content_feedback` 테이블 생성** — 새 마이그레이션 파일
2. **RLS 정책 추가** — 같은 마이그레이션 또는 별도 파일
3. **데이터 이관** — `term_feedback` → `content_feedback`:
   ```sql
   INSERT INTO content_feedback (user_id, source_type, source_id, locale, reaction, reason, message, archived, created_at, updated_at)
   SELECT user_id, 'handbook', term_id, locale,
     CASE reaction WHEN 'helpful' THEN 'positive' WHEN 'confusing' THEN 'negative' ELSE 'positive' END,
     CASE reaction WHEN 'confusing' THEN 'confusing' ELSE NULL END,
     message, COALESCE(archived, FALSE), created_at, updated_at
   FROM term_feedback
   WHERE reaction IN ('helpful', 'confusing');
   ```
4. **새 API + 컴포넌트 배포** — `content-feedback.ts`, `ContentFeedback.astro`, `contentFeedback.ts`
5. **기존 파일 제거** — `term-feedback.ts`, `HandbookFeedback.astro`, `handbookFeedback.ts`
6. **정상 확인 후** — `term_feedback` 테이블 DROP + 관련 마이그레이션 정리
7. **어드민 대시보드 구현** — `/admin/feedback/index.astro`

---

## 7. 롤백 계획

마이그레이션은 파괴적(DROP)이므로 안전 순서:
- Step 1~3 (테이블 생성 + 이관) 후 Step 4~5 (코드 배포) 전까지 **양 테이블 공존** 상태. 이 시점에서 문제 발생 시 새 테이블만 DROP하면 원복.
- Step 6 (`term_feedback` DROP)은 코드 배포 + 정상 확인 **최소 1일 후** 실행. 급하지 않음.
- DROP 전 `term_feedback` 백업: `CREATE TABLE term_feedback_backup AS SELECT * FROM term_feedback;`

---

## 8. 테스트 계획

| 시나리오 | 검증 내용 |
|----------|----------|
| 긍정 피드백 | 👍 클릭 → API POST → DB 저장 → 버튼 하이라이트 |
| 부정 피드백 | 👎 → Bottom Sheet → reason 선택 + 메시지 → 제출 → DB 저장 |
| 피드백 철회 | DELETE → DB 삭제 → 버튼 초기화 |
| 피드백 변경 | 👍→👎 또는 👎→👍 → UPSERT → DB 업데이트 |
| 비로그인 | 버튼 클릭 → 로그인 프롬프트 |
| 프리뷰 모드 | 버튼 비활성화 + 읽기 전용 안내 |
| 4개 콘텐츠 타입 | 뉴스/핸드북/블로그/제품 각각 피드백 정상 동작 |
| reason 검증 | positive일 때 reason 전송 시 거부 |
| 어드민 대시보드 | 탭 필터, 리액션 필터, 검색, 페이지네이션 |
| 데이터 이관 | term_feedback 데이터가 content_feedback에 정확히 이관 (archived 포함) |

---

## 9. 제거 대상 (기존 시스템)

| 파일 | 설명 |
|------|------|
| `supabase/migrations/00014_term_feedback.sql` | 기존 테이블 (이관 후 DROP) |
| `supabase/migrations/00029_term_feedback_message.sql` | message 컬럼 추가 (통합됨) |
| `supabase/migrations/00030_admin_read_feedback.sql` | RLS (새 정책으로 교체) |
| `supabase/migrations/00031_term_feedback_archived.sql` | archived 컬럼 + 어드민 업데이트 정책 (통합됨) |
| `frontend/src/pages/api/user/term-feedback.ts` | 기존 API |
| `frontend/src/components/newsprint/HandbookFeedback.astro` | 기존 컴포넌트 |
| `frontend/src/scripts/handbookFeedback.ts` | 기존 스크립트 |
| `frontend/tests/handbook-feedback-*.test.cjs` | 기존 테스트 (새 테스트로 교체) |

---

## 10. 스코프 외 (추후 확장)

- 사이트 전반 UX 피드백 (푸터 피드백 버튼) — 사용자 규모 성장 후 `source_type = 'site'` 추가
- 피드백 기반 자동 알림 (부정 피드백 N건 이상 시 어드민 알림)
- 피드백 통계 대시보드 (Pipeline Analytics처럼 차트)
