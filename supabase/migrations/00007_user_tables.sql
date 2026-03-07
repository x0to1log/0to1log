-- 00007_user_tables.sql
-- Phase 3-USER: profiles, user_bookmarks, reading_history, learning_progress
-- Design doc: docs/plans/2026-03-08-user-features-design.md

-- 1. profiles
CREATE TABLE profiles (
  id           UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name TEXT,
  avatar_url   TEXT,
  persona      TEXT CHECK (persona IN ('beginner', 'learner', 'expert')),
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  updated_at   TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users read own profile"
  ON profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users update own profile"
  ON profiles FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Users insert own profile"
  ON profiles FOR INSERT WITH CHECK (auth.uid() = id);

-- 2. user_bookmarks (polymorphic: post + term)
CREATE TABLE user_bookmarks (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  item_type  TEXT NOT NULL CHECK (item_type IN ('post', 'term')),
  item_id    UUID NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, item_type, item_id)
);

CREATE INDEX idx_user_bookmarks_user ON user_bookmarks(user_id);
CREATE INDEX idx_user_bookmarks_item ON user_bookmarks(item_type, item_id);

ALTER TABLE user_bookmarks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users read own bookmarks"
  ON user_bookmarks FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users insert own bookmarks"
  ON user_bookmarks FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users delete own bookmarks"
  ON user_bookmarks FOR DELETE USING (auth.uid() = user_id);

-- 3. reading_history (polymorphic: post + term)
CREATE TABLE reading_history (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  item_type  TEXT NOT NULL CHECK (item_type IN ('post', 'term')),
  item_id    UUID NOT NULL,
  read_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, item_type, item_id)
);

CREATE INDEX idx_reading_history_user ON reading_history(user_id);
CREATE INDEX idx_reading_history_item ON reading_history(item_type, item_id);

ALTER TABLE reading_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users read own history"
  ON reading_history FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users insert own history"
  ON reading_history FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users delete own history"
  ON reading_history FOR DELETE USING (auth.uid() = user_id);

-- 4. learning_progress (Handbook 학습 진도)
-- NOTE: handbook_terms FK will be added after Handbook H1 merge.
-- For now, term_id is UUID without FK constraint (same pattern as user_bookmarks.item_id).
CREATE TABLE learning_progress (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  term_id    UUID NOT NULL,
  status     TEXT NOT NULL DEFAULT 'read'
             CHECK (status IN ('read', 'learned')),
  read_at    TIMESTAMPTZ DEFAULT NOW(),
  learned_at TIMESTAMPTZ,
  UNIQUE(user_id, term_id)
);

CREATE INDEX idx_learning_progress_user ON learning_progress(user_id);

ALTER TABLE learning_progress ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users read own progress"
  ON learning_progress FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users insert own progress"
  ON learning_progress FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users update own progress"
  ON learning_progress FOR UPDATE USING (auth.uid() = user_id);
