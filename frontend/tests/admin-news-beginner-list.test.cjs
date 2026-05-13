const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..', '..');
const adminNewsIndex = fs.readFileSync(
  path.join(root, 'frontend', 'src', 'pages', 'admin', 'news', 'index.astro'),
  'utf8',
);

assert(
  adminNewsIndex.includes('title_beginner') && adminNewsIndex.includes('guide_items'),
  'admin news list must fetch beginner title metadata, not only canonical title fields',
);

assert(
  adminNewsIndex.includes('getBeginnerTitle(post)'),
  'admin news list must resolve and render the beginner-specific title when available',
);

assert(
  adminNewsIndex.includes("data-title={`${post.title} ${getBeginnerTitle(post)}`.toLowerCase()}"),
  'admin news list search data must include beginner title text',
);

assert(
  !adminNewsIndex.includes('admin-persona-badge--beginner') &&
    !adminNewsIndex.includes('data-has-beginner=') &&
    !adminNewsIndex.includes('getListItemsForPost') &&
    !adminNewsIndex.includes('data-persona={'),
  'admin news list must not add a redundant beginner tag or split beginner into a separate row',
);

console.log('admin-news-beginner-list.test.cjs passed');
