const fs = require('fs');
const path = require('path');

function read(filePath) {
  return fs.readFileSync(path.join(__dirname, '..', filePath), 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const heroComponent = read('src/components/home/HomeSplitHero.astro');
assert(
  heroComponent.includes("['AI 뉴스를 읽고,', '개념을 쌓고,', '함께 해석하세요']"),
  'Korean hero headline must use the approved homepage copy',
);
assert(
  heroComponent.includes("['Read AI news,', 'build your understanding,', 'and make sense of it together']"),
  'English hero headline must match the updated homepage positioning',
);

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

const adminSettings = read('src/pages/admin/settings.astro');
assert(
  adminSettings.includes("home_intro: { ko: '가장 빠르게 AI 변화를 읽고, 필요한 용어를 바로 찾고, 읽은 뉴스와 용어를 쌓아가며, 서로의 생각을 나누는 공간입니다.'"),
  'Admin default Korean home intro must stay in sync with the homepage hero copy',
);
