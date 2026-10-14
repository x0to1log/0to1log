const fs = require('fs');
const path = require('path');
const assert = require('assert');

const navigation = fs.readFileSync(
  path.join(process.cwd(), 'frontend/src/components/Navigation.astro'),
  'utf8',
);

// Rendered for everyone and revealed by session.ts, so cached pages stay user-neutral.
const adminBlockMatch = navigation.match(/<a href="\/admin\/"[^>]*data-admin-only[^>]*>([\s\S]*?)<\/a>/);
assert.ok(adminBlockMatch, 'Admin dropdown item must exist and be gated by data-admin-only');

const adminBlock = adminBlockMatch[1];
assert.ok(adminBlock.includes('copy.admin'), 'Admin dropdown item must render admin label');
assert.ok(adminBlock.includes('dropdown-icon'), 'Admin dropdown item must render an icon');

console.log('navigation-admin-icon.test.cjs passed');
