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
for (const p of ['components/blog/BlogSerialItem.astro']) {
  const f = read(p);
  assert(!/style=\{`background:/.test(f) && !/style=\{`color:/.test(f), `${p} has no inline badge/tag colors`);
  assert(f.includes('--cat-color:'), `${p} passes the category color as --cat-color only`);
}
const badge = rule('.blog-category-badge');
assert(/background:\s*none/.test(badge) && !/var\(--cat-color/.test(badge), 'badge text/background do not use the category color');
assert(css.includes('.blog-category-badge::before {') && rule('.blog-category-badge::before').includes('var(--cat-color, var(--color-accent))'), 'category color lives only on the dot');

// 카드 → 칼럼 목록
assert(/border-bottom:\s*1px dotted var\(--color-border\)/.test(rule('.blog-list-item')), 'list items separated by dotted lines');

// 폴더 카드 줄 → 탭 → 연재 칼럼(2026-10-17): 탭·추천 카드 없이 BlogFront
for (const p of ['pages/ko/blog/index.astro', 'pages/en/blog/index.astro']) {
  const f = read(p);
  assert(!f.includes('blog-category-tabs') && f.includes('<BlogFront '), `${p} renders the serial column instead of tabs`);
  assert(!f.includes('blog-category-showcase-card'), `${p} drops the folder cards`);
  assert(f.includes('blog-masthead-tagline'), `${p} has the masthead tagline`);
  assert(!f.includes('CATEGORY_ICONS'), `${p} drops the unused showcase icon map`);
}
assert(read('pages/en/blog/index.astro').includes('A column on building, learning and keeping notes'), 'en tagline');

// Task 2: 상세
const layout = read('components/blog/BlogArticleLayout.astro');
assert(!layout.includes('📘') && !layout.includes('blog-article-icon'), 'hardcoded 📘 article icon removed');
assert(layout.includes('data-admin-only') && layout.includes('newsprint-comments') && layout.includes('data-comment-form') && layout.includes('ContentFeedback') && layout.includes('id="persona-data"'), 'blog article keeps admin/comments/feedback/persona hooks');
assert(/class="blog-category-badge blog-post-byline-series"[^>]*--cat-color/.test(layout), 'byline shows the series as a color dot label');
assert(!/style=\{`background:/.test(layout), 'article tags have no inline colors');
assert(/font-weight:\s*700/.test(rule('.blog-article-title')), 'article title 700');
assert(!rule('.blog-post-toc-summary').includes('uppercase'), 'contents label not uppercase');
for (const p of ['pages/ko/blog/[slug].astro', 'pages/en/blog/[slug].astro']) {
  const f = read(p);
  assert(f.includes('onSessionReady') && f.includes('recordReadingHistory') && f.includes('handbook-terms-data'), `${p} keeps session/reading-history/terms hooks`);
}

// Follow-up fixes
assert(rule('.blog-post-byline-meta').includes('var(--font-blog-ui)'), 'byline uses the blog UI font');
for (const d of ['components/blog', 'pages/ko/blog', 'pages/en/blog']) {
  for (const f of fs.readdirSync(path.join(src, d))) {
    if (!f.endsWith('.astro')) continue;
    assert(!read(`${d}/${f}`).includes('#{tag}'), `${d}/${f} must not render #{tag} (CSS adds the #)`);
  }
}

console.log('blog-v2.test.cjs passed');
