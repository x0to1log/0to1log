-- 00030_quiz_responses.sql
-- Track user quiz responses for future points/streak system.
-- One response per user per post per persona.

CREATE TABLE quiz_responses (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID        NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  post_id     UUID        NOT NULL REFERENCES news_posts(id) ON DELETE CASCADE,
  persona     TEXT        NOT NULL CHECK (persona IN ('expert', 'learner')),
  selected    TEXT        NOT NULL,
  is_correct  BOOLEAN     NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, post_id, persona)
);

CREATE INDEX idx_quiz_responses_user ON quiz_responses(user_id);
CREATE INDEX idx_quiz_responses_post ON quiz_responses(post_id);

ALTER TABLE quiz_responses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "quiz_responses_own" ON quiz_responses
FOR ALL USING (auth.uid() = user_id);
