const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');

function read(relPath) {
  return fs.readFileSync(path.join(root, relPath), 'utf8');
}

function exists(relPath) {
  return fs.existsSync(path.join(root, relPath));
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

[
  'src/lib/pageData/blogDetailPage.ts',
  'src/lib/pageData/newsDetailPage.ts',
  'src/lib/pageData/handbookDetailPage.ts',
].forEach((file) => {
  assert(exists(file), `Missing shared preview/detail helper: ${file}`);
});

[
  'src/pages/en/blog/[slug].astro',
  'src/pages/ko/blog/[slug].astro',
  'src/pages/en/news/[slug].astro',
  'src/pages/ko/news/[slug].astro',
  'src/pages/en/handbook/[slug].astro',
  'src/pages/ko/handbook/[slug].astro',
].forEach((file) => {
  const source = read(file);
  assert(source.includes("Astro.url.searchParams.get('preview') === '1'"), `${file} must understand preview=1`);
});

const enNews = read('src/pages/en/news/[slug].astro');
assert(enNews.includes("Astro.url.searchParams.get('previewPersona')"), 'News detail must support previewPersona');

const enHandbook = read('src/pages/en/handbook/[slug].astro');
assert(enHandbook.includes("Astro.url.searchParams.get('previewLevel')"), 'Handbook detail must support previewLevel');

[
  'src/pages/admin/blog/edit/[slug].astro',
  'src/pages/admin/edit/[slug].astro',
  'src/pages/admin/handbook/edit/[slug].astro',
].forEach((file) => {
  const source = read(file);
  assert(source.includes('<iframe'), `${file} must render an iframe-based preview`);
  assert(!source.includes('marked.parse'), `${file} must no longer render preview content with marked.parse`);
  assert(source.includes('history.pushState'), `${file} must sync preview state into URL history`);
  assert(source.includes('popstate'), `${file} must react to browser history changes`);
  assert(source.includes('ResizeObserver'), `${file} must resize preview iframe to live content height`);
});

const blogLayout = read('src/components/blog/BlogArticleLayout.astro');
assert(blogLayout.includes('previewMode?: boolean;'), 'Blog article layout must support previewMode');
assert(blogLayout.includes("data-preview-mode={previewMode ? 'true' : 'false'}"), 'Blog article layout must expose preview mode to scripts');
assert(blogLayout.includes('Admin preview'), 'Blog article layout must show a preview read-only banner');
assert(blogLayout.includes('aria-disabled={previewMode ?'), 'Blog article layout must visibly disable gated actions in preview');
assert(blogLayout.includes('Preview mode · comments are read-only.'), 'Blog article layout must explain read-only comments in preview');

const newsLayout = read('src/components/newsprint/NewsprintArticleLayout.astro');
assert(newsLayout.includes('previewMode?: boolean;'), 'News article layout must support previewMode');
assert(newsLayout.includes("data-preview-mode={previewMode ? 'true' : 'false'}"), 'News article layout must expose preview mode to scripts');
assert(newsLayout.includes('Admin preview'), 'News article layout must show a preview read-only banner');
assert(newsLayout.includes('aria-disabled={previewMode ?'), 'News article layout must visibly disable gated actions in preview');
assert(newsLayout.includes('Preview mode · comments are read-only.'), 'News article layout must explain read-only comments in preview');

const handbookFeedback = read('src/components/newsprint/HandbookFeedback.astro');
assert(handbookFeedback.includes('previewMode?: boolean;'), 'Handbook feedback must support previewMode');
assert(handbookFeedback.includes("data-preview-mode={previewMode ? 'true' : 'false'}"), 'Handbook feedback must expose preview mode');
assert(handbookFeedback.includes('Preview mode'), 'Handbook feedback must show preview-specific guidance');

const handbookDetail = read('src/pages/en/handbook/[slug].astro');
assert(handbookDetail.includes('Admin preview'), 'Handbook detail page must show a preview read-only banner');
assert(handbookDetail.includes('aria-disabled={previewMode ?'), 'Handbook detail page must visibly disable bookmark action in preview');

const commentsScript = read('src/scripts/comments.ts');
assert(commentsScript.includes("const previewMode = section.dataset.previewMode === 'true';"), 'Comments script must detect preview mode');

const bookmarkScript = read('src/scripts/bookmark.ts');
assert(bookmarkScript.includes("if (btn.dataset.previewMode === 'true') return;"), 'Bookmark script must bail out in preview mode');

const likesScript = read('src/scripts/likes.ts');
assert(likesScript.includes("if (btn.dataset.previewMode === 'true') return;"), 'Likes script must bail out in preview mode');

const feedbackScript = read('src/scripts/handbookFeedback.ts');
assert(feedbackScript.includes("const previewMode = root.dataset.previewMode === 'true';"), 'Handbook feedback script must detect preview mode');

const globalCss = read('src/styles/global.css');
assert(globalCss.includes('admin-preview-frame-shell--loading'), 'Preview shell must have loading styles');
assert(globalCss.includes('newsprint-preview-banner'), 'Preview banner styling must exist');
assert(globalCss.includes('newsprint-engage-btn[aria-disabled="true"]'), 'Disabled preview actions must have dedicated styles');

console.log('admin-live-preview.test.cjs passed');
