const fs = require('fs');
const path = require('path');
const assert = require('assert');

function read(relativePath) {
  return fs.readFileSync(path.join(process.cwd(), relativePath), 'utf8');
}

const layout = read('frontend/src/components/newsprint/NewsprintArticleLayout.astro');
assert.ok(layout.includes('Fact Pack'), 'layout must include Fact Pack section');
assert.ok(layout.includes('Core Analysis'), 'layout must include Core Analysis section');
assert.ok(layout.includes('Sources'), 'layout must include Sources section');
assert.ok(layout.includes('source-card'), 'layout must render source cards');
assert.ok(layout.includes('newsprint-sources-toggle'), 'layout must include sources accordion toggle');

const pageData = read('frontend/src/lib/pageData/newsDetailPage.ts');
assert.ok(pageData.includes('factPack'), 'page data must return fact pack');
assert.ok(pageData.includes('sourceCards'), 'page data must return source cards');
assert.ok(pageData.includes('analysisHtml'), 'page data must return analysis HTML');
assert.ok(pageData.includes('applySourceCitations'), 'page data must apply inline citation rendering');

console.log('news-fact-pack-structure.test.cjs passed');
