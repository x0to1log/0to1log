-- Pipeline checkpoint storage for rerun support
-- Each pipeline stage saves its output, enabling restart from any point

CREATE TABLE IF NOT EXISTS pipeline_checkpoints (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
  stage TEXT NOT NULL,
  data JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(run_id, stage)
);

-- RLS: backend service_role only
ALTER TABLE pipeline_checkpoints ENABLE ROW LEVEL SECURITY;

-- Index on run_id for fast lookup
CREATE INDEX IF NOT EXISTS idx_pipeline_checkpoints_run_id ON pipeline_checkpoints(run_id);
