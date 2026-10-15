import assert from 'node:assert/strict';
import test from 'node:test';

import {
  classifyPipelineFailure,
  expectedDailyBatchId,
  expectedWeeklyRunKey,
  summarizePipelineHealth,
} from './pipelineHealth.js';

const at = (iso) => new Date(iso);

function dailyRun(batchId, status = 'success', lastError = null) {
  return {
    run_key: `news-${batchId}`,
    status,
    started_at: `${batchId}T00:00:00+00:00`,
    last_error: lastError,
  };
}

function healthyRuns(endBatch, days) {
  const runs = [];
  const end = new Date(`${endBatch}T00:00:00Z`);
  for (let i = 0; i < days; i += 1) {
    const d = new Date(end.getTime() - i * 86_400_000).toISOString().slice(0, 10);
    runs.push(dailyRun(d));
  }
  return runs;
}

test('daily batch id is the KST date of the 22:12 UTC cron, after a 30 minute grace', () => {
  // 2026-10-14 22:12 UTC = 2026-10-15 07:12 KST
  assert.equal(expectedDailyBatchId(at('2026-10-14T22:50:00Z')), '2026-10-15');
  // Within the grace window the previous batch is still the latest expected one.
  assert.equal(expectedDailyBatchId(at('2026-10-14T22:30:00Z')), '2026-10-14');
});

test('weekly run key is the previous ISO week once Monday 10:00 KST has passed', () => {
  // Monday 2026-09-21 01:00 UTC ran weekly-2026-W38 (Sep 14-20).
  assert.equal(expectedWeeklyRunKey(at('2026-09-21T02:00:00Z')), 'weekly-2026-W38');
  // Before that Monday's grace, the latest expected weekly is still W37.
  assert.equal(expectedWeeklyRunKey(at('2026-09-21T01:10:00Z')), 'weekly-2026-W37');
});

test('classifies the failures that caused real outages', () => {
  assert.equal(
    classifyPipelineFailure("Error code: 429 - {'error': {'message': 'You have no credits remaining. Add credits'}}"),
    'openai_credits',
  );
  assert.equal(classifyPipelineFailure("Error code: 429 - {'code': 'flex_unavailable'}"), 'openai_capacity');
  assert.equal(classifyPipelineFailure('could not connect to server: Connection refused'), 'database');
  assert.equal(classifyPipelineFailure('Content too short'), 'other');
});

test('healthy history reports ok', () => {
  const now = at('2026-10-14T23:00:00Z');
  const runs = [...healthyRuns('2026-10-15', 14), { run_key: 'weekly-2026-W41', status: 'success', started_at: '2026-10-13T01:10:00Z' }];
  const health = summarizePipelineHealth(runs, now);
  assert.equal(health.level, 'ok');
  assert.deepEqual(health.issues, []);
});

test("missing today's run is critical even with no failure rows (silent outage)", () => {
  const now = at('2026-10-14T23:00:00Z');
  const runs = healthyRuns('2026-10-14', 14); // nothing for 2026-10-15
  const health = summarizePipelineHealth(runs, now);
  assert.equal(health.level, 'critical');
  assert.ok(health.issues.some((i) => i.code === 'latest_daily_missing' && i.message.includes('2026-10-15')));
});

test('older gaps in the window are a warning that lists the dates', () => {
  const now = at('2026-10-14T23:00:00Z');
  const runs = healthyRuns('2026-10-15', 14).filter((r) => !['news-2026-10-08', 'news-2026-10-09'].includes(r.run_key));
  const health = summarizePipelineHealth(runs, now);
  assert.equal(health.level, 'warning');
  assert.deepEqual(health.missingDates, ['2026-10-08', '2026-10-09']);
});

test('latest failed daily run is critical and names the cause', () => {
  const now = at('2026-09-18T01:00:00Z');
  const runs = [
    ...healthyRuns('2026-09-15', 10),
    dailyRun('2026-09-16', 'failed', 'You have no credits remaining.'),
    dailyRun('2026-09-17', 'failed', 'You have no credits remaining.'),
    dailyRun('2026-09-18', 'failed', 'You have no credits remaining.'),
  ];
  const health = summarizePipelineHealth(runs, now);
  assert.equal(health.level, 'critical');
  const failure = health.issues.find((i) => i.code === 'daily_failing');
  assert.ok(failure);
  assert.equal(failure.cause, 'openai_credits');
  assert.equal(failure.consecutive, 3);
});
