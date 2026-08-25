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
    !source.includes("Astro.response.headers.set('Cache-Control'"),
    `${page} must rely on the centralized middleware cache policy`,
  );
}

const middleware = read('src/middleware.ts');
const cachePolicy = read('src/lib/server/publicCachePolicy.ts');
assert(
  middleware.includes('hasSessionCookie') && middleware.includes('finalizePublicResponse'),
  'Middleware must keep authenticated public HTML out of shared cache',
);
assert(
  cachePolicy.includes("cacheControl: 'private, no-store'") && cachePolicy.includes("vary: 'Cookie'"),
  'Central cache policy must separate personalized and anonymous HTML',
);

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
