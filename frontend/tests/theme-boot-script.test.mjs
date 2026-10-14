import assert from 'node:assert/strict';
import vm from 'node:vm';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { THEME_BOOT_SCRIPT } = await import(pathToFileURL(path.join(here, '../src/lib/theme.js')).href);

function run({ stored = null, prefersDark = false, withMeta = true } = {}) {
  const store = new Map(stored == null ? [] : [['theme', stored]]);
  const listeners = {};
  const meta = { content: '', setAttribute(k, v) { this.content = v; } };
  const root = { attrs: {}, style: {}, setAttribute(k, v) { this.attrs[k] = v; } };
  const ctx = {
    localStorage: { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, v) },
    matchMedia: () => ({ matches: prefersDark }),
    document: {
      documentElement: root,
      querySelector: () => (withMeta ? meta : null),
      addEventListener: (type, fn) => { listeners[type] = fn; },
    },
  };
  ctx.window = ctx;
  vm.runInNewContext(THEME_BOOT_SCRIPT, ctx);
  return { root, meta, store, listeners };
}

let r = run({ stored: 'white' });
assert.equal(r.root.attrs['data-theme'], 'white');
assert.equal(r.root.style.colorScheme, 'light');
assert.equal(r.meta.content, '#FFFFFF');

r = run({ stored: 'midnight' });
assert.equal(r.root.attrs['data-theme'], 'dark');
assert.equal(r.store.get('theme'), 'dark', 'legacy value must be migrated in storage');

r = run({ prefersDark: true });
assert.equal(r.root.attrs['data-theme'], 'dark');
assert.equal(r.store.has('theme'), false, 'OS-derived theme must not be persisted');

r = run({ withMeta: false });
assert.equal(r.root.attrs['data-theme'], 'light');

r = run({ stored: 'constructor' });
assert.equal(r.root.attrs['data-theme'], 'light', 'prototype keys must not leak through');

// after-swap 핸들러가 등록되고, 다시 실행해도 같은 결과
assert.equal(typeof r.listeners['astro:after-swap'], 'function');
r.root.attrs['data-theme'] = 'stale';
r.listeners['astro:after-swap']();
assert.equal(r.root.attrs['data-theme'], 'light');

// 테마 이름은 theme.js 상수에서 주입된 것이어야 한다
assert.match(THEME_BOOT_SCRIPT, /"light","white","dark"/);
assert.doesNotMatch(THEME_BOOT_SCRIPT, /import\s/);

// matchMedia 없음: 예외 없이 light, after-swap 핸들러 등록
{
  const listeners = {};
  const root = { attrs: {}, style: {}, setAttribute(k, v) { this.attrs[k] = v; } };
  const ctx = {
    localStorage: { getItem: () => null, setItem() {} },
    document: { documentElement: root, querySelector: () => null, addEventListener: (t, f) => { listeners[t] = f; } },
  };
  ctx.window = ctx;
  vm.runInNewContext(THEME_BOOT_SCRIPT, ctx);
  assert.equal(root.attrs['data-theme'], 'light');
  assert.equal(typeof listeners['astro:after-swap'], 'function');
}

// localStorage getter가 throw해도 중단되지 않는다
{
  const listeners = {};
  const root = { attrs: {}, style: {}, setAttribute(k, v) { this.attrs[k] = v; } };
  const ctx = {
    matchMedia: () => ({ matches: true }),
    document: { documentElement: root, querySelector: () => null, addEventListener: (t, f) => { listeners[t] = f; } },
  };
  Object.defineProperty(ctx, 'localStorage', { get() { throw new Error('SecurityError'); } });
  ctx.window = ctx;
  vm.runInNewContext(THEME_BOOT_SCRIPT, ctx);
  assert.equal(root.attrs['data-theme'], 'dark');
  assert.equal(typeof listeners['astro:after-swap'], 'function');
}

console.log('theme-boot-script.test.mjs passed');
