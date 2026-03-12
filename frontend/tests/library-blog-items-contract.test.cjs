const fs = require('fs');
const path = require('path');

function read(relativePath) {
  return fs.readFileSync(path.join(process.cwd(), relativePath), 'utf8');
}

function assertIncludes(haystack, needle, label) {
  if (!haystack.includes(needle)) {
    throw new Error(`Missing ${label}: ${needle}`);
  }
}

const libraryPage = read('frontend/src/pages/library/index.astro');

assertIncludes(
  libraryPage,
  "const articleBookmarks = bookmarkItems.filter((item) => item.item_type === 'news' || item.item_type === 'blog');",
  'saved tab must treat blog bookmarks as articles',
);
assertIncludes(
  libraryPage,
  "if (item.item_type === 'news' || item.item_type === 'blog') postIds.add(item.item_id);",
  'library data lookup must include blog post ids',
);
assertIncludes(
  libraryPage,
  ".from('blog_posts').select('id, title, slug, category, locale, reading_time_min')",
  'library must fetch blog post metadata',
);
assertIncludes(
  libraryPage,
  "const href = post ? `/${post.locale || 'en'}/${post.type === 'blog' ? 'blog' : 'news'}/${post.slug}/` : '#';",
  'saved tab must route blog bookmarks to /blog/',
);
assertIncludes(
  libraryPage,
  "const post = item.item_type === 'news' || item.item_type === 'blog' ? postMap.get(item.item_id) : null;",
  'read tab must resolve blog history items from the shared post map',
);

console.log('library-blog-items-contract.test.cjs passed');
