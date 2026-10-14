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
