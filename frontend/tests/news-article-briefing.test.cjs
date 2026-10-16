// frontend/tests/news-article-briefing.test.cjs
// News detail B+C: crumb shell, no rail, briefing, same-day twin link, end blocks.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');
const css = read('styles/global.css');

for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/news/[slug].astro`);
  assert(/<NewsprintShell[\s\S]*?compact[\s\S]*?rail=\{false\}/.test(page), `${locale}: compact shell without rail`);
  assert(!page.includes('showStickyActions={false}'), `${locale}: inline reading actions on`);
  assert(!/NewsprintTOC|NewsprintSideRail|ReadingActionsRail|slot="rail"/.test(page), `${locale}: rail removed`);
  assert(page.includes('briefingItems={focusItemsAreFallback ? [] : focusItems}') && page.includes('sibling={sibling}'), `${locale}: briefing + sibling wired`);
  assert(page.includes('slot="after-guide"') && page.includes('<NewsArticleTerms') && page.includes('<NewsTwinDesks'), `${locale}: end blocks in the layout slot`);
  assert(page.includes('<NewsReadNext'), `${locale}: read next`);
  assert(!/masthead=|editionMap|subkicker=/.test(page), `${locale}: no masthead props`);
  assert(page.includes(locale === 'ko' ? "backLabel=\"AI 뉴스\"" : "backLabel=\"AI News\""), `${locale}: crumb label`);
}

const shell = read('components/newsprint/NewsprintShell.astro');
assert(/compact\?: boolean/.test(shell) && /masthead\?: string/.test(shell), 'shell: compact prop, optional masthead');
assert(shell.includes('class="newsprint-crumb"') && shell.includes('newsprint-main--article'), 'shell: crumb + article column');

const layout = read('components/newsprint/NewsprintArticleLayout.astro');
assert(/briefingItems\?: string\[\];/.test(layout) && /sibling\?: \{/.test(layout), 'layout: new optional props');
const idx = ['newsprint-twin-link', 'class="switcher-bar"', 'class="news-briefing"', 'class="newsprint-article-find"'].map((s) => layout.indexOf(s));
assert(idx.every((i) => i > 0) && idx[0] < idx[1] && idx[1] < idx[2] && idx[2] < idx[3], 'order: twin link → edition switcher → briefing → find');
const slotAt = layout.indexOf('<slot name="after-guide" />');
assert(slotAt > layout.indexOf('class="newsprint-guide-items"') && slotAt < layout.indexOf('class="newsprint-sources"'), 'after-guide slot sits between guide items and sources');
for (const s of ['30초 브리핑', '30-second briefing', '리서치 데스크는 이렇게 봤어요', "The research desk's take", '비즈니스 데스크는 이렇게 봤어요', "The business desk's take"]) {
  assert(layout.includes(s), `layout copy: ${s}`);
}

const terms = read('components/newsprint/NewsArticleTerms.astro');
assert(terms.includes("{isKo ? '이 기사의 용어' : 'Terms in This Article'}"), 'terms block title');
const twin = read('components/newsprint/NewsTwinDesks.astro');
for (const s of ['이 소식, 두 데스크의 시선', 'Two desks on this story', '지금 읽은 글', 'You just read']) assert(twin.includes(s), `twin copy: ${s}`);
assert(twin.includes('postTypeLabel(locale, '), 'twin labels from lib/postType.js');
const next = read('components/newsprint/NewsReadNext.astro');
assert(next.includes("{isKo ? '다음 읽어볼 글' : 'Read Next'}") && next.includes('postTypeLabel(locale, '), 'read next title + shared labels');

assert(/\.newsprint-main--article\s*\{[^}]*max-width:\s*800px/.test(css), '800px article column');
assert(/\.news-briefing-list\s*\{[^}]*grid-template-columns:\s*repeat\(3, minmax\(0, 1fr\)\)/.test(css), 'briefing: three columns');
assert(/@media \(max-width: 767px\)\s*\{[^}]*\.news-briefing-list\s*\{\s*grid-template-columns:\s*minmax\(0, 1fr\)/.test(css), 'briefing: one column on phones');
assert(/\.newsprint-twin-link--business\s*\{\s*--desk:\s*var\(--tier-paid\);/.test(css) && /\.newsprint-twin-link--research\s*\{\s*--desk:\s*var\(--tier-freemium\);/.test(css), 'twin link desk colours');
console.log('news-article-briefing.test.cjs passed');
