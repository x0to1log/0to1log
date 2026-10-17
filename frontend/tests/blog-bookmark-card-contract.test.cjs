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

const serialItem = read('frontend/src/components/blog/BlogSerialItem.astro');
const listItem = read('frontend/src/components/blog/BlogListItem.astro');
const enIndex = read('frontend/src/pages/en/blog/index.astro');
const koIndex = read('frontend/src/pages/ko/blog/index.astro');
const bookmarkScript = read('frontend/src/scripts/bookmark.ts');

// list page rows (series episodes + short notes): the button lives inside li.blog-list-item (read-state target)
assertIncludes(serialItem, '<li class="blog-list-item">', 'blog serial row read-state target');
assertIncludes(serialItem, 'class="newsprint-bookmark-icon"', 'blog serial bookmark button markup');
assertIncludes(serialItem, 'data-item-id={post.id}', 'blog serial bookmark item id binding');
assertIncludes(serialItem, 'data-item-type="blog"', 'blog serial bookmark item type binding');
assertIncludes(serialItem, 'data-bookmarked="false"', 'blog serial bookmark neutral SSR state');

assertIncludes(listItem, 'isBookmarked?: boolean;', 'blog list bookmark prop');
assertIncludes(listItem, 'itemId?: string;', 'blog list bookmark item id prop');
assertIncludes(listItem, "itemType?: 'blog';", 'blog list bookmark item type prop');
assertIncludes(listItem, 'newsprint-bookmark-icon', 'blog list bookmark button markup');
assertIncludes(listItem, 'data-item-id={itemId}', 'blog list bookmark item id binding');
assertIncludes(listItem, 'data-item-type={itemType}', 'blog list bookmark item type binding');

assertExcludes(enIndex, 'bookmarkedPostIds', 'EN blog SSR bookmark state');
assertIncludes(enIndex, '<BlogFront ', 'EN blog serial front usage');

assertExcludes(koIndex, 'bookmarkedPostIds', 'KO blog SSR bookmark state');
assertIncludes(koIndex, '<BlogFront ', 'KO blog serial front usage');
assertIncludes(bookmarkScript, "import './content-status';", 'shared client bookmark hydration');

console.log('blog-bookmark-card-contract.test.cjs passed');
