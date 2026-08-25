const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');

const helper = read('src/lib/pageData/publicTermIndex.ts');
assert.match(helper, /export async function fetchPublicTermIndex/, 'one shared helper must own the detail term query');
assert.match(helper, /summary:\$\{summaryField\}/, 'summary must use one locale column');
assert.match(helper, /definition:\$\{definitionField\}/, 'definition must use one locale column');
assert.match(helper, /basic_plain:\$\{basicField\}/, 'basic body must use one locale column');
assert.match(helper, /\.limit\(limit\)/, 'public term index must be bounded');

for (const file of ['src/lib/pageData/newsDetailPage.ts', 'src/lib/pageData/blogDetailPage.ts']) {
  const source = read(file);
  assert.match(source, /fetchPublicTermIndex/, `${file} must reuse the shared term index`);
  assert.doesNotMatch(source, /body_basic_ko, body_basic_en/, `${file} must not transfer both locale bodies`);
  assert.doesNotMatch(source, /from\('handbook_terms'\)/, `${file} must not own a duplicate term query`);
}

const handbookPage = read('src/lib/pageData/handbookPage.ts');
assert.doesNotMatch(handbookPage, /definition_ko, definition_en/, 'handbook lists must not transfer both definitions');
assert.match(handbookPage, /definition:\$\{definitionField\}/, 'handbook lists must select the active locale definition');

console.log('public-term-index.test.cjs passed');
