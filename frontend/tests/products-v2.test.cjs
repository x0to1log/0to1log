const fs = require('fs');
const path = require('path');
const assert = require('assert');

const css = fs.readFileSync(path.join(__dirname, '..', 'src', 'styles', 'global.css'), 'utf8');

function rules(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return [...css.matchAll(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`, 'g'))].map((m) => m[1]);
}
function rule(selector) {
  const all = rules(selector);
  assert(all.length > 0, `missing CSS rule ${selector}`);
  return all[all.length - 1];
}

// Unused spotlight styles are gone
assert(!css.includes('.product-spotlight'), 'ProductSpotlight CSS removed (component unused)');

// Thumbnail fallback: neutral surface, no category gradients
assert(!/\.product-card-thumb-fallback\[data-category[^{]*\{[^}]*gradient/.test(css), 'no gradient thumbnail fallbacks');
assert(/var\(--color-bg-secondary\)/.test(rule('.product-card-thumb-fallback')), 'fallback uses neutral surface');

// Decision B: tier colour only on dots
assert(/--tier-free:/.test(css) && /--tier-freemium:/.test(css), 'tier dot tokens defined');
for (const sel of ['.product-pricing-badge', '.product-difficulty-badge']) {
  // Base style may be grouped; check every block whose selector list names the badge itself.
  const esc = sel.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const blocks = [...css.matchAll(new RegExp(`(?:^|\\n)((?:[^{}\\n]*,\\n)*${esc}(?:,\\n[^{}\\n]*)*)\\s*\\{([^}]*)\\}`, 'g'))].map((m) => m[2]);
  assert(blocks.length > 0, `${sel}: base rule exists`);
  for (const r of blocks) {
    assert(!/background/.test(r), `${sel}: no pill background`);
    assert(!/border-radius:\s*99/.test(r), `${sel}: no pill radius`);
  }
  assert(css.includes(`${sel}::before`), `${sel}: dot marker`);
}
assert(/--dot:\s*var\(--tier-free\)/.test(rule('.product-pricing-badge[data-pricing="free"]')), 'free pricing sets dot colour only');
assert(!/color-mix\(in srgb, #22c55e/.test(css), 'old green pill tint removed');

// Pros / cons without red-green
assert(!/#16a34a|#dc2626/.test(css.slice(css.indexOf('Pros & Cons'), css.indexOf('Korean Note'))), 'pros/cons not red/green');

// Cards: no lift on hover, filter bar without shadow
assert(!rules('.product-card:hover').some((r) => /transform/.test(r)), 'product card does not lift on hover');
assert(!/border-radius|box-shadow/.test(rule('.product-card')), 'product card is not a boxed card');
assert(!/box-shadow/.test(rule('.product-filter-bar')), 'filter bar has no shadow');

console.log('products-v2.test.cjs passed');
