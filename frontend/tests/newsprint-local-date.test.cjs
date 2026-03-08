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

const shell = read('src/components/newsprint/NewsprintShell.astro');

assert(
  shell.includes('data-local-date'),
  'Newsprint shell must mark the kicker date for browser-local formatting'
);

assert(
  shell.includes('toLocaleDateString(locale'),
  'Newsprint shell must reformat the kicker date in the browser locale'
);
