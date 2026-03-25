-- 00028_handbook_queued_status.sql
-- Add 'queued' status to handbook_terms for low-confidence pipeline extractions.
-- Queued terms have title/slug only — no LLM-generated content until admin approves.

ALTER TABLE handbook_terms
  DROP CONSTRAINT IF EXISTS handbook_terms_status_check;

ALTER TABLE handbook_terms
  ADD CONSTRAINT handbook_terms_status_check
  CHECK (status IN ('draft', 'published', 'archived', 'queued'));
