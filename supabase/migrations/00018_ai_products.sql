-- 00018_ai_products.sql
-- AI Products feature: ai_product_categories and ai_products tables with RLS, indexes, and seed data

-- =============================================================================
-- 1. ai_product_categories table
-- =============================================================================
CREATE TABLE IF NOT EXISTS ai_product_categories (
  id              text PRIMARY KEY,
  label_en        text NOT NULL,
  label_ko        text NOT NULL,
  description_en  text,
  description_ko  text,
  icon            text,
  sort_order      int DEFAULT 0
);

ALTER TABLE ai_product_categories ENABLE ROW LEVEL SECURITY;

-- Public read
CREATE POLICY "public_select_ai_product_categories"
  ON ai_product_categories FOR SELECT
  USING (true);

-- Admin write
CREATE POLICY "admin_all_ai_product_categories"
  ON ai_product_categories FOR ALL
  USING (EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid()));

-- =============================================================================
-- 2. ai_products table
-- =============================================================================
CREATE TABLE IF NOT EXISTS ai_products (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug                 text UNIQUE NOT NULL,
  name                 text NOT NULL,
  name_ko              text,
  url                  text NOT NULL,

  tagline              text,
  tagline_ko           text,

  description          text,
  description_ko       text,

  primary_category     text NOT NULL REFERENCES ai_product_categories(id),
  secondary_categories text[],

  logo_url             text,
  thumbnail_url        text,
  demo_media           jsonb DEFAULT '[]'::jsonb,

  tags                 text[],
  platform             text[],
  korean_support       boolean DEFAULT false,
  released_at          date,

  pricing              text CHECK (pricing IN ('free', 'freemium', 'paid', 'enterprise')),
  pricing_note         text,

  is_published         boolean DEFAULT false,
  featured             boolean DEFAULT false,
  featured_order       int,
  sort_order           int DEFAULT 0,

  view_count           int DEFAULT 0,
  like_count           int DEFAULT 0,

  created_at           timestamptz DEFAULT NOW(),
  updated_at           timestamptz DEFAULT NOW()
);

ALTER TABLE ai_products ENABLE ROW LEVEL SECURITY;

-- Public read (published only)
CREATE POLICY "public_select_ai_products"
  ON ai_products FOR SELECT
  USING (is_published = true);

-- Admin write
CREATE POLICY "admin_all_ai_products"
  ON ai_products FOR ALL
  USING (EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid()));

-- =============================================================================
-- 3. Indexes
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_ai_products_primary_category
  ON ai_products(primary_category);

CREATE INDEX IF NOT EXISTS idx_ai_products_featured
  ON ai_products(featured, featured_order)
  WHERE is_published = true;

CREATE INDEX IF NOT EXISTS idx_ai_products_slug
  ON ai_products(slug);

CREATE INDEX IF NOT EXISTS idx_ai_products_published
  ON ai_products(is_published, sort_order);

CREATE INDEX IF NOT EXISTS idx_ai_products_tags
  ON ai_products USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_ai_products_platform
  ON ai_products USING GIN (platform);

CREATE INDEX IF NOT EXISTS idx_ai_products_secondary_categories
  ON ai_products USING GIN (secondary_categories);

-- =============================================================================
-- 4. RPC: increment view count (anon allowed)
-- =============================================================================
CREATE OR REPLACE FUNCTION increment_product_view_count(product_id uuid)
RETURNS void
LANGUAGE sql
SECURITY DEFINER
AS $$
  UPDATE ai_products
  SET view_count = view_count + 1
  WHERE id = product_id AND is_published = true;
$$;

