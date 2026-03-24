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

const handbookDetail = read('src/pages/en/handbook/[slug].astro');
assert(
  handbookDetail.includes('id="handbook-body"'),
  'Handbook detail page should keep a stable handbook-body container for overflow-safe prose styling',
);

const globalCss = read('src/styles/global.css');
const tableBlock = extractBlock(globalCss, '#handbook-body table');

assert(
  tableBlock.includes('display: block;'),
  'Handbook detail tables should become block scroll containers',
);
assert(
  tableBlock.includes('overflow-x: auto;'),
  'Handbook detail tables should scroll horizontally instead of pushing the page wider',
);
assert(
  tableBlock.includes('max-width: 100%;'),
  'Handbook detail tables should never exceed the content column width',
);
assert(
  tableBlock.includes('width: max-content;'),
  'Handbook detail tables should keep their natural width inside the scroll container',
);
assert(
  tableBlock.includes('min-width: 100%;'),
  'Handbook detail tables should still fill the available width when they fit',
);
assert(
  tableBlock.includes('scrollbar-width: thin;'),
  'Handbook detail tables should use the same thin themed scrollbar treatment as other overflow surfaces',
);
assert(
  tableBlock.includes('scrollbar-color: var(--color-border) transparent;'),
  'Handbook detail tables should tint the scrollbar thumb with the active theme border color',
);
assert(
  globalCss.includes('#handbook-body table::-webkit-scrollbar { height: 6px; }'),
  'Handbook detail tables should define a compact horizontal scrollbar size on WebKit browsers',
);
assert(
  globalCss.includes('#handbook-body table::-webkit-scrollbar-thumb {\n  background: var(--color-border);'),
  'Handbook detail tables should use the themed scrollbar thumb color on WebKit browsers',
);

console.log('handbook-detail-table-overflow.test.cjs passed');
