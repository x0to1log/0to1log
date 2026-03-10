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

const enIndex = read('src/pages/en/log/index.astro');
const koIndex = read('src/pages/ko/log/index.astro');

assert(
  enIndex.includes(".order('created_at', { ascending: false })"),
  'EN public AI News list must order posts by created_at DESC',
);
assert(
  koIndex.includes(".order('created_at', { ascending: false })"),
  'KO public AI News list must order posts by created_at DESC',
);

assert(
  !enIndex.includes(".order('published_at', { ascending: false })"),
  'EN public AI News list must not order by published_at DESC anymore',
);
assert(
  !koIndex.includes(".order('published_at', { ascending: false })"),
  'KO public AI News list must not order by published_at DESC anymore',
);
