const fs = require('fs');
const path = require('path');

const root = process.cwd();

function read(relPath) {
  return fs.readFileSync(path.join(root, relPath), 'utf8');
}

function assertIncludes(haystack, needle, label) {
  if (!haystack.includes(needle)) {
    throw new Error(`Missing ${label}: ${needle}`);
  }
}

const readingActionsRail = read('frontend/src/components/common/StickyReadingActions.astro');
const newsLayout = read('frontend/src/components/newsprint/NewsprintArticleLayout.astro');
const blogLayout = read('frontend/src/components/blog/BlogArticleLayout.astro');
const newsEn = read('frontend/src/pages/en/news/[slug].astro');
const newsKo = read('frontend/src/pages/ko/news/[slug].astro');
const blogEn = read('frontend/src/pages/en/blog/[slug].astro');
const blogKo = read('frontend/src/pages/ko/blog/[slug].astro');
const handbookEn = read('frontend/src/pages/en/handbook/[slug].astro');
const handbookKo = read('frontend/src/pages/ko/handbook/[slug].astro');
const css = read('frontend/src/styles/global.css');

assertIncludes(readingActionsRail, 'placement?:', 'reading actions placement prop');

assertIncludes(newsLayout, 'showStickyActions?: boolean;', 'news layout sticky action visibility prop');
assertIncludes(newsLayout, 'showStickyActions = true', 'news layout sticky action default');
assertIncludes(blogLayout, 'showStickyActions?: boolean;', 'blog layout sticky action visibility prop');
assertIncludes(blogLayout, 'showStickyActions = true', 'blog layout sticky action default');

assertIncludes(newsEn, 'showStickyActions={false}', 'news EN inline actions disabled');
assertIncludes(newsKo, 'showStickyActions={false}', 'news KO inline actions disabled');
assertIncludes(blogEn, 'showStickyActions={false}', 'blog EN inline actions disabled');
assertIncludes(blogKo, 'showStickyActions={false}', 'blog KO inline actions disabled');

assertIncludes(newsEn, '<ReadingActionsRail', 'news EN right rail action wrapper');
assertIncludes(newsKo, '<ReadingActionsRail', 'news KO right rail action wrapper');
assertIncludes(blogEn, '<ReadingActionsRail', 'blog EN right rail action wrapper');
assertIncludes(blogKo, '<ReadingActionsRail', 'blog KO right rail action wrapper');
assertIncludes(handbookEn, '<ReadingActionsRail', 'handbook EN right rail action wrapper');
assertIncludes(handbookKo, '<ReadingActionsRail', 'handbook KO right rail action wrapper');

assertIncludes(css, '.reading-actions--rail-placement {', 'desktop rail placement action styles');
assertIncludes(css, '.newsprint-rail-stack {', 'newsprint rail stack wrapper styles');
assertIncludes(css, '.blog-rail {', 'blog rail wrapper styles');
assertIncludes(css, '.blog-rail .blog-toc {', 'blog TOC inside unified rail styles');

console.log('detail-rail-actions-placement.test.cjs passed');
