# 사이트 리디자인 1단계(기반) Implementation Plan

**Status:** done (2026-10-14)

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사이트 전체를 Soft Newsprint(V2)의 테마 3개(종이/화이트/다크)와 새 글꼴 체계로 전환하고, 레트로 장식을 제거한다. 레이아웃은 바꾸지 않는다.

**Architecture:** 테마 이름·색·마이그레이션 로직을 `src/lib/theme.js` 한 곳으로 모은다. 인라인 FOUC 스크립트도 이 모듈이 문자열로 생성(`THEME_BOOT_SCRIPT`)한다. 색은 기존 `--color-*` 토큰 이름을 유지하고 값만 교체한다. 글꼴은 기존 `--font-*` 역할 토큰을 다시 분리한다.

**Tech Stack:** Astro v5, Tailwind v4(`@theme`), 순수 Node 테스트 스크립트(`frontend/tests/*.test.{cjs,mjs}`, 테스트 러너 없음, `node <file>`로 실행)

**Spec:** [[2026-10-14-site-redesign-soft-newsprint-design]] §3, §4, §7-1단계

**스펙과 다른 점:** 스펙은 `src/lib/theme.ts`와 `DEFAULT_THEME`이라고 적었다. 이 계획은 `src/lib/theme.js`(JSDoc)로 만든다. 기존 `src/lib/admin/pipelineRunLogs.js`처럼 Node 테스트가 빌드 없이 import할 수 있게 하기 위해서다. 기본값은 `resolveTheme`의 `'light'` fallback으로 표현한다.

**push 규칙:** Task 5부터 Task 7 사이에는 토글로 `white`를 고를 수 있지만 CSS 블록이 아직 없다. 그래서 **Task 7 커밋 전까지 push하지 않는다.** 전체 push는 Task 10 검증 후에 한다.

---

## 사전 정보 (실행자 필독)

### 테스트 실행 방법과 기준선
- 테스트는 러너 없이 파일 단위로 실행한다. 일부는 `process.cwd()`를 repo 루트로 가정하고, 일부는 `__dirname`을 기준으로 한다. **항상 repo 루트(`C:\Users\amy\Desktop\0to1log`)에서** `node frontend/tests/<file>`로 실행한다.
- 전체 실행 스크립트(repo 루트에서):
  ```bash
  for f in frontend/tests/*.test.cjs frontend/tests/*.test.mjs; do node "$f" >/dev/null 2>&1 && echo "PASS $f" || echo "FAIL $f"; done | sort > /tmp/after.txt; grep -c PASS /tmp/after.txt
  ```
- **기준선 (2026-10-14, 이 계획 시작 전): PASS 47 / FAIL 25.** 이미 실패하던 25개는 이번 작업과 무관한 stale 테스트다. 이번 작업에서 고치지 않는다. 목록:
  `admin-live-preview, admin-v1-structure, article-deck-font, auth-prompt-library-preview, blog-section-heading-font, blog-sidebar-categories, blog-sidebar-layout, blog-title-fonts, comments-admin-delete-contract, content-feedback-contract, csp-inline-scripts(서버 필요), detail-rail-copy, handbook-category-icons, handbook-detail-table-overflow, handbook-search-recognition, list-meta-order, list-rail-copy, log-list-created-order, navigation-shell-copy, news-fact-pack-structure, product-detail-scenarios-theme, public-slug-visibility, reading-actions-editorial-subtle, reading-actions-layout-regression, sticky-reading-actions-structure`
- **완료 기준:** 기준선에서 PASS였던 47개는 계속 PASS여야 한다. 단, 의도적으로 교체하는 2개(`dark-theme-palette`, `blog-dropcap`)는 예외다. 여기에 이번에 추가하는 새 테스트가 모두 PASS여야 한다.

### 규칙 (frontend/CLAUDE.md)
- 모든 `<script is:inline>`에는 `nonce={Astro.locals.cspNonce || ''}`가 필요하다(MainLayout에서는 `nonce` 변수).
- `client:load` 금지. 컴포넌트 `<script>`는 Vite 번들이므로 `import`를 쓸 수 있다.
- 빌드: `cd frontend && npm run build`가 에러 0이어야 한다.
- 커밋 메시지: `feat:` / `fix:` / `chore:` / `docs:`. **`Co-Authored-By`는 넣지 않는다.** 브랜치는 `main`.
- `git add`는 이 계획에서 만든·수정한 파일만 경로를 지정해서 한다. 작업 트리에 사용자의 다른 미커밋 변경이 있다.

### 확정 팔레트 (스펙 시안에서 WCAG AA를 맞추려고 조정함)
| 토큰 | light (종이) | white | dark |
|---|---|---|---|
| bg-primary | #F7F4EE | #FFFFFF | #181715 |
| bg-secondary | #EFEAE0 | #F3F5F8 | #121110 |
| bg-tertiary | #E6E0D3 | #E9EDF2 | #23211E |
| bg-card | #F2EEE6 | #FAFBFC | #1E1C1A |
| input-surface | #FBF9F5 | #FFFFFF | #1F1D1B |
| text-primary | #24211D | #16181B | #ECE7DD |
| text-secondary | #5A544B | #4D5057 | #B3ACA0 |
| text-muted | **#6B6459** (시안 #8A8378은 3.4:1이라 불합격) | **#6B6F76** | **#948D82** |
| border | #D9D2C5 | #E3E4E7 | #35322D |
| accent | **#B4472A** (시안 #C2502F는 4.27:1이라 불합격) | #2448A8 | #E3774F |
| accent-hover | #9C3C22 | #1C3A8A | #EC8A65 |

---

## Chunk 1: 테마 모듈 단일화

### Task 1: `src/lib/theme.js` 핵심 함수

**Files:**
- Create: `frontend/src/lib/theme.js`
- Test: `frontend/tests/theme-module.test.mjs`

- [ ] **Step 1: 실패하는 테스트 작성**

```js
// frontend/tests/theme-module.test.mjs
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
```

- [ ] **Step 2: 실행해서 실패 확인**

Run: `node frontend/tests/theme-module.test.mjs`
Expected: FAIL. `Cannot find module ... src/lib/theme.js`

- [ ] **Step 3: 최소 구현**

