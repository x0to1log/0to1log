-- 00011_rename_posts_create_blog.sql
-- Rename posts → news_posts (AI news only) + create blog_posts (study/career/project)
-- Also rename post_likes → news_likes, post_comments → news_comments
-- Create blog_likes, blog_comments
-- Update polymorphic item_type: 'post' → 'news', add 'blog'

-- ============================================================
-- 0. Relax polymorphic CHECK constraints BEFORE data migration
-- ============================================================
ALTER TABLE user_bookmarks DROP CONSTRAINT user_bookmarks_item_type_check;
ALTER TABLE user_bookmarks ADD CONSTRAINT user_bookmarks_item_type_check
    CHECK (item_type IN ('post', 'news', 'blog', 'term'));

ALTER TABLE reading_history DROP CONSTRAINT reading_history_item_type_check;
ALTER TABLE reading_history ADD CONSTRAINT reading_history_item_type_check
    CHECK (item_type IN ('post', 'news', 'blog', 'term'));

-- ============================================================
-- 1. Migrate blog-category rows out of posts before renaming
-- ============================================================

-- Create blog_posts first so we can move data into it
CREATE TABLE blog_posts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT NOT NULL,
    slug            TEXT UNIQUE NOT NULL,
    locale          TEXT NOT NULL DEFAULT 'en' CHECK (locale IN ('en', 'ko')),
    category        TEXT NOT NULL CHECK (category IN ('study', 'career', 'project')),
    status          TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    excerpt         TEXT,
    content         TEXT,
    focus_items     TEXT[],
    source_urls     TEXT[],
    reading_time_min INTEGER,
    tags            TEXT[],
    og_image_url    TEXT,

    -- Locale referential integrity
    translation_group_id UUID,
    source_post_id       UUID REFERENCES blog_posts(id) ON DELETE SET NULL,
    source_post_version  INTEGER,

    -- Timestamps
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    published_at    TIMESTAMPTZ
);

-- Move existing blog-category rows from posts → blog_posts
INSERT INTO blog_posts (
    id, title, slug, locale, category, status, excerpt, content,
    focus_items, source_urls, reading_time_min, tags, og_image_url,
    translation_group_id, source_post_id, source_post_version,
    created_at, updated_at, published_at
)
SELECT
    id, title, slug, locale, category, status, excerpt, content_original,
    focus_items, source_urls, reading_time_min, tags, og_image_url,
    translation_group_id, source_post_id, source_post_version,
    created_at, updated_at, published_at
FROM posts
WHERE category IN ('study', 'career', 'project');

-- Create blog engagement tables before moving data
CREATE TABLE blog_likes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    post_id UUID NOT NULL REFERENCES blog_posts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, post_id)
);

CREATE TABLE blog_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    post_id UUID NOT NULL REFERENCES blog_posts(id) ON DELETE CASCADE,
    body TEXT NOT NULL CHECK (char_length(body) BETWEEN 1 AND 2000),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Move likes/comments for blog posts
INSERT INTO blog_likes (id, user_id, post_id, created_at)
SELECT pl.id, pl.user_id, pl.post_id, pl.created_at
FROM post_likes pl
JOIN posts p ON pl.post_id = p.id
WHERE p.category IN ('study', 'career', 'project');

INSERT INTO blog_comments (id, user_id, post_id, body, created_at, updated_at)
SELECT pc.id, pc.user_id, pc.post_id, pc.body, pc.created_at, pc.updated_at
FROM post_comments pc
JOIN posts p ON pc.post_id = p.id
WHERE p.category IN ('study', 'career', 'project');

-- Update polymorphic references for blog items
UPDATE user_bookmarks SET item_type = 'blog'
WHERE item_type = 'post' AND item_id IN (
    SELECT id FROM posts WHERE category IN ('study', 'career', 'project')
);

UPDATE reading_history SET item_type = 'blog'
WHERE item_type = 'post' AND item_id IN (
    SELECT id FROM posts WHERE category IN ('study', 'career', 'project')
);

-- Clear self-referential FK before deleting to avoid ordering issues
UPDATE posts SET source_post_id = NULL WHERE category IN ('study', 'career', 'project');

-- Delete blog rows from posts (CASCADE removes their post_likes/post_comments)
DELETE FROM posts WHERE category IN ('study', 'career', 'project');

-- ============================================================
-- 2. Rename posts → news_posts
-- ============================================================
ALTER TABLE posts RENAME TO news_posts;
ALTER TABLE post_likes RENAME TO news_likes;
ALTER TABLE post_comments RENAME TO news_comments;

