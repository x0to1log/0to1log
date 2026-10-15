const fs = require('fs');
const path = require('path');
const assert = require('assert');

const css = fs.readFileSync(path.join(__dirname, '..', 'src/styles/global.css'), 'utf8');

function block(name) {
  const m = css.match(new RegExp(`\\[data-theme="${name}"\\] \\{([\\s\\S]*?)\\r?\\n\\}`));
  assert(m, `missing ${name} theme block`);
  return m[1];
}
function token(b, name) {
  const m = b.match(new RegExp(`\\s${name}:\\s*(#[0-9A-Fa-f]{6})\\s*;`));
  assert(m, `missing ${name}`);
  return m[1];
}
function lum(hex) {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
function ratio(a, b) {
  const [x, y] = [lum(a), lum(b)];
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}

const expected = {
  light: { '--color-bg-primary': '#F7F4EE', '--color-text-primary': '#24211D', '--color-accent': '#B4472A' },
  white: { '--color-bg-primary': '#FFFFFF', '--color-text-primary': '#16181B', '--color-accent': '#2448A8' },
  dark: { '--color-bg-primary': '#181715', '--color-text-primary': '#ECE7DD', '--color-accent': '#E3774F' },
};

for (const [theme, values] of Object.entries(expected)) {
  const b = block(theme);
  for (const [k, v] of Object.entries(values)) assert.strictEqual(token(b, k).toUpperCase(), v, `${theme} ${k}`);

  // WCAG AA: 작은 텍스트로 쓰이는 토큰은 주요 배경 3종 위에서 4.5:1 이상
  for (const fg of ['--color-text-primary', '--color-text-secondary', '--color-text-muted', '--color-accent']) {
    for (const bg of ['--color-bg-primary', '--color-bg-secondary', '--color-bg-card']) {
      const r = ratio(token(b, fg), token(b, bg));
      assert(r >= 4.5, `${theme}: ${fg} on ${bg} is ${r.toFixed(2)}:1 (< 4.5)`);
    }
  }
  // Grey buttons/cards (cookie banner, login features) put body text on bg-tertiary
  for (const fg of ['--color-text-secondary', '--color-text-muted']) {
    const r = ratio(token(b, fg), token(b, '--color-bg-tertiary'));
    assert(r >= 4.5, `${theme}: ${fg} on --color-bg-tertiary is ${r.toFixed(2)}:1 (< 4.5)`);
  }
  // Code tokens (except punctuation) on the code background
  for (const t of ['keyword', 'string', 'function', 'comment', 'constant']) {
    const r = ratio(token(b, `--shiki-token-${t}`), token(b, '--color-bg-tertiary'));
    assert(r >= 4.5, `${theme}: --shiki-token-${t} on bg-tertiary is ${r.toFixed(2)}:1 (< 4.5)`);
  }
  // Status colors on primary/secondary backgrounds
  for (const fg of ['--color-success', '--color-warning', '--color-error']) {
    for (const bg of ['--color-bg-primary', '--color-bg-secondary']) {
      const r = ratio(token(b, fg), token(b, bg));
      assert(r >= 4.5, `${theme}: ${fg} on ${bg} is ${r.toFixed(2)}:1 (< 4.5)`);
    }
  }
  assert(!b.includes('--noise-opacity'),`${theme}: noise token must be removed`);
}

assert(!/\[data-theme="(pink|midnight)"\]/.test(css), 'retired theme selectors must be removed');
console.log('theme-palette.test.cjs passed');
