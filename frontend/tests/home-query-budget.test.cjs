const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const source = fs.readFileSync(
  path.resolve(__dirname, '../src/lib/pageData/homePage.ts'),
  'utf8',
);

assert.equal(
  (source.match(/\.from\('news_posts'\)/g) || []).length,
  1,
  'home data must use one bounded news window',
);
assert.match(source, /const termDefinitionField = locale === 'ko'/, 'term fields must be locale-aware');
assert.match(source, /definition:\$\{termDefinitionField\}/, 'term select must normalize one locale definition');
assert.doesNotMatch(source, /definition_en, definition_ko/, 'home must not transfer both definitions');

const initialParallel = source.slice(source.indexOf('await Promise.all(['), source.indexOf(']);', source.indexOf('await Promise.all([')));
assert.doesNotMatch(initialParallel, /is_favourite', false/, 'fallback terms must not be fetched eagerly');
assert.match(source, /if \(terms\.length < 6\)[\s\S]*is_favourite', false/, 'fallback terms must be conditional');

assert.match(source, /\.from\('blog_posts'\)[\s\S]*\.limit\(4\)/, 'blog cards must stay bounded');
assert.match(source, /eq\('is_favourite', true\)[\s\S]*\.limit\(6\)/, 'favourite terms must stay bounded');
assert.match(source, /\.limit\(20\)/, 'news window must stay bounded');

console.log('home-query-budget.test.cjs passed');
