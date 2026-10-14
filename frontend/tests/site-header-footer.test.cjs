// frontend/tests/site-header-footer.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');
const css = read('styles/global.css');
const nav = read('components/Navigation.astro');

function rule(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const m = css.match(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`));
  assert(m, `missing CSS rule ${selector}`);
  return m[1];
}

// header
const headerTag = nav.match(/<header class="site-header"[^>]*>/);
assert(headerTag, 'site-header element missing');
assert(!/style=/.test(headerTag[0]), 'site-header must not use inline background/border styles');
assert(/class="site-brand-link"[^>]*>\s*0to1log<span class="site-brand-dot" aria-hidden="true">\.<\/span>/.test(nav), 'brand must render 0to1log + accent period');
assert(rule('.site-header').includes('var(--color-bg-primary)'), 'header uses the page background');
assert(rule('.site-brand-link').includes('var(--color-text-primary)'), 'brand text is ink, not accent');
assert(rule('.site-brand-dot').includes('var(--color-accent)'), 'brand period is accent');

// dot rule shared by header bottom + footer top
assert(/\.site-header::after,\s*\.site-footer::before\s*\{[^}]*radial-gradient/.test(css), 'header/footer share one dot-rule declaration');

// current nav = dot
const active = rule('.site-nav-pill--active::after');
assert(active.includes('var(--color-accent)'), 'active nav dot is accent');
const base = rule('.site-nav-pill::after');
assert(/border-radius:\s*50%/.test(base) && /width:\s*4px/.test(base), 'nav marker is a 4px dot');

// page label
assert(!rule('.site-page-label').includes('uppercase'), 'page label must not be uppercase');

// session hydration attributes
for (const attr of ['data-auth-only', 'data-guest-only', 'data-admin-only', 'data-auth-avatar', 'data-label-user', 'data-label-guest']) {
  assert(nav.includes(attr), `Navigation must keep ${attr}`);
}

const footer = read('components/Footer.astro');
assert(/<footer class="site-footer">/.test(footer), 'footer uses .site-footer (no inline styles)');
assert(!/<footer[^>]*style=/.test(footer), 'footer must not use inline styles');
assert(/class="site-footer-brand"[^>]*>0to1log<span class="site-brand-dot" aria-hidden="true">\.<\/span>/.test(footer), 'footer brand renders 0to1log + accent period');
assert(footer.includes('AI 뉴스와 용어를 기록하는 신문'), 'footer shows the ko motto');
assert(rule('.site-footer').includes('var(--color-bg-primary)'), 'footer uses page background');
assert(!rule('.newsprint-footer-nav').includes('uppercase'), 'footer links must not be uppercase');

console.log('site-header-footer.test.cjs passed');
