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

const authPromptSheet = read('src/components/auth/AuthPromptSheet.astro');
assert(
  authPromptSheet.includes('product_like'),
  'Auth prompt copy should define a dedicated product_like action',
);
assert(
  authPromptSheet.includes('관심 가는 AI 도구를 모아두고 나중에 다시 살펴보세요'),
  'Auth prompt copy should include the approved Korean product save title',
);
assert(
  authPromptSheet.includes('Save AI tools you want to revisit'),
  'Auth prompt copy should include the approved English product save title',
);

const authPrompt = read('src/scripts/auth-prompt.ts');
assert(
  authPrompt.includes("type AuthAction = 'library' | 'bookmark' | 'like' | 'product_like' | 'feedback' | 'comment';"),
  'Auth prompt action union should include product_like',
);

const productLikeScript = read('src/scripts/productLike.ts');
assert(
  productLikeScript.includes("openAuthPrompt({ action: 'product_like'"),
  'Product like interactions should open the dedicated product_like auth prompt',
);

console.log('product-auth-prompt-copy.test.cjs passed');
