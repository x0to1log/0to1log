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

const detailLoader = read('src/lib/pageData/blogDetailPage.ts');
assert(detailLoader.includes("from './blogSidebar'"), 'Blog detail loader must reuse the shared sidebar helper');
assert(!detailLoader.includes('.limit(4)'), 'Blog detail sidebar dataset must not be limited to 4 recent posts');
assert(!detailLoader.includes(".neq('slug', pageSlug)"), 'Blog detail sidebar dataset must not exclude the current slug');

const blogShell = read('src/components/blog/BlogShell.astro');
assert(blogShell.includes('mode?: BlogSidebarMode;'), 'Blog shell must expose an explicit sidebar mode prop');
assert(blogShell.includes('currentCategory?: string;'), 'Blog shell must expose the current category prop');
assert(blogShell.includes('mode={mode}'), 'Blog shell must pass the sidebar mode through to BlogSidebar');
assert(blogShell.includes('currentCategory={currentCategory}'), 'Blog shell must pass the current category through to BlogSidebar');

const koDetail = read('src/pages/ko/blog/[slug].astro');
assert(koDetail.includes('mode="detail"'), 'Korean blog detail page must render sidebar in detail mode');
assert(koDetail.includes('currentCategory={post?.category}'), 'Korean blog detail page must pass the current post category to the sidebar');

const enDetail = read('src/pages/en/blog/[slug].astro');
assert(enDetail.includes('mode="detail"'), 'English blog detail page must render sidebar in detail mode');
assert(enDetail.includes('currentCategory={post?.category}'), 'English blog detail page must pass the current post category to the sidebar');

const koIndex = read('src/pages/ko/blog/index.astro');
assert(koIndex.includes('mode="index"'), 'Korean blog list page must render sidebar in index mode');

const enIndex = read('src/pages/en/blog/index.astro');
assert(enIndex.includes('mode="index"'), 'English blog list page must render sidebar in index mode');

console.log('blog detail sidebar structure ok');
