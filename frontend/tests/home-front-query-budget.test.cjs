// frontend/tests/home-front-query-budget.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const file = path.join(__dirname, '..', 'src/lib/pageData/homeFrontPage.ts');
const src = fs.readFileSync(file, 'utf8');
const count = (re) => (src.match(re) || []).length;

assert.equal(count(/\.from\('news_posts'\)/g), 1, 'exactly one news_posts query');
assert.equal(count(/\.from\('handbook_terms'\)/g), 2, 'handbook_terms: one count query + one single-row query');
assert(/\.from\('news_posts'\)[\s\S]*?\.limit\(6\)/.test(src), 'news query is limited to 6 rows');
assert(/count: 'exact', head: true/.test(src), 'term count uses head-only exact count');
assert(/\.range\(i, i\)/.test(src), 'term fetch is a single row via range(i, i)');
assert(/\.order\('slug'/.test(src), 'term order is stable by slug');
assert(!/is_favourite/.test(src), 'term of the day comes from all published terms');
assert(!/select\('\*'\)/.test(src), 'no select(*)');
assert(/definition:\$\{definitionField\}/.test(src), 'only the locale definition column is selected');
assert(/selectFrontPage\(/.test(src), 'selection logic lives in lib/homeFront.js');
assert(/termIndex\(/.test(src), 'term index comes from lib/homeFront.js');
console.log('home-front-query-budget.test.cjs passed');
