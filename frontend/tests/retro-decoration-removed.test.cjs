// frontend/tests/retro-decoration-removed.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const css = fs.readFileSync(path.join(src, 'styles/global.css'), 'utf8');

assert(!css.includes('::first-letter'), 'drop caps must be removed');
assert(!/\b\d+px double\b/.test(css), 'double rules must be removed');
assert(!css.includes('feTurbulence'), 'page noise texture must be removed');
assert(!css.includes('--noise-opacity'), 'noise token must be removed');

function rule(selector) {
  const m = css.match(new RegExp(`\\n${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')} \\{([\\s\\S]*?)\\n\\}`));
  assert(m, `missing ${selector}`);
  return m[1];
}
for (const sel of ['.newsprint-kicker', '.newsprint-subkicker', '.blog-masthead-kicker', '.blog-masthead-subkicker']) {
  assert(!rule(sel).includes('text-transform: uppercase'), `${sel} must not be uppercase small caps`);
}

console.log('retro-decoration-removed.test.cjs passed');
