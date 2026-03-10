const fs = require('fs');
const path = require('path');

function read(filePath) {
  return fs.readFileSync(path.join(__dirname, '..', filePath), 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const rail = read('src/components/newsprint/NewsprintSideRail.astro');
assert(rail.includes('Summary of This Article'), 'Missing EN detail rail heading: Summary of This Article');
assert(rail.includes('비슷한 뉴스 더 보기'), 'Missing KO detail rail heading: 비슷한 뉴스 더 보기');
assert(rail.includes('focusItems.length === 0'), 'Detail rail must handle empty focus state');
assert(rail.includes('posts.length === 0'), 'Detail rail must handle empty related-posts state');

const enDetail = read('src/pages/en/log/[slug].astro');
const koDetail = read('src/pages/ko/log/[slug].astro');
const libraryIndex = read('src/pages/library/index.astro');

assert(enDetail.includes('focusItems={focusItems}'), 'EN detail page must pass focusItems into NewsprintSideRail');
assert(koDetail.includes('focusItems={focusItems}'), 'KO detail page must pass focusItems into NewsprintSideRail');
assert(libraryIndex.includes("tabProgress: '나의 학습 현황'"), 'Library tab label must be 나의 학습 현황 in Korean');
