const PIPELINE_LOG_PAGE_SIZE = 1000;

export async function fetchPipelineLogsForRuns(
  sb,
  runIds,
  { pageSize = PIPELINE_LOG_PAGE_SIZE } = {},
) {
  if (!Array.isArray(runIds) || runIds.length === 0) {
    return [];
  }

  const logs = [];
  let from = 0;

  while (true) {
    const to = from + pageSize - 1;
    const { data, error } = await sb
      .from('pipeline_logs')
      .select('run_id, pipeline_type, cost_usd, tokens_used, debug_meta')
      .in('run_id', runIds)
      .order('created_at', { ascending: true })
      .range(from, to);

    if (error) {
      throw error;
    }

    const page = data ?? [];
    logs.push(...page);

    if (page.length < pageSize) {
      break;
    }

    from += pageSize;
  }

  return logs;
}
