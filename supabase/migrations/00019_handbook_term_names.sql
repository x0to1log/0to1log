-- 00019_handbook_term_names.sql
-- Add term_full and korean_full columns for expanded term naming

ALTER TABLE handbook_terms
  ADD COLUMN IF NOT EXISTS term_full text,
  ADD COLUMN IF NOT EXISTS korean_full text;

COMMENT ON COLUMN handbook_terms.term_full IS 'English full name (e.g., Long Short-Term Memory for LSTM)';
COMMENT ON COLUMN handbook_terms.korean_full IS 'Korean formal name (e.g., 장단기 기억 네트워크 for LSTM)';
