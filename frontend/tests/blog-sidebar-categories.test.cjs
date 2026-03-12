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

const categories = read('src/lib/categories.ts');
assert(categories.includes("'work-note'"), 'Blog categories must include the work-note slug');
assert(categories.includes("'daily'"), 'Blog categories must include the daily slug');
assert(
  categories.includes("export const BLOG_MAIN_CATEGORIES: BlogCategorySlug[] = ['study', 'project', 'career'];"),
  'Blog categories must define the main posting group in the requested order',
);
assert(
  categories.includes("export const BLOG_SUB_CATEGORIES: BlogCategorySlug[] = ['work-note', 'daily'];"),
  'Blog categories must define the sub posting group',
);
assert(categories.includes("main: { en: 'Main Posts', ko: '\uc8fc\uc694 \uae30\ub85d' }"), 'Blog categories must define the main group label');
assert(categories.includes("sub: { en: 'Small Notes', ko: '\uc791\uc740 \ub178\ud2b8' }"), 'Blog categories must define the sub group label');

const sidebar = read('src/components/blog/BlogSidebar.astro');
const sidebarHelper = read('src/lib/pageData/blogSidebar.ts');
assert(sidebar.includes('getBlogSidebarLabel'), 'Blog sidebar must use sidebar-specific category labels');
assert(sidebar.includes('getBlogCategoryGroupLabel'), 'Blog sidebar must render grouped folder headings from the category model');
assert(sidebarHelper.includes('BLOG_SIDEBAR_VISIBLE_LIMIT = 3;'), 'Blog sidebar must show only 3 recent posts per category before the more button');
assert(sidebarHelper.includes('BLOG_SIDEBAR_SUB_VISIBLE_LIMIT = 1;'), 'Blog sidebar must limit small-note categories to 1 recent post');
assert(sidebarHelper.includes('BLOG_DETAIL_ACTIVE_VISIBLE_LIMIT = 10;'), 'Blog detail sidebar must expand the active category to 10 posts');
assert(sidebarHelper.includes('BLOG_SUB_CATEGORIES.includes'), 'Blog sidebar helper must branch the visible post limit for small-note categories');
assert(sidebar.includes('getBlogSidebarCategoryState'), 'Blog sidebar must delegate category state calculations to the shared helper');
assert(sidebar.includes('blog-sidebar-link__title'), 'Blog sidebar links must clamp a dedicated title wrapper');
assert(sidebar.includes('const CATEGORY_ICONS'), 'Blog sidebar cleanup must define category line icons');
assert(sidebar.includes('blog-folder-icon'), 'Blog sidebar cleanup must render the category icon slot');
assert(!sidebar.includes('blog-folder-dot'), 'Blog sidebar cleanup must remove the category dot marker');

const css = read('src/styles/global.css');
assert(css.includes('.blog-sidebar-link {'), 'Blog sidebar link styles must exist');
assert(css.includes('.blog-sidebar-link__title {'), 'Blog sidebar title clamp styles must exist');
assert(css.includes('-webkit-line-clamp: 2;'), 'Blog sidebar link titles must be clamped to 2 lines');
assert(css.includes('text-overflow: ellipsis;'), 'Blog sidebar link titles must show an ellipsis when truncated');
assert(css.includes('max-height: calc(2 * 1em * var(--blog-sidebar-link-line-height));'), 'Blog sidebar titles must hard-cap the visible height to 2 lines');
assert(css.includes('.blog-folder-icon {'), 'Blog sidebar cleanup must style the category line icons');

const editor = read('src/pages/admin/blog/edit/[slug].astro');
assert(editor.includes("'work-note': 'Work Notes'"), 'Blog editor must define a preview edition for work-note');
assert(editor.includes("daily: 'Daily Life'"), 'Blog editor must define a preview edition for daily');

const migrationPath = path.join(process.cwd(), 'supabase', 'migrations', '20260311_blog_post_subcategories.sql');
assert(fs.existsSync(migrationPath), 'Missing migration for blog post subcategories');

const migration = fs.readFileSync(migrationPath, 'utf8');
assert(migration.includes("'work-note'"), 'Blog post subcategory migration must allow work-note');
assert(migration.includes("'daily'"), 'Blog post subcategory migration must allow daily');

console.log('blog sidebar category structure ok');
