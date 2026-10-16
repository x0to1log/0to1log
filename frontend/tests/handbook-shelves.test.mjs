// frontend/tests/handbook-shelves.test.mjs
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { buildShelves, buildAzIndex, plainDefinition, firstNewsLine, termNames } = await import(
  pathToFileURL(path.join(here, '../src/lib/handbookShelves.js')).href
);

const CATS = ['products-platforms', 'llm-genai', 'deep-learning', 'math-statistics'];
const t = (term, categories, extra = {}) => ({
  term,
  slug: term.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
  categories,
  ...extra,
});

const itemsBySlug = (list) => Object.fromEntries(list.map((s) => [s.slug, s.items.map((i) => i.term)]));

// count = membership; placement = first canonical category (listed first); non-canonical-only terms skipped;
// empty fields hidden. Short shelves fill with their other members (here: duplicates, stage 3).
const terms = [
  t('RAG', ['llm-genai']),
  t('Agent', ['llm-genai', 'products-platforms']), // counted in both, placed in llm-genai
  t('Claude', ['products-platforms', 'llm-genai']), // placed in products-platforms
  t('CNN', ['legacy-slug', 'deep-learning']), // first canonical = deep-learning
  t('Orphan', ['legacy-slug']), // no canonical field: index only
];
let shelves = buildShelves(terms, CATS, []);
assert.deepEqual(shelves.map((s) => [s.slug, s.count, s.wide]), [
  ['products-platforms', 2, false],
  ['llm-genai', 3, true],
  ['deep-learning', 1, false],
]);
assert.deepEqual(itemsBySlug(shelves), {
  'products-platforms': ['Claude', 'Agent'],
  'llm-genai': ['Agent', 'RAG', 'Claude'],
  'deep-learning': ['CNN'],
});
assert(!shelves.some((s) => s.items.some((i) => i.term === 'Orphan')), 'orphan stays out of the shelves');

// fill stages: 1) first canonical, 2) unlisted members, 3) members listed elsewhere (duplicates)
const fillTerms = [
  t('P1', ['products-platforms']),
  t('L1', ['llm-genai', 'products-platforms']),
  t('L2', ['llm-genai', 'products-platforms']),
  ...['L3', 'L4', 'L5', 'L6', 'L7'].map((n) => t(n, ['llm-genai'])),
  t('X1', ['llm-genai', 'deep-learning']), // placed in llm-genai but not among its 6 listed
  t('X2', ['llm-genai', 'deep-learning']),
  t('D1', ['deep-learning']),
];
shelves = buildShelves(fillTerms, CATS, ['l2']);
assert.deepEqual(shelves.map((s) => [s.slug, s.count, s.wide]), [
  ['products-platforms', 3, false],
  ['llm-genai', 9, true],
  ['deep-learning', 3, false],
]);
assert.deepEqual(itemsBySlug(shelves), {
  'llm-genai': ['L2', 'L1', 'L3', 'L4', 'L5', 'L6'], // stage 1 only, trending first
  'products-platforms': ['P1', 'L2', 'L1'], // no unlisted members -> stage 3 duplicates, trending first
  'deep-learning': ['D1', 'X1', 'X2'], // stage 2: unlisted members; no more members, stays short of 4
});
assert(shelves.every((s) => s.items.length > 0), 'no shelf renders without terms');
assert(!shelves.find((s) => s.slug === 'llm-genai').items.some((i) => i.term === 'X1'), 'stage 2 picks only unlisted terms');

// stage 2 never hands the same unlisted term to two shelves; the later shelf falls back to stage 3
shelves = buildShelves([
  ...['A1', 'A2', 'A3', 'A4', 'A5', 'A6'].map((n) => t(n, ['llm-genai'])),
  t('Z1', ['llm-genai', 'products-platforms', 'deep-learning']),
  t('B1', ['products-platforms']),
  t('C1', ['deep-learning']),
], CATS, []);
assert.deepEqual(itemsBySlug(shelves), {
  'products-platforms': ['B1', 'Z1'],
  'llm-genai': ['A1', 'A2', 'A3', 'A4', 'A5', 'A6'],
  'deep-learning': ['C1', 'Z1'],
});

