const fs = require('fs');
const path = require('path');
const assert = require('assert');

const repoRoot = path.resolve(__dirname, '..');
const globalCss = fs.readFileSync(path.join(repoRoot, 'src/styles/global.css'), 'utf8');
const articleLayout = fs.readFileSync(
  path.join(repoRoot, 'src/components/newsprint/NewsprintArticleLayout.astro'),
  'utf8'
);
const enDetail = fs.readFileSync(path.join(repoRoot, 'src/pages/en/log/[slug].astro'), 'utf8');
const koDetail = fs.readFileSync(path.join(repoRoot, 'src/pages/ko/log/[slug].astro'), 'utf8');
const head = fs.readFileSync(path.join(repoRoot, 'src/components/Head.astro'), 'utf8');

assert(
  globalCss.includes('--font-article-deck:'),
  'global.css should declare --font-article-deck'
);
assert(
  globalCss.includes('.newsprint-deck'),
  'global.css should define .newsprint-deck'
);
assert(
  globalCss.includes('font-family: var(--font-article-deck);'),
  '.newsprint-deck should use the article deck font role'
);
assert(
  globalCss.includes('font-style: italic;'),
  '.newsprint-deck should render italic'
);
assert(
  articleLayout.includes('excerpt?: string | null;'),
  'NewsprintArticleLayout should accept excerpt'
);
assert(
  articleLayout.includes('<p class="newsprint-deck">{excerpt}</p>'),
  'NewsprintArticleLayout should render excerpt as deck'
);
assert(
  enDetail.includes('excerpt={post.excerpt}'),
  'EN detail page should pass excerpt into NewsprintArticleLayout'
);
assert(
  koDetail.includes('excerpt={post.excerpt}'),
  'KO detail page should pass excerpt into NewsprintArticleLayout'
);
assert(
  head.includes('family=Playfair+Display'),
  'Head.astro should load Playfair Display for the article deck'
);

console.log('article-deck-font.test.cjs passed');
