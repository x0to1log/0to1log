// frontend/tests/issue-number-shell.test.cjs
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const src = path.join(__dirname, '..', 'src');
const read = (p) => fs.readFileSync(path.join(src, p), 'utf8');

const shell = read('components/newsprint/NewsprintShell.astro');
assert(/import\s*\{[^}]*issueNumber[^}]*\}\s*from\s*['"][./]+lib\/issue\.js['"]/.test(shell), 'NewsprintShell must import issueNumber from lib/issue.js');
assert(shell.includes('issueLabel(locale, issueNumber(displayDate))'), 'kicker must show the issue for the displayed date');
assert(!shell.includes('제01권') && !shell.includes('Vol.01'), 'hardcoded volume label must be removed');
assert(!/volumeLabel/.test(shell), 'volumeLabel prop is obsolete');

for (const p of ['pages/en/news/index.astro', 'pages/ko/news/index.astro', 'pages/en/handbook/index.astro', 'pages/ko/handbook/index.astro', 'pages/admin/settings.astro']) {
  assert(!read(p).includes('volume_issue'), `${p} must not use volume_issue`);
  assert(!read(p).includes('volumeLabel'), `${p} must not pass volumeLabel`);
}
console.log('issue-number-shell.test.cjs passed');
