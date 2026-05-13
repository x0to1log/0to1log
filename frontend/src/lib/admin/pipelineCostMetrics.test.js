import assert from 'node:assert/strict';
import test from 'node:test';

import { summarizeCostMetrics } from './pipelineCostMetrics.js';

test('summarizeCostMetrics separates cached input, flex tier, and savings', () => {
  const summary = summarizeCostMetrics([
    {
      model_used: 'gpt-5-mini',
      cost_usd: 0.52375,
      tokens_used: 1_500_000,
      debug_meta: {
        input_tokens: 1_000_000,
        cached_tokens: 900_000,
        output_tokens: 500_000,
        service_tier: 'flex',
      },
    },
  ]);

  assert.equal(summary.inputTokens, 1_000_000);
  assert.equal(summary.cachedTokens, 900_000);
  assert.equal(summary.outputTokens, 500_000);
  assert.equal(summary.cacheHitRate, 0.9);
  assert.equal(summary.flexCallCount, 1);
  assert.equal(summary.loggedCost, 0.52375);
  assert.equal(summary.standardCost, 1.25);
  assert.equal(summary.cacheSavings, 0.10125);
  assert.equal(summary.tierSavings, 0.625);
  assert.equal(summary.estimatedSavings, 0.72625);
  assert.equal(summary.pricedCallCount, 1);
});

test('summarizeCostMetrics tolerates logs without model pricing', () => {
  const summary = summarizeCostMetrics([
    {
      model_used: 'unknown-model',
      cost_usd: 0.25,
      tokens_used: 1000,
      debug_meta: { input_tokens: 800, output_tokens: 200 },
    },
  ]);

  assert.equal(summary.loggedCost, 0.25);
  assert.equal(summary.standardCost, 0);
  assert.equal(summary.estimatedSavings, 0);
  assert.equal(summary.pricedCallCount, 0);
  assert.equal(summary.unpricedCallCount, 1);
});
