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

const styles = read('src/styles/global.css');
assert(
  styles.includes('background-size: 1.2rem 1.2rem;'),
  'Handbook search input must enlarge the search icon'
);
assert(
  styles.includes('border-radius: 12px;'),
  'Handbook search input must use a softer rounded corner'
);
assert(
  styles.includes('--color-input-surface: #2A2420;') &&
    styles.includes('--color-input-surface: #E9E4D9;') &&
    styles.includes('--color-input-surface: #FFE1E7;'),
  'Handbook search input must define theme-specific input surface colors'
);
assert(
  styles.includes('background: var(--color-input-surface);'),
  'Handbook search input must use the themed input surface token'
);

const enPage = read('src/pages/en/handbook/index.astro');
const koPage = read('src/pages/ko/handbook/index.astro');

assert(
  enPage.includes('data-placeholder-hints') && koPage.includes('data-placeholder-hints'),
  'Handbook search inputs must declare localized placeholder hint lists'
);

const script = read('src/scripts/handbookSearchHints.ts');
assert(
  script.includes('prefers-reduced-motion'),
  'Handbook search hint animation must respect reduced-motion'
);
assert(
  script.includes('focus') && script.includes('blur') && script.includes('input'),
  'Handbook search hint animation must respond to focus, blur, and input'
);
assert(
  script.includes('pointerdown') && script.includes('touchstart'),
  'Handbook search hint animation must stop immediately on touch interaction'
);
assert(
  script.includes('MOBILE_RESUME_DELAY_MS'),
  'Handbook search hint animation must use a mobile-safe resume delay'
);
assert(
  styles.includes('@media (max-width: 640px)') &&
    styles.includes('min-height: 3rem;') &&
    styles.includes('font-size: 1rem;') &&
    styles.includes('background-size: 1.3rem 1.3rem;'),
  'Handbook search input must add mobile-specific sizing polish'
);
