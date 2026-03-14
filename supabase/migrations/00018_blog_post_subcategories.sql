-- 00018_blog_post_subcategories.sql
-- Expand blog_posts category CHECK to include work-note and daily subcategories

ALTER TABLE blog_posts
DROP CONSTRAINT IF EXISTS blog_posts_category_check;

ALTER TABLE blog_posts
ADD CONSTRAINT blog_posts_category_check
CHECK (category IN ('study', 'career', 'project', 'work-note', 'daily'));
