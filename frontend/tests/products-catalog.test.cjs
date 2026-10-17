// frontend/tests/products-catalog.test.cjs
// Products catalog A (fields): head + jump bar + editor's picks + field sections; modes in scripts/productCatalog.ts.
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
  return all[0]; // first match = the base rule (media-query copies come later)
}

// pages
const copy = {
  ko: ['AI 도구 {shownCount}개 · {sections.length}개 분야', '← 모든 분야', 'aria-label="분야 바로가기"', 'data-also-label="다른 분야에서 함께 쓰이는 도구 {k}개"', '제품명, 로고 및 상표는 각 소유자의 자산입니다.'],
  en: ['{shownCount} AI tools · {sections.length} fields', '← All fields', 'aria-label="Jump to field"', 'data-also-label="Also used for this ({k})"', 'Product names, logos, and trademarks are the property of their respective owners.'],
};
for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/products/index.astro`);
  for (const s of copy[locale]) assert(page.includes(s), `${locale}: copy ${s}`);
  assert(page.includes(`<h1 class="product-catalog-title">{t.${locale}['products.title']}</h1>`), `${locale}: h1`);
  assert(page.includes('<header class="product-catalog-head">') && page.includes('<ProductSearchBar locale={locale} />'), `${locale}: title row with the search bar`);
  assert(page.includes('<nav class="product-catalog-jump"') && page.includes('href={`#cat-${section.category.id}`}'), `${locale}: jump bar links to #cat-{id}`);
  assert(page.includes(`jumpLabel(locale, section.category.id, section.category.label_${locale})`), `${locale}: short jump labels`);
  assert(page.includes('<ProductPicks picks={picks} locale={locale} />'), `${locale}: editor's picks`);
  assert(page.includes('<ProductCatalogSection section={section} locale={locale} searchTexts={searchTexts} />'), `${locale}: field sections`);
  assert(page.includes('catalogSections(categories, productsByCategory, CATEGORY_ORDER, locale)'), `${locale}: sections from lib/productCatalog.js`);
  assert(page.includes('sections.reduce((sum, section) => sum + section.products.length, 0)'), `${locale}: N = rendered products`);
  assert(page.includes('id="products-top"') && page.includes('class="products-page product-catalog"'), `${locale}: root keeps #products-top`);
  assert(page.includes('<button type="button" class="product-catalog-back" hidden>'), `${locale}: hidden back button`);
  assert(page.includes('id="product-search-no-results"'), `${locale}: no-results line`);
  assert(page.includes('<section class="product-outro">') && page.includes('products-trademark-disclaimer'), `${locale}: outro + trademark notice stay`);
  assert(page.includes("import '../../../scripts/productCatalog';") && !page.includes('is:inline'), `${locale}: bundled catalog script`);
  assert(/if \(error\) Astro\.response\.status = 503;/.test(page), `${locale}: 503 on loader error`);
  for (const gone of ['ProductCategoryTile', 'ProductCard', 'ProductFilterBar', 'filtered-grid', 'category-preview', 'productLike', 'products-back-all', 'product-cat-tag', 'spotlight']) {
    assert(!page.includes(gone), `${locale}: ${gone} removed`);
  }
}

// components
const section = read('components/products/ProductCatalogSection.astro');
assert(section.includes('<section class="product-cat" id={`cat-${category.id}`} data-category={category.id}'), 'section id + data-category');
assert(section.includes('<h2 class="product-cat-title" id={titleId} tabindex="-1">'), 'focusable section heading');
assert(section.includes("{ko ? `${total}개 모두 보기 →` : `See all ${total} →`}") && section.includes('{total > PREVIEW_ROWS && ('), 'see-all button only above six rows');
assert(section.includes('const PREVIEW_ROWS = 6;'), 'six rows per field');
assert(section.includes('<p class="product-cat-lede">') && section.includes('<p class="product-cat-desc" hidden>'), 'lede + hidden full description');
assert(section.includes("import ProductRow from './ProductRow.astro';") && section.includes('overflow={index >= PREVIEW_ROWS}'), 'rows come from ProductRow, data-overflow after six');
assert(section.includes("searchText={searchTexts[product.id] ?? ''}"), 'list rows carry their search text');
const row = read('components/products/ProductRow.astro');
for (const attr of ['data-search-text={searchText}', 'data-category={product.primary_category}', 'data-secondary-categories=', "data-overflow={overflow ? '' : undefined}"]) {
  assert(row.includes(attr), `row attribute ${attr}`);
}
assert(row.includes('<li\n  class="product-row"'), 'row root is li.product-row');
assert(row.includes('class="product-pricing-badge" data-pricing={product.pricing}') && row.includes('class="product-difficulty-badge" data-difficulty={product.difficulty}'), 'existing badge classes');
assert(row.includes('difficultyLabel(locale, product.difficulty)'), 'difficulty labels from lib/productCatalog.js');
assert(row.includes('{name}</span>') && row.includes('product.name_original ?? product.name'), 'brand name');
assert(row.includes('loading="lazy"') && row.includes('alt=""'), 'lazy decorative logo');
assert(section.includes('<div class="product-cat-also" hidden>'), 'hidden "also used" box');

