const fs = require('fs');
const path = require('path');
const assert = require('assert');

function read(relativePath) {
  return fs.readFileSync(path.join(process.cwd(), relativePath), 'utf8');
}

const css = read('frontend/src/styles/global.css');

assert.ok(
  css.includes('--blog-shell-header-offset'),
  'Blog shell styles must define a shared header offset variable',
);
assert.ok(
  css.includes('top: calc(var(--blog-shell-header-offset) + var(--blog-shell-rail-gap));'),
  'Desktop blog rails must anchor below the shared header offset',
);
assert.ok(
  css.includes('height: calc(100vh - var(--blog-shell-header-offset) - (var(--blog-shell-rail-gap) * 2));'),
  'Desktop blog sidebar must use the shared viewport height calculation',
);
assert.ok(
  css.includes('border-radius: var(--blog-shell-panel-radius);'),
  'Blog sidebar panel must use the shared card radius',
);
assert.ok(
  css.includes('background: var(--color-bg-secondary);'),
  'Blog sidebar cleanup must use a single-tone sidebar background',
);
assert.ok(
  !css.includes('linear-gradient(180deg, color-mix(in srgb, var(--color-bg-secondary) 92%, white 8%), var(--color-bg-primary))'),
  'Blog sidebar cleanup must remove the sidebar body gradient',
);
assert.ok(
  !css.includes('linear-gradient(180deg, color-mix(in srgb, var(--color-accent-subtle) 65%, transparent), transparent)'),
  'Blog sidebar cleanup must remove the sidebar header gradient',
);
assert.ok(
  css.includes('overflow: hidden;'),
  'Blog sidebar panel must clip chrome and delegate scrolling to the nav',
);
assert.ok(
  css.includes('.blog-mobile-toolbar {'),
  'Blog pages must use a dedicated mobile toolbar wrapper instead of inline styles',
);
assert.ok(
  css.includes('width: min(22rem, calc(100vw - 1.25rem));'),
  'Mobile blog sidebar panel must use the card-style slideout width',
);
assert.ok(
  css.includes('.blog-folder-icon {'),
  'Blog sidebar cleanup must define explicit line-icon styles for categories',
);
assert.ok(
  css.includes('.blog-toc {') && css.includes('top: calc(var(--blog-shell-header-offset) + var(--blog-shell-rail-gap));'),
  'Blog TOC must align with the shared rail offset',
);
assert.ok(
  !css.includes('padding-top: 4rem;'),
  'Legacy hard-coded sidebar padding-top must be removed',
);
assert.ok(
  !css.includes('.blog-sidebar-header {'),
  'Blog sidebar cleanup must remove the sidebar header styles',
);

function assertNoInlineToolbar(relativePath) {
  const source = read(relativePath);
  assert.ok(
    source.includes('class="blog-mobile-toolbar"'),
    `${relativePath}: blog pages must render the shared mobile toolbar wrapper`,
  );
  assert.ok(
    !source.includes('style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;"'),
    `${relativePath}: inline mobile toolbar styles must be removed`,
  );
}

assertNoInlineToolbar('frontend/src/pages/ko/blog/index.astro');
assertNoInlineToolbar('frontend/src/pages/en/blog/index.astro');
assertNoInlineToolbar('frontend/src/pages/ko/blog/[slug].astro');
assertNoInlineToolbar('frontend/src/pages/en/blog/[slug].astro');

console.log('blog-sidebar-layout.test.cjs passed');
