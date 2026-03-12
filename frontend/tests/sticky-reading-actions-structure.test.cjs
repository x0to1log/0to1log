const fs = require('fs');
const path = require('path');

const root = process.cwd();

function read(relPath) {
  return fs.readFileSync(path.join(root, relPath), 'utf8');
}

function assertIncludes(haystack, needle, label) {
  if (!haystack.includes(needle)) {
    throw new Error(`Missing ${label}: ${needle}`);
  }
}

function assertNotIncludes(haystack, needle, label) {
  if (haystack.includes(needle)) {
    throw new Error(`Unexpected ${label}: ${needle}`);
  }
}

const newsLayout = read('frontend/src/components/newsprint/NewsprintArticleLayout.astro');
const blogLayout = read('frontend/src/components/blog/BlogArticleLayout.astro');
const handbookEn = read('frontend/src/pages/en/handbook/[slug].astro');
const handbookKo = read('frontend/src/pages/ko/handbook/[slug].astro');
const css = read('frontend/src/styles/global.css');
const stickyActions = read('frontend/src/components/common/StickyReadingActions.astro');

assertNotIncludes(stickyActions, 'const shareDropdown = (', 'frontmatter JSX share dropdown constant');
assertIncludes(stickyActions, '<div class="newsprint-share-wrapper reading-actions__share-wrapper">', 'inline share dropdown markup');
assertIncludes(stickyActions, "const placementClass = placement === 'rail' ? 'reading-actions--rail-placement' : '';", 'placement class helper');
assertIncludes(stickyActions, 'reading-actions reading-actions--article ${placementClass}', 'article action rail modifier');
assertIncludes(stickyActions, 'reading-actions reading-actions--term reading-actions--article ${placementClass}', 'term action rail article modifier');
assertIncludes(stickyActions, 'class="reading-actions__items reading-actions__items--article"', 'article action group container');
assertIncludes(stickyActions, 'class="reading-actions__items reading-actions__items--article reading-actions__items--term"', 'term action group container');
assertIncludes(stickyActions, 'class="reading-actions__group reading-actions__group--primary"', 'primary action group');
assertIncludes(stickyActions, 'class="reading-actions__group reading-actions__group--secondary"', 'secondary action group');
assertIncludes(stickyActions, 'data-reading-action="like"', 'like action marker');
assertIncludes(stickyActions, 'data-reading-action="comments"', 'comments action marker');
assertIncludes(stickyActions, 'data-reading-action="helpful"', 'helpful action marker');
assertIncludes(stickyActions, 'data-reading-action="confusing"', 'confusing action marker');
assertIncludes(stickyActions, 'data-reading-action="bookmark"', 'bookmark action marker');
assertIncludes(stickyActions, 'data-reading-action="share"', 'share action marker');
assertIncludes(stickyActions, 'class="reading-actions__count" data-like-count', 'like count element');
assertIncludes(stickyActions, 'class="reading-actions__count" data-comment-count', 'comment count element');
assertNotIncludes(stickyActions, '<span>{copy.like}</span>', 'article like text label');
assertNotIncludes(stickyActions, '<span>{copy.comments}</span>', 'article comments text label');
assertNotIncludes(stickyActions, '<span>{copy.helpful}</span>', 'term helpful text label');
assertNotIncludes(stickyActions, '<span>{copy.confusing}</span>', 'term confusing text label');

assertIncludes(newsLayout, '<StickyReadingActions', 'news sticky actions component');
assertIncludes(blogLayout, '<StickyReadingActions', 'blog sticky actions component');
assertIncludes(newsLayout, 'showStickyActions?: boolean;', 'news layout sticky visibility prop');
assertIncludes(blogLayout, 'showStickyActions?: boolean;', 'blog layout sticky visibility prop');
assertIncludes(newsLayout, 'showStickyActions = true', 'news layout sticky default');
assertIncludes(blogLayout, 'showStickyActions = true', 'blog layout sticky default');
assertIncludes(newsLayout, "class={`reading-actions-layout ${showStickyActions ? 'reading-actions-layout--article' : ''}`.trim()}", 'news article action layout modifier');
assertIncludes(blogLayout, "class={`reading-actions-layout ${showStickyActions ? 'reading-actions-layout--article' : ''}`.trim()}", 'blog article action layout modifier');
assertIncludes(handbookEn, '<ReadingActionsRail', 'handbook EN rail action wrapper');
assertIncludes(handbookKo, '<ReadingActionsRail', 'handbook KO rail action wrapper');

assertNotIncludes(newsLayout, 'class="newsprint-engagement-bar"', 'legacy news inline engagement bar');
assertNotIncludes(blogLayout, 'class="newsprint-engagement-bar"', 'legacy blog inline engagement bar');
assertNotIncludes(handbookEn, '<HandbookFeedback', 'legacy handbook feedback card');
assertNotIncludes(handbookKo, '<HandbookFeedback', 'legacy handbook feedback card');
assertNotIncludes(handbookEn, 'class="newsprint-engagement-bar"', 'legacy handbook inline engagement bar');
assertNotIncludes(handbookKo, 'class="newsprint-engagement-bar"', 'legacy handbook inline engagement bar');

assertIncludes(css, '.reading-actions {', 'sticky action base styles');
assertIncludes(css, '.reading-actions-layout--article {', 'article action layout styles');
assertIncludes(css, '.reading-actions--article {', 'article action rail styles');
assertIncludes(css, '.reading-actions__items--article {', 'article action items styles');
assertIncludes(css, '.reading-actions__group--primary {', 'primary action group styles');
assertIncludes(css, '.reading-actions__group--secondary {', 'secondary action group styles');
assertIncludes(css, 'grid-template-columns: minmax(0, 1fr) 72px;', 'desktop article body-first grid');
assertIncludes(css, 'env(safe-area-inset-bottom', 'mobile safe area support');
assertIncludes(css, 'bottom: calc(100% + 0.5rem);', 'mobile share dropdown above trigger');
assertIncludes(css, 'right: calc(100% + 0.5rem);', 'desktop share dropdown opens left');
assertIncludes(css, '.reading-actions--article .newsprint-bookmark-icon svg {', 'article bookmark icon svg rule');
assertIncludes(css, '.reading-actions--article .newsprint-bookmark-icon--active svg {', 'article active bookmark icon svg rule');
assertIncludes(css, 'stroke: currentColor;', 'bookmark stroke visibility');
assertIncludes(css, 'fill: none;', 'bookmark default hollow state');

console.log('sticky-reading-actions-structure.test.cjs passed');
