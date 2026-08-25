const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');

const navigation = read('src/components/Navigation.astro');
const notFound = read('src/pages/404.astro');
const astroConfig = read('astro.config.mjs');

assert(
  !navigation.includes('data-astro-prefetch="viewport"'),
  'Primary navigation must not prefetch every visible destination',
);
assert(
  !notFound.includes('data-astro-prefetch="viewport"'),
  '404 recovery links must not prefetch every visible destination',
);
assert(
  astroConfig.includes("defaultStrategy: 'hover'"),
  'Astro prefetch must remain intent-driven through the hover strategy',
);

console.log('public-prefetch-budget.test.cjs passed');