const picks = read('components/products/ProductPicks.astro');
assert(picks.includes('<section class="product-picks" aria-labelledby="product-picks-title">'), 'picks section');
assert(picks.includes('<h2 id="product-picks-title" class="sr-only">') && picks.includes("'편집자 추천'") && picks.includes(`"Editor's picks"`), 'sr-only picks heading');
assert(picks.includes('{picks.length > 0 && ('), 'no picks → no section');
assert(picks.includes('<a class="product-pick" href={`/${locale}/products/${pick.slug}/`}>'), 'pick links to the product');
assert(picks.includes('`편집자 추천 ${index + 1}`') && picks.includes('`Pick ${index + 1}`'), 'pick labels');
assert(picks.includes('ko ? pick.editor_note_ko || pick.editor_note : pick.editor_note'), 'en never falls back to the ko note');
assert(picks.includes('firstSentence(note) || pick.tagline'), 'first sentence of the note, else the tagline');

// data
const data = read('lib/pageData/productsPage.ts');
const cardColumns = data.match(/const CARD_COLUMNS =[\s\S]*?;/)[0];
assert(/difficulty/.test(cardColumns), 'cards carry difficulty');
assert(!/editor_note/.test(cardColumns), 'card query does not ship editor notes');
assert(/demo_media/.test(cardColumns), 'demo_media stays (card query unchanged)');
assert(/const PRODUCT_CATEGORY_COLUMNS = 'id, label_en, label_ko, description_ko, description_en, sort_order';/.test(data), 'field descriptions');
const listFn = data.slice(data.indexOf('export async function getProductsPageData'), data.indexOf('// Detail page'));
assert(listFn.includes(".select(PICK_NOTE_COLUMNS)") && listFn.includes(".eq('featured', true)"), 'featured note query');
assert(data.includes("const PICK_NOTE_COLUMNS = 'id, editor_note, editor_note_ko';"), 'note columns');
assert(listFn.includes('categoriesRes.error || productsRes.error'), '503 only for the two list queries');
assert(listFn.includes('notesRes.error ? [] : notesRes.data'), 'failed note query → tagline fallback');
assert(listFn.includes('orderPicks(resolvedProducts)'), 'picks ordered by orderPicks');
assert(!data.includes('spotlightProduct'), 'spotlightProduct removed');
assert(data.includes('picks: ProductPick[];'), 'ProductsPageData.picks');
const altFn = data.slice(data.indexOf('export async function fetchAlternatives'), data.indexOf('// Detail page: related news'));
assert(altFn.includes('name_original: p.name as string,'), 'similar tools keep the brand name (name_original)');

// script
const script = read('scripts/productCatalog.ts');
assert(script.includes('const DEBOUNCE_MS = 150;'), 'debounce 150ms');
assert(script.includes("root.dataset.catalogReady === 'true'") && script.includes("root.dataset.catalogReady = 'true';"), 'binding guard');
assert(script.includes("document.addEventListener('astro:page-load', initProductCatalog);"), 'runs on every page load');
assert(script.includes("querySelectorAll<HTMLElement>('.product-cat-list > li.product-row')"), 'original rows collected once');
const cloneAt = script.indexOf('row.cloneNode(true)');
assert(cloneAt > 0, 'also rows are clones');
const afterClone = script.slice(cloneAt, cloneAt + 200);
assert(afterClone.includes("removeAttribute('data-overflow')") && afterClone.includes("removeAttribute('hidden')"), 'clones drop data-overflow and hidden');
assert(script.includes("replaceChildren()"), 'also list emptied when leaving the field');
assert(script.includes("history.replaceState(history.state, '', url.toString())"), 'URL via replaceState');
assert(script.includes('event.preventDefault();') && script.includes('event.stopImmediatePropagation();') && script.includes('}, true);'), 'Enter never reloads');
assert(script.includes("params.get('cat')") && script.includes('fieldIds.has(initialField)'), 'only rendered fields apply from ?cat=');
assert(script.includes("focus({ preventScroll: true })") && script.includes('returnTo.focus()'), 'focus moves to the field and back');

