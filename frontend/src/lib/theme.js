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
  return Object.prototype.hasOwnProperty.call(LEGACY_THEMES, value) ? LEGACY_THEMES[value] : null;
}

/** Stored preference wins; otherwise follow the OS color scheme. */
export function resolveTheme(stored, prefersDark) {
  return normalizeTheme(stored) ?? (prefersDark ? 'dark' : 'light');
}

export function nextTheme(current) {
  const idx = THEMES.indexOf(current);
  return THEMES[(idx + 1) % THEMES.length];
}

function safeStorage() {
  // Accessing window.localStorage itself can throw when site data is blocked.
  try { return localStorage; } catch { return null; }
}

function defaultEnv() {
  return { doc: document, storage: safeStorage(), win: window };
}

function storageOf(env) {
  try { return env.storage ?? null; } catch { return null; }
}

/** Read the effective theme. Migrates legacy stored values in place. */
export function readTheme(env = defaultEnv()) {
  const storage = storageOf(env);
  let stored = null;
  try { stored = storage?.getItem(STORAGE_KEY) ?? null; } catch { /* storage blocked */ }
  const normalized = normalizeTheme(stored);
  if (normalized && normalized !== stored) {
    try { storage?.setItem(STORAGE_KEY, normalized); } catch { /* ignore */ }
  }
  if (normalized) return normalized;
  let prefersDark = false;
  try { prefersDark = Boolean(env.win?.matchMedia?.('(prefers-color-scheme: dark)')?.matches); } catch { /* ignore */ }
  return resolveTheme(null, prefersDark);
}

/** Apply a theme to <html>, color-scheme and theme-color, and persist it. */
export function applyTheme(theme, env = defaultEnv()) {
  const safe = normalizeTheme(theme) ?? THEMES[0];
  const root = env.doc.documentElement;
  root.setAttribute('data-theme', safe);
  root.style.colorScheme = COLOR_SCHEMES[safe];
  env.doc.querySelector('meta[name="theme-color"]')?.setAttribute('content', THEME_COLORS[safe]);
  try { storageOf(env)?.setItem(STORAGE_KEY, safe); } catch { /* ignore */ }
}

/**
 * Inline <script is:inline> body for MainLayout and auth/callback.
 * Runs before paint and again after every ViewTransitions swap.
 * Generated from the constants above so theme names live in one place.
 */
export const THEME_BOOT_SCRIPT = `(function(){
var T=${JSON.stringify(THEMES)},C=${JSON.stringify(THEME_COLORS)},S=${JSON.stringify(COLOR_SCHEMES)},L=${JSON.stringify(LEGACY_THEMES)},K=${JSON.stringify(STORAGE_KEY)};
function boot(){
  var s=null,st=null;try{st=window.localStorage;s=st.getItem(K);}catch(e){}
  var t=T.indexOf(s)>=0?s:(Object.prototype.hasOwnProperty.call(L,s)?L[s]:null);
  if(t&&t!==s){try{st.setItem(K,t);}catch(e){}}
  if(!t){try{t=(window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches)?'dark':'light';}catch(e){t='light';}}
  var d=document.documentElement;d.setAttribute('data-theme',t);d.style.colorScheme=S[t];
  var m=document.querySelector('meta[name="theme-color"]');if(m){m.setAttribute('content',C[t]);}
}
boot();
if(!window.__themeBootBound){window.__themeBootBound=true;document.addEventListener('astro:after-swap',boot);}
})();`;
