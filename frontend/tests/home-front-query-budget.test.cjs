// frontend/tests/home-front-query-budget.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const file = path.join(__dirname, '..', 'src/lib/pageData/homeFrontPage.ts');
const src = fs.readFileSync(file, 'utf8');
const count = (re) => (src.match(re) || []).length;

assert.equal(count(/\.from\('news_posts'\)/g), 1, 'exactly one news_posts query');
assert.equal(count(/\.from\('handbook_terms'\)/g), 1, 'exactly one handbook_terms query');
assert(/\.from\('news_posts'\)[\s\S]*?\.limit\(6\)/.test(src), 'news query is limited to 6 rows');
assert(/\.from\('handbook_terms'\)[\s\S]*?\.limit\(60\)/.test(src), 'term query is limited to 60 rows');
assert(!/select\('\*'\)/.test(src), 'no select(*)');
assert(/\.eq\('is_favourite', true\)/.test(src), 'term of the day comes from favourites');
assert(/definition:\$\{definitionField\}/.test(src), 'only the locale definition column is selected');
assert(/selectFrontPage\(/.test(src), 'selection logic lives in lib/homeFront.js');
console.log('home-front-query-budget.test.cjs passed');
