// frontend/tests/home-front-query-budget.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const read = (p) => fs.readFileSync(path.join(__dirname, '..', p), 'utf8');
const home = read('src/lib/pageData/homeFrontPage.ts');
const tod = read('src/lib/pageData/termOfDay.ts');
const count = (src, re) => (src.match(re) || []).length;

// home: one news query + the shared term of the day
assert.equal(count(home, /\.from\('news_posts'\)/g), 1, 'exactly one news_posts query');
assert.equal(count(home, /\.from\('handbook_terms'\)/g), 0, 'home owns no term query (lib/pageData/termOfDay.ts does)');
assert(/\.from\('news_posts'\)[\s\S]*?\.limit\(6\)/.test(home), 'news query is limited to 6 rows');
assert(/selectFrontPage\(/.test(home), 'selection logic lives in lib/homeFront.js');
assert(/fetchTermOfDay\(/.test(home), 'term of the day comes from the shared helper');
assert(!/select\('\*'\)/.test(home), 'no select(*) on the home');

// term of the day: one count query + one single-row query
assert.equal(count(tod, /\.from\('handbook_terms'\)/g), 2, 'handbook_terms: one count query + one single-row query');
assert(/count: 'exact', head: true/.test(tod), 'term count uses head-only exact count');
assert(/\.range\(i, i\)/.test(tod), 'term fetch is a single row via range(i, i)');
assert(/\.order\('slug'/.test(tod), 'term order is stable by slug');
assert(!/is_favourite/.test(tod), 'term of the day comes from all published terms');
assert(!/select\('\*'\)/.test(tod), 'no select(*)');
assert(/definition:\$\{definitionField\}/.test(tod), 'only the locale definition column is selected');
assert(/termIndex\(/.test(tod), 'term index comes from lib/homeFront.js');
console.log('home-front-query-budget.test.cjs passed');
