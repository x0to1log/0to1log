const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');
const css = read('styles/global.css');
function rule(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const m = css.match(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`));
  assert(m, `missing CSS rule ${selector}`);
  return m[1];
}

// Task 1: 유형 라벨 단일화, inline 카테고리 색 제거
for (const p of [
  'components/newsprint/NewsprintListCard.astro',
  'components/newsprint/NewsprintHeadline.astro',
  'components/newsprint/NewsprintListRail.astro',
  'components/home/HomeFrontPage.astro',
  'components/newsprint/NewsprintArticleLayout.astro',
]) {
  const f = read(p);
  assert(/import \{ postTypeLabel \} from '[./]+lib\/postType\.js'/.test(f), `${p} uses postTypeLabel`);
  assert(!/'Research' : 'Business'|'RESEARCH' : 'BUSINESS'/.test(f), `${p} has no hardcoded type ternary`);
}
for (const p of ['components/newsprint/NewsprintListCard.astro', 'components/newsprint/NewsprintHeadline.astro']) {
  const f = read(p);
  assert(!/newsprint-card-kicker" style=/.test(f), `${p} kicker has no inline category color`);
  assert(f.includes('data-post-type=') && f.includes('newsprint-card-stretched-link'), `${p} keeps filter/search hooks`);
}
assert(!read('components/newsprint/NewsprintHeadline.astro').includes('◆'), 'headline drops the ◆ HEADLINE label');
assert(!/const typeLabel = /.test(read('components/home/HomeFrontPage.astro')), 'home front page uses the shared helper');

// Task 2: 스타일 + 레일
const railSrc = read('components/newsprint/NewsprintListRail.astro');
assert(railSrc.includes("{isKo ? '최신 기사' : 'Latest'}"), 'rail section is honestly named 최신 기사');
assert(railSrc.includes('class="newsprint-rail-rank"'), 'rail items are numbered');
assert(/border-bottom:\s*1px dotted var\(--color-border\)/.test(rule('.newsprint-card')), 'cards separated by dotted lines');
assert(/background(-color)?:\s*transparent|background(-color)?:\s*none/.test(rule('.newsprint-card:hover')), 'card hover has no background wash');
assert(/font-weight:\s*600/.test(rule('.newsprint-card-title')), 'card title uses Hahmlet 600');
assert(!rule('.newsprint-filter-tab').includes('uppercase'), 'tabs not uppercase');
assert(rule('.newsprint-filter-tab[aria-selected="true"]::after').includes('var(--color-accent)'), 'active tab marked by an accent dot');
assert(css.includes(".newsprint-tags-inline .newsprint-tag,\n.newsprint-article-tags .newsprint-tag {") && css.includes(".newsprint-tags-inline .newsprint-tag::before,\n.newsprint-article-tags .newsprint-tag::before {\n  content: '#';"), 'news/article tags render as #text (scoped: portfolio chips keep their pill)');
assert(/font-weight:\s*700/.test(rule('.newsprint-headline-title')), 'headline title 700');
assert(!rule('.newsprint-headline-kicker').includes('uppercase'), 'headline kicker not uppercase');
assert(rule('.handbook-search-sticky').includes('var(--color-bg-primary)'), 'sticky search has a solid background');
// 기존 계약 유지
assert(/min-width:\s*0/.test(rule('.newsprint-card-bottom')), 'card-bottom keeps min-width: 0');
assert(/flex-wrap:\s*wrap/.test(rule('.newsprint-tags-inline')) && /max-width:\s*100%/.test(rule('.newsprint-tags-inline')), 'tags-inline wrap contract');

console.log('list-v2.test.cjs passed');
