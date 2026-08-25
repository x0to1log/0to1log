const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');

const middleware = read('src/middleware.ts');
const navigation = read('src/components/Navigation.astro');

assert(
  !/pathname\.startsWith\('\/(?:en|ko)\/'\)[\s\S]{0,120}cookies\.set\('site-locale'/.test(middleware),
  'Localized page requests must not rewrite the locale cookie on every response',
);
assert(
  middleware.includes("cleanUrl.searchParams.delete('lang')"),
  'Explicit locale preference must redirect to a clean URL',
);
assert(
  middleware.includes('context.redirect(cleanPath, 303)'),
  'Locale cookie must be written on a redirect response, not content HTML',
);
assert(
  navigation.includes('function withLocalePreference'),
  'Language switch targets must explicitly persist the selected locale',
);
assert(
  navigation.includes('withLocalePreference(altPath, altLocale)'),
  'The rendered language link must use the locale preference helper',
);

console.log('public-locale-cache.test.cjs passed');
