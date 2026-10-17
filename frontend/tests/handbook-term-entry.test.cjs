// frontend/tests/handbook-term-entry.test.cjs
// Term detail A+B: crumb shell, entry head, two-column hero, see-also, inline actions, concept map, news mentions.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

// data
const data = read('lib/pageData/handbookDetailPage.ts');
const columns = data.slice(data.indexOf('HANDBOOK_DETAIL_PUBLIC_COLUMNS = ['), data.indexOf("].join(', ')"));
for (const c of ['term_type', 'facet_intent', 'facet_volatility']) {
  assert(columns.includes(`'${c}'`), `detail columns include ${c}`);
}
assert.strictEqual((data.match(/\.from\('news_posts'\)/g) || []).length, 1, 'one news query: real mentions only (latest-news fallback removed)');
assert(!/recentNewsRes|backfill/.test(data), 'fallback query and assignment removed');
assert(/\.or\(`tags\.cs\.\{\$\{term\.term\.toLowerCase\(\)\}\},title\.ilike\.%\$\{term\.term\}%`\)[\s\S]{0,120}\.limit\(5\)/.test(data), 'mentions query unchanged (max 5)');
assert(data.includes('relatedArticles = articlesRes.data ?? [];'), 'no mentions -> empty list');
assert(data.includes("import { orderBySlugs } from '../handbookFacets.js';"), 'imports orderBySlugs');
assert(data.includes('relatedTerms = orderBySlugs(relatedRes.data ?? [], term.related_term_slugs ?? []);'), 'related terms follow related_term_slugs order');

// shell: crumb items replace issue/date only when given
const shell = read('components/newsprint/NewsprintShell.astro');
assert(/crumbItems\?: string\[\];/.test(shell), 'shell: optional crumbItems prop');
assert(shell.includes('{crumbItems ? (') && shell.includes("crumbItems.join(' · ')"), 'shell: crumb items joined with " · "');
assert(shell.includes('issueLabel(locale, issueNumber(displayDate))'), 'shell: default crumb keeps issue/date');

// pages
for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/handbook/[slug].astro`);
  assert(/<NewsprintShell[\s\S]*?compact[\s\S]*?rail=\{false\}[\s\S]*?crumbItems=\{crumbItems\}/.test(page), `${locale}: compact shell, no rail, crumb items`);
  assert(page.includes('backHref={`/${locale}/handbook/`}'), `${locale}: crumb back link to the glossary`);
  assert(page.includes(locale === 'ko' ? 'backLabel="AI 용어집"' : 'backLabel="AI Glossary"'), `${locale}: crumb label`);
  assert(page.includes('getHandbookCategoryLabel(locale, cat)'), `${locale}: crumb items are field labels`);
  assert(!/HandbookSideRail|HandbookSectionNav|ReadingActionsRail|slot="rail"|newsprint-rail-search|masthead=|subkicker=|handbook-detail-meta/.test(page), `${locale}: rail, masthead and field line removed`);
  for (const c of ['<HandbookEntryHead ', '<HandbookXref ', '<HandbookConceptMap ', '<HandbookNewsMentions ']) {
    assert(page.includes(c), `${locale}: uses ${c.trim()}`);
  }

  // inline actions: direct first child of the article layout, before __body (CSS > and order rely on it)
  const layoutAt = page.indexOf('<div class="reading-actions-layout reading-actions-layout--article">');
  const actionsAt = page.indexOf('<StickyReadingActions', layoutAt);
  const bodyAt = page.indexOf('<div class="reading-actions-layout__body">', layoutAt);
  assert(layoutAt > 0 && actionsAt > layoutAt && actionsAt < bodyAt, `${locale}: actions sit before the body inside the article layout`);
  assert(/<StickyReadingActions\s+locale=\{locale\}\s+variant="term"[\s\S]*?itemType="term"[\s\S]*?\/>/.test(page), `${locale}: term actions`);
  assert(!/<StickyReadingActions[^/]*placement=/.test(page), `${locale}: inline placement (default)`);

  // order: entry -> hero -> see also -> switcher -> body -> concept map -> news -> references -> reading end
  const order = ['<HandbookEntryHead ', '<HandbookHeroCard', '<HandbookXref ', 'class="switcher-bar"', 'id="handbook-body"', '<HandbookConceptMap ', '<HandbookNewsMentions ', '<HandbookReferences ', '<div data-reading-end>', 'class="handbook-bottom-nav"'].map((s) => page.indexOf(s));
  assert(order.every((i, n) => i > 0 && (n === 0 || i > order[n - 1])), `${locale}: block order`);
  const proseToMap = page.slice(page.indexOf('id="handbook-body"'), page.indexOf('<HandbookConceptMap '));
  assert(proseToMap.includes('</div>') && proseToMap.includes(')}'), `${locale}: end blocks sit outside #handbook-body`);

  // level switcher: bound once per page, scroll + progress events kept
  assert(page.includes("switcher.dataset.levelReady === 'true'") && page.includes("switcher.dataset.levelReady = 'true';"), `${locale}: level switcher double-binding guard`);
  assert(page.includes("document.addEventListener('astro:page-load', initLevelSwitcher);") && /\n  initLevelSwitcher\(\);\n/.test(page), `${locale}: page-load + immediate init`);
  assert.strictEqual((page.match(/onSessionReady\(\(session\) =>/g) || []).length, 1, `${locale}: saved level applied from one place`);
  assert(page.includes("document.querySelector('.handbook-detail-title')?.scrollIntoView") && page.includes("new Event('reading-content-changed')"), `${locale}: scroll target + progress event kept`);
}
const en = read('pages/en/handbook/[slug].astro');
assert(en.indexOf("t[locale]['handbook.translationPending']") > 0 && en.indexOf("t[locale]['handbook.translationPending']") < en.indexOf('<HandbookEntryHead '), 'en: translation notice between crumb and entry');
assert(!fs.existsSync(path.join(src, 'components/newsprint/HandbookSectionNav.astro')), 'section nav deleted');

