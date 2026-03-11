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

const component = read('frontend/src/components/newsprint/HandbookFeedback.astro');
assertIncludes(component, 'class="handbook-feedback-inner"', 'two-column feedback wrapper');
assertIncludes(component, 'class="handbook-feedback-copy"', 'feedback copy wrapper');
assertNotIncludes(component, 'class="handbook-feedback-header"', 'header-only layout wrapper');

const css = read('frontend/src/styles/global.css');
assertIncludes(css, '.handbook-feedback-inner {', 'desktop inner layout styles');
assertIncludes(css, '.handbook-feedback-copy {', 'copy region styles');
assertIncludes(css, '@media (max-width: 640px)', 'mobile feedback media query');

console.log('handbook-feedback-layout.test.cjs passed');
