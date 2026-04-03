const fs = require('fs');
const path = require('path');

function read(filePath) {
  return fs.readFileSync(path.join(__dirname, '..', filePath), 'utf8');
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

const headline = read('src/components/newsprint/NewsprintHeadline.astro');
assert(
  headline.includes('<span class="newsprint-tags-inline">'),
  'NewsprintHeadline should keep rendering headline tags through the shared inline tag row',
);

const globalCss = read('src/styles/global.css');
const cardBottomBlock = extractBlock(globalCss, '.newsprint-card-bottom');
assert(
  cardBottomBlock.includes('min-width: 0;'),
  'News headline meta row should be allowed to shrink instead of forcing the card wider than the viewport',
);

const tagsInlineBlock = extractBlock(globalCss, '.newsprint-tags-inline');
assert(
  tagsInlineBlock.includes('flex-wrap: wrap;'),
  'Inline news tags should wrap onto multiple lines when there are too many to fit on mobile',
);
assert(
  tagsInlineBlock.includes('max-width: 100%;'),
  'Inline news tags should stay bound to the card width on small screens',
);

console.log('news-headline-mobile-tags-wrap.test.cjs passed');
