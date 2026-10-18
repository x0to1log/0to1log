// frontend/tests/blog-category-toc.test.cjs
// Blog field page A (series table of contents): one column, crumb, title, byline, rows with summaries, other fields.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

const COPY = {
  ko: {
    crumbAria: 'aria-label="분야 위치"', back: '← IT 블로그', series: "'연재'", notes: "'짧은 글'",
    seriesByline: '연재 {count}편</span>{period && ` · ${period}`}', notesByline: '짧은 글 {count}편{lastDate && ` · 마지막 글 ${lastDate}`}',
    start: '1화부터 읽기 →', othersAria: 'aria-label="다른 분야"', others: '>다른 분야</span>',
    empty: ['<h2>아직 작성된 글이 없습니다</h2>', '<p>곧 새 글이 올라올 거예요.</p>'],
  },
  en: {
    crumbAria: 'aria-label="Field location"', back: '← IT Blog', series: "'Series'", notes: "'Short notes'",
    seriesByline: '{count}-part series</span>{period && ` · ${period}`}', notesByline: "{count} short note{count === 1 ? '' : 's'}{lastDate && ` · Latest ${lastDate}`}",
    start: 'Start from Ep. 1 →', othersAria: 'aria-label="Other fields"', others: '>Other fields</span>',
    empty: ['<h2>No posts yet</h2>', '<p>New posts coming soon.</p>'],
  },
};

// field pages
for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/blog/category/[slug].astro`);
  const c = COPY[locale];
  for (const gone of ['BlogSidebar', 'blogSidebar', 'BlogCategoryHeader', 'BlogListItem', 'blog-mobile-toolbar', 'data-sidebar-toggle', 'data-blog-sentinel', 'data-blog-batch', 'IntersectionObserver', 'isAdmin', 'fetchCategoryGroups', 'is:inline', ".eq('category'", 'Astro.locals.user']) {
    assert(!page.includes(gone), `${locale}: ${gone} removed`);
  }
  // access: redirect without slug/DB, 404 for a missing or hidden field (no admin branch: shared-cache path)
  assert(page.includes(`return Astro.redirect('/${locale}/blog/');`), `${locale}: redirect without slug or DB`);
  assert(page.includes('if (!category || !category.is_visible) {\n  return new Response(null, { status: 404 });'), `${locale}: missing or hidden field → 404`);
  // data: same posts query as the list and post pages
  const queryAt = page.indexOf(".from('blog_posts')");
  const query = page.slice(queryAt, page.indexOf('.limit(100)', queryAt) + '.limit(100)'.length);
  assert(queryAt > 0 && query.includes(".select('id, title, slug, category, published_at, excerpt')") && query.includes(".eq('status', 'published')") && query.includes(".eq('locale', locale)") && query.includes(".order('created_at', { ascending: false })"), `${locale}: posts query = list page shape (published, locale, created_at desc, 100)`);
  assert(page.includes("import { categoryPage, formatBlogDate } from '../../../../lib/blogSerial.js';") && page.includes('const page = categoryPage(postsRes.data ?? [], dbCategories, slug);'), `${locale}: rows from categoryPage`);
  assert(page.includes("import { fetchCategories, fetchCategoryBySlug } from '../../../../lib/pageData/blogCategories';"), `${locale}: field + field list queries only`);
  // fetch failure: 503 + notice (never a cacheable 200 empty state)
  assert(/if \(fetchError\)\s*\{?\s*Astro\.response\.status = 503/.test(page), `${locale}: 503 on posts query error`);
  assert(page.includes(`<NewsprintNotice variant="error" message={t.${locale}['blog.error']}`), `${locale}: error notice`);
  // layout
  assert(page.includes(`<BlogShell locale="${locale}">`), `${locale}: one-column shell`);
  assert(page.includes(`<nav class="blog-cat-crumb" ${c.crumbAria}>`) && page.includes(`<a href="/${locale}/blog/">${c.back}</a>`), `${locale}: crumb back to the blog`);
  assert(page.includes(c.series) && page.includes(c.notes), `${locale}: kind label in the crumb`);
  assert(page.includes('<h1 class="blog-cat-title">{categoryLabel}</h1>') && page.includes('{categoryDesc && <p class="blog-cat-desc">{categoryDesc}</p>}'), `${locale}: h1 + description only when present`);
  assert(page.includes('{count > 0 ? (') && page.includes('<div class="blog-cat-byline">'), `${locale}: byline only with posts`);
  assert(page.includes(c.seriesByline) && page.includes(c.notesByline), `${locale}: byline copy`);
  assert(page.includes("const period = firstDate && firstDate !== lastDate ? `${firstDate} ~ ${lastDate}` : lastDate;"), `${locale}: one date when the period is a single day`);
  assert(page.includes(`<a class="blog-cat-start" href={\`/${locale}/blog/\${page.posts[0].slug}/\`}>${c.start}</a>`), `${locale}: start from episode 1`);
  assert(page.includes("<ol class:list={['blog-serial-list', 'blog-cat-list', { 'blog-cat-list--series': isSeries }]}>"), `${locale}: rows reuse the list page row grid`);
  assert(page.includes(`<BlogSerialItem locale="${locale}" post={post} episode={isSeries ? i + 1 : undefined} excerpt={post.excerpt} />`), `${locale}: BlogSerialItem with episode (series) and excerpt, no field label`);
  assert(page.includes(`<nav class="blog-cat-others" ${c.othersAria}>`) && page.includes(c.others), `${locale}: other fields`);
  assert(page.includes('const others = dbCategories.filter((c) => c.is_visible && c.slug !== slug);') && page.includes('{page.counts[c.slug] ?? 0}'), `${locale}: visible fields except this one, with counts`);
  assert(page.includes('<div class="blog-empty-state">') && page.includes('<div class="blog-empty-icon">📝</div>') && c.empty.every((s) => page.includes(s)), `${locale}: empty state copy kept`);
  assert(page.includes("<script>\n  import '../../../../scripts/bookmark';\n</script>"), `${locale}: bundled bookmark + content-status script`);
}

