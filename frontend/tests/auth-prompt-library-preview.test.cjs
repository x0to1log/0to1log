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

console.log('auth-prompt-library-preview.test.cjs passed');
