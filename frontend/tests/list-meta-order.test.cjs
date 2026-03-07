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

function assertBefore(source, firstNeedle, secondNeedle, message) {
  const firstIndex = source.indexOf(firstNeedle);
  const secondIndex = source.indexOf(secondNeedle);
  assert(firstIndex !== -1, `Missing expected snippet: ${firstNeedle}`);
  assert(secondIndex !== -1, `Missing expected snippet: ${secondNeedle}`);
  assert(firstIndex < secondIndex, message);
}

const listCard = read('src/components/newsprint/NewsprintListCard.astro');
assertBefore(
  listCard,
  '<div class="newsprint-meta" style="margin-top: 0.5rem;">',
  '<div class="newsprint-tags">',
  'NewsprintListCard must render date/meta before tags',
);

const enIndex = read('src/pages/en/log/index.astro');
assertBefore(
  enIndex,
  '<div class="newsprint-meta">',
  '<div class="newsprint-tags">',
  'EN featured card must render date/meta before tags',
);

const koIndex = read('src/pages/ko/log/index.astro');
assertBefore(
  koIndex,
  '<div class="newsprint-meta">',
  '<div class="newsprint-tags">',
  'KO featured card must render date/meta before tags',
);
