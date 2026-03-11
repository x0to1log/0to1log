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
    history.replaceState(null, '', url.toString());
  }

  function applySearch(updateUrl = false): void {
    const query = search.value.trim().toLowerCase();
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
  }

  search.addEventListener('input', () => applySearch(true));
  window.addEventListener('newsprint:filter-change', () => applySearch(false));

  requestAnimationFrame(() => applySearch(false));
}

document.addEventListener('astro:page-load', initNewsListSearch);
initNewsListSearch();