```js
// frontend/src/lib/theme.js
// Single source of truth for site themes. Used by MainLayout (boot script),
// Navigation, AdminSidebar and auth/callback. Do not hardcode theme names elsewhere.

export const STORAGE_KEY = 'theme';

/** Cycle order for theme toggles. First entry is the light default. */
export const THEMES = ['light', 'white', 'dark'];

/** <meta name="theme-color"> value per theme (matches --color-bg-primary). */
export const THEME_COLORS = { light: '#F7F4EE', white: '#FFFFFF', dark: '#181715' };

/** CSS color-scheme per theme. */
export const COLOR_SCHEMES = { light: 'light', white: 'light', dark: 'dark' };

/** Retired themes mapped to their replacement (2026-10 redesign). */
export const LEGACY_THEMES = { pink: 'light', midnight: 'dark' };

/** @returns {string|null} a supported theme, or null when unknown/missing */
export function normalizeTheme(value) {
  if (typeof value !== 'string') return null;
  if (THEMES.includes(value)) return value;
  return Object.hasOwn(LEGACY_THEMES, value) ? LEGACY_THEMES[value] : null;
}

/** Stored preference wins; otherwise follow the OS color scheme. */
export function resolveTheme(stored, prefersDark) {
  return normalizeTheme(stored) ?? (prefersDark ? 'dark' : 'light');
}

export function nextTheme(current) {
  const idx = THEMES.indexOf(current);
  return THEMES[(idx + 1) % THEMES.length];
}
```

- [ ] **Step 4: 실행해서 통과 확인**

Run: `node frontend/tests/theme-module.test.mjs`
Expected: `theme-module.test.mjs passed`

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/theme.js frontend/tests/theme-module.test.mjs
git commit -m "feat: add single theme module for light/white/dark"
```

### Task 2: `applyTheme`과 `readTheme` (브라우저 적용)

**Files:**
- Modify: `frontend/src/lib/theme.js`
- Test: `frontend/tests/theme-module.test.mjs` (이어서 추가)

- [ ] **Step 1: 실패하는 테스트 추가** (파일 끝 `console.log` 위에 추가)

```js
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
```

- [ ] **Step 2: 실행해서 실패 확인**

Run: `node frontend/tests/theme-module.test.mjs`
Expected: FAIL. `applyTheme is not a function`

- [ ] **Step 3: 구현** (`theme.js` 끝에 추가)

```js
function defaultEnv() {
  return { doc: document, storage: localStorage, win: window };
}

/** Read the effective theme. Migrates legacy stored values in place. */
export function readTheme(env = defaultEnv()) {
  let stored = null;
  try { stored = env.storage.getItem(STORAGE_KEY); } catch { /* storage blocked */ }
  const normalized = normalizeTheme(stored);
  if (normalized && normalized !== stored) {
    try { env.storage.setItem(STORAGE_KEY, normalized); } catch { /* ignore */ }
  }
  const prefersDark = Boolean(env.win.matchMedia?.('(prefers-color-scheme: dark)').matches);
  return normalized ?? (prefersDark ? 'dark' : 'light');
}

/** Apply a theme to <html>, color-scheme and theme-color, and persist it. */
export function applyTheme(theme, env = defaultEnv()) {
  const root = env.doc.documentElement;
  root.setAttribute('data-theme', theme);
  root.style.colorScheme = COLOR_SCHEMES[theme];
  env.doc.querySelector('meta[name="theme-color"]')?.setAttribute('content', THEME_COLORS[theme]);
  try { env.storage.setItem(STORAGE_KEY, theme); } catch { /* ignore */ }
}
```

- [ ] **Step 4: 통과 확인**

Run: `node frontend/tests/theme-module.test.mjs`
Expected: `theme-module.test.mjs passed`

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/theme.js frontend/tests/theme-module.test.mjs
git commit -m "feat: add applyTheme/readTheme with legacy theme migration"
```

### Task 3: 인라인 부트 스크립트 `THEME_BOOT_SCRIPT`

인라인 스크립트는 모듈을 import할 수 없다. 그래서 `theme.js`의 상수로 스크립트 **문자열**을 만들고, 레이아웃이 `set:html`로 삽입한다. 이 스크립트 하나가 기존 FOUC 스크립트와 `astro:after-swap` 핸들러를 모두 대체한다. 저장값을 쓰지 않는 점이 `applyTheme`과 다르다. 사용자가 고른 적 없는 OS 기반 값을 저장하면 안 되기 때문이다.

**Files:**
- Modify: `frontend/src/lib/theme.js`
- Test: `frontend/tests/theme-boot-script.test.mjs`

- [ ] **Step 1: 실패하는 테스트 작성**

```js
// frontend/tests/theme-boot-script.test.mjs
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

console.log('theme-boot-script.test.mjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/theme-boot-script.test.mjs`
Expected: FAIL. `THEME_BOOT_SCRIPT`가 undefined여서 vm에서 TypeError

- [ ] **Step 3: 구현** (`theme.js` 끝에 추가)

```js
/**
 * Inline <script is:inline> body for MainLayout and auth/callback.
 * Runs before paint and again after every ViewTransitions swap.
 * Generated from the constants above so theme names live in one place.
 */
export const THEME_BOOT_SCRIPT = `(function(){
var T=${JSON.stringify(THEMES)},C=${JSON.stringify(THEME_COLORS)},S=${JSON.stringify(COLOR_SCHEMES)},L=${JSON.stringify(LEGACY_THEMES)},K=${JSON.stringify(STORAGE_KEY)};
function boot(){
  var s=null;try{s=localStorage.getItem(K);}catch(e){}
  var t=T.indexOf(s)>=0?s:(Object.prototype.hasOwnProperty.call(L,s)?L[s]:null);
  if(t&&t!==s){try{localStorage.setItem(K,t);}catch(e){}}
  if(!t){t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}
  var d=document.documentElement;d.setAttribute('data-theme',t);d.style.colorScheme=S[t];
  var m=document.querySelector('meta[name="theme-color"]');if(m){m.setAttribute('content',C[t]);}
}
boot();
if(!window.__themeBootBound){window.__themeBootBound=true;document.addEventListener('astro:after-swap',boot);}
})();`;
```

- [ ] **Step 4: 통과 확인**