// components
const head = read('components/handbook/HandbookEntryHead.astro');
for (const s of ["'표제어'", "'Entry'", '<header class="handbook-entry">', '<h1 class="handbook-detail-title">', 'class="handbook-detail-korean"', 'class="handbook-detail-subtitle"', 'entryGrammar(locale, term)', '{grammar && <p class="handbook-entry-gram">{grammar}</p>}']) {
  assert(head.includes(s), `entry head: ${s}`);
}
const xref = read('components/handbook/HandbookXref.astro');
for (const s of ['→ 함께 볼 말', '→ See also', '→ 같은 분야', '→ Same field', '<nav class="handbook-xref" aria-label={copy.aria}>', '<span class="handbook-xref-label">', 'termNames(t, locale).name']) {
  assert(xref.includes(s), `xref: ${s}`);
}
const map = read('components/handbook/HandbookConceptMap.astro');
for (const s of ["'개념 지도'", "'Concept map'", '.slice(0, 6)', 'conceptMapNodes(items.length', '<a class="handbook-concept-map-node" href={l.href} aria-label={l.name}>', '<g class="handbook-concept-map-center" aria-hidden="true">', 'role="group"', '{links.length > 0 && (', '<h2 class="news-end-title"']) {
  assert(map.includes(s), `concept map: ${s}`);
}
assert(!map.includes('role="img"'), 'concept map is a group of links, not an image');
const news = read('components/handbook/HandbookNewsMentions.astro');
for (const s of ["'최근 뉴스에서'", "'In recent news'", 'postTypeLabel(locale, a.post_type)', '{articles.length > 0 && (', 'articles.slice(0, 5)', '<h2 class="news-end-title"']) {
  assert(news.includes(s), `news mentions: ${s}`);
}
const hero = read('components/newsprint/HandbookHeroCard.astro');
for (const s of ['뉴스에서는 이렇게 쓰여요', 'How the news uses it', 'role="heading" aria-level="2"', 'handbook-hero-card--solo', 'class="handbook-hero-card__plate"', ':global([data-theme="dark"]) .handbook-hero-card__plate']) {
  assert(hero.includes(s), `hero: ${s}`);
}
assert(/:global\(\[data-theme="dark"\]\) \.handbook-hero-card__plate \{[^}]*var\(--color-bg-tertiary\)/.test(hero), 'hero: dark plate uses bg-tertiary');
assert(/@media \(max-width: 767px\) \{\s*\.handbook-hero-card \{\s*grid-template-columns: minmax\(0, 1fr\);/.test(hero), 'hero: one column on mobile');

// CSS
const css = read('styles/global.css');
function rule(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const all = [...css.matchAll(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`, 'g'))].map((m) => m[1]);
  assert(all.length > 0, `missing CSS rule ${selector}`);
  return all[all.length - 1];
}
assert(/font-size:\s*3rem/.test(rule('.handbook-entry .handbook-detail-title')), 'headword ~3rem');
assert(/term\.korean_name\.trim\(\)\.toLowerCase\(\) !== term\.term\.trim\(\)\.toLowerCase\(\)/.test(read('components/handbook/HandbookEntryHead.astro')), 'Korean name hidden when it repeats the headword');
assert(/font-weight:\s*600/.test(rule('.handbook-entry .handbook-detail-korean')) && rule('.handbook-entry .handbook-detail-korean').includes('var(--font-heading)'), 'Korean name in Hahmlet 600');
assert(rule('.handbook-entry .handbook-detail-subtitle').includes('var(--font-masthead)'), 'full name in Newsreader');
assert(/border-bottom:\s*2px solid var\(--color-text-primary\)/.test(rule('.handbook-entry')), 'entry closes with a 2px ink rule');
assert(rule('.handbook-entry-gram').includes('var(--color-text-secondary)'), 'grammar line style');
assert(/width:\s*100%/.test(rule('.handbook-concept-map-svg')) && /height:\s*auto/.test(rule('.handbook-concept-map-svg')), 'concept map scales to the column');
assert(rule('[data-theme="dark"] .handbook-concept-map-center circle').includes('var(--color-bg-tertiary)'), 'dark centre circle uses bg-tertiary');
assert(rule('.handbook-concept-map-node:focus-visible').includes('outline'), 'map links show focus');
const mobileAt = css.indexOf('/* Handbook term entry: mobile */');
assert(mobileAt > 0, 'term entry mobile block');
const mobile = css.slice(mobileAt, css.indexOf('\n}\n', mobileAt));
assert(/\.handbook-entry \.handbook-detail-title\s*\{[^}]*font-size:\s*2\.4rem/.test(mobile), 'mobile headword 2.4rem');
assert(/\.handbook-news-mentions a\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\) auto/.test(mobile), 'mobile news rows wrap');

// unused CSS removed (Task 4): the TOC was page-only, the rail search lived in the removed rail
for (const gone of ['.handbook-toc', 'HandbookSectionNav', '.newsprint-rail-search']) {
  assert(!css.includes(gone), `unused CSS removed: ${gone}`);
}
assert(css.includes('  .handbook-search-sticky--detail {\n    display: none;'), 'desktop still hides the main-column search');

console.log('handbook-term-entry.test.cjs passed');
