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

if (newsEn.includes('showStickyActions={false}')) throw new Error('news EN uses inline reading actions');
if (newsKo.includes('showStickyActions={false}')) throw new Error('news KO uses inline reading actions');
// Blog post A (2026-10-17): blog uses the inline actions too (right 72px column from 1024px, bottom bar below).
if (blogEn.includes('showStickyActions={false}')) throw new Error('blog EN uses inline reading actions');
if (blogKo.includes('showStickyActions={false}')) throw new Error('blog KO uses inline reading actions');

if (newsEn.includes('<ReadingActionsRail')) throw new Error('news EN has no right rail');
if (newsKo.includes('<ReadingActionsRail')) throw new Error('news KO has no right rail');
if (blogEn.includes('<ReadingActionsRail')) throw new Error('blog EN has no right rail');
if (blogKo.includes('<ReadingActionsRail')) throw new Error('blog KO has no right rail');
if (handbookEn.includes('<ReadingActionsRail')) throw new Error('handbook EN has no right rail');
if (handbookKo.includes('<ReadingActionsRail')) throw new Error('handbook KO has no right rail');
assertIncludes(handbookEn, '<StickyReadingActions', 'handbook EN inline term actions');
assertIncludes(handbookKo, '<StickyReadingActions', 'handbook KO inline term actions');

assertIncludes(css, '.reading-actions--rail-placement {', 'desktop rail placement action styles');
assertIncludes(css, '.newsprint-rail-stack {', 'newsprint rail stack wrapper styles');
assertIncludes(css, '.blog-rail {', 'blog rail wrapper styles');
assertIncludes(css, '.blog-rail .blog-toc {', 'blog TOC inside unified rail styles');

console.log('detail-rail-actions-placement.test.cjs passed');
