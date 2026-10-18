const fs = require('fs');
const path = require('path');
const css = fs.readFileSync(path.join(process.cwd(), 'frontend/src/styles/global.css'), 'utf8');
const serialItem = fs.readFileSync(path.join(process.cwd(), 'frontend/src/components/blog/BlogSerialItem.astro'), 'utf8');

function assert(cond, msg) {
  if (!cond) {
    console.error(msg);
    process.exit(1);
  }
}

assert(css.includes('.blog-category-badge'), 'Missing .blog-category-badge selector');
assert(/\.blog-category-badge\s*\{[^}]*font-family:\s*var\(--font-blog-ui\)/s.test(css), 'Category badge should use --font-blog-ui');
assert(serialItem.includes('<span class="blog-category-badge" style='), 'Short-note row field label should use blog-category-badge');
console.log('blog category badge font mapping ok');
