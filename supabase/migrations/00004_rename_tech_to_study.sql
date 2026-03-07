-- 00004_rename_tech_to_study.sql
-- Rename legacy category slug "tech" to "study" for existing environments.

BEGIN;

UPDATE posts
SET category = 'study'
WHERE category = 'tech';

ALTER TABLE posts
    DROP CONSTRAINT IF EXISTS posts_category_check;

ALTER TABLE posts
    DROP CONSTRAINT IF EXISTS chk_post_type_by_category;

ALTER TABLE posts
    ADD CONSTRAINT posts_category_check
    CHECK (category IN ('ai-news', 'study', 'career', 'project'));

ALTER TABLE posts
    ADD CONSTRAINT chk_post_type_by_category
    CHECK (
        (category = 'ai-news' AND post_type IN ('research', 'business'))
        OR
        (category IN ('study', 'career', 'project') AND post_type IS NULL)
    );

COMMIT;
