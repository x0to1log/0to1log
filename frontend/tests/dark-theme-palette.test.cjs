const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');

function read(relPath) {
  return fs.readFileSync(path.join(root, relPath), 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function extractThemeBlock(css, themeName) {
  const pattern = new RegExp(`\\[data-theme="${themeName}"\\] \\{([\\s\\S]*?)\\n\\}`, 'm');
  const match = css.match(pattern);
  assert(match, `Could not find ${themeName} theme block`);
  return match[1];
}

function assertToken(block, token, value, label) {
  assert(
    block.includes(`  ${token}: ${value};`),
    `${label} must be ${value}`,
  );
}

function assertIncludes(haystack, needle, label) {
  assert(haystack.includes(needle), `${label} must include ${needle}`);
}

const css = read('src/styles/global.css');
const darkTheme = extractThemeBlock(css, 'dark');
const midnightTheme = extractThemeBlock(css, 'midnight');

assertToken(darkTheme, '--color-bg-primary', '#171311', 'Dark theme primary background');
assertToken(darkTheme, '--color-bg-secondary', '#100D0B', 'Dark theme secondary background');
assertToken(darkTheme, '--color-bg-tertiary', '#201B18', 'Dark theme tertiary background');
assertToken(darkTheme, '--color-bg-card', '#1C1714', 'Dark theme card background');
assertToken(darkTheme, '--color-input-surface', '#1D1916', 'Dark theme input surface');
assertToken(darkTheme, '--color-text-primary', '#E7DFCF', 'Dark theme primary text');
assertToken(darkTheme, '--color-border', '#4A4137', 'Dark theme border');
assertToken(darkTheme, '--color-accent', '#C8A66F', 'Dark theme accent');
assertToken(darkTheme, '--color-accent-glow', 'rgba(200, 166, 111, 0.16)', 'Dark theme accent glow');
assertToken(darkTheme, '--color-accent-subtle', 'rgba(200, 166, 111, 0.09)', 'Dark theme accent subtle fill');

assertToken(midnightTheme, '--color-bg-primary', '#070910', 'Midnight theme primary background');
assertToken(midnightTheme, '--color-bg-secondary', '#0D1118', 'Midnight theme secondary background');
assertToken(midnightTheme, '--color-bg-tertiary', '#171C26', 'Midnight theme tertiary background');
assertToken(midnightTheme, '--color-bg-card', '#10151E', 'Midnight theme card background');
assertToken(midnightTheme, '--color-input-surface', '#121822', 'Midnight theme input surface');
assertToken(midnightTheme, '--color-text-primary', '#D6DCE8', 'Midnight theme primary text');
assertToken(midnightTheme, '--color-border', '#353D50', 'Midnight theme border');
assertToken(midnightTheme, '--color-accent', '#C7B07B', 'Midnight theme accent');
assertToken(midnightTheme, '--color-accent-glow', 'rgba(199, 176, 123, 0.14)', 'Midnight theme accent glow');
assertToken(midnightTheme, '--color-accent-subtle', 'rgba(199, 176, 123, 0.07)', 'Midnight theme accent subtle fill');
assert(
  !midnightTheme.includes('rgba(100, 150, 255, 0.06)') && !midnightTheme.includes('rgba(100, 150, 255, 0.12)'),
  'Midnight theme should not mix blue hover surfaces into the gold accent system',
);

const head = read('src/components/Head.astro');
const navigation = read('src/components/Navigation.astro');
const adminSidebar = read('src/components/admin/AdminSidebar.astro');
const mainLayout = read('src/layouts/MainLayout.astro');
const authCallback = read('src/pages/auth/callback.astro');

assertIncludes(head, '<meta name="theme-color" content="#171311" />', 'Default theme-color meta tag');
assertIncludes(navigation, "dark: '#171311'", 'Navigation dark theme-color map');
assertIncludes(navigation, "midnight: '#070910'", 'Navigation midnight theme-color map');
assertIncludes(adminSidebar, "dark: '#171311'", 'Admin sidebar dark theme-color map');
assertIncludes(adminSidebar, "midnight: '#070910'", 'Admin sidebar midnight theme-color map');
assertIncludes(mainLayout, "dark: '#171311'", 'Main layout dark theme-color map');
assertIncludes(mainLayout, "midnight: '#070910'", 'Main layout midnight theme-color map');
assertIncludes(authCallback, "[data-theme=\"dark\"] { --bg: #171311; --fg: #E7DFCF; }", 'Auth callback dark palette');
assertIncludes(authCallback, "[data-theme=\"midnight\"] { --bg: #070910; --fg: #D6DCE8; }", 'Auth callback midnight palette');

console.log('dark-theme-palette.test.cjs passed');
