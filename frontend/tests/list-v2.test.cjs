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
  'components/newsprint/NewsDeskCell.astro',
  'components/home/HomeFrontPage.astro',
  'components/newsprint/NewsprintArticleLayout.astro',
]) {
  const f = read(p);
  assert(/import \{ postTypeLabel \} from '[./]+lib\/postType\.js'/.test(f), `${p} uses postTypeLabel`);
  assert(!/'Research' : 'Business'|'RESEARCH' : 'BUSINESS'/.test(f), `${p} has no hardcoded type ternary`);
}
{
  const f = read('components/newsprint/NewsDeskCell.astro');
  assert(!/news-desk-label" style=/.test(f), 'desk label has no inline colour');
  assert(f.includes('data-post-type=') && f.includes('newsprint-card-stretched-link'), 'desk cell keeps filter/search hooks');
}
assert(!/const typeLabel = /.test(read('components/home/HomeFrontPage.astro')), 'home front page uses the shared helper');

// Task 2: 스타일 + 레일
assert(/border-bottom:\s*1px dotted var\(--color-border\)/.test(rule('.newsprint-card')), 'cards separated by dotted lines');
assert(/background(-color)?:\s*transparent|background(-color)?:\s*none/.test(rule('.newsprint-card:hover')), 'card hover has no background wash');
assert(/font-weight:\s*600/.test(rule('.newsprint-card-title')), 'card title uses Hahmlet 600');
assert(!rule('.newsprint-filter-tab').includes('uppercase'), 'tabs not uppercase');
assert(rule('.newsprint-filter-tab[aria-selected="true"]::after').includes('var(--color-accent)'), 'active tab marked by an accent dot');
assert(css.includes(".newsprint-tags-inline .newsprint-tag,\n.newsprint-article-tags .newsprint-tag {") && css.includes(".newsprint-tags-inline .newsprint-tag::before,\n.newsprint-article-tags .newsprint-tag::before {\n  content: '#';"), 'news/article tags render as #text (scoped: portfolio chips keep their pill)');
assert(/font-weight:\s*700/.test(rule('.news-desk-title')), 'desk title 700');
assert(!rule('.news-desk-label').includes('uppercase'), 'desk label not uppercase');
assert(rule('.handbook-search-sticky').includes('var(--color-bg-primary)'), 'sticky search has a solid background');
// 기존 계약 유지
assert(/min-width:\s*0/.test(rule('.newsprint-card-bottom')), 'card-bottom keeps min-width: 0');
assert(/flex-wrap:\s*wrap/.test(rule('.newsprint-tags-inline')) && /max-width:\s*100%/.test(rule('.newsprint-tags-inline')), 'tags-inline wrap contract');

console.log('list-v2.test.cjs passed');