// CSS
assert(/grid-template-columns:\s*repeat\(3, minmax\(0, 1fr\)\)/.test(rule('.product-cat-list,\n.product-cat-also-list')), 'rows: 3 columns');
assert(/grid-template-columns:\s*repeat\(5, minmax\(0, 1fr\)\)/.test(rule('.product-picks-list')), 'picks: 5 columns');
assert(/display:\s*none/.test(rule('.product-cat-list > [data-overflow]')), 'rows after six hidden');
assert(/display:\s*block/.test(rule('.product-cat[data-expanded] .product-cat-list > [data-overflow]:not([hidden])')), 'expanded field shows every row');
assert(rule('.product-cat').includes('scroll-margin-top: calc(var(--header-h, 4rem) + 1rem)'), 'anchors clear the fixed header');
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.product-cat-head')), 'field ink rule');
assert(/border-bottom:\s*2px solid var\(--color-text-primary\)/.test(rule('.product-catalog-head')), 'title ink rule');
const tabletAt = css.indexOf('@media (min-width: 768px) and (max-width: 1023px) {\n  .product-picks-list');
assert(tabletAt > 0, 'catalog tablet block');
const tablet = css.slice(tabletAt, css.indexOf('\n}\n', tabletAt));
assert(/\.product-picks-list\s*\{[^}]*repeat\(3, minmax\(0, 1fr\)\)/.test(tablet), 'tablet: picks 3 columns');
assert(/\.product-cat-also-list\s*\{[^}]*repeat\(2, minmax\(0, 1fr\)\)/.test(tablet), 'tablet: rows 2 columns');
const mobileAt = css.indexOf('/* Products catalog: mobile */');
assert(mobileAt > 0, 'catalog mobile block');
const mobile = css.slice(mobileAt, css.indexOf('\n}\n', mobileAt));
assert(/\.product-cat-also-list\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/.test(mobile), 'mobile: rows 1 column');
assert(/\.product-catalog-jump-list\s*\{[^}]*overflow-x:\s*auto/.test(mobile), 'mobile: jump bar scrolls sideways');
assert(/\.product-picks-list\s*\{[^}]*overflow-x:\s*auto[^}]*scroll-snap-type:\s*x mandatory/.test(mobile), 'mobile: picks scroll sideways');
assert(/\.product-catalog-title\s*\{[^}]*font-size:\s*1\.7rem/.test(mobile), 'mobile: smaller h1');

// one label table for the detail page too
const detail = read('components/products/ProductDetail.astro');
assert(detail.includes("import { DIFFICULTY_LABELS, jumpLabel } from '../../lib/productCatalog.js';"), 'ProductDetail imports DIFFICULTY_LABELS (and the short field labels)');
assert(!detail.includes("beginner: { en: 'Beginner-friendly'"), 'no second difficulty table');

// old list pieces are gone (Task 3)
for (const gone of ['components/products/ProductCategoryTile.astro', 'components/products/ProductFilterBar.astro', 'components/products/ProductSpotlight.astro', 'lib/productCategoryIcons.ts']) {
  assert(!fs.existsSync(path.join(src, gone)), `deleted: ${gone}`);
}
for (const gone of ['.product-category-grid', '.product-category-preview', '.product-category-see-all', '.product-cat-tile', '.product-cat-row', '.product-cat-tag', '.products-back-all', '.product-filter-bar', '.product-filter-tab', '.product-outro-cta']) {
  assert(!css.includes(gone), `unused CSS removed: ${gone}`);
}
assert(css.includes('.product-filter-search {') && css.includes('.product-pricing-badge,') && css.includes('.product-card {'), 'shared product styles stay');
const i18n = read('i18n/index.ts');
for (const key of ['products.categoryAll', 'products.heroTitle', 'products.outroCta']) {
  assert(!i18n.includes(`'${key}'`), `unused i18n key removed: ${key}`);
}
assert(i18n.includes("'products.heroSubtitle'") && i18n.includes("'products.outroTitle'"), 'used product keys stay');

console.log('products-catalog.test.cjs passed');
