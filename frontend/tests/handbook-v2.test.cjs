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

console.log('handbook-v2.test.cjs passed');
