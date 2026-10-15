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

console.log('misc-pages-v2.test.cjs passed');
