const fs = require('fs');
const path = require('path');
const assert = require('assert');

function read(relativePath) {
  return fs.readFileSync(path.join(process.cwd(), relativePath), 'utf8');
}

function assertListPage(relativePath) {
  const source = read(relativePath);

  assert.ok(
    source.includes('id="news-search"'),
    `${relativePath}: news list search input is missing`,
  );
  assert.ok(
    source.includes('data-placeholder-hints'),
    `${relativePath}: news list search must define rotating placeholder hints`,
  );
  assert.ok(
    source.includes('id="news-result-count"'),
    `${relativePath}: news list result count is missing`,
  );
  assert.ok(
    source.includes('id="news-no-results"'),
    `${relativePath}: news list empty state is missing`,
  );
  assert.ok(
    source.includes("import '../../../scripts/newsListSearch';"),
    `${relativePath}: news list search script is missing`,
  );
}

assertListPage('frontend/src/pages/en/news/index.astro');
assertListPage('frontend/src/pages/ko/news/index.astro');

const headline = read('frontend/src/components/newsprint/NewsprintHeadline.astro');
assert.ok(
  headline.includes('data-search-text='),
  'NewsprintHeadline.astro must expose search text for list filtering',
);

const listCard = read('frontend/src/components/newsprint/NewsprintListCard.astro');
assert.ok(
  listCard.includes('data-search-text='),
  'NewsprintListCard.astro must expose search text for list filtering',
);

const filter = read('frontend/src/components/newsprint/NewsprintCategoryFilter.astro');
assert.ok(
  filter.includes("newsprint:filter-change"),
  'NewsprintCategoryFilter.astro must dispatch a filter-change event for combined search',
);

console.log('news-search-list-structure.test.cjs passed');