-- ============================================================
-- 3. Rename indexes
-- ============================================================
ALTER INDEX idx_posts_locale RENAME TO idx_news_posts_locale;
ALTER INDEX idx_posts_category RENAME TO idx_news_posts_category;
ALTER INDEX idx_posts_status RENAME TO idx_news_posts_status;
ALTER INDEX idx_posts_published RENAME TO idx_news_posts_published;
ALTER INDEX idx_posts_slug RENAME TO idx_news_posts_slug;
ALTER INDEX idx_posts_batch RENAME TO idx_news_posts_batch;
ALTER INDEX uq_posts_daily_ai_type RENAME TO uq_news_posts_daily_ai_type;
ALTER INDEX idx_post_likes_post_id RENAME TO idx_news_likes_post_id;
ALTER INDEX idx_post_comments_post_id RENAME TO idx_news_comments_post_id;

-- ============================================================
-- 4. Tighten news_posts constraints (ai-news only)
-- ============================================================

-- Safety: ensure no non-ai-news rows remain (in case prior DELETE was partial)
UPDATE news_posts SET source_post_id = NULL WHERE category != 'ai-news';
DELETE FROM news_posts WHERE category != 'ai-news';

ALTER TABLE news_posts DROP CONSTRAINT IF EXISTS chk_post_type_by_category;
-- Drop the old category check (was: category IN ('ai-news','study','career','project'))
ALTER TABLE news_posts DROP CONSTRAINT IF EXISTS posts_category_check;
ALTER TABLE news_posts ADD CONSTRAINT news_posts_category_check
    CHECK (category = 'ai-news');
-- post_type is now always required for news — set NULL values to 'research' first
UPDATE news_posts SET post_type = 'research' WHERE post_type IS NULL;
ALTER TABLE news_posts ALTER COLUMN post_type SET NOT NULL;

-- ============================================================
-- 5. Update remaining polymorphic item_type: 'post' → 'news'
--    then tighten CHECK to remove legacy 'post' value
-- ============================================================
UPDATE user_bookmarks SET item_type = 'news' WHERE item_type = 'post';
UPDATE reading_history SET item_type = 'news' WHERE item_type = 'post';

-- Tighten: remove legacy 'post' from allowed values
ALTER TABLE user_bookmarks DROP CONSTRAINT user_bookmarks_item_type_check;
ALTER TABLE user_bookmarks ADD CONSTRAINT user_bookmarks_item_type_check
    CHECK (item_type IN ('news', 'blog', 'term'));

ALTER TABLE reading_history DROP CONSTRAINT reading_history_item_type_check;
ALTER TABLE reading_history ADD CONSTRAINT reading_history_item_type_check
    CHECK (item_type IN ('news', 'blog', 'term'));

-- ============================================================
-- 6. blog_posts indexes
-- ============================================================
CREATE INDEX idx_blog_posts_locale ON blog_posts(locale);
CREATE INDEX idx_blog_posts_category ON blog_posts(category);
CREATE INDEX idx_blog_posts_status ON blog_posts(status);
CREATE INDEX idx_blog_posts_published ON blog_posts(published_at DESC NULLS LAST);
CREATE INDEX idx_blog_posts_slug ON blog_posts(slug);

CREATE INDEX idx_blog_likes_post_id ON blog_likes(post_id);
CREATE INDEX idx_blog_comments_post_id ON blog_comments(post_id, created_at);

-- ============================================================
-- 7. RLS for blog tables
-- ============================================================
ALTER TABLE blog_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE blog_likes ENABLE ROW LEVEL SECURITY;
ALTER TABLE blog_comments ENABLE ROW LEVEL SECURITY;

-- blog_posts: same pattern as news_posts
CREATE POLICY "blog_posts_read" ON blog_posts FOR SELECT
    USING (
        status = 'published'
        OR EXISTS (SELECT 1 FROM admin_users au WHERE au.user_id = auth.uid())
    );
CREATE POLICY "blog_posts_write" ON blog_posts FOR INSERT
    WITH CHECK (EXISTS (SELECT 1 FROM admin_users au WHERE au.user_id = auth.uid()));
CREATE POLICY "blog_posts_update" ON blog_posts FOR UPDATE
    USING (EXISTS (SELECT 1 FROM admin_users au WHERE au.user_id = auth.uid()));
CREATE POLICY "blog_posts_delete" ON blog_posts FOR DELETE
    USING (EXISTS (SELECT 1 FROM admin_users au WHERE au.user_id = auth.uid()));

-- blog_likes
CREATE POLICY "Anyone can read blog likes" ON blog_likes FOR SELECT USING (true);
CREATE POLICY "Auth users can blog like" ON blog_likes FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can unlike blog" ON blog_likes FOR DELETE USING (auth.uid() = user_id);

-- blog_comments
CREATE POLICY "Anyone can read blog comments" ON blog_comments FOR SELECT USING (true);
CREATE POLICY "Auth users can blog comment" ON blog_comments FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can edit own blog comment" ON blog_comments FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own blog comment" ON blog_comments FOR DELETE USING (auth.uid() = user_id);
