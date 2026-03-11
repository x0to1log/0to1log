const fs = require('fs');
const path = require('path');
const css = fs.readFileSync(path.join(process.cwd(), 'frontend/src/styles/global.css'), 'utf8');
const featured = fs.readFileSync(path.join(process.cwd(), 'frontend/src/components/blog/BlogFeaturedCard.astro'), 'utf8');
const listItem = fs.readFileSync(path.join(process.cwd(), 'frontend/src/components/blog/BlogListItem.astro'), 'utf8');

function assert(cond, msg) {
  if (!cond) {
    console.error(msg);
    process.exit(1);
  }
}

assert(css.includes('.blog-category-badge'), 'Missing .blog-category-badge selector');
assert(/\.blog-category-badge\s*\{[^}]*font-family:\s*var\(--font-blog-ui\)/s.test(css), 'Category badge should use --font-blog-ui');
assert(featured.includes('class="blog-category-badge"'), 'Featured card should use blog-category-badge');
assert(listItem.includes('class="blog-list-item-category blog-category-badge"'), 'List item category should include blog-category-badge');
console.log('blog category badge font mapping ok');
