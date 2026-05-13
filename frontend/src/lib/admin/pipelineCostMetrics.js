const MODEL_PRICING_PER_1M = {
  'gpt-5': { input: 2.0, output: 8.0 },
  'gpt-5-mini': { input: 0.25, output: 2.0 },
  'gpt-5-nano': { input: 0.05, output: 0.4 },
};

export function parseCost(value) {
  if (value === null || value === undefined || value === '') return 0;
  const parsed = Number.parseFloat(String(value));
  return Number.isFinite(parsed) ? parsed : 0;
}

function numeric(value) {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

function resolvePricing(modelName) {
  if (!modelName) return null;
  if (MODEL_PRICING_PER_1M[modelName]) return MODEL_PRICING_PER_1M[modelName];
  const key = Object.keys(MODEL_PRICING_PER_1M)
    .sort((a, b) => b.length - a.length)
    .find((candidate) => modelName.startsWith(candidate));
  return key ? MODEL_PRICING_PER_1M[key] : null;
}

function debugMeta(log) {
  return log?.debug_meta && typeof log.debug_meta === 'object' ? log.debug_meta : {};
}

function serviceTierMultiplier(serviceTier) {
  return serviceTier === 'flex' ? 0.5 : 1;
}

export function summarizeCostMetrics(logs) {
  const summary = {
    inputTokens: 0,
    outputTokens: 0,
    cachedTokens: 0,
    totalTokens: 0,
    loggedCost: 0,
    standardCost: 0,
    cacheSavings: 0,
    tierSavings: 0,
    estimatedSavings: 0,
    cacheHitRate: 0,
    flexCallCount: 0,
    pricedCallCount: 0,
    unpricedCallCount: 0,
  };

  for (const log of logs ?? []) {
    const meta = debugMeta(log);
    const inputTokens = numeric(meta.input_tokens);
    const outputTokens = numeric(meta.output_tokens);
    const cachedTokens = Math.min(numeric(meta.cached_tokens), inputTokens);
    const loggedCost = parseCost(log?.cost_usd);
    const pricing = resolvePricing(log?.model_used);

    summary.inputTokens += inputTokens;
    summary.outputTokens += outputTokens;
    summary.cachedTokens += cachedTokens;
    summary.totalTokens += numeric(log?.tokens_used);
    summary.loggedCost += loggedCost;
    if (meta.service_tier === 'flex') summary.flexCallCount += 1;

    if (!pricing || (inputTokens === 0 && outputTokens === 0)) {
      if (inputTokens > 0 || outputTokens > 0 || loggedCost > 0) {
        summary.unpricedCallCount += 1;
      }
      continue;
    }

    summary.pricedCallCount += 1;
    const noCacheStandardCost = (
      inputTokens * pricing.input
      + outputTokens * pricing.output
    ) / 1_000_000;
    const tierMultiplier = serviceTierMultiplier(meta.service_tier);
    const noCacheSameTierCost = noCacheStandardCost * tierMultiplier;
    const cacheSavings = (
      cachedTokens
      * pricing.input
      * 0.9
      * tierMultiplier
    ) / 1_000_000;

    summary.standardCost += noCacheStandardCost;
    summary.tierSavings += Math.max(0, noCacheStandardCost - noCacheSameTierCost);
    summary.cacheSavings += cacheSavings;
  }

  summary.cacheHitRate = summary.inputTokens > 0
    ? summary.cachedTokens / summary.inputTokens
    : 0;
  summary.estimatedSavings = Math.max(0, summary.tierSavings + summary.cacheSavings);

  return {
    ...summary,
    loggedCost: Number(summary.loggedCost.toFixed(6)),
    standardCost: Number(summary.standardCost.toFixed(6)),
    cacheSavings: Number(summary.cacheSavings.toFixed(6)),
    tierSavings: Number(summary.tierSavings.toFixed(6)),
    estimatedSavings: Number(summary.estimatedSavings.toFixed(6)),
  };
}
