const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');

for (const locale of ['ko', 'en']) {
  const news = read(`src/pages/${locale}/news/index.astro`);
  assert.match(news, /const POSTS_FIELDS = ['"][^'"]+['"]/, `${locale} news fields must stay explicit`);
  assert.doesNotMatch(news.match(/const POSTS_FIELDS = ['"][^'"]+['"]/)[0], /guide_items/, `${locale} news list must not transfer guide JSON`);
  assert.match(news, /eq\('status', 'published'\)/, `${locale} news must keep published filter`);
  assert.match(news, new RegExp(`eq\\('locale', '${locale}'\\)`), `${locale} news must keep locale filter`);
  assert.match(news, /\.limit\(100\)/, `${locale} news archive window must stay bounded`);

  const productsPage = read(`src/pages/${locale}/products/index.astro`);
  assert.doesNotMatch(productsPage, /search_corpus/, `${locale} product search must use compact card fields`);
  assert.match(productsPage, /demoMediaFirst/, `${locale} product cards must preserve rendered demo image fallback`);
}

const handbook = read('src/lib/pageData/handbookPage.ts');
assert.doesNotMatch(handbook, /body_basic|body_advanced/, 'handbook list must not fetch body fields');
assert.doesNotMatch(handbook, /definition_ko, definition_en/, 'handbook list must not fetch both definitions');
assert.match(handbook, /eq\('status', 'published'\)/, 'handbook list must keep published filter');
assert.match(handbook, /\.limit\(500\)/, 'handbook search coverage must stay bounded');

const products = read('src/lib/pageData/productsPage.ts');
assert.doesNotMatch(products, /ai_product_categories'\)\.select\('\*'\)/, 'product categories must use exact tile fields');
assert.match(products, /const PRODUCT_CATEGORY_COLUMNS/, 'product category fields must be named');
const cardColumns = products.match(/const CARD_COLUMNS =[\s\S]*?;/)?.[0] || '';
assert.match(cardColumns, /demo_media/, 'demo media stays because cards render its first image');
assert.doesNotMatch(cardColumns, /search_corpus/, 'full product search corpus must not ship on every list card');
assert.match(products, /eq\('is_published', true\)/, 'products must keep published filter');
assert.match(products, /eq\('archived', false\)/, 'products must keep archived filter');

console.log('public-list-query-budget.test.cjs passed');
