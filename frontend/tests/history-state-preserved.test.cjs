// frontend/tests/history-state-preserved.test.cjs
// Back/forward does a full reload on this site (MainLayout), and Astro's router then restores
// scroll from history.state ({index, scrollX, scrollY}). It only saves the scroll position while
// that state exists. A script that rewrites the URL with history.replaceState(null, …) drops the
// state, so the page comes back at the top. Public pages must pass history.state through.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(full) : [full];
  });
}

const offenders = [];
for (const file of walk(src)) {
  const rel = path.relative(src, file).replace(/\\/g, '/');
  if (!/\.(astro|ts|js)$/.test(rel)) continue;
  // Admin pages do not load the view-transition router, so its state is not at stake there.
  if (rel.startsWith('pages/admin/')) continue;
  read(rel).split('\n').forEach((line, i) => {
    if (/history\.replaceState\(\s*null\b/.test(line)) offenders.push(`${rel}:${i + 1}`);
  });
}
assert.deepEqual(offenders, [], 'public scripts must not wipe history.state when rewriting the URL');

for (const file of ['components/newsprint/NewsprintCategoryFilter.astro', 'scripts/newsListSearch.ts', 'scripts/articleFind.ts']) {
  assert(read(file).includes("history.replaceState(history.state, '', url.toString());"), `${file}: URL rewrite keeps the router's history state`);
}

// Back/forward must have one handler. The layout reloads; if the view-transition router also
// handles the traversal, the two race. When the router's in-place swap finishes first it scrolls
// against the server-rendered page, the position is clamped, and its scrollend handler saves the
// clamped value over the real one before the reload happens.
const layout = read('layouts/MainLayout.astro');
const handler = layout.slice(layout.indexOf("window.addEventListener('popstate'"), layout.indexOf('window.location.reload();'));
assert(handler.length > 0 && handler.includes('event.stopImmediatePropagation();'), 'layout: the reload handler stops the router from also handling back/forward');
assert(handler.includes('astro-view-transitions-enabled'), 'layout: only where the router is loaded (admin pages keep their own popstate listeners)');
assert(layout.indexOf("window.addEventListener('popstate'") < layout.indexOf('<ViewTransitions />'), 'layout: the reload handler is registered before the router, so it runs first');

// Lists that a tab or search reshapes: the target is captured while the page is parsed (before the
// router can clamp and re-save it) and applied again once the list has settled.
const deskList = read('components/newsprint/NewsDeskList.astro');
assert(deskList.includes('window.__newsListScrollY = (history.state && history.state.scrollY) || 0;'), 'news list: scroll target captured by the inline script');
const mode = read('scripts/newsDeskMode.ts');
assert(/function update\(\): void \{[\s\S]*?reapplyScroll\(\);\s*\n\}/.test(mode), 'news list: saved position re-applied whenever the list settles');
assert(mode.includes('captured.__newsListScrollY = 0;'), 'news list: the captured target is used once');
assert(/for \(const type of \['wheel', 'touchstart', 'keydown', 'pointerdown'\]\)/.test(mode), "news list: the reader's own input cancels a pending restore");

console.log('history-state-preserved.test.cjs passed');
