// frontend/tests/article-v2.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');
const layout = read('components/newsprint/NewsprintArticleLayout.astro');
const css = read('styles/global.css');
function rule(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const m = css.match(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`));
  assert(m, `missing CSS rule ${selector}`);
  return m[1];
}

// Task 1: 판 라벨 + 스위처
assert(/ko:\s*\{\s*beginner:\s*'입문판',\s*learner:\s*'학습판',\s*expert:\s*'전문판'\s*\}/.test(layout), 'ko edition labels');
assert(/en:\s*\{\s*beginner:\s*'Beginner',\s*learner:\s*'Learner',\s*expert:\s*'Expert'\s*\}/.test(layout), 'en labels unchanged');
assert(layout.includes("{locale === 'ko' ? '판 선택' : 'Edition'}"), 'switcher label reads 판 선택 / Edition');
assert(layout.includes("(['beginner', 'learner', 'expert'] as const)"), 'persona values unchanged');
assert(layout.includes('onSessionReady') && layout.includes('session.persona'), 'session persona hydration kept');
assert(!rule('.switcher-bar-label').includes('uppercase'), 'switcher label not uppercase');
assert(/border:\s*none/.test(rule('.persona-switcher')), 'switcher has no box border');
assert(/width:\s*4px/.test(rule('.persona-switcher-btn--active::after')) && rule('.persona-switcher-btn--active::after').includes('var(--color-accent)'), 'active edition marked by an accent dot');

// Task 2: 머리 / 섹션 제목 / 핵심 팩트
assert(!/newsprint-article-kicker"\s+style=/.test(layout), 'kicker uses the accent from CSS, no inline category color');
const deckIdx = layout.indexOf('<p class="newsprint-deck">');
const tagsIdx = layout.indexOf('<div class="newsprint-article-tags">');
assert(deckIdx > 0 && tagsIdx > deckIdx, 'tags render below the deck');
assert(!rule('.newsprint-card-kicker').includes('uppercase'), 'kicker not uppercase');
assert(/clip-path:\s*none/.test(rule('.newsprint-card-kicker-type')), 'type badge drops the arrow shape');
assert(!/\n\.newsprint-card-kicker-type::before/.test(css) && css.includes('.newsprint-card-kicker .newsprint-card-kicker-type::before'), 'middle dot only inside a kicker (rails use kicker-type standalone)');
assert(/font-weight:\s*700/.test(rule('.newsprint-lead-title')), 'lead title uses a loaded Hahmlet weight');
assert(/height:\s*1px/.test(rule('.newsprint-divider')), 'divider is a hairline');
assert(!rule('.newsprint-section-title').includes('uppercase'), 'section titles not uppercase');
assert(!rule('.newsprint-guide-label').includes('uppercase'), 'guide labels not uppercase');
assert(/border-bottom:\s*1px dotted/.test(rule('.newsprint-fact-pack-item')), 'fact pack items separated by dotted lines');
assert(/box-shadow:\s*none/.test(rule('.newsprint-fact-pack-item')), 'fact pack items are not cards');

console.log('article-v2.test.cjs passed');
