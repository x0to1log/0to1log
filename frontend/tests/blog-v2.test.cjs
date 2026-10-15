// frontend/tests/blog-v2.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');
const css = read('styles/global.css');
function rules(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return [...css.matchAll(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`, 'g'))].map((m) => m[1]);
}
function rule(selector) {
  const all = rules(selector);
  assert(all.length > 0, `missing CSS rule ${selector}`);
  return all[all.length - 1];
}

// Task 1: 카테고리 색은 점에만
for (const p of ['components/blog/BlogFeaturedCard.astro', 'components/blog/BlogListItem.astro']) {
  const f = read(p);
  assert(!/style=\{`background:/.test(f) && !/style=\{`color:/.test(f), `${p} has no inline badge/tag colors`);
  assert(f.includes('--cat-color:'), `${p} passes the category color as --cat-color only`);
}
const badge = rule('.blog-category-badge');
assert(/background:\s*none/.test(badge) && !/var\(--cat-color/.test(badge), 'badge text/background do not use the category color');
assert(css.includes('.blog-category-badge::before {') && rule('.blog-category-badge::before').includes('var(--cat-color, var(--color-accent))'), 'category color lives only on the dot');
assert(!/style=\{`color:/.test(read('components/blog/BlogSidebar.astro')), 'sidebar folder icon has no inline color');

// 카드 → 칼럼 목록
const feat = rule('.blog-featured-card');
assert(/border:\s*none/.test(feat) && /border-bottom:\s*1px dotted var\(--color-border\)/.test(feat), 'featured posts are dotted column entries');
assert(/border-bottom:\s*1px dotted var\(--color-border\)/.test(rule('.blog-list-item')), 'list items separated by dotted lines');

// 폴더 카드 줄 → 탭
for (const p of ['pages/ko/blog/index.astro', 'pages/en/blog/index.astro']) {
  const f = read(p);
  assert(f.includes('class="blog-category-tabs"'), `${p} renders category tabs`);
  assert(!f.includes('blog-category-showcase-card'), `${p} drops the folder cards`);
  assert(f.includes('blog-masthead-tagline'), `${p} has the masthead tagline`);
  assert(!f.includes('CATEGORY_ICONS'), `${p} drops the unused showcase icon map`);
}
assert(read('pages/en/blog/index.astro').includes('A column on building, learning and keeping notes'), 'en tagline');
assert(/@media \(max-width: 1023px\)\s*\{[\s\S]*?\.blog-sidebar\s*\{[^}]*background:\s*var\(--color-bg-primary\)/.test(css), 'mobile sidebar drawer keeps an opaque background');

// 사이드바 패널 정리
const sidebar = rule('.blog-sidebar');
assert(/box-shadow:\s*none/.test(sidebar) && /border-radius:\s*0/.test(sidebar), 'sidebar is not a floating rounded panel');
assert(!rule('.blog-folder-btn--group').includes('uppercase'), 'sidebar group labels not uppercase');

// Task 2: 상세
const layout = read('components/blog/BlogArticleLayout.astro');
assert(!layout.includes('📘') && !layout.includes('blog-article-icon'), 'hardcoded 📘 article icon removed');
assert(layout.includes('data-admin-only') && layout.includes('newsprint-comments') && layout.includes('data-comment-form') && layout.includes('ContentFeedback') && layout.includes('id="persona-data"'), 'blog article keeps admin/comments/feedback/persona hooks');
assert(/class="blog-article-category"[^>]*--cat-color/.test(layout), 'article meta shows the category as a color dot label');
assert(!/style=\{`background:/.test(layout), 'article tags have no inline colors');
assert(/font-weight:\s*700/.test(rule('.blog-article-title')), 'article title 700');
assert(!rule('.blog-toc-header').includes('uppercase'), 'toc header not uppercase');
for (const p of ['pages/ko/blog/[slug].astro', 'pages/en/blog/[slug].astro']) {
  const f = read(p);
  assert(f.includes('onSessionReady') && f.includes('recordReadingHistory') && f.includes('handbook-terms-data'), `${p} keeps session/reading-history/terms hooks`);
}

console.log('blog-v2.test.cjs passed');
