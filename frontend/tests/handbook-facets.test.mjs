// frontend/tests/handbook-facets.test.mjs
// Term detail: facet labels, entry grammar line, editorial order, concept map geometry and label fitting.
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const load = (p) => import(pathToFileURL(path.join(here, p)).href);
const { termTypeLabel, intentLabel, volatilityLabel, entryGrammar, orderBySlugs } = await load('../src/lib/handbookFacets.js');
const { CONCEPT_MAP, conceptMapNodes, labelEm, fitLabel, nodeLabel, centerLabel } = await load('../src/lib/conceptMap.js');

// label maps: all 13 backend TERM_TYPES, KO/EN; unknown values -> ''
const TERM_TYPES = [
  'foundational_concept', 'problem_failure_mode', 'model_algorithm_family', 'training_optimization_method',
  'retrieval_knowledge_system', 'system_workflow_pattern', 'data_storage_indexing_system',
  'protocol_format_data_structure', 'capability_feature_spec', 'metric_benchmark',
  'product_platform_service', 'library_framework_sdk', 'hardware_runtime_infra',
];
for (const v of TERM_TYPES) {
  assert.ok(termTypeLabel('ko', v), `ko label for ${v}`);
  assert.ok(termTypeLabel('en', v), `en label for ${v}`);
}
assert.equal(termTypeLabel('ko', 'retrieval_knowledge_system'), '검색·지식 시스템');
assert.equal(termTypeLabel('en', 'problem_failure_mode'), 'Failure mode');
assert.equal(termTypeLabel('ko', 'concept'), '');
assert.equal(termTypeLabel('ko', null), '');
assert.equal(termTypeLabel('ko', 'toString'), '', 'prototype keys are not labels');

for (const v of ['understand', 'compare', 'build', 'debug', 'evaluate', 'operate', 'apply', 'defend']) {
  assert.ok(intentLabel('ko', v) && intentLabel('en', v), `intent label ${v}`);
}
assert.equal(intentLabel('ko', 'understand'), '이해할 때');
assert.equal(intentLabel('en', 'build'), 'When building');
assert.equal(intentLabel('en', 'explore'), '');

assert.equal(volatilityLabel('ko', 'stable'), '안정된 개념');
assert.equal(volatilityLabel('ko', 'fast-changing'), '빠르게 바뀌는 개념');
assert.equal(volatilityLabel('en', 'evolving'), 'Evolving');
assert.equal(volatilityLabel('en', 'volatile'), '');

// entryGrammar: type · intents(·) · volatility; nothing without a known type
assert.equal(
  entryGrammar('ko', { term_type: 'retrieval_knowledge_system', facet_intent: ['build', 'understand'], facet_volatility: 'evolving' }),
  '검색·지식 시스템 · 만들 때·이해할 때 · 변화 중인 개념',
);
assert.equal(
  entryGrammar('en', { term_type: 'metric_benchmark', facet_intent: ['evaluate'], facet_volatility: 'stable' }),
  'Metric / benchmark · When evaluating · Stable',
);
assert.equal(entryGrammar('ko', { term_type: null, facet_intent: null, facet_volatility: 'stable' }), '', 'unclassified: no lone "안정된 개념"');
assert.equal(entryGrammar('ko', { term_type: 'mystery', facet_volatility: 'stable' }), '');
assert.equal(entryGrammar('ko', { term_type: 'metric_benchmark', facet_intent: [], facet_volatility: null }), '지표·벤치마크');
assert.equal(entryGrammar('en', { term_type: 'metric_benchmark', facet_intent: ['explore', 'compare', 'compare'] }), 'Metric / benchmark · When comparing');
assert.equal(entryGrammar('ko', {}), '');

// orderBySlugs: editorial order, missing slugs skipped, unlisted rows dropped
const rows = [{ slug: 'bm25' }, { slug: 're-ranking' }, { slug: 'hybrid-search' }, { slug: 'stray' }];
assert.deepEqual(
  orderBySlugs(rows, ['hybrid-search', 'dpo', 'bm25', 're-ranking', 'bm25']).map((r) => r.slug),
  ['hybrid-search', 'bm25', 're-ranking'],
);
assert.deepEqual(orderBySlugs(null, ['a']), []);
assert.deepEqual(orderBySlugs(rows, null), []);

