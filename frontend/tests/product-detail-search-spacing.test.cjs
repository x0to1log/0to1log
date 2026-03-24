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

const globalCss = read('src/styles/global.css');
const productPageBlock = extractBlock(globalCss, '.product-detail-page');
const productSearchBlock = extractBlock(globalCss, '.product-detail-search');

assert(
  productPageBlock.includes('padding-top: 1rem;'),
  'Product detail page should add enough top padding so the sticky search does not hug the top edge',
);
assert(
  productSearchBlock.includes('margin: 0 auto 0.75rem;'),
  'Product detail search should keep a roomier bottom gap like other detail search bars',
);

console.log('product-detail-search-spacing.test.cjs passed');
