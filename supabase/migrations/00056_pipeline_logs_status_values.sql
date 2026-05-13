-- Allow non-terminal pipeline log events that are already emitted by backend code.
-- Some handbook gates log skipped/queued decisions for admin observability.

ALTER TABLE pipeline_logs
  DROP CONSTRAINT IF EXISTS pipeline_logs_status_check;

ALTER TABLE pipeline_logs
  ADD CONSTRAINT pipeline_logs_status_check
  CHECK (status IN (
    'started',
    'success',
    'failed',
    'retried',
    'no_news',
    'skipped',
    'queued'
  ));
