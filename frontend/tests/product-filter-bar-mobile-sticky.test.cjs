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

function extractBlock(source, selector, fromIndex = 0) {
  const start = source.indexOf(`${selector} {`, fromIndex);
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

const filterBarBlock = extractBlock(globalCss, '.product-filter-bar');
assert(
  filterBarBlock.includes('position: sticky;'),
  'Product filter bar should stay sticky on the products page',
);
assert(
  filterBarBlock.includes('top: calc(var(--toolbar-top, 0px) + 0.25rem);'),
  'Product filter bar should stay visible with a small offset below the header',
);

const mobileStart = globalCss.indexOf('@media (max-width: 767px) {');
assert(mobileStart !== -1, 'Missing mobile media query for product filter bar');
const mobileCss = globalCss.slice(mobileStart, globalCss.indexOf('/* --- Handbook trending terms --- */', mobileStart));
const mobileTabsBlock = extractBlock(mobileCss, '.product-filter-tabs');

assert(
  !mobileTabsBlock.includes('padding-right: 2.5rem;'),
  'Mobile product filter tabs should not add extra right padding that pushes content outward',
);
assert(
  !mobileTabsBlock.includes('mask-image: linear-gradient'),
  'Mobile product filter tabs should not rely on a mask that makes the right overflow feel broken',
);
assert(
  !mobileTabsBlock.includes('-webkit-mask-image: linear-gradient'),
  'Mobile product filter tabs should not rely on a webkit mask that makes the right overflow feel broken',
);

console.log('product-filter-bar-mobile-sticky.test.cjs passed');
