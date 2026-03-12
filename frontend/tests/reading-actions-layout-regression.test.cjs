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

assertNotIncludes(
  css,
  'grid-template-columns: 88px minmax(0, 1fr);',
  'desktop base layout reserving the obsolete left action column'
);

assertIncludes(
  css,
  "  .reading-actions-layout--article {\n    display: grid;\n    grid-template-columns: minmax(0, 1fr) 72px;",
  'desktop article layout owning the body and right-rail grid'
);

assertIncludes(
  css,
  '.reading-actions--rail-placement .reading-actions__button:hover {',
  'desktop rail action hover feedback'
);

assertIncludes(
  css,
  '.reading-actions--rail-placement .reading-actions__button:focus-visible {',
  'desktop rail action focus-visible feedback'
);

console.log('reading-actions-layout-regression.test.cjs passed');
