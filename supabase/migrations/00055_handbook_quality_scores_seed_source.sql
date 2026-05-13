-- 00055_handbook_quality_scores_seed_source.sql
-- Allow curated seed batch generations to record handbook quality scores
-- without collapsing them into the generic pipeline source.

ALTER TABLE handbook_quality_scores
  DROP CONSTRAINT IF EXISTS handbook_quality_scores_source_check;

ALTER TABLE handbook_quality_scores
  ADD CONSTRAINT handbook_quality_scores_source_check
  CHECK (source IN ('pipeline', 'manual', 'seed'));
