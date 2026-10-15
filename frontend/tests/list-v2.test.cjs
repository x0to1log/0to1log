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

console.log('list-v2.test.cjs passed');
