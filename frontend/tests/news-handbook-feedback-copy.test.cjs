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

const articleLayout = read('frontend/src/components/newsprint/NewsprintArticleLayout.astro');
assertIncludes(articleLayout, '댓글', 'KO news comment title');
assertIncludes(articleLayout, 'Comments', 'EN news comment title');
assertIncludes(articleLayout, '핵심 변화에 대한 생각이나 해석을 남겨보세요.', 'KO news comment prompt');
assertIncludes(articleLayout, 'Share your take on what changed and why it matters.', 'EN news comment prompt');
assertIncludes(articleLayout, '의견을 남기려면 로그인하세요.', 'KO news login prompt');
assertIncludes(articleLayout, 'Log in to share your thoughts.', 'EN news login prompt');

const handbookFeedback = read('frontend/src/components/newsprint/HandbookFeedback.astro');
assertIncludes(handbookFeedback, '이 설명이 도움이 되었나요?', 'KO handbook feedback title');
assertIncludes(handbookFeedback, 'Was this explanation helpful?', 'EN handbook feedback title');
assertIncludes(handbookFeedback, '짧은 피드백은 더 좋은 설명을 만드는 데 도움이 됩니다.', 'KO handbook feedback body');
assertIncludes(handbookFeedback, 'Quick feedback helps improve future explanations.', 'EN handbook feedback body');

const handbookDetailEn = read('frontend/src/pages/en/handbook/[slug].astro');
const handbookDetailKo = read('frontend/src/pages/ko/handbook/[slug].astro');
assertIncludes(handbookDetailEn, '<HandbookFeedback locale={locale} />', 'EN handbook feedback mount');
assertIncludes(handbookDetailKo, '<HandbookFeedback locale={locale} />', 'KO handbook feedback mount');

console.log('news-handbook-feedback-copy.test.cjs passed');
