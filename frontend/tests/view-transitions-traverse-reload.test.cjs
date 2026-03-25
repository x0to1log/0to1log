const fs = require('fs');
const path = require('path');
const assert = require('assert');

function read(relativePath) {
  return fs.readFileSync(path.join(process.cwd(), relativePath), 'utf8');
}

const layout = read('frontend/src/layouts/MainLayout.astro');

assert.ok(
  layout.includes("window.addEventListener('popstate'"),
  'MainLayout.astro must hard-reload on browser history traversal via popstate',
);

assert.ok(
  layout.includes('window.location.reload()'),
  'MainLayout.astro must reload the current URL on back/forward traversal',
);

assert.ok(
  !layout.includes("document.addEventListener('astro:before-preparation'"),
  'MainLayout.astro must not trap traverse navigation in astro:before-preparation',
);

assert.ok(
  !layout.includes('new Promise(function() { window.location.reload(); })'),
  'MainLayout.astro must not use a never-resolving reload loader for traverse navigation',
);

console.log('view-transitions-traverse-reload.test.cjs passed');
