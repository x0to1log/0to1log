// frontend/tests/blog-list-serial.test.cjs
// Blog list A (serial column): no sidebar, byline + search, latest post, series, short notes.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

// shell: always one column (blog field A, 2026-10-18: the field pages lost the sidebar too, so the prop is gone)
const shell = read('components/blog/BlogShell.astro');
assert(shell.includes('<div class="blog-shell blog-shell--single">') && !shell.includes('BlogSidebar') && !shell.includes('sidebar?:'), 'shell: one column, no sidebar prop');
for (const p of ['pages/ko/blog/[slug].astro', 'pages/en/blog/[slug].astro', 'pages/ko/blog/category/[slug].astro', 'pages/en/blog/category/[slug].astro']) {
  assert(!read(p).includes('sidebar='), `${p}: no sidebar prop`);
}

// pages
for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/blog/index.astro`);
  assert(page.includes(`<BlogShell locale="${locale}">`), `${locale}: list renders in the one-column shell`);
  for (const gone of ['BlogFeaturedCard', 'BlogListItem', 'data-blog-sentinel', 'blog-category-tabs', 'blog-mobile-toolbar', 'data-sidebar-toggle', 'buildBlogSidebarDataset', 'IntersectionObserver', "'blog.featured'", "'blog.allPosts'"]) {
    assert(!page.includes(gone), `${locale}: ${gone} removed`);
  }
  assert(page.includes(".select('id, title, slug, category, published_at, tags, reading_time_min, excerpt')") && page.includes(".order('created_at', { ascending: false })") && page.includes('.limit(100)'), `${locale}: posts query unchanged`);
  assert(page.includes('const front = buildBlogFront(posts, dbCategories);'), `${locale}: front built by the pure module`);
  assert(page.includes(`<BlogFront locale="${locale}" front={front} categories={dbCategories} />`), `${locale}: renders BlogFront`);
  assert(page.includes(') : front.total > 0 ? (') && page.includes('<div class="blog-empty-state">'), `${locale}: empty state when there are no posts`);
  assert(page.includes("import '../../../scripts/bookmark';"), `${locale}: bookmark + content-status hydration`);
  assert(page.includes('<h1 class="blog-masthead-title">–도록: do log</h1>') && page.includes('class="blog-masthead-tagline"'), `${locale}: masthead kept`);
}
assert(read('pages/ko/blog/index.astro').includes('<h2>준비 중</h2>') && read('pages/en/blog/index.astro').includes('<h2>Coming Soon</h2>'), 'empty state copy kept');
assert(!fs.existsSync(path.join(src, 'components/blog/BlogFeaturedCard.astro')), 'BlogFeaturedCard deleted');
const i18n = read('i18n/index.ts');
assert(!i18n.includes("'blog.featured'") && !i18n.includes("'blog.allPosts'") && i18n.includes("'blog.allPostsCount'"), 'unused i18n keys removed (sidebar count key kept)');

// front: byline, lead, series, short notes, search
const front = read('components/blog/BlogFront.astro');
for (const s of ["'마지막 글'", "'Latest'", "'글 검색'", "'Search posts'", "'최신'", "'개의 연재'", "'series'", "'짧은 글'", "'Short notes'", "'일치하는 글이 없어요'", "'No posts match'", '`${n}편`', "`${n} post${n === 1 ? '' : 's'}`", '`${label} ${s.posts.length}편`', '`${label} · ${s.posts.length}`']) {
  assert(front.includes(s), `front copy: ${s}`);
}
assert(front.includes('<div class="blog-byline">') && front.includes('<strong>Amy</strong> · {postsLabel(front.total)}{latest && ` · ${copy.latest} ${latest}`}'), 'byline: Amy · N · latest date');
assert(front.includes('<input type="search" id="blog-search" class="blog-search-input" placeholder={copy.search} aria-label={copy.search} autocomplete="off" />'), 'search input');

assert(front.includes('{front.lead && ('), 'lead guarded: posts without published_at give lead null while total > 0');
const leadAt = front.indexOf("<section class:list={['blog-lead'");
const lead = front.slice(leadAt, front.indexOf('</section>', leadAt));
assert(leadAt > 0 && lead.includes('<h2 class="blog-lead-title">'), 'lead title is an h2');
assert(lead.includes('{front.lead.excerpt && <p class="blog-lead-excerpt">{front.lead.excerpt}</p>}'), 'lead excerpt only when present');
assert(!lead.includes('newsprint-bookmark-icon') && !lead.includes('<BlogSerialItem'), 'no bookmark button in the lead block');
assert(lead.includes("{ 'blog-lead--solo': front.series.length === 0 }") && lead.includes('{front.series.length > 0 && ('), 'series summary only with series');

assert(front.includes('<article class="blog-series">') && front.includes('<h2 class="blog-series-title"><a href={`/${locale}/blog/category/${category.slug}/`}>{label}</a></h2>'), 'series heading links to the field page');
assert(front.includes('{desc && <p class="blog-series-desc">{desc}</p>}'), 'series description only when present');
assert(front.includes('<BlogSerialItem locale={locale} post={post} episode={i + 1} />'), 'episodes numbered from 1');
assert(front.includes('{front.shortNotes.length > 0 && (') && front.includes('<h2 class="blog-short-notes-title">{copy.short}</h2>'), 'short notes h2, hidden when empty');
assert((front.match(/<ol class="blog-serial-list">/g) || []).length === 2, 'series and short notes are ordered lists');
assert(front.includes('<p id="blog-search-empty" class="blog-search-empty" role="status" aria-live="polite" hidden>{copy.empty}</p>'), 'no-results status');

// search script: bundled (no nonce needed), guarded, debounced, restores everything when cleared
assert(!front.includes('is:inline'), 'search script is bundled');
for (const s of [
  "input.dataset.blogSearchReady === 'true'",
  "input.dataset.blogSearchReady = 'true';",
  "document.addEventListener('astro:page-load', initBlogSearch);",
  'timer = window.setTimeout(apply, 150);',
  "front.querySelectorAll<HTMLElement>('.blog-series, .blog-short-notes')",
  "item.querySelector('.blog-serial-title')?.textContent",
  'item.hidden = !match;',
  'group.hidden = visible === 0;',
  'lead.hidden = query.length > 0;',
  'empty.hidden = !query || shown > 0;',
]) {
  assert(front.includes(s), `search script: ${s}`);
}

// row: li.blog-list-item with the bookmark button inside (content-status marks the closest .blog-list-item read)
const item = read('components/blog/BlogSerialItem.astro');
const li = item.slice(item.indexOf('<li class="blog-list-item">'), item.indexOf('</li>'));
assert(li.length > 0 && li.includes('class="newsprint-bookmark-icon"') && li.includes('data-item-id={post.id}') && li.includes('data-item-type="blog"') && li.includes('data-bookmarked="false"'), 'bookmark contract inside li.blog-list-item');
assert(!item.includes('blog-list-item-icon'), 'no icon slot');
assert(item.includes('`${episode}화`') && item.includes('`Ep. ${episode}`'), 'episode labels');
assert(item.includes('<a class="blog-serial-title" href={`/${locale}/blog/${post.slug}/`}>{post.title}</a>'), 'title link');
assert(item.includes('style={`--cat-color: ${categoryColor || \'var(--color-border)\'}`}'), 'short note dot label uses the DB color');

