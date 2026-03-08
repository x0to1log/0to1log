# User Features Design ? ?? ??? ?? (AI News + Handbook + Library ??)

> **작성일:** 2026-03-08
> **작성자:** Amy (Solo)
> **상태:** Design Approved
> **스택:** Astro v5 SSR + Supabase Auth + FastAPI
> **선행 조건:** Phase 2D-INT 완료
> **관련 스펙:** `docs/08_Handbook.md`, `docs/04_Frontend_Spec.md` §15-1

---

> Naming note: public product language uses `AI News`, `Handbook`, and `Library`; internal/admin language uses `Posts`; route compatibility remains `/{locale}/log/`.

## 1. 목적

로그인한 일반 사용자(non-admin)를 위한 콘텐츠 참여 기능을 구현한다.
현재는 admin 로그인만 존재하며, 일반 사용자 기능은 0개 상태.

**핵심 전략: "로그인 발판"**

Phase 4의 커뮤니티/수익화로 가기 전에, 로그인 습관을 만드는 발판이 필요하다.
Log(기사)와 Handbook(용어)를 하나의 학습 플랫폼으로 묶어, 로그인의 가치를 높인다.

```
현재                     발판 (B단계)                       목표 (C/D단계)
────                    ────                              ────
댓글만 가능      →    통합 북마크 + 학습 기록 + 진도       →    포인트/게임/구독
(로그인 이유 없음)     (로그인하면 편리함)                    (로그인 필수)
```

**즉시 구현 범위 (B: Content Participation):**
- 소셜 로그인 (GitHub + Google)
- 프로필 (페르소나 선택)
- 통합 북마크 (기사 + 용어 저장)
- 통합 읽기 기록 (기사 + 용어 자동 추적, 리스트 시각 표시)
- 학습 진도 (Handbook 카테고리별 용어 학습 현황)
- 내 서재 페이지 (`/library`)

**추후 확장 (C: Community, D: Monetization):**
- 댓글/리액션
- 페르소나 기반 추천 (읽기 기록 + 학습 진도 데이터 활용)
- 하이라이트 & 메모
- 포인트 시스템 (학습 진도와 연동)
- 프리미엄 구독

---

## 2. 비즈니스 근거

### 로그인 가치 분석 (Log + Handbook 통합)

| 기능 | 비로그인 | 로그인 | 가치 |
|------|---------|--------|------|
| Log/Handbook 읽기 | O (쿠키) | O (DB 동기화) | 기기 간 유지 |
| 페르소나 전환 | O (쿠키) | O (DB) | 기기 간 유지 |
| 피드백 (좋아요) | O (쿠키) | O | — |
| 댓글 작성 | X | O | 참여 |
| 기사 북마크 | X | O | 재방문 이유 |
| **용어 북마크** | X | O | **학습 맥락 보존** |
| **읽기 기록 (기사+용어)** | X | O | **학습 여정 타임라인** |
| **학습 진도** | X | O | **0to1log만의 차별화** |

### Handbook이 만드는 시너지

- `handbook_terms.is_favourite`는 현재 Amy 관리용 boolean → 사용자별 북마크로 확장
- 기사 읽다가 → 모르는 용어 클릭 → 이해 → 다시 기사: 이 플라이휠 행동이 **기록으로 남음**
- 10개 카테고리 + 난이도 3단계가 이미 **학습 구조**를 형성 → 진도 UI 자연스러움
- "40% 학습" → 나머지 완성 심리 (Progress Bias, Endowed Progress Effect)

### KPI 연결

| 기능 | 영향 받는 KPI (06 §3.2) |
|------|------------------------|
| 통합 북마크 | Retention (재방문율) — 저장한 콘텐츠 확인하러 재방문 |
| 읽기 기록 | Activation (세션 깊이) — 연속 읽기 유도 |
| 학습 진도 | Retention + Activation — "완성하고 싶다" 심리로 재방문 |

---

## 3. 인증 (Auth)

### 3.1 Provider
- **GitHub OAuth** + **Google OAuth** via Supabase Auth
- admin은 기존 email/password 유지 (`/admin/login`)
- 일반 사용자는 소셜 로그인 전용 (`/login`)

