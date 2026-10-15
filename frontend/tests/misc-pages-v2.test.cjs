// frontend/tests/misc-pages-v2.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');
const style = (f) => (f.match(/<style[^>]*>([\s\S]*?)<\/style>/) || [, ''])[1];

// Task 1
for (const p of ['pages/ko/about/index.astro', 'pages/en/about/index.astro']) {
  const s = style(read(p));
  assert(!/text-transform:\s*uppercase/.test(s), `${p}: no uppercase labels`);
  assert(!/letter-spacing:\s*0\.(1|2)\d*em/.test(s), `${p}: no wide tracking`);
}
for (const p of ['pages/ko/privacy/index.astro', 'pages/en/privacy/index.astro', 'pages/ko/terms/index.astro', 'pages/en/terms/index.astro', 'pages/404.astro']) {
  const s = style(read(p));
  assert(!/text-transform:\s*uppercase/.test(s), `${p}: no uppercase`);
  assert(!/font-weight:\s*(800|900)/.test(s), `${p}: no 800/900 weights (Hahmlet loads 600/700)`);
}

// Task 2
const css = read('styles/global.css');
function rule(selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const all = [...css.matchAll(new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`, 'g'))].map((m) => m[1]);
  assert(all.length > 0, `missing CSS rule ${selector}`);
  return all[all.length - 1];
}
const tab = rule('.library-tab');
assert(!/text-transform:\s*uppercase/.test(tab) && !/font-weight:\s*800/.test(tab), 'library tabs: no uppercase / 800');
assert(css.includes('.library-tab--active::after') || css.includes('.library-tab[aria-selected="true"]::after'), 'active library tab marked by a dot');
assert(!/font-weight:\s*800/.test(rule('.pf-name')), 'portfolio name uses a loaded weight');
assert(!/text-transform:\s*uppercase/.test(rule('.pf-overline')), 'portfolio overline not uppercase');
for (const p of ['pages/settings/index.astro', 'pages/settings/webhooks.astro']) {
  assert(!/text-transform:\s*uppercase/.test(style(read(p))), `${p}: no uppercase labels`);
}

console.log('misc-pages-v2.test.cjs passed');
