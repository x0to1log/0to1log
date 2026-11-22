// frontend/tests/prose-korean-line-breaks.test.cjs
// Korean body text on handbook and blog pages must wrap between words, not inside them.
// The shared prose container carries the rule, so news, handbook and blog bodies all get it;
// the text blocks that sit outside the prose container on those pages are listed with it.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const css = fs.readFileSync(path.join(__dirname, '..', 'src', 'styles', 'global.css'), 'utf8');

const marker = '/* Korean line breaks:';
const start = css.indexOf(marker);
assert(start !== -1, 'global.css has the Korean line-break rule');
const open = css.indexOf('{', start);
const close = css.indexOf('}', open);
const selectors = css.slice(css.indexOf('*/', start) + 2, open).split(',').map((s) => s.trim());
const body = css.slice(open + 1, close);

for (const selector of [
  '.newsprint-prose',
  '.handbook-hero-card__definition',
  '.handbook-hero-card__news-line',
  '.handbook-references__annotation',
  '.handbook-today-def',
  '.handbook-intro',
  '.blog-article-title',
  '.blog-post-dek',
  '.blog-post-pager-title',
  '.blog-lead-title',
  '.blog-lead-excerpt',
  '.blog-serial-title',
  '.news-article-terms',
  '.news-read-next-title',
  '.news-twin-desk-title',
  '.news-twin-desk-excerpt',
  '.weekly-card-heading',
  '.weekly-card-def',
  '.newsprint-quiz-question',
  '.newsprint-quiz-option',
  '.newsprint-quiz-explanation',
]) {
  assert(selectors.includes(selector), `${selector} wraps between words`);
}
assert(/word-break:\s*keep-all;/.test(body), 'words are kept whole');
assert(/overflow-wrap:\s*break-word;/.test(body), 'a string longer than the line (URL, identifier) still wraps');

// Code keeps its own rule: identifiers may break anywhere rather than overflow.
assert(/\.newsprint-prose code \{[^}]*word-break:\s*break-word;/.test(css), 'inline code still breaks inside long identifiers');

console.log('prose-korean-line-breaks: ok');
