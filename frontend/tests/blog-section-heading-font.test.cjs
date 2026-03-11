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

const css = read('frontend/src/styles/global.css');
const match = css.match(/\.blog-section-header\s*\{([\s\S]*?)\n\}/);
if (!match) {
  throw new Error('Missing blog section header rule block');
}

const block = match[1];
assertIncludes(block, 'font-family: var(--font-blog-masthead);', 'blog section header masthead font');

console.log('blog-section-heading-font.test.cjs passed');
