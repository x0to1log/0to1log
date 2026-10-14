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

// --- applyTheme / readTheme with fakes ---
function makeEnv({ stored = null, prefersDark = false } = {}) {
  const store = new Map(stored == null ? [] : [['theme', stored]]);
  const meta = { content: '', setAttribute(k, v) { if (k === 'content') this.content = v; } };
  const root = { attrs: {}, style: {}, setAttribute(k, v) { this.attrs[k] = v; } };
  return {
    doc: { documentElement: root, querySelector: (sel) => (sel === 'meta[name="theme-color"]' ? meta : null) },
    storage: { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, v) },
    win: { matchMedia: () => ({ matches: prefersDark }) },
    store, meta, root,
  };
}

{
  const { applyTheme, readTheme } = mod;
  const env = makeEnv();
  applyTheme('dark', env);
  assert.equal(env.root.attrs['data-theme'], 'dark');
  assert.equal(env.root.style.colorScheme, 'dark');
  assert.equal(env.meta.content, '#181715');
  assert.equal(env.store.get('theme'), 'dark');

  // legacy 저장값은 읽을 때 매핑되고 저장소도 갱신된다
  const legacy = makeEnv({ stored: 'pink' });
  assert.equal(readTheme(legacy), 'light');
  assert.equal(legacy.store.get('theme'), 'light');

  // 저장값 없음 + OS 다크 → dark, 저장소는 건드리지 않는다
  const fresh = makeEnv({ prefersDark: true });
  assert.equal(readTheme(fresh), 'dark');
  assert.equal(fresh.store.has('theme'), false);
}

// --- hardening: blocked storage, missing matchMedia, invalid input ---
{
  const { applyTheme, readTheme } = mod;
  const base = makeEnv();
  const throwing = { getItem() { throw new Error('blocked'); }, setItem() { throw new Error('blocked'); } };
  const variants = [
    { ...base, storage: throwing },
    { ...base, storage: null },
    Object.defineProperty({ ...base }, 'storage', { get() { throw new Error('SecurityError'); } }),
  ];
  for (const env of variants) {
    assert.equal(readTheme(env), 'light');
    applyTheme('white', env);
    assert.equal(env.root.attrs['data-theme'], 'white');
    assert.equal(env.root.style.colorScheme, 'light');
    assert.equal(env.meta.content, '#FFFFFF');
  }

  // matchMedia missing must not throw
  const noMq = makeEnv();
  noMq.win = {};
  assert.equal(readTheme(noMq), 'light');

  // matchMedia is only consulted when nothing valid is stored
  const spy = makeEnv({ stored: 'white' });
  spy.win = { matchMedia() { throw new Error('should not be called'); } };
  assert.equal(readTheme(spy), 'white');

  // applyTheme rejects unknown values
  const bad = makeEnv();
  applyTheme('sepia', bad);
  assert.equal(bad.root.attrs['data-theme'], 'light');
  assert.equal(bad.store.get('theme'), 'light');
  applyTheme('midnight', bad);
  assert.equal(bad.root.attrs['data-theme'], 'dark');
}

// defaultEnv: a throwing global localStorage getter must not break no-arg calls
{
  const env = makeEnv();
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, get() { throw new Error('SecurityError'); } });
  globalThis.document = env.doc;
  globalThis.window = env.win;
  assert.equal(mod.readTheme(), 'light');
  mod.applyTheme('dark');
  assert.equal(env.root.attrs['data-theme'], 'dark');
  delete globalThis.localStorage; delete globalThis.document; delete globalThis.window;
}

console.log('theme-module.test.mjs passed');
