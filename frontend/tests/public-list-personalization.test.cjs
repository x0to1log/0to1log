const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const listPages = [
  'src/pages/ko/news/index.astro',
  'src/pages/en/news/index.astro',
  'src/pages/ko/handbook/index.astro',
  'src/pages/en/handbook/index.astro',
  'src/pages/ko/blog/index.astro',
  'src/pages/en/blog/index.astro',
];

for (const relativePath of listPages) {
  const source = fs.readFileSync(path.join(root, relativePath), 'utf8');
  assert.doesNotMatch(source, /createClient/, `${relativePath} must not create an authenticated Supabase client`);
  assert.doesNotMatch(source, /reading_history/, `${relativePath} must not query reading history during SSR`);
  assert.doesNotMatch(source, /user_bookmarks/, `${relativePath} must not query bookmarks during SSR`);
}

const bookmarkScript = fs.readFileSync(path.join(root, 'src/scripts/bookmark.ts'), 'utf8');
assert.match(bookmarkScript, /import ['"]\.\/content-status['"]/, 'bookmark behavior must load shared content status hydration');
assert.doesNotMatch(bookmarkScript, /bookmarks\/status/, 'bookmark behavior must not issue a second status request');

const endpoint = fs.readFileSync(path.join(root, 'src/pages/api/user/content-status.ts'), 'utf8');
assert.match(endpoint, /MAX_ITEMS\s*=\s*200/, 'content status batches must be bounded');
assert.match(endpoint, /from\('user_bookmarks'\)/, 'content status must query bookmarks');
assert.match(endpoint, /from\('reading_history'\)/, 'content status must query reading history');
assert.match(endpoint, /private, no-store/, 'personalization responses must never be publicly cached');

const hydration = fs.readFileSync(path.join(root, 'src/scripts/content-status.ts'), 'utf8');
assert.match(hydration, /\/api\/user\/content-status/, 'hydration must use the combined endpoint');
assert.match(hydration, /newsprint-card--read/, 'hydration must mark news and handbook cards as read');
assert.match(hydration, /blog-list-item--read/, 'hydration must mark blog list items as read');
assert.match(hydration, /content-status:refresh/, 'hydration must support lazily rendered cards');

for (const locale of ['ko', 'en']) {
  const handbook = fs.readFileSync(path.join(root, `src/pages/${locale}/handbook/index.astro`), 'utf8');
  assert.match(handbook, /content-status:refresh/, `${locale} handbook must hydrate cards created after page load`);
}

console.log('public-list-personalization.test.cjs passed');
