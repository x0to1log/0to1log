// Run-level pipeline health for the admin dashboard.
//
// The per-run health checks (debug_meta.warnings) cannot see a run that never
// happened. Both real outages in Sep-Oct 2026 were of that kind: OpenAI credits
// ran out (3 failed days) and Supabase was paused (13 days with no run rows).
// This module compares the runs that exist against the cron schedule.
// See vault plan 2026-10-13-news-pipeline-gpt6-upgrade, Task 0.2.

const DAY_MS = 86_400_000;
// Daily cron fires 22:12 UTC (07:12 KST) for the next KST date; allow 30 minutes.
const DAILY_DUE_OFFSET_MS = (22 * 60 + 42) * 60_000;
// Weekly cron fires Monday 01:00 UTC (10:00 KST) for the previous ISO week.
const WEEKLY_DUE_OFFSET_MS = 90 * 60_000;

const isoDate = (date) => date.toISOString().slice(0, 10);

/** Latest daily batch id (`YYYY-MM-DD`, KST) whose cron should have run by `now`. */
export function expectedDailyBatchId(now) {
  const cronDay = new Date(now.getTime() - DAILY_DUE_OFFSET_MS);
  return isoDate(new Date(cronDay.getTime() + DAY_MS));
}

function isoWeekKey(date) {
  const d = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  const day = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - day); // Thursday decides the ISO year
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const week = Math.ceil(((d - yearStart) / DAY_MS + 1) / 7);
  return `${d.getUTCFullYear()}-W${String(week).padStart(2, '0')}`;
}

/** Latest weekly run key (`weekly-YYYY-Www`) whose Monday cron should have run by `now`. */
export function expectedWeeklyRunKey(now) {
  const shifted = new Date(now.getTime() - WEEKLY_DUE_OFFSET_MS);
  const sinceMonday = (shifted.getUTCDay() + 6) % 7;
  const monday = new Date(shifted.getTime() - sinceMonday * DAY_MS);
  return `weekly-${isoWeekKey(new Date(monday.getTime() - 7 * DAY_MS))}`;
}

/** Map a run's last_error to a cause the admin can act on. */
export function classifyPipelineFailure(lastError) {
  const text = String(lastError || '').toLowerCase();
  if (/no credits remaining|insufficient_quota|exceeded your current quota/.test(text)) return 'openai_credits';
  if (/flex_unavailable|resource_unavailable/.test(text)) return 'openai_capacity';
  if (/supabase|postgres|connection refused|could not connect|connecterror|name or service not known/.test(text)) {
    return 'database';
  }
  return 'other';
}

const CAUSE_LABELS = {
  openai_credits: 'OpenAI credits exhausted — add credits',
  openai_capacity: 'OpenAI Flex capacity unavailable',
  database: 'Database connection failed',
  other: 'See the run error',
};

const QUIZ_PERSONAS = ['expert', 'learner', 'beginner'];

/**
 * Published daily posts whose persona quizzes are missing. A quiz that fails
 * answer verification three times is dropped and the post still publishes
 * (10-18 business KO expert), so the run log alone is easy to miss.
 * Each post carries `quiz_<persona>`: the quiz question text, or null.
 *
 * @param {Array<{pipeline_batch_id: string, post_type: string, locale: string} & Record<string, unknown>>} posts
 */
export function findMissingDailyQuizzes(posts) {
  const gaps = [];
  for (const post of posts) {
    const personas = QUIZ_PERSONAS.filter((p) => !String(post[`quiz_${p}`] ?? '').trim());
    if (personas.length) {
      gaps.push({ batch: post.pipeline_batch_id, postType: post.post_type, locale: post.locale, personas });
    }
  }
  return gaps.sort((a, b) => (a.batch < b.batch ? 1 : a.batch > b.batch ? -1 : 0));
}

/**
 * @param {Array<{run_key: string, status: string, started_at: string, last_error?: string|null}>} runs
 * @param {Date} now
 */
export function summarizePipelineHealth(runs, now, { windowDays = 14, quizPosts = [] } = {}) {
  const issues = [];
  const latestDailyByBatch = new Map();
  for (const run of runs) {
    if (!run.run_key?.startsWith('news-')) continue;
    const batch = run.run_key.slice('news-'.length);
    const prev = latestDailyByBatch.get(batch);
    if (!prev || prev.started_at < run.started_at) latestDailyByBatch.set(batch, run);
  }

  const expectedBatch = expectedDailyBatchId(now);
  const windowDates = [];
  const expectedTime = new Date(`${expectedBatch}T00:00:00Z`).getTime();
  for (let i = windowDays - 1; i >= 0; i -= 1) windowDates.push(isoDate(new Date(expectedTime - i * DAY_MS)));

  if (!latestDailyByBatch.has(expectedBatch)) {
    issues.push({
      level: 'critical',
      code: 'latest_daily_missing',
      message: `No daily run for ${expectedBatch} (cron 07:12 KST). Check Supabase and the Vercel cron.`,
    });
  }

  const dailyNewestFirst = [...latestDailyByBatch.entries()].sort((a, b) => (a[0] < b[0] ? 1 : -1));
  let consecutive = 0;
  for (const [, run] of dailyNewestFirst) {
    if (run.status !== 'failed') break;
    consecutive += 1;
  }
  if (consecutive > 0) {
    const cause = classifyPipelineFailure(dailyNewestFirst[0][1].last_error);
    issues.push({
      level: 'critical',
      code: 'daily_failing',
      cause,
      consecutive,
      message: `Last ${consecutive} daily run(s) failed: ${CAUSE_LABELS[cause]}.`,
    });
  }

  const missingDates = windowDates.filter((d) => d !== expectedBatch && !latestDailyByBatch.has(d));
  if (missingDates.length) {
    issues.push({
      level: 'warning',
      code: 'daily_gaps',
      message: `${missingDates.length} day(s) without a daily run in the last ${windowDays} days.`,
    });
  }

  const expectedWeekly = expectedWeeklyRunKey(now);
  if (!runs.some((run) => run.run_key === expectedWeekly)) {
    issues.push({ level: 'warning', code: 'weekly_missing', message: `No ${expectedWeekly} run (cron Monday 10:00 KST).` });
  }

  const quizGaps = findMissingDailyQuizzes(quizPosts);
  if (quizGaps.length) {
    const list = quizGaps
      .map((g) => `${g.batch} ${g.postType} ${String(g.locale).toUpperCase()} (${g.personas.join(', ')})`)
      .join('; ');
    issues.push({ level: 'warning', code: 'daily_quiz_missing', message: `Quiz missing on published posts: ${list}.` });
  }

  const level = issues.some((i) => i.level === 'critical') ? 'critical' : issues.length ? 'warning' : 'ok';
  return { level, issues, missingDates, quizGaps, expectedBatch, expectedWeekly };
}
