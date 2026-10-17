// frontend/src/lib/handbookFacets.js
// Pure helpers for the term detail page: facet labels, the entry "grammar" line, editorial order. No I/O.

// backend/services/agents/prompts_handbook_types.py TERM_TYPES (all 13)
const TERM_TYPE_LABELS = {
  ko: {
    foundational_concept: '기초 개념',
    problem_failure_mode: '문제·실패 유형',
    model_algorithm_family: '모델·알고리즘',
    training_optimization_method: '학습·최적화 기법',
    retrieval_knowledge_system: '검색·지식 시스템',
    system_workflow_pattern: '시스템·워크플로 패턴',
    data_storage_indexing_system: '데이터 저장·색인',
    protocol_format_data_structure: '프로토콜·형식',
    capability_feature_spec: '기능·사양',
    metric_benchmark: '지표·벤치마크',
    product_platform_service: '제품·플랫폼',
    library_framework_sdk: '라이브러리·프레임워크',
    hardware_runtime_infra: '하드웨어·인프라',
  },
  en: {
    foundational_concept: 'Foundational concept',
    problem_failure_mode: 'Failure mode',
    model_algorithm_family: 'Model / algorithm',
    training_optimization_method: 'Training method',
    retrieval_knowledge_system: 'Retrieval system',
    system_workflow_pattern: 'Workflow pattern',
    data_storage_indexing_system: 'Data storage / indexing',
    protocol_format_data_structure: 'Protocol / format',
    capability_feature_spec: 'Capability / feature',
    metric_benchmark: 'Metric / benchmark',
    product_platform_service: 'Product / platform',
    library_framework_sdk: 'Library / framework',
    hardware_runtime_infra: 'Hardware / infra',
  },
};

// INTENT_VALUES (understand/compare/build/debug/evaluate) + operate/apply/defend found in the DB
const INTENT_LABELS = {
  ko: {
    understand: '이해할 때',
    compare: '비교할 때',
    build: '만들 때',
    debug: '고칠 때',
    evaluate: '평가할 때',
    operate: '운영할 때',
    apply: '적용할 때',
    defend: '방어할 때',
  },
  en: {
    understand: 'When learning',
    compare: 'When comparing',
    build: 'When building',
    debug: 'When debugging',
    evaluate: 'When evaluating',
    operate: 'When operating',
    apply: 'When applying',
    defend: 'When defending',
  },
};

const VOLATILITY_LABELS = {
  ko: { stable: '안정된 개념', evolving: '변화 중인 개념', 'fast-changing': '빠르게 바뀌는 개념' },
  en: { stable: 'Stable', evolving: 'Evolving', 'fast-changing': 'Fast-changing' },
};

function pick(tables, locale, value) {
  const table = tables[locale] ?? tables.en;
  return typeof value === 'string' && Object.prototype.hasOwnProperty.call(table, value) ? table[value] : '';
}

/** @param {'ko'|'en'} locale */
export function termTypeLabel(locale, value) {
  return pick(TERM_TYPE_LABELS, locale, value);
}

/** @param {'ko'|'en'} locale */
export function intentLabel(locale, value) {
  return pick(INTENT_LABELS, locale, value);
}

/** @param {'ko'|'en'} locale */
export function volatilityLabel(locale, value) {
  return pick(VOLATILITY_LABELS, locale, value);
}

/**
 * "유형 · 쓰임 · 변화 정도". Empty unless term_type has a label: migration 00047 defaults
 * facet_volatility to 'stable', so an unclassified term must not show "안정된 개념" alone.
 * Intents are joined with '·' (unknown values dropped, duplicates removed).
 */
export function entryGrammar(locale, { term_type, facet_intent, facet_volatility } = {}) {
  const type = termTypeLabel(locale, term_type);
  if (!type) return '';
  const intents = [...new Set((Array.isArray(facet_intent) ? facet_intent : []).map((v) => intentLabel(locale, v)).filter(Boolean))];
  return [type, intents.join('·'), volatilityLabel(locale, facet_volatility)].filter(Boolean).join(' · ');
}

/**
 * Rows in the editorial order of `slugs`. Slugs without a row (unpublished) are skipped,
 * rows whose slug is not listed are dropped, duplicates appear once.
 */
export function orderBySlugs(rows, slugs) {
  const bySlug = new Map((rows || []).map((row) => [row.slug, row]));
  const seen = new Set();
  const out = [];
  for (const slug of slugs || []) {
    if (seen.has(slug)) continue;
    seen.add(slug);
    const row = bySlug.get(slug);
    if (row) out.push(row);
  }
  return out;
}
