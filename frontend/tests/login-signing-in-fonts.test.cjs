const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');

function read(relPath) {
  return fs.readFileSync(path.join(root, relPath), 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function extractBlock(source, selector) {
  const start = source.indexOf(`${selector} {`);
  assert(start !== -1, `Missing CSS block for ${selector}`);

  const bodyStart = source.indexOf('{', start);
  let depth = 0;

  for (let index = bodyStart; index < source.length; index += 1) {
    const char = source[index];
    if (char === '{') depth += 1;
    if (char === '}') depth -= 1;
    if (depth === 0) {
      return source.slice(bodyStart + 1, index);
    }
  }

  throw new Error(`Unclosed CSS block for ${selector}`);
}

const callbackPage = read('src/pages/auth/callback.astro');
assert(
  callbackPage.includes('font-size: clamp(1.75rem, 6vw, 2.1rem);'),
  'Signing-in callback text should use a larger responsive font size',
);

const globalCss = read('src/styles/global.css');
const oauthButtonBlock = extractBlock(globalCss, '.login-oauth-btn');
assert(
  oauthButtonBlock.includes('font-size: 1rem;'),
  'OAuth buttons should use a larger base font size so the signing-in state remains readable',
);

console.log('login-signing-in-fonts.test.cjs passed');
