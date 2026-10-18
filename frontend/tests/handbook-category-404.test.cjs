// frontend/tests/handbook-category-404.test.cjs
// Unknown handbook field: real 404 rendered in the page (status + notice), not a soft 404 or an empty Response.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8').replace(/\r\n/g, '\n');

for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/handbook/category/[slug].astro`);
  // getHandbookCategoryLabel falls back to the raw slug, so the check must use the known list
  assert(page.includes('const notFound = !(categories as string[]).includes(slug);\nif (notFound) Astro.response.status = 404;'), `${locale}: unknown field → 404 status`);
  assert(!page.includes('new Response(null'), `${locale}: no empty Response (crashes on Vercel)`);
  assert(!page.includes('if (!categoryLabel) {'), `${locale}: old label check (never true) removed`);
  assert(/notFound\s*\?\s*\{ terms: \[\] as any\[\], totalTerms: 0, error: null \}\s*:\s*await getHandbookCategoryPageData\(locale, slug\)/.test(page), `${locale}: no data query for an unknown field`);
  assert(page.includes("import NewsprintNotice from '../../../../components/newsprint/NewsprintNotice.astro';"), `${locale}: imports NewsprintNotice`);
  assert(page.includes('<NewsprintNotice variant="notfound"') && page.includes("linkHref={`/${locale}/handbook/`} linkLabel={t[locale]['handbook.back']}"), `${locale}: notice links back to the glossary`);
  assert(page.includes('if (error) Astro.response.status = 503;'), `${locale}: 503 on loader error kept`);
  assert(page.includes('<MainLayout title={pageTitle} locale={locale}>'), `${locale}: title switches for the 404`);
}

console.log('handbook-category-404.test.cjs passed');
