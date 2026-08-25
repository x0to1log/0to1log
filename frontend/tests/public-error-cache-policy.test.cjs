const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');

for (const locale of ['ko', 'en']) {
  const home = read(`src/pages/${locale}/index.astro`);
  assert.match(home, /siteContentError[\s\S]*Astro\.response\.status = 503/, `${locale} home must mark site-content failures unavailable`);

  for (const section of ['news', 'handbook', 'blog']) {
    const list = read(`src/pages/${locale}/${section}/index.astro`);
    assert.match(list, /if \(fetchError\)\s*\{?\s*Astro\.response\.status = 503/, `${locale} ${section} list must return 503 on loader error`);
  }

  const productsList = read(`src/pages/${locale}/products/index.astro`);
  assert.match(productsList, /if \(error\)\s*\{?\s*Astro\.response\.status = 503/, `${locale} products list must return 503 on loader error`);

  for (const [section, errorName, rowName] of [
    ['news', 'postError', 'post'],
    ['blog', 'postError', 'post'],
    ['handbook', 'termError', 'term'],
  ]) {
    const detail = read(`src/pages/${locale}/${section}/[slug].astro`);
    assert.match(detail, new RegExp(`if \\(${errorName}\\)[\\s\\S]*status = 503`), `${locale} ${section} detail must return 503 on loader error`);
    assert.match(detail, new RegExp(`else if \\(!${rowName}\\)[\\s\\S]*status = 404`), `${locale} ${section} detail must preserve 404 for missing rows`);
  }

  const productDetail = read(`src/pages/${locale}/products/[slug].astro`);
  assert.match(productDetail, /if \(error\)[\s\S]*status = 503/, `${locale} product detail must return 503 on loader error`);
  assert.match(productDetail, /else if \(!product\)[\s\S]*status = 404/, `${locale} product detail must preserve 404`);

  const handbookCategory = read(`src/pages/${locale}/handbook/category/[slug].astro`);
  assert.match(handbookCategory, /if \(error\)\s*\{?\s*Astro\.response\.status = 503/, `${locale} handbook category must return 503 on loader error`);
}

const productsLoader = read('src/lib/pageData/productsPage.ts');
assert.match(productsLoader, /categoriesRes\.error \|\| productsRes\.error/, 'products loader must surface either list query failure');

const cachePolicy = read('src/lib/server/publicCachePolicy.ts');
assert.match(cachePolicy, /hasError[\s\S]*no-store/, 'public cache policy must keep error responses uncached');

console.log('public-error-cache-policy.test.cjs passed');
