-- ============================================================
-- Migration: 00034_blog_category_system.sql
-- Blog category system: groups, categories, subscriptions,
-- pinned posts, RLS policies, and moddatetime triggers.
-- ============================================================


-- ============================================================
-- 1. moddatetime extension
-- ============================================================
CREATE EXTENSION IF NOT EXISTS moddatetime;


-- ============================================================
-- 2. category_groups table + seed
-- ============================================================
CREATE TABLE category_groups (
  slug        text        PRIMARY KEY,
  label_ko    text        NOT NULL,
  label_en    text        NOT NULL,
  sort_order  integer     NOT NULL DEFAULT 0,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

INSERT INTO category_groups (slug, label_ko, label_en, sort_order) VALUES
  ('main', '주요 기록', 'Main Posts',   0),
  ('sub',  '작은 노트', 'Small Notes',  1);


-- ============================================================
-- 3. blog_categories table + seed
-- ============================================================
CREATE TABLE blog_categories (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  slug            text        UNIQUE NOT NULL,
  label_ko        text        NOT NULL,
  label_en        text        NOT NULL,
  description_ko  text,
  description_en  text,
  color           text        NOT NULL,
  icon            text,
  group_slug      text        NOT NULL REFERENCES category_groups(slug),
  sort_order      integer     NOT NULL DEFAULT 0,
  is_visible      boolean     NOT NULL DEFAULT true,
  write_mode      text        NOT NULL DEFAULT 'admin_only',
  banner_url      text,
  guidelines      text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

INSERT INTO blog_categories (slug, label_ko, label_en, color, group_slug, sort_order, icon, write_mode, is_visible) VALUES
  (
    'study',
    '학습 노트',
    'Study Notes',
    '#6E9682',
    'main',
    0,
    '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
    'admin_only',
    true
  ),
  (
    'project',
    '프로젝트 기록',
    'Project Log',
    '#8282AF',
    'main',
    1,
    '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    'admin_only',
    true
  ),
  (
    'career',
    '커리어 생각',
    'Career Thoughts',
    '#8C94AA',
    'main',
    2,
    '<rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    'admin_only',
    true
  ),
  (
    'work-note',
    '작업 메모',
    'Work Notes',
    '#6496AA',
    'sub',
    0,
    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/>',
    'admin_only',
    true
  ),
  (
    'daily',
    '일상',
    'Daily Life',
    '#AA8282',
    'sub',
    1,
    '<path d="M18 8h1a4 4 0 0 1 0 8h-1"/><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"/><line x1="6" y1="1" x2="6" y2="4"/><line x1="10" y1="1" x2="10" y2="4"/><line x1="14" y1="1" x2="14" y2="4"/>',
    'admin_only',
    true
  );


-- ============================================================
-- 4. Drop existing CHECK constraint + add FK on blog_posts
-- ============================================================
ALTER TABLE blog_posts DROP CONSTRAINT blog_posts_category_check;

ALTER TABLE blog_posts
  ADD CONSTRAINT fk_blog_posts_category
  FOREIGN KEY (category) REFERENCES blog_categories(slug)
  ON UPDATE CASCADE
  ON DELETE RESTRICT;


-- ============================================================
-- 5. category_subscriptions (future use, empty)
-- ============================================================
CREATE TABLE category_subscriptions (
  user_id      uuid        NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  category_id  uuid        NOT NULL REFERENCES blog_categories(id) ON DELETE CASCADE,
  created_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, category_id)
);


-- ============================================================
-- 6. pinned_posts (future use, empty)
-- ============================================================
CREATE TABLE pinned_posts (
  category_id  uuid        NOT NULL REFERENCES blog_categories(id) ON DELETE CASCADE,
  post_id      uuid        NOT NULL REFERENCES blog_posts(id) ON DELETE CASCADE,
  sort_order   integer     NOT NULL DEFAULT 0,
  pinned_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (category_id, post_id)
);


-- ============================================================
-- 7. RLS policies
-- ============================================================

-- blog_categories
ALTER TABLE blog_categories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "blog_categories_select" ON blog_categories
FOR SELECT USING (
  is_visible = true
  OR EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
);

CREATE POLICY "blog_categories_admin_insert" ON blog_categories
FOR INSERT WITH CHECK (
  EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
);

CREATE POLICY "blog_categories_admin_update" ON blog_categories
FOR UPDATE USING (
  EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
);

CREATE POLICY "blog_categories_admin_delete" ON blog_categories
FOR DELETE USING (
  EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
);

-- category_groups
ALTER TABLE category_groups ENABLE ROW LEVEL SECURITY;

CREATE POLICY "category_groups_select" ON category_groups
FOR SELECT USING (true);

CREATE POLICY "category_groups_admin_all" ON category_groups
FOR ALL USING (
  EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
);

-- category_subscriptions
ALTER TABLE category_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "category_subscriptions_own" ON category_subscriptions
FOR ALL USING (auth.uid() = user_id);

-- pinned_posts
ALTER TABLE pinned_posts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "pinned_posts_select" ON pinned_posts
FOR SELECT USING (true);

CREATE POLICY "pinned_posts_admin_all" ON pinned_posts
FOR ALL USING (
  EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
);


-- ============================================================
-- 8. moddatetime triggers
-- ============================================================
CREATE TRIGGER set_blog_categories_updated_at
BEFORE UPDATE ON blog_categories
FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at);

CREATE TRIGGER set_category_groups_updated_at
BEFORE UPDATE ON category_groups
FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at);
