// frontend/tests/handbook-index-shelves.test.cjs
// Handbook index B+A: term of the day, shelves by field, A–Z index; search/category mode in the inline script.
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

// components
const today = read('components/handbook/HandbookToday.astro');
for (const s of ['오늘의 용어', 'Term of the day', '풀이 읽기 →', 'Read the explainer →', '뉴스에서는 이렇게 쓰여요', 'How the news uses it']) {
  assert(today.includes(s), `today copy: ${s}`);
}
assert(today.includes('firstNewsLine(newsContext)') && today.includes('{newsLine && ('), 'plate only when a news line exists');
assert(today.includes('issueLabel(locale, issueNumber('), 'label carries the issue number');
assert(today.includes('plainDefinition(term.definition)'), 'definition is plain text');

const shelvesC = read('components/handbook/HandbookShelves.astro');
for (const s of ['분야별 서가', 'Shelves by field', '개 모두 보기 →', 'All ${n} →']) {
  assert(shelvesC.includes(s), `shelves copy: ${s}`);
}
assert(shelvesC.includes('/${locale}/handbook/category/${shelf.slug}/'), 'shelf links to the category page');
assert(shelvesC.includes('handbook-shelf--wide'), 'wide shelf modifier');
assert(shelvesC.includes('getHandbookCategoryLabel(locale, shelf.slug)'), 'shelf name from handbookCategories');

const az = read('components/handbook/HandbookAzIndex.astro');
for (const s of ['A–Z 색인', 'A–Z index']) assert(az.includes(s), `index copy: ${s}`);
assert(az.includes('id={`az-${group.anchor}`}') && az.includes('href={`#az-${l.anchor}`}'), 'letter bar links to group anchors (id="az-…")');
assert(az.includes('<span aria-hidden="true">{l.letter}</span>'), 'letters without terms are muted spans');

// pages
for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/handbook/index.astro`);
  for (const c of ['<HandbookToday ', '<HandbookShelves ', '<HandbookAzIndex ']) {
    assert(page.includes(c), `${locale}: uses ${c.trim()}`);
  }
  assert(/<NewsprintShell[\s\S]*?rail=\{false\}/.test(page), `${locale}: no right rail`);
  assert(!/HandbookListRail|handbook-trending|handbook-showcase|handbook-filter-btn|PREVIEW_COUNT|termsByCategory|handbookTags/.test(page), `${locale}: old trending/showcase/filter/rail removed`);
  assert(page.includes('buildShelves(indexTerms, categories, trendingSlugs)') && page.includes('buildAzIndex(indexTerms)'), `${locale}: shelves and index from lib/handbookShelves.js`);
  assert(page.includes('termOfDay.total || allTerms.length'), `${locale}: term count prefers the exact count`);
  assert(page.includes('<strong>{shelves.length}</strong>'), `${locale}: category count = shelves with terms`);

  // active filter link: hidden, labelled, right before the result count
  const linkAt = page.indexOf('<a id="handbook-active-filter"');
  assert(linkAt > 0 && linkAt < page.indexOf('id="handbook-result-count"'), `${locale}: active-filter link sits right before the result count`);
  assert(/<a id="handbook-active-filter"[^>]*\shidden\s[^>]*data-labels=\{JSON\.stringify\(categoryLabels\)\}/.test(page), `${locale}: link is hidden and carries category labels`);

  // inline script
  assert(page.includes('dataset.handbookIndexReady'), `${locale}: double-binding guard`);
  assert(page.includes("document.addEventListener('astro:page-load', initHandbookIndex);") && /\n  initHandbookIndex\(\);\n/.test(page), `${locale}: page-load + immediate init`);
  assert(page.includes("params.get('category')") && page.includes('Object.prototype.hasOwnProperty.call(labels, slug)'), `${locale}: only canonical ?category= values apply`);
  assert(page.includes("querySelectorAll<HTMLElement>('.handbook-today, .handbook-shelves, .handbook-az')"), `${locale}: browse sections toggle with search mode`);
  assert(page.includes("new Event('content-status:refresh')"), `${locale}: cards hydrate after render`);
  assert(!/IntersectionObserver|sentinel|BATCH_SIZE/.test(page), `${locale}: no infinite scroll`);
}
assert(read('pages/ko/handbook/index.astro').includes("' · 전체 보기로'"), 'ko back-to-all copy');
assert(read('pages/en/handbook/index.astro').includes("' · Back to all'"), 'en back-to-all copy');
assert(!fs.existsSync(path.join(src, 'components/newsprint/HandbookListRail.astro')), 'list rail deleted');
assert(!read('lib/pageData/handbookPage.ts').includes('termsByCategory'), 'unused termsByCategory removed');

// CSS
assert(/grid-template-columns:\s*minmax\(0, 1\.2fr\) minmax\(0, 1fr\)/.test(rule('.handbook-today')), 'today: 1.2fr : 1fr');
assert(rule('.handbook-today-plate').includes('background: var(--color-text-primary)'), 'ink plate in light themes');
assert(rule('[data-theme="dark"] .handbook-today-plate').includes('var(--color-bg-tertiary)'), 'dark plate uses bg-tertiary');
assert(/grid-template-columns:\s*repeat\(3, minmax\(0, 1fr\)\)/.test(rule('.handbook-shelves-grid')), 'shelves: 3 columns');
assert(/grid-row:\s*span 2/.test(rule('.handbook-shelf--wide')), 'wide shelf spans 2 rows');
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.handbook-shelf')), 'shelf ink rule');
assert(/column-count:\s*3/.test(rule('.handbook-az-dict')) && /column-rule:/.test(rule('.handbook-az-dict')), 'dictionary: 3 ruled columns');
assert(rule('.handbook-az-group').includes('scroll-margin-top: calc(var(--header-h, 4rem) + 4.5rem)'), 'anchors clear the sticky header + search');
assert(/display:\s*none/.test(rule('.handbook-active-filter[hidden]')), 'hidden active-filter link stays hidden');
const mobileAt = css.indexOf('/* Handbook index: mobile */');
assert(mobileAt > 0, 'handbook index mobile block');
const mobile = css.slice(mobileAt, css.indexOf('\n}\n', mobileAt));
assert(/\.handbook-today\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/.test(mobile), 'mobile: today one column');
assert(/\.handbook-shelves-grid\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/.test(mobile), 'mobile: shelves one column');
assert(/\.handbook-shelf--wide\s*\{[^}]*grid-row:\s*auto/.test(mobile), 'mobile: wide shelf one cell');
assert(/\.handbook-az-bar\s*\{[^}]*overflow-x:\s*auto/.test(mobile), 'mobile: letter bar scrolls sideways');
assert(/\.handbook-az-dict\s*\{[^}]*column-count:\s*1/.test(mobile), 'mobile: dictionary one column');

// unused CSS removed (Task 4); .handbook-result-count stays because the news list uses it
for (const gone of ['.handbook-trending', '#handbook-showcase', '.product-category-showcase', '.newsprint-rail-category-', '.handbook-filter-', '.handbook-difficulty-btn', '.handbook-controls']) {
  assert(!css.includes(gone), `unused CSS removed: ${gone}`);
}
assert(css.includes('.handbook-result-count {'), 'result count style stays (news list)');

console.log('handbook-index-shelves.test.cjs passed');
