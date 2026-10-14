const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

const layout = read('layouts/MainLayout.astro');
const callback = read('pages/auth/callback.astro');
const bootTag = /<script\b(?=[^>]*\bis:inline\b)(?=[^>]*\bnonce=)(?=[^>]*set:html=\{THEME_BOOT_SCRIPT\})[^>]*>/;
for (const [name, file] of [['MainLayout', layout], ['auth/callback', callback]]) {
  assert(/import\s*\{[^}]*\bTHEME_BOOT_SCRIPT\b[^}]*\}\s*from\s*['"][^'"]*lib\/theme\.js['"]/.test(file), name + ' must import THEME_BOOT_SCRIPT from lib/theme.js');
  assert(bootTag.test(file), name + ' must inline the shared boot script with a CSP nonce');
}
assert(!layout.includes("localStorage.getItem('theme')"), 'MainLayout must not keep its own theme logic');

const head = read('components/Head.astro');
assert(/<meta name="theme-color" content={THEME_COLORS.light}/.test(head), 'Head must derive the default theme-color from THEME_COLORS.light');
assert(/<meta name="theme-color" content=\{THEME_COLORS\.light\}/.test(head), 'Head must derive the default theme-color from THEME_COLORS.light');

const nav = read('components/Navigation.astro');
assert(nav.includes("from '../lib/theme.js'"), 'Navigation must import from lib/theme.js');
assert(nav.includes('data-white-label={copy.themeWhite}'), 'Navigation needs a white theme label');
for (const t of ['light', 'white', 'dark']) {
  assert(nav.includes(`data-theme-icon="${t}"`), `Navigation needs a ${t} icon`);
}
assert(!/data-theme-icon="(pink|midnight)"/.test(nav) && !/data-(pink|midnight)-label/.test(nav), 'Navigation must not reference retired theme ids');

const sidebar = read('components/admin/AdminSidebar.astro');
assert(sidebar.includes("from '../../lib/theme.js'"), 'AdminSidebar must import from lib/theme.js');
assert(sidebar.includes('id="sidebar-theme-icon-white"'), 'AdminSidebar needs a white icon');
assert(!/sidebar-theme-icon-(pink|midnight)/.test(sidebar), 'AdminSidebar must not reference retired theme ids');
assert(!fs.existsSync(path.join(src, 'components/ThemeToggle.astro')), 'unused ThemeToggle must be deleted');
assert(!fs.existsSync(path.join(src, 'pages/preview')), 'legacy newsprint preview pages must be deleted');

console.log('theme-wiring.test.cjs passed');
