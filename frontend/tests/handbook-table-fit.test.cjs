// frontend/tests/handbook-table-fit.test.cjs
// Handbook tables on a phone: tighter cells for every table, and only a table that still does not
// fit is marked data-fit="tight" by a script and allowed to break inside a word. Breaking is never
// allowed for all tables at once: that makes the browser squeeze columns that had room.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8').replace(/\r\n/g, '\n');

const css = read('styles/global.css');
const phone = css.match(/@media \(max-width: 640px\) \{\s*#handbook-body table \{([^}]*)\}\s*#handbook-body th,\s*#handbook-body td \{([^}]*)\}\s*\}/);
assert(phone, 'phone rule: table font size and cell padding');
assert(/font-size:\s*0\.86em;/.test(phone[1]), 'phone: smaller table text');
assert(/padding:\s*0\.45rem 0\.5rem;/.test(phone[2]), 'phone: tighter cells');

const tight = css.match(/#handbook-body table\[data-fit="tight"\] th,\s*#handbook-body table\[data-fit="tight"\] td \{([^}]*)\}/);
assert(tight, 'tight rule exists');
assert(/overflow-wrap:\s*anywhere;/.test(tight[1]), 'a tight table may break inside a word');
assert(/#handbook-body table\[data-fit="tight"\] th:first-child,\s*#handbook-body table\[data-fit="tight"\] td:first-child \{\s*overflow-wrap:\s*break-word;/.test(css), 'tight: the row-label column keeps its words whole');
const anywhereOnAllCells = /#handbook-body t[hd][^{[]*\{[^}]*overflow-wrap:\s*anywhere/.test(css.replace(tight[0], ''));
assert(!anywhereOnAllCells, 'breaking inside words is not allowed for every table');

const script = read('scripts/handbookTableFit.ts');
assert(script.includes("'#handbook-body table'"), 'script: handbook tables only');
assert(/removeAttribute\('data-fit'\)/.test(script) && /scrollWidth - table\.clientWidth > 1/.test(script) && /setAttribute\('data-fit', 'tight'\)/.test(script), 'script: measure loose first, then mark what overflows');
for (const event of ['astro:page-load', 'reading-content-changed', 'resize']) {
  assert(script.includes(`'${event}'`), `script: refits on ${event}`);
}

for (const locale of ['ko', 'en']) {
  assert(read(`pages/${locale}/handbook/[slug].astro`).includes("import '../../../scripts/handbookTableFit';"), `${locale}: page loads the script`);
}

console.log('handbook-table-fit: ok');
