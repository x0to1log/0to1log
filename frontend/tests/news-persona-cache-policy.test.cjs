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
  /Zone 3a[\s\S]*getPublicContentCacheKind\(pathname\)[\s\S]*return finalizePublicResponse/.test(middleware),
  'Middleware must render cacheable public HTML without auth lookups',
);
assert(
  !/vary: 'Cookie'/.test(cachePolicy),
  'Vercel never caches Vary: Cookie responses; personalization must be hydrated client-side',
);

const pageData = read('src/lib/pageData/newsDetailPage.ts');
assert(
  pageData.includes("const personaKey = previewMode ? (previewPersona || 'learner') : 'learner'"),
  'cached news HTML must start on learner; saved persona is applied client-side',
);

const layout = read('src/components/newsprint/NewsprintArticleLayout.astro');
assert(
  layout.includes('onSessionReady') && layout.includes('session.persona'),
  'news layout must apply the signed-in reader persona after session hydration',
);

const personaTitle = read('src/lib/personaTitle.ts');
assert(
  personaTitle.includes("return profile?.persona || 'learner';"),
  'news list title resolution must default anonymous/unset users to learner',
);

console.log('news-persona-cache-policy.test.cjs passed');
