// frontend/src/scripts/newsDeskMode.ts
// News list: two-desk layout when the "all" tab is active and the search box is empty,
// single-column list otherwise. Rows whose cards are all hidden get data-row-empty.
// Runs after NewsprintCategoryFilter (data-filtered) and newsListSearch (data-search-matched).

function activeFilter(): string {
  const tab = document.querySelector<HTMLElement>(
    '.newsprint-filter-tabs[data-filter-key="post_type"] .newsprint-filter-tab[aria-selected="true"]',
  );
  return tab?.dataset.filter || new URLSearchParams(window.location.search).get('post_type') || 'all';
}

function update(): void {
  const root = document.querySelector<HTMLElement>('.news-desks');
  if (!root) return;
  const search = document.getElementById('news-search') as HTMLInputElement | null;
  const query = (search?.value ?? '').trim();
  root.dataset.mode = activeFilter() === 'all' && !query ? 'desks' : 'list';

  root.querySelectorAll<HTMLElement>('.news-desk-row, .news-desk-weekly').forEach((row) => {
    const hasVisible = Array.from(row.querySelectorAll<HTMLElement>('.newsprint-card')).some(
      (card) => card.dataset.filtered !== 'false' && card.dataset.searchMatched !== 'false',
    );
    if (hasVisible) row.removeAttribute('data-row-empty');
    else row.setAttribute('data-row-empty', 'true');
  });
}

function init(): void {
  const root = document.querySelector<HTMLElement>('.news-desks');
  if (!root || root.dataset.deskModeReady === 'true') return;
  root.dataset.deskModeReady = 'true';
  window.addEventListener('newsprint:filter-change', () => requestAnimationFrame(update));
  window.addEventListener('news:list-updated', update);
  update();
}

document.addEventListener('astro:page-load', init);
init();
