// frontend/tests/handbook-term-entry.test.cjs
// Term detail A+B: crumb shell, entry head, two-column hero, see-also, inline actions, concept map, news mentions.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

// data
const data = read('lib/pageData/handbookDetailPage.ts');
const columns = data.slice(data.indexOf('HANDBOOK_DETAIL_PUBLIC_COLUMNS = ['), data.indexOf("].join(', ')"));
for (const c of ['term_type', 'facet_intent', 'facet_volatility']) {
  assert(columns.includes(`'${c}'`), `detail columns include ${c}`);
}
assert.strictEqual((data.match(/\.from\('news_posts'\)/g) || []).length, 1, 'one news query: real mentions only (latest-news fallback removed)');
assert(!/recentNewsRes|backfill/.test(data), 'fallback query and assignment removed');
assert(/\.or\(`tags\.cs\.\{\$\{term\.term\.toLowerCase\(\)\}\},title\.ilike\.%\$\{term\.term\}%`\)[\s\S]{0,120}\.limit\(5\)/.test(data), 'mentions query unchanged (max 5)');
assert(data.includes('relatedArticles = articlesRes.data ?? [];'), 'no mentions -> empty list');
assert(data.includes("import { orderBySlugs } from '../handbookFacets.js';"), 'imports orderBySlugs');
assert(data.includes('relatedTerms = orderBySlugs(relatedRes.data ?? [], term.related_term_slugs ?? []);'), 'related terms follow related_term_slugs order');

console.log('handbook-term-entry.test.cjs passed');