// wide tie -> earlier canonical field
shelves = buildShelves([t('A1', ['products-platforms']), t('B1', ['llm-genai'])], CATS, []);
assert.deepEqual(shelves.map((s) => [s.slug, s.wide]), [['products-platforms', true], ['llm-genai', false]]);

// 6 items on the wide shelf, 4 elsewhere; trending order first, then A-Z by term
const many = ['Zeta', 'Alpha', 'Mu', 'Beta', 'Kappa', 'Gamma', 'Delta', 'Eta'].map((n) => t(n, ['llm-genai']));
const few = ['Omega', 'Iota', 'Nu', 'Pi', 'Rho', 'Tau'].map((n) => t(n, ['deep-learning']));
shelves = buildShelves([...many, ...few], CATS, ['mu', 'tau', 'zeta']);
const wide = shelves.find((s) => s.slug === 'llm-genai');
const narrow = shelves.find((s) => s.slug === 'deep-learning');
assert.equal(wide.wide, true);
assert.equal(wide.count, 8);
assert.deepEqual(wide.items.map((i) => i.term), ['Mu', 'Zeta', 'Alpha', 'Beta', 'Delta', 'Eta']);
assert.equal(narrow.wide, false);
assert.deepEqual(narrow.items.map((i) => i.term), ['Tau', 'Iota', 'Nu', 'Omega']);

// plain definition
assert.equal(plainDefinition('  **RAG** is retrieval-augmented **generation**. '), 'RAG is retrieval-augmented generation.');
assert.equal(plainDefinition(null), '');

// A-Z: 27 letters, '#' last (digits/other), groups sorted by term
const az = buildAzIndex([t('rag', []), t('Agent', []), t('API', []), t('3D Gaussian', []), t('Claude', []), t('ablation', [])]);
assert.equal(az.letters.length, 27);
assert.deepEqual(az.letters[26], { letter: '#', anchor: 'num', has: true });
assert.deepEqual(az.letters.filter((l) => l.has).map((l) => l.letter), ['A', 'C', 'R', '#']);
assert.deepEqual(az.groups.map((g) => [g.letter, g.anchor]), [['A', 'A'], ['C', 'C'], ['R', 'R'], ['#', 'num']]);
assert.deepEqual(az.groups[0].items.map((i) => i.term), ['ablation', 'Agent', 'API']);
assert.deepEqual(az.groups[3].items.map((i) => i.term), ['3D Gaussian']);
assert.equal(az.letters[1].has, false); // B

// first news line
assert.equal(firstNewsLine('\n   \n- "RAG를 붙였다" → 검색 결과를 섞었다는 뜻\n- second'), '"RAG를 붙였다" → 검색 결과를 섞었다는 뜻');
assert.equal(firstNewsLine('• bullet line'), 'bullet line');
assert.equal(firstNewsLine('-\n• real line'), 'real line');
assert.equal(firstNewsLine('  plain line  '), 'plain line');
assert.equal(firstNewsLine('   \n\t'), '');
assert.equal(firstNewsLine(null), '');

// display names
assert.deepEqual(termNames({ term: 'RAG', korean_name: '검색 증강 생성' }, 'ko'), { name: '검색 증강 생성', sub: 'RAG' });
assert.deepEqual(termNames({ term: 'RAG', korean_name: '검색 증강 생성' }, 'en'), { name: 'RAG', sub: '' });
assert.deepEqual(termNames({ term: 'GPU', korean_name: 'GPU' }, 'ko'), { name: 'GPU', sub: '' });
assert.deepEqual(termNames({ term: 'GPU', korean_name: null }, 'ko'), { name: 'GPU', sub: '' });

console.log('handbook-shelves.test.mjs passed');
