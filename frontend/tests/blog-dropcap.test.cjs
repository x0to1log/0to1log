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

const blogArticleLayout = read('frontend/src/components/blog/BlogArticleLayout.astro');
assertIncludes(
  blogArticleLayout,
  '<div class="newsprint-prose newsprint-prose--no-dropcap">',
  'blog prose no-dropcap class'
);

const globalCss = read('frontend/src/styles/global.css');
assertIncludes(globalCss, '.newsprint-prose--no-dropcap p:first-of-type::first-letter {', 'no-dropcap override styles');

console.log('blog-dropcap.test.cjs passed');
