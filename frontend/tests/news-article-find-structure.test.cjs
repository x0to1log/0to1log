const fs = require('fs');
const path = require('path');
const assert = require('assert');

function read(relativePath) {
  return fs.readFileSync(path.join(process.cwd(), relativePath), 'utf8');
}

const layout = read('frontend/src/components/newsprint/NewsprintArticleLayout.astro');

assert.ok(
  layout.includes('data-article-find-root'),
  'NewsprintArticleLayout.astro must mark the article body as searchable',
);
assert.ok(
  layout.includes('id="article-find"'),
  'NewsprintArticleLayout.astro must render an article find input',
);
assert.ok(
  layout.includes('data-article-find-count'),
  'NewsprintArticleLayout.astro must render an article find result count',
);
assert.ok(
  layout.includes("import '../../scripts/articleFind';"),
  'NewsprintArticleLayout.astro must import the article find script',
);
assert.ok(
  layout.includes("newsprint:article-content-updated"),
  'NewsprintArticleLayout.astro must notify article search after persona switches',
);

function assertDetailPage(relativePath) {
  const source = read(relativePath);

  assert.ok(
    source.includes('articleFindQuery'),
    `${relativePath}: detail page must read q from the URL for article search restore`,
  );
}

assertDetailPage('frontend/src/pages/en/news/[slug].astro');
assertDetailPage('frontend/src/pages/ko/news/[slug].astro');

console.log('news-article-find-structure.test.cjs passed');
