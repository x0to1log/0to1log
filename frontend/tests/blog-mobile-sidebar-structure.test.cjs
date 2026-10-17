const fs = require('fs');
const path = require('path');
const assert = require('assert');

function read(relativePath) {
  return fs.readFileSync(path.join(process.cwd(), relativePath), 'utf8');
}

const sidebar = read('frontend/src/components/blog/BlogSidebar.astro');

assert.ok(
  !sidebar.includes('blog-sidebar-close'),
  'BlogSidebar.astro must not render the mobile close button',
);
assert.ok(
  !sidebar.includes('data-sidebar-close'),
  'BlogSidebar.astro must not expose sidebar-close hooks',
);
assert.ok(
  !sidebar.includes('blog-sidebar-header'),
  'BlogSidebar.astro must not render the sidebar brand header',
);
assert.ok(
  !sidebar.includes('sidebarBrand'),
  'BlogSidebar.astro must not keep the removed sidebar brand copy',
);
assert.ok(
  sidebar.includes('mobileMenuInit') || sidebar.includes('blogSidebarInit'),
  'BlogSidebar.astro must guard sidebar initialization against duplicate listeners',
);
assert.ok(
  sidebar.includes('document.body.style.overflow'),
  'BlogSidebar.astro must manage body scroll lock for the mobile sidebar',
);
assert.ok(
  sidebar.includes('data-sidebar-toggle'),
  'BlogSidebar.astro must own the shared mobile toggle wiring',
);
assert.ok(
  sidebar.includes('blog-sidebar-overlay--open'),
  'BlogSidebar.astro must control the shared mobile overlay state',
);

function assertNoPageLevelToggle(relativePath) {
  const source = read(relativePath);
  assert.ok(
    !source.includes('initBlogMobileToggle') && !source.includes('initMobileSidebarToggle'),
    `${relativePath}: page-level mobile sidebar toggle logic must be removed`,
  );
}

assertNoPageLevelToggle('frontend/src/pages/ko/blog/category/[slug].astro');
assertNoPageLevelToggle('frontend/src/pages/en/blog/category/[slug].astro');
assertNoPageLevelToggle('frontend/src/pages/ko/blog/[slug].astro');
assertNoPageLevelToggle('frontend/src/pages/en/blog/[slug].astro');

// The list page (A: serial column) has no sidebar, so no drawer toggle either.
for (const locale of ['ko', 'en']) {
  const index = read(`frontend/src/pages/${locale}/blog/index.astro`);
  assert.ok(
    index.includes('sidebar={false}') && !index.includes('data-sidebar-toggle'),
    `${locale} blog list: no sidebar and no drawer toggle`,
  );
}

const shell = read('frontend/src/components/blog/BlogShell.astro');
assert.ok(
  shell.includes('data-sidebar-overlay'),
  'BlogShell.astro must still render the shared sidebar overlay',
);

console.log('blog-mobile-sidebar-structure.test.cjs passed');
