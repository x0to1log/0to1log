import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const mod = await import(pathToFileURL(path.join(here, '../src/lib/theme.js')).href);
const { THEMES, THEME_COLORS, COLOR_SCHEMES, normalizeTheme, resolveTheme, nextTheme } = mod;

assert.deepEqual(THEMES, ['light', 'white', 'dark']);
assert.deepEqual(THEME_COLORS, { light: '#F7F4EE', white: '#FFFFFF', dark: '#181715' });
assert.deepEqual(COLOR_SCHEMES, { light: 'light', white: 'light', dark: 'dark' });

// normalizeTheme: 유효값 통과, legacy 매핑, 그 외는 null
assert.equal(normalizeTheme('white'), 'white');
assert.equal(normalizeTheme('pink'), 'light');
assert.equal(normalizeTheme('midnight'), 'dark');
assert.equal(normalizeTheme('sepia'), null);
assert.equal(normalizeTheme(null), null);
assert.equal(normalizeTheme(undefined), null);
assert.equal(normalizeTheme('constructor'), null, 'prototype keys must not leak through');

// resolveTheme: 저장값 우선, 없으면 OS 기준
assert.equal(resolveTheme('pink', true), 'light');
assert.equal(resolveTheme(null, true), 'dark');
assert.equal(resolveTheme(null, false), 'light');
assert.equal(resolveTheme('garbage', false), 'light');

// nextTheme: light → white → dark → light, 알 수 없는 값은 light
assert.equal(nextTheme('light'), 'white');
assert.equal(nextTheme('white'), 'dark');
assert.equal(nextTheme('dark'), 'light');
assert.equal(nextTheme('pink'), 'light');

console.log('theme-module.test.mjs passed');
