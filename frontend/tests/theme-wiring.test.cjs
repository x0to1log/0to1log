const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

const layout = read('layouts/MainLayout.astro');
assert(layout.includes("import { THEME_BOOT_SCRIPT } from '../lib/theme.js';"), 'MainLayout must import THEME_BOOT_SCRIPT');
assert(/<script is:inline nonce=\{nonce\} set:html=\{THEME_BOOT_SCRIPT\}><\/script>/.test(layout), 'MainLayout must inline the boot script with nonce');
assert(!layout.includes("localStorage.getItem('theme')"), 'MainLayout must not keep its own theme logic');

const callback = read('pages/auth/callback.astro');
assert(callback.includes('set:html={THEME_BOOT_SCRIPT}'), 'auth/callback must use the shared boot script');
assert(callback.includes('nonce={nonce}'), 'auth/callback inline script needs the CSP nonce');

const head = read('components/Head.astro');
assert(head.includes('<meta name="theme-color" content="#F7F4EE" />'), 'default theme-color must be the paper background');

const nav = read('components/Navigation.astro');
assert(nav.includes("from '../lib/theme.js'"), 'Navigation must import from lib/theme.js');
assert(nav.includes('data-white-label={copy.themeWhite}'), 'Navigation needs a white theme label');
for (const t of ['light', 'white', 'dark']) {
  assert(nav.includes(`data-theme-icon="${t}"`), `Navigation needs a ${t} icon`);
}
assert(!/pink|midnight/i.test(nav), 'Navigation must not mention retired themes');

const sidebar = read('components/admin/AdminSidebar.astro');
assert(sidebar.includes("from '../../lib/theme.js'"), 'AdminSidebar must import from lib/theme.js');
assert(sidebar.includes('id="sidebar-theme-icon-white"'), 'AdminSidebar needs a white icon');
assert(!/pink|midnight/i.test(sidebar), 'AdminSidebar must not mention retired themes');
assert(!fs.existsSync(path.join(src, 'components/ThemeToggle.astro')), 'unused ThemeToggle must be deleted');
assert(!fs.existsSync(path.join(src, 'pages/preview')), 'legacy newsprint preview pages must be deleted');

console.log('theme-wiring.test.cjs passed');