// conceptMapNodes: 12 o'clock first, clockwise, anchors by half, 0..6 nodes
const geo = { cx: 280, cy: 160, rx: 125, ry: 108 };
assert.deepEqual(conceptMapNodes(0, geo), []);
assert.deepEqual(conceptMapNodes(1, geo), [{ x: 280, y: 52, anchor: 'middle' }]);
assert.deepEqual(conceptMapNodes(4, geo), [
  { x: 280, y: 52, anchor: 'middle' },
  { x: 405, y: 160, anchor: 'start' },
  { x: 280, y: 268, anchor: 'middle' },
  { x: 155, y: 160, anchor: 'end' },
]);
const six = conceptMapNodes(6, geo);
assert.equal(six.length, 6);
assert.deepEqual(six.map((n) => n.anchor), ['middle', 'start', 'start', 'middle', 'end', 'end']);
assert.deepEqual(six[1], { x: 388.3, y: 106, anchor: 'start' });
assert.deepEqual(six[4], { x: 171.7, y: 214, anchor: 'end' });
assert.equal(conceptMapNodes(9, geo).length, 6, 'at most 6 nodes');
assert.deepEqual(conceptMapNodes(5, geo).map((n) => n.anchor), ['middle', 'start', 'start', 'end', 'end']);

// labels never leave the viewBox
assert.equal(labelEm('RAG 검색'), 4.4);
assert.equal(fitLabel('하이브리드 검색', 8), '하이브리드 검색');
assert.equal(fitLabel('벡터 데이터베이스 인덱스', 7), '벡터 데이터…');
const right = nodeLabel('벡터 데이터베이스 인덱스', { x: 405, y: 160, anchor: 'start' });
assert.deepEqual(right, { x: 417, y: 166, text: '벡터 데이터베…' });
const left = nodeLabel('하이브리드 검색', { x: 155, y: 160, anchor: 'end' });
assert.deepEqual(left, { x: 143, y: 166, text: '하이브리드 검색' });
assert.deepEqual(nodeLabel('BM25', { x: 280, y: 52, anchor: 'middle' }), { x: 280, y: 38, text: 'BM25' });
assert.deepEqual(nodeLabel('BM25', { x: 280, y: 268, anchor: 'middle' }), { x: 280, y: 296, text: 'BM25' });
const { width, margin, fontSize } = CONCEPT_MAP;
for (const n of conceptMapNodes(6, CONCEPT_MAP)) {
  const label = nodeLabel('Retrieval-Augmented Generation Pipeline', n);
  const w = labelEm(label.text) * fontSize;
  const [x0, x1] = n.anchor === 'start' ? [label.x, label.x + w] : n.anchor === 'end' ? [label.x - w, label.x] : [label.x - w / 2, label.x + w / 2];
  assert.ok(x0 >= margin && x1 <= width - margin, `label inside the viewBox (${n.anchor} ${x0}..${x1})`);
}

// centre label: shrinks, then wraps at a space, then cuts
assert.deepEqual(centerLabel('RRF'), { fontSize: 20, lines: [{ text: 'RRF', y: 167 }] });
assert.deepEqual(centerLabel('상호 순위 융합'), { fontSize: 15, lines: [{ text: '상호 순위 융합', y: 165.3 }] });
assert.deepEqual(centerLabel('자기지도 사전학습 과제'), {
  fontSize: 15,
  lines: [{ text: '자기지도', y: 156.8 }, { text: '사전학습 과제', y: 173.8 }],
});
assert.deepEqual(centerLabel('Self-Supervised Pretext Tasks').lines.map((l) => l.text), ['Self-Supervised', 'Pretext Tasks']);
const long = centerLabel('Supercalifragilisticexpialidocious');
assert.equal(long.fontSize, CONCEPT_MAP.centerMinFont);
assert.ok(long.lines[0].text.endsWith('…') && labelEm(long.lines[0].text) * long.fontSize <= CONCEPT_MAP.centerRadius * 2 - 16);

console.log('handbook-facets.test.mjs passed');
