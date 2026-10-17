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

// Blog list A (2026-10-17): the old .blog-section-header ("추천 글"/"전체 글") is gone.
// Section headings are now the latest post, series and short-notes h2s: Hahmlet 700.
const css = read('frontend/src/styles/global.css');
for (const selector of ['.blog-lead-title', '.blog-series-title', '.blog-short-notes-title']) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = css.match(new RegExp(`(?:^|\\n)${escaped}\\s*\\{([\\s\\S]*?)\\n\\}`));
  if (!match) {
    throw new Error(`Missing ${selector} rule block`);
  }
  assertIncludes(match[1], 'font-family: var(--font-blog-heading);', `${selector} heading font`);
  assertIncludes(match[1], 'font-weight: 700;', `${selector} weight`);
}
if (css.includes('.blog-section-header')) {
  throw new Error('Unexpected legacy .blog-section-header rule');
}

console.log('blog-section-heading-font.test.cjs passed');
