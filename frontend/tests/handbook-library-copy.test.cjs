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

const koIndex = read('src/pages/ko/handbook/index.astro');
const enIndex = read('src/pages/en/handbook/index.astro');
assert(
  enIndex.includes("sc.handbook_intro || 'A concise reference of technical terms across AI, backend, frontend, security, and operations.'"),
  'Handbook intro line must fall back to the English glossary description',
);
assert(
  koIndex.includes("sc.handbook_intro || 'AI, 백엔드, 프론트엔드, 보안, 운영 전반의 기술 용어를 한 곳에서 읽기 쉽게 정리합니다.'"),
  'Handbook intro line must fall back to the Korean glossary description',
);

const libraryIndex = read('src/pages/library/index.astro');
assert(
  libraryIndex.includes("tabProgress: 'My Progress'"),
  'Library English progress tab label must say My Progress',
);