// KST everywhere: components only format through formatBlogDate
assert(read('lib/blogSerial.js').includes("timeZone: 'Asia/Seoul'"), 'dates in KST');
for (const [name, f] of [['BlogFront', front], ['BlogSerialItem', item]]) {
  assert(!f.includes('toLocaleDateString') && f.includes('formatBlogDate('), `${name}: dates via formatBlogDate`);
}

// CSS
const css = read('styles/global.css');
function rule(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const all = [...css.matchAll(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`, 'g'))].map((m) => m[1]);
  assert(all.length > 0, `missing CSS rule ${selector}`);
  return all[all.length - 1];
}
assert(/max-width:\s*820px/.test(rule('.blog-shell--single .blog-main-inner')), 'single column up to 820px');
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.blog-byline')) && /border-bottom:\s*1px solid var\(--color-text-primary\)/.test(rule('.blog-byline')), 'byline: 2px ink rule above, 1px below');
assert(/grid-template-columns:\s*minmax\(0, 1fr\) 200px/.test(rule('.blog-lead')), 'lead: 1fr : 200px');
assert(/border-left:\s*1px solid var\(--color-border\)/.test(rule('.blog-lead-aside')), 'series summary has a left rule');
assert(/grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\)/.test(rule('.blog-series-grid')), 'series: 2 columns');
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.blog-series-head')), 'series head: 2px ink rule');
for (const sel of ['.blog-lead-title', '.blog-series-title', '.blog-short-notes-title']) {
  assert(rule(sel).includes('var(--font-blog-heading)') && /font-weight:\s*700/.test(rule(sel)), `${sel}: Hahmlet 700`);
}
assert(rule('.blog-serial-ep').includes('var(--font-masthead)'), 'episode number in Newsreader');
assert(/font-weight:\s*600/.test(rule('.blog-serial-title')), 'episode title 600');
assert(rule('.blog-front [hidden]').includes('display: none'), 'search hides grid rows (display: grid beats the UA [hidden] rule)');
const mobileAt = css.indexOf('/* Blog list A: mobile */');
assert(mobileAt > 0, 'blog list mobile block');
const mobile = css.slice(mobileAt, css.indexOf('\n}\n', mobileAt));
assert(/\.blog-byline\s*\{[^}]*flex-wrap:\s*wrap/.test(mobile), 'mobile: byline wraps');
assert(/\.blog-search-input\s*\{[^}]*width:\s*100%/.test(mobile), 'mobile: search on its own full-width line');
assert(/\.blog-lead\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/.test(mobile), 'mobile: lead one column');
assert(/\.blog-series-grid\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/.test(mobile), 'mobile: series one column');

// unused CSS removed (Task 3): featured cards, list-page tabs and section headers were list-only
for (const gone of ['.blog-featured-', '.blog-category-tab', '.blog-section-header', 'Blog Masthead Tagline + Category Tabs']) {
  assert(!css.includes(gone), `unused CSS removed: ${gone}`);
}
// still used by the category pages / article layout
for (const kept of ['.blog-list-batch[hidden] {', '.blog-scroll-sentinel {', '.blog-mobile-toolbar {', '.blog-list-section {', '.blog-mono-tag {', '.blog-category-badge {', '.blog-masthead-tagline {']) {
  assert(css.includes(kept), `CSS kept: ${kept}`);
}

console.log('blog-list-serial.test.cjs passed');
