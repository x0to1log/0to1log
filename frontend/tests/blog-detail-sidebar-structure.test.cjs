const fs = require('fs');
const path = require('path');

function read(filePath) {
  return fs.readFileSync(path.join(__dirname, '..', filePath), 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const helperPath = path.join(__dirname, '..', 'src', 'lib', 'pageData', 'blogSidebar.ts');
assert(fs.existsSync(helperPath), 'Blog detail sidebar must define a shared sidebar helper module');

const helper = read('src/lib/pageData/blogSidebar.ts');
assert(helper.includes('buildBlogSidebarDataset'), 'Shared sidebar helper must expose a dataset builder');
assert(helper.includes('getBlogSidebarCategoryState'), 'Shared sidebar helper must expose category display state');
assert(helper.includes('getBlogSidebarGroupExpanded'), 'Shared sidebar helper must expose group expansion logic');

// Blog post A (2026-10-17): the post page has no sidebar. Its list window feeds locatePost (series position),
// so it keeps the current post and the list page's 100-post window.
const detailLoader = read('src/lib/pageData/blogDetailPage.ts');
assert(!detailLoader.includes("from './blogSidebar'"), 'Blog detail loader must not build a sidebar dataset');
assert(!detailLoader.includes('.limit(4)') && detailLoader.includes('.limit(100)'), 'Blog detail list window must match the list page (100 posts)');
assert(!detailLoader.includes(".neq('slug', pageSlug)"), 'Blog detail list window must not exclude the current slug');

const blogShell = read('src/components/blog/BlogShell.astro');
assert(blogShell.includes('mode?: BlogSidebarMode;'), 'Blog shell must expose an explicit sidebar mode prop');
assert(blogShell.includes('currentCategory?: string;'), 'Blog shell must expose the current category prop');
assert(blogShell.includes('mode={mode}'), 'Blog shell must pass the sidebar mode through to BlogSidebar');
assert(blogShell.includes('currentCategory={currentCategory}'), 'Blog shell must pass the current category through to BlogSidebar');

const koDetail = read('src/pages/ko/blog/[slug].astro');
assert(koDetail.includes('sidebar={false}') && !koDetail.includes('mode="detail"'), 'Korean blog detail page must render without the sidebar');

const enDetail = read('src/pages/en/blog/[slug].astro');
assert(enDetail.includes('sidebar={false}') && !enDetail.includes('mode="detail"'), 'English blog detail page must render without the sidebar');

// The list page (A: serial column) renders without the sidebar; category pages keep it in index mode.
const koIndex = read('src/pages/ko/blog/index.astro');
assert(koIndex.includes('sidebar={false}') && !koIndex.includes('mode="index"'), 'Korean blog list page must render without the sidebar');

const enIndex = read('src/pages/en/blog/index.astro');
assert(enIndex.includes('sidebar={false}') && !enIndex.includes('mode="index"'), 'English blog list page must render without the sidebar');

for (const locale of ['ko', 'en']) {
  const categoryPage = read(`src/pages/${locale}/blog/category/[slug].astro`);
  assert(categoryPage.includes('mode="index"') && categoryPage.includes('currentCategory={slug}'), `${locale} blog category page must keep the index-mode sidebar`);
}

console.log('blog detail sidebar structure ok');
