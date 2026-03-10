const fs = require('fs');
const path = require('path');
const assert = require('assert');

function read(relativePath) {
  return fs.readFileSync(path.join(process.cwd(), relativePath), 'utf8');
}

function assertBusinessBeforeResearch(relativePath) {
  const source = read(relativePath);
  const arrayStart = source.indexOf('const postTypeItems = [');
  assert.ok(arrayStart !== -1, `${relativePath}: postTypeItems array not found`);

  const businessIndex = source.indexOf("{ value: 'business'", arrayStart);
  const researchIndex = source.indexOf("{ value: 'research'", arrayStart);

  assert.ok(businessIndex !== -1, `${relativePath}: business tab not found`);
  assert.ok(researchIndex !== -1, `${relativePath}: research tab not found`);
  assert.ok(
    businessIndex < researchIndex,
    `${relativePath}: expected business tab before research tab`,
  );
}

assertBusinessBeforeResearch('frontend/src/pages/en/news/index.astro');
assertBusinessBeforeResearch('frontend/src/pages/ko/news/index.astro');

console.log('news-post-type-tab-order.test.cjs passed');
