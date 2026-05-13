const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');

const detailPages = [
  'src/pages/ko/news/[slug].astro',
  'src/pages/en/news/[slug].astro',
];

for (const page of detailPages) {
  const source = read(page);

  assert(
    source.includes('const shouldUsePublicNewsCache ='),
    `${page} must make public cache conditional explicit`,
  );
  assert(
    source.includes('!Astro.locals.user') && source.includes('!Astro.locals.accessToken'),
    `${page} must only public-cache anonymous news detail HTML because persona content is server-rendered`,
  );
  assert(
    source.includes("'Cache-Control', 'private, no-store'"),
    `${page} must prevent shared caching for authenticated persona-specific HTML`,
  );
  assert(
    source.includes("if (shouldUsePublicNewsCache) {\n  Astro.response.headers.set('Cache-Control', 'public, s-maxage=3600, stale-while-revalidate=86400');"),
    `${page} must only set public cache in the anonymous cache branch`,
  );
}

const pageData = read('src/lib/pageData/newsDetailPage.ts');
assert(
  pageData.includes("const personaKey = previewMode ? (previewPersona || 'learner') : (userPersona || 'learner')"),
  'detail page data must default anonymous/unset users to learner while honoring logged-in persona',
);

const personaTitle = read('src/lib/personaTitle.ts');
assert(
  personaTitle.includes("return profile?.persona || 'learner';"),
  'news list title resolution must default anonymous/unset users to learner',
);

console.log('news-persona-cache-policy.test.cjs passed');
