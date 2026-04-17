ALTER TABLE news_posts ADD COLUMN IF NOT EXISTS title_learner TEXT;
UPDATE news_posts
SET title_learner = guide_items->>'title_learner'
WHERE guide_items->>'title_learner' IS NOT NULL AND title_learner IS NULL;
