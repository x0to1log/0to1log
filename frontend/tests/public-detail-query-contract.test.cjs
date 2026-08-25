const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const contracts = [
  ['src/lib/pageData/newsDetailPage.ts', 'NEWS_DETAIL_PUBLIC_COLUMNS'],
  ['src/lib/pageData/handbookDetailPage.ts', 'HANDBOOK_DETAIL_PUBLIC_COLUMNS'],
  ['src/lib/pageData/blogDetailPage.ts', 'BLOG_DETAIL_PUBLIC_COLUMNS'],
  ['src/lib/pageData/productsPage.ts', 'PRODUCT_DETAIL_PUBLIC_COLUMNS'],
];

for (const [relativePath, constant] of contracts) {
  const source = fs.readFileSync(path.join(root, relativePath), 'utf8');
  const detailSource = relativePath.endsWith('productsPage.ts')
    ? source.slice(source.indexOf('export async function getProductDetailData'), source.indexOf('export async function fetchAlternatives'))
    : source;
  assert.doesNotMatch(detailSource, /\.select\(\s*['"]\*['"]\s*\)/, `${relativePath} must not fetch wildcard detail rows`);
  assert.match(source, new RegExp(`(?:export )?const ${constant}`), `${relativePath} must define ${constant}`);
  assert.match(source, new RegExp(`\\.select\\(${constant}\\)`), `${relativePath} must use ${constant}`);
}

const news = fs.readFileSync(path.join(root, contracts[0][0]), 'utf8');
for (const field of ['content_analysis', 'content_beginner', 'content_learner', 'content_expert', 'fact_pack', 'source_cards']) {
  assert.match(news, new RegExp(`\\b${field}\\b`), `news detail contract must retain ${field}`);
}

const handbook = fs.readFileSync(path.join(root, contracts[1][0]), 'utf8');
for (const field of ['body_basic_ko', 'body_basic_en', 'body_advanced_ko', 'body_advanced_en', 'references_ko', 'references_en']) {
  assert.match(handbook, new RegExp(`\\b${field}\\b`), `handbook detail contract must retain ${field}`);
}

console.log('public-detail-query-contract.test.cjs passed');
