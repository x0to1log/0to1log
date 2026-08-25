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

function assertExcludes(haystack, needle, label) {
  if (haystack.includes(needle)) {
    throw new Error(`Unexpected ${label}: ${needle}`);
  }
}

const featuredCard = read('frontend/src/components/blog/BlogFeaturedCard.astro');
const listItem = read('frontend/src/components/blog/BlogListItem.astro');
const enIndex = read('frontend/src/pages/en/blog/index.astro');
const koIndex = read('frontend/src/pages/ko/blog/index.astro');
const bookmarkScript = read('frontend/src/scripts/bookmark.ts');

assertIncludes(featuredCard, 'isBookmarked?: boolean;', 'blog featured bookmark prop');
assertIncludes(featuredCard, 'itemId?: string;', 'blog featured bookmark item id prop');
assertIncludes(featuredCard, "itemType?: 'blog';", 'blog featured bookmark item type prop');
assertIncludes(featuredCard, 'newsprint-bookmark-icon', 'blog featured bookmark button markup');
assertIncludes(featuredCard, 'data-item-id={itemId}', 'blog featured bookmark item id binding');
assertIncludes(featuredCard, 'data-item-type={itemType}', 'blog featured bookmark item type binding');

assertIncludes(listItem, 'isBookmarked?: boolean;', 'blog list bookmark prop');
assertIncludes(listItem, 'itemId?: string;', 'blog list bookmark item id prop');
assertIncludes(listItem, "itemType?: 'blog';", 'blog list bookmark item type prop');
assertIncludes(listItem, 'newsprint-bookmark-icon', 'blog list bookmark button markup');
assertIncludes(listItem, 'data-item-id={itemId}', 'blog list bookmark item id binding');
assertIncludes(listItem, 'data-item-type={itemType}', 'blog list bookmark item type binding');

assertExcludes(enIndex, 'bookmarkedPostIds', 'EN blog SSR bookmark state');
assertIncludes(enIndex, 'itemId={post.id}', 'EN blog list bookmark item id wiring');
assertIncludes(enIndex, 'itemType="blog"', 'EN blog list bookmark item type wiring');
assertIncludes(enIndex, '<BlogFeaturedCard', 'EN featured blog card usage');

assertExcludes(koIndex, 'bookmarkedPostIds', 'KO blog SSR bookmark state');
assertIncludes(koIndex, 'itemId={post.id}', 'KO blog list bookmark item id wiring');
assertIncludes(koIndex, 'itemType="blog"', 'KO blog list bookmark item type wiring');
assertIncludes(koIndex, '<BlogFeaturedCard', 'KO featured blog card usage');
assertIncludes(bookmarkScript, "import './content-status';", 'shared client bookmark hydration');

console.log('blog-bookmark-card-contract.test.cjs passed');
