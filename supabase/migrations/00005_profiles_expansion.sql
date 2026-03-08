-- 00005_profiles_expansion.sql
-- Add new columns to existing profiles table (username, bio, preferred_locale, is_public, onboarding_completed)
-- Ref: docs/plans/2026-03-09-profiles-redesign.md

-- New columns
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS username TEXT UNIQUE;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS bio TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS preferred_locale TEXT DEFAULT 'ko' CHECK (preferred_locale IN ('en', 'ko'));
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT FALSE;

-- Username format constraint: 3-20 chars, lowercase + digits + hyphens
ALTER TABLE profiles ADD CONSTRAINT chk_username_format
  CHECK (username ~ '^[a-z0-9][a-z0-9-]{1,18}[a-z0-9]$');

CREATE INDEX IF NOT EXISTS idx_profiles_username ON profiles(username);

-- RLS policies (if not already present)
-- Allow reading own profile or public profiles
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'profiles' AND policyname = 'Users read own or public profile'
  ) THEN
    CREATE POLICY "Users read own or public profile"
      ON profiles FOR SELECT USING (auth.uid() = id OR is_public = true);
  END IF;
END
$$;