Run: `node frontend/tests/theme-boot-script.test.mjs && node frontend/tests/theme-module.test.mjs`
Expected: 두 파일 모두 `passed`

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/theme.js frontend/tests/theme-boot-script.test.mjs
git commit -m "feat: generate inline theme boot script from theme module"
```

### Task 4: MainLayout, Head, auth/callback을 부트 스크립트로 전환

**Files:**
- Modify: `frontend/src/layouts/MainLayout.astro:37-67` (html 태그, FOUC 스크립트, after-swap 스크립트)
- Modify: `frontend/src/components/Head.astro:81` (theme-color 기본값)
- Modify: `frontend/src/pages/auth/callback.astro:5-35`
- Test: `frontend/tests/theme-wiring.test.cjs`

- [ ] **Step 1: 실패하는 구조 테스트 작성**

```js
// frontend/tests/theme-wiring.test.cjs
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
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/theme-wiring.test.cjs`
Expected: FAIL. `MainLayout must import THEME_BOOT_SCRIPT`

- [ ] **Step 3: MainLayout 수정**
  - frontmatter의 import 목록(8행 `import '../styles/global.css';` 다음)에 추가한다.
    ```astro
    import { THEME_BOOT_SCRIPT } from '../lib/theme.js';
    ```
  - 40–67행의 FOUC 스크립트와 after-swap 스크립트(주석 `<!-- FOUC Prevention ... -->`부터 `<!-- Restore theme after ViewTransitions ... -->` 블록의 `</script>`까지)를 **통째로** 아래로 교체한다. `<!-- Fall back to full reload on back/forward ... -->` 스크립트는 그대로 둔다.
    ```astro
      <!-- Theme boot: before paint + after every ViewTransitions swap (source: lib/theme.js) -->
      <script is:inline nonce={nonce} set:html={THEME_BOOT_SCRIPT}></script>
    ```
  - 37행 `<html lang={locale} data-theme="light">`는 그대로 둔다. 이제 `light`가 종이 테마다.

- [ ] **Step 4: Head 수정**
  81행 `<meta name="theme-color" content="#171311" />`를 `<meta name="theme-color" content="#F7F4EE" />`로 바꾼다.

- [ ] **Step 5: auth/callback 수정**
  파일 첫 줄부터 `</head>`까지를 **통째로** 아래로 교체한다. `<body>` 이하는 그대로 둔다. `.signing-in`의 `clamp(...)` 줄은 `login-signing-in-fonts` 테스트가 검사하므로 반드시 유지한다.
  ```astro
  ---
  import { THEME_BOOT_SCRIPT } from '../../lib/theme.js';
  export const prerender = false;
  const nonce = Astro.locals.cspNonce || '';
  ---

  <html lang="en" data-theme="light">
    <head>
      <title>Signing in...</title>
      <meta name="theme-color" content="#F7F4EE" />
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
      <link href="https://fonts.googleapis.com/css2?family=Hahmlet:wght@400;600&display=swap" rel="stylesheet" />
      <script is:inline nonce={nonce} set:html={THEME_BOOT_SCRIPT}></script>
      <style>
        [data-theme="light"] { --bg: #F7F4EE; --fg: #24211D; }
        [data-theme="white"] { --bg: #FFFFFF; --fg: #16181B; }
        [data-theme="dark"] { --bg: #181715; --fg: #ECE7DD; }
        body {
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 100vh;
          margin: 0;
          font-family: 'Hahmlet', 'Pretendard', Georgia, serif;
          color: var(--fg);
          background: var(--bg);
          transition: background 0.2s, color 0.2s;
        }
        .signing-in {
          font-size: clamp(1.75rem, 6vw, 2.1rem);
          letter-spacing: 0.02em;
        }
        .signing-in-dots::after {
          content: '';
          animation: dots 1.4s steps(4, end) infinite;
        }
        @keyframes dots {
          0%  { content: ''; }
          25% { content: '.'; }
          50% { content: '..'; }
          75% { content: '...'; }
        }
      </style>
    </head>
  ```

- [ ] **Step 6: 통과 확인**

Run: `node frontend/tests/theme-wiring.test.cjs`
Expected: `theme-wiring.test.cjs passed`

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/layouts/MainLayout.astro frontend/src/components/Head.astro frontend/src/pages/auth/callback.astro frontend/tests/theme-wiring.test.cjs
git commit -m "feat: boot themes from shared script in layout and auth callback"
```

### Task 5: Navigation 테마 버튼 전환

**Files:**
- Modify: `frontend/src/components/Navigation.astro`
  - copy 객체: ko 76–79행, en 101–104행(`themePink`, `themeMidnight`)
  - 버튼 마크업: 220–254행
  - 스크립트: 384–411행
- Test: `frontend/tests/theme-wiring.test.cjs` (이어서 추가)

- [ ] **Step 1: 실패하는 테스트 추가** (`console.log` 위에)

```js
const nav = read('components/Navigation.astro');
assert(nav.includes("from '../lib/theme.js'"), 'Navigation must import from lib/theme.js');
assert(nav.includes('data-white-label={copy.themeWhite}'), 'Navigation needs a white theme label');
for (const t of ['light', 'white', 'dark']) {
  assert(nav.includes(`data-theme-icon="${t}"`), `Navigation needs a ${t} icon`);
}
assert(!/pink|midnight/i.test(nav), 'Navigation must not mention retired themes');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/theme-wiring.test.cjs`
Expected: FAIL. `Navigation must import from lib/theme.js`

- [ ] **Step 3: copy 수정**
  - ko: `themeLight: '라이트', themePink: '핑크', themeMidnight: '미드나잇',` → `themeLight: '종이', themeWhite: '화이트',`
  - en: `themeLight: 'Light', themePink: 'Pink', themeMidnight: 'Midnight',` → `themeLight: 'Paper', themeWhite: 'White',`
  - `themeDark`는 그대로 둔다.

- [ ] **Step 4: 버튼 마크업 수정**
  - `data-pink-label`, `data-midnight-label` 두 줄을 `data-white-label={copy.themeWhite}`로 교체한다.
  - `data-theme-icon="pink"`와 `data-theme-icon="midnight"` SVG 두 개를 삭제하고, light SVG 바로 뒤에 아래를 추가한다. 이 아이콘은 테두리 안에 점이 하나 있는 "빈 종이" 모양이다.
    ```html
    <svg data-theme-icon="white" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="display:none;">
      <rect x="5" y="3" width="14" height="18" rx="1.5"></rect>
      <circle cx="12" cy="12" r="1.2" fill="currentColor"></circle>
    </svg>
    ```
  - 서버 렌더 직후에는 모든 아이콘 중 dark만 보이고, 스크립트가 곧바로 올바른 아이콘으로 바꾼다. 이 동작은 그대로 둔다.

- [ ] **Step 5: 스크립트 수정** (384–411행)
  `<script>` 첫 줄 바로 아래의 `themes`, `Theme`, `themeColors`, `getTheme`, `setTheme` 정의를 아래로 교체한다. `renderThemeCycle`과 그 아래 코드는 유지한다. 클릭 핸들러(436행 부근)의 `themes.indexOf` / `themes[(idx + 1) % themes.length]` 계산은 `nextTheme(getTheme())`로 바꾼다.
  ```ts
  import { applyTheme, nextTheme, readTheme } from '../lib/theme.js';

  type Theme = 'light' | 'white' | 'dark';

  function getTheme(): Theme {
    return readTheme() as Theme;
  }

  function setTheme(theme: Theme) {
    applyTheme(theme);
    renderThemeCycle(document.querySelector('[data-theme-cycle]') as HTMLElement | null);
  }
  ```
  클릭 핸들러:
  ```ts
  setTheme(nextTheme(getTheme()) as Theme);
  ```

- [ ] **Step 6: 통과 확인**

Run: `node frontend/tests/theme-wiring.test.cjs`
Expected: `passed`

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/components/Navigation.astro frontend/tests/theme-wiring.test.cjs
git commit -m "feat: switch navigation theme toggle to light/white/dark"
```

### Task 6: AdminSidebar 전환, 죽은 코드와 preview 페이지 삭제

**Files:**
- Modify: `frontend/src/components/admin/AdminSidebar.astro:158-176` (아이콘), `:256-284` (스크립트)
- Delete: `frontend/src/components/ThemeToggle.astro` (사용처 0건, 확인 완료)
- Delete: `frontend/src/pages/preview/newsprint-dark.astro`, `newsprint-light.astro`, `newsprint-pink.astro`
- Modify: `frontend/CLAUDE.md` (Supported themes 줄)
- Test: `frontend/tests/theme-wiring.test.cjs`

- [ ] **Step 1: 실패하는 테스트 추가**

```js
const sidebar = read('components/admin/AdminSidebar.astro');
assert(sidebar.includes("from '../../lib/theme.js'"), 'AdminSidebar must import from lib/theme.js');
assert(sidebar.includes('id="sidebar-theme-icon-white"'), 'AdminSidebar needs a white icon');
assert(!/pink|midnight/i.test(sidebar), 'AdminSidebar must not mention retired themes');
assert(!fs.existsSync(path.join(src, 'components/ThemeToggle.astro')), 'unused ThemeToggle must be deleted');
assert(!fs.existsSync(path.join(src, 'pages/preview')), 'legacy newsprint preview pages must be deleted');

```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/theme-wiring.test.cjs`
Expected: FAIL. `AdminSidebar must import from lib/theme.js`

- [ ] **Step 3: AdminSidebar 수정**
  - 아이콘: `sidebar-theme-icon-midnight`, `sidebar-theme-icon-pink` SVG 두 개를 삭제하고, light 아이콘 뒤에 Task 5와 같은 white SVG를 추가한다. 이때 `data-theme-icon` 대신 `id="sidebar-theme-icon-white"`, `stroke-width="1.5"`로 쓴다.
  - 스크립트: `<script>` 맨 위에 `import { THEMES, applyTheme, nextTheme, readTheme } from '../../lib/theme.js';`를 추가한다. `themeList`, `themeColors`, `getSidebarTheme` 정의를 삭제한다.
  - `updateSidebarThemeUI`에서 `getSidebarTheme()`를 `readTheme()`로, `themeList.forEach`를 `THEMES.forEach`로 바꾼다.
  - 클릭 핸들러 본문은 아래로 교체한다.
    ```js
    applyTheme(nextTheme(readTheme()));
    updateSidebarThemeUI();
    ```
  - 라벨: `updateSidebarThemeUI`의 `labelEl.textContent = current.charAt(0).toUpperCase() + current.slice(1);`를 아래로 바꾼다. Navigation EN 라벨과 맞추기 위해서다.
    ```js
    const THEME_LABELS = { light: 'Paper', white: 'White', dark: 'Dark' };
    if (labelEl) labelEl.textContent = THEME_LABELS[current];
    ```

- [ ] **Step 4: 삭제**

```bash
git rm frontend/src/components/ThemeToggle.astro frontend/src/pages/preview/newsprint-dark.astro frontend/src/pages/preview/newsprint-light.astro frontend/src/pages/preview/newsprint-pink.astro
```

- [ ] **Step 5: frontend/CLAUDE.md 갱신**
  `- Supported themes: \`light\` (default), \`dark\`, \`pink\`.`를 아래로 바꾼다.
  `- Supported themes: \`light\` (paper, default), \`white\`, \`dark\`. Theme names, colors and migration live only in \`src/lib/theme.js\`.`

- [ ] **Step 6: 확인**

Run: `node frontend/tests/theme-wiring.test.cjs`
Expected: `theme-wiring.test.cjs passed`

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/components/admin/AdminSidebar.astro frontend/tests/theme-wiring.test.cjs frontend/CLAUDE.md
git commit -m "chore: move admin theme toggle to theme module, drop dead theme code"
```

---

## Chunk 2: 색 토큰

### Task 7: 테마 토큰 블록 3개 재작성

**Files:**
- Modify: `frontend/src/styles/global.css:97-262` (DARK, MIDNIGHT, LIGHT, PINK 블록 → LIGHT, WHITE, DARK)
- Delete+Create: `frontend/tests/dark-theme-palette.test.cjs` → `frontend/tests/theme-palette.test.cjs`
- Modify: `frontend/tests/theme-wiring.test.cjs` (retired 테마 이름 src 전체 검사 추가)

- [ ] **Step 1: 실패하는 테스트 작성** (기존 `dark-theme-palette.test.cjs`는 midnight와 옛 갈색 값을 검사하므로 삭제한다)

```js
// frontend/tests/theme-palette.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const css = fs.readFileSync(path.join(__dirname, '..', 'src/styles/global.css'), 'utf8');

function block(name) {
  const m = css.match(new RegExp(`\\[data-theme="${name}"\\] \\{([\\s\\S]*?)\\n\\}`));
  assert(m, `missing ${name} theme block`);
  return m[1];
}
function token(b, name) {
  const m = b.match(new RegExp(`\\s${name}:\\s*(#[0-9A-Fa-f]{6})\\s*;`));
  assert(m, `missing ${name}`);
  return m[1];
}
function lum(hex) {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
function ratio(a, b) {
  const [x, y] = [lum(a), lum(b)];
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}

const expected = {
  light: { '--color-bg-primary': '#F7F4EE', '--color-text-primary': '#24211D', '--color-accent': '#B4472A' },
  white: { '--color-bg-primary': '#FFFFFF', '--color-text-primary': '#16181B', '--color-accent': '#2448A8' },
  dark: { '--color-bg-primary': '#181715', '--color-text-primary': '#ECE7DD', '--color-accent': '#E3774F' },
};

for (const [theme, values] of Object.entries(expected)) {
  const b = block(theme);
  for (const [k, v] of Object.entries(values)) assert.strictEqual(token(b, k).toUpperCase(), v, `${theme} ${k}`);

  // WCAG AA: 작은 텍스트로 쓰이는 토큰은 주요 배경 3종 위에서 4.5:1 이상
  for (const fg of ['--color-text-primary', '--color-text-secondary', '--color-text-muted', '--color-accent']) {
    for (const bg of ['--color-bg-primary', '--color-bg-secondary', '--color-bg-card']) {
      const r = ratio(token(b, fg), token(b, bg));
      assert(r >= 4.5, `${theme}: ${fg} on ${bg} is ${r.toFixed(2)}:1 (< 4.5)`);
    }
  }
  assert(!b.includes('--noise-opacity'), `${theme}: noise token must be removed`);
}

assert(!/\[data-theme="(pink|midnight)"\]/.test(css), 'retired theme selectors must be removed');
console.log('theme-palette.test.cjs passed');
```

그리고 `frontend/tests/theme-wiring.test.cjs`의 `console.log` 위에 src 전체 검사를 추가한다. global.css 정리 후에만 통과할 수 있어서 이 Task에 둔다.

```js
// lib/theme.js 밖에서는 retired 테마 이름이 나오면 안 된다
function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? walk(path.join(dir, e.name)) : [path.join(dir, e.name)]);
}
const offenders = walk(src)
  .filter((f) => /\.(astro|ts|js|css)$/.test(f) && !f.endsWith(path.join('lib', 'theme.js')))
  .filter((f) => /data-theme="(pink|midnight)"|['"](pink|midnight)['"]/.test(fs.readFileSync(f, 'utf8')));
assert.deepStrictEqual(offenders, [], `retired theme names still referenced:\n${offenders.join('\n')}`);
```

- [ ] **Step 2: 실패 확인**

```bash
git rm frontend/tests/dark-theme-palette.test.cjs
node frontend/tests/theme-palette.test.cjs
```
Expected: FAIL. `light --color-bg-primary` 불일치(기존 light 블록이 #F4F1EA). `theme-wiring.test.cjs`도 offenders에 global.css가 나와 FAIL

- [ ] **Step 3: 토큰 블록 교체**
  `global.css`에서 `/* ===========================\n   DARK THEME (Default)` 주석부터 PINK 블록의 닫는 `}`(262행 부근, `MAIN LAYOUT` 주석 직전)까지를 **통째로** 아래로 교체한다.

```css
/* ===========================
   THEMES — Soft Newsprint (2026-10 redesign)
   Names/colors must match src/lib/theme.js
   =========================== */
[data-theme="light"] {
  --color-bg-primary: #F7F4EE;
  --color-bg-secondary: #EFEAE0;
  --color-bg-tertiary: #E6E0D3;
  --color-bg-card: #F2EEE6;
  --color-input-surface: #FBF9F5;
  --color-text-primary: #24211D;
  --color-text-secondary: #5A544B;
  --color-text-muted: #6B6459;
  --color-border: #D9D2C5;
  --color-accent: #B4472A;
  --color-accent-hover: #9C3C22;
  --color-accent-glow: rgba(180, 71, 42, 0.16);
  --color-accent-subtle: rgba(180, 71, 42, 0.08);
  --color-success: #2E6F57;
  --color-warning: #9A6B0A;
  --color-error: #A63A2E;
  --color-shadow: rgba(36, 33, 29, 0.10);

  /* Category colors unified to accent (spec §3) */
  --color-cat-ainews: var(--color-accent);
  --color-cat-study: var(--color-accent);
  --color-cat-career: var(--color-accent);
  --color-cat-project: var(--color-accent);
  --color-cat-work-note: var(--color-accent);
  --color-cat-daily: var(--color-accent);

  /* Shiki — Paper */
  --shiki-token-keyword: #8B3A3A;
  --shiki-token-string: #2E6F57;
  --shiki-token-function: #5B4A8A;
  --shiki-token-comment: #6B6459;
  --shiki-token-constant: #9C3C22;
  --shiki-token-punctuation: #24211D;
  --shiki-color-text: #24211D;
  --shiki-color-background: var(--color-bg-tertiary);
}

[data-theme="white"] {
  --color-bg-primary: #FFFFFF;
  --color-bg-secondary: #F3F5F8;
  --color-bg-tertiary: #E9EDF2;
  --color-bg-card: #FAFBFC;
  --color-input-surface: #FFFFFF;
  --color-text-primary: #16181B;
  --color-text-secondary: #4D5057;
  --color-text-muted: #6B6F76;
  --color-border: #E3E4E7;
  --color-accent: #2448A8;
  --color-accent-hover: #1C3A8A;
  --color-accent-glow: rgba(36, 72, 168, 0.14);
  --color-accent-subtle: rgba(36, 72, 168, 0.07);
  --color-success: #2E6F57;
  --color-warning: #9A6B0A;
  --color-error: #B3362F;
  --color-shadow: rgba(22, 24, 27, 0.08);

  --color-cat-ainews: var(--color-accent);
  --color-cat-study: var(--color-accent);
  --color-cat-career: var(--color-accent);
  --color-cat-project: var(--color-accent);
  --color-cat-work-note: var(--color-accent);
  --color-cat-daily: var(--color-accent);

  /* Shiki — shares the paper palette */
  --shiki-token-keyword: #8B3A3A;
  --shiki-token-string: #2E6F57;
  --shiki-token-function: #5B4A8A;
  --shiki-token-comment: #6B6F76;
  --shiki-token-constant: #1C3A8A;
  --shiki-token-punctuation: #16181B;
  --shiki-color-text: #16181B;
  --shiki-color-background: var(--color-bg-tertiary);
}

[data-theme="dark"] {
  --color-bg-primary: #181715;
  --color-bg-secondary: #121110;
  --color-bg-tertiary: #23211E;
  --color-bg-card: #1E1C1A;
  --color-input-surface: #1F1D1B;
  --color-text-primary: #ECE7DD;
  --color-text-secondary: #B3ACA0;
  --color-text-muted: #948D82;
  --color-border: #35322D;
  --color-accent: #E3774F;
  --color-accent-hover: #EC8A65;
  --color-accent-glow: rgba(227, 119, 79, 0.16);
  --color-accent-subtle: rgba(227, 119, 79, 0.08);
  --color-success: #6FA67A;
  --color-warning: #D4A843;
  --color-error: #E07067;
  --color-shadow: rgba(0, 0, 0, 0.4);

  --color-cat-ainews: var(--color-accent);
  --color-cat-study: var(--color-accent);
  --color-cat-career: var(--color-accent);
  --color-cat-project: var(--color-accent);
  --color-cat-work-note: var(--color-accent);
  --color-cat-daily: var(--color-accent);

  /* Shiki — Ink */
  --shiki-token-keyword: #E3A27C;
  --shiki-token-string: #8FAE7E;
  --shiki-token-function: #B8A9D4;
  --shiki-token-comment: #948D82;
  --shiki-token-constant: #E3774F;
  --shiki-token-punctuation: #ECE7DD;
  --shiki-color-text: #ECE7DD;
  --shiki-color-background: var(--color-bg-tertiary);
}
```

- [ ] **Step 4: 테마 전용 오버라이드 정리** (줄 번호는 Step 3 이후 약 −40 이동한다. 셀렉터 문자열로 찾는다)
  - `[data-theme="pink"] .newsprint-type-badge--research {…}`와 `[data-theme="pink"] .newsprint-type-badge--business {…}` 두 규칙을 삭제한다.
  - `[data-theme="light"] .newsprint-type-badge--research`와 `--business`의 셀렉터를 각각 `:is([data-theme="light"], [data-theme="white"]) .newsprint-type-badge--research` / `--business`로 바꾼다.
  - `.product-pricing-badge` 4개 규칙에서 `[data-theme="midnight"] …,` 셀렉터 줄만 삭제하고, `[data-theme="dark"]` 줄은 남긴다. 이때 남는 `[data-theme="dark"] …` 줄 끝의 `,`를 ` {`로 정리한다.
  - `[data-theme="dark"]` 전용 admin/product 규칙(3702–4209, 13139–13281 부근)은 그대로 둔다. 다크는 유지되는 테마다.

- [ ] **Step 5: 통과 확인**

Run: `node frontend/tests/theme-palette.test.cjs && node frontend/tests/theme-wiring.test.cjs`
Expected: 둘 다 `passed`

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/styles/global.css frontend/tests/theme-palette.test.cjs frontend/tests/theme-wiring.test.cjs
git commit -m "feat: replace theme palettes with paper/white/dark soft newsprint tokens"
```

---

## Chunk 3: 글꼴

### Task 8: 글꼴 역할 재분리와 로딩 교체

**Files:**
- Modify: `frontend/src/styles/global.css:14-34` (Pretendard @font-face), `:48-61` (@theme 글꼴 토큰)
- Modify: `global.css`의 Playfair 하드코딩 4곳(셀렉터로 찾기): `.site-brand-link`, `.admin-sidebar-logo`, `.login-logo`, `.home-split-hero-wordmark`
- Modify: `global.css`의 `var(--font-blog-heading, Lora, serif)`와 `var(--font-blog-ui, Lora, serif)` fallback 2곳
- Modify: `frontend/src/components/Head.astro:49-50`
- Modify: `frontend/src/pages/admin/analytics.astro:1319`
- Test: `frontend/tests/font-roles.test.cjs`

- [ ] **Step 1: 실패하는 테스트 작성**

```js
// frontend/tests/font-roles.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const css = fs.readFileSync(path.join(src, 'styles/global.css'), 'utf8');
const head = fs.readFileSync(path.join(src, 'components/Head.astro'), 'utf8');

const SERIF_KO = "'Hahmlet', 'Pretendard', Georgia, serif";
const SANS = "'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', sans-serif";
const MAST = "'Newsreader', 'Hahmlet', Georgia, serif";
const expected = {
  '--font-masthead': MAST,
  '--font-display': SERIF_KO,
  '--font-heading': SERIF_KO,
  '--font-article-heading': SERIF_KO,
  '--font-blog-heading': SERIF_KO,
  '--font-blog-masthead': SERIF_KO,
  '--font-sans': SANS,
  '--font-body': SANS,
  '--font-ui': SANS,
  '--font-article-deck': SANS,
  '--font-blog-body': SANS,
  '--font-blog-ui': SANS,
};
for (const [token, value] of Object.entries(expected)) {
  assert(css.includes(`  ${token}: ${value};`), `${token} must be ${value}`);
}

for (const w of ['Regular', 'Medium', 'SemiBold', 'Bold']) {
  assert(css.includes(`Pretendard-${w}.woff2`), `Pretendard ${w} must be loaded`);
}
assert(head.includes('family=Hahmlet:wght@400;600;700'), 'Head must load Hahmlet');
assert(head.includes('family=Newsreader:opsz,wght@6..72,500'), 'Head must load Newsreader');

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? walk(path.join(dir, e.name)) : [path.join(dir, e.name)]);
}
const legacy = walk(src)
  .filter((f) => /\.(astro|ts|js|css)$/.test(f))
  .filter((f) => /\bLora\b|Playfair|Gowun/.test(fs.readFileSync(f, 'utf8')));
assert.deepStrictEqual(legacy, [], `legacy fonts still referenced:\n${legacy.join('\n')}`);

assert(/font-variant-numeric:\s*lining-nums/.test(css), 'masthead brand marks need lining numerals ("0to1" must not read "oto1")');
console.log('font-roles.test.cjs passed');
```

- [ ] **Step 2: 실패 확인**

Run: `node frontend/tests/font-roles.test.cjs`
Expected: FAIL. `--font-masthead must be ...`

- [ ] **Step 3: @theme 글꼴 토큰 교체** (`global.css` 49–61행)

```css
  --font-sans: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', sans-serif;
  --font-display: 'Hahmlet', 'Pretendard', Georgia, serif;
  --font-body: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', sans-serif;
  --font-masthead: 'Newsreader', 'Hahmlet', Georgia, serif;
  --font-heading: 'Hahmlet', 'Pretendard', Georgia, serif;
  --font-article-heading: 'Hahmlet', 'Pretendard', Georgia, serif;
  --font-article-deck: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', sans-serif;
  --font-ui: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', sans-serif;
  --font-code: 'JetBrains Mono', 'D2Coding', monospace;
  --font-blog-masthead: 'Hahmlet', 'Pretendard', Georgia, serif;
  --font-blog-heading: 'Hahmlet', 'Pretendard', Georgia, serif;
  --font-blog-body: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', sans-serif;
  --font-blog-ui: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', sans-serif;
```

- [ ] **Step 4: Pretendard 굵기 추가**
  기존 Regular(400)와 Bold(700) `@font-face` 사이에 아래 두 블록을 추가한다(URL 200 응답 확인 완료). ExtraBold(800) 블록은 남겨둔다. 사용처는 2단계에서 정리한다.

```css
@font-face {
  font-family: 'Pretendard';
  src: url('https://cdn.jsdelivr.net/gh/projectnoonnu/pretendard@1.0/Pretendard-Medium.woff2') format('woff2');
  font-weight: 500;
  font-display: swap;
}

@font-face {
  font-family: 'Pretendard';
  src: url('https://cdn.jsdelivr.net/gh/projectnoonnu/pretendard@1.0/Pretendard-SemiBold.woff2') format('woff2');
  font-weight: 600;
  font-display: swap;
}
```

- [ ] **Step 5: Playfair 하드코딩 4곳 교체**
  `.site-brand-link`, `.admin-sidebar-logo`, `.login-logo`, `.home-split-hero-wordmark` 각각의 `font-family: 'Playfair Display', …;` 줄을 아래 두 줄로 바꾼다.

```css
  font-family: var(--font-masthead);
  font-variant-numeric: lining-nums;
```
  `.login-logo`와 `.home-split-hero-wordmark`의 `font-weight: 900`/`700`은 Newsreader 500만 로드하므로 `font-weight: 500;`으로 바꾼다. `.site-brand-link`와 `.admin-sidebar-logo`의 `font-weight: 700`도 `500`으로 바꾼다.

  이미 `var(--font-masthead)`를 쓰는 곳도 맞춘다. Newsreader는 500만 로드하므로, 브라우저가 가짜 굵게를 만들지 않도록 `font-weight: 500;`으로 바꾸고 `font-variant-numeric: lining-nums;`를 추가한다.
  - `global.css` `.newsprint-masthead` (현재 900, uppercase. uppercase는 2단계 헤더 작업에서 다룬다. 여기선 굵기와 숫자만)
  - `global.css` `.library-title` (현재 700)
  - `frontend/src/pages/404.astro` `.error-404-number` (현재 900)
  - `frontend/src/pages/en/about/index.astro`, `frontend/src/pages/ko/about/index.astro` `.about-title` (현재 700)

- [ ] **Step 6: Lora fallback과 analytics 교체**
  - `var(--font-blog-heading, Lora, serif)` → `var(--font-blog-heading)`
  - `var(--font-blog-ui, Lora, serif)` → `var(--font-blog-ui)`
  - `frontend/src/pages/admin/analytics.astro:1319`의 `|| 'Lora, serif'` → `|| 'Pretendard, sans-serif'`

- [ ] **Step 7: Head.astro 글꼴 링크 교체** (49–50행 두 줄)

```astro
  <link rel="preload" as="style" href="https://fonts.googleapis.com/css2?family=Hahmlet:wght@400;600;700&family=Newsreader:opsz,wght@6..72,500&display=swap" />
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hahmlet:wght@400;600;700&family=Newsreader:opsz,wght@6..72,500&display=swap" />
```

- [ ] **Step 8: 통과 확인**

Run: `node frontend/tests/font-roles.test.cjs`
Expected: `font-roles.test.cjs passed`. legacy 목록에 파일이 남아 있으면 해당 파일의 Lora/Playfair/Gowun 참조를 위 토큰으로 바꾼다.

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/styles/global.css frontend/src/components/Head.astro frontend/src/pages/admin/analytics.astro frontend/src/pages/404.astro frontend/src/pages/en/about/index.astro frontend/src/pages/ko/about/index.astro frontend/tests/font-roles.test.cjs
git commit -m "feat: split font roles into Newsreader/Hahmlet/Pretendard"
```

---

## Chunk 4: 레트로 장식 제거와 검증

### Task 9: 드롭캡, 이중선, 노이즈, small-caps 키커 제거

**Files:**
- Modify: `frontend/src/styles/global.css` (아래 셀렉터들)
- Modify: `newsprint-prose--no-dropcap` 클래스 사용처 4곳: `frontend/src/components/blog/BlogArticleLayout.astro`, `frontend/src/pages/ko/handbook/[slug].astro:182`, `frontend/src/pages/en/handbook/[slug].astro:187`, `frontend/src/pages/admin/handbook/edit/[slug].astro:500`
- Delete+Create: `frontend/tests/blog-dropcap.test.cjs` → `frontend/tests/retro-decoration-removed.test.cjs`

- [ ] **Step 1: 실패하는 테스트 작성** (기존 `blog-dropcap.test.cjs`는 드롭캡 "끄기" 규칙의 존재를 검사하므로 의미가 없어진다. 삭제한다.)

```js
// frontend/tests/retro-decoration-removed.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const css = fs.readFileSync(path.join(src, 'styles/global.css'), 'utf8');

assert(!css.includes('::first-letter'), 'drop caps must be removed');
assert(!/\b\d+px double\b/.test(css), 'double rules must be removed');
assert(!css.includes('feTurbulence'), 'page noise texture must be removed');
assert(!css.includes('--noise-opacity'), 'noise token must be removed');

function rule(selector) {
  const m = css.match(new RegExp(`\\n${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')} \\{([\\s\\S]*?)\\n\\}`));
  assert(m, `missing ${selector}`);
  return m[1];
}
for (const sel of ['.newsprint-kicker', '.newsprint-subkicker', '.blog-masthead-kicker', '.blog-masthead-subkicker']) {
  assert(!rule(sel).includes('text-transform: uppercase'), `${sel} must not be uppercase small caps`);
}

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? walk(path.join(dir, e.name)) : [path.join(dir, e.name)]);
}
const stale = walk(src).filter((f) => f.endsWith('.astro') && fs.readFileSync(f, 'utf8').includes('newsprint-prose--no-dropcap'));
assert.deepStrictEqual(stale, [], `no-dropcap modifier is obsolete:\n${stale.join('\n')}`);

console.log('retro-decoration-removed.test.cjs passed');
```

- [ ] **Step 2: 실패 확인**

```bash
git rm frontend/tests/blog-dropcap.test.cjs
node frontend/tests/retro-decoration-removed.test.cjs
```
Expected: FAIL. `drop caps must be removed`

- [ ] **Step 3: 드롭캡 제거**
  `global.css`에서 다음 규칙 3개를 블록째 삭제한다.
  - `.newsprint-prose>p:first-of-type::first-letter { … }`
  - `.newsprint-prose--no-dropcap p:first-of-type::first-letter { … }`
  - `.blog-shell .newsprint-prose>p:first-of-type::first-letter { … }`

  위 4개 파일에서 `newsprint-prose--no-dropcap` 클래스 토큰만 삭제한다(`newsprint-prose`는 유지). class 속성 형태가 파일마다 다를 수 있으니 `grep -rn "no-dropcap" frontend/src`로 확인하며 지운다.

- [ ] **Step 4: 이중선 교체**
  `global.css`의 `3px double var(--color-border)` 9곳(`grep -n "px double" frontend/src/styles/global.css`로 확인)을 모두 `1px solid var(--color-border)`로 바꾼다.
  ```bash
  sed -i 's/3px double var(--color-border)/1px solid var(--color-border)/g' frontend/src/styles/global.css
  ```
  `.newsprint-divider-thick`은 `border-top`만 남는 0높이 구분선이 된다. 이는 의도된 결과다. 점 줄(dot rule)은 2단계 헤더 작업에서 추가한다.

- [ ] **Step 5: 노이즈 제거**
  `html { … }` 규칙(BASE STYLES)에서 `background-image: url('data:image/svg+xml;utf8,…feTurbulence…');` 한 줄을 삭제한다. `--noise-opacity`는 Task 7에서 이미 사라졌다. `grep -n noise-opacity`로 남은 사용처가 없는지 확인한다.

- [ ] **Step 6: small-caps 키커 완화**
  아래 규칙에서 `text-transform: uppercase;`를 삭제하고, `letter-spacing` 값을 `0.02em`으로 바꾼다.
  - `.newsprint-kicker` (기본 규칙과 `@media (max-width: 767px)` 안의 규칙 모두. 모바일 규칙의 `letter-spacing: 0.08em`도 `0.02em`)
  - `.newsprint-subkicker`
  - `.blog-masthead-kicker`, `.blog-masthead-subkicker` (10033, 10044행 부근)
  - 이중선 줄이 있던 `font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;` 블록 2곳(원래 5885행, 10050행 부근. Step 4 이후에는 `1px solid`로 찾는다)

- [ ] **Step 7: 통과 확인**

Run: `node frontend/tests/retro-decoration-removed.test.cjs`
Expected: `retro-decoration-removed.test.cjs passed`

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/styles/global.css frontend/src/components/blog/BlogArticleLayout.astro "frontend/src/pages/ko/handbook/[slug].astro" "frontend/src/pages/en/handbook/[slug].astro" "frontend/src/pages/admin/handbook/edit/[slug].astro" frontend/tests/retro-decoration-removed.test.cjs
git commit -m "feat: remove retro newsprint decorations (drop caps, double rules, noise)"
```

### Task 10: 전체 회귀, 빌드, 시각 검증

**Files:** 없음 (검증만)

- [ ] **Step 1: 전체 테스트를 기준선과 비교** (repo 루트에서)

```bash
for f in frontend/tests/*.test.cjs frontend/tests/*.test.mjs; do node "$f" >/dev/null 2>&1 && echo "PASS $f" || echo "FAIL $f"; done | sort > /tmp/after.txt
grep -c PASS /tmp/after.txt
grep FAIL /tmp/after.txt
```
Expected: PASS **51** = 기준선 47 − 교체 2(`dark-theme-palette`, `blog-dropcap`) + 신규 6(`theme-module`, `theme-boot-script`, `theme-wiring`, `theme-palette`, `font-roles`, `retro-decoration-removed`). FAIL은 "사전 정보"의 기준선 FAIL 25개와 정확히 같아야 한다. 새로 생긴 FAIL이 있으면 원인을 고친 뒤 진행한다.

- [ ] **Step 2: 빌드**

Run: `cd frontend && npm run build`
Expected: 에러 0으로 완료

- [ ] **Step 3: 개발 서버로 시각 확인**
  `cd frontend && npm run dev`(기본 4321)를 띄운다. 각 테마와 화면 크기 조합에서 아래 페이지의 스크린샷을 찍는다.
  - 테마: 브라우저 콘솔에서 `localStorage.setItem('theme','<t>')` 후 새로고침. `<t>`는 light / white / dark
  - 크기: 데스크톱 1280px, 모바일 375px
  - 페이지: `/ko/`, `/ko/news/` 목록과 기사 1개, `/ko/handbook/` 상세 1개, `/ko/blog/` 글 1개, `/admin/`(로그인 가능할 때)

  확인 항목:
  1. 갈색 배경이나 금색 accent가 남은 곳이 없는가
  2. 텍스트가 배경에 묻히는 곳이 없는가
  3. 제호에서 "0to1"이 "oto1"로 보이지 않는가
  4. 코드 블록 색이 세 테마 모두에서 읽히는가
  5. KaTeX 수식이 세 테마에서 보이는가(`needsKatex` 기사)

  시각 버그는 computed style뿐 아니라 스크린샷으로도 확인한다(메모리의 feedback_visual_debugging).

- [ ] **Step 4: legacy 저장값 확인**
  `localStorage.setItem('theme','pink')` 후 새로고침하면 `document.documentElement.dataset.theme === 'light'`이고 `localStorage.theme === 'light'`여야 한다. `midnight`는 `dark`가 돼야 한다. `localStorage.removeItem('theme')` 후 OS 다크 모드에서는 `dark`, 라이트 모드에서는 `light`여야 한다(`resize_window`의 `colorScheme`으로 에뮬레이트).

- [ ] **Step 5: CSP 확인**
  dev 서버가 떠 있는 상태에서 실행한다.
  ```bash
  node frontend/tests/csp-inline-scripts.test.cjs http://127.0.0.1:4321
  ```
  기준선에서는 서버가 없어서 실패했다. 이번엔 부트 스크립트에 nonce가 붙었는지 본다. 이 테스트가 이번 변경과 무관한 이유로 실패하면 그 내용을 기록만 한다.

- [ ] **Step 6: 기록 커밋은 없음.** 문제가 발견되면 해당 Task로 돌아가 수정하고 그 Task의 커밋 규칙을 따른다.

### Task 11: vault 문서 갱신

**Files:**
- Modify: `vault/03-Features/Color-Theme.md` (테마 표를 light/white/dark 새 값으로)
- Modify: `vault/03-Features/Typography.md` (역할별 글꼴 표를 Newsreader/Hahmlet/Pretendard로)
- Modify: `vault/08-Design/Design-System.md` (테마와 글꼴 요약, `src/lib/theme.js` 단일 출처 명시)
- Modify: `vault/09-Implementation/plans/ACTIVE_SPRINT.md` (1단계 완료 항목과 증거: 커밋 해시, 스크린샷 경로)

- [ ] **Step 1:** 각 노트에서 옛 값(`#171311`, `#C8A66F`, Lora, Playfair, pink, midnight)을 `grep`으로 찾아 핵심 내용만 갱신한다. 변경 이력 설명은 넣지 않고 현재 상태만 적는다.
- [ ] **Step 2: 커밋**

```bash
git add vault/03-Features/Color-Theme.md vault/03-Features/Typography.md vault/08-Design/Design-System.md vault/09-Implementation/plans/ACTIVE_SPRINT.md
git commit -m "docs: sync design notes with soft newsprint phase 1"
```

---

## 범위 밖 (2단계 이후)

- 헤더 레이아웃: 점 줄, 제호 마침표, 섹션 메뉴의 점 표시, 제N호와 오늘 N건
- 망점 이미지 처리(`.halftone`)
- 페이지별 레이아웃(홈, 기사, 목록 등)
- CSS 파일 분리
- Pretendard 800 정리, `--color-cat-*` 토큰 삭제

## 실행 결과

**커밋:** `ffac2fb0..0448f82a` (main). **검증:** 전체 테스트 54 PASS / 23 FAIL (23개는 모두 기준선의 기존 실패, 신규 실패 없음), `npm run build` 에러 0, 3개 테마와 375px 모바일에서 주요 페이지 브라우저 확인, 레거시 pink→light / midnight→dark 마이그레이션과 토글 순환 확인, CSP 콘솔 에러 없음.

**계획과 달라진 점**
- `theme.js`에 방어 로직 추가: localStorage 접근 차단(throw) 대비, 레거시 값 in-place 마이그레이션, 인라인 부트 스크립트(`THEME_BOOT_SCRIPT`)를 MainLayout과 auth/callback에 주입.
- 대비 부족으로 색 보정: 주석·경고색을 light `#615A50`(주석) / white `#5E6269`(주석) / 경고 `#855C08`로 조정.
- 한글 faux italic 제거, 헤딩에 `word-break: keep-all` + `text-wrap: balance` 적용.
- `newsprint-prose--no-dropcap` 클래스는 드롭캡 제거로 무의미해졌지만, 다른 세션이 해당 파일을 편집 중이라 마크업 정리를 미뤘다.

## 후속 작업

- [ ] 무효가 된 `newsprint-prose--no-dropcap` 클래스 제거: BlogArticleLayout, ko/en 핸드북 `[slug]`, admin 핸드북 edit
- [ ] `.admin-*` 스타일의 faux italic 정리
- [ ] Pretendard 800 굵기 정리
- [ ] `--color-cat-*` 토큰 삭제 (현재 모두 accent로 통일된 상태)
- [ ] 모바일 홈 히어로 제목 크기 조정 (375px에서 40px 제목이 6줄로 줄바꿈) → 3단계