### 3.2 로그인 흐름
```
[/login 페이지] → 사용자가 GitHub/Google 버튼 클릭
→ Supabase OAuth redirect → provider 인증
→ Supabase callback → /api/auth/callback (기존 엔드포인트 재사용)
→ httpOnly cookie 설정 (sb-access-token, sb-refresh-token)
→ 원래 페이지로 redirect
```

### 3.3 세션 관리
- 기존 middleware.ts의 토큰 검증/갱신 로직 재사용
- 현재 middleware는 `/admin/*` 경로만 보호 → 일반 사용자 API 경로 (`/api/user/*`) 추가
- `context.locals.user`에 사용자 정보 저장 (기존 패턴 유지)

### 3.4 역할 구분
- `admin_users` 테이블에 email이 존재하면 admin
- 그 외 Supabase Auth 사용자는 일반 사용자
- 역할에 따른 UI 분기: admin → `/admin` 접근 가능, 일반 → `/library` 접근 가능

---

## 4. DB 스키마 (4개 테이블 추가)

### 4.1 `profiles`
```sql
CREATE TABLE profiles (
  id         UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name TEXT,
  avatar_url   TEXT,
  persona      TEXT CHECK (persona IN ('beginner', 'learner', 'expert')),
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- RLS: 본인만 read/update
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users read own profile"
  ON profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users update own profile"
  ON profiles FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Users insert own profile"
  ON profiles FOR INSERT WITH CHECK (auth.uid() = id);
```

### 4.2 `user_bookmarks` (통합 — 기사 + 용어)
```sql
CREATE TABLE user_bookmarks (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  item_type  TEXT NOT NULL CHECK (item_type IN ('post', 'term')),
  item_id    UUID NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, item_type, item_id)
);

CREATE INDEX idx_user_bookmarks_user ON user_bookmarks(user_id);
CREATE INDEX idx_user_bookmarks_item ON user_bookmarks(item_type, item_id);

-- RLS: 본인만 CRUD
ALTER TABLE user_bookmarks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users read own bookmarks"
  ON user_bookmarks FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users insert own bookmarks"
  ON user_bookmarks FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users delete own bookmarks"
  ON user_bookmarks FOR DELETE USING (auth.uid() = user_id);
```

**설계 근거:** `post_id` 대신 `item_type + item_id` 패턴을 사용하여 기사(posts)와 용어(handbook_terms)를 하나의 테이블로 통합. FK constraint 대신 앱 레벨에서 참조 무결성 관리 — `item_type`이 확장 시 새 타입 추가만 하면 됨.

### 4.3 `reading_history` (통합 — 기사 + 용어)
```sql
CREATE TABLE reading_history (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  item_type  TEXT NOT NULL CHECK (item_type IN ('post', 'term')),
  item_id    UUID NOT NULL,
  read_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, item_type, item_id)
);

CREATE INDEX idx_reading_history_user ON reading_history(user_id);
CREATE INDEX idx_reading_history_item ON reading_history(item_type, item_id);

-- RLS: 본인만 read/insert/delete
ALTER TABLE reading_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users read own history"
  ON reading_history FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users insert own history"
  ON reading_history FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users delete own history"
  ON reading_history FOR DELETE USING (auth.uid() = user_id);
```

### 4.4 `learning_progress` (Handbook 학습 진도)
```sql
CREATE TABLE learning_progress (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  term_id    UUID NOT NULL REFERENCES handbook_terms(id) ON DELETE CASCADE,
  status     TEXT NOT NULL DEFAULT 'read'
             CHECK (status IN ('read', 'learned')),
  read_at    TIMESTAMPTZ DEFAULT NOW(),
  learned_at TIMESTAMPTZ,
  UNIQUE(user_id, term_id)
);

CREATE INDEX idx_learning_progress_user ON learning_progress(user_id);

-- RLS: 본인만 CRUD
ALTER TABLE learning_progress ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users read own progress"
  ON learning_progress FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users insert own progress"
  ON learning_progress FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users update own progress"
  ON learning_progress FOR UPDATE USING (auth.uid() = user_id);
```

**학습 상태 정의:**
- `read`: 용어 상세 페이지 방문 시 자동 기록 (읽기 기록과 동시)
- `learned`: 사용자가 "학습 완료" 버튼 클릭 시 수동 전환

---

