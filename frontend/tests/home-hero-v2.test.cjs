// frontend/tests/home-hero-v2.test.cjs
// Masthead/dateline moved from the old split hero into HomeFrontPage; typewriter + split hero styles are gone.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const front = fs.readFileSync(path.join(src, 'components/home/HomeFrontPage.astro'), 'utf8');
const css = fs.readFileSync(path.join(src, 'styles/global.css'), 'utf8');
function rule(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const m = css.match(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`));
  assert(m, `missing CSS rule ${selector}`);
  return m[1];
}

assert(front.includes('AI 뉴스와 용어를 기록하는 신문'), 'ko motto in the dateline');
assert(/import \{ issueLabel, issueNumber \} from '\.\.\/\.\.\/lib\/issue\.js'/.test(front), 'issue number uses lib/issue.js');
assert(/todayCount\?: number/.test(front), 'front page accepts todayCount');
assert(/todayCount > 0 \?/.test(front), '"오늘 N건" only when there are stories today');

assert(rule('.home-front-masthead').includes('var(--font-masthead)'), 'masthead uses Newsreader');
assert(rule('.home-front-masthead').includes('lining-nums'), 'masthead digits are lining (0to1, not oto1)');
assert(rule('.home-front-masthead').includes('var(--color-text-primary)'), 'masthead is ink');
assert(/border-top:\s*2px solid var\(--color-text-primary\)/.test(rule('.home-front-dateline')), 'dateline double rule (top)');
assert(/font-weight:\s*700/.test(rule('.home-front-lead-title')), 'lead title uses a loaded Hahmlet weight');

assert(!/home-split-hero|home-type-|home-cursor-blink/.test(css), 'split hero + typewriter styles removed');
assert(!/data-type-words/.test(front), 'no typewriter markup');
console.log('home-hero-v2.test.cjs passed');
