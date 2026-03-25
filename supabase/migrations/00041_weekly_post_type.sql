-- 00041_weekly_post_type.sql
-- Allow 'weekly' as a post_type value for news_posts.

ALTER TABLE news_posts
  DROP CONSTRAINT IF EXISTS news_posts_post_type_check;

ALTER TABLE news_posts
  ADD CONSTRAINT news_posts_post_type_check
  CHECK (post_type IN ('research', 'business', 'weekly'));
