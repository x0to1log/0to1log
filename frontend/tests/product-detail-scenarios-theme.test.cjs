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

const globalCss = read('src/styles/global.css');
const scenarioLine = globalCss
  .split('\n')
  .find((line) => line.includes('.product-detail-scenario {'));

assert(scenarioLine, 'Scenario card styles should exist');
assert(
  scenarioLine.includes('background: var(--color-bg-secondary'),
  'Scenario cards should use the theme background surface instead of a hard white fill',
);
assert(
  !scenarioLine.includes('#fff'),
  'Scenario cards should not fall back to a hard-coded white background',
);

console.log('product-detail-scenarios-theme.test.cjs passed');
