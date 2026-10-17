// frontend/tests/product-detail-review.test.cjs
// Product detail as a review page (A): crumb, head + facts box, editor's take first, similar tools as catalog rows.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');
const css = read('styles/global.css');
function rules(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return [...css.matchAll(new RegExp(`(?:^|\\n)\\s*${esc}\\s*\\{([^}]*)\\}`, 'g'))].map((m) => m[1]);
}
function rule(selector) {
  const all = rules(selector);
  assert(all.length > 0, `missing CSS rule ${selector}`);
  return all[0];
}

// pages
for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/products/[slug].astro`);
  assert(!page.includes('ProductSearchBar') && !page.includes('handbookSearchHints'), `${locale}: no search bar on the detail page`);
  assert(page.includes("import ProductDetail from '../../../components/products/ProductDetail.astro';") && page.includes('<ProductDetail product={product}'), `${locale}: ProductDetail`);
  assert(page.includes("import '../../../scripts/productLike';") && page.includes("import '../../../scripts/contentFeedback';"), `${locale}: like + feedback scripts`);
  assert(page.includes('<ContentFeedback') && page.includes('isAdmin={!!Astro.locals.isAdmin}'), `${locale}: feedback slot + admin prop`);
  assert(page.includes('<div class="product-detail-page">'), `${locale}: page wrapper stays`);
  assert(/if \(error\)[\s\S]*status = 503/.test(page) && /else if \(!product\)[\s\S]*status = 404/.test(page), `${locale}: 503 / 404`);
  assert(!page.includes('is:inline'), `${locale}: bundled scripts only`);
}

// component
const detail = read('components/products/ProductDetail.astro');
assert(detail.includes('<nav class="product-detail-crumb" aria-label={copy.crumb}>'), 'crumb nav');
assert(detail.includes("crumb: '제품 위치'") && detail.includes("crumb: 'Product location'"), 'crumb labels');
assert(detail.includes("back: '← AI 제품군'") && detail.includes("back: '← AI Products'"), 'crumb back link copy');
assert(detail.includes('jumpLabel(locale, product.primary_category, product.primary_category)'), 'short field label');
assert(detail.includes('const categoryHref = (id: string) => `/${locale}/products/?cat=${id}`;'), 'field links open ?cat=');
assert(detail.includes('<header class="product-detail-head">') && detail.includes('<h1 class="product-detail-name">{product.name_original}</h1>'), 'head + brand name h1');
assert(detail.includes('<aside class="product-detail-spec" aria-label={copy.facts}>') && detail.includes('<dl class="product-detail-spec-list">'), 'facts box');
assert(detail.includes("notListed: '정보 없음'") && detail.includes("notListed: 'Not listed'"), 'price not listed');
assert(detail.includes("supported: '지원'") && detail.includes("notSupported: 'Not supported'"), 'Korean support row');
assert.equal(detail.split('id="product-like-btn"').length - 1, 1, 'exactly one like button');
for (const kept of ['id="like-label"', 'id="like-count"', 'data-product-id={product.id}', "data-liked={isLiked ? 'true' : 'false'}"]) {
  assert(detail.includes(kept), `like button keeps ${kept}`);
}
assert(detail.includes('<div class="product-detail-actions">') && detail.includes('rel="noopener noreferrer"'), 'action row with the visit link');
assert(detail.indexOf('<div class="product-detail-actions">') > detail.indexOf('<aside class="product-detail-spec"'), 'action row sits inside the facts box');
assert(!detail.includes('product-detail-chip'), 'no chip classes (tags row uses new classes)');

const order = [
  'class="product-detail-verdict"',
  'class="product-detail-pros-cons"',
  'class="product-detail-scenarios"',
  'class="product-detail-pair"',
  'class="product-detail-pricing-table',
  'class="product-detail-steps"',
  'class="product-detail-description',
  'class="product-detail-korean-note"',
  'class="product-detail-news-list"',
  'class="product-detail-alts"',
  'product-detail-faq"',
];
let at = detail.indexOf('</header>');
for (const marker of order) {
  const next = detail.indexOf(marker);
  assert(next > at, `section order: ${marker}`);
  at = next;
}

assert(detail.includes('const SCENARIOS_SHOWN = 3;') && detail.includes('<details class="product-detail-more">'), 'scenarios: three, then details');
assert(detail.includes('{scenariosMore.length > 0 && ('), 'no details with three or fewer');
assert(detail.includes('more: (n: number) => `${n}개 더 보기`') && detail.includes('more: (n: number) => `Show ${n} more`'), 'show-more copy');
assert(detail.includes('{SCENARIOS_SHOWN + i + 1}'), 'numbering continues inside details');
assert(detail.includes("verdict: '에디터 한마디'") && detail.includes(`verdict: "Editor's take"`), "editor's take label");
assert(detail.includes("pros: '좋은 점'") && detail.includes("cons: 'What to watch'"), 'pros / cons labels');
assert(detail.includes("import ProductRow from './ProductRow.astro';") && detail.includes('<ProductRow product={alt} locale={locale} />'), 'similar tools use ProductRow');
assert(!detail.includes('import ProductCard from') && !detail.includes('<ProductCard') && !detail.includes('product-detail-bottom-cta') && !detail.includes('product-visit-btn--large'), 'no cards, no bottom CTA');
assert(detail.includes('data-admin-only') && detail.includes('hidden={!isAdmin}'), 'admin actions stay hidden for the public');
assert(detail.indexOf('newsprint-admin-actions') < detail.indexOf('<slot />'), 'admin actions before the slot');
assert(!detail.includes('is:inline'), 'bundled script only');

// row component
const section = read('components/products/ProductCatalogSection.astro');
assert(section.includes('<ProductRow'), 'catalog sections use ProductRow');

// data
const data = read('lib/pageData/productsPage.ts');
const altFn = data.slice(data.indexOf('export async function fetchAlternatives'), data.indexOf('// Detail page: related news'));
assert(altFn.includes('.select(CARD_COLUMNS)') && altFn.includes('name_original: p.name as string,'), 'similar tools: same query + brand name');

// CSS
assert(/grid-template-columns:\s*minmax\(0, 1fr\) 250px/.test(rule('.product-detail-head')), 'head: 2 columns (1fr : 250px)');
assert(/border-bottom:\s*2px solid var\(--color-text-primary\)/.test(rule('.product-detail-head')), 'head ink rule');
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.product-detail-section-title')), 'section heads: ink rule');
assert(/grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\)/.test(rule('.product-detail-pros-cons')), 'pros / cons: 2 columns');
assert(/grid-column:\s*1 \/ -1/.test(rule('.product-detail-pros-cons > :only-child')), 'one side only → full width');
assert(/list-style:\s*none/.test(rule('.product-detail-alts')), 'similar tools list reset');
const mobileAt = css.indexOf('/* Product detail: mobile */');
assert(mobileAt > 0, 'detail mobile block');
const mobile = css.slice(mobileAt, css.indexOf('\n}\n', mobileAt));
assert(mobile.includes('@media (max-width: 767px) {'), 'mobile at 767px');
assert(/\.product-detail-head\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/.test(mobile), 'mobile: head 1 column');
const bar = mobile.match(/\.product-detail-actions\s*\{([^}]*)\}/);
assert(bar && /position:\s*fixed/.test(bar[1]) && /z-index:\s*50;/.test(bar[1]) && /bottom:\s*0/.test(bar[1]), 'mobile: action row fixed at the bottom, z-index 50');
assert(bar[1].includes('env(safe-area-inset-bottom)'), 'mobile: action row clears the home indicator');
assert(/body:has\(\.product-detail-actions\)\s*\{[^}]*padding-bottom:\s*calc\([^}]*env\(safe-area-inset-bottom\)/.test(mobile), 'mobile: page bottom padding for the bar');
assert(/\.product-detail-pros-cons,\s*\n\s*\.product-detail-pair,\s*\n\s*\.product-detail-alts\s*\{[^}]*minmax\(0, 1fr\)/.test(mobile), 'mobile: pros/cons, pair, similar tools 1 column');
const scenarioLine = css.split('\n').find((line) => line.includes('.product-detail-scenario {'));
assert(scenarioLine && scenarioLine.includes('background: var(--color-bg-secondary'), 'scenario cards on the theme surface');
const prosCons = css.slice(css.indexOf('Pros & Cons'), css.indexOf('Korean Note'));
assert(prosCons.length > 0 && prosCons.includes('var(--color-success)') && prosCons.includes('var(--color-error)'), 'pros/cons colours from tokens');

console.log('product-detail-review.test.cjs passed');
