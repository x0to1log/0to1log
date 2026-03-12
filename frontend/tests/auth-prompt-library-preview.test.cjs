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

function extractBlock(source, selector) {
  const start = source.indexOf(`${selector} {`);
  assert(start !== -1, `Missing CSS block for ${selector}`);

  const bodyStart = source.indexOf('{', start);
  let depth = 0;

  for (let index = bodyStart; index < source.length; index += 1) {
    const char = source[index];
    if (char === '{') depth += 1;
    if (char === '}') depth -= 1;
    if (depth === 0) {
      return source.slice(bodyStart + 1, index);
    }
  }

  throw new Error(`Unclosed CSS block for ${selector}`);
}

const middleware = read('src/middleware.ts');
assert(!middleware.includes("pathname.startsWith('/library')"), 'Library routes should no longer be middleware-protected guest redirects');

const layout = read('src/layouts/MainLayout.astro');
assert(layout.includes("import AuthPromptSheet from '../components/auth/AuthPromptSheet.astro';"), 'MainLayout must include the shared auth prompt sheet');
assert(layout.includes('<AuthPromptSheet locale={locale} />'), 'MainLayout must render the shared auth prompt sheet');
assert(layout.includes("data-authenticated={Astro.locals.user ? 'true' : 'false'}"), 'MainLayout body must expose auth state for public action gates');

const libraryPage = read('src/pages/library/index.astro');
assert(!libraryPage.includes("return Astro.redirect(`/login?redirectTo=${encodeURIComponent('/library/')}`);"), 'Library page must not redirect guests to login');
assert(libraryPage.includes('const isAuthenticated = !!user && !!accessToken;'), 'Library page must branch between signed-in and guest preview states');
assert(libraryPage.includes('library-preview-card'), 'Library page must render a guest preview experience');
assert(libraryPage.includes('data-auth-action="library"'), 'Library guest preview CTA must open the shared auth prompt');

const authPrompt = read('src/scripts/auth-prompt.ts');
assert(authPrompt.includes('auth-prompt:open'), 'Shared auth prompt script must expose a custom-event entry point');
assert(authPrompt.includes('[data-auth-gate]'), 'Shared auth prompt script must wire declarative auth-gate triggers');

const authPromptSheet = read('src/components/auth/AuthPromptSheet.astro');
assert(authPromptSheet.includes('auth-prompt-handle'), 'Auth prompt sheet must expose a mobile bottom-sheet handle');
assert(authPromptSheet.includes('auth-prompt-header'), 'Auth prompt sheet must group header content for modal layout');

const authOauth = read('src/scripts/auth-oauth.ts');
assert(authOauth.includes('export function initOAuthButtons'), 'Shared OAuth helper must expose a reusable button initializer');
assert(authOauth.includes('sessionStorage.setItem'), 'Shared OAuth helper must preserve redirect targets before sign-in');

const loginPage = read('src/pages/login.astro');
assert(loginPage.includes("import { initOAuthButtons } from '../scripts/auth-oauth';"), 'Login page must reuse the shared OAuth button helper');

const bookmarkScript = read('src/scripts/bookmark.ts');
assert(bookmarkScript.includes('openAuthPrompt'), 'Bookmark interactions must open the auth prompt instead of redirecting immediately');

const likesScript = read('src/scripts/likes.ts');
assert(likesScript.includes('openAuthPrompt'), 'Like interactions must open the auth prompt instead of redirecting immediately');

const feedbackScript = read('src/scripts/handbookFeedback.ts');
assert(feedbackScript.includes('openAuthPrompt'), 'Handbook feedback must open the auth prompt for guests');

const newsLayout = read('src/components/newsprint/NewsprintArticleLayout.astro');
assert(newsLayout.includes('data-auth-action="comment"'), 'News article comments must declare comment auth-gate triggers');
assert(newsLayout.includes('#comments'), 'News article comment login redirect must return to the comment anchor');

const blogLayout = read('src/components/blog/BlogArticleLayout.astro');
assert(blogLayout.includes('data-auth-action="comment"'), 'Blog article comments must declare comment auth-gate triggers');
assert(blogLayout.includes('#comments'), 'Blog article comment login redirect must return to the comment anchor');

const globalCss = read('src/styles/global.css');
assert(globalCss.includes('.auth-prompt-handle'), 'Auth prompt styles must include a mobile sheet handle');
assert(globalCss.includes('place-items: end center;'), 'Auth prompt should dock to the bottom on smaller screens');
assert(globalCss.includes('.login-oauth-btn:focus-visible'), 'OAuth buttons should have a dedicated focus treatment');

const authPromptBlock = extractBlock(globalCss, '.auth-prompt');
assert(authPromptBlock.includes('place-items: end center;'), 'Auth prompt should dock to the bottom again');
assert(!authPromptBlock.includes('place-items: center;'), 'Auth prompt should no longer center on desktop');

const overlayBlock = extractBlock(globalCss, '.auth-prompt-overlay');
assert(!overlayBlock.includes('linear-gradient'), 'Auth prompt overlay should not use a gradient backdrop');
assert(/rgba\([^)]*,\s*0\.(?:2|3|4)/.test(overlayBlock), 'Auth prompt overlay should be more transparent so background content remains visible');

const sheetBlock = extractBlock(globalCss, '.auth-prompt-sheet');
assert(!sheetBlock.includes('linear-gradient'), 'Auth prompt sheet should not use a gradient surface');

const oauthButtonBlock = extractBlock(globalCss, '.auth-prompt .login-oauth-btn');
assert(!oauthButtonBlock.includes('linear-gradient'), 'Auth prompt OAuth buttons should not use gradient fills');

console.log('auth-prompt-library-preview.test.cjs passed');
