-- 00042_avatars_storage_bucket.sql
-- Create avatars storage bucket + RLS policies for user avatar uploads.

-- Create public bucket (avatars need public URLs for display)
INSERT INTO storage.buckets (id, name, public)
VALUES ('avatars', 'avatars', true)
ON CONFLICT (id) DO NOTHING;

-- Policy: authenticated users can upload their own avatar (filename = user_id.ext)
CREATE POLICY "Users can upload own avatar"
  ON storage.objects FOR INSERT
  TO authenticated
  WITH CHECK (
    bucket_id = 'avatars'
    AND (storage.foldername(name))[1] IS NULL  -- root level only, no subfolders
    AND starts_with(name, auth.uid()::text)
  );

-- Policy: authenticated users can update (upsert) their own avatar
CREATE POLICY "Users can update own avatar"
  ON storage.objects FOR UPDATE
  TO authenticated
  USING (
    bucket_id = 'avatars'
    AND starts_with(name, auth.uid()::text)
  );

-- Policy: authenticated users can delete their own avatar
CREATE POLICY "Users can delete own avatar"
  ON storage.objects FOR DELETE
  TO authenticated
  USING (
    bucket_id = 'avatars'
    AND starts_with(name, auth.uid()::text)
  );

-- Policy: anyone can read avatars (public bucket)
CREATE POLICY "Public avatar read"
  ON storage.objects FOR SELECT
  TO public
  USING (bucket_id = 'avatars');
