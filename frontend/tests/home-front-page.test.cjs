// frontend/tests/home-front-page.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

const comp = read('components/home/HomeFrontPage.astro');
assert(comp.includes('class="home-front"'), 'front strip root');
assert(/오늘의 1면/.test(comp) && /Today's front page/.test(comp), 'ko/en section title');
assert(/오늘의 용어/.test(comp) && /Term of the day/.test(comp), 'ko/en term label');
assert(comp.includes('href={`/${locale}/news/${lead.slug}/`}'), 'lead links to the news article');
assert(comp.includes('href={`/${locale}/handbook/${term.slug}/`}'), 'term links to the handbook');
assert(/\{\(lead \|\| term\) && \(/.test(comp), 'strip renders only when there is a lead or a term');

for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/index.astro`);
  assert(/import \{ getHomeFrontPageData \} from '\.\.\/\.\.\/lib\/pageData\/homeFrontPage'/.test(page), `${locale} page loads front page data`);
  assert(page.includes(`getHomeFrontPageData('${locale}')`), `${locale} page calls the loader`);
  assert(/<HomeFrontPage locale=\{locale\} \{\.\.\.front\} \/>/.test(page), `${locale} page renders the strip`);
  assert(/todayCount=\{front\.todayCount\}/.test(page), `${locale} hero receives todayCount`);
  assert(page.includes('if (siteContentError) Astro.response.status = 503;'), `${locale} keeps 503 on site content error`);
}

const css = fs.readFileSync(path.join(src, 'styles/global.css'), 'utf8');
for (const sel of ['.home-front {', '.home-front-grid {', '.home-front-term {']) {
  assert(css.includes(sel), `missing ${sel}`);
}
console.log('home-front-page.test.cjs passed');
