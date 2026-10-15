// frontend/tests/handbook-v2.test.cjs
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
  return all[all.length - 1]; // last top-level rule wins
}

// Task 1: 목록
const card = rule('.handbook-card');
assert(/border-bottom:\s*1px dotted var\(--color-border\)/.test(card), 'term entries separated by dotted lines');
assert(/background:\s*none|background:\s*transparent/.test(card) && /box-shadow:\s*none/.test(card), 'term entries are not cards');
assert(/font-weight:\s*600/.test(rule('.handbook-card-title')) && rule('.handbook-card-title').includes('var(--font-heading)'), 'entry title in Hahmlet 600');
assert(/-webkit-line-clamp:\s*2/.test(rule('.handbook-card-def')), 'definition clamps to 2 lines');
const pill = rule('.handbook-cat-pill');
assert(/background:\s*none/.test(pill) && pill.includes('var(--color-accent)'), 'category pill becomes an accent label');
assert(css.includes('.handbook-cat-pill::before {'), 'category label has a dot');
assert(rule('.handbook-filter-btn[aria-pressed="true"]::after').includes('var(--color-accent)'), 'active filter marked by an accent dot');
assert(rules('.handbook-trending').length === 1, 'duplicate .handbook-trending block removed');
assert(/border-bottom:\s*1px dotted/.test(rule('.handbook-trending-list li')), 'trending is a dotted numbered list');
assert(css.includes('#handbook-showcase .product-category-showcase-card {'), 'showcase override is scoped to the handbook');

// Task 2: 상세
for (const p of ['pages/ko/handbook/[slug].astro', 'pages/en/handbook/[slug].astro']) {
  const page = read(p);
  assert(!/handbook-detail-meta[\s\S]{0,400}<span style=/.test(page), `${p} meta spans have no inline styles`);
  assert(page.includes('data-auth-only') && page.includes('learning-check') && page.includes('data-term-id'), `${p} keeps the learning action bar`);
  assert(page.includes('id="level-data"') && page.includes('data-level'), `${p} keeps the level switcher hooks`);
  assert(page.includes('onSessionReady'), `${p} keeps session hydration`);
  assert(page.includes('data-admin-only'), `${p} keeps the admin block`);
}
for (const body of rules('.handbook-detail-title')) {
  assert(!/font-weight:\s*(800|900)/.test(body), 'detail title uses a loaded Hahmlet weight');
}
assert(rule('.handbook-detail-meta').includes('var(--color-accent)'), 'detail category label is accent');
assert(/border:\s*none/.test(rule('.handbook-level-switcher')), 'level switcher has no box border');
assert(rule('.handbook-level-btn--active::after').includes('var(--color-accent)'), 'active level marked by an accent dot');
assert(!rule('.handbook-toc__title').includes('uppercase'), 'toc title not uppercase');
assert(!rule('.handbook-section-label').includes('uppercase'), 'section label not uppercase');

console.log('handbook-v2.test.cjs passed');
