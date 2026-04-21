/**
 * News list page — per-tab headline visibility.
 *
 * The page renders 3 headlines (business/research/weekly). This script listens
 * for filter-change events and shows only the matching headline:
 * - 'all' tab: show business headline only
 * - 'business' / 'research' / 'weekly' tab: show matching headline only
 *
 * Also hides the duplicate rest-grid card when its post_id matches the
 * currently visible type-specific headline (so research headline + research
 * grid don't both show the same latest post).
 */

function applyHeadlineFilter(filterValue: string): void {
  const container = document.querySelector<HTMLElement>('#news-list-results[data-multi-headline]');
  if (!container) return;

  const headlines = container.querySelectorAll<HTMLElement>('.newsprint-headline[data-post-type]');
  const visiblePostIds = new Set<string>();

  headlines.forEach((h) => {
    const type = h.dataset.postType || '';
    // 'all' tab: only business headline. Specific tabs: only matching headline.
    const show = filterValue === 'all' ? type === 'business' : type === filterValue;
    if (show) {
      h.removeAttribute('data-headline-hidden');
      const postId = h.dataset.postId;
      if (postId) visiblePostIds.add(postId);
    } else {
      h.setAttribute('data-headline-hidden', 'true');
    }
  });

  // Hide any rest-grid card that duplicates a currently-visible headline
  const cards = document.querySelectorAll<HTMLElement>(
    '.newsprint-grid-cards .newsprint-card[data-post-id]',
  );
  cards.forEach((card) => {
    const postId = card.dataset.postId;
    if (postId && visiblePostIds.has(postId)) {
      card.setAttribute('data-headline-duplicate', 'true');
    } else {
      card.removeAttribute('data-headline-duplicate');
    }
  });
}

function getInitialFilter(): string {
  const params = new URLSearchParams(window.location.search);
  return params.get('post_type') || 'all';
}

function init(): void {
  applyHeadlineFilter(getInitialFilter());

  window.addEventListener('newsprint:filter-change', (e) => {
    const detail = (e as CustomEvent).detail as { filterKey?: string; value?: string };
    if (detail?.filterKey === 'post_type') {
      applyHeadlineFilter(detail.value || 'all');
    }
  });
}

document.addEventListener('astro:page-load', init);
init();
