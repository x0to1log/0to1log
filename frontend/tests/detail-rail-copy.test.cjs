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
assert(rail.includes('Focus of This Article'), 'Missing EN detail rail heading: Focus of This Article');
assert(rail.includes('More in This Issue'), 'Missing EN detail rail heading: More in This Issue');
assert(rail.includes('focusItems.length === 0'), 'Detail rail must handle empty focus state');
assert(rail.includes('posts.length === 0'), 'Detail rail must handle empty related-posts state');

const enDetail = read('src/pages/en/log/[slug].astro');
const koDetail = read('src/pages/ko/log/[slug].astro');

assert(enDetail.includes('focusItems={focusItems}'), 'EN detail page must pass focusItems into NewsprintSideRail');
assert(koDetail.includes('focusItems={focusItems}'), 'KO detail page must pass focusItems into NewsprintSideRail');
