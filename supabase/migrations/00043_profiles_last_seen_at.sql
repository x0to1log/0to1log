-- 00043_profiles_last_seen_at.sql
-- Add last_seen_at for DAU/MAU tracking.
-- Updated by middleware once per day per user.

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;

-- Partial index for efficient DAU/MAU queries
CREATE INDEX IF NOT EXISTS idx_profiles_last_seen_at ON profiles(last_seen_at)
  WHERE last_seen_at IS NOT NULL;

-- Backfill: set existing users' last_seen_at to their updated_at
UPDATE profiles SET last_seen_at = updated_at WHERE last_seen_at IS NULL;
