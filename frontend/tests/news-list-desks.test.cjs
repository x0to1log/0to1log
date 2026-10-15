// frontend/tests/news-list-desks.test.cjs
// News list "two desks": business | date spine | research; list mode on filter/search.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');
const css = read('styles/global.css');

const cell = read('components/newsprint/NewsDeskCell.astro');
for (const attr of ['data-category=', 'data-post-type=', 'data-post-id=', 'data-search-text=']) {
  assert(cell.includes(attr), `cell keeps the list-card contract: ${attr}`);
}
assert(/class=\{`newsprint-card news-desk-cell/.test(cell), 'cell is a .newsprint-card (filter/search hide it)');
assert(cell.includes('newsprint-bookmark-icon') && cell.includes('data-bookmarked="false"'), 'bookmark button, user-neutral');
assert(cell.includes('newsprint-card-stretched-link'), 'whole cell is clickable');
assert(cell.includes('postTypeLabel(locale, '), 'desk label comes from lib/postType.js');
assert(!/newsprint-tags-inline|newsprint-tag\b|getCategoryLabel/.test(cell), 'no hashtag row or category label in the list');

const list = read('components/newsprint/NewsDeskList.astro');
assert(list.includes('id="news-list-results"') && list.includes('data-mode="desks"'), 'results root starts in desk mode');
for (const s of ['비즈니스 데스크', '리서치 데스크', 'Business desk', 'Research desk', '이날은 리서치 기사가 없어요', 'No research story this day']) {
  assert(list.includes(s), `copy: ${s}`);
}
assert(/<p class="news-desk-empty news-desk-empty--business">/.test(list) && !/news-desk-empty[^>]*(data-search-text|newsprint-card)/.test(list), 'empty placeholders are plain elements');
const order = ['class="news-desk-date"', '<NewsDeskCell locale={locale} post={entry.business}', '<NewsDeskCell locale={locale} post={entry.research}'].map((s) => list.indexOf(s));
assert(order.every((i) => i > 0) && order[0] < order[1] && order[1] < order[2], 'DOM order: date, business, research');

for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/news/index.astro`);
  assert(page.includes('<NewsDeskList locale=') && page.includes('buildDeskRows('), `${locale}: renders desks from buildDeskRows`);
  assert(/<NewsprintShell[\s\S]*?rail=\{false\}/.test(page), `${locale}: no right rail`);
  assert(page.includes("import '../../../scripts/newsDeskMode';"), `${locale}: desk mode script`);
  assert(!/NewsprintHeadline|NewsprintListCard|NewsprintListRail|newsListMultiHeadline/.test(page), `${locale}: old headline/card/rail removed`);
  assert(page.includes('sc.editorial_note'), `${locale}: editorial note kept`);
}

const shell = read('components/newsprint/NewsprintShell.astro');
assert(/rail\?: boolean/.test(shell) && /\{rail && \(/.test(shell), 'shell can drop the rail');

const mode = read('scripts/newsDeskMode.ts');
assert(mode.includes('deskModeReady') && mode.includes("'news:list-updated'") && mode.includes("'newsprint:filter-change'"), 'mode script: guard + both signals');
assert(mode.includes('data-row-empty'), 'mode script hides empty rows');
assert(read('scripts/newsListSearch.ts').includes("new CustomEvent('news:list-updated')"), 'search announces updates');

assert(/grid-template-areas:\s*"business date research"/.test(css), 'desk grid: business | date | research');
assert(/\.news-desks\[data-mode="list"\] \.news-desk-row\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/.test(css), 'list mode is one column');
assert(/\.news-desk-row\[data-row-empty="true"\],\s*\n\.news-desk-weekly\[data-row-empty="true"\]\s*\{\s*display:\s*none;/.test(css), 'empty rows hidden');
assert(/\[data-theme="dark"\] \.news-desk-weekly\s*\{/.test(css), 'dark weekly band rule');
assert(/\.news-desk-cell--business\s*\{\s*--desk:\s*var\(--tier-paid\);/.test(css) && /\.news-desk-cell--research\s*\{\s*--desk:\s*var\(--tier-freemium\);/.test(css), 'desk colours reuse tier tokens');
assert(!/\.news-desk[a-z-]*[^{]*\{[^}]*(?:^|[\s;{])order:/m.test(css), 'no CSS order on desk items');

// desk colours are small text: >= 4.5:1 on bg-primary in all three themes
function block(sel) { const i = css.indexOf(sel); assert(i >= 0, `missing ${sel}`); return css.slice(i, css.indexOf('}', i)); }
function tok(b, name) { const m = b.match(new RegExp(`${name}:\\s*(#[0-9A-Fa-f]{6})`)); return m && m[1]; }
function lum(h) { return [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)).reduce((s, v, i) => s + v * [0.2126, 0.7152, 0.0722][i], 0); }
function ratio(a, b) { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); }
const tierLight = block(':root {\n  --tier-free');
const tierDark = block('[data-theme="dark"] {\n  --tier-free');
const bgs = { light: block('[data-theme="light"] {').match(/--color-bg-primary:\s*(#[0-9A-Fa-f]{6})/)[1], white: block('[data-theme="white"] {').match(/--color-bg-primary:\s*(#[0-9A-Fa-f]{6})/)[1], dark: block('[data-theme="dark"] {').match(/--color-bg-primary:\s*(#[0-9A-Fa-f]{6})/)[1] };
for (const t of ['--tier-paid', '--tier-freemium']) {
  assert(ratio(tok(tierLight, t), bgs.light) >= 4.5, `${t} on paper`);
  assert(ratio(tok(tierLight, t), bgs.white) >= 4.5, `${t} on white`);
  assert(ratio(tok(tierDark, t), bgs.dark) >= 4.5, `${t} on dark`);
}
console.log('news-list-desks.test.cjs passed');
