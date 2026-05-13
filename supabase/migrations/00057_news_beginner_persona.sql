-- Reintroduce beginner persona storage for daily news.
-- content_beginner existed in the initial schema but was removed in 00022
-- when the product only shipped expert/learner views.

ALTER TABLE news_posts
  ADD COLUMN IF NOT EXISTS content_beginner TEXT,
  ADD COLUMN IF NOT EXISTS title_beginner TEXT;

UPDATE news_posts
SET title_beginner = guide_items->>'title_beginner'
WHERE guide_items->>'title_beginner' IS NOT NULL
  AND title_beginner IS NULL;

ALTER TABLE quiz_responses
  DROP CONSTRAINT IF EXISTS quiz_responses_persona_check;

ALTER TABLE quiz_responses
  ADD CONSTRAINT quiz_responses_persona_check
  CHECK (persona IN ('expert', 'learner', 'beginner'));
