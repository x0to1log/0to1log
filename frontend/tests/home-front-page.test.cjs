// frontend/tests/home-front-page.test.cjs
// Home front page: masthead h1, dateline, 3-column page (earlier / lead / term), keyword plate.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

const comp = read('components/home/HomeFrontPage.astro');
assert(comp.includes('class="home-front"'), 'front page root');
assert((comp.match(/<h1[\s>]/g) || []).length === 1 && comp.includes('class="home-front-masthead"'), 'masthead is the single h1');
assert(/<h1 class="home-front-masthead">0to1log<span class="site-brand-dot" aria-hidden="true">\.<\/span><\/h1>/.test(comp), 'masthead text + accent period');
assert(!/\{\(lead \|\| term\) && \(/.test(comp), 'masthead and dateline always render');
assert(comp.includes('class="home-front-dateline"'), 'dateline');
assert(/오늘의 1면/.test(comp) && /최근 1면/.test(comp) && /Front page/.test(comp) && /Latest front page/.test(comp), 'lead label: today vs latest, ko/en');
assert(comp.includes('leadIsToday'), 'lead label depends on leadIsToday');
assert(comp.includes('postTypeLabel(locale, '), 'type labels come from lib/postType.js');
assert(/오늘의 용어/.test(comp) && /Term of the day/.test(comp), 'ko/en term label');
assert(/지난 지면/.test(comp) && /Earlier pages/.test(comp), 'ko/en earlier label');
assert(/아직 발행된 기사가 없어요/.test(comp) && /No stories published yet/.test(comp), 'empty state');
assert(comp.includes('class="home-front-plate"') && /오늘의 키워드/.test(comp) && /Today's keyword/.test(comp), 'keyword plate');
assert(comp.includes('href={`/${locale}/news/${lead.slug}/`}'), 'lead links to the news article');
assert(comp.includes('href={`/${locale}/handbook/${term.slug}/`}'), 'term links to the handbook');
assert(/<article class="home-front-lead">[\s\S]*class="home-front-plate"[\s\S]*<\/article>/.test(comp), 'plate sits inside the lead article');
const order = ['class="home-front-lead"', 'class="home-front-term"', 'class="home-front-earlier"'].map((s) => comp.indexOf(s));
assert(order.every((i) => i > 0) && order[0] < order[1] && order[1] < order[2], 'DOM order = reading order: lead, term, earlier');
assert(!/Astro\.locals/.test(comp), 'user-neutral (CDN cached)');

for (const locale of ['ko', 'en']) {
  const page = read(`pages/${locale}/index.astro`);
  assert(/import \{ getHomeFrontPageData \} from '\.\.\/\.\.\/lib\/pageData\/homeFrontPage'/.test(page), `${locale} page loads front page data`);
  assert(page.includes(`getHomeFrontPageData('${locale}')`), `${locale} page calls the loader`);
  assert(/<HomeFrontPage locale=\{locale\} \{\.\.\.front\} \/>/.test(page), `${locale} page renders the front page`);
  assert(page.includes('if (siteContentError) Astro.response.status = 503;'), `${locale} keeps 503 on site content error`);
}

const css = read('styles/global.css');
assert(/grid-template-areas:\s*"earlier lead term"/.test(css), 'desktop places earlier | lead | term');
assert(/\.home-front-grid > \*\s*\{\s*grid-area:\s*auto;/.test(css), 'mobile drops named areas so items stack in DOM order');
assert(!/\.home-front-[a-z-]+[^{]*\{[^}]*(?:^|[\s;{])order:/m.test(css), 'no CSS order on front page items ("border:" does not count)');
for (const sel of ['.home-front {', '.home-front-masthead {', '.home-front-dateline {', '.home-front-plate {', '.home-intro {']) {
  assert(css.includes(sel), `missing ${sel}`);
}
console.log('home-front-page.test.cjs passed');
