const fs = require('fs');
const path = require('path');
const assert = require('assert');

const navigation = fs.readFileSync(
  path.join(process.cwd(), 'frontend/src/components/Navigation.astro'),
  'utf8',
);

const adminBlockMatch = navigation.match(/\{isAdmin && \(([\s\S]*?)\n\s*\)\}/);
assert.ok(adminBlockMatch, 'Admin dropdown block must exist');

const adminBlock = adminBlockMatch[1];
assert.ok(adminBlock.includes('href="/admin/"'), 'Admin dropdown item must link to /admin/');
assert.ok(adminBlock.includes('copy.admin'), 'Admin dropdown item must render admin label');
assert.ok(adminBlock.includes('dropdown-icon'), 'Admin dropdown item must render an icon');

console.log('navigation-admin-icon.test.cjs passed');
