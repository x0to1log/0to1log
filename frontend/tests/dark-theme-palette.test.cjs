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

const css = read('src/styles/global.css');

assert(css.includes('--color-bg-primary: #1F1A17;'), 'Dark theme bg primary must use Subtle Espresso value');
assert(css.includes('--color-bg-secondary: #191512;'), 'Dark theme bg secondary must use Subtle Espresso value');
assert(css.includes('--color-bg-tertiary: #25201C;'), 'Dark theme bg tertiary must use Subtle Espresso value');
assert(css.includes('--color-border: #433B32;'), 'Dark theme border must use Subtle Espresso value');
