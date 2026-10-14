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
