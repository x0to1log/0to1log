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

const listRailPath = path.join(__dirname, '..', 'src/components/newsprint/NewsprintListRail.astro');
assert(fs.existsSync(listRailPath), 'Missing NewsprintListRail.astro');

const listRail = read('src/components/newsprint/NewsprintListRail.astro');
assert(listRail.includes("Editor's Note"), 'Missing EN list rail heading: Editor\'s Note');
assert(listRail.includes('Most Read'), 'Missing EN list rail heading: Most Read');
assert(listRail.includes('Start Here'), 'Missing EN list rail heading: Start Here');
assert(listRail.includes('starterSections'), 'List rail must keep the curated Start Here section');
assert(listRail.includes('editorialNote'), 'List rail must keep the editorial note block');
assert(listRail.includes('오늘 바뀐 것부터 가장 빠르게 봅니다.'), 'KO AI News rail copy must use the updated description');
assert(listRail.includes('공부 개념과 메모 노트를 남깁니다.'), 'KO study rail copy must use the updated description');
assert(listRail.includes('일과 성장을 기록합니다.'), 'KO career rail copy must use the updated description');
assert(listRail.includes('만드는 과정과 회고를 기록합니다.'), 'KO project rail copy must use the updated description');

const enIndex = read('src/pages/en/log/index.astro');
const koIndex = read('src/pages/ko/log/index.astro');

assert(enIndex.includes('import NewsprintListRail'), 'EN log index must import NewsprintListRail');
assert(koIndex.includes('import NewsprintListRail'), 'KO log index must import NewsprintListRail');
assert(enIndex.includes('<NewsprintListRail'), 'EN log index must render NewsprintListRail');
assert(koIndex.includes('<NewsprintListRail'), 'KO log index must render NewsprintListRail');

const categories = read('src/lib/categories.ts');
assert(categories.includes("study: { en: 'Study', ko: '학습' }"), 'Study category label must be 학습 in Korean');