// row: optional summary after the title link (title string unchanged for the list page tests/search)
const item = read('components/blog/BlogSerialItem.astro');
assert(item.includes('excerpt?: string | null;') && item.includes('const { locale, post, episode, categoryLabel, categoryColor, excerpt } = Astro.props;'), 'row: excerpt prop');
assert(item.includes('<a class="blog-serial-title" href={`/${locale}/blog/${post.slug}/`}>{post.title}</a>\n  {excerpt && <p class="blog-serial-excerpt">{excerpt}</p>}'), 'row: summary right after the title');
const li = item.slice(item.indexOf('<li class="blog-list-item">'), item.indexOf('</li>'));
assert((li.match(/class="newsprint-bookmark-icon"/g) || []).length === 1, 'row: one bookmark button inside the li');

// shell: always one column, no sidebar props
const shell = read('components/blog/BlogShell.astro');
assert(shell.includes('<div class="blog-shell blog-shell--single">'), 'shell: single column always');
for (const gone of ['BlogSidebar', 'blogSidebar', 'sidebar?:', 'sidebarPosts', 'currentSlug', 'currentCategory', 'totalCount', 'mode', 'showTOC', 'slot name="toc"', 'data-sidebar-overlay', 'class:list']) {
  assert(!shell.includes(gone), `shell: ${gone} removed`);
}
for (const p of ['index.astro', '[slug].astro', 'category/[slug].astro']) {
  for (const locale of ['ko', 'en']) {
    const page = read(`pages/${locale}/blog/${p}`);
    assert(page.includes(`<BlogShell locale="${locale}">`) && !page.includes('sidebar='), `${locale}/blog/${p}: BlogShell without sidebar props`);
    assert(!page.includes('data-sidebar-toggle') && !page.includes('initBlogMobileToggle') && !page.includes('initMobileSidebarToggle'), `${locale}/blog/${p}: no drawer toggle`);
  }
}

// moved from blog-detail-sidebar-structure: the post page list window feeds locatePost (same 100-post window as the list)
const detailLoader = read('lib/pageData/blogDetailPage.ts');
assert(!detailLoader.includes("from './blogSidebar'"), 'Blog detail loader must not build a sidebar dataset');
assert(!detailLoader.includes('.limit(4)') && detailLoader.includes('.limit(100)'), 'Blog detail list window must match the list page (100 posts)');
assert(!detailLoader.includes(".neq('slug', pageSlug)"), 'Blog detail list window must not exclude the current slug');