-- =============================================================================
-- 5. Seed: 7 categories with editorial descriptions
-- =============================================================================
INSERT INTO ai_product_categories (id, label_en, label_ko, description_en, description_ko, icon, sort_order)
VALUES
(
  'assistant',
  'AI Assistants',
  'AI 어시스턴트',
  $desc$Stop searching, start asking. Summarize papers, write emails, plan trips, translate anything — you now have a brilliant assistant available 24/7. ChatGPT, Claude, and Gemini are leading this revolution.$desc$,
  $desc$모르는 게 있으면 검색 대신 물어보세요. 논문 요약, 이메일 작성, 계획 수립, 언어 번역까지 — 이제 한 명의 똑똑한 조수가 24시간 옆에 있습니다. ChatGPT, Claude, Gemini가 이 싸움을 이끌고 있습니다.$desc$,
  '💬',
  1
),
(
  'image',
  'Image Generation',
  'AI 이미지 생성',
  $desc$No art school required. Describe the scene in your head and get back a watercolor, photograph, anime illustration, or product poster in seconds. One Midjourney prompt can replace a designer's full day.$desc$,
  $desc$미술을 배운 적 없어도 됩니다. 머릿속 장면을 글로 설명하면 — 수채화, 사진, 애니메이션, 포스터 — 그 어떤 스타일로도 만들어줍니다. Midjourney 한 장이 디자이너의 하루 작업을 대체하는 시대입니다.$desc$,
  '🎨',
  2
),
(
  'video',
  'Video Generation',
  'AI 영상 생성',
  $desc$A single sentence — or a single image — becomes a video. Ads, YouTube content, short films — you can now become a video creator without a camera. Sora and Kling are redefining what's possible.$desc$,
  $desc$텍스트 한 줄, 또는 이미지 한 장에서 동영상이 만들어집니다. 광고, 유튜브 썸네일, 단편 영화 — 촬영 장비 없이 영상 크리에이터가 될 수 있는 시대가 열렸습니다. Sora와 Kling이 이 분야를 바꾸고 있습니다.$desc$,
  '🎬',
  3
),
(
  'audio',
  'Voice & Music',
  'AI 음성/음악',
  $desc$No instrument skills needed. Type lyrics and get a full song. Type text and hear a human-like voice. Podcasts, ads, game narration — all possible solo now.$desc$,
  $desc$악기를 다룰 줄 몰라도, 노래를 못해도 괜찮습니다. 가사를 입력하면 완성된 노래가 나오고, 텍스트를 입력하면 실제 사람 같은 목소리로 읽어줍니다. 팟캐스트, 광고, 게임 더빙이 1인으로 가능해졌습니다.$desc$,
  '🎵',
  4
),
(
  'coding',
  'Coding Tools',
  'AI 코딩 도구',
  $desc$"Where do I even start learning to code?" is no longer the right question. Describe what you want, and the AI writes it. Developers are reporting 2-3x productivity gains with these tools.$desc$,
  $desc$"코딩을 배우려면 어디서부터?"라고 묻던 시대는 끝났습니다. 원하는 기능을 설명하면 코드를 작성해주고, 버그를 찾아주고, 테스트까지 만들어줍니다. 개발자라면 생산성이 2~3배 올라갑니다.$desc$,
  '💻',
  5
),
(
  'workflow',
  'Workflow & Automation',
  'AI 워크플로우',
  $desc$Automate repetitive work. Sort incoming emails, save to Notion, notify Slack — no code needed. These tools now let AI handle the decision-making in the middle, not just the routing.$desc$,
  $desc$반복되는 업무를 자동화하세요. Gmail로 들어오는 이메일을 자동으로 분류하고, Notion에 저장하고, Slack으로 알림 — 코딩 없이 가능합니다. AI가 중간 판단까지 맡아줍니다.$desc$,
  '⚙️',
  6
),
(
  'builder',
  'App Builders',
  'AI 앱 빌더',
  $desc$"I have an idea but no developer" is no longer an excuse. Describe your app in chat and get a working web application. Lovable, Bolt.new, and v0 are making this mainstream.$desc$,
  $desc$"앱을 만들고 싶은데 개발자가 없어요"라는 말이 더 이상 변명이 되지 않습니다. 아이디어를 채팅으로 설명하면 실제로 동작하는 웹 앱이 만들어집니다. Lovable, Bolt.new, v0가 이 영역을 개척하고 있습니다.$desc$,
  '🚀',
  7
)
ON CONFLICT (id) DO UPDATE SET
  label_en       = EXCLUDED.label_en,
  label_ko       = EXCLUDED.label_ko,
  description_en = EXCLUDED.description_en,
  description_ko = EXCLUDED.description_ko,
  icon           = EXCLUDED.icon,
  sort_order     = EXCLUDED.sort_order;
