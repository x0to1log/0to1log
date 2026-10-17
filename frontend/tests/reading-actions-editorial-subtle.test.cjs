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

function assertNotIncludes(haystack, needle, label) {
  if (haystack.includes(needle)) {
    throw new Error(`Unexpected ${label}: ${needle}`);
  }
}

// Blog post A (2026-10-17): the editorial rail placement (ReadingActionsRail, blog only) is gone.
// News, handbook and blog details all use the inline article actions; keep them quiet and flat.
const css = read('frontend/src/styles/global.css');
const articleButtonBlock = css.split('\n.reading-actions--article .reading-actions__button {')[1]?.split('}')[0] || '';

assertNotIncludes(css, '.reading-actions--rail-placement', 'removed rail placement styles');

assertIncludes(
  articleButtonBlock,
  'color: var(--color-text-secondary);',
  'subtle article action text color'
);

assertIncludes(
  articleButtonBlock,
  'background: color-mix(in srgb, var(--color-bg-secondary) 92%, transparent);',
  'quiet article action surface'
);

assertNotIncludes(articleButtonBlock, 'box-shadow', 'raised article action buttons');
assertNotIncludes(articleButtonBlock, 'transform:', 'lifted article action buttons');

console.log('reading-actions-editorial-subtle.test.cjs passed');
