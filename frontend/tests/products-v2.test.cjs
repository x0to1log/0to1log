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

// Mobile: tiles don't scroll inside the page; a "see all" button opens the category
const tile = fs.readFileSync(path.join(__dirname, '..', 'src', 'components', 'products', 'ProductCategoryTile.astro'), 'utf8');
assert(tile.includes('class="product-cat-tile-more"') && tile.includes('data-category={categoryId}'), 'tile has a see-all button');
assert(/\.product-cat-tile\s*\{\s*height:\s*auto;/.test(css), 'phone tiles are not fixed height');
assert(/\.product-cat-row:nth-child\(n \+ 5\)\s*\{\s*display:\s*none;/.test(css), 'phone tiles show the first four rows');
for (const loc of ['ko', 'en']) {
  const page = fs.readFileSync(path.join(__dirname, '..', 'src', 'pages', loc, 'products', 'index.astro'), 'utf8');
  assert(page.includes("'.product-cat-tile-header, .product-cat-tile-more'"), `${loc}: see-all shares the header click handler`);
}
assert(!/border-bottom/.test(rule('.product-filter-bar')), 'no rule under the search bar (tiles carry their own top rule)');

// Mobile nav labels never wrap
assert(/grid-template-columns:\s*repeat\(5,\s*auto\)/.test(css), 'mobile nav columns follow label width');

console.log('products-v2.test.cjs passed');
