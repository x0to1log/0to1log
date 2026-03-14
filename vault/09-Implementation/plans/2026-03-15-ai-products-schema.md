# AI Products — DB 스키마

> Date: 2026-03-15
> Status: Confirmed
> DB: Supabase (PostgreSQL)

---

## ai_products 테이블

```sql
CREATE TABLE ai_products (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug                 text UNIQUE NOT NULL,         -- URL: "midjourney", "chatgpt"
  name                 text NOT NULL,
  name_ko              text,                          -- 한국어 이름 (선택)
  url                  text NOT NULL,                 -- 공식 사이트 URL

  -- 한줄 설명
  tagline              text,                          -- EN
  tagline_ko           text,                          -- KO

  -- 에디토리얼 설명 (마크다운)
  description          text,                          -- EN
  description_ko       text,                          -- KO

  -- 카테고리
  primary_category     text NOT NULL REFERENCES ai_product_categories(id),
  secondary_categories text[],                        -- 복수 카테고리 (선택)

  -- 미디어
  logo_url             text,                          -- Supabase Storage
  thumbnail_url        text,                          -- 대표 이미지
  demo_media           jsonb DEFAULT '[]',            -- [{type: "image"|"video", url, caption}]

  -- 태그 & 메타
  tags                 text[],                        -- ["무료", "API", "모바일앱", ...]
  platform             text[],                        -- ["web", "ios", "android", "api", "desktop"]
  korean_support       boolean DEFAULT false,
  released_at          date,

  -- 가격
  pricing              text CHECK (pricing IN ('free', 'freemium', 'paid', 'enterprise')),
  pricing_note         text,                          -- "무료 플랜: 월 25크레딧"

  -- 노출
  is_published         boolean DEFAULT false,
  featured             boolean DEFAULT false,
  featured_order       int,                           -- featured 정렬 순서
  sort_order           int DEFAULT 0,                 -- 카테고리 내 수동 정렬

  -- 통계
  view_count           int DEFAULT 0,
  like_count           int DEFAULT 0,

  -- 시스템
  created_at           timestamptz DEFAULT now(),
  updated_at           timestamptz DEFAULT now()
);
```

---

## ai_product_categories 테이블

```sql
CREATE TABLE ai_product_categories (
  id              text PRIMARY KEY,    -- "assistant", "image", "video", "audio", "coding", "workflow", "builder"
  label_en        text NOT NULL,
  label_ko        text NOT NULL,
  description_en  text,               -- 에디토리얼 설명 (EN)
  description_ko  text,               -- 에디토리얼 설명 (KO)
  icon            text,               -- emoji 또는 lucide icon name
  sort_order      int DEFAULT 0
);
```

---

## 초기 카테고리 데이터

```sql
INSERT INTO ai_product_categories (id, label_en, label_ko, icon, sort_order) VALUES
  ('assistant', 'AI Assistants',    'AI 어시스턴트', '💬', 1),
  ('image',     'Image Generation', 'AI 이미지 생성', '🎨', 2),
  ('video',     'Video Generation', 'AI 영상 생성',   '🎬', 3),
  ('audio',     'Voice & Music',    'AI 음성/음악',   '🎵', 4),
  ('coding',    'Coding Tools',     'AI 코딩 도구',   '💻', 5),
  ('workflow',  'Workflow & Automation', 'AI 워크플로우', '⚙️', 6),
  ('builder',   'App Builders',     'AI 앱 빌더',     '🚀', 7);
```

에디토리얼 설명은 `vault/05-Content/AI-Products-Categories.md` 참조.

---

## 인덱스 (성능)

```sql
CREATE INDEX idx_ai_products_primary_category ON ai_products(primary_category);
CREATE INDEX idx_ai_products_featured ON ai_products(featured, featured_order) WHERE is_published = true;
CREATE INDEX idx_ai_products_slug ON ai_products(slug);
CREATE INDEX idx_ai_products_published ON ai_products(is_published, sort_order);
```

---

## demo_media JSONB 구조

```json
[
  { "type": "image", "url": "https://...", "caption": "메인 인터페이스" },
  { "type": "video", "url": "https://youtube.com/...", "caption": "사용 데모" },
  { "type": "video", "url": "https://storage.../demo.mp4", "caption": "30초 소개" }
]
```

---

## RLS 정책

- `SELECT`: `is_published = true` 조건으로 공개 접근 허용
- `INSERT/UPDATE/DELETE`: 어드민 role만 허용 (기존 어드민 정책 패턴 동일)
- `view_count`, `like_count` 업데이트: 별도 RPC 함수로 처리 (anon 허용)
