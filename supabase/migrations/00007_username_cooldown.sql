-- 00007_username_cooldown.sql
-- Track when a user last changed their username (User ID) for 30-day cooldown enforcement.

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS username_changed_at TIMESTAMPTZ;
