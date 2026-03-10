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

const handbookRail = read('src/components/newsprint/HandbookListRail.astro');
assert(
  handbookRail.includes('About This Glossary'),
  'Handbook rail heading must say About This Glossary in English',
);
assert(
  handbookRail.includes('용어집 소개'),
  'Handbook rail heading must say 용어집 소개 in Korean',
);

const libraryIndex = read('src/pages/library/index.astro');
assert(
  libraryIndex.includes("tabProgress: 'My Progress'"),
  'Library English progress tab label must say My Progress',
);
