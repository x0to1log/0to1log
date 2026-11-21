// frontend/tests/news-article-reading.test.cjs
// News article reading pass: bold clean-up wired into the news render path only,
// newsReading layout mode, scoped prose typography, hide-on-scroll-down bars.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

// --- bold clean-up wiring ---
const detail = read('lib/pageData/newsDetailPage.ts');
assert(detail.includes("import { normalizeNewsBold } from '../newsBold.js';"), 'news detail imports the bold clean-up');
assert(detail.includes('renderMarkdownWithTerms(normalizeNewsBold(md), handbookTermsMap)') && detail.includes('renderMarkdown(normalizeNewsBold(md))'), 'both render branches normalise bold first');
assert(!read('lib/markdown.ts').includes('normalizeNewsBold'), 'shared renderer stays untouched (blog, products, handbook)');

// --- crumb: desk + reading time ---
const shell = read('components/newsprint/NewsprintShell.astro');
assert(/crumbDesk\?: string;/.test(shell) && /crumbReading\?: string;/.test(shell), 'shell: optional crumb props');
assert(shell.includes('{crumbDesk && <span class="newsprint-crumb-desk">{crumbDesk}</span>}') && shell.includes('{crumbReading && <span>{crumbReading}</span>}'), 'shell: desk before the issue, reading time after the date');
assert(shell.includes('{crumbItems ? (') && shell.includes('issueLabel(locale, issueNumber(displayDate))'), 'shell: strings other tests assert are intact');

const pages = { ko: read('pages/ko/news/[slug].astro'), en: read('pages/en/news/[slug].astro') };
for (const [locale, page] of Object.entries(pages)) {
  assert(page.includes("import { postTypeLabel } from '../../../lib/postType.js';"), `${locale}: desk label from lib/postType.js`);
  assert(page.includes('crumbDesk={crumbDesk}') && page.includes('crumbReading={crumbReading}'), `${locale}: crumb props passed`);
}
assert(pages.ko.includes('`${deskBase} 데스크`') && pages.ko.includes('`읽는 데 ${post.reading_time_min}분`'), 'ko: crumb copy');
assert(pages.en.includes('`${deskBase} desk`') && pages.en.includes('`${post.reading_time_min} min read`'), 'en: crumb copy');

// --- layout: newsReading mode ---
const layout = read('components/newsprint/NewsprintArticleLayout.astro');
assert(/newsReading\?: boolean;/.test(layout) && /newsReading = false,/.test(layout), 'layout: newsReading prop, off by default');
assert(layout.includes("class={`newsprint-article${newsReading ? ' newsprint-article--news' : ''}`}"), 'layout: scope class on the article root');
assert(/\{!newsReading && \(\s*<div class="newsprint-article-topline">/.test(layout), 'layout: topline only outside newsReading');
assert(layout.includes('{!newsReading && tags && tags.length > 0 && ('), 'layout: head tags only outside newsReading');
assert(layout.includes('{!newsReading && <div class="newsprint-divider"></div>}'), 'layout: head divider only outside newsReading');
assert(layout.includes("<div class={newsReading ? 'news-edition-bar' : undefined}>"), 'layout: edition bar wrapper');
assert(layout.includes('{!newsReading && <div class="switcher-bar-line"></div>}'), 'layout: switcher rules only outside newsReading');
const endTags = layout.indexOf('class="newsprint-article-tags newsprint-article-tags--end"');
assert(endTags > layout.indexOf('<slot name="after-guide" />') && endTags < layout.indexOf('class="newsprint-sources"'), 'layout: tags move to the end, between the slot and sources');
for (const s of ['리서치 데스크의 시선 →', '비즈니스 데스크의 시선 →', "The research desk's take →", "The business desk's take →"]) {
  assert(layout.includes(s), `layout copy: ${s}`);
}
for (const [locale, page] of Object.entries(pages)) {
  assert(/<NewsprintArticleLayout[\s\S]*?\n\s+newsReading\s*\n/.test(page), `${locale}: public news page turns newsReading on`);
}
for (const p of ['pages/admin/news/edit/[slug].astro', 'pages/admin/blog/edit/[slug].astro']) {
  assert(!read(p).includes('newsReading'), `${p}: admin editors do not pass newsReading`);
}

// --- CSS: head ---
const css = read('styles/global.css');
function block(selector) {
  const at = css.indexOf(`\n${selector} {`);
  assert(at > 0, `css rule exists: ${selector}`);
  return css.slice(at, css.indexOf('}', at));
}
assert(/color:\s*var\(--color-accent\)/.test(block('.newsprint-crumb-desk')), 'crumb desk in accent');
assert(/font-size:\s*1\.125rem/.test(block('.newsprint-article--news .newsprint-deck')) && /word-break:\s*keep-all/.test(block('.newsprint-article--news .newsprint-deck')), 'deck: 18px, keep-all');
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(block('.news-edition-bar')), 'edition bar: heavy top rule');
assert(/background:\s*var\(--color-text-primary\)/.test(block('.news-edition-bar .persona-switcher-btn--active')), 'edition bar: active segment inverted');
assert(/background:\s*none/.test(block('.newsprint-article--news .news-briefing')), 'briefing: no box');
assert(/grid-template-columns:\s*minmax\(0, 1fr\)/.test(block('.newsprint-article--news .news-briefing-list')), 'briefing: one column list');
assert(/font-size:\s*1\.0625rem/.test(block('.newsprint-article--news .news-briefing-list li')), 'briefing: body-size text');

console.log('news-article-reading.test.cjs passed');
