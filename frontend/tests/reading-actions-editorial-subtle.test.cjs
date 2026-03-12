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

const css = read('frontend/src/styles/global.css');
const railHoverBlock = css.split('.reading-actions--rail-placement .reading-actions__button:hover {')[1]?.split('}')[0] || '';

assertIncludes(
  css,
  '.reading-actions--rail-placement .reading-actions__button {',
  'desktop rail button block'
);

assertIncludes(
  css,
  'min-height: 3.35rem;',
  'smaller editorial rail buttons'
);

assertIncludes(
  css,
  'box-shadow: none;',
  'flat editorial button treatment'
);

assertIncludes(
  css,
  'color: var(--color-text-secondary);',
  'subtle rail button text color'
);

assertIncludes(
  css,
  '.reading-actions--rail-placement .reading-actions__items--article {\n    display: grid;\n    grid-template-columns: repeat(4, minmax(0, 1fr));',
  'desktop rail actions arranged in a single four-button row'
);

assertIncludes(
  css,
  '.reading-actions--rail-placement .reading-actions__button:hover {',
  'editorial rail hover state'
);

assertNotIncludes(railHoverBlock, 'transform:', 'lifted hover effect on editorial rail buttons');

console.log('reading-actions-editorial-subtle.test.cjs passed');
