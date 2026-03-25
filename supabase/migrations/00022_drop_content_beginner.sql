-- 00022_drop_content_beginner.sql
-- v4: Remove content_beginner column from news_posts.
-- Beginner persona merged into Learner. Existing beginner data is no longer used.
-- Run manually: DO NOT apply automatically.
ALTER TABLE news_posts DROP COLUMN IF EXISTS content_beginner;
