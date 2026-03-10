const fs = require('fs');
const path = require('path');
const assert = require('assert');

const railPath = path.join(__dirname, '..', 'src', 'components', 'newsprint', 'HandbookListRail.astro');
const cssPath = path.join(__dirname, '..', 'src', 'styles', 'global.css');

const rail = fs.readFileSync(railPath, 'utf8');
const css = fs.readFileSync(cssPath, 'utf8');

[
  'web3',
  'ai-ml',
  'performance',
  'devops',
  'frontend-ux',
  'backend',
  'security',
  'db-data',
  'network',
  'os-core',
].forEach((slug) => {
  assert(
    rail.includes(`${slug}: {`) || rail.includes(`'${slug}': {`),
    `missing icon entry for ${slug}`,
  );
});

const labelIndex = rail.indexOf('newsprint-rail-category-label');
const iconIndex = rail.indexOf('newsprint-rail-category-icon');

assert(labelIndex !== -1, 'missing category label class usage');
assert(iconIndex !== -1, 'missing category icon class usage');
assert(iconIndex < labelIndex, 'category icon should render before the label');

assert(
  css.includes('width: 1.35rem;') && css.includes('height: 1.35rem;'),
  'category icon size should be increased to 1.35rem',
);
assert(
  css.includes('align-items: center;'),
  'category links should vertically center icon and label',
);
assert(
  !css.includes('margin-top: 0.08rem;'),
  'category icon should not be nudged down with margin-top',
);

console.log('handbook-category-icons.test: ok');
