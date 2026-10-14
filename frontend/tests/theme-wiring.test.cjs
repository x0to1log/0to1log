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

console.log('theme-wiring.test.cjs passed');
