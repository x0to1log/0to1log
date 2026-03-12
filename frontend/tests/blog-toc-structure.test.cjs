const fs = require('fs');
const path = require('path');
const assert = require('assert');

function read(relativePath) {
  return fs.readFileSync(path.join(process.cwd(), relativePath), 'utf8');
}

function sliceBetween(source, startMarker, endMarker) {
  const start = source.indexOf(startMarker);
  const end = source.indexOf(endMarker, start);
  assert.notStrictEqual(start, -1, `Missing start marker: ${startMarker}`);
  assert.notStrictEqual(end, -1, `Missing end marker: ${endMarker}`);
  return source.slice(start, end);
}

const tocSource = read('frontend/src/components/blog/BlogTOC.astro');

assert.ok(
  tocSource.includes("document.addEventListener('astro:page-load', initBlogTOC);"),
  'BlogTOC.astro must reinitialize on astro:page-load for client-side page transitions',
);
assert.ok(
  !tocSource.includes("document.addEventListener('DOMContentLoaded', initBlogTOC);"),
  'BlogTOC.astro must not double-bind initialization through DOMContentLoaded',
);
assert.ok(
  tocSource.includes("nav.innerHTML = '';"),
  'BlogTOC.astro must clear old TOC links before rebuilding',
);
assert.ok(
  tocSource.includes('observer.disconnect()'),
  'BlogTOC.astro must disconnect the previous IntersectionObserver before reinitializing',
);
assert.ok(
  tocSource.includes("window.addEventListener('scroll', updateActiveHeading"),
  'BlogTOC.astro must track active headings while scrolling for more stable TOC highlighting',
);

const css = read('frontend/src/styles/global.css');
const tocBlock = sliceBetween(css, '.blog-toc {', '.blog-toc::-webkit-scrollbar');

assert.ok(
  tocBlock.includes('background: transparent;'),
  'Blog TOC must keep a transparent right rail background',
);
assert.ok(
  tocBlock.includes('border: none;'),
  'Blog TOC must remove the card border',
);
assert.ok(
  tocBlock.includes('box-shadow: none;'),
  'Blog TOC must remove the card shadow',
);

console.log('blog-toc-structure.test.cjs passed');
