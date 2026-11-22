import { withFindQuery } from '../lib/newsSearchLink.js';

function initNewsListSearch(): void {
  const results = document.getElementById('news-list-results');
  const search = document.getElementById('news-search') as HTMLInputElement | null;
  const countEl = document.getElementById('news-result-count');
  const noResults = document.getElementById('news-no-results');

  if (!results || !search || results.dataset.newsSearchReady === 'true') {
    return;
  }

  results.dataset.newsSearchReady = 'true';

  const cards = Array.from(
    results.querySelectorAll<HTMLElement>('.newsprint-card[data-search-text]'),
  );

  if (cards.length === 0) {
    return;
  }

  const params = new URLSearchParams(window.location.search);
  const initialQuery = params.get('q');
  if (initialQuery) {
    search.value = initialQuery;
  }

  function getActiveFilter(): string {
    const active = document.querySelector<HTMLElement>(
      '.newsprint-filter-tabs[data-filter-key="post_type"] .newsprint-filter-tab[aria-selected="true"]',
    );
    return active?.dataset.filter || 'all';
  }

  function syncQuery(query: string): void {
    const url = new URL(window.location.href);
    if (query) {
      url.searchParams.set('q', query);
    } else {
      url.searchParams.delete('q');
    }
    history.replaceState(history.state, '', url.toString());
  }

  // A story opened from a search carries the search text (?q=): the article highlights it and
  // shows its find box. Links are rewritten rather than intercepted so that opening in a new
  // tab and link prefetching carry it too.
  const storyLinks = Array.from(
    results.querySelectorAll<HTMLAnchorElement>('a.newsprint-card-stretched-link'),
  );

  function syncStoryLinks(text: string): void {
    storyLinks.forEach((link) => {
      const href = link.getAttribute('href');
      if (href) link.setAttribute('href', withFindQuery(href, text));
    });
  }

  function applySearch(updateUrl = false): void {
    if (!search) return;
    const query = search.value.trim().toLowerCase();
    syncStoryLinks(search.value);
    const activeFilter = getActiveFilter();
    let visibleCount = 0;

    cards.forEach((card) => {
      const haystack = (card.dataset.searchText || '').toLowerCase();
      const matchesSearch = !query || haystack.includes(query);
      card.setAttribute('data-search-matched', matchesSearch ? 'true' : 'false');

      if (matchesSearch && card.dataset.filtered !== 'false') {
        visibleCount += 1;
      }
    });

    const totalCount = cards.length;
    const isFiltered = Boolean(query) || activeFilter !== 'all';

    if (countEl) {
      countEl.textContent = isFiltered ? `${visibleCount} / ${totalCount}` : '';
      countEl.style.display = isFiltered ? 'block' : 'none';
    }

    if (noResults) {
      noResults.style.display = visibleCount === 0 && isFiltered ? 'block' : 'none';
    }

    if (updateUrl) {
      syncQuery(query);
    }
    window.dispatchEvent(new CustomEvent('news:list-updated'));
  }

  let debounceTimer: ReturnType<typeof setTimeout>;
  search.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => applySearch(true), 150);
  });
  window.addEventListener('newsprint:filter-change', () => applySearch(false));

  requestAnimationFrame(() => applySearch(false));
}

document.addEventListener('astro:page-load', initNewsListSearch);
initNewsListSearch();
