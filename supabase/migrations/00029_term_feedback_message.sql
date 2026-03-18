-- 00029_term_feedback_message.sql
-- Add optional message field to term_feedback for detailed user feedback
ALTER TABLE term_feedback ADD COLUMN IF NOT EXISTS message TEXT;