// CSS
const css = read('styles/global.css');
function rule(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const all = [...css.matchAll(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`, 'g'))].map((m) => m[1]);
  assert(all.length > 0, `missing CSS rule ${selector}`);
  return all[all.length - 1];
}
assert(/max-width:\s*820px/.test(rule('.blog-shell--single .blog-main-inner')), 'one column up to 820px');
assert(rule('.blog-cat-title').includes('var(--font-blog-heading)') && /font-weight:\s*700/.test(rule('.blog-cat-title')) && /font-size:\s*2\.5rem/.test(rule('.blog-cat-title')), 'title: Hahmlet 700, 2.5rem');
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.blog-cat-byline')) && /border-bottom:\s*1px solid var\(--color-text-primary\)/.test(rule('.blog-cat-byline')) && /justify-content:\s*space-between/.test(rule('.blog-cat-byline')), 'byline: 2px ink rule above, 1px below, both ends');
assert(rule('.blog-cat-list--series > .blog-list-item:first-child .blog-serial-ep').includes('color: var(--color-accent)'), 'episode 1 in the accent color');
assert(/grid-column:\s*2;/.test(rule('.blog-serial-excerpt')) && /grid-row:\s*2;/.test(rule('.blog-serial-excerpt')) && /-webkit-line-clamp:\s*2/.test(rule('.blog-serial-excerpt')), 'summary: title column, second row, two lines');
assert(/grid-template-columns:\s*minmax\(0, 1fr\) auto auto/.test(rule('.blog-cat-list:not(.blog-cat-list--series) .blog-list-item')) && rule('.blog-cat-list:not(.blog-cat-list--series) .blog-serial-cat').includes('display: none') && /grid-column:\s*1;/.test(rule('.blog-cat-list:not(.blog-cat-list--series) .blog-serial-excerpt')), 'short notes: no empty first cell (title flush left, summary under it)');
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.blog-cat-others')) && /flex-wrap:\s*wrap/.test(rule('.blog-cat-others-list')), 'other fields: ink rule, wrapping links');
const mobileAt = css.indexOf('/* Blog field page A: mobile */');
assert(mobileAt > 0, 'field page mobile block');
const mobile = css.slice(mobileAt, css.indexOf('\n}\n', mobileAt));
assert(/\.blog-cat-title\s*\{[^}]*font-size:\s*1\.9rem/.test(mobile), 'mobile: title 1.9rem');
for (const kept of ['.blog-list-item {', '.blog-list-item:hover {', '.blog-list-item--read {', '.blog-category-badge {', '.blog-empty-state {', '.blog-empty-icon {']) {
  assert(css.includes(kept), `CSS kept: ${kept}`);
}

// removed with the sidebar (Task 3): components, the sidebar helper, their CSS and i18n key
for (const file of ['components/blog/BlogSidebar.astro', 'lib/pageData/blogSidebar.ts', 'components/blog/BlogCategoryHeader.astro', 'components/blog/BlogListItem.astro']) {
  assert(!fs.existsSync(path.join(src, file)), `${file} deleted`);
}
for (const gone of ['.blog-sidebar', '.blog-folder', '.blog-mobile-toolbar', '.blog-mobile-toggle', '.blog-category-header', '.blog-category-banner', '.blog-category-title', '.blog-category-icon', '.blog-category-description', '.blog-category-count', '.blog-list-section', '.blog-list-batch', '.blog-scroll-sentinel', '--blog-shell-rail-gap', '--blog-shell-panel-radius']) {
  assert(!css.includes(gone), `unused CSS removed: ${gone}`);
}
assert(!/\.blog-list-item-[a-z]/.test(css), 'unused CSS removed: BlogListItem parts (.blog-list-item-title, -meta, …; .blog-list-item--read stays)');
assert(css.includes('--blog-shell-header-offset: 5rem;'), 'header offset kept (BlogArticleLayout reads it)');
assert(/@media \(max-width: 1023px\) \{\n  \.blog-shell \{\n    display: block;\n    min-height: auto;\n  \}\n\}/.test(css), '1023px block keeps only the shared shell rule');
assert(!read('i18n/index.ts').includes("'blog.allPostsCount'"), 'sidebar-only i18n key removed');
for (const gone of ['blog-detail-sidebar-behavior.test.mjs', 'blog-detail-sidebar-structure.test.cjs', 'blog-mobile-sidebar-structure.test.cjs', 'blog-sidebar-categories.test.cjs', 'blog-sidebar-layout.test.cjs']) {
  assert(!fs.existsSync(path.join(__dirname, gone)), `deleted: tests/${gone}`);
}

console.log('blog-category-toc.test.cjs passed');
