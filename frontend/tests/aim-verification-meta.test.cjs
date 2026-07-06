const fs = require('fs');
const path = require('path');

const root = process.cwd();
const head = fs.readFileSync(path.join(root, 'frontend/src/components/Head.astro'), 'utf8');
const expectedMeta = '<meta name="aim-verification" content="aim_verify_WoMMLgke5Uu0xiEXjbR6fl_pXDrV2ydD" />';

if (!head.includes(expectedMeta)) {
  throw new Error(`Head.astro must include AIM verification meta tag: ${expectedMeta}`);
}

console.log('aim-verification-meta.test.cjs passed');
