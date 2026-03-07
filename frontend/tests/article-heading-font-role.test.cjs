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

const css = read('src/styles/global.css');

assert(css.includes('--font-article-heading:'), 'Theme must define a dedicated --font-article-heading token');
assert(css.includes('.newsprint-prose h1,'), 'Article prose must style h1 headings');
assert(css.includes('.newsprint-prose h2,'), 'Article prose must style h2 headings');
assert(css.includes('.newsprint-prose h3,'), 'Article prose must style h3 headings');
assert(css.includes('.newsprint-prose h4 {'), 'Article prose must style h4 headings');
assert(css.includes('font-family: var(--font-article-heading);'), 'Article prose headings must use the article heading font token');
assert(css.includes('.newsprint-lead-title {'), 'Lead title block must still exist separately');
