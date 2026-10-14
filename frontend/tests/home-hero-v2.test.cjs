// frontend/tests/home-hero-v2.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const hero = fs.readFileSync(path.join(src, 'components/home/HomeSplitHero.astro'), 'utf8');
const css = fs.readFileSync(path.join(src, 'styles/global.css'), 'utf8');
function rule(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const m = css.match(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`));
  assert(m, `missing CSS rule ${selector}`);
  return m[1];
}

assert(/class="home-split-hero-wordmark"[^>]*>0to1log<span class="site-brand-dot" aria-hidden="true">\.<\/span>/.test(hero), 'wordmark gets the accent period');
assert(hero.includes('AI 뉴스와 용어를 기록하는 신문'), 'ko motto');
assert(/import \{ issueLabel, issueNumber \} from '\.\.\/\.\.\/lib\/issue\.js'/.test(hero), 'issue line uses lib/issue.js');
assert(/todayCount\?: number/.test(hero), 'hero accepts todayCount');
assert(/todayCount > 0 &&/.test(hero), '"오늘 N건" only when there are stories today');
assert(hero.includes('class="home-split-hero-issue"'), 'issue line element');

assert(rule('.home-split-hero-wordmark').includes('var(--color-text-primary)'), 'wordmark is ink');
assert(!/min-height:\s*calc\(100svh/.test(rule('.home-split-hero')), 'hero no longer fills the viewport (front strip follows)');
assert(/font-weight:\s*700/.test(rule('.home-split-hero-headline')), 'headline uses a loaded Hahmlet weight');
assert(rule('.home-type-target').includes('var(--color-accent)'), 'typed word is accent');
assert(/@media \(max-width: 639px\)\s*\{[^}]*\.home-split-hero-sub\s*\{\s*display:\s*none;/.test(css), 'sub copy hidden on small screens');
console.log('home-hero-v2.test.cjs passed');
