// frontend/tests/home-hero-copy.test.cjs
// Home intro block (bottom of the front page) + approved intro copy.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const read = (p) => fs.readFileSync(path.join(__dirname, '..', p), 'utf8');

assert(!fs.existsSync(path.join(__dirname, '..', 'src/components/home/HomeSplitHero.astro')), 'HomeSplitHero is replaced by HomeIntro');

const intro = read('src/components/home/HomeIntro.astro');
assert(intro.includes('class="home-intro"'), 'intro root');
assert(intro.includes('0to1log는 이런 곳이에요') && intro.includes('What 0to1log is'), 'ko/en intro title');
assert(intro.includes('{homeIntro}'), 'intro renders the admin-edited home_intro');
assert(intro.includes('href={`/${locale}/news/`}') && intro.includes('href={`/${locale}/handbook/`}'), 'two CTAs: news + glossary');
assert(!/data-type-words|home-type-|<script/.test(intro), 'no typewriter or script');

const koHome = read('src/pages/ko/index.astro');
assert(
  koHome.includes('가장 빠르게 AI 변화를 읽고, 필요한 용어를 바로 찾고, 읽은 뉴스와 용어를 쌓아가며, 서로의 생각을 나누는 공간입니다.'),
  'Korean homepage intro must use the approved homepage copy',
);
const enHome = read('src/pages/en/index.astro');
assert(
  enHome.includes('Stay on top of AI as it changes fast, look up the terms you need right away, build your own library of news and concepts, and share how you make sense of it with others.'),
  'English homepage intro must reflect the updated hero copy',
);
for (const [loc, page] of [['ko', koHome], ['en', enHome]]) {
  assert(/<HomeFrontPage locale=\{locale\} \{\.\.\.front\} \/>\s*<HomeIntro locale=\{locale\} homeIntro=\{homeIntro\} \/>/.test(page), `${loc}: front page first, intro below`);
  assert(!page.includes('HomeSplitHero'), `${loc}: no HomeSplitHero`);
}

const adminSettings = read('src/pages/admin/settings.astro');
assert(
  adminSettings.includes("home_intro: { ko: '가장 빠르게 AI 변화를 읽고, 필요한 용어를 바로 찾고, 읽은 뉴스와 용어를 쌓아가며, 서로의 생각을 나누는 공간입니다.'"),
  'Admin default Korean home intro must stay in sync with the homepage hero copy',
);
console.log('home-hero-copy.test.cjs passed');
