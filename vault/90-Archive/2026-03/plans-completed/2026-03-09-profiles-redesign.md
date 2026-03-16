# Profiles Table Redesign — Hybrid Private-First

> **작성일:** 2026-03-09
> **상태:** Design Approved
> **관련 문서:** `docs/plans/2026-03-08-user-features-design.md` §4.1

---

## 1. 목적

기존 `profiles` 테이블(5개 컬럼)을 확장하여 하이브리드 프로필(기본 프라이빗, 공개 전환 가능)을 지원한다.

## 2. 접근 방식

**Lean Extension** — 지금 필요한 컬럼 + 퍼블릭 전환 준비만. YAGNI 원칙 적용.
알림 설정, 관심 카테고리 등은 해당 기능 구현 시 별도 추가.

## 3. 스키마

```sql
CREATE TABLE profiles (
  id                    UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,

  -- Identity
  display_name          TEXT,
  username              TEXT UNIQUE,
  avatar_url            TEXT,
  bio                   TEXT,

  -- Preferences
  persona               TEXT CHECK (persona IN ('beginner', 'learner', 'expert')),
  preferred_locale      TEXT DEFAULT 'ko' CHECK (preferred_locale IN ('en', 'ko')),

  -- Visibility
  is_public             BOOLEAN DEFAULT FALSE,

  -- Onboarding
  onboarding_completed  BOOLEAN DEFAULT FALSE,

  -- Timestamps
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at            TIMESTAMPTZ DEFAULT NOW()
);
```

### 기존 대비 변경점

| 컬럼 | 상태 | 용도 |
|---|---|---|
| `display_name` | 유지 | 사이트 내 표시 이름 |
| `avatar_url` | 유지 | OAuth 기본값, 유저 업로드 시 덮어쓰기 |
| `persona` | 유지 | 콘텐츠 난이도 기본 선호 |
| `username` | **신규** | 유니크 아이디. 퍼블릭 전환 시 URL `/u/{username}` |
| `bio` | **신규** | 자기소개. 공개 전환 시 프로필에 표시 |
| `preferred_locale` | **신규** | 선호 언어. 로그인 시 자동 안내 |
| `is_public` | **신규** | 프로필 공개 여부 (기본 비공개) |
| `onboarding_completed` | **신규** | 첫 로그인 온보딩 완료 여부 |

## 4. Indexes & Constraints

```sql
CREATE INDEX idx_profiles_username ON profiles(username);

-- username: 3~20자, 영소문자 + 숫자 + 하이픈
ALTER TABLE profiles ADD CONSTRAINT chk_username_format
  CHECK (username ~ '^[a-z0-9][a-z0-9-]{1,18}[a-z0-9]$');
```

## 5. RLS

```sql
-- 본인 OR 공개 프로필은 누구나 읽기
CREATE POLICY "Users read own or public profile"
  ON profiles FOR SELECT
  USING (auth.uid() = id OR is_public = true);

-- INSERT/UPDATE: 본인만
CREATE POLICY "Users insert own profile"
  ON profiles FOR INSERT WITH CHECK (auth.uid() = id);
CREATE POLICY "Users update own profile"
  ON profiles FOR UPDATE USING (auth.uid() = id);
```

## 6. avatar_url 동작

- 첫 로그인 시 OAuth provider 이미지로 자동 세팅
- 유저가 프로필에서 직접 이미지 업로드 → Supabase Storage 저장 → URL 덮어쓰기
- 유저가 이미지 삭제 → OAuth 이미지로 복귀 (앱 로직에서 처리)

## 7. persona 동작 규칙

- `profiles.persona` = DB에 저장된 **기본 페르소나** (프로필 설정에서만 변경)
- 기사 페이지에서 탭 전환 = **임시 보기 전환** (클라이언트 UI만, DB 미반영)
- `PUT /api/user/profile`로 persona 변경할 때만 DB 업데이트

## 8. 프로필 생성 타이밍

- OAuth 첫 로그인 성공 후, 앱 코드에서 `profiles` INSERT
- `display_name`: OAuth provider의 이름
- `avatar_url`: OAuth provider의 프로필 이미지
- `persona`: NULL (온보딩에서 선택)
- `preferred_locale`: 로그인 시점의 URL locale 또는 기본값 `'ko'`
- `onboarding_completed`: FALSE

## 9. 확장 예정 (별도 마이그레이션)

- 관심 카테고리 (`interests TEXT[]`) — 내부 알림 기능 구현 시
- 알림 설정 — 사이트 내부 알림 기능 구현 시 별도 테이블 또는 JSONB
- 소셜 링크 — 커뮤니티 기능(Phase C) 시

## Related Plans

- [[plans/2026-03-08-user-features-design|사용자 기능 설계]]
