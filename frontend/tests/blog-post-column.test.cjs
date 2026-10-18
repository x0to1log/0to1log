// frontend/tests/blog-post-column.test.cjs
// Blog post A (one column): no sidebar/rail, crumb, byline, contents, inline actions, pager, series list.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

// pages: one column, series position computed once via lib/blogSerial.js
for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/blog/[slug].astro`);
  assert(page.includes(`<BlogShell locale="${locale}">`), `${locale}: post renders in the one-column shell`);
  for (const gone of ['ReadingActionsRail', 'BlogTOC', 'slot="toc"', 'showTOC', 'blog-mobile-toolbar', 'data-sidebar-toggle', 'sidebarPosts', 'nextPost', 'backLabel', 'showStickyActions={false}', 'categories={dbCategories}', 'editionLabel', 'masthead']) {
    assert(!page.includes(gone), `${locale}: ${gone} removed`);
  }
  assert(page.includes("import { locatePost, toSerialProps } from '../../../lib/blogSerial.js';"), `${locale}: serial helpers imported`);
  assert(page.includes(`const serial = toSerialProps(locatePost(recentPosts, dbCategories, pageSlug), dbCategories, '${locale}', post?.category);`), `${locale}: serial computed from the list window`);
  assert(page.includes('serial={serial}'), `${locale}: serial passed to the layout`);
  assert(page.includes("import '../../../scripts/handbook-popup';") && page.includes('id="handbook-terms-data"'), `${locale}: term popup kept`);
}

// data: list query = list page shape, no "next post" query
const loader = read('lib/pageData/blogDetailPage.ts');
assert(!loader.includes(".lt('published_at'"), 'no older-post "next" query');
assert.strictEqual((loader.match(/\.from\('blog_posts'\)/g) || []).length, 3, 'blog_posts queries: post, list window, translation pair');
const listAt = loader.indexOf(".select('title, slug, category, published_at')");
const listQuery = loader.slice(listAt, loader.indexOf('.limit(100)', listAt) + '.limit(100)'.length);
assert(listAt > 0 && listQuery.includes(".eq('status', 'published')") && listQuery.includes(".eq('locale', locale)") && listQuery.includes(".order('created_at', { ascending: false })"), 'list window: published, same locale, created_at desc, 100 (as the list page)');
assert(!loader.includes('blogSidebar') && !loader.includes('nextPost') && !loader.includes('sidebarPosts'), 'no sidebar dataset or next post in the loader');
assert(loader.includes('recentPosts: listRows,'), 'list rows returned for locatePost');

// layout
const layout = read('components/blog/BlogArticleLayout.astro');
for (const gone of ['BlogBreadcrumb', 'blog-article-meta', 'blog-article-category', 'newsprint-article-nav', 'persona-float', 'backLabel', 'nextPost', 'categories', 'normalizeCategorySlug', 'toLocaleDateString', 'placement=']) {
  assert(!layout.includes(gone), `layout: ${gone} removed`);
}
assert(layout.includes('serial: {') && layout.includes('episodes: SerialLink[];') && layout.includes('prev: SerialLink | null;') && layout.includes('next: SerialLink | null;'), 'layout: serial prop');
assert(layout.includes("formatBlogDate(publishedAt, locale, { year: true })"), 'byline date: KST with the year');

const crumbAt = layout.indexOf('<nav class="blog-post-crumb" aria-label={copy.crumb}>');
const crumb = layout.slice(crumbAt, layout.indexOf('</nav>', crumbAt));
assert(crumbAt > 0 && crumb.includes("<a href={`/${locale}/blog/`}>← {t[locale]['blog.title']}</a>"), 'crumb: back to the blog');
assert(crumb.includes('{serial.categoryHref ? <a href={serial.categoryHref}>{serial.categoryLabel}</a> : <span>{serial.categoryLabel}</span>}'), 'crumb: field link, or a label for hidden fields');
assert(crumb.includes('<span>{ep(episode)}</span>'), 'crumb: episode');
for (const s of ["'글 위치'", "'Post location'", '`${n}화`', '`Ep. ${n}`', "'이 글의 차례'", "'In this post'", "'이전·다음 글'", "'Previous and next posts'", "'← 이전 글'", "'← Previous'", "'다음 글 →'", "'Next →'", '`연재 ${total}편 · 전체 보기 →`', "`${total} post${total === 1 ? '' : 's'} · View all →`", "' · 지금 읽는 글'", "' · Reading now'", '`약 ${readingTimeMin}분`', '`${readingTimeMin} min read`', '`${serial.categoryLabel} · ${total}편 중 ${episode}화`', '`${serial.categoryLabel} · Ep. ${episode} of ${total}`']) {
  assert(layout.includes(s), `layout copy: ${s}`);
}
assert(layout.includes('<h1 class="blog-article-title">{title}</h1>') && layout.includes('{excerpt && <p class="blog-post-dek">{excerpt}</p>}'), 'title + dek');
assert(layout.includes('<div class="blog-post-byline">') && layout.includes('<strong>Amy</strong>{dateLabel && ` · ${dateLabel}`}{readingLabel && ` · ${readingLabel}`}'), 'byline: Amy · date · reading time');
assert(layout.includes('{bylineSeries && <span class="blog-category-badge blog-post-byline-series" style={`--cat-color: ${catColor}`}>{bylineSeries}</span>}'), 'byline: series dot label');
assert(layout.includes('<details class="blog-post-toc" hidden>') && layout.includes('<ol class="blog-post-toc-list"></ol>') && layout.includes('<span data-toc-count>0</span>'), 'contents: empty hidden details, filled by the script');

// body + actions: StickyReadingActions is the first child of the article grid, inline (no placement)
const gridAt = layout.indexOf("<div class={`reading-actions-layout ${showStickyActions ? 'reading-actions-layout--article' : ''}`.trim()}>");
assert(gridAt > 0, 'article action grid');
const afterGrid = layout.slice(gridAt).split('\n').slice(1).map((l) => l.trim()).filter(Boolean);
assert.deepStrictEqual(afterGrid.slice(0, 2), ['{showStickyActions && (', '<StickyReadingActions'], 'StickyReadingActions is the first child of the grid');
assert(layout.includes('showStickyActions = true,'), 'inline actions on by default');
assert.strictEqual((layout.match(/<StickyReadingActions/g) || []).length, 1, 'one action bar (one blog bookmark button per page)');

// end blocks, in order, inside the body
const bodyAt = layout.indexOf('<div class="reading-actions-layout__body">');
const order = ['<div class="newsprint-prose', '<div class="blog-tags-footer">', 'class="newsprint-admin-actions"', '<ContentFeedback', '<div data-reading-end></div>', '<nav class="blog-post-pager" aria-label={copy.pager}>', '<aside class="blog-post-series" aria-labelledby="blog-post-series-title">', '<section\n        id="comments"'];
let last = bodyAt;
for (const marker of order) {
  const at = layout.indexOf(marker, last);
  assert(at > last, `end blocks in order: ${marker}`);
  last = at;
}
assert(layout.includes('{(serial.prev || serial.next) && ('), 'pager only with a neighbour');
assert(layout.includes('{serial.prev && (') && layout.includes('<a class="blog-post-pager-link blog-post-pager-link--next"'), 'pager: each card optional, next marked');
assert(layout.includes('{isSeries && (') && layout.includes('<p id="blog-post-series-title" class="blog-post-series-title">{serial.categoryLabel}</p>'), 'series list only for episodes; head is not a heading tag');
assert(layout.includes('<span class="blog-post-series-name" aria-current="page">{item.title}<span class="blog-post-series-now">{copy.readingNow}</span></span>'), 'current episode: text, aria-current');
assert(layout.includes('<a class="blog-post-series-name" href={`${resolvedBasePath}/${item.slug}/`}>{item.title}</a>'), 'other episodes link');
assert(layout.includes('<h2 class="newsprint-comments-title">') && !layout.includes('<h3 class="newsprint-comments-title">'), 'comments heading is an h2');

// contents script: bundled, rebuilt per page load, h2 only, old id rule, no scroll spy
assert(!layout.includes('is:inline'), 'layout scripts are bundled (no nonce needed)');
for (const s of [
  "document.querySelector<HTMLDetailsElement>('details.blog-post-toc')",
  "list.innerHTML = '';",
  "prose.querySelectorAll<HTMLHeadingElement>('h2')",
  'if (headings.length < 2) {',
  "heading.id || slugifyHeading(heading.textContent || '') || `section-${index + 1}`",
  'heading.id = occurrence === 1 ? baseId : `${baseId}-${occurrence}`;',
  "link.textContent = heading.textContent?.trim() || '';",
  "getPropertyValue('--blog-shell-header-offset')",
  "window.scrollTo({ top, behavior: 'smooth' });",
  "toc.open = window.matchMedia('(min-width: 1024px)').matches;",
  "document.addEventListener('astro:page-load', initBlogPostToc);",
]) {
  assert(layout.includes(s), `contents script: ${s}`);
}
assert(!layout.includes('IntersectionObserver'), 'no scroll position highlight');

// CSS
const css = read('styles/global.css');
function rule(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const all = [...css.matchAll(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`, 'g'))].map((m) => m[1]);
  assert(all.length > 0, `missing CSS rule ${selector}`);
  return all[all.length - 1];
}
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.blog-post-byline')) && /border-bottom:\s*1px solid var\(--color-text-primary\)/.test(rule('.blog-post-byline')) && /justify-content:\s*space-between/.test(rule('.blog-post-byline')), 'byline: 2px ink rule above, 1px below, both ends');
assert(rule('.blog-post-toc').includes('var(--color-bg-secondary)'), 'contents on the secondary surface');
assert(rule('.blog-post-toc[hidden]').includes('display: none'), 'hidden contents stay hidden');
assert(/grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\)/.test(rule('.blog-post-pager')), 'pager: 2 cards');
assert(/grid-column:\s*2/.test(rule('.blog-post-pager-link--next')), 'next card stays on the right');
assert(rule('.blog-post-pager-title').includes('var(--font-blog-heading)') && /font-weight:\s*600/.test(rule('.blog-post-pager-title')), 'pager title Hahmlet 600');
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.blog-post-series-head')), 'series head: 2px ink rule');
assert(rule('.blog-post-series-ep').includes('var(--font-masthead)'), 'episode number in Newsreader');
const desktopAt = css.indexOf('/* Blog post A: desktop */');
const desktop = css.slice(desktopAt, css.indexOf('\n}\n', desktopAt));
assert(desktopAt > 0 && desktop.includes('@media (min-width: 1024px)') && /\.blog-post-toc-list\s*\{[^}]*columns:\s*2/.test(desktop), 'desktop: contents in 2 columns');
const mobileAt = css.indexOf('/* Blog post A: mobile */');
const mobile = css.slice(mobileAt, css.indexOf('\n}\n', mobileAt));
assert(mobileAt > 0 && mobile.includes('@media (max-width: 767px)'), 'blog post mobile block');
assert(/\.blog-post-byline\s*\{[^}]*flex-wrap:\s*wrap/.test(mobile), 'mobile: byline wraps');
assert(/\.blog-post-pager\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/.test(mobile), 'mobile: pager one column');
assert(/\.blog-post-pager-link--next\s*\{[^}]*grid-column:\s*auto/.test(mobile), 'mobile: next card in flow');
// shared action bar: right 72px column from 1024px (no blog-only override)
assert(css.includes('  .reading-actions-layout--article {\n    display: grid;\n    grid-template-columns: minmax(0, 1fr) 72px;'), 'shared desktop action column');
assert(!/\.blog-[\w-]*\s+\.reading-actions-layout/.test(css), 'no blog-only action layout override');

// removed with the rail (Task 3): blog-detail-only components, the rail placement and their CSS
for (const file of ['components/blog/BlogTOC.astro', 'components/blog/BlogBreadcrumb.astro', 'components/common/ReadingActionsRail.astro']) {
  assert(!fs.existsSync(path.join(src, file)), `${file} deleted`);
}
assert(!read('components/common/StickyReadingActions.astro').includes('placement'), 'StickyReadingActions: no rail placement');
for (const gone of ['.blog-toc', '.blog-rail', '.blog-breadcrumb', '.blog-article-meta', '.blog-article-category', '.reading-actions-rail', '.reading-actions--rail-placement', '.newsprint-article-nav', '.newsprint-nav-']) {
  assert(!css.includes(gone), `unused CSS removed: ${gone}`);
}
// still used elsewhere: news/handbook layouts and handbook-popup.ts (persona float)
for (const kept of ['.persona-float {', '.persona-float--back', '.blog-article-title {', '.blog-article-header {', '.blog-shell .newsprint-comments-title {']) {
  assert(css.includes(kept), `CSS kept: ${kept}`);
}
assert(!read('i18n/index.ts').includes("'blog.onThisPage'"), 'unused i18n key removed');

console.log('blog-post-column.test.cjs passed');