## 5. API 엔드포인트 (Astro API Routes)

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/auth/callback` | 기존 — OAuth/email 토큰 → cookie 설정 |
| POST | `/api/auth/logout` | 기존 — cookie 삭제 |
| GET | `/api/user/profile` | 내 프로필 조회 |
| PUT | `/api/user/profile` | 프로필 수정 (display_name, persona) |
| POST | `/api/user/reading-history` | 읽기 기록 추가 (`{ item_type, item_id }`) |
| GET | `/api/user/reading-history` | 내 읽기 기록 목록 (query: `?type=post\|term`) |
| DELETE | `/api/user/reading-history/:id` | 읽기 기록 삭제 |
| GET | `/api/user/bookmarks` | 내 북마크 목록 (query: `?type=post\|term`) |
| POST | `/api/user/bookmarks` | 북마크 추가 (`{ item_type, item_id }`) |
| DELETE | `/api/user/bookmarks/:id` | 북마크 삭제 |
| GET | `/api/user/learning-progress` | 학습 진도 조회 (카테고리별 집계 포함) |
| POST | `/api/user/learning-progress` | 학습 기록 추가 (`{ term_id }`, 자동: `read`) |
| PUT | `/api/user/learning-progress/:id` | 학습 완료 전환 (`status: 'learned'`) |

모든 `/api/user/*` 엔드포인트는 `sb-access-token` cookie 기반 인증 필수.

---

## 6. UI 변경

### 6.1 헤더 (Navigation.astro)
- **비로그인:** 우측에 "Sign In" 텍스트 링크 추가
- **로그인:** "Sign In" 대신 아바타 아이콘 (Google/GitHub 프로필 이미지 또는 이니셜)
- **아바타 클릭 → 드롭다운:**
  - 내 서재 (`/library`)
  - 설정 (페르소나 변경 등)
  - 로그아웃

### 6.2 로그인 페이지 (`/login`)
- 별도 경로 (admin의 `/admin/login`과 분리)
- GitHub 로그인 버튼 + Google 로그인 버튼
- 뉴스프린트 디자인 토큰 사용
- 로그인 후 이전 페이지로 redirect (`redirectTo` query param)

### 6.3 리스트 페이지 — 읽기 기록 표시 (Log + Handbook 공통)
- 로그인 사용자가 이미 읽은 글/용어: `opacity: 0.55` 적용
- CSS class: `.newsprint-card--read { opacity: 0.55; }`
- 서버에서 사용자의 `reading_history` id 목록을 조회 → 카드에 class 적용
- **Log 리스트** (`/en/log/`, `/ko/log/`): 읽은 기사 표시
- **Handbook 리스트** (`/en/handbook/`, `/ko/handbook/`): 읽은 용어 표시

### 6.4 북마크 버튼 (Log + Handbook 공통)
- **리스트 카드:** 카드 우측 하단에 작은 북마크 아이콘 (flag/ribbon)
- **상세 페이지:** 제목 영역 옆에 북마크 아이콘
- 토글 동작: 클릭 시 즉시 북마크 추가/제거 (optimistic UI)
- 비로그인 시 클릭 → `/login?redirectTo=현재경로`로 이동
- **Log 상세** + **Handbook 상세** 모두 동일 패턴

### 6.5 상세 페이지 — 자동 기록 (Log + Handbook 공통)
- 페이지 로드 시 `POST /api/user/reading-history` 호출 (로그인 사용자만)
- `UNIQUE(user_id, item_type, item_id)` 제약 → `ON CONFLICT DO NOTHING`
- **Handbook 상세:** 추가로 `POST /api/user/learning-progress` 호출 (자동 `read` 상태)

### 6.6 Handbook 상세 — 학습 완료 버튼
- 용어 상세 페이지 하단에 "학습 완료" 체크 버튼
- 이미 `read` 상태 → 클릭 시 `learned`로 전환
- 이미 `learned` → 체크 해제 가능 (다시 `read`로)
- 비로그인 시: 버튼 숨김 (학습 진도는 로그인 전용)

```
┌──────────────────────────────────────┐
│  LLM (Large Language Model)          │
│  ...본문...                          │
│                                      │
│  ┌────────────────────────────────┐  │
│  │  [x] 학습 완료    2026-03-08   │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

### 6.7 내 서재 페이지 (`/library`)
- 로그인 필수 (비로그인 → `/login?redirectTo=/library`)
- **3개 탭:**

```
[읽은 글 / Read]  [저장한 글 / Saved]  [학습 현황 / Progress]
```

**읽은 글 탭:**
- `reading_history` 기반, 최신 순
- 기사와 용어가 섞여서 타임라인으로 표시
- 타입 구분: 기사는 카테고리 배지, 용어는 "Handbook" 배지
- 개별 삭제 가능

```
[최근 본 콘텐츠]
• LLM (Handbook · AI/ML · Beginner)              3월 8일
• GPT-5 아키텍처 분석 (Log · AI NEWS)             3월 8일
• RAG (Handbook · AI/ML · Intermediate)           3월 7일
• Cursor 투자 유치 분석 (Log · AI NEWS)            3월 7일
```

**저장한 글 탭:**
- `user_bookmarks` 기반, 최신 순
- 기사/용어 통합 목록 (타입 배지로 구분)
- 개별 삭제 가능

**학습 현황 탭 (Handbook 특화):**
- 카테고리별 학습 진도 바
- `read` = 방문만 함, `learned` = 학습 완료 체크
- 진도 바는 `learned` 기준으로 계산

```
[내 학습 현황]
AI/ML & Algorithm    ████████░░  4/5 용어 학습 완료
DB / Data Infra      ██░░░░░░░░  1/3 용어 학습 완료
Backend              ░░░░░░░░░░  미시작

전체 진도: 5/30 용어 학습 완료 (17%)
         12/30 용어 읽음 (40%)
```

---

## 7. `handbook_terms.is_favourite`와의 관계

`is_favourite`는 **Amy의 관리용 필드** (어드민에서 "이 용어는 중요" 마킹)로 유지한다.
사용자별 즐겨찾기는 별도 `user_bookmarks` 테이블로 관리.

| 필드 | 용도 | 소유자 |
|------|------|--------|
| `handbook_terms.is_favourite` | 어드민 큐레이션 (목록 상단 고정 등) | Amy |
| `user_bookmarks (item_type='term')` | 사용자 개인 저장 | 각 사용자 |

---

## 8. 기존 코드 재사용

| 기존 코드 | 재사용 방식 |
|-----------|------------|
| `frontend/src/lib/supabase.ts` | Supabase client — OAuth 호출에도 동일 사용 |
| `frontend/src/lib/supabaseAdmin.ts` | 인증된 Supabase client (user JWT 기반) |
| `frontend/src/pages/api/auth/callback.ts` | OAuth redirect 후 토큰 → cookie 설정 |
| `frontend/src/middleware.ts` | 토큰 검증/갱신 로직 확장 (admin + user 경로) |
| `frontend/src/components/newsprint/NewsprintListCard.astro` | 내 서재 목록 렌더링 |
| `frontend/src/components/Navigation.astro` | Sign In / 아바타 드롭다운 추가 |
| `frontend/src/styles/global.css` | `.newsprint-card--read` 등 스타일 추가 |

---

## 9. 기존 코드 영향 범위

| 파일 | 변경 유형 | 영향 |
|------|-----------|------|
| `supabase/migrations/00007_user_tables.sql` | 새 파일 | 없음 (새 테이블 4개) |
| `frontend/src/pages/login.astro` | 새 파일 | 없음 (새 라우트) |
| `frontend/src/pages/library/index.astro` | 새 파일 | 없음 (새 라우트) |
| `frontend/src/pages/api/user/*.ts` | 새 파일 (4개) | 없음 (새 API) |
| `frontend/src/pages/api/auth/callback.ts` | 수정 | OAuth redirect 지원 추가 |
| `frontend/src/middleware.ts` | 수정 | `/api/user/*`, `/library` 경로 보호 추가 |
| `frontend/src/components/Navigation.astro` | 수정 | Sign In / 아바타 드롭다운 |
| `frontend/src/components/newsprint/NewsprintListCard.astro` | 수정 | 북마크 아이콘 + read 상태 |
| `frontend/src/pages/en/log/index.astro` | 수정 | 읽기 기록 → read class |
| `frontend/src/pages/ko/log/index.astro` | 수정 | 동일 |
| `frontend/src/pages/en/log/[slug].astro` | 수정 | 자동 기록 + 북마크 |
| `frontend/src/pages/ko/log/[slug].astro` | 수정 | 동일 |
| `frontend/src/pages/en/handbook/index.astro` | 수정 | 읽기 기록 → read class |
| `frontend/src/pages/ko/handbook/index.astro` | 수정 | 동일 |
| `frontend/src/pages/en/handbook/[slug].astro` | 수정 | 자동 기록 + 북마크 + 학습 완료 |
| `frontend/src/pages/ko/handbook/[slug].astro` | 수정 | 동일 |
| `frontend/src/styles/global.css` | 수정 | user UI 스타일 추가 |

**기존 기능에 대한 영향:** 최소. 기존 페이지에는 로그인 사용자 전용 UI 요소(북마크 아이콘, read 상태)를 추가하는 수준. 비로그인 사용자의 기존 경험은 변경 없음.

---

## 10. 확장성 (C/D단계)

### Phase 3 — 추천 & 학습 고도화 (C: Community 준비)

| 기능 | 데이터 소스 | 설명 |
|------|------------|------|
| 페르소나 기반 추천 | 읽기 기록 + 학습 진도 + persona | "아직 안 읽은 Beginner 용어" 추천 |
| 하이라이트 & 메모 | 새 테이블 | 기사 + 용어 페이지에서 형광펜 + 노트 |
| 알림 (관심 카테고리) | 학습 진도의 카테고리 데이터 | 카테고리 신규 기사/용어 알림 |

### Phase 4 — 포인트 & 커뮤니티 (D: Monetization 준비)

| 기능 | 연결 포인트 |
|------|------------|
| 포인트 시스템 | 학습 진도와 직접 연동 ("용어 5개 학습 → 10포인트") |
| 뱃지 | "AI/ML 카테고리 전체 학습 완료" → 뱃지 부여 |
| 댓글/리액션 | `profiles` 테이블 확장 (bio, preferences) |
| 프리미엄 구독 | `user_bookmarks` 패턴으로 `reactions`, `comments` 복제 |

### 확장 시 스키마 변경

- `profiles`에 `bio`, `preferences` 컬럼 추가
- `user_bookmarks.item_type`에 새 타입 추가 가능 (예: `'collection'`)
- `learning_progress.status`에 새 상태 추가 가능 (예: `'mastered'`)
- 드롭다운 메뉴에 "댓글 관리", "포인트" 메뉴 추가

---

## 11. 구현 로드맵

| 시점 | 기능 | 선행 조건 |
|------|------|-----------|
| Phase 2 후반 | 소셜 로그인 + 프로필 + 댓글 | Phase 2D-INT 완료 |
| Phase 2 후반 | 통합 북마크 (기사 + 용어) | 소셜 로그인 + Handbook H1 |
| Phase 2 후반 | 통합 읽기 기록 (기사 + 용어) | 소셜 로그인 + Handbook H1 |
| H1.5 직후 | 학습 진도 (Handbook 특화) | Handbook H1 완료 |
| Phase 3 초반 | 추천 + 학습 고도화 | 읽기 기록 데이터 축적 |
| Phase 4 | 포인트/뱃지/구독 | 학습 진도 + 커뮤니티 규모 확보 |

---

## 12. 검증

1. `supabase migration` 적용 → 테이블 4개 생성 확인
2. GitHub/Google 소셜 로그인 → cookie 설정 → 세션 유지 확인
3. **Log 상세** 방문 → `reading_history (item_type='post')` 자동 기록 확인
4. **Handbook 상세** 방문 → `reading_history (item_type='term')` + `learning_progress (status='read')` 자동 기록 확인
5. Log 리스트에서 읽은 기사 opacity 감소 확인
6. Handbook 리스트에서 읽은 용어 opacity 감소 확인
7. 기사 북마크 토글 → `user_bookmarks (item_type='post')` DB 반영 확인
8. 용어 북마크 토글 → `user_bookmarks (item_type='term')` DB 반영 확인
9. Handbook 상세에서 "학습 완료" 체크 → `learning_progress (status='learned')` 전환 확인
10. `/library` — 읽은 글 탭: 기사+용어 통합 타임라인 확인
11. `/library` — 저장한 글 탭: 기사+용어 통합 목록 확인
12. `/library` — 학습 현황 탭: 카테고리별 진도 바 확인
13. 비로그인 시 북마크 클릭 → `/login` redirect 확인
14. 비로그인 시 학습 완료 버튼 미표시 확인
15. 로그아웃 → cookie 삭제 → 읽기 기록/북마크/학습 UI 미표시 확인
16. `cd frontend && npm run build` — 0 errors
